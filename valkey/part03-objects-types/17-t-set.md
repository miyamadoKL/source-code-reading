# 第17章 セット型

> **本章で読むソース**
>
> - [`src/t_set.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c)
> - [`src/object.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/object.c)（セットオブジェクトの生成）
> - [`src/config.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/config.c)（エンコーディング閾値の設定項目）

## この章の狙い

セット型は重複を許さない要素の集まりであり、Valkey はこれを要素の中身と数に応じて三つの内部表現で持つ。
本章では、整数だけの小さなセットを **intset**、整数以外を含む小さなセットを **listpack**、大きくなったセットを **hashtable** で表す仕組みと、要素を追加するたびにこの三段の表現を昇格させる変換ロジックを実コードで追う。
存在判定がエンコーディングごとに二分探索か O(1) かに分かれる点も読み解く。

## 前提

- 整数集合の表現は [第10章 intset](../part01-data-structures/10-intset.md)。
- 小さな集合に使うコンパクト表現は [第8章 listpack](../part01-data-structures/08-listpack.md)。
- 大きな集合の表現は [第7章 hashtable](../part01-data-structures/07-hashtable.md)。
- オブジェクトとエンコーディングの基礎は [第14章 オブジェクトとエンコーディング](14-object-encoding.md)。

## 三つのエンコーディング

セット型には三つの内部表現がある。
要素がすべて整数で表せて数が少なければ intset、整数以外の文字列を含むが数が少なければ listpack、数が増えれば hashtable を使う。
それぞれ `OBJ_ENCODING_INTSET`、`OBJ_ENCODING_LISTPACK`、`OBJ_ENCODING_HASHTABLE` で識別される。

どの表現を選ぶかは、新しいセットを作る `setTypeCreate` に集約されている。
第一引数の値が整数として表せ、かつ予想要素数が intset の上限以下なら intset を作る。
そうでなくても予想要素数が listpack の上限以下なら listpack を作る。
どちらの上限も超えるなら hashtable を作り、予想要素数ぶんの容量をあらかじめ確保する。

[`src/t_set.c` L51-L61](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L51-L61)

```c
robj *setTypeCreate(sds value, size_t size_hint) {
    if (isSdsRepresentableAsLongLong(value, NULL) == C_OK && size_hint <= server.set_max_intset_entries)
        return createIntsetObject();
    if (size_hint <= server.set_max_listpack_entries) return createSetListpackObject();

    /* We may oversize the set by using the hint if the hint is not accurate,
     * but we will assume this is acceptable to maximize performance. */
    robj *o = createSetObject();
    hashtableExpand(objectGetVal(o), size_hint);
    return o;
}
```

`size_hint` は SADD で一度に渡す要素数のような「だいたいこれくらい入る」という見積もりである。
これを使うことで、最終的に hashtable になると分かっているセットを最初から hashtable で作り、intset や listpack を経由する無駄な変換を省ける。
見積もりが外れて過大に確保することはあるが、性能のためにそれを許容するとコメントが明言している。

三つの生成関数はそれぞれ対応する空のデータ構造を包んだ `robj` を返す。

[`src/object.c` L495-L514](https://github.com/valkey-io/valkey/blob/9.1.0/src/object.c#L495-L514)

```c
robj *createSetObject(void) {
    hashtable *ht = hashtableCreate(&setHashtableType);
    robj *o = createObject(OBJ_SET, ht);
    o->encoding = OBJ_ENCODING_HASHTABLE;
    return o;
}

robj *createIntsetObject(void) {
    intset *is = intsetNew();
    robj *o = createObject(OBJ_SET, is);
    o->encoding = OBJ_ENCODING_INTSET;
    return o;
}

robj *createSetListpackObject(void) {
    unsigned char *lp = lpNew(0);
    robj *o = createObject(OBJ_SET, lp);
    o->encoding = OBJ_ENCODING_LISTPACK;
    return o;
}
```

### エンコーディングを切り替える閾値

三つの表現を分ける境目は、三つの設定項目で決まる。

[`src/config.c` L3466-L3468](https://github.com/valkey-io/valkey/blob/9.1.0/src/config.c#L3466-L3468)

```c
    createSizeTConfig("set-max-intset-entries", NULL, MODIFIABLE_CONFIG, 0, LONG_MAX, server.set_max_intset_entries, 512, INTEGER_CONFIG, NULL, NULL),
    createSizeTConfig("set-max-listpack-entries", NULL, MODIFIABLE_CONFIG, 0, LONG_MAX, server.set_max_listpack_entries, 128, INTEGER_CONFIG, NULL, NULL),
    createSizeTConfig("set-max-listpack-value", NULL, MODIFIABLE_CONFIG, 0, LONG_MAX, server.set_max_listpack_value, 64, INTEGER_CONFIG, NULL, NULL),
```

- **`set-max-intset-entries`**（既定 512）：intset に保持する要素数の上限。これを超えると intset は別の表現へ変換される。
- **`set-max-listpack-entries`**（既定 128）：listpack に保持する要素数の上限。
- **`set-max-listpack-value`**（既定 64）：listpack の各要素が許される最大バイト長。長い文字列が入ると listpack をやめて hashtable へ移る。

intset の上限が listpack の上限より大きいのは、要素がすべて整数なら listpack より intset のほうが密に詰められ、走査も軽いためである。
整数だけの集合は要素数が `set-max-intset-entries` に達するまで intset のまま保てる。

## 要素の追加と表現の昇格

要素の追加は `setTypeAdd` が入口になる。
これは値の長さを測って汎用版の `setTypeAddAux` に委譲するだけの薄いラッパーである。

[`src/t_set.c` L117-L119](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L117-L119)

```c
int setTypeAdd(robj *subject, sds value) {
    return setTypeAddAux(subject, value, sdslen(value), 0, 1);
}
```

`setTypeAddAux` がエンコーディングごとに分岐し、必要なら表現を昇格させる本体である。
この関数は値を sds 文字列、生のバイト列と長さ、整数のいずれかの形で受け取れるよう作られている。
ここでは現在のエンコーディングごとに、追加と昇格がどう絡むかを順に見る。

### intset での追加と昇格

現在のセットが intset で、追加する値が整数に変換できる場合を見る。

[`src/t_set.c` L181-L220](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L181-L220)

```c
    } else if (set->encoding == OBJ_ENCODING_INTSET) {
        long long value;
        if (string2ll(str, len, &value)) {
            uint8_t success = 0;
            objectSetVal(set, intsetAdd(objectGetVal(set), value, &success));
            if (success) {
                maybeConvertIntset(set);
                return 1;
            }
        } else {
            /* Check if listpack encoding is safe not to cross any threshold. */
            size_t maxelelen = 0, totsize = 0;
            unsigned long n = intsetLen(objectGetVal(set));
            // ... (中略) ...
            if (intsetLen((const intset *)objectGetVal(set)) < server.set_max_listpack_entries &&
                len <= server.set_max_listpack_value && maxelelen <= server.set_max_listpack_value &&
                lpSafeToAdd(NULL, totsize + len)) {
                // ... (中略) ...
                setTypeConvertAndExpand(set, OBJ_ENCODING_LISTPACK, intsetLen(objectGetVal(set)) + 1, 1);
                unsigned char *lp = objectGetVal(set);
                lp = lpAppend(lp, (unsigned char *)str, len);
                lp = lpShrinkToFit(lp);
                objectSetVal(set, lp);
                return 1;
            } else {
                setTypeConvertAndExpand(set, OBJ_ENCODING_HASHTABLE, intsetLen(objectGetVal(set)) + 1, 1);
                /* The set *was* an intset and this value is not integer
                 * encodable, so hashtableAdd should always work. */
                serverAssert(hashtableAdd(objectGetVal(set), sdsnewlen(str, len)));
                return 1;
            }
        }
```

値が整数なら `intsetAdd` で挿入し、新しく追加できたときだけ `maybeConvertIntset` を呼ぶ。
intset のまま要素数が増えすぎていないかを点検する関数である。

[`src/t_set.c` L80-L84](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L80-L84)

```c
/* Converts intset to HT if it contains too many entries. */
static void maybeConvertIntset(robj *subject) {
    serverAssert(subject->encoding == OBJ_ENCODING_INTSET);
    if (intsetLen(objectGetVal(subject)) > intsetMaxEntries()) setTypeConvert(subject, OBJ_ENCODING_HASHTABLE);
}
```

要素数が intset の上限を超えていれば hashtable へ変換する。
ここで listpack を経由しないのは、上限を超えた整数集合は listpack で持つには大きすぎ、O(1) で引ける hashtable が適するためである。
なお intset の最大要素数は内部の都合で 1G に制限される。

[`src/t_set.c` L72-L78](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L72-L78)

```c
/* Return the maximum number of entries to store in an intset. */
static size_t intsetMaxEntries(void) {
    size_t max_entries = server.set_max_intset_entries;
    /* limit to 1G entries due to intset internals. */
    if (max_entries >= 1 << 30) max_entries = 1 << 30;
    return max_entries;
}
```

整数でない値を intset に入れようとした場合は、上のコードの `else` 側に進む。
このとき昇格先は listpack か hashtable の二択になる。
現在の要素数が listpack の上限未満で、追加する文字列も既存要素も `set-max-listpack-value` の範囲に収まり、listpack に安全に足せるなら listpack へ変換して追記する。
どれか一つでも条件を満たさなければ hashtable へ変換する。
既存要素の長さは intset の最大値と最小値の桁数から見積もり、これを全要素の上界として安全側に判断する。

### listpack での追加と昇格

セットが listpack のときは、まず線形探索で重複を確かめる。

[`src/t_set.c` L158-L180](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L158-L180)

```c
    } else if (set->encoding == OBJ_ENCODING_LISTPACK) {
        unsigned char *lp = objectGetVal(set);
        unsigned char *p = lpFirst(lp);
        if (p != NULL) p = lpFind(lp, p, (unsigned char *)str, len, 0);
        if (p == NULL) {
            /* Not found.  */
            if (lpLength(lp) < server.set_max_listpack_entries && len <= server.set_max_listpack_value &&
                lpSafeToAdd(lp, len)) {
                if (str == tmpbuf) {
                    /* This came in as integer so we can avoid parsing it again.
                     * TODO: Create and use lpFindInteger; don't go via string. */
                    lp = lpAppendInteger(lp, llval);
                } else {
                    lp = lpAppend(lp, (unsigned char *)str, len);
                }
                objectSetVal(set, lp);
            } else {
                /* Size limit is reached. Convert to hashtable and add. */
                setTypeConvertAndExpand(set, OBJ_ENCODING_HASHTABLE, lpLength(lp) + 1, 1);
                serverAssert(hashtableAdd(objectGetVal(set), sdsnewlen(str, len)));
            }
            return 1;
        }
```

重複がなければ三つの条件を確かめる。
要素数が `set-max-listpack-entries` 未満であること、値が `set-max-listpack-value` の範囲であること、listpack に安全に追記できること。
これらをすべて満たせば listpack に追記し、一つでも破れば hashtable へ昇格させてから追加する。
listpack はいったん hashtable に上がると intset や listpack へ戻ることはない。

### hashtable での追加

セットがすでに hashtable のときは、これ以上の昇格はなく、挿入位置を求めて追加するだけである。

[`src/t_set.c` L143-L157](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L143-L157)

```c
    if (set->encoding == OBJ_ENCODING_HASHTABLE) {
        /* Avoid duping the string if it is an sds string. */
        sds sdsval = str_is_sds ? (sds)str : sdsnewlen(str, len);
        hashtable *ht = objectGetVal(set);
        hashtablePosition position;
        if (hashtableFindPositionForInsert(ht, sdsval, &position, NULL)) {
            /* Key doesn't already exist in the set. Add it but dup the key. */
            if (sdsval == str) sdsval = sdsdup(sdsval);
            hashtableInsertAtPosition(ht, sdsval, &position);
            return 1;
        } else if (sdsval != str) {
            /* String is already a member. Free our temporary sds copy. */
            sdsfree(sdsval);
            return 0;
        }
```

挿入位置を一度の探索で求めてからその場に挿入することで、重複確認と挿入のために二度ハッシュ計算する無駄を避けている。
入力がすでに sds 文字列ならコピーを避け、そうでないときだけ一時的な sds を作って判定する。

### 昇格の全体像

ここまでの分岐をまとめると、セット型は要素の型と数に応じて intset から listpack を経て hashtable へ一方向に昇格する。
昇格は要素を追加するたびに点検され、いちど上がった表現が下がることはない。

```mermaid
flowchart TD
    start([SADD で要素を追加]) --> intset{intset}
    listpack{listpack}
    hashtable[(hashtable)]

    intset -->|整数を追加し<br/>要素数が上限以下| intset
    intset -->|整数を追加し<br/>要素数が上限超過| hashtable
    intset -->|非整数を追加し<br/>listpack の閾値内| listpack
    intset -->|非整数を追加し<br/>listpack の閾値超過| hashtable

    listpack -->|要素数と値長が<br/>閾値内| listpack
    listpack -->|要素数または値長が<br/>閾値超過| hashtable

    hashtable -->|常に O(1) で追加| hashtable
```

整数だけの小さな集合は intset で密に持ち、文字列が混ざるか少し大きくなれば listpack で省メモリに持ち、要素が増えれば hashtable で O(1) のアクセスに切り替える。
この三段構えにより、小さな集合のメモリ消費を抑えつつ、大きな集合の操作速度を確保している。

### 変換の実体

実際の変換は `setTypeConvertAndExpand` が行う。
変換先のために新しいデータ構造を確保し、抽象イテレータで全要素を移し替えてから古い内部表現を解放する。

[`src/t_set.c` L496-L551](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L496-L551)

```c
int setTypeConvertAndExpand(robj *setobj, int enc, unsigned long cap, int panic) {
    setTypeIterator *si;
    serverAssertWithInfo(NULL, setobj, setobj->type == OBJ_SET && setobj->encoding != enc);

    if (enc == OBJ_ENCODING_HASHTABLE) {
        hashtable *ht = hashtableCreate(&setHashtableType);
        sds element;

        /* Presize the hashtable to avoid rehashing */
        if (panic) {
            hashtableExpand(ht, cap);
        } else if (!hashtableTryExpand(ht, cap)) {
            // ... (中略) ...
        }

        /* To add the elements we extract integers and create Objects */
        si = setTypeInitIterator(setobj);
        while ((element = setTypeNextObject(si)) != NULL) {
            serverAssert(hashtableAdd(ht, element));
        }
        setTypeReleaseIterator(si);

        freeSetObject(setobj); /* frees the internals but not setobj itself */
        setobj->encoding = OBJ_ENCODING_HASHTABLE;
        objectSetVal(setobj, ht);
    } else if (enc == OBJ_ENCODING_LISTPACK) {
        // ... (中略) ...
    } else {
        serverPanic("Unsupported set conversion");
    }
    return C_OK;
}
```

hashtable へ変換するときは、最終要素数 `cap` ぶんの容量を先に確保してから要素を流し込む。
これにより移し替えの最中にリハッシュが起きるのを避けている。

## SADD コマンド

SADD は `saddCommand` が処理する。
既存のキーがなければ要素数の見積もりつきでセットを新規作成し、すでにあれば追加前に表現を昇格させる余地を確かめる。

[`src/t_set.c` L597-L620](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L597-L620)

```c
void saddCommand(client *c) {
    robj *set;
    int j, added = 0;

    set = lookupKeyWrite(c->db, c->argv[1]);
    if (checkType(c, set, OBJ_SET)) return;

    if (set == NULL) {
        set = setTypeCreate(objectGetVal(c->argv[2]), c->argc - 2);
        dbAdd(c->db, c->argv[1], &set);
    } else {
        setTypeMaybeConvert(set, c->argc - 2);
    }

    for (j = 2; j < c->argc; j++) {
        if (setTypeAdd(set, objectGetVal(c->argv[j]))) added++;
    }
    if (added) {
        signalModifiedKey(c, c->db, c->argv[1]);
        notifyKeyspaceEvent(NOTIFY_SET, "sadd", c->argv[1], c->db->id);
        server.dirty += added;
    }
    addReplyLongLong(c, added);
}
```

新規キーでは渡された引数の個数 `c->argc - 2` を見積もりとして `setTypeCreate` に渡す。
一度に多数の要素を追加すると分かっていれば、最初から hashtable で作って途中の変換を避けられる。

既存キーで `setTypeMaybeConvert` を呼ぶのも同じ狙いである。
これから追加する個数を加味して、いま listpack や intset でも最終的に上限を超えると分かるなら、要素を入れる前に一括で hashtable へ変換しておく。

[`src/t_set.c` L65-L70](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L65-L70)

```c
void setTypeMaybeConvert(robj *set, size_t size_hint) {
    if ((set->encoding == OBJ_ENCODING_LISTPACK && size_hint > server.set_max_listpack_entries) ||
        (set->encoding == OBJ_ENCODING_INTSET && size_hint > server.set_max_intset_entries)) {
        setTypeConvertAndExpand(set, OBJ_ENCODING_HASHTABLE, size_hint, 1);
    }
}
```

要素を一つずつ追加しながら段階的に listpack を経て hashtable へ昇格させると、途中の表現で作っては捨てる変換が重なる。
追加前に最終形へ一度で変換しておけば、その中間コストをまとめて省ける。

## SISMEMBER と存在判定

SISMEMBER は要素がセットに属するかを判定する。
判定の本体は `setTypeIsMemberAux` であり、エンコーディングごとに探索の仕方が変わる。

[`src/t_set.c` L301-L317](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L301-L317)

```c
    if (set->encoding == OBJ_ENCODING_LISTPACK) {
        unsigned char *lp = objectGetVal(set);
        unsigned char *p = lpFirst(lp);
        return p && lpFind(lp, p, (unsigned char *)str, len, 0);
    } else if (set->encoding == OBJ_ENCODING_INTSET) {
        long long llval;
        return string2ll(str, len, &llval) && intsetFind(objectGetVal(set), llval);
    } else if (set->encoding == OBJ_ENCODING_HASHTABLE && str_is_sds) {
        return hashtableFind(objectGetVal(set), (sds)str, NULL);
    } else if (set->encoding == OBJ_ENCODING_HASHTABLE) {
        sds sdsval = sdsnewlen(str, len);
        int result = hashtableFind(objectGetVal(set), sdsval, NULL);
        sdsfree(sdsval);
        return result;
    } else {
        serverPanic("Unknown set encoding");
    }
```

三つの表現で存在判定の計算量が異なる。

- **intset**：要素は昇順に並んだ整数配列なので、`intsetFind` が二分探索で引く。計算量は O(log N)。判定値が整数に変換できなければ、その時点で非メンバと分かる。
- **listpack**：`lpFind` が先頭から線形に走査する。計算量は O(N) だが、要素数が `set-max-listpack-entries` 以下に抑えられているため実用上は短い。
- **hashtable**：`hashtableFind` がハッシュで直接引く。計算量は平均 O(1)。

listpack は線形探索でも、小さい集合に限ればキャッシュに乗りやすい連続領域を走るほうが速いことが多い。
集合が大きくなると線形探索の不利が効いてくるため、hashtable へ昇格して O(1) の判定に切り替える。
存在判定のコストが表現の昇格を促す動機になっている。

`setTypeIsMemberAux` を呼ぶ `sismemberCommand` は薄い。

[`src/t_set.c` L703-L712](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L703-L712)

```c
void sismemberCommand(client *c) {
    robj *set;

    if ((set = lookupKeyReadOrReply(c, c->argv[1], shared.czero)) == NULL || checkType(c, set, OBJ_SET)) return;

    if (setTypeIsMember(set, objectGetVal(c->argv[2])))
        addReply(c, shared.cone);
    else
        addReply(c, shared.czero);
}
```

## SMEMBERS とイテレータ

SMEMBERS は全要素を返す。
このコマンドはキー一つの SINTER として実装されており、`sinterCommand` 経由で `sinterGenericCommand` を呼ぶ。
キーが一つだけの積集合は、そのキーの全要素をそのまま返すことに等しい。

積集合の本体は、もっとも小さい集合を `setTypeInitIterator` で走査し、各要素が他の集合すべてに属するかを `setTypeIsMemberAux` で確かめる。

[`src/t_set.c` L1339-L1377](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L1339-L1377)

```c
    int only_integers = 1;
    si = setTypeInitIterator(sets[0]);
    while ((encoding = setTypeNext(si, &str, &len, &intobj)) != -1) {
        for (j = 1; j < setnum; j++) {
            if (sets[j] == sets[0]) continue;
            if (!setTypeIsMemberAux(sets[j], str, len, intobj, encoding == OBJ_ENCODING_HASHTABLE)) break;
        }

        /* Only take action when all sets contain the member */
        if (j == setnum) {
            // ... (中略) ...
            } else if (!dstkey) {
                if (str != NULL)
                    addReplyBulkCBuffer(c, str, len);
                else
                    addReplyBulkLongLong(c, intobj);
                cardinality++;
            // ... (中略) ...
        }
    }
    setTypeReleaseIterator(si);
```

SMEMBERS のように集合が一つだけのときは内側の `for` がただちに `j == setnum` を満たし、全要素がそのまま返る。

ここで効いているのが、エンコーディングの差を吸収する **抽象イテレータ** `setTypeIterator` である。
セットの中身が整数配列か listpack かハッシュテーブルかにかかわらず、呼び出し側は `setTypeInitIterator` と `setTypeNext` だけで全要素をたどれる。

[`src/server.h` L2769-L2776](https://github.com/valkey-io/valkey/blob/9.1.0/src/server.h#L2769-L2776)

```c
/* Structure to hold set iteration abstraction. */
typedef struct {
    robj *subject;
    int encoding;
    int ii; /* intset iterator */
    hashtableIterator *hashtable_iterator;
    unsigned char *lpi; /* listpack iterator */
} setTypeIterator;
```

`setTypeNext` がエンコーディングごとに分岐し、共通の引数を通じて要素を返す。
intset なら整数を `llele` に、listpack なら文字列か整数を、hashtable なら sds 文字列を返し、戻り値で要素がどの形で返ったかを呼び出し側に伝える。

[`src/t_set.c` L362-L389](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L362-L389)

```c
int setTypeNext(setTypeIterator *si, char **str, size_t *len, int64_t *llele) {
    if (si->encoding == OBJ_ENCODING_HASHTABLE) {
        void *next;
        if (!hashtableNext(si->hashtable_iterator, &next)) return -1;
        *str = next;
        *len = sdslen(*str);
        *llele = -123456789; /* Not needed. Defensive. */
    } else if (si->encoding == OBJ_ENCODING_INTSET) {
        if (!intsetGet(objectGetVal(si->subject), si->ii++, llele)) return -1;
        *str = NULL;
    } else if (si->encoding == OBJ_ENCODING_LISTPACK) {
        unsigned char *lp = objectGetVal(si->subject);
        unsigned char *lpi = si->lpi;
        if (lpi == NULL) {
            lpi = lpFirst(lp);
        } else {
            lpi = lpNext(lp, lpi);
        }
        if (lpi == NULL) return -1;
        si->lpi = lpi;
        unsigned int l;
        *str = (char *)lpGetValue(lpi, &l, (long long *)llele);
        *len = (size_t)l;
    } else {
        serverPanic("Wrong set encoding in setTypeNext");
    }
    return si->encoding;
}
```

戻り値で返ってくるエンコーディングを見て、呼び出し側は `str` が `NULL` なら整数、そうでなければ文字列として要素を扱う。
この抽象化のおかげで、SMEMBERS や積集合、差集合などの上位ロジックは三つの表現を一切意識せずに書ける。
表現を増やしたり閾値を変えたりしても、走査するコマンド側のコードは手を入れずに済む。

## SRANDMEMBER とランダム抽出

SRANDMEMBER は集合からランダムに要素を取り出す。
件数指定のない素の形は `srandmemberCommand` が `setTypeRandomElement` を一度呼ぶだけである。

[`src/t_set.c` L1201-L1224](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L1201-L1224)

```c
void srandmemberCommand(client *c) {
    robj *set;
    char *str;
    size_t len;
    int64_t llele;

    if (c->argc == 3) {
        srandmemberWithCountCommand(c);
        return;
    } else if (c->argc > 3) {
        addReplyErrorObject(c, shared.syntaxerr);
        return;
    }

    /* Handle variant without <count> argument. Reply with simple bulk string */
    if ((set = lookupKeyReadOrReply(c, c->argv[1], shared.null[c->resp])) == NULL || checkType(c, set, OBJ_SET)) return;

    setTypeRandomElement(set, &str, &len, &llele);
    if (str == NULL) {
        addReplyBulkLongLong(c, llele);
    } else {
        addReplyBulkCBuffer(c, str, len);
    }
}
```

ランダムな一要素の取り出しも、エンコーディングごとに最適な手段を選ぶ。

[`src/t_set.c` L421-L442](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_set.c#L421-L442)

```c
int setTypeRandomElement(robj *setobj, char **str, size_t *len, int64_t *llele) {
    if (setobj->encoding == OBJ_ENCODING_HASHTABLE) {
        void *entry = NULL;
        hashtableFairRandomEntry(objectGetVal(setobj), &entry);
        *str = entry;
        *len = sdslen(*str);
        *llele = -123456789; /* Not needed. Defensive. */
    } else if (setobj->encoding == OBJ_ENCODING_INTSET) {
        *llele = intsetRandom(objectGetVal(setobj));
        *str = NULL; /* Not needed. Defensive. */
    } else if (setobj->encoding == OBJ_ENCODING_LISTPACK) {
        unsigned char *lp = objectGetVal(setobj);
        int r = rand() % lpLength(lp);
        unsigned char *p = lpSeek(lp, r);
        unsigned int l;
        *str = (char *)lpGetValue(p, &l, (long long *)llele);
        *len = (size_t)l;
    } else {
        serverPanic("Unknown set encoding");
    }
    return setobj->encoding;
}
```

intset は整数配列なので添字を一つ無作為に選べばよく、`intsetRandom` がそれを行う。
listpack も `rand()` で位置を選び `lpSeek` でその要素まで移動する。
hashtable は `hashtableFairRandomEntry` で偏りの小さい一様抽出を行う。
件数指定つきの SRANDMEMBER は `srandmemberWithCountCommand` が扱い、重複の許否や件数と集合サイズの比に応じて抽出戦略を切り替える。

## まとめ

- セット型は要素の中身と数に応じて intset、listpack、hashtable の三表現を使い分ける。整数だけで小さければ intset、文字列を含み小さければ listpack、大きくなれば hashtable になる。
- 表現は `setTypeAddAux` の中で要素を追加するたびに点検され、`set-max-intset-entries`、`set-max-listpack-entries`、`set-max-listpack-value` の閾値を超えると一方向に昇格する。いちど上がった表現は下がらない。
- SADD は新規キーでは要素数の見積もりで適切な表現から作り、既存キーでは `setTypeMaybeConvert` で追加前にまとめて昇格させ、中間表現を作っては捨てる無駄を省く。
- 存在判定の計算量は表現で異なる。intset は二分探索で O(log N)、listpack は線形で O(N)、hashtable は O(1)。小さい集合の省メモリと大きい集合の高速判定を両立させるのが三段エンコーディングの狙いである。
- 抽象イテレータ `setTypeIterator` がエンコーディングの差を吸収し、SMEMBERS や積集合などの上位ロジックは三表現を意識せずに全要素をたどれる。

## 関連する章

- [第10章 intset](../part01-data-structures/10-intset.md)：整数集合の内部表現と二分探索。
- [第8章 listpack](../part01-data-structures/08-listpack.md)：小さな集合に使うコンパクト表現。
- [第7章 hashtable](../part01-data-structures/07-hashtable.md)：大きな集合の表現とランダム抽出。
- [第14章 オブジェクトとエンコーディング](14-object-encoding.md)：`robj` とエンコーディングの基礎。
- [第18章 ハッシュ型](18-t-hash.md)：同様に listpack と hashtable を使い分ける別の型。
