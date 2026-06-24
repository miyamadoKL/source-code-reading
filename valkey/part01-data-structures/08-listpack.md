# 第8章 listpack コンパクト列

> **本章で読むソース**
>
> - [`src/listpack.h`](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.h)
> - [`src/listpack.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c)
> - [`src/ziplist.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/ziplist.c)（前身の形式として冒頭のみ）

## この章の狙い

`listpack` は、複数の要素を一つの連続したメモリ領域に直列化してまとめる構造である。
本章では、要素列を単一のアロケーションに詰め込むことでメモリと断片化を抑える仕組みと、各要素を最小バイト数で表す各エンコーディングを実コードで読む。
さらに、各要素の末尾に自分自身の長さを置くことで末尾から先頭へたどれる仕組み（back length）を確認する。

## 前提

第4章「[文字列 SDS](04-sds.md)」を先に読むと、要素として格納される短い文字列の扱いを具体的に思い描ける。
ただし本章は SDS の知識がなくても読める。

## 役割と使われ方

`listpack` は、要素数の少ないリスト、ハッシュ、ソート済みセットや、ストリームのエントリ表現として使われる小さなコンテナである。
これらの型は、要素が少なくサイズが小さいうちは `listpack` で表現し、閾値を超えると別のエンコーディングへ切り替える。
各型がどの条件で `listpack` を選ぶかは、第16章「[リスト型 t_list](../part03-objects-types/16-t-list.md)」、第18章「[ハッシュ型 t_hash](../part03-objects-types/18-t-hash.md)」、第19章「[ソート済みセット型 t_zset](../part03-objects-types/19-t-zset.md)」、第20章「[ストリーム型 t_stream](../part03-objects-types/20-t-stream.md)」で扱う。

`listpack` を指すポインタの型は `unsigned char *` である。
構造体ではなく生のバイト列であり、その先頭から末尾までが一つの連続領域に収まっている。
要素を一つ追加するたびに、この領域全体が再確保される場合がある点は、後の挿入処理で確認する。

## 全体のレイアウト

`listpack` は、固定長のヘッダ、可変長の要素列、終端を示す1バイトの順に並ぶ。
ヘッダのサイズと終端の値は次のように定義されている。

[`src/listpack.c` L48-L49](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L48-L49)

```c
#define LP_HDR_SIZE 6 /* 32 bit total len + 16 bit number of elements. */
#define LP_HDR_NUMELE_UNKNOWN UINT16_MAX
```

[`src/listpack.c` L97](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L97)

```c
#define LP_EOF 0xFF
```

ヘッダは6バイトである。
先頭の4バイトが領域全体のバイト数（total bytes）、続く2バイトが要素数（number of elements）を保持する。
末尾の終端バイトは `0xFF`（`LP_EOF`）である。

全体像を整形済みの図で示す。

```text
+--------+--------+--------+--------+--------+--------+-----------+-----------+-----+-----------+------+
| tot[0] | tot[1] | tot[2] | tot[3] | num[0] | num[1] | entry 0   | entry 1   | ... | entry N-1 | 0xFF |
+--------+--------+--------+--------+--------+--------+-----------+-----------+-----+-----------+------+
|<--------- total bytes (32bit) --->|<-- numele -->|                                          |      |
|<--------------- LP_HDR_SIZE = 6 ---------------->|<------------ 要素列（可変長）----------->| LP_EOF|

各 entry の内部:
+----------+----------+-----------+
| encoding |  value   |  backlen  |
+----------+----------+-----------+
|<-- 種別と長さ -->|<- 値 ->|<- 自分の長さ（後方走査用）->|
```

total bytes は領域全体のバイト数を持つため、要素列を先頭から走査しなくても領域全体の大きさが分かる。
要素数は2バイトしか持たないため、`UINT16_MAX`（`LP_HDR_NUMELE_UNKNOWN`）を超える数は表現できない。
この値が入っているときは「要素数は不明」を意味し、長さの取得には全要素の走査が必要になる。

