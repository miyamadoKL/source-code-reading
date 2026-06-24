# 第19章 ソート済みセットと skiplist

> **本章で読むソース**
>
> - [`src/server.h`](https://github.com/valkey-io/valkey/blob/9.1.0/src/server.h)
> - [`src/t_zset.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c)
> - [`src/config.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/config.c)

## この章の狙い

ソート済みセットは、メンバごとにスコアを持ち、スコア順に整列された集合である。
本章では、この型がスコア順の範囲探索とランク取得を `O(log n)` で行うために用いる **skiplist** の構造を実コードから読む。
さらに、skiplist と `dict`（hashtable）を併用する二重構造が、`ZSCORE` のような単一メンバ参照と範囲操作の双方を速くする仕組みを説明する。

## 前提

- [第8章 listpack](../part01-data-structures/08-listpack.md)：小さなソート済みセットを格納する省メモリ表現。
- [第7章 hashtable](../part01-data-structures/07-hashtable.md)：skiplist と組む `dict` の実装。

## 二つのエンコーディング

ソート済みセットには二つの内部表現がある。
要素数が少なくメンバ文字列も短いあいだは **listpack** に格納し、いずれかが閾値を超えると **skiplist** に切り替える。
切り替えの閾値は二つの設定値で決まる。

[`src/config.c` L3469-L3473](https://github.com/valkey-io/valkey/blob/9.1.0/src/config.c#L3469-L3473)

```c
createSizeTConfig("zset-max-listpack-entries", "zset-max-ziplist-entries", MODIFIABLE_CONFIG, 0, LONG_MAX, server.zset_max_listpack_entries, 128, INTEGER_CONFIG, NULL, NULL),
// ... (中略) ...
createSizeTConfig("zset-max-listpack-value", "zset-max-ziplist-value", MODIFIABLE_CONFIG, 0, LONG_MAX, server.zset_max_listpack_value, 64, MEMORY_CONFIG, NULL, NULL),
```

`zset-max-listpack-entries` は要素数の上限で、初期値は 128 である。
`zset-max-listpack-value` はメンバ文字列の長さの上限で、初期値は 64 バイトである。
要素数がこの上限を超えるか、長いメンバを追加しようとすると、listpack から skiplist へ変換される。

listpack 版は、メンバとスコアを交互に並べた一本の連続バイト列である。
要素が少ないうちはこの形が省メモリで、走査も実用上速い。
listpack そのものの構造は第8章で扱った。
本章はソート済みセットが大きくなったときに使う skiplist に集中する。

## skiplist のノード構造

skiplist のノードは `zskiplistNode` 型である。

[`src/server.h` L1493-L1527](https://github.com/valkey-io/valkey/blob/9.1.0/src/server.h#L1493-L1527)

```c
typedef struct zskiplistNode {
    union {
        double score;         /* Sorting score for node ordering. */
        unsigned long length; /* Number of elements in the skiplist. */
    };
    union {
        struct zskiplistNode *backward; /* Pointer to previous node for reverse traversal. */
        struct zskiplistNode *tail;     /* Tail element of the skiplist. */
    };
    struct zskiplistLevel {
        struct zskiplistNode *forward;
        unsigned long span;
    } level[1]; /* Flexible array member - actual levels determined at node creation. */
    /* For non-header nodes, after the level[], sds header length (1 byte) and an embedded sds element are stored. */
} zskiplistNode;

typedef struct zskiplist {
    zskiplistNode header;
} zskiplist;

typedef struct zset {
    hashtable *ht;
    zskiplist *zsl;
} zset;
```

各ノードは `score`、後方への一本のポインタ `backward`、そして `level` 配列を持つ。
`level` 配列の各要素は二つの値を持つ。
一つは同じ段で次のノードを指す `forward` ポインタである。
もう一つは `span` で、この段でこのノードから次のノードまでに何個の要素を飛び越えるかを表す。

`level[1]` は柔軟配列メンバで、実際の段数はノード生成時に決まる。
段数が高いノードほど多くの段の `forward` を持ち、遠くまで一気に飛べる。
メンバ文字列の sds は、`level` 配列の直後に同じ確保ブロック内へ埋め込まれる。
ノードと sds を一度の `zmalloc` でまとめて確保するため、参照局所性が良く、確保回数も減る。

`zskiplist` は先頭ノード `header` を一つ持つだけの構造体である。
`header` は実データを持たないダミーで、`union` を使って役割を切り替えている。
通常ノードでは `score` だが、`header` では `length`（要素数）として使う。
同様に `backward` の位置を、`header` では `tail`（末尾ノードへのポインタ）として使う。
データを持たない `header` の領域を、リスト全体のメタ情報の置き場として再利用することで、別途メタデータ用の構造体を持たずに済ませている。

## span をランク計算に使う

`span` は、ランク（先頭から何番目か）を `O(log n)` で求めるための仕掛けである。
ある段で `forward` をたどってノードを飛び越えるたびに、その段の `span` を足していけば、飛び越えた要素数の合計が分かる。

ただし `level[0]`（最下段）の `span` だけは特別な使い方をする。
最下段では隣のノードまでの距離は常に 1 なので、`span` を本来の意味では使わず、そのノードの段数（高さ）を格納する領域として流用する。
この約束はアクセサ関数に閉じ込められている。

[`src/t_zset.c` L79-L115](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L79-L115)

```c
static inline unsigned long zslGetNodeSpanAtLevel(const zskiplistNode *x, int level) {
    /* We use the level 0 span in order to hold the node height, so in case the span is requested on
     * level 0 and this is not the last node we return 1 and 0 otherwise. For the rest of the levels we just return
     * the recorded span in that level. */
    if (level > 0) return x->level[level].span;
    return x->level[level].forward ? 1 : 0;
}

// ... (中略) ...

static inline unsigned long zslGetNodeHeight(const zskiplistNode *x) {
    /* Since the span at level 0 is always 1 (or 0 for the last node), this
     * field is instead used for storing the height of the node. */
    return x->level[0].span;
}
```

`zslGetNodeSpanAtLevel` は、最下段では `forward` の有無から 1 か 0 を返し、それ以外の段では記録された `span` をそのまま返す。
`zslGetNodeHeight` は、最下段の `span` 領域を読んでノードの高さを得る。
最下段の `span` が常に 1 か 0 に固定できるという性質を使い、本来空く 1 ワードにノード高さを同居させている。

## 確率的な高さ

skiplist の検索が `O(log n)` になるのは、ノードの高さが確率的に決まるからである。
高いノードほど少なく、低いノードほど多く現れるように高さを割り当てると、上の段は要素をまばらに、下の段は密につなぐ多段リンクになる。
新しいノードの高さは `zslRandomLevel` が決める。

[`src/t_zset.c` L223-L232](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L223-L232)

```c
static int zslRandomLevel(void) {
    uint64_t rand = genrand64_int64();

    /* The probability of gaining 2 additional leading zeros is 0.25.
     * This matches the level calculation logic perfectly: each
     * iteration has a 0.25 probability of increasing the level by 1.
     * Note: __builtin_clzll has undefined behavior when the input is 0. */
    int level = rand == 0 ? ZSKIPLIST_MAXLEVEL : (__builtin_clzll(rand) / 2 + 1);
    return level;
}
```

`genrand64_int64` で 64 ビットの乱数を引き、その先頭から続くゼロビットの数を `__builtin_clzll` で数える。
ゼロビットが 2 個増えるごとに高さが 1 上がる対応になっており、高さが 1 上がる確率は `0.25` である。
ループで毎回 `0.25` の確率を引くのと同じ分布を、ビット演算一回で得ている。
高さの上限は `ZSKIPLIST_MAXLEVEL`（`server.h` で 32）で、`2^64` 個の要素に十分な段数である。

## 挿入と span の更新

挿入は `zslInsert` から始まる。
ランダムな高さを決め、その高さのノードを生成し、`zslInsertNode` に渡す。

[`src/t_zset.c` L305-L312](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L305-L312)

```c
zskiplistNode *zslInsert(zskiplist *zsl, double score, const_sds ele) {
    const int level = zslRandomLevel();
    zskiplistNode *node = zslCreateNode(level, score, ele);
    zslInsertNode(zsl, node);
    return node;
}
```

`zslInsertNode` は、挿入位置を上の段から順に下りながら探し、各段で「どのノードの後ろに入るか」を `update` 配列に、「先頭からそこまでに飛び越えた要素数」を `rank` 配列に記録する。

[`src/t_zset.c` L254-L303](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L254-L303)

```c
static zskiplistNode *zslInsertNode(zskiplist *zsl, zskiplistNode *node) {
    zskiplistNode *update[ZSKIPLIST_MAXLEVEL];
    unsigned long rank[ZSKIPLIST_MAXLEVEL];
    const int level = zslGetNodeHeight(node);

    serverAssert(!isnan(node->score));
    zskiplistNode *x = zslGetHeader(zsl);
    for (int i = zslGetHeight(zsl) - 1; i >= 0; i--) {
        /* store rank that is crossed to reach the insert position */
        rank[i] = i == (zslGetHeight(zsl) - 1) ? 0 : rank[i + 1];
        while (zslCompareNodes(x->level[i].forward, node) < 0) {
            rank[i] += zslGetNodeSpanAtLevel(x, i);
            x = x->level[i].forward;
        }
        update[i] = x;
    }
    // ... (中略) ...
    for (int i = 0; i < level; i++) {
        node->level[i].forward = update[i]->level[i].forward;
        update[i]->level[i].forward = node;

        /* update span covered by update[i] as x is inserted here */
        zslSetNodeSpanAtLevel(node, i, zslGetNodeSpanAtLevel(update[i], i) - (rank[0] - rank[i]));
        zslSetNodeSpanAtLevel(update[i], i, (rank[0] - rank[i]) + 1);
    }

    /* increment span for untouched levels */
    for (int i = level; i < zslGetHeight(zsl); i++) {
        zslIncrNodeSpanAtLevel(update[i], i, 1);
    }
    // ... (中略) ...
}
```

最上段から始め、各段で次のノードが挿入対象より前にあるあいだは前進する。
`zslCompareNodes` はスコアを第一キー、メンバ文字列を第二キーとして比較するので、同じスコアの要素はメンバの辞書順で並ぶ。
前進のたびに `zslGetNodeSpanAtLevel` で飛び越えた要素数を `rank[i]` に足し込む。
段を下りるときは一つ上の段の `rank` を引き継ぐ。

挿入位置が決まったら、ノードの高さ分の段でポインタをつなぎ替える。
このとき `rank[0] - rank[i]` が「段 `i` の挿入点から最下段の挿入点までの距離」になるので、新ノードと直前ノードの `span` をこの距離から正確に計算できる。
新ノードより高い段（ノードが届かない段）では、要素が一つ増えたぶん `span` を 1 増やすだけでよい。
このように `span` を挿入時に更新し続けるため、ランク取得は探索のついでに合計を読むだけで済む。

## ランク取得

`zslGetElementByRankFromNode` は、ランクから要素を引く。
上の段から、飛び越えた合計が目標ランクを超えない範囲で前進し、超えそうになったら段を下りる。

[`src/t_zset.c` L597-L619](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L597-L619)

```c
static zskiplistNode *zslGetElementByRankFromNode(zskiplistNode *start_node, int start_level, unsigned long rank) {
    zskiplistNode *x;
    unsigned long traversed = 0;
    int i;

    x = start_node;
    for (i = start_level; i >= 0; i--) {
        while (x->level[i].forward && (traversed + zslGetNodeSpanAtLevel(x, i)) <= rank) {
            traversed += zslGetNodeSpanAtLevel(x, i);
            x = x->level[i].forward;
        }
        if (traversed == rank) {
            return x;
        }
    }
    return NULL;
}
```

`traversed` に `span` を足し込みながら、合計が `rank` 以下のあいだ前進する。
上の段ほど一歩で大きく飛べるので、目標まで段階的に近づける。
合計が `rank` に一致したノードが答えで、対数段数で到達できる。

逆に、ノードからランクを求める `zslGetRank` は、そのノードから最高段の `forward` をたどって末尾までに残る要素数を数え、全長から引く。

[`src/t_zset.c` L585-L595](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L585-L595)

```c
static unsigned long zslGetRank(zskiplist *zsl, const zskiplistNode *node) {
    unsigned long count_after_node = 0;
    while (node) { /* note this is never null the first time */
        int highest_node_span = zslGetNodeHeight(node) - 1;
        count_after_node += zslGetNodeSpanAtLevel(node, highest_node_span);
        node = node->level[highest_node_span].forward;
    }

    unsigned long rank = zslGetLength(zsl) - count_after_node;
    return rank;
}
```

## skiplist と dict の二重構造

`zset` 構造体は `hashtable *ht` と `zskiplist *zsl` の二つを併せ持つ。
これが最適化の核となる二点目である。
skiplist は順序づけと範囲探索を担い、dict はメンバからスコアおよびノードへの `O(1)` 参照を担う。
同じメンバの sds 文字列を両者で別々に持たず、dict はノードへのポインタだけを持つ。

```text
            zset
        +-----------+
        |  ht  ----------> hashtable: member -> zskiplistNode*  (O(1) 参照)
        |  zsl ----------> zskiplist: スコア順の多段リンク       (O(log n) 範囲/ランク)
        +-----------+

  zskiplist（スコア昇順、L2/L1/L0 は段。数字は span）
    header ==4==============================> [E] ----------> NULL   (L2)
    header ==2==========> [C] ==2===========> [E] ==1==> [F]         (L1)
    header --1--> [A] --> [B] --> [C] --> [D] --> [E] --> [F]        (L0)
                 a:1.0   b:1.0   c:2.0   d:5.0   e:8.0   f:9.0

  hashtable（メンバ → ノード）
    "a" -> [A]   "c" -> [C]   "e" -> [E]   ...   ノードを共有して指すだけ
```

`ZSCORE` はメンバ一個のスコアを返すコマンドで、二重構造の片方だけを使う典型である。

[`src/t_zset.c` L1401-L1416](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L1401-L1416)

```c
int zsetScore(robj *zobj, sds member, double *score) {
    if (!zobj || !member) return C_ERR;

    if (zobj->encoding == OBJ_ENCODING_LISTPACK) {
        if (zzlFind(objectGetVal(zobj), member, score) == NULL) return C_ERR;
    } else if (zobj->encoding == OBJ_ENCODING_SKIPLIST) {
        zset *zs = objectGetVal(zobj);
        void *entry;
        if (!hashtableFind(zs->ht, member, &entry)) return C_ERR;
        zskiplistNode *setElement = entry;
        *score = setElement->score;
    } else {
        serverPanic("Unknown sorted set encoding");
    }
    return C_OK;
}
```

skiplist 版では `hashtableFind` でメンバからノードを `O(1)` で引き、そのノードの `score` を返す。
skiplist だけだと、メンバ一個のスコアを引くにもスコア順の探索が必要になり効率が悪い。
dict を併せ持つことで、`ZSCORE` のような点アクセスを `O(1)`、`ZRANGEBYSCORE` のような範囲アクセスを `O(log n)` と、両方を速く保てる。

## ZADD のエンコーディング分岐

`ZADD` は最終的に `zsetAdd` を呼ぶ。
この関数はエンコーディングごとに処理を分け、skiplist 版では二つの構造を同時に更新する。

[`src/t_zset.c` L1534-L1583](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L1534-L1583)

```c
    if (zobj->encoding == OBJ_ENCODING_SKIPLIST) {
        zset *zs = objectGetVal(zobj);

        void **node_ref_in_hashtable = hashtableFindRef(zs->ht, ele);
        if (node_ref_in_hashtable != NULL) {
            // ... (中略：NX/XX/GT/LT/INCR の判定) ...
            /* Remove and re-insert when score changes. */
            if (score != curscore) {
                zskiplistNode *new_node = zslUpdateScore(zs->zsl, old_node, score);
                /* Note that this assignment updates the node pointer stored in
                 * the hashtable */
                if (new_node) *node_ref_in_hashtable = new_node;
                *out_flags |= ZADD_OUT_UPDATED;
            }
            return 1;
        } else if (!xx) {
            zskiplistNode *new_node = zslInsert(zs->zsl, score, ele);
            serverAssert(hashtableAdd(zs->ht, new_node));
            *out_flags |= ZADD_OUT_ADDED;
            if (newscore) *newscore = score;
            return 1;
        } else {
            *out_flags |= ZADD_OUT_NOP;
            return 1;
        }
    } else {
        serverPanic("Unknown sorted set encoding");
    }
```

既存メンバかどうかは、まず `hashtableFindRef` で dict を引いて `O(1)` で判定する。
新規メンバなら `zslInsert` で skiplist にノードを作り、そのノードを `hashtableAdd` で dict にも登録する。
スコア更新時は `zslUpdateScore` で skiplist 内の位置を取り直し、dict が持つノードポインタを書き換える。
dict に登録するのはノードへのポインタなので、メンバ文字列の実体は skiplist ノード側に一つだけ存在する。

listpack 版では、追加によって要素数が `zset_max_listpack_entries` を超えるか、メンバ長が `zset_max_listpack_value` を超えると、その場で skiplist へ変換してから処理を続ける。

[`src/t_zset.c` L1514-L1525](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L1514-L1525)

```c
        } else if (!xx) {
            /* check if the element is too large or the list
             * becomes too long *before* executing zzlInsert. */
            if (zzlLength(objectGetVal(zobj)) + 1 > server.zset_max_listpack_entries ||
                sdslen(ele) > server.zset_max_listpack_value || !lpSafeToAdd(objectGetVal(zobj), sdslen(ele))) {
                zsetConvertAndExpand(zobj, OBJ_ENCODING_SKIPLIST, zsetLength(zobj) + 1);
            } else {
                objectSetVal(zobj, zzlInsert(objectGetVal(zobj), ele, score));
                if (newscore) *newscore = score;
                *out_flags |= ZADD_OUT_ADDED;
                return 1;
            }
        } else {
```

## ZRANK のランク取得

`ZRANK` は `zsetRank` を呼ぶ。
skiplist 版では、二重構造をそのまま順に使う。

[`src/t_zset.c` L1669-L1684](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L1669-L1684)

```c
    } else if (zobj->encoding == OBJ_ENCODING_SKIPLIST) {
        zset *zs = objectGetVal(zobj);

        void *entry;
        if (!hashtableFind(zs->ht, ele, &entry)) return -1;
        zskiplistNode *node = entry;

        rank = zslGetRank(zs->zsl, node);
        /* Existing elements always have a rank. */
        serverAssert(rank != 0);
        if (output_score) *output_score = node->score;
        if (reverse)
            return llen - rank;
        else
            return rank - 1;
    } else {
```

まず `hashtableFind` でメンバからノードを `O(1)` で引き当て、その存在を確かめる。
listpack 版なら先頭から線形に走査してランクを数えるしかないが、skiplist 版ではノードが直接手に入る。
得たノードを `zslGetRank` に渡せば、`span` の合計から `O(log n)` でランクが求まる。
点アクセス（dict）と順序情報（skiplist の `span`）を組み合わせて、メンバ指定のランク取得を速くしている。

## ZRANGEBYSCORE の範囲探索

`ZRANGEBYSCORE` はスコア範囲に入る要素を返す。
skiplist 版では `zslNthInRange` が範囲の入口ノードを `O(log n)` で見つける。

[`src/t_zset.c` L3265-L3295](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_zset.c#L3265-L3295)

```c
    } else if (zobj->encoding == OBJ_ENCODING_SKIPLIST) {
        zset *zs = objectGetVal(zobj);
        zskiplist *zsl = zs->zsl;
        zskiplistNode *ln;

        /* If reversed, get the last node in range as starting point. */
        if (reverse) {
            ln = zslNthInRange(zsl, range, -offset - 1, NULL);
        } else {
            ln = zslNthInRange(zsl, range, offset, NULL);
        }

        while (ln && limit--) {
            /* Abort when the node is no longer in range. */
            if (reverse) {
                if (!zslValueGteMin(ln->score, range)) break;
            } else {
                if (!zslValueLteMax(ln->score, range)) break;
            }

            rangelen++;
            sds ele = zslGetNodeElement(ln);
            handler->emitResultFromCBuffer(handler, ele, sdslen(ele), ln->score);

            /* Move to next node */
            if (reverse) {
                ln = ln->backward;
            } else {
                ln = ln->level[0].forward;
            }
        }
    } else {
```

`zslNthInRange` は、最上段から「範囲の下限より小さいあいだ」前進して入口に寄せ、段を下りながら位置を絞り込む。
入口が決まったら、あとは最下段の `forward`（逆順なら `backward`）を一歩ずつたどり、上限を超えたら止める。
範囲の入口探しが `O(log n)`、要素の取り出しが結果件数に比例するので、全件走査せずに範囲だけを返せる。

## まとめ

- ソート済みセットは要素が少ないあいだ listpack で省メモリに保持し、`zset-max-listpack-entries`（既定 128）か `zset-max-listpack-value`（既定 64）を超えると skiplist へ変換する。
- skiplist のノードは確率的な高さを持つ多段リンクで、`zslRandomLevel` が高さ 1 上昇あたり確率 `0.25` の分布を `__builtin_clzll` 一回で生成する。
- 各段の `span` は飛び越える要素数で、挿入時に更新し続けるため、ランク取得と範囲探索を `O(log n)` で行える。最下段の `span` はノード高さの格納に流用される。
- `zset` は skiplist と dict を併せ持ち、メンバ文字列の実体は skiplist ノードに一つだけ置き、dict はノードへのポインタを持つ。
- この二重構造により、`ZSCORE` などの点アクセスを dict で `O(1)`、`ZRANGEBYSCORE` などの範囲アクセスを skiplist で `O(log n)` と、両方を速く保てる。`ZRANK` は dict でノードを引き当ててから `span` でランクを求める。

## 関連する章

- [第8章 listpack](../part01-data-structures/08-listpack.md)：小さなソート済みセットの省メモリ表現。
- [第7章 hashtable](../part01-data-structures/07-hashtable.md)：skiplist と組む dict の内部実装。
