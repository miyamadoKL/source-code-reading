# Valkey ソースコードリーディング

Valkey（[valkey-io/valkey](https://github.com/valkey-io/valkey)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「高速化・省メモリの工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：9.1.0（コード引用はすべて [`9.1.0` タグ](https://github.com/valkey-io/valkey/tree/9.1.0)に固定。Redis OSS 7.2.4 互換のフォーク）
- **想定読者**：C と一般的なサーバ/DB の基礎がある中級エンジニア
- **読み方**：低レベルのデータ構造から順に積み上がる構成。第0部から順に読むことを想定する。

コード引用は、本文中の `[path L開始-L終了](https://github.com/valkey-io/valkey/blob/9.1.0/...)` 形式のリンクから GitHub 上の該当箇所を直接参照できる。

## 目次

### 第0部　導入と全体像

1. [Valkey とは何か](part00-introduction/01-what-is-valkey.md)
2. [アーキテクチャ全体像](part00-introduction/02-architecture-overview.md)
3. [起動と最小の対話](part00-introduction/03-hello-valkey.md)

### 第1部　低レベルデータ構造

4. [SDS 動的文字列](part01-data-structures/04-sds.md)
5. [双方向リスト adlist](part01-data-structures/05-adlist.md)
6. [dict チェイン法ハッシュテーブル](part01-data-structures/06-dict.md)
7. [hashtable 新ハッシュテーブル](part01-data-structures/07-hashtable.md)
8. [listpack コンパクト列](part01-data-structures/08-listpack.md)
9. [quicklist](part01-data-structures/09-quicklist.md)
10. [intset 整数集合](part01-data-structures/10-intset.md)
11. [rax 基数木](part01-data-structures/11-rax.md)

### 第2部　メモリとキー空間基盤

12. [zmalloc とメモリ管理](part02-memory-keyspace/12-zmalloc.md)
13. [kvstore キー空間抽象](part02-memory-keyspace/13-kvstore.md)

### 第3部　オブジェクトシステムと型エンコーディング

14. [robj とエンコーディング](part03-objects-types/14-object-encoding.md)
15. [文字列型](part03-objects-types/15-t-string.md)
16. [リスト型](part03-objects-types/16-t-list.md)
17. [セット型](part03-objects-types/17-t-set.md)
18. [ハッシュ型とフィールド TTL](part03-objects-types/18-t-hash.md)
19. [ソート済みセットと skiplist](part03-objects-types/19-t-zset.md)
20. [ストリーム型](part03-objects-types/20-t-stream.md)
21. [HyperLogLog](part03-objects-types/21-hyperloglog.md)
22. [ビットマップと地理空間](part03-objects-types/22-bitops-geo.md)
23. [ボラタイルセット vset（フィールド失効の索引）](part03-objects-types/23-vset.md)

### 第4部　サーバとイベント駆動

24. [イベントループ ae](part04-server-events/24-event-loop.md)
25. [ネットワークとクライアント](part04-server-events/25-networking.md)
26. [RESP プロトコルと応答生成](part04-server-events/26-resp-protocol.md)
27. [コマンド実行パイプライン](part04-server-events/27-command-execution.md)
28. [I/O スレッドとプリフェッチ](part04-server-events/28-io-threads.md)
29. [設定管理](part04-server-events/29-config.md)

### 第5部　データベース管理

30. [データベースとキー操作](part05-database/30-database.md)
31. [有効期限](part05-database/31-expire.md)
32. [メモリ退避](part05-database/32-eviction.md)
33. [遅延解放とデフラグ](part05-database/33-lazyfree-defrag.md)
34. [キースペース通知](part05-database/34-keyspace-notifications.md)

### 第6部　永続化

35. [RDB スナップショット](part06-persistence/35-rdb.md)
36. [AOF 追記ファイル](part06-persistence/36-aof.md)
37. [永続化の下支え](part06-persistence/37-persistence-internals.md)

### 第7部　レプリケーションとクラスタ

38. [レプリケーション](part07-replication-cluster/38-replication.md)
39. [クラスタの仕組み](part07-replication-cluster/39-cluster.md)
40. [アトミックスロット移行](part07-replication-cluster/40-slot-migration.md)
41. [Sentinel](part07-replication-cluster/41-sentinel.md)

### 第8部　拡張機能

42. [トランザクション MULTI/EXEC](part08-features/42-transactions.md)
43. [Pub/Sub](part08-features/43-pubsub.md)
44. [スクリプティング EVAL/Lua](part08-features/44-scripting.md)
45. [Functions とスクリプトエンジン](part08-features/45-functions.md)
46. [クライアントサイドキャッシュ](part08-features/46-client-tracking.md)
47. [ブロッキングコマンド](part08-features/47-blocking.md)
48. [ACL とセキュリティ](part08-features/48-acl.md)
49. [モジュールシステム](part08-features/49-modules.md)

### 第9部　可観測性・運用・ツール

50. [可観測性とデバッグ](part09-ops-tools/50-observability-debug.md)
51. [ハッシュ・チェックサム・ユーティリティ](part09-ops-tools/51-hashing-utils.md)
52. [クライアントツール](part09-ops-tools/52-client-tools.md)

---

> 全52章すべて執筆済み。コード引用は `9.1.0` タグ固定の GitHub リンクから該当行を直接参照できる。