ヘッダの読み書きはマクロで行う。
バイト列をリトルエンディアンで組み立てている。

[`src/listpack.c` L104-L107](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L104-L107)

```c
#define lpGetTotalBytes(p) \
    (((uint32_t)(p)[0] << 0) | ((uint32_t)(p)[1] << 8) | ((uint32_t)(p)[2] << 16) | ((uint32_t)(p)[3] << 24))

#define lpGetNumElements(p) (((uint32_t)(p)[4] << 0) | ((uint32_t)(p)[5] << 8))
```

空の `listpack` を作る `lpNew` を見ると、この最小構成が分かる。

[`src/listpack.c` L155-L162](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L155-L162)

```c
unsigned char *lpNew(size_t capacity) {
    unsigned char *lp = lp_malloc(capacity > LP_HDR_SIZE + 1 ? capacity : LP_HDR_SIZE + 1);
    if (lp == NULL) return NULL;
    lpSetTotalBytes(lp, LP_HDR_SIZE + 1);
    lpSetNumElements(lp, 0);
    lp[LP_HDR_SIZE] = LP_EOF;
    return lp;
}
```

確保する最小サイズは `LP_HDR_SIZE + 1` バイト、つまり6バイトのヘッダと1バイトの終端だけである。
total bytes には `LP_HDR_SIZE + 1`、要素数には `0` を書き、6バイト目に終端 `LP_EOF` を置く。
要素列はまだ存在せず、ヘッダの直後がそのまま終端になる。

## 要素のエンコード

要素列を省メモリにする核は、各要素を最小のバイト数で表すエンコーディングにある。
要素は整数または文字列のいずれかで表され、整数として表せる文字列は整数として格納する。
どちらに表すかを決めるのが `lpEncodeGetType` である。

[`src/listpack.c` L248-L262](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L248-L262)

```c
static inline int lpEncodeGetType(unsigned char *ele, uint32_t size, unsigned char *intenc, uint64_t *enclen) {
    int64_t v;
    if (string2ll((const char *)ele, size, (long long *)&v)) {
        lpEncodeIntegerGetType(v, intenc, enclen);
        return LP_ENCODING_INT;
    } else {
        if (size < 64)
            *enclen = 1 + size;
        else if (size < 4096)
            *enclen = 2 + size;
        else
            *enclen = 5 + (uint64_t)size;
        return LP_ENCODING_STRING;
    }
}
```

`string2ll` が成功すれば、その文字列は整数として解釈でき、整数エンコーディングを選ぶ。
たとえば文字列 `"12345"` は5バイトの文字列ではなく、2バイトの整数として格納される。
整数として解釈できなければ文字列エンコーディングを選ぶ。

### 整数エンコーディング

整数は、値の大きさに応じて1バイトから9バイトまでの幅で表す。
小さい値ほど短く表せるように、エンコーディングが段階的に用意されている。

[`src/listpack.c` L186-L235](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L186-L235)

```c
static inline void lpEncodeIntegerGetType(int64_t v, unsigned char *intenc, uint64_t *enclen) {
    if (v >= 0 && v <= 127) {
        /* Single byte 0-127 integer. */
        intenc[0] = v;
        *enclen = 1;
    } else if (v >= -4096 && v <= 4095) {
        /* 13 bit integer. */
        if (v < 0) v = ((int64_t)1 << 13) + v;
        intenc[0] = (v >> 8) | LP_ENCODING_13BIT_INT;
        intenc[1] = v & 0xff;
        *enclen = 2;
    } else if (v >= -32768 && v <= 32767) {
        /* 16 bit integer. */
        // ... (中略) ...
    } else {
        /* 64 bit integer. */
        uint64_t uv = v;
        intenc[0] = LP_ENCODING_64BIT_INT;
        // ... (中略) ...
        *enclen = 9;
    }
}
```

`0` から `127` までの値は、エンコーディングバイトそのものに値を埋め込み、わずか1バイトで表す。
このとき最上位ビットは `0` である。
これを判定するのが `LP_ENCODING_7BIT_UINT` 系のマクロである。

