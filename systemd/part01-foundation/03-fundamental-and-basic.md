# 第3章 fundamental と basic のメモリ管理とデータ構造

> 本章で読むソース
>
> - [`src/fundamental/string-util.h`](https://github.com/systemd/systemd/blob/v261.1/src/fundamental/string-util.h#L32-L45)
> - [`src/fundamental/string-util.h`](https://github.com/systemd/systemd/blob/v261.1/src/fundamental/string-util.h#L104-L110)
> - [`src/basic/hashmap.c`](https://github.com/systemd/systemd/blob/v261.1/src/basic/hashmap.c#L123-L128)
> - [`src/basic/hashmap.c`](https://github.com/systemd/systemd/blob/v261.1/src/basic/hashmap.c#L155-L177)
> - [`src/basic/hashmap.c`](https://github.com/systemd/systemd/blob/v261.1/src/basic/hashmap.c#L192-L227)
> - [`src/basic/hashmap.c`](https://github.com/systemd/systemd/blob/v261.1/src/basic/hashmap.c#L794-L806)
> - [`src/basic/mempool.c`](https://github.com/systemd/systemd/blob/v261.1/src/basic/mempool.c#L21-L63)
> - [`src/basic/alloc-util.c`](https://github.com/systemd/systemd/blob/v261.1/src/basic/alloc-util.c#L77-L110)

## この章の狙い

systemd の全コードが土台とする二つの層、`fundamental` と `basic` を読む。
ハッシュマップ、メモリプール、動的配列という基礎部品が、どのように速度とメモリ効率を両立させているのかを把握する。

## 前提

読者は C のポインタと構造体、`malloc`/`realloc`/`free`、オープンアドレス法のハッシュテーブルの概念を理解していることを前提とする。
第1章で見た `fundamental` → `basic` という依存の向きを踏まえる。

## fundamental 層：カーネルと共有できる最小コード

`src/fundamental/` は systemd の最も内側の層である。
特徴は、通常のユーザー空間プログラムだけでなく、UEFI ブートスタブ（`systemd-boot`）でも同じコードを使える点にある。
そのため libc に依存しない書き方をし、文字型さえも切り替えられるようになっている。

[`src/fundamental/string-util.h` L32-L45](https://github.com/systemd/systemd/blob/v261.1/src/fundamental/string-util.h#L32-L45)

```c
#if SD_BOOT
#  define strlen strlen16
#  define strcmp strcmp16
#  define strncmp strncmp16
#  define strcasecmp strcasecmp16
#  define strncasecmp strncasecmp16
#  define strspn strspn16
#  define strcspn strcspn16
#  define STR_C(str)       (L ## str)
typedef char16_t sd_char;
#else
#  define STR_C(str)       (str)
typedef char sd_char;
#endif
```

`SD_BOOT` が定義されるとき、つまり EFI 環境でコンパイルするときは、文字型が UTF-16 の `char16_t` になり、文字列関数も UTF-16 版に差し替えられる。
通常のユーザー空間では `sd_char` は普通の `char` である。
同じ `startswith` や `streq` のロジックを、型引数を切り替えるだけで両環境に供給できる。

小さなヘルパーも `static inline` で置かれる。

[`src/fundamental/string-util.h` L104-L110](https://github.com/systemd/systemd/blob/v261.1/src/fundamental/string-util.h#L104-L110)

```c
static inline bool isempty(const sd_char *a) {
        return !a || a[0] == '\0';
}

static inline const sd_char *strempty(const sd_char *s) {
        return s ?: STR_C("");
}
```

`isempty` は NULL と空文字列を同一に扱い、`strempty` は NULL を空文字列に読み替える。
systemd のコードは文字列ポインタが NULL でも安全に扱えるヘルパーを多用し、NULL 判定の分岐をコードのあちこちに散らさない。

## basic 層：Hashmap の内部表現

`src/basic/hashmap.c` は systemd 全体で最も使われるデータ構造を実装する。
`Hashmap`（キーから値へのマップ）、`OrderedHashmap`（挿入順を保つマップ）、`Set`（集合）の三つが、共通の基底 `HashmapBase` の上に作られる。

[`src/basic/hashmap.c` L192-L227](https://github.com/systemd/systemd/blob/v261.1/src/basic/hashmap.c#L192-L227)

```c
struct HashmapBase {
        const struct hash_ops *hash_ops;  /* hash and compare ops to use */

        union _packed_ {
                struct indirect_storage indirect; /* if  has_indirect */
                struct direct_storage direct;     /* if !has_indirect */
        };

        enum HashmapType type:2;     /* HASHMAP_TYPE_* */
        bool has_indirect:1;         /* whether indirect storage is used */
        unsigned n_direct_entries:3; /* Number of entries in direct storage.
                                      * Only valid if !has_indirect. */
        bool from_pool:1;            /* whether was allocated from mempool */
        bool dirty:1;                /* whether dirtied since last iterated_cache_get() */
        bool cached:1;               /* whether this hashmap is being cached */
        ...
};

struct Hashmap {
        struct HashmapBase b;
};

struct OrderedHashmap {
        struct HashmapBase b;
        unsigned iterate_list_head, iterate_list_tail;
};

struct Set {
        struct HashmapBase b;
};
```

三つの型はどれも先頭に `HashmapBase` を置く。
共通のアルゴリズムを一組の関数で書き、型ごとの差分はエントリのサイズと `OrderedHashmap` の連結リスト用フィールドだけに閉じ込めている。
`OrderedHashmap` が挿入順を保てるのは、`iterate_list_head` と `iterate_list_tail` が各エントリを挿入順に連結するからである。

### 直接格納と間接格納

`HashmapBase` の記憶領域は共用体で、二つの表現を切り替える。

[`src/basic/hashmap.c` L155-L177](https://github.com/systemd/systemd/blob/v261.1/src/basic/hashmap.c#L155-L177)

```c
struct _packed_ indirect_storage {
        void *storage;                     /* where buckets and DIBs are stored */
        uint8_t  hash_key[HASH_KEY_SIZE];  /* hash key; changes during resize */

        unsigned n_entries;                /* number of stored entries */
        unsigned n_buckets;                /* number of buckets */

        unsigned idx_lowest_entry;         /* Index below which all buckets are free. ... */
        uint8_t  _pad[3];                  /* padding for the whole HashmapBase */
};

struct direct_storage {
        /* This gives us 39 bytes on 64-bit, or 35 bytes on 32-bit.
         * That's room for 4 set_entries + 4 DIB bytes + 3 unused bytes on 64-bit, ... */
        uint8_t storage[sizeof(struct indirect_storage)];
};
```

エントリ数が少ないうちは、別領域を確保せず `HashmapBase` の中の `direct_storage` にエントリを直接埋め込む。
64 ビット環境では 4 個までのエントリをこの内部領域に収められる。
容量を超えると `indirect_storage` に切り替わり、`storage` が指す別ヒープにバケット配列を構える。
小さなマップが大量に生成される systemd では、ほとんどのマップが数個のエントリしか持たないため、この直接格納が追加の `malloc` を丸ごと省く。

### Robin Hood ハッシュ

間接格納のバケット配列は、オープンアドレス法に Robin Hood 方式を組み合わせて衝突を捌く。
各バケットには「本来のバケットからどれだけずれた位置にいるか」を表す DIB（Distance from Initial Bucket）を持たせる。

[`src/basic/hashmap.c` L123-L128](https://github.com/systemd/systemd/blob/v261.1/src/basic/hashmap.c#L123-L128)

```c
/* Distance from Initial Bucket */
typedef uint8_t dib_raw_t;
#define DIB_RAW_OVERFLOW ((dib_raw_t)0xfdU)   /* indicates DIB value is greater than representable */
#define DIB_RAW_REHASH   ((dib_raw_t)0xfeU)   /* entry yet to be rehashed during in-place resize */
#define DIB_RAW_FREE     ((dib_raw_t)0xffU)   /* a free bucket */
#define DIB_RAW_INIT     ((char)DIB_RAW_FREE) /* a byte to memset a DIB store with when initializing */
```

Robin Hood 方式は、挿入時に「自分より DIB の小さい（恵まれた）エントリ」を見つけると、その位置を奪って相手を後ろへ押しやる。
これによりバケットごとの探索距離のばらつきが小さくなり、最悪ケースの探索コストが抑えられる。
DIB を 1 バイトに収め、削除時は後方シフトで詰めるため、トゥームストーンを残さずに済む。

## メモリプール：小さな割り当ての集約

Hashmap 本体のような小さくて大量に作られるオブジェクトは、`malloc` を都度呼ぶとオーバーヘッドが積み上がる。
systemd は同じサイズの「タイル」をまとめて確保するメモリプールを用意する。

[`src/basic/mempool.c` L21-L63](https://github.com/systemd/systemd/blob/v261.1/src/basic/mempool.c#L21-L63)

```c
void* mempool_alloc_tile(struct mempool *mp) {
        size_t i;

        /* When a tile is released we add it to the list and simply
         * place the next pointer at its offset 0. */
        ...
        if (mp->freelist) {
                void *t;

                t = mp->freelist;
                mp->freelist = *(void**) mp->freelist;
                return t;
        }

        if (_unlikely_(!mp->first_pool) ||
            _unlikely_(mp->first_pool->n_used >= mp->first_pool->n_tiles)) {
                ...
                n = mp->first_pool ? mp->first_pool->n_tiles : 0;
                n = MAX(mp->at_least, n * 2);
                size = PAGE_ALIGN(ALIGN(sizeof(struct pool)) + n*mp->tile_size);
                ...
                mp->first_pool = p;
        }

        i = mp->first_pool->n_used++;

        return (uint8_t*) pool_ptr(mp->first_pool) + i*mp->tile_size;
}
```

割り当ての戦略は二段構えである。
解放済みのタイルがあれば、フリーリストの先頭をそのまま返す。
このとき解放済みタイルの先頭 8 バイトを次ポインタとして流用するので、フリーリストの管理に追加のメモリを一切使わない。
フリーリストが空でプールも満杯なら、新しいプールを一度の `malloc` で確保する。
確保するタイル数は前回の倍に増やすため、割り当て回数はエントリ数の対数でしか増えない。

`hashmap_base_new` はこのプールから Hashmap 本体を取る。

[`src/basic/hashmap.c` L794-L806](https://github.com/systemd/systemd/blob/v261.1/src/basic/hashmap.c#L794-L806)

```c
static struct HashmapBase* hashmap_base_new(const struct hash_ops *hash_ops, enum HashmapType type) {
        HashmapBase *h;
        const struct hashmap_type_info *hi = &hashmap_type_info[type];

        bool use_pool = mempool_enabled && mempool_enabled();  /* mempool_enabled is a weak symbol */

        h = use_pool ? mempool_alloc0_tile(hi->mempool) : malloc0(hi->head_size);
        if (!h)
                return NULL;

        h->type = type;
        h->from_pool = use_pool;
        h->hash_ops = hash_ops ?: &trivial_hash_ops;
```

プールを使うかどうかは弱シンボル `mempool_enabled` で切り替わる。
これはメモリリーク検査（valgrind など）を走らせるときにプールを無効化し、割り当て単位を個別の `malloc` に落として検査しやすくするためである。

## 動的配列：greedy_realloc

可変長配列を一要素ずつ伸ばすと、そのたびに `realloc` が走る。
systemd は必要量の倍を確保して再割り当ての回数を減らす `greedy_realloc` を用意する。

[`src/basic/alloc-util.c` L77-L110](https://github.com/systemd/systemd/blob/v261.1/src/basic/alloc-util.c#L77-L110)

```c
void* greedy_realloc(
                void **p,
                size_t need,
                size_t size) {

        size_t newalloc;
        void *q;
        ...
        if (*p && (size == 0 || (MALLOC_SIZEOF_SAFE(*p) / size >= need)))
                return *p;
        ...
        newalloc = need * 2;

        if (!MUL_ASSIGN_SAFE(&newalloc, size))
                return NULL;

        if (newalloc < 64) /* Allocate at least 64 bytes */
                newalloc = 64;

        q = realloc(*p, newalloc);
        if (!q)
                return NULL;

        return *p = q;
}
```

現在の割り当てサイズは `malloc_usable_size` で調べ、必要量が収まっていれば再割り当てせず既存の領域を返す。
伸ばすときは必要量の倍を、最低でも 64 バイト確保する。
`GREEDY_REALLOC` マクロがこの関数を包み、配列変数と要素数を渡すだけで型に応じた要素サイズを補う。
文字列ベクタ（`strv`）やイベントソース配列など、systemd 内の伸長する配列はこの仕組みに乗る。

## 最適化の工夫：割り当て回数の対数化

本章で見た三つの部品は、いずれも「割り当て回数を減らす」という同じ狙いを別の場面に適用している。
Hashmap は小さいうちは内部領域に直接埋め込み、`malloc` そのものを起こさない。
メモリプールはタイルをまとめ買いし、確保量を倍々に増やすので、n 個のタイルを配るのに必要な `malloc` は O(log n) 回で済む。
`greedy_realloc` も必要量の倍を取り、配列を n 要素まで伸ばす間の `realloc` を O(log n) 回に抑える。
systemd が数千のユニットとイベントソースを扱っても割り当てコストが線形に膨らまないのは、この対数化が層の底で効いているからである。

## まとめ

`fundamental` 層は libc にも文字型にも依存しない最小コードで、UEFI スタブとユーザー空間の両方に同じロジックを供給する。
`basic` の Hashmap は共通の基底の上に三つの型を積み、少数エントリは内部領域に直接格納し、多数になると Robin Hood 方式のオープンアドレス表へ移る。
メモリプールは同サイズのタイルをまとめ買いしてフリーリストで回し、`greedy_realloc` は倍々確保で動的配列の再割り当てを抑える。
どの部品も割り当て回数を対数に抑えることで、大量の小オブジェクトを扱う systemd の土台を支えている。

## 関連する章

- 第1章（systemd の全体像とプロセスツリー）
- 第4章（sd-event イベントループ）
- 第5章（sd-bus と D-Bus 連携）
