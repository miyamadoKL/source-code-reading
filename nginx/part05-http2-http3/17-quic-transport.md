# 第17章 QUIC トランスポート

> **本章で読むソース**
>
> - [`src/event/quic/ngx_event_quic.h`](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.h)
> - [`src/event/quic/ngx_event_quic.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.c)
> - [`src/event/quic/ngx_event_quic_connection.h`](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_connection.h)
> - [`src/event/quic/ngx_event_quic_streams.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_streams.c)
> - [`src/event/quic/ngx_event_quic_transport.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_transport.c)
> - [`src/event/quic/ngx_event_quic_ack.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_ack.c)
> - [`src/event/quic/ngx_event_quic_output.c`](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_output.c)

## この章の狙い

本章は、HTTP/3 の土台となる QUIC トランスポート層の実装を読む。
QUIC は UDP 上に信頼性のあるストリーム多重化と暗号化を載せたプロトコルであり、RFC 9000 で定義される。
nginx の QUIC 実装は `src/event/quic/` にあり、コアのイベントループに統合されている。
具体的には、UDP データグラムの受理からパケットの復号、フレームの解釈、ストリームの生成とフロー制御、コネクションIDの管理、そして輻輳制御までを追う。
HTTP/3 固有のヘッダー圧縮（QPACK）やフレームマッピングは第18章で扱い、本章ではトランスポート層に集中する。

## 前提

第7章のイベントループとタイマー、第8章の接続管理（`ngx_connection_t`、UDP の `ngx_udp_connection_t`）を前提とする。
TLS のハンドシェイクが OpenSSL 層で処理されることは第9章で見た。
QUIC は TLS 1.3 のハンドシェイクをプロトコルの接続確立に組み込んでいるため、暗号化の鍵導出は `ngx_event_quic_ssl.c` と OpenSSL のコールバックで処理されるが、本章ではその詳細には立ち入らない。

## 接続の確立：UDP から QUIC 接続へ

QUIC 接続は、クライアントから届いた Initial パケットを UDP ソケットで受けることから始まる。
`ngx_quic_recvmsg()` が UDP データグラムを読み、`ngx_quic_handle_datagram()` がデータグラム内のパケットを1つずつ解釈する。