[`src/listpack.c` L55-L58](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L55-L58)

```c
#define LP_ENCODING_7BIT_UINT 0
#define LP_ENCODING_7BIT_UINT_MASK 0x80
#define LP_ENCODING_IS_7BIT_UINT(byte) (((byte) & LP_ENCODING_7BIT_UINT_MASK) == LP_ENCODING_7BIT_UINT)
#define LP_ENCODING_7BIT_UINT_ENTRY_SIZE 2
```

`-4096` から `4095` までは13ビット整数として2バイトで表す。
先頭バイトの上位3ビットにエンコーディング種別 `LP_ENCODING_13BIT_INT`（`0xC0`）を立て、残りのビットに値を分けて入れる。
これ以降、16ビット、24ビット、32ビット、64ビットと続き、値の範囲が広がるごとに必要なバイト数が増える。
負の整数は2の補数の形に変換してから格納する。

### 文字列エンコーディング

文字列は、長さに応じて3種類のエンコーディングを使い分ける。

[`src/listpack.c` L325-L341](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L325-L341)

```c
static inline void lpEncodeString(unsigned char *buf, unsigned char *s, uint32_t len) {
    if (len < 64) {
        buf[0] = len | LP_ENCODING_6BIT_STR;
        memcpy(buf + 1, s, len);
    } else if (len < 4096) {
        buf[0] = (len >> 8) | LP_ENCODING_12BIT_STR;
        buf[1] = len & 0xff;
        memcpy(buf + 2, s, len);
    } else {
        buf[0] = LP_ENCODING_32BIT_STR;
        buf[1] = len & 0xff;
        buf[2] = (len >> 8) & 0xff;
        buf[3] = (len >> 16) & 0xff;
        buf[4] = (len >> 24) & 0xff;
        memcpy(buf + 5, s, len);
    }
}
```

長さが64バイト未満なら、先頭1バイトの下位6ビットに長さを入れる6ビット文字列エンコーディングを使う。
このとき長さを表す追加のバイトは不要で、文字列本体を1バイトの直後に置く。
長さが4096バイト未満なら、長さに2バイトを使う12ビット文字列エンコーディングを使う。
それ以上なら、長さに4バイトを使う32ビット文字列エンコーディングを使う。
短い文字列ほど長さフィールドが小さく済み、要素1個あたりのオーバーヘッドが小さくなる。

各エンコーディングを識別する先頭バイトの値は、互いに重ならないように割り当てられている。
たとえば6ビット文字列は `0x80`、整数の各種別は `0xC0` 以上の値を使う。

[`src/listpack.c` L60-L91](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L60-L91)

```c
#define LP_ENCODING_6BIT_STR 0x80
#define LP_ENCODING_6BIT_STR_MASK 0xC0
#define LP_ENCODING_IS_6BIT_STR(byte) (((byte) & LP_ENCODING_6BIT_STR_MASK) == LP_ENCODING_6BIT_STR)

#define LP_ENCODING_13BIT_INT 0xC0
// ... (中略) ...
#define LP_ENCODING_64BIT_INT 0xF4
#define LP_ENCODING_64BIT_INT_MASK 0xFF
#define LP_ENCODING_IS_64BIT_INT(byte) (((byte) & LP_ENCODING_64BIT_INT_MASK) == LP_ENCODING_64BIT_INT)
#define LP_ENCODING_64BIT_INT_ENTRY_SIZE 10
```

### 値の取り出し

格納された要素を読み出すのが `lpGet` である。
先頭バイトのエンコーディング種別を見て、整数なら値を復元し、文字列なら領域内の文字列本体へのポインタを返す。

[`src/listpack.c` L510-L552](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L510-L552)

