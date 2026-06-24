# 第47章 ブロッキングコマンド

> **本章で読むソース**
>
> - [`src/blocked.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c)
> - [`src/t_list.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_list.c)
> - [`src/timeout.c`](https://github.com/valkey-io/valkey/blob/9.1.0/src/timeout.c)

## この章の狙い

`BLPOP` のように、データが届くまでクライアントを待たせるコマンドが、単一スレッドの中でどう実現されているかを読む。
待っているクライアントを本当に止めながら、他のクライアントの処理は止めないという要求を、Valkey は二つの機構で満たしている。
クライアントをブロック状態にしてキーごとの待ち行列へ登録する仕組みと、キーにデータが入ったときだけ待っていたクライアントを起こす仕組みである。
この二つを実コードで追い、ポーリングなしで待ちと起床が成立する理由を理解する。

## 前提

リストへのプッシュとポップは [第16章](../part03-objects-types/16-t-list.md)、コマンドを処理するイベントループは [第24章](../part04-server-events/24-event-loop.md) で扱う。
本章はそれらの上に、待ちと起床の層を重ねて読む。

## ブロッキングの目的

`BLPOP key timeout` は、`key` のリストに要素があればただちにポップして返す。
要素がなければ、誰かがそのキーにプッシュするまで、あるいはタイムアウトに達するまで待つ。
通常の `LPOP` が空リストに対してすぐ nil を返すのとは、待つ点が違う。

ここで問題になるのが、Valkey のコマンド実行が単一スレッドだという点である。
あるクライアントを待たせるあいだ、サーバ全体を止めるわけにはいかない。
待っているクライアント以外は、その間も `SET` や `GET` を処理し続けなければならない。
さらに、待っているキーへ要素をプッシュするのも別のクライアントなのだから、待ちながら他クライアントのコマンドを動かせなければ、そもそも待ちが解ける契機が来ない。

したがってブロッキングは、スレッドを止める方式では実装できない。
クライアントを論理的に「ブロック状態」に置き、そのクライアントへの応答だけを保留したまま、イベントループは次のクライアントへ進む。
`blocked.c` 冒頭の API コメントが、この設計の骨格を説明している。

[`src/blocked.c` L36-L65](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c#L36-L65)

```c
/*
 * API:
 *
 * blockClient() set the CLIENT_BLOCKED flag in the client, and set the
 * specified block type 'btype' filed to one of BLOCKED_* macros.
 *
 * unblockClient() unblocks the client doing the following:
 * 1) It calls the btype-specific function to cleanup the state.
 * 2) It unblocks the client by unsetting the CLIENT_BLOCKED flag.
 * 3) It puts the client into a list of just unblocked clients that are
 *    processed ASAP in the beforeSleep() event loop callback, so that
 *    if there is some query buffer to process, we do it.
 * ... (中略) ...
 */
```

ブロックには種類がある。
`BLPOP` のようなキー待ちのほかに、レプリカの ACK を待つ `WAIT`、シャットダウンや一時停止に伴う待ちなどがあり、それぞれ `BLOCKED_*` という型で区別される。

[`src/server.h` L340-L351](https://github.com/valkey-io/valkey/blob/9.1.0/src/server.h#L340-L351)

```c
typedef enum blocking_type {
    BLOCKED_NONE,     /* Not blocked, no CLIENT_BLOCKED flag set. */
    BLOCKED_LIST,     /* BLPOP & co. */
    BLOCKED_WAIT,     /* WAIT for synchronous replication. */
    BLOCKED_MODULE,   /* Blocked by a loadable module. */
    BLOCKED_STREAM,   /* XREAD. */
    BLOCKED_ZSET,     /* BZPOP et al. */
    BLOCKED_POSTPONE, /* Blocked by processCommand, re-try processing later. */
    BLOCKED_SHUTDOWN, /* SHUTDOWN. */
    BLOCKED_NUM,      /* Number of blocked states. */
    BLOCKED_END       /* End of enumeration */
} blocking_type;
```

本章では、このうちキー待ち（`BLOCKED_LIST` を代表とする `BLOCKED_ZSET` と `BLOCKED_STREAM`）を中心に読む。
`BLOCKED_WAIT` には節末で触れる。

## BLPOP がブロックを決めるまで

まず、待つかどうかを誰が判断するかを `BLPOP` の実装で見る。
`BLPOP` は `blockingPopGenericCommand` を呼ぶ。
この関数は、与えられたキーを順に調べ、要素のある非空リストが一つでも見つかればポップして返す。

[`src/t_list.c` L1167-L1213](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_list.c#L1167-L1213)

```c
void blockingPopGenericCommand(client *c, robj **keys, int numkeys, int where, int timeout_idx, long count) {
    robj *o;
    robj *key;
    mstime_t timeout;
    int j;

    if (getTimeoutFromObjectOrReply(c, c->argv[timeout_idx], &timeout, UNIT_SECONDS) != C_OK) return;

    /* Traverse all input keys, we take action only based on one key. */
    for (j = 0; j < numkeys; j++) {
        key = keys[j];
        o = lookupKeyWrite(c->db, key);

        /* Non-existing key, move to next key. */
        if (o == NULL) continue;
        /* ... (中略：型チェックと空リストの読み飛ばし) ... */

        /* Non empty list, this is like a normal [LR]POP. */
        robj *value = listTypePop(o, where);
        /* ... (中略：応答を書き、[LR]POP として伝播) ... */
        return;
    }
    // ... (中略：ブロックの判断は次のコードへ続く) ...
}
```

すべてのキーが空、または存在しなかった場合だけ、関数の末尾に到達する。
ここでブロックを決める。

[`src/t_list.c` L1215-L1224](https://github.com/valkey-io/valkey/blob/9.1.0/src/t_list.c#L1215-L1224)

```c
    /* If we are not allowed to block the client, the only thing
     * we can do is treating it as a timeout (even with timeout 0). */
    if (c->flag.deny_blocking) {
        addReplyNullArray(c);
        return;
    }

    /* If the keys do not exist we must block */
    blockForKeys(c, BLOCKED_LIST, keys, numkeys, timeout, 0);
}
```

`deny_blocking` フラグが立っているとき（`MULTI`/`EXEC` の中や Lua スクリプトからの呼び出しなど、待たせると進めなくなる文脈）は、待たずに nil を返す。
それ以外では `blockForKeys` を呼ぶ。
ブロックするかどうかは、データの有無を見たコマンド側が決める。
ブロックの機構そのものは `blocked.c` が引き受ける。

## ブロックの登録（設計の核その1）

`blockForKeys` が、待ちの状態を作る本体である。
やることは二つある。
クライアントを `BLOCKED_LIST` 型のブロック状態にすることと、待っているキーを引けば待っているクライアントが分かるよう、データベースの索引に登録することである。

[`src/blocked.c` L434-L486](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c#L434-L486)

```c
void blockForKeys(client *c, int btype, robj **keys, int numkeys, mstime_t timeout, int unblock_on_nokey) {
    dictEntry *db_blocked_entry, *db_blocked_existing_entry, *client_blocked_entry;
    list *l;
    int j;

    initClientBlockingState(c);

    if (!c->flag.reexecuting_command) {
        c->bstate->timeout = timeout;
    }

    for (j = 0; j < numkeys; j++) {
        /* If the key already exists in the dictionary ignore it. */
        if (!(client_blocked_entry = dictAddRaw(c->bstate->keys, keys[j], NULL))) {
            continue;
        }
        incrRefCount(keys[j]);

        /* And in the other "side", to map keys -> clients */
        db_blocked_entry = dictAddRaw(c->db->blocking_keys, keys[j], &db_blocked_existing_entry);

        /* In case key[j] did not have blocking clients yet, we need to create a new list */
        if (db_blocked_entry != NULL) {
            l = listCreate();
            dictSetVal(c->db->blocking_keys, db_blocked_entry, l);
            incrRefCount(keys[j]);
        } else {
            l = dictGetVal(db_blocked_existing_entry);
        }
        listAddNodeTail(l, c);
        dictSetVal(c->bstate->keys, client_blocked_entry, listLast(l));
        /* ... (中略：unblock_on_nokey の登録) ... */
    }
    c->bstate->unblock_on_nokey = unblock_on_nokey;
    if (btype != BLOCKED_MODULE) c->flag.pending_command = 1;
    blockClient(c, btype);
}
```

中心は `c->db->blocking_keys` という辞書である。
これはキーを引くと、そのキーを待っているクライアントのリスト（連結リスト）が得られる索引である。
待ち手が複数いれば、`listAddNodeTail` で末尾に並ぶ。
これが先着順（FIFO）で起こすための並びになる。

同時に、クライアント側にも `c->bstate->keys` という辞書を持たせ、自分が待っているキーを覚えさせる。
さらに、辞書の値として `listLast(l)`、つまり自分が並んだリストノードへのポインタを保存している。
こうしておくと、後で起床するときに、リストを線形に走査せず、ノードを直接外せる。

二つの索引を張る理由は、起床と後始末の両方を定数時間に近づけるためである。
キーから待ち手を引くのは起床のときに使い、クライアントから待っているキーを引くのは後始末のときに使う。
登録の最後に `blockClient` を呼ぶ。

[`src/blocked.c` L106-L118](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c#L106-L118)

```c
void blockClient(client *c, int btype) {
    /* Replicated clients should never be blocked unless pause or module */
    serverAssert(!(isReplicatedClient(c) && btype != BLOCKED_MODULE && btype != BLOCKED_POSTPONE));

    initClientBlockingState(c);

    c->flag.blocked = 1;
    c->bstate->btype = btype;
    if (!c->flag.module)
        server.blocked_clients++; /* We count blocked client stats on regular clients and not on module clients */
    server.blocked_clients_by_type[btype]++;
    addClientToTimeoutTable(c);
}
```

`blockClient` は `CLIENT_BLOCKED` フラグを立て、ブロック型を記録し、タイムアウト表へ登録する。
フラグが立つと、このクライアントの受信ハンドラはデータをクエリバッファへ溜めるだけになり、コマンドの解析と実行を止める。
冒頭の API コメントが述べていたとおり、待ちのあいだ入力は捨てられず、起床後に処理される。
イベントループは何も待たずに次のクライアントへ進む。
これでクライアントは止まり、サーバは止まらない。

## 起床（設計の核その2）

待っているクライアントは、誰がいつ起こすのか。
鍵は、待っているキーへデータが入る操作だけが起床の契機になる点である。
`LPUSH` のようなコマンドが新しいキーを作ると、`dbAdd` の内部で `signalKeyAsReady` が呼ばれる。

[`src/db.c` L222-L224](https://github.com/valkey-io/valkey/blob/9.1.0/src/db.c#L222-L224)

```c
    kvstoreHashtableAdd(db->keys, dict_index, val);
    signalKeyAsReady(db, key, val->type);
    notifyKeyspaceEvent(NOTIFY_NEW, "new", key, db->id);
```

`signalKeyAsReady` の実体は `signalKeyAsReadyLogic` である。
この関数は、そのキーを本当に待っているクライアントがいるかを確かめてから、キーを `server.ready_keys` という起床候補のリストへ積む。

[`src/blocked.c` L522-L566](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c#L522-L566)

```c
static void signalKeyAsReadyLogic(serverDb *db, robj *key, int type, int deleted) {
    readyList *rl;

    /* Quick returns. */
    int btype = getBlockedTypeByType(type);
    if (btype == BLOCKED_NONE) {
        /* The type can never block. */
        return;
    }
    if (!server.blocked_clients_by_type[btype] && !server.blocked_clients_by_type[BLOCKED_MODULE]) {
        /* No clients block on this type. */
        // ... (中略：BLOCKED_MODULE の補足コメント) ...
        return;
    }
    /* ... (中略：deleted の分岐) ... */
    } else {
        /* No clients blocking for this key? No need to queue it. */
        if (dictFind(db->blocking_keys, key) == NULL) return;
    }

    dictEntry *de, *existing;
    de = dictAddRaw(db->ready_keys, key, &existing);
    if (de) {
        /* We add the key in the db->ready_keys dictionary in order
         * to avoid adding it multiple times into a list with a simple O(1)
         * check. */
        incrRefCount(key);
    } else {
        /* Key was already signaled? No need to queue it again. */
        return;
    }

    /* Ok, we need to queue this key into server.ready_keys. */
    rl = zmalloc(sizeof(*rl));
    rl->key = key;
    rl->db = db;
    incrRefCount(key);
    listAddNodeTail(server.ready_keys, rl);
}
```

ここに無駄を省く工夫が二つ重なっている。
一つは、待っているクライアントが一人もいない型やキーなら、関数の冒頭で早々に戻る点である。
`db->blocking_keys` を引いて待ち手がいなければ、起床候補のリストには何も積まない。
普段のプッシュは、誰も待っていなければこの追加コストをほぼ払わない。

もう一つは、`db->ready_keys` という辞書で重複を防ぐ点である。
`MULTI`/`EXEC` や Lua スクリプトの中で同じキーへ何度もプッシュしても、起床候補リストにそのキーが載るのは一度だけになる。

`signalKeyAsReady` はキーを候補に積むだけで、まだ誰も起こさない。
実際に起こすのは、コマンドの実行が一区切りした後である。
`processCommand` は `call` でコマンドを実行した直後に、候補がたまっていれば `handleClientsBlockedOnKeys` を呼ぶ。

[`src/server.c` L4636-L4638](https://github.com/valkey-io/valkey/blob/9.1.0/src/server.c#L4636-L4638)

```c
        int flags = CMD_CALL_FULL;
        call(c, flags);
        if (listLength(server.ready_keys) && !isInsideYieldingLongCommand()) handleClientsBlockedOnKeys();
```

このタイミングが重要である。
プッシュの最中ではなく、コマンドが終わってデータベースが一貫した状態になってから起床処理に入る。
`handleClientsBlockedOnKeys` は、起床候補リストを走査し、各キーについて待っていたクライアントを起こす。

[`src/blocked.c` L383-L425](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c#L383-L425)

```c
void handleClientsBlockedOnKeys(void) {
    /* In case we are already in the process of unblocking clients we should
     * not make a recursive call, in order to prevent breaking fairness. */
    static int in_handling_blocked_clients = 0;
    if (in_handling_blocked_clients) return;
    in_handling_blocked_clients = 1;
    // ... (中略：also_propagate の状態確認と BLMOVE の連鎖に関するコメント) ...
    while (listLength(server.ready_keys) != 0) {
        list *l;

        /* Point server.ready_keys to a fresh list and save the current one
         * locally. This way as we run the old list we are free to call
         * signalKeyAsReady() that may push new elements in server.ready_keys
         * when handling clients blocked into BLMOVE. */
        l = server.ready_keys;
        server.ready_keys = listCreate();

        while (listLength(l) != 0) {
            listNode *ln = listFirst(l);
            readyList *rl = ln->value;

            /* First of all remove this key from db->ready_keys so that
             * we can safely call signalKeyAsReady() against this key. */
            dictDelete(rl->db->ready_keys, rl->key);

            handleClientsBlockedOnKey(rl);

            /* Free this item. */
            decrRefCount(rl->key);
            zfree(rl);
            listDelNode(l, ln);
        }
        listRelease(l); /* We have the new list on place at this point. */
    }
    in_handling_blocked_clients = 0;
}
```

候補リストを丸ごと別のリストへ退避してから走査している点に注目したい。
`BLMOVE` のように、待ち手を起こした結果さらに別のキーへプッシュが起き、新しい起床候補が積まれることがある。
走査中のリストに追加が混ざらないよう、現在のリストを取り出してから空の新リストへ差し替え、追加は新リストへ向かわせる。
外側の `while` がそれを次の周回で拾う。

キー単位の起床は `handleClientsBlockedOnKey` が担う。
`db->blocking_keys` からそのキーの待ち行列を引き、先頭から順にクライアントを起こす。

[`src/blocked.c` L624-L657](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c#L624-L657)

```c
static void handleClientsBlockedOnKey(readyList *rl) {
    /* We serve clients in the same order they blocked for
     * this key, from the first blocked to the last. */
    dictEntry *de = dictFind(rl->db->blocking_keys, rl->key);

    if (de) {
        list *clients = dictGetVal(de);
        listNode *ln;
        listIter li;
        listRewind(clients, &li);

        /* Avoid processing more than the initial count so that we're not stuck
         * in an endless loop in case the reprocessing of the command blocks again. */
        long count = listLength(clients);
        while ((ln = listNext(&li)) && count--) {
            client *receiver = listNodeValue(ln);
            robj *o = lookupKeyReadWithFlags(rl->db, rl->key, LOOKUP_NOEFFECTS);
            /* ... (中略：待ち型とキーの型が一致するか確認) ... */
            if ((o != NULL && (receiver->bstate->btype == getBlockedTypeByType(o->type))) ||
                (o != NULL && (receiver->bstate->btype == BLOCKED_MODULE)) || (receiver->bstate->unblock_on_nokey)) {
                if (receiver->bstate->btype != BLOCKED_MODULE)
                    unblockClientOnKey(receiver, rl->key);
                else
                    moduleUnblockClientOnKey(receiver, rl->key);
            }
        }
    }
}
```

待ち行列の先頭から順に起こすので、`BLPOP` が複数待っていれば先に待ち始めたクライアントが先に要素を受け取る。
起こされたクライアントは `unblockClientOnKey` の中で `BLPOP` を再実行し、こんどは要素のある非空リストを見つけてポップする。
要素が一つしかなく先頭のクライアントが取り切れば、後続のクライアントは非空リストを見つけられず、再びブロックへ戻る。
全体として、起床は待っているキーが変わったときにだけ走り、空振りした分は待ちへ戻るので、無駄なくクライアントを捌ける。

## BLPOP の待ちと起床

ここまでの流れを `BLPOP` で通して図にする。

```mermaid
sequenceDiagram
    participant A as クライアントA (BLPOP)
    participant Loop as イベントループ
    participant DB as データベース
    participant B as クライアントB (LPUSH)

    A->>Loop: BLPOP mylist 0
    Loop->>DB: mylist を参照（空）
    Loop->>DB: blockForKeys（blocking_keys に登録）
    Note over A,Loop: A は CLIENT_BLOCKED。応答を保留し、ループは他へ進む
    B->>Loop: LPUSH mylist x
    Loop->>DB: dbAdd → signalKeyAsReady
    DB-->>Loop: ready_keys に mylist を積む
    Note over Loop: call() 直後、handleClientsBlockedOnKeys
    Loop->>DB: mylist を待っていた A を起こす
    Loop->>A: BLPOP を再実行し x をポップして返す
```

待ちのあいだ A は何もポーリングしていない。
B のプッシュが起床候補を積み、コマンド処理の区切りで起床処理が走り、A が再実行されて要素を取る。
起床の契機は「待っているキーにデータが入ったこと」だけに限られている。

## タイムアウトとアンブロック

`BLPOP key timeout` の `timeout` がゼロでなければ、その時刻までに要素が来なければ待ちを打ち切る。
`blockForKeys` は `c->bstate->timeout` に期限（絶対時刻のミリ秒）を入れ、`blockClient` 経由で `addClientToTimeoutTable` がクライアントを期限つきの索引へ登録する。
この索引は基数木（rax）で、128 ビットのキーを期限と クライアント ID で構成している。

[`src/timeout.c` L76-L88](https://github.com/valkey-io/valkey/blob/9.1.0/src/timeout.c#L76-L88)

```c
/* For blocked clients timeouts we populate a radix tree of 128 bit keys
 * composed as such:
 *
 *  [8 byte big endian expire time]+[8 byte client ID]
 * ... (中略) ...
 * Every time a client blocks with a timeout, we add the client in
 * the tree. In beforeSleep() we call handleBlockedClientsTimeout() to run
 * the tree and unblock the clients. */
```

期限を先頭 8 バイトのビッグエンディアンに置くことで、木を前から走査すれば期限の早い順に並ぶ。
`handleBlockedClientsTimeout` は木を前から辿り、現在時刻に達していないキーに当たった時点で走査を止める。
期限切れだけを見て、まだ先のものは触らない。

[`src/timeout.c` L130-L148](https://github.com/valkey-io/valkey/blob/9.1.0/src/timeout.c#L130-L148)

```c
void handleBlockedClientsTimeout(void) {
    if (raxSize(server.clients_timeout_table) == 0) return;
    uint64_t now = mstime();
    raxIterator ri;
    raxStart(&ri, server.clients_timeout_table);
    raxSeek(&ri, "^", NULL, 0);

    while (raxNext(&ri)) {
        uint64_t timeout;
        client *c;
        decodeTimeoutKey(ri.key, &timeout, &c);
        if (timeout >= now) break; /* All the timeouts are in the future. */
        c->flag.in_to_table = 0;
        checkBlockedClientTimeout(c, now);
        raxRemove(server.clients_timeout_table, ri.key, ri.key_len, NULL);
        raxSeek(&ri, "^", NULL, 0);
    }
    raxStop(&ri);
}
```

期限に達したクライアントは `checkBlockedClientTimeout` を通って `unblockClientOnTimeout` で起こされ、`BLPOP` なら nil 配列が返る。
クライアントが明示的に待ちを打ち切られることもある。
`CLIENT UNBLOCK <id>` がそれで、対象クライアントがタイムアウト可能なブロック型のときに、タイムアウト扱いかエラー扱いで起こす。

[`src/networking.c` L5434-L5440](https://github.com/valkey-io/valkey/blob/9.1.0/src/networking.c#L5434-L5440)

```c
    if (target && target->flag.blocked && blockedClientMayTimeout(target)) {
        if (unblock_error)
            unblockClientOnError(target, "-UNBLOCKED client unblocked via CLIENT UNBLOCK");
        else
            unblockClientOnTimeout(target);

        addReply(c, shared.cone);
    }
```

どの経路で起こす場合も、最後は `unblockClient` に集約される。
ブロック型ごとの後始末を呼んでから、`CLIENT_BLOCKED` フラグを下ろし、待ち状態の索引やタイムアウト表からクライアントを外す。

[`src/blocked.c` L217-L256](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c#L217-L256)

```c
void unblockClient(client *c, int queue_for_reprocessing) {
    if (c->bstate->btype == BLOCKED_LIST || c->bstate->btype == BLOCKED_ZSET || c->bstate->btype == BLOCKED_STREAM) {
        unblockClientWaitingData(c);
    } else if (c->bstate->btype == BLOCKED_WAIT) {
        unblockClientWaitingReplicas(c);
    }
    /* ... (中略：モジュール・POSTPONE・SHUTDOWN の後始末) ... */

    /* We count blocked client stats on regular clients and not on module clients */
    if (!c->flag.module) server.blocked_clients--;
    server.blocked_clients_by_type[c->bstate->btype]--;
    /* Clear the flags, and put the client in the unblocked list so that
     * we'll process new commands in its query buffer ASAP. */
    c->flag.blocked = 0;
    c->bstate->btype = BLOCKED_NONE;
    c->bstate->unblock_on_nokey = 0;
    removeClientFromTimeoutTable(c);
    if (queue_for_reprocessing) queueClientForReprocessing(c);
}
```

キー待ちの後始末 `unblockClientWaitingData` は、`blockForKeys` が張った二つの索引を逆にたどって解く。
クライアントが保存していたリストノードを直接外せるので、待ち行列をなめ直さずに済む。
タイムアウトと起床の処理は、いずれもイベントループの `beforeSleep` から呼ばれる。

[`src/blocked.c` L796-L818](https://github.com/valkey-io/valkey/blob/9.1.0/src/blocked.c#L796-L818)

```c
void blockedBeforeSleep(void) {
    /* Handle precise timeouts of blocked clients. */
    handleBlockedClientsTimeout();

    /* Unblock all the clients blocked for synchronous replication
     * in WAIT or WAITAOF. */
    if (listLength(server.clients_waiting_acks)) processClientsWaitingReplicas();

    /* Try to process blocked clients every once in while.
     * ... (中略：モジュールのタイマーコールバックからの起床に関する説明) ... */
    handleClientsBlockedOnKeys();
    // ... (中略：モジュールがブロックを解除したクライアントの処理) ...
    /* Try to process pending commands for clients that were just unblocked. */
    if (listLength(server.unblocked_clients)) processUnblockedClients();
}
```

起こされたクライアントは、いったん `server.unblocked_clients` に積まれ、`processUnblockedClients` で溜まっていたクエリバッファを処理してもらう。
待ちのあいだ受信ハンドラが捨てずに溜めておいた入力が、ここで初めて解析され実行される。

## キー待ち以外のブロック

ブロックの機構はキー待ち専用ではない。
`WAIT numreplicas timeout` は、直前の書き込みが指定数のレプリカへ複製されるまで待つコマンドで、`BLOCKED_WAIT` 型のブロックを使う。
キーではなくレプリカの ACK オフセットを待つので、`blocking_keys` ではなく `server.clients_waiting_acks` の行列に並び、`beforeSleep` の `processClientsWaitingReplicas` で条件を満たしたクライアントを起こす。
レプリケーションと `WAIT` の詳しい仕組みは [第38章](../part07-replication-cluster/38-replication.md) で扱う。
そのほか、サーバが一時停止やシャットダウン処理に入るときの待ち（`BLOCKED_POSTPONE` と `BLOCKED_SHUTDOWN`）も、同じ `blockClient` と `unblockClient` の枠組みに乗っている。
待つ条件こそ違っても、クライアントを論理的にブロックし、契機が来たら `beforeSleep` で起こすという骨格は共通である。

## まとめ

- ブロッキングコマンドは、単一スレッドを止めずにクライアントを論理的に待たせる。`CLIENT_BLOCKED` フラグを立てたクライアントは応答を保留され、イベントループは他のクライアントを処理し続ける。
- 待ちの登録は `blockForKeys` が行う。`db->blocking_keys`（キー → 待ち手の行列）とクライアント側の `c->bstate->keys` という二つの索引を張り、起床と後始末を線形走査なしで行えるようにする。
- 起床は、待っているキーへデータが入る操作（`LPUSH` など）が `signalKeyAsReady` を呼ぶことで始まる。キーは `server.ready_keys` に積まれ、コマンド処理の区切りで `handleClientsBlockedOnKeys` が待ち手を先着順に起こす。
- 待ち手がいない型やキーは起床候補に積まず、`db->ready_keys` 辞書で同一キーの重複登録も防ぐ。普段のプッシュはブロッキングのコストをほぼ払わない。
- タイムアウトは期限つきの基数木で管理し、`beforeSleep` で期限切れだけを前から処理する。`CLIENT UNBLOCK` でも待ちを打ち切れる。どの経路も `unblockClient` に集約される。
- `WAIT` などキー待ち以外のブロックも、同じ `blockClient`/`unblockClient` の枠組みを共有する。

## 関連する章

- リスト型のプッシュとポップの実装は [第16章](../part03-objects-types/16-t-list.md)。
- ブロックと起床を駆動するイベントループと `beforeSleep` は [第24章](../part04-server-events/24-event-loop.md)。
- `WAIT` とレプリカ ACK の待ちは [第38章](../part07-replication-cluster/38-replication.md)。