[`src/event/quic/ngx_event_quic.c` L674-L776](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.c#L674-L776)

```c
static ngx_int_t
ngx_quic_handle_datagram(ngx_connection_t *c, ngx_buf_t *b,
    ngx_quic_conf_t *conf)
{
    size_t                  size;
    u_char                 *p, *start;
    ngx_int_t               rc;
    ngx_uint_t              good;
    ngx_quic_path_t        *path;
    ngx_quic_header_t       pkt;
    ngx_quic_connection_t  *qc;

    good = 0;
    path = NULL;

    size = b->last - b->pos;

    p = start = b->pos;

    while (p < b->last) {

        ngx_memzero(&pkt, sizeof(ngx_quic_header_t));
        pkt.raw = b;
        pkt.data = p;
        pkt.len = b->last - p;
        pkt.log = c->log;
        pkt.first = (p == start) ? 1 : 0;
        pkt.path = path;
        pkt.flags = p[0];
        pkt.raw->pos++;

        rc = ngx_quic_handle_packet(c, conf, &pkt);

        // ... (中略) ...

        if (rc == NGX_ERROR || rc == NGX_DONE) {
            return rc;
        }

        if (rc == NGX_OK) {
            good = 1;
        }

        path = pkt.path;

        b->pos = pkt.data + pkt.len;
        p = b->pos;
    }

    if (!good) {
        return NGX_DONE;
    }

    qc = ngx_quic_get_connection(c);

    if (qc) {
        qc->received += size;

        if ((uint64_t) (c->sent + qc->received) / 8 >
            (qc->streams.sent + qc->streams.recv_last) + 1048576)
        {
            ngx_log_error(NGX_LOG_INFO, c->log, 0, "quic flood detected");

            qc->error = NGX_QUIC_ERR_NO_ERROR;
            qc->error_reason = "QUIC flood detected";
            return NGX_ERROR;
        }
    }

    return NGX_OK;
}
```

1つの UDP データグラムには複数の QUIC パケットが詰め込まれていることがある（パケットの結合）。
ループは `p < b->last` の間、先頭からパケットを1つずつ取り出して `ngx_quic_handle_packet()` に渡す。
パケットの長さはヘッダーを解釈した時点で決まるため、次のパケットの開始位置は `pkt.data + pkt.len` で求まる。

まだ接続が存在しない場合（Initial パケットを初めて受けた場合）、`ngx_quic_handle_packet()` の中で `ngx_quic_new_connection()` が呼ばれ、`ngx_quic_connection_t` が確保される。

[`src/event/quic/ngx_event_quic.c` L231-L354](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.c#L231-L354)

```c
static ngx_quic_connection_t *
ngx_quic_new_connection(ngx_connection_t *c, ngx_quic_conf_t *conf,
    ngx_quic_header_t *pkt)
{
    ngx_uint_t              i;
    ngx_quic_tp_t          *ctp;
    ngx_quic_connection_t  *qc;

    qc = ngx_pcalloc(c->pool, sizeof(ngx_quic_connection_t));
    if (qc == NULL) {
        return NULL;
    }

    qc->keys = ngx_pcalloc(c->pool, sizeof(ngx_quic_keys_t));
    // ... (中略) ...

    qc->version = pkt->version;

    ngx_rbtree_init(&qc->streams.tree, &qc->streams.sentinel,
                    ngx_quic_rbtree_insert_stream);

    for (i = 0; i < NGX_QUIC_SEND_CTX_LAST; i++) {
        ngx_queue_init(&qc->send_ctx[i].frames);
        ngx_queue_init(&qc->send_ctx[i].sending);
        ngx_queue_init(&qc->send_ctx[i].sent);
        qc->send_ctx[i].largest_pn = NGX_QUIC_UNSET_PN;
        qc->send_ctx[i].largest_ack = NGX_QUIC_UNSET_PN;
        qc->send_ctx[i].largest_range = NGX_QUIC_UNSET_PN;
        qc->send_ctx[i].pending_ack = NGX_QUIC_UNSET_PN;
    }

    qc->send_ctx[0].level = NGX_QUIC_ENCRYPTION_INITIAL;
    qc->send_ctx[1].level = NGX_QUIC_ENCRYPTION_HANDSHAKE;
    qc->send_ctx[2].level = NGX_QUIC_ENCRYPTION_APPLICATION;

    ngx_queue_init(&qc->free_frames);

    ngx_quic_init_rtt(qc);

    // ... (中略) ...

    qc->congestion.window = ngx_min(10 * NGX_QUIC_MIN_INITIAL_SIZE,
                                    ngx_max(2 * NGX_QUIC_MIN_INITIAL_SIZE,
                                            14720));
    qc->congestion.ssthresh = (size_t) -1;
    qc->congestion.mtu = NGX_QUIC_MIN_INITIAL_SIZE;
    qc->congestion.recovery_start = ngx_current_msec - 1;

    // ... (中略) ...

    if (ngx_quic_keys_set_initial_secret(qc->keys, &pkt->dcid, c->log)
        != NGX_OK)
    {
        return NULL;
    }

    // ... (中略) ...

    if (ngx_quic_open_sockets(c, qc, pkt) != NGX_OK) {
        ngx_quic_keys_cleanup(qc->keys);
        return NULL;
    }

    c->idle = 1;
    ngx_reusable_connection(c, 1);

    // ... (中略) ...

    return qc;
}
```

`ngx_quic_connection_t` は QUIC 接続全体の状態を持つ構造体である。
初期化では、ストリームの赤黒木、3つの暗号化レベル（Initial、Handshake、Application）ごとの送信コンテキスト、フリーフレームのキュー、RTT の初期値、そして輻輳制御のウィンドウを設定する。
輻輳ウィンドウの初期値は RFC 9002 の推奨に従い、`10 * 1200` バイトと `14720` バイトの小さい方を取る。
初期秘密鍵はクライアントの DCID から導出され、Initial パケットの復号に使えるようになる。

`ngx_quic_run()` が呼ばれると、接続の読み込みハンドラが `ngx_quic_input_handler()` に差し替わり、以降の UDP データグラムは同じハンドラで処理される。

[`src/event/quic/ngx_event_quic.c` L200-L228](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.c#L200-L228)

```c
void
ngx_quic_run(ngx_connection_t *c, ngx_quic_conf_t *conf)
{
    ngx_int_t               rc;
    ngx_quic_connection_t  *qc;

    ngx_log_debug0(NGX_LOG_DEBUG_EVENT, c->log, 0, "quic run");

    rc = ngx_quic_handle_datagram(c, c->buffer, conf);
    if (rc != NGX_OK) {
        ngx_quic_close_connection(c, rc);
        return;
    }

    qc = ngx_quic_get_connection(c);

    ngx_add_timer(c->read, qc->tp.max_idle_timeout);

    if (!qc->streams.initialized) {
        ngx_add_timer(&qc->close, qc->conf->handshake_timeout);
    }

    ngx_quic_connstate_dbg(c);

    c->read->handler = ngx_quic_input_handler;

    return;
}
```

## パケットの復号とペイロードの処理

`ngx_quic_handle_packet()` は、まずパケットヘッダーを解釈して暗号化レベル（Initial、Handshake、Application）を決め、次に `ngx_quic_handle_payload()` で復号とフレーム解釈に進む。

[`src/event/quic/ngx_event_quic.c` L957-L1091](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.c#L957-L1091)

```c
static ngx_int_t
ngx_quic_handle_payload(ngx_connection_t *c, ngx_quic_header_t *pkt)
{
    ngx_int_t               rc;
    ngx_quic_send_ctx_t    *ctx;
    ngx_quic_connection_t  *qc;
    static u_char           buf[NGX_QUIC_MAX_UDP_PAYLOAD_SIZE];

    qc = ngx_quic_get_connection(c);

    // ... (中略) ...

    if (!ngx_quic_keys_available(qc->keys, pkt->level, 0)) {
        ngx_log_error(NGX_LOG_INFO, c->log, 0,
                      "quic no %s keys, ignoring packet",
                      ngx_quic_level_name(pkt->level));
        return NGX_DECLINED;
    }

    // ... (中略) ...

    pkt->keys = qc->keys;
    pkt->key_phase = qc->key_phase;
    pkt->plaintext = buf;

    ctx = ngx_quic_get_send_ctx(qc, pkt->level);

    rc = ngx_quic_decrypt(pkt, &ctx->largest_pn);
    if (rc != NGX_OK) {
        qc->error = pkt->error;
        qc->error_reason = "failed to decrypt packet";
        return rc;
    }

    pkt->decrypted = 1;

    // ... (中略) ...

    if (pkt->level == NGX_QUIC_ENCRYPTION_HANDSHAKE) {
        ngx_quic_discard_ctx(c, NGX_QUIC_ENCRYPTION_INITIAL);

        if (!qc->path->validated) {
            qc->path->validated = 1;
            ngx_post_event(&qc->push, &ngx_posted_events);
        }
    }

    if (pkt->level == NGX_QUIC_ENCRYPTION_APPLICATION) {
        ngx_quic_keys_discard(qc->keys, NGX_QUIC_ENCRYPTION_EARLY_DATA);
    }

    // ... (中略) ...

    c->log->action = "handling payload";

    if (pkt->level != NGX_QUIC_ENCRYPTION_APPLICATION) {
        return ngx_quic_handle_frames(c, pkt);
    }

    // ... (中略) ...

    return ngx_quic_handle_frames(c, pkt);
}
```

復号に成功すると、その暗号化レベルより下のキーは破棄される。
Handshake パケットの復号に成功すれば Initial キーを捨て、Application パケットを受ければ 0-RTT キーを捨てる。
これは RFC 9001 の鍵管理規則に従ったもので、不要になった鍵メモリを即座に解放する。

復号後のペイロードは `ngx_quic_handle_frames()` でフレームごとに解釈される。

[`src/event/quic/ngx_event_quic.c` L1174-L1443](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.c#L1174-L1443)

```c
static ngx_int_t
ngx_quic_handle_frames(ngx_connection_t *c, ngx_quic_header_t *pkt)
{
    // ... (中略) ...

    while (p < end) {

        // ... (中略) ...

        len = ngx_quic_parse_frame(pkt, p, end, &frame);

        if (len < 0) {
            qc->error = pkt->error;
            return NGX_ERROR;
        }

        ngx_quic_log_frame(c->log, &frame, 0);

        p += len;

        switch (frame.type) {
        case NGX_QUIC_FT_ACK:
            if (ngx_quic_handle_ack_frame(c, pkt, &frame) != NGX_OK) {
                return NGX_ERROR;
            }
            continue;

        case NGX_QUIC_FT_PADDING:
            continue;

        case NGX_QUIC_FT_CONNECTION_CLOSE:
        case NGX_QUIC_FT_CONNECTION_CLOSE_APP:
            do_close = 1;
            continue;
        }

        pkt->need_ack = 1;

        switch (frame.type) {

        case NGX_QUIC_FT_CRYPTO:
            if (ngx_quic_handle_crypto_frame(c, pkt, &frame) != NGX_OK) {
                return NGX_ERROR;
            }
            break;

        case NGX_QUIC_FT_STREAM:
            if (ngx_quic_handle_stream_frame(c, pkt, &frame) != NGX_OK) {
                return NGX_ERROR;
            }
            break;

        case NGX_QUIC_FT_MAX_DATA:
            // ... (中略) ...
            break;

        // ... (その他のフレーム種別) ...
        }
    }

    // ... (中略) ...

    if (pkt->path != qc->path && nonprobing) {
        if (ngx_quic_handle_migration(c, pkt) != NGX_OK) {
            return NGX_ERROR;
        }
    }

    if (ngx_quic_ack_packet(c, pkt) != NGX_OK) {
        return NGX_ERROR;
    }

    return NGX_OK;
}
```

フレームの解釈は `switch` の2段階構成になっている。
第1段階は ACK や PADDING、CONNECTION_CLOSE などの ack-eliciting でないフレームを処理し、第2段階は残りのフレームを処理する。
ack-eliciting なフレームを含むパケットは `pkt->need_ack = 1` が立ち、後で ACK が送られる。

ループの最後で、パケットの送信元が既知のパスと異なる場合に `ngx_quic_handle_migration()` が呼ばれる。
非プロービングフレーム（PATH_CHALLENGE 以外）が新アドレスから届いたとき、接続マイグレーションの処理が始まる。

## ストリーム管理

QUIC のストリームは、ストリームIDをキーにした**赤黒木**で管理される。

[`src/event/quic/ngx_event_quic_streams.c` L150-L170](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_streams.c#L150-L170)

```c
ngx_quic_stream_t *
ngx_quic_find_stream(ngx_rbtree_t *rbtree, uint64_t id)
{
    ngx_rbtree_node_t  *node, *sentinel;
    ngx_quic_stream_t  *qn;

    node = rbtree->root;
    sentinel = rbtree->sentinel;

    while (node != sentinel) {
        qn = (ngx_quic_stream_t *) node;

        if (id == qn->id) {
            return qn;
        }

        node = (id < qn->id) ? node->left : node->right;
    }

    return NULL;
}
```

ストリームIDは62ビットの整数であり、赤黒木で O(log n) の探索が行われる。
HTTP/2 のハッシュ表と違い、ストリームIDの範囲が広い QUIC では木構造が適している。

新しいストリームが届くと、`ngx_quic_get_stream()` が既存のストリームを検索し、なければ作成する。
このとき、連続するストリームIDのギャップを埋めるために、間に当たるストリームもまとめて作られる。

[`src/event/quic/ngx_event_quic_streams.c` L452-L495](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_streams.c#L452-L495)

```c
    for ( /* void */ ; min_id <= id; min_id += 0x04) {

        qs = ngx_quic_create_stream(c, min_id);

        if (qs == NULL) {
            if (ngx_quic_reject_stream(c, min_id) != NGX_OK) {
                return NULL;
            }

            continue;
        }

        ngx_queue_insert_tail(&qc->streams.uninitialized, &qs->queue);

        rev = qs->connection->read;
        rev->handler = ngx_quic_init_stream_handler;

        if (qc->streams.initialized) {
            ngx_post_event(rev, &ngx_posted_events);

            if (qc->push.posted) {
                ngx_delete_posted_event(&qc->push);
                ngx_post_event(&qc->push, &ngx_posted_events);
            }
        }
    }
```

ストリームIDの下位2ビットはストリームの種類（クライアント/サーバー起始、双方向/単方向）を表し、残りの上位ビットがストリームの通し番号である。
通し番号が飛んでいる場合（たとえばID 0 と ID 8 が届いて ID 4 が未着）、間のストリームも暗黙的にオープンされたとみなされる（RFC 9000, 2.1）。
作られたストリームは `uninitialized` キューに入れられ、TLS ハンドシェイク完了後に `ngx_quic_init_streams()` で一斉に初期化される。

各ストリームは `ngx_quic_stream_t` で表現され、それぞれが仮想的な `ngx_connection_t` を持つ。

[`src/event/quic/ngx_event_quic.h` L105-L127](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.h#L105-L127)

```c
struct ngx_quic_stream_s {
    ngx_rbtree_node_t              node;
    ngx_queue_t                    queue;
    ngx_connection_t              *parent;
    ngx_connection_t              *connection;
    uint64_t                       id;
    uint64_t                       sent;
    uint64_t                       acked;
    uint64_t                       send_max_data;
    uint64_t                       send_offset;
    uint64_t                       send_final_size;
    uint64_t                       recv_max_data;
    uint64_t                       recv_offset;
    uint64_t                       recv_window;
    uint64_t                       recv_last;
    uint64_t                       recv_final_size;
    ngx_quic_buffer_t              send;
    ngx_quic_buffer_t              recv;
    ngx_quic_stream_send_state_e   send_state;
    ngx_quic_stream_recv_state_e   recv_state;
    unsigned                       cancelable:1;
    unsigned                       fin_acked:1;
};
```

`send` と `recv` はストリーム固有のバッファ（`ngx_quic_buffer_t`）であり、送信データと受信データを保持する。
`send_max_data` と `recv_max_data` はストリームレベルのフロー制御ウィンドウ、`recv_window` はウィンドウの更新閾値である。
`send_state` と `recv_state` は RFC 9000 の状態機械（Ready、Send、DataSent、DataRecvd、ResetSent 等）を追う。

ストリームの `connection` は、HTTP/2 の場合と同様に、既存の HTTP エンジンが `ngx_connection_t` として扱える仮想的な接続である。
`recv`、`send`、`send_chain` には QUIC ストリーム専用の関数がセットされ、内部で `ngx_quic_buffer_t` の読み書きを行う。

## フロー制御

QUIC のフロー制御も HTTP/2 と同様に接続レベルとストリームレベルの2層で動く。
受信側では、STREAM フレームでデータを受けるたびに `recv_last` を進め、`recv_max_data` を超えたらフロー制御エラーとする。

[`src/event/quic/ngx_event_quic_streams.c` L1660-L1698](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_streams.c#L1660-L1698)

```c
static ngx_int_t
ngx_quic_control_flow(ngx_quic_stream_t *qs, uint64_t last)
{
    uint64_t                len;
    ngx_connection_t       *pc;
    ngx_quic_connection_t  *qc;

    pc = qs->parent;
    qc = ngx_quic_get_connection(pc);

    if (last <= qs->recv_last) {
        return NGX_OK;
    }

    len = last - qs->recv_last;

    // ... (中略) ...

    qs->recv_last += len;

    if (qs->recv_state == NGX_QUIC_STREAM_RECV_RECV
        && qs->recv_last > qs->recv_max_data)
    {
        qc->error = NGX_QUIC_ERR_FLOW_CONTROL_ERROR;
        return NGX_ERROR;
    }

    qc->streams.recv_last += len;

    if (qc->streams.recv_last > qc->streams.recv_max_data) {
        qc->error = NGX_QUIC_ERR_FLOW_CONTROL_ERROR;
        return NGX_ERROR;
    }

    return NGX_OK;
}
```

データを読み込んだ側は `ngx_quic_update_flow()` で `recv_offset` を進め、ウィンドウの半分を消費したら MAX_STREAM_DATA と MAX_DATA フレームでウィンドウを更新する。

[`src/event/quic/ngx_event_quic_streams.c` L1701-L1739](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_streams.c#L1701-L1739)

```c
static ngx_int_t
ngx_quic_update_flow(ngx_quic_stream_t *qs, uint64_t last)
{
    // ... (中略) ...

    if (last <= qs->recv_offset) {
        return NGX_OK;
    }

    len = last - qs->recv_offset;

    qs->recv_offset += len;

    if (qs->recv_max_data <= qs->recv_offset + qs->recv_window / 2) {
        if (ngx_quic_update_max_stream_data(qs) != NGX_OK) {
            return NGX_ERROR;
        }
    }

    qc->streams.recv_offset += len;

    if (qc->streams.recv_max_data
        <= qc->streams.recv_offset + qc->streams.recv_window / 2)
    {
        if (ngx_quic_update_max_data(pc) != NGX_OK) {
            return NGX_ERROR;
        }
    }

    return NGX_OK;
}
```

ウィンドウの1/2を閾値に使う点は HTTP/2 の1/4と異なるが、考え方は同じである。
データを読み込むたびに MAX_STREAM_DATA を送るとフレームのオーバーヘッドが大きくなるため、半分消費したところで1回だけ更新する。

## フレームの再利用とフリーリスト

`ngx_quic_frame_t` は、フレームの生成と ACK 待ちのキュー管理で頻繁に確保・解放される。
nginx は `qc->free_frames` というフリーリストでフレーム構造体を再利用する。

[`src/event/quic/ngx_event_quic_connection.h` L266-L268](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_connection.h#L266-L268)

```c
    ngx_queue_t                       free_frames;
    ngx_buf_t                        *free_bufs;
    ngx_buf_t                        *free_shadow_bufs;
```

フレームを使い切ると `free_frames` に戻し、次に使うときにそこから取る。
バッファ（`ngx_buf_t`）とシャドウバッファも `free_bufs`、`free_shadow_bufs` で同様に再利用される。
これにより、大量のストリームが同時にデータを送受信しても、フレーム構造体の確保がメモリプールを圧迫しない。

`max_frames` は同時存在できるフレーム数の上限であり、ストリーム数とバッファサイズから動的に計算される。

[`src/event/quic/ngx_event_quic.c` L322-L324](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.c#L322-L324)

```c
    qc->max_frames = (conf->max_concurrent_streams_uni
                      + conf->max_concurrent_streams_bidi)
                     * conf->stream_buffer_size / 2000;
```

この上限により、悪意のあるクライアントが大量のフレームを生成させてメモリを枯渇させる攻撃を防ぐ。

## 輻輳制御

QUIC の輻輳制御は `ngx_quic_congestion_t` で管理される。

[`src/event/quic/ngx_event_quic_connection.h` L174-L186](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic_connection.h#L174-L186)

```c
typedef struct {
    size_t                            in_flight;
    size_t                            window;
    size_t                            ssthresh;
    size_t                            w_max;
    size_t                            w_est;
    size_t                            w_prior;
    size_t                            mtu;
    ngx_msec_t                        recovery_start;
    ngx_msec_t                        idle_start;
    ngx_msec_t                        k;
    ngx_uint_t                        idle;
} ngx_quic_congestion_t;
```

`window` は輻輳ウィンドウ、`ssthresh` は slow start の閾値、`in_flight` は送出済みで ACK を待っているバイト数である。
初期ウィンドウは `ngx_quic_new_connection()` で設定され、`w_max` と `w_est` は BBR や Cubic のような先進的な輻輳制御アルゴリズムで使われる変数である。

パケットが ACK されると `ngx_quic_congestion_ack()` が呼ばれ、ウィンドウを拡大する。
ロスが検出されるとウィンドウを縮小し、`recovery_start` を設定して一定期間の回復モードに入る。

## 接続のクローズ

QUIC 接続のクローズは2段階で行われる。
まず `ngx_quic_finalize_connection()` が CONNECTION_CLOSE フレームをキューに入れ、`ngx_quic_close_connection()` が実際に送信と後始末を行う。

[`src/event/quic/ngx_event_quic.c` L468-L622](https://github.com/nginx/nginx/blob/release-1.31.2/src/event/quic/ngx_event_quic.c#L468-L622)

```c
void
ngx_quic_close_connection(ngx_connection_t *c, ngx_int_t rc)
{
    // ... (中略) ...

    if (!qc->closing) {

        for (i = 0; i < NGX_QUIC_SEND_CTX_LAST; i++) {
            ngx_quic_free_frames(c, &qc->send_ctx[i].frames);
            ngx_quic_free_frames(c, &qc->send_ctx[i].sent);
        }

        // ... (中略) ...

        if (rc == NGX_DONE) {
            // サイレントクローズ
        } else {
            // CONNECTION_CLOSE を送信
            for (i = 0; i < NGX_QUIC_SEND_CTX_LAST; i++) {
                ctx = &qc->send_ctx[i];

                if (!ngx_quic_keys_available(qc->keys, ctx->level, 1)) {
                    continue;
                }

                qc->error_level = ctx->level;
                (void) ngx_quic_send_cc(c);

                if (rc == NGX_OK) {
                    ngx_add_timer(&qc->close, 3 * ngx_quic_pto(c, ctx));
                }
            }
        }

        qc->closing = 1;
    }

    // ... (中略) ...

    if (ngx_quic_close_streams(c, qc) == NGX_AGAIN) {
        return;
    }

    // ... (中略) ...

    ngx_quic_close_sockets(c);
    ngx_quic_keys_cleanup(qc->keys);

    // ... (中略) ...

    c->destroyed = 1;

    pool = c->pool;

    ngx_close_connection(c);

    ngx_destroy_pool(pool);
}
```

`rc == NGX_DONE` はアイドルタイムアウトによるサイレントクローズであり、CONNECTION_CLOSE を送らずに状態を破棄する。
それ以外では、利用可能な暗号化レベルごとに CONNECTION_CLOSE を送り、PTO の3倍のタイマーを掛けて相手からの応答を待つ。
ストリームが残っていれば先にそれらを閉じ、すべて片付いてからソケットと鍵を解放する。

## まとめ

- QUIC 接続は UDP データグラムから始まり、`ngx_quic_handle_datagram()` がデータグラム内の複数パケットを順に処理する。
- 接続は `ngx_quic_connection_t` で管理され、3つの暗号化レベル（Initial、Handshake、Application）ごとに送信コンテキストを持つ。
- パケットの復号に成功すると、より低いレベルの鍵は即座に破棄される。
- ストリームは赤黒木で O(log n) に管理され、ストリームIDのギャップを埋めるために暗黙のストリームも作成される。
- フロー制御は接続レベルとストリームレベルの2層で動き、ウィンドウの半分を消費した時点で MAX_DATA / MAX_STREAM_DATA で更新する。
- フレーム構造体とバッファはフリーリストで再利用され、`max_frames` による上限でメモリ枯渇を防ぐ。
- 輻輳制御は Cubic ベースのウィンドウ管理で、ACK で拡大、ロスで縮小する。

## 関連する章

- [第7章 イベントループとタイマー](../part02-event/07-event-loop-and-timers.md)
- [第8章 接続管理と epoll](../part02-event/08-connection-and-epoll.md)
- [第16章 HTTP/2](16-http2.md)
- [第18章 HTTP/3](18-http3.md)