```c
    if (LP_ENCODING_IS_7BIT_UINT(p[0])) {
        negstart = UINT64_MAX; /* 7 bit ints are always positive. */
        negmax = 0;
        uval = p[0] & 0x7f;
        if (entry_size) *entry_size = LP_ENCODING_7BIT_UINT_ENTRY_SIZE;
    } else if (LP_ENCODING_IS_6BIT_STR(p[0])) {
        *count = LP_ENCODING_6BIT_STR_LEN(p);
        if (entry_size) *entry_size = 1 + *count + lpEncodeBacklen(NULL, *count + 1);
        return p + 1;
    } else if (LP_ENCODING_IS_13BIT_INT(p[0])) {
        uval = ((p[0] & 0x1f) << 8) | p[1];
        // ... (中略) ...
    } else if (LP_ENCODING_IS_32BIT_STR(p[0])) {
        *count = LP_ENCODING_32BIT_STR_LEN(p);
        if (entry_size) *entry_size = 5 + *count + lpEncodeBacklen(NULL, *count + 5);
        return p + 5;
    } else {
        uval = 12345678900000000ULL + p[0];
        negstart = UINT64_MAX;
        negmax = 0;
    }
```

文字列のときは、文字列本体へのポインタ（`p + 1` など）を返す。
このポインタは `listpack` の領域の内部を指している。
値をコピーして返すのではなく、領域内をそのまま指すため、読み出しに余分なメモリ確保が要らない。
整数のときは、エンコーディングから値を復元し、呼び出し側の変数に書き込む。

## back length による後方走査

各要素の末尾には、その要素自身の長さ（エンコーディングバイトと値の合計）を表す back length が置かれる。
これがあるため、ある要素の位置から、前の要素の先頭を計算でたどれる。
`listpack` には前方ポインタも後方ポインタもないが、この仕組みで末尾から先頭への走査ができる。

back length は可変長で、1バイトから5バイトで表す。
書き込むのが `lpEncodeBacklen` である。

[`src/listpack.c` L264-L304](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L264-L304)

```c
static inline unsigned long lpEncodeBacklen(unsigned char *buf, uint64_t l) {
    if (l <= 127) {
        if (buf) buf[0] = l;
        return 1;
    } else if (l <= 16383) {
        if (buf) {
            buf[0] = l >> 7;
            buf[1] = (l & 127) | 128;
        }
        return 2;
    } else if (l <= 2097151) {
        // ... (中略) ...
        return 3;
    } else if (l <= 268435455) {
        // ... (中略) ...
        return 4;
    } else {
        // ... (中略) ...
        return 5;
    }
}
```

長さが127以下なら1バイトで表せる。
それより大きいときは、7ビットずつに区切って複数バイトに分け、最上位ビットを継続フラグとして使う。
ここで重要なのは、バイトの並べ方が後方から読めるようにしてある点である。
最も後ろのバイトには長さの下位7ビットが入り、前へ進むほど上位のビットが入る。
継続を表すフラグ `128` は、最後尾以外のバイトに立つ。

この並びを末尾側から読んでいくのが `lpDecodeBacklen` である。

[`src/listpack.c` L306-L319](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L306-L319)

```c
static inline uint64_t lpDecodeBacklen(unsigned char *p) {
    uint64_t val = 0;
    uint64_t shift = 0;
    do {
        val |= (uint64_t)(p[0] & 127) << shift;
        if (!(p[0] & 128)) break;
        shift += 7;
        p--;
        if (shift > 28) return UINT64_MAX;
    } while (1);
    return val;
}
```

`lpDecodeBacklen` は、back length の最後尾のバイトを指す `p` から開始する。
下位7ビットを取り出して値に足し、継続フラグ（`128`）が立っていれば一つ前のバイト（`p--`）へ進む。
継続フラグが立っていなければ、そこが back length の先頭であり、走査を終える。
こうして、要素の末尾から、その要素自身の長さを復元する。

復元した長さを使って前の要素へ移るのが `lpPrev` である。

[`src/listpack.c` L412-L421](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L412-L421)

