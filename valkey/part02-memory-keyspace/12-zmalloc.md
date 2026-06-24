# 第12章 zmalloc とメモリ管理

> **本章で読むソース**
>
> - [`src/zmalloc.h`](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.h)
> - [`src/zmalloc.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c)

## この章の狙い

Valkey は `malloc` を直接呼ばず、`zmalloc` という薄い包み層を通してメモリを確保する。
本章を読むと、`zmalloc` がなぜ確保したメモリの総量を常に把握できるのか、そのためのカウンタをどうやって低コストで更新しているのか、確保サイズの記録を環境によって省ける仕組みは何か、確保に失敗したときに何が起きるのかを、実コードのレベルで説明できるようになる。

## 前提

特になし。
SDS（第4章）や dict（第6章）など、本書のデータ構造はすべて `zmalloc` の上に載っているため、それらの章と合わせて読むと理解が深まる。

## zmalloc の役割

`zmalloc` は `malloc` と `free` を包む薄い層である。
役割は二つある。
一つは、確保したメモリの総量を `used_memory` というカウンタで追跡することである。
もう一つは、確保失敗時の振る舞いを一箇所に集約することである。

総量の追跡には実用上の目的がある。
サーバは自分がいま何バイト使っているかをいつでも答えられなければならない。
この値は `maxmemory` の設定と突き合わせてメモリ退避を起こすかどうかの判断材料になる（メモリ退避の仕組みは第32章で扱う）。
素の `malloc` は確保した総量を呼び出し側に教えてくれないので、Valkey は確保と解放のたびに自前のカウンタを増減させて総量を保持する。

確保関数の名前は、リンク時の衝突を避けるために内部では別名へ展開される。
`zmalloc` という呼び名はそのまま使いつつ、実体のシンボル名は `valkey_malloc` になる。

[`src/zmalloc.h` L107-L111](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.h#L107-L111)

```c
#define zmalloc valkey_malloc
#define zcalloc valkey_calloc
#define zrealloc valkey_realloc
#define zfree valkey_free
#define zmalloc_cache_aligned valkey_malloc_cache_aligned
```

裏で実際にメモリを確保するアロケータは、ビルド設定で切り替わる。
既定では Valkey に同梱された jemalloc が使われ、`USE_JEMALLOC` が定義されると `malloc` などの呼び出しが `je_malloc` へ差し替えられる。

[`src/zmalloc.c` L86-L92](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L86-L92)

```c
/* Explicitly override malloc/free etc when using jemalloc. */
#elif defined(USE_JEMALLOC)
#define malloc(size) je_malloc(size)
#define calloc(count, size) je_calloc(count, size)
#define realloc(ptr, size) je_realloc(ptr, size)
#define free(ptr) je_free(ptr)
#endif
```

jemalloc の実体は `deps/jemalloc/` に置かれている。
本章ではアロケータそのものの内部には立ち入らず、`zmalloc` がそれをどう包むかに絞って読む。

## 使用量の追跡

確保したメモリの総量は、`zmalloc` が独自に持つカウンタで管理する。
このカウンタはスレッドごとに分けて持たれる。
配列 `used_memory_thread` の各要素が、各スレッドが確保したバイト数を保持する。

[`src/zmalloc.c` L106-L116](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L106-L116)

```c
#if defined(__i386__) || defined(__x86_64__) || defined(__amd64__) || defined(__POWERPC__) || defined(__arm__) || \
    defined(__arm64__)
static __attribute__((aligned(CACHE_LINE_SIZE))) size_t used_memory_thread_padded[MAX_THREADS_NUM + PADDING_ELEMENT_NUM];
static size_t *used_memory_thread = &used_memory_thread_padded[PADDING_ELEMENT_NUM];
#else
static __attribute__((aligned(CACHE_LINE_SIZE))) _Atomic size_t used_memory_thread_padded[MAX_THREADS_NUM + PADDING_ELEMENT_NUM];
static _Atomic size_t *used_memory_thread = &used_memory_thread_padded[PADDING_ELEMENT_NUM];
#endif
```

配列をスレッド数で分ける理由は、確保のたびに走る加算を安く保つことにある。
全スレッドが一つの共有カウンタを更新すると、その変数を巡って書き込みが競合し、キャッシュ行の奪い合いが起きる。
そこで各スレッドは自分専用の要素だけを書き込む。
どの要素が自分のものかは、スレッドローカル変数 `thread_index` が指す。

更新の本体が `update_zmalloc_stat_alloc` と `update_zmalloc_stat_free` である。
確保時には確保サイズを加算し、解放時には同じだけ減算する。

[`src/zmalloc.c` L123-L139](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L123-L139)

```c
static inline void update_zmalloc_stat_alloc(size_t size) {
    if (unlikely(thread_index == -1)) zmalloc_register_thread_index();
    if (unlikely(thread_index >= MAX_THREADS_NUM)) {
        atomic_fetch_add_explicit(&used_memory_for_additional_threads, size, memory_order_relaxed);
    } else {
        used_memory_thread[thread_index] += size;
    }
}

static inline void update_zmalloc_stat_free(size_t size) {
    if (unlikely(thread_index == -1)) zmalloc_register_thread_index();
    if (unlikely(thread_index >= MAX_THREADS_NUM)) {
        atomic_fetch_sub_explicit(&used_memory_for_additional_threads, size, memory_order_relaxed);
    } else {
        used_memory_thread[thread_index] -= size;
    }
}
```

通常のスレッドは `used_memory_thread[thread_index] += size` のように、自分専用の要素を素の加算で更新する。
要素はスレッドごとに分かれているので、この加算に他スレッドとの同期はいらない。
カウンタ全体を一つのロックや atomic で守る設計に比べ、確保のたびのコストが小さく済む。

ただし、自分専用の要素を持てるスレッドの数には上限がある。
`thread_index` が `MAX_THREADS_NUM` を超えたスレッド、すなわちモジュールなどが大量にスレッドを作った場合の追加スレッドは、専用要素を割り当てられない。
そうしたスレッドは共有カウンタ `used_memory_for_additional_threads` を atomic 演算で更新する。
この経路は分岐予測で外れる側に置かれており、`unlikely` で例外扱いと示されている。

総量の読み出しは `zmalloc_used_memory` が担う。
各スレッドの要素を全部足し合わせ、上限を超えたスレッドぶんの共有カウンタも加える。

[`src/zmalloc.c` L519-L530](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L519-L530)

```c
size_t zmalloc_used_memory(void) {
    size_t um = 0;
    int threads_num = total_active_threads;
    if (unlikely(total_active_threads > MAX_THREADS_NUM)) {
        um += atomic_load_explicit(&used_memory_for_additional_threads, memory_order_relaxed);
        threads_num = MAX_THREADS_NUM;
    }
    for (int i = 0; i < threads_num; i++) {
        um += used_memory_thread[i];
    }
    return um;
}
```

読み出しの側に集計の手間を寄せ、確保と解放という頻繁な側を軽くする配分になっている。
更新は確保や解放のたびに走るが、総量の問い合わせは退避判定や `INFO` の応答のときに限られるので、この配分が効く。

## サイズの取得と PREFIX_SIZE

カウンタを正しく増減させるには、確保時と解放時で同じサイズを足し引きしなければならない。
ここで問題になるのは、解放時に渡される情報がポインタだけだという点である。
利用者が `zfree(ptr)` を呼ぶとき、そのブロックが何バイトだったかは引数に含まれない。
減算すべきサイズを知る方法が要る。

方法は環境によって二通りに分かれる。
分岐の鍵は `HAVE_MALLOC_SIZE` というマクロである。
アロケータがポインタから確保サイズを問い合わせる関数を提供していれば、このマクロが定義される。
jemalloc を使うビルドでは `je_malloc_usable_size` がその役を果たし、`zmalloc_size(p)` として使えるようになる。

[`src/zmalloc.h` L50-L59](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.h#L50-L59)

```c
#elif defined(USE_JEMALLOC)
#define ZMALLOC_LIB \
    ("jemalloc-" __xstr(JEMALLOC_VERSION_MAJOR) "." __xstr(JEMALLOC_VERSION_MINOR) "." __xstr(JEMALLOC_VERSION_BUGFIX))
#include <jemalloc/jemalloc.h>
#if (JEMALLOC_VERSION_MAJOR == 2 && JEMALLOC_VERSION_MINOR >= 1) || (JEMALLOC_VERSION_MAJOR > 2)
#define HAVE_MALLOC_SIZE 1
#define zmalloc_size(p) je_malloc_usable_size(p)
#else
#error "Newer version of jemalloc required"
#endif
```

`HAVE_MALLOC_SIZE` が立っているかどうかで、ブロックの先頭に確保するヘッダの大きさ `PREFIX_SIZE` が変わる。
サイズを問い合わせられるなら、サイズを自前で記録する必要がないので `PREFIX_SIZE` は 0 になる。
問い合わせられないなら、サイズを書き込む領域として `size_t` ぶん（多くの環境で8バイト）を前置きする。

[`src/zmalloc.c` L59-L68](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L59-L68)

```c
#ifdef HAVE_MALLOC_SIZE
#define PREFIX_SIZE (0)
#else
/* Use at least 8 bytes alignment on all systems. */
#if SIZE_MAX < 0xffffffffffffffffull
#define PREFIX_SIZE 8
#else
#define PREFIX_SIZE (sizeof(size_t))
#endif
#endif
```

この分岐が `zmalloc` の省メモリ最適化の核心である。
確保したブロック一つにつき、サイズを書く8バイトを省ける。
小さなオブジェクトを大量に持つサーバでは、この8バイトがブロックの数だけ積み上がる。
jemalloc がサイズを答えてくれる以上、同じ情報を自前で持つのは二重管理になるので、それを省く。

二つの版の違いは確保処理の内側に現れる。
確保の実体は `ztrymalloc_usable_internal` にある。

[`src/zmalloc.c` L169-L187](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L169-L187)

```c
static inline void *ztrymalloc_usable_internal(size_t size, size_t *usable) {
    /* Possible overflow, return NULL, so that the caller can panic or handle a failed allocation. */
    if (size >= SIZE_MAX / 2) return NULL;
    void *ptr = malloc(MALLOC_MIN_SIZE(size) + PREFIX_SIZE);

    if (!ptr) return NULL;
#ifdef HAVE_MALLOC_SIZE
    size = zmalloc_size(ptr);
    update_zmalloc_stat_alloc(size);
    if (usable) *usable = size;
    return ptr;
#else
    size = MALLOC_MIN_SIZE(size);
    *((size_t *)ptr) = size;
    update_zmalloc_stat_alloc(size + PREFIX_SIZE);
    if (usable) *usable = size;
    return (char *)ptr + PREFIX_SIZE;
#endif
}
```

`HAVE_MALLOC_SIZE` の版では、`malloc` が返したポインタをそのまま利用者へ返す。
`PREFIX_SIZE` は 0 なので前置き領域はない。
カウンタには、要求したサイズではなくアロケータが実際に確保した `zmalloc_size(ptr)` の値を足す。
jemalloc はサイズクラスに切り上げて確保するため、実際の確保量は要求量より大きいことがある。
実量で数えることで、カウンタが本当の使用量に一致する。

フォールバック版では話が変わる。
`malloc(MALLOC_MIN_SIZE(size) + PREFIX_SIZE)` で前置き領域を含めて確保し、先頭の `size_t` にデータ部のサイズを書き込む。
そのうえで、利用者へは前置き領域の直後を指すポインタ `(char *)ptr + PREFIX_SIZE` を返す。
利用者は前置き領域の存在を意識しない。

解放時はこの配置を逆にたどる。
`zfree` は、サイズが問い合わせられる版ではポインタから直接サイズを得て、フォールバック版ではポインタを `PREFIX_SIZE` ぶん手前に戻して書き込んだサイズを読み出す。

[`src/zmalloc.c` L473-L492](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L473-L492)

```c
void zfree(void *ptr) {
    if (ptr == NULL) return;

#ifdef HAVE_MALLOC_SIZE
    size_t size = zmalloc_size(ptr);
#else
    unsigned char *prefix = (unsigned char *)ptr - PREFIX_SIZE;
    size_t data_size = *((size_t *)prefix);
    if (zmallocIsCacheAlignedAllocation(data_size)) {
        size_t size = zmallocCacheAlignedDataSize(data_size) + PREFIX_SIZE;
        void *raw = *((void **)(prefix - sizeof(void *)));
        zfree_internal(raw, size);
        return;
    }
    ptr = prefix;
    size_t size = data_size + PREFIX_SIZE;
#endif

    zfree_internal(ptr, size);
}
```

どちらの版でも、得たサイズを `update_zmalloc_stat_free` に渡してカウンタから引く（減算は `zfree_internal` の中で行う）。
確保時に足した量と解放時に引く量が一致するので、総量は正しく保たれる。

二つの版でブロックの先頭がどう違うかを図にすると、次のようになる。

```text
HAVE_MALLOC_SIZE 版 (jemalloc など。PREFIX_SIZE = 0)

  malloc が返す先頭
  ↓
  +---------------------------+
  | データ部                  |  ← 利用者が受け取るポインタは先頭そのもの
  +---------------------------+
  サイズは zmalloc_size(ptr) でアロケータに問い合わせる


フォールバック版 (PREFIX_SIZE = 8)

  malloc が返す先頭
  ↓
  +-------------+-------------------+
  | サイズ 8B   | データ部          |
  +-------------+-------------------+
                ↑
                利用者が受け取るポインタ (先頭 + PREFIX_SIZE)
  サイズは前置き領域から読み出す
```

なお、サイズを問い合わせる版でも利用者がサイズを知りたい場面はある。
ヘッダ `zmalloc.h` には、問い合わせる版のときに `zmalloc_usable_size(p)` を `zmalloc_size(p)` へ展開する定義と、確保サイズより大きい領域まで使うことをコンパイラに伝える `extend_to_usable` の宣言が置かれている。

[`src/zmalloc.h` L147-L167](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.h#L147-L167)

```c
#ifndef HAVE_MALLOC_SIZE
size_t zmalloc_size(void *ptr);
size_t zmalloc_usable_size(void *ptr);
#else
/* If we use 'zmalloc_usable_size()' to obtain additional available memory size
 * and manipulate it, we need to call 'extend_to_usable()' afterwards to ensure
 * the compiler recognizes this extra memory. However, if we use the pointer
 * obtained from z[*]_usable() family functions, there is no need for this step. */
#define zmalloc_usable_size(p) zmalloc_size(p)

/* derived from https://github.com/systemd/systemd/pull/25688
 * ... (中略) ... */
__attribute__((alloc_size(2), noinline)) void *extend_to_usable(void *ptr, size_t size);
#endif
```

## 確保失敗と OOM ハンドラ

確保に失敗したときの振る舞いも `zmalloc` が一箇所に集める。
失敗時に呼ばれる関数は、関数ポインタ `zmalloc_oom_handler` に保持される。
既定の中身は `zmalloc_default_oom` で、確保しようとしたバイト数を標準エラーへ出し、`abort` でプロセスを落とす。

[`src/zmalloc.c` L141-L147](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L141-L147)

```c
static void zmalloc_default_oom(size_t size) {
    fprintf(stderr, "zmalloc: Out of memory trying to allocate %zu bytes\n", size);
    fflush(stderr);
    abort();
}

static void (*zmalloc_oom_handler)(size_t) = zmalloc_default_oom;
```

ハンドラを関数ポインタにしてあるのは、サーバ側で差し替えられるようにするためである。
`zmalloc_set_oom_handler` がポインタを書き換える口を提供する。
サーバはこれを使い、確保失敗時にログを残してから落ちるなど、独自の終了処理に置き換える。

[`src/zmalloc.c` L532-L534](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L532-L534)

```c
void zmalloc_set_oom_handler(void (*oom_handler)(size_t)) {
    zmalloc_oom_handler = oom_handler;
}
```

確保関数は、失敗を許すかどうかで二系統に分かれる。
落としてよい確保には `zmalloc` を使う。
内部の確保が `NULL` を返したら、その場でハンドラを呼ぶ。
ハンドラは既定では戻らないので、`zmalloc` が `NULL` を返すことはない。

[`src/zmalloc.c` L199-L204](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L199-L204)

```c
/* Allocate memory or panic */
void *zmalloc(size_t size) {
    void *ptr = ztrymalloc_usable_internal(size, NULL);
    if (!ptr) zmalloc_oom_handler(size);
    return ptr;
}
```

失敗を呼び出し側で扱いたい確保には `ztrymalloc` を使う。
こちらはハンドラを呼ばず、失敗をそのまま `NULL` として返す。

[`src/zmalloc.c` L258-L262](https://github.com/valkey-io/valkey/blob/9.1.0/src/zmalloc.c#L258-L262)

```c
/* Try allocating memory, and return NULL if failed. */
void *ztrymalloc(size_t size) {
    void *ptr = ztrymalloc_usable_internal(size, NULL);
    return ptr;
}
```

二つの呼び分けには使い分けがある。
内部構造の確保のように、失敗したら処理を続けようがない場面では `zmalloc` を使い、その場で落とす。
利用者の要求に応じた大きな確保のように、失敗してもエラーを返して動き続けたい場面では `ztrymalloc` を使い、`NULL` を受けて呼び出し側が判断する。
どちらの系統も同じ内部関数 `ztrymalloc_usable_internal` を共有し、ハンドラを呼ぶかどうかだけが違う。

`zmalloc` の総量追跡と OOM ハンドラは、`maxmemory` を超えたときにキーを退避させる仕組みの土台になる。
退避の判定がいつ走り、どのキーを選ぶのかは第32章で扱う。

## まとめ

- `zmalloc` は `malloc` と `free` を包む薄い層であり、確保した総量の追跡と確保失敗時の振る舞いを一箇所に集約する。既定のアロケータは同梱の jemalloc である。
- 使用量はスレッドごとに分けたカウンタで持ち、通常スレッドは自分専用の要素を同期なしで増減させる。総量の問い合わせは読み出し側で全要素を集計し、頻繁な確保や解放の側を軽く保つ。
- カウンタには要求量ではなく実際の確保量を足し引きするので、総量は本当の使用量に一致する。
- `HAVE_MALLOC_SIZE`（jemalloc など）が使える環境では、サイズをアロケータに問い合わせ、`PREFIX_SIZE` を 0 にして前置き領域を省く。使えない環境ではサイズを `size_t` ぶん前置きする版にフォールバックする。
- 確保失敗時は関数ポインタ `zmalloc_oom_handler` が呼ばれる。`zmalloc` は失敗時にハンドラを呼んで落とし、`ztrymalloc` は `NULL` を返して呼び出し側に判断を委ねる。

## 関連する章

- [第4章 SDS 動的文字列](../part01-data-structures/04-sds.md)：`zmalloc` の上に載る代表的なデータ構造。
- [第13章 kvstore](./13-kvstore.md)：キー空間を支えるデータ構造。
- [第32章 メモリ退避](../part05-database/32-eviction.md)：`used_memory` と `maxmemory` を使った退避の判定。
