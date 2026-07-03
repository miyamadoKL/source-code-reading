# 第16章 HTTP/2

> **本章で読むソース**
>
> - [`src/http/v2/ngx_http_v2.h`](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.h)
> - [`src/http/v2/ngx_http_v2.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.c)
> - [`src/http/v2/ngx_http_v2_table.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2_table.c)
> - [`src/http/v2/ngx_http_v2_filter_module.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2_filter_module.c)
> - [`src/http/v2/ngx_http_v2_module.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2_module.c)

## この章の狙い

本章は、nginx が HTTP/2 接続をどのように処理するかを追う。
HTTP/2 は TCP 上のバイナリフレームプロトコルであり、1本の接続の上を複数のストリームが多重化される。
nginx の実装は、接続レベルの状態機械でフレームを解釈し、ストリームごとに仮想的な `ngx_connection_t` を割り当てて既存の HTTP エンジン（第9章以降）に流し込む構造になっている。
具体的には、`ngx_http_v2_init()` による接続の初期化、`ngx_http_v2_read_handler()` を入口とするフレームの読み込みループ、`ngx_http_v2_frame_states[]` によるフレーム種別の振り分け、HPACK の静的表と動的表を扱う `ngx_http_v2_table.c`、そして出力側の優先度付きキューと DATA フレームの分割を送る `ngx_http_v2_filter_module.c` を読む。

## 前提

第8章の接続管理（`ngx_connection_t`、epoll、posted キュー）と、第9章の HTTP リクエスト受理（`ngx_http_request_t`、パース後のフェーズエンジンへの受け渡し）を前提とする。
第11章のフィルタチェーン（`ngx_http_top_header_filter` の付け替え方式）も前提である。

## 接続の初期化：`ngx_http_v2_init()`

HTTP/2 の接続は、TLS の ALPN で `h2` が選ばれた場合、あるいは平文の Upgrade で `h2c` が成立した場合に始まる。
いずれの経路でも、最終的には `ngx_http_v2_init()` が読み込みイベントのハンドラとして呼ばれる。