```c
unsigned char *lpPrev(unsigned char *lp, unsigned char *p) {
    assert(p);
    if (p - lp == LP_HDR_SIZE) return NULL;
    p--; /* Seek the first backlen byte of the last element. */
    uint64_t prevlen = lpDecodeBacklen(p);
    prevlen += lpEncodeBacklen(NULL, prevlen);
    p -= prevlen - 1; /* Seek the first byte of the previous entry. */
    lpAssertValidEntry(lp, lpBytes(lp), p);
    return p;
}
```

`lpPrev` は、現在の要素の先頭 `p` の1バイト手前へ移る。
そこは前の要素の back length の最後尾のバイトである。
`lpDecodeBacklen` で前の要素の長さ（エンコーディングと値の合計）を得て、それに back length 自身のバイト数を足す。
その合計だけ後ろへ戻ると、前の要素の先頭に着く。
`p - lp` がヘッダのサイズに等しいとき、`p` は先頭要素を指しているので、これ以上前はなく `NULL` を返す。

前方への走査はより単純である。
`lpNext` は、現在の要素の長さを先頭バイトのエンコーディングから求め、その分だけ進めば次の要素に着く。

[`src/listpack.c` L386-L407](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L386-L407)

```c
unsigned char *lpSkip(unsigned char *p) {
    unsigned long entrylen = lpCurrentEncodedSizeUnsafe(p);
    entrylen += lpEncodeBacklen(NULL, entrylen);
    p += entrylen;
    return p;
}

unsigned char *lpNext(unsigned char *lp, unsigned char *p) {
    assert(p);
    p = lpSkip(p);
    size_t bytes = lpBytes(lp);
    if (unlikely(p[0] == LP_EOF)) {
        /* EOF must only appear at the end of a listpack. */
        assert(p + 1 == lp + bytes);
        return NULL;
    }
    lpAssertValidEntry(lp, bytes, p);
    return p;
}
```

`lpSkip` は、要素のエンコード長を `lpCurrentEncodedSizeUnsafe` で求め、それに back length のバイト数を足して、要素一つ分だけポインタを進める。
進んだ先が終端 `LP_EOF` なら、それが最後の要素だったので `lpNext` は `NULL` を返す。

## 単一アロケーションの省メモリ

`listpack` が省メモリである核は、要素ごとにノードを確保せず、すべてを一つの連続領域に詰める点にある。
連結リストなら要素ごとに前後ポインタとアロケーションのヘッダが付くが、`listpack` はそれらを持たない。
要素は前節までに見たエンコーディングで最小バイトに詰められ、要素間の境界は各要素の長さから計算でたどる。
そのためポインタの分のメモリがいらず、確保単位が一つにまとまることでヒープの断片化も抑えられる。
要素が小さく数が多いときに、この効果が効く。

その代わり、要素の挿入は領域全体の再確保を伴う場合がある。
挿入処理 `lpInsert` の中核を見る。

[`src/listpack.c` L756-L791](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L756-L791)

```c
    /* We need to also encode the backward-parsable length of the element
     * and append it to the end: this allows to traverse the listpack from
     * the end to the start. */
    unsigned long backlen_size = (!del_ele) ? lpEncodeBacklen(backlen, enclen) : 0;
    uint64_t old_listpack_bytes = lpGetTotalBytes(lp);
    // ... (中略) ...
    uint64_t new_listpack_bytes = old_listpack_bytes + enclen + backlen_size - replaced_len;
    if (new_listpack_bytes > UINT32_MAX) return NULL;
    // ... (中略) ...
    unsigned char *dst = lp + poff; /* May be updated after reallocation. */

    /* Realloc before: we need more room. */
    if (new_listpack_bytes > old_listpack_bytes && new_listpack_bytes > lp_malloc_size(lp)) {
        if ((lp = lp_realloc(lp, new_listpack_bytes)) == NULL) return NULL;
        dst = lp + poff;
    }

    /* Setup the listpack relocating the elements to make the exact room
     * we need to store the new one. */
    if (where == LP_BEFORE) {
        memmove(dst + enclen + backlen_size, dst, old_listpack_bytes - poff);
    } else { /* LP_REPLACE. */
        memmove(dst + enclen + backlen_size, dst + replaced_len, old_listpack_bytes - poff - replaced_len);
    }
```

挿入では、新しい要素のエンコード長 `enclen` と back length のバイト数 `backlen_size` を加えた新しい総バイト数を求める。
領域が足りなければ `lp_realloc` で確保し直し、`memmove` で挿入位置より後ろの要素をずらして隙間を空ける。
その隙間に、エンコードした値と back length を書き込む。

[`src/listpack.c` L806-L817](https://github.com/valkey-io/valkey/blob/9.1.0/src/listpack.c#L806-L817)

```c
    if (!del_ele) {
        if (enctype == LP_ENCODING_INT) {
            memcpy(dst, eleint, enclen);
        } else if (elestr) {
            lpEncodeString(dst, elestr, size);
        } else {
            valkey_unreachable();
        }
        dst += enclen;
        memcpy(dst, backlen, backlen_size);
        dst += backlen_size;
    }
```

エンコード済みの値を書いた直後に、その要素の back length を書く。
これで「エンコーディング、値、back length」の並びが一つ完成する。
最後にヘッダの total bytes と要素数を更新して、挿入が終わる。
連続領域に詰める利点と引き換えに、挿入のたびに後続要素の移動と再確保が起こりうる。
これは要素数が小さいうちは小さなコストにとどまり、要素が増えると無視できなくなる。
そのため各型は閾値を超えると別のエンコーディングへ切り替える。

## 前身としての ziplist

`listpack` の前身にあたる形式が `ziplist` である。
`ziplist` も、要素列を一つの連続領域に詰める省メモリな形式という点では同じ発想に立つ。

[`src/ziplist.c` L11-L16](https://github.com/valkey-io/valkey/blob/9.1.0/src/ziplist.c#L11-L16)

```c
 * ZIPLIST OVERALL LAYOUT
 * ======================
 *
 * The general layout of the ziplist is as follows:
 *
 * <zlbytes> <zltail> <zllen> <entry> <entry> ... <entry> <zlend>
```

`ziplist` は、各要素の先頭に前の要素の長さ（`<prevlen>`）を置く形式である。
`listpack` は、長さを要素の末尾の back length に置く形式へ変わった。
本書では `ziplist` を前身の形式として事実のみ記すにとどめ、以後の章では `listpack` を扱う。

## まとめ

- `listpack` は、ヘッダ（total bytes と要素数）、要素列、終端バイト `0xFF` を一つの連続領域に直列化した構造である。
- 各要素は「エンコーディング、値、back length」の並びで表す。整数は値の大きさに応じて1〜9バイト、文字列は長さに応じて長さフィールドを1〜4バイトに詰める。
- 要素ごとにノードやポインタを持たず連続領域に詰めるため、メモリのオーバーヘッドと断片化を抑えられる。要素が小さく数が多いときに効く。
- 各要素末尾の back length は後方から読めるように並べてあり、`lpDecodeBacklen` と `lpPrev` で前の要素へたどれる。前方走査は `lpNext` がエンコード長から次の要素位置を求める。
- 挿入は領域全体の再確保と後続要素の移動を伴う場合があるため、各型は要素が増えると別のエンコーディングへ切り替える。
- `ziplist` は前身の形式で、長さを要素の先頭に置いていた。

## 関連する章

- 第9章「[quicklist](09-quicklist.md)」では、`listpack` をノードとしてつなぐリストの実装を扱う。
- 第16章「[リスト型 t_list](../part03-objects-types/16-t-list.md)」、第18章「[ハッシュ型 t_hash](../part03-objects-types/18-t-hash.md)」、第19章「[ソート済みセット型 t_zset](../part03-objects-types/19-t-zset.md)」、第20章「[ストリーム型 t_stream](../part03-objects-types/20-t-stream.md)」では、各型が `listpack` を選ぶ条件と切り替えの閾値を扱う。