[`src/http/v2/ngx_http_v2.c` L203-L331](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.c#L203-L331)

```c
void
ngx_http_v2_init(ngx_event_t *rev)
{
    // ... (中略) ...

    c = rev->data;
    hc = c->data;

    ngx_log_debug0(NGX_LOG_DEBUG_HTTP, c->log, 0, "init http2 connection");

    c->log->action = "processing HTTP/2 connection";

    // ... (中略) ...

    h2c = ngx_pcalloc(c->pool, sizeof(ngx_http_v2_connection_t));
    if (h2c == NULL) {
        ngx_http_close_connection(c);
        return;
    }

    h2c->connection = c;
    h2c->http_connection = hc;

    h2c->send_window = NGX_HTTP_V2_DEFAULT_WINDOW;
    h2c->recv_window = NGX_HTTP_V2_MAX_WINDOW;

    h2c->init_window = NGX_HTTP_V2_DEFAULT_WINDOW;

    h2c->frame_size = NGX_HTTP_V2_DEFAULT_FRAME_SIZE;

    // ... (中略) ...

    h2c->pool = ngx_create_pool(h2scf->pool_size, h2c->connection->log);

    // ... (中略) ...

    h2c->streams_index = ngx_pcalloc(c->pool, ngx_http_v2_index_size(h2scf)
                                              * sizeof(ngx_http_v2_node_t *));

    // ... (中略) ...

    if (ngx_http_v2_send_settings(h2c) == NGX_ERROR) {
        ngx_http_close_connection(c);
        return;
    }

    if (ngx_http_v2_send_window_update(h2c, 0, NGX_HTTP_V2_MAX_WINDOW
                                               - NGX_HTTP_V2_DEFAULT_WINDOW)
        == NGX_ERROR)
    {
        ngx_http_close_connection(c);
        return;
    }

    h2c->state.handler = ngx_http_v2_state_preface;

    ngx_queue_init(&h2c->waiting);
    ngx_queue_init(&h2c->dependencies);
    ngx_queue_init(&h2c->closed);

    c->data = h2c;

    // ... (中略) ...

    rev->handler = ngx_http_v2_read_handler;
    c->write->handler = ngx_http_v2_write_handler;

    // ... (中略) ...

    if (c->buffer) {
        p = c->buffer->pos;
        end = c->buffer->last;

        do {
            p = h2c->state.handler(h2c, p, end);

            if (p == NULL) {
                return;
            }

        } while (p != end);

        h2c->total_bytes += p - c->buffer->pos;
        c->buffer->pos = p;
    }

    ngx_http_v2_read_handler(rev);
}
```

`ngx_http_v2_connection_t` は HTTP/2 接続1本全体の状態を持つ。
`send_window` と `recv_window` は接続レベルのフロー制御ウィンドウ、`frame_size` は SETTINGS で合意した最大フレームサイズ、`streams_index` はストリームIDからストリームノードを引くハッシュ表、`pool` はストリームやフレームの確保に使う接続専用のメモリプールである。
`state.handler` には、次に読むべきバイト列の種類を示す関数ポインタが入る。
初期値は `ngx_http_v2_state_preface` であり、クライアントプリフェイスの24バイト（`"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"`）の検証から始まる。

初期化の途中で、SETTINGS フレームと WINDOW_UPDATE フレームを送っている。
SETTINGS で nginx 側の希望（`concurrent_streams` の上限など）を伝え、WINDOW_UPDATE で接続レベルのウィンドウをデフォルトの65535から最大値（2^31 - 1）へ引き上げる。
こうすることで、クライアントはストリームをすぐに使い始められる。

`c->data` は `ngx_http_connection_t` から `ngx_http_v2_connection_t` に差し替わる。
HTTP/1.x では `c->data` は `ngx_http_request_t` を指すが、HTTP/2 では接続が複数のリクエストを同時にさばくため、接続レベルのコンテキストが1つ上に来る。

## 状態機械によるフレーム解釈

HTTP/2 の受信は、`h2c->state.handler` を次々に呼び出すループで進む。
各ハンドラは、渡されたバイト列を消費して次のハンドラを `state.handler` にセットし、新しいポインタを返す。
データが足りなければ `ngx_http_v2_state_save()` で状態を保存して `NULL` を返し、次の読み込みイベントで続きから再開する。

[`src/http/v2/ngx_http_v2.c` L884-L916](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.c#L884-L916)

```c
static u_char *
ngx_http_v2_state_head(ngx_http_v2_connection_t *h2c, u_char *pos, u_char *end)
{
    uint32_t    head;
    ngx_uint_t  type;

    if (end - pos < NGX_HTTP_V2_FRAME_HEADER_SIZE) {
        return ngx_http_v2_state_save(h2c, pos, end, ngx_http_v2_state_head);
    }

    head = ngx_http_v2_parse_uint32(pos);

    h2c->state.length = ngx_http_v2_parse_length(head);
    h2c->state.flags = pos[4];

    h2c->state.sid = ngx_http_v2_parse_sid(&pos[5]);

    pos += NGX_HTTP_V2_FRAME_HEADER_SIZE;

    type = ngx_http_v2_parse_type(head);

    ngx_log_debug4(NGX_LOG_DEBUG_HTTP, h2c->connection->log, 0,
                   "http2 frame type:%ui f:%Xd l:%uz sid:%ui",
                   type, h2c->state.flags, h2c->state.length, h2c->state.sid);

    if (type >= NGX_HTTP_V2_FRAME_STATES) {
        ngx_log_error(NGX_LOG_INFO, h2c->connection->log, 0,
                      "client sent frame with unknown type %ui", type);
        return ngx_http_v2_state_skip(h2c, pos, end);
    }

    return ngx_http_v2_frame_states[type](h2c, pos, end);
}
```

フレームヘッダーの9バイトを読み、上位24ビットから長さを、下位8ビットから種別を取り出し、残りの32ビットからストリームIDとフラグを取り出す。
種別に対応するハンドラは静的配列 `ngx_http_v2_frame_states[]` に並んでおり、配列の境界外は `ngx_http_v2_state_skip()` で読み飛ばす。

[`src/http/v2/ngx_http_v2.c` L186-L200](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.c#L186-L200)

```c
static ngx_http_v2_handler_pt ngx_http_v2_frame_states[] = {
    ngx_http_v2_state_data,               /* NGX_HTTP_V2_DATA_FRAME */
    ngx_http_v2_state_headers,            /* NGX_HTTP_V2_HEADERS_FRAME */
    ngx_http_v2_state_priority,           /* NGX_HTTP_V2_PRIORITY_FRAME */
    ngx_http_v2_state_rst_stream,         /* NGX_HTTP_V2_RST_STREAM_FRAME */
    ngx_http_v2_state_settings,           /* NGX_HTTP_V2_SETTINGS_FRAME */
    ngx_http_v2_state_push_promise,       /* NGX_HTTP_V2_PUSH_PROMISE_FRAME */
    ngx_http_v2_state_ping,               /* NGX_HTTP_V2_PING_FRAME */
    ngx_http_v2_state_goaway,             /* NGX_HTTP_V2_GOAWAY_FRAME */
    ngx_http_v2_state_window_update,      /* NGX_HTTP_V2_WINDOW_UPDATE_FRAME */
    ngx_http_v2_state_continuation        /* NGX_HTTP_V2_CONTINUATION_FRAME */
};
```

この「関数ポインタ配列で種別を振り分ける」構造は、`if` の連鎖で種別を比較するより分岐コストが一定である。
未知の種別も配列の範囲外として1箇所で処理できる。

## HPACK：ヘッダーの圧縮と展開

HTTP/2 のヘッダーブロックは HPACK で符号化される。
nginx の HPACK 実装は、62エントリの**静的表**と、実行時に構築する**動的表**の2つで構成される。

### 静的表

静的表は RFC 7541 の付録に定義された62個のヘッダーフィールドの組であり、起動時に読み取り専用の配列として配置される。

[`src/http/v2/ngx_http_v2_table.c` L20-L82](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2_table.c#L20-L82)

```c
static ngx_http_v2_header_t  ngx_http_v2_static_table[] = {
    { ngx_string(":authority"), ngx_string("") },
    { ngx_string(":method"), ngx_string("GET") },
    { ngx_string(":method"), ngx_string("POST") },
    { ngx_string(":path"), ngx_string("/") },
    { ngx_string(":path"), ngx_string("/index.html") },
    { ngx_string(":scheme"), ngx_string("http") },
    { ngx_string(":scheme"), ngx_string("https") },
    { ngx_string(":status"), ngx_string("200") },
    // ... (中略) ...
    { ngx_string("www-authenticate"), ngx_string("") },
};
```

静的表の参照は配列アクセス1回で済むため、`:method: GET` や `:status: 200` のような高頻度のヘッダーは1バイトのインデックス指定だけで送受信できる。

### 動的表のリングバッファ

動的表は、接続ごとに確保するリングバッファで実現される。

[`src/http/v2/ngx_http_v2.h` L109-L121](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.h#L109-L121)

```c
typedef struct {
    ngx_http_v2_header_t           **entries;

    ngx_uint_t                       added;
    ngx_uint_t                       deleted;
    ngx_uint_t                       reused;
    ngx_uint_t                       allocated;

    size_t                           size;
    size_t                           free;
    u_char                          *storage;
    u_char                          *pos;
} ngx_http_v2_hpack_t;
```

`entries` はエントリへのポインタ配列、`storage` は名前と値の文字列本体を格納する4KBのリングバッファ、`pos` は次に書き込む位置である。
`added` と `deleted` は追加と削除の累積カウンタであり、`added - deleted` が現在のエントリ数になる。
エントリは `added % allocated` の位置に追加され、`deleted % allocated` の位置から削除される。
リングバッファの折り返しは、`storage` の終端に達したら先頭に戻ってコピーする処理で吸収される。

[`src/http/v2/ngx_http_v2_table.c` L237-L266](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2_table.c#L237-L266)

```c
    avail = h2c->hpack.storage + NGX_HTTP_V2_TABLE_SIZE - h2c->hpack.pos;

    entry->name.len = header->name.len;
    entry->name.data = h2c->hpack.pos;

    if (avail >= header->name.len) {
        h2c->hpack.pos = ngx_cpymem(h2c->hpack.pos, header->name.data,
                                    header->name.len);
    } else {
        ngx_memcpy(h2c->hpack.pos, header->name.data, avail);
        h2c->hpack.pos = ngx_cpymem(h2c->hpack.storage,
                                    header->name.data + avail,
                                    header->name.len - avail);
        avail = NGX_HTTP_V2_TABLE_SIZE;
    }
```

文字列がリングバッファの末尾をまたぐ場合は、残りにコピーしてから先頭に戻る。
この動的表のサイズは、エントリごとに32バイトのオーバーヘッドを加えた値で管理される（HPACK の仕様で、各エントリに32バイトの固定コストが課されている）。

### 出力側：既知ヘッダーの事前符号化

出力側の高速化は、nginx のバージョン文字列や `Accept-Encoding` などの頻出ヘッダーを、起動時に1度だけ HPACK 符号化して静的バッファに置いておく手法で実現されている。

[`src/http/v2/ngx_http_v2_filter_module.c` L123-L135](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2_filter_module.c#L123-L135)

```c
    static const u_char nginx[5] = { 0x84, 0xaa, 0x63, 0x55, 0xe7 };
#if (NGX_HTTP_GZIP)
    static const u_char accept_encoding[12] = {
        0x8b, 0x84, 0x84, 0x2d, 0x69, 0x5b, 0x05, 0x44, 0x3c, 0x86, 0xaa, 0x6f
    };
#endif

    static size_t nginx_ver_len = ngx_http_v2_literal_size(NGINX_VER);
    static u_char nginx_ver[ngx_http_v2_literal_size(NGINX_VER)];
```

`nginx[5]` は `"nginx"` を Huffman 符号化した結果をバイト列で保持したものである。
リクエストごとに Huffman エンコーダを呼ぶのではなく、既知の文字列はコンパイル済みのバイト列を `ngx_cpymem()` でコピーするだけである。
バージョン文字列も `static` バッファに初回だけ符号化して使い回す。

## ストリーム多重化と依存ツリー

HTTP/2 のストリームは、ストリームIDをキーにハッシュ表で引かれる。

[`src/http/v2/ngx_http_v2.c` L126-L127](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.c#L126-L127)

```c
#define ngx_http_v2_index_size(h2scf)  (h2scf->streams_index_mask + 1)
#define ngx_http_v2_index(h2scf, sid)  ((sid >> 1) & h2scf->streams_index_mask)
```

ストリームIDは奇数（クライアント起始）であり、右に1ビットシフトしてマスクで叩くことで、ハッシュ表のインデックスを得る。
マスクは2の累乗に制限されており（`streams_index_mask` のデフォルトは31）、ビット演算だけでインデックスが計算できる。

各ストリームは `ngx_http_v2_node_t` で表現され、依存ツリーを構成する。

[`src/http/v2/ngx_http_v2.h` L174-L185](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.h#L174-L185)

```c
struct ngx_http_v2_node_s {
    ngx_uint_t                       id;
    ngx_http_v2_node_t              *index;
    ngx_http_v2_node_t              *parent;
    ngx_queue_t                      queue;
    ngx_queue_t                      children;
    ngx_queue_t                      reuse;
    ngx_uint_t                       rank;
    ngx_uint_t                       weight;
    double                           rel_weight;
    ngx_http_v2_stream_t            *stream;
};
```

`parent` と `children` は依存関係のツリー構造、`rank` はツリーの深さ、`weight` は同一親の下での相対重み、`rel_weight` は親から自分までの重みの積を累積した値である。
`reuse` キューは、閉じたストリームのノードを再利用候補として管理するために使う。

### 出力キューの優先度挿入

ストリームから DATA フレームを送るとき、`ngx_http_v2_queue_frame()` はフレームを優先度に従って出力キューに挿入する。

[`src/http/v2/ngx_http_v2.h` L243-L266](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.h#L243-L266)

```c
static ngx_inline void
ngx_http_v2_queue_frame(ngx_http_v2_connection_t *h2c,
    ngx_http_v2_out_frame_t *frame)
{
    ngx_http_v2_out_frame_t  **out;

    for (out = &h2c->last_out; *out; out = &(*out)->next) {

        if ((*out)->blocked || (*out)->stream == NULL) {
            break;
        }

        if ((*out)->stream->node->rank < frame->stream->node->rank
            || ((*out)->stream->node->rank == frame->stream->node->rank
                && (*out)->stream->node->rel_weight
                   >= frame->stream->node->rel_weight))
        {
            break;
        }
    }

    frame->next = *out;
    *out = frame;
}
```

キューは `rank`（深さ）が小さい順、同じ `rank` なら `rel_weight` が大きい順に並ぶ。
依存ツリーの上位（根に近い）ストリームが先に送られ、同じ深さでは重みの大きいストリームが優先される。
`blocked` フラグの立っているフレーム（SETTINGS ACK など制御フレーム）や `stream == NULL` のフレームに出会うと、そこで挿入位置を決める。
これは、制御フレームがストリームの優先度に左右されずに確実に先頭に送られることを保証する。

この優先度付きキューが、本章の最適化の工夫である。
HTTP/2 の依存ツリーはクライアントが望む帯域配分を表現するものであり、nginx はフレームを送るたびにリストを走査して適切な位置に挿入する。
リンク드리ストの挿入は O(n) だが、キューの長さ（送出待ちフレーム数）は通常小さいため、ソート済み配列への挿入よりキャッシュに優しく、ロック不要で動く。

## フロー制御

HTTP/2 のフロー制御は、接続レベルとストリームレベルの2層で動く。
受信側では、DATA フレームを受けるたびにウィンドウを減らし、閾値を下回ったら WINDOW_UPDATE フレームで返す。

[`src/http/v2/ngx_http_v2.c` L968-L990](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.c#L968-L990)

```c
    if (size > h2c->recv_window) {
        ngx_log_error(NGX_LOG_INFO, h2c->connection->log, 0,
                      "client violated connection flow control: "
                      "received DATA frame length %uz, available window %uz",
                      size, h2c->recv_window);

        return ngx_http_v2_connection_error(h2c, NGX_HTTP_V2_FLOW_CTRL_ERROR);
    }

    h2c->recv_window -= size;

    if (h2c->recv_window < NGX_HTTP_V2_MAX_WINDOW / 4) {

        if (ngx_http_v2_send_window_update(h2c, 0, NGX_HTTP_V2_MAX_WINDOW
                                                   - h2c->recv_window)
            == NGX_ERROR)
        {
            return ngx_http_v2_connection_error(h2c,
                                                NGX_HTTP_V2_INTERNAL_ERROR);
        }

        h2c->recv_window = NGX_HTTP_V2_MAX_WINDOW;
    }
```

ウィンドウが最大値の1/4を下回った時点で、差分を WINDOW_UPDATE で返してウィンドウを最大値に戻す。
1/4 という閾値は、WINDOW_UPDATE フレームの送出頻度とウィンドウ枯渇のリスクのバランスを取った値である。

送信側では、`ngx_http_v2_flow_control()` が接続とストリームの両方のウィンドウを調べ、どちらかでも0以下なら `NGX_DECLINED` を返して送出を止める。
接続ウィンドウが0のときは、ストリームを `waiting` キューに入れて待機させる。

[`src/http/v2/ngx_http_v2_filter_module.c` L1408-L1427](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2_filter_module.c#L1408-L1427)

```c
static ngx_inline ngx_int_t
ngx_http_v2_flow_control(ngx_http_v2_connection_t *h2c,
    ngx_http_v2_stream_t *stream)
{
    ngx_log_debug3(NGX_LOG_DEBUG_HTTP, h2c->connection->log, 0,
                   "http2:%ui windows: conn:%uz stream:%z",
                   stream->node->id, h2c->send_window, stream->send_window);

    if (stream->send_window <= 0) {
        stream->exhausted = 1;
        return NGX_DECLINED;
    }

    if (h2c->send_window == 0) {
        ngx_http_v2_waiting_queue(h2c, stream);
        return NGX_DECLINED;
    }

    return NGX_OK;
}
```

`waiting` キューも優先度順に並べられており、WINDOW_UPDATE で接続ウィンドウが回復したときに、優先度の高いストリームから順に送出が再開される。

## 出力の送信：`ngx_http_v2_send_output_queue()`

フレームの送信は、`h2c->last_out` のリンクドリリストを走査して、全フレームのチェーンを1つの `ngx_chain_t` リストに連結し、`c->send_chain()` で1回のシステムコールで送る。

[`src/http/v2/ngx_http_v2.c` L508-L620](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.c#L508-L620)

```c
ngx_int_t
ngx_http_v2_send_output_queue(ngx_http_v2_connection_t *h2c)
{
    // ... (中略) ...

    cl = NULL;
    out = NULL;

    for (frame = h2c->last_out; frame; frame = fn) {
        frame->last->next = cl;
        cl = frame->first;

        fn = frame->next;
        frame->next = out;
        out = frame;
    }

    cl = c->send_chain(c, cl, 0);

    // ... (中略) ...

    for ( /* void */ ; out; out = fn) {
        fn = out->next;

        if (out->handler(h2c, out) != NGX_OK) {
            out->blocked = 1;
            break;
        }

        // ... (中略) ...
    }

    // ... (中略) ...

    h2c->last_out = frame;

    // ... (中略) ...
}
```

全フレームのバッファチェーンを1列に並べて `send_chain()` で送るため、複数のフレームが1回の `writev()` で送出される。
送信後に各フレームのハンドラを呼び、完全に送れたフレームは `free_frames` リストに回収して再利用する。
部分的にしか送れなかったフレームは `blocked` を立て、残りのチェーンを `h2c->last_out` に保持して次回に送る。

## フラッド検出

HTTP/2 は HTTP/1.x よりオーバーヘッドが小さい反面、小さなフレームを大量に送るフラッド攻撃のリスクがある。
nginx は受信バイト数とペイロードバイト数の比率を監視し、異常を検出すると接続を切る。

[`src/http/v2/ngx_http_v2.c` L434-L438](https://github.com/nginx/nginx/blob/release-1.31.2/src/http/v2/ngx_http_v2.c#L434-L438)

```c
        if (h2c->total_bytes / 8 > h2c->payload_bytes + 1048576) {
            ngx_log_error(NGX_LOG_INFO, c->log, 0, "http2 flood detected");
            ngx_http_v2_finalize_connection(h2c, NGX_HTTP_V2_NO_ERROR);
            return;
        }
```

`total_bytes` はフレームヘッダーを含む総受信バイト数、`payload_bytes` は DATA フレームのペイロードなど実際に処理に使うバイト数である。
総バイト数がペイロードの8倍を超え、かつ1MBの余裕を超えた場合にフラッドと判定する。
正常な通信では、フレームヘッダー9バイトに対してペイロードは数百バイト以上になるため、この比率は容易に満たされない。

## まとめ

- HTTP/2 接続は `ngx_http_v2_connection_t` で管理され、状態機械のハンドラを次々に呼び出すループでフレームを解釈する。
- フレーム種別の振り分けは関数ポインタ配列 `ngx_http_v2_frame_states[]` で行われ、未知種別は一律で読み飛ばす。
- HPACK の静的表は配列アクセス1回で参照でき、出力側は頻出ヘッダーを事前符号化した静的バッファで毎リクエストの符号化コストを省く。
- 動的表はリングバッファで実装され、文字列が末尾をまたぐ場合は2回のコピーで吸収する。
- 出力キューは依存ツリーの `rank` と `rel_weight` で優先度順に並べられ、制御フレームは優先度を無視して先に送られる。
- フロー制御は接続レベルとストリームレベルの2層で動き、ウィンドウが1/4を下回った時点で WINDOW_UPDATE を返す。
- フラッド検出は総バイト数とペイロードバイト数の比率で判定する。

## 関連する章

- [第8章 接続管理と epoll](../part02-event/08-connection-and-epoll.md)
- [第9章 HTTP リクエストの受理とパース](../part03-http/09-http-request-parsing.md)
- [第11章 フィルタチェーンと output chain](../part03-http/11-filter-chain-and-output-chain.md)
- [第17章 QUIC トランスポート](17-quic-transport.md)
- [第18章 HTTP/3](18-http3.md)
