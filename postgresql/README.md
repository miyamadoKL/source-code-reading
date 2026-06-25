# PostgreSQL 18.4 ソースコードリーディング

PostgreSQL（[postgres/postgres](https://github.com/postgres/postgres)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：18.4（コード引用はすべて [`REL_18_4` タグ](https://github.com/postgres/postgres/tree/REL_18_4)に固定）
- **想定読者**：C と一般的な DB の基礎がある中級エンジニア
- **読み方**：プロセスモデルから WAL とリカバリまで基礎から順に積み上がる構成で、第0部から順に読むことを想定する。

コード引用は、`REL_18_4` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
末尾の付録では、2026 年に話題となった Linux カーネルの `PREEMPT_NONE` 廃止が PostgreSQL の性能へ与える影響を、スピンロックの実装に即して解説する。

## 第0部　導入とアーキテクチャ

1. [PostgreSQL とは何か](part00-introduction/01-what-is-postgresql.md)
2. [全体アーキテクチャとプロセスモデル](part00-introduction/02-architecture-overview.md)
3. [ソースツリーとビルド、問い合わせ処理の俯瞰](part00-introduction/03-source-tree-and-build.md)

## 第1部　プロセスとメモリ管理

4. [postmaster とプロセスの起動](part01-process-memory/04-postmaster-and-processes.md)
5. [共有メモリとプロセス間通信](part01-process-memory/05-shared-memory-and-ipc.md)
6. [メモリコンテキストと palloc](part01-process-memory/06-memory-contexts.md)
7. [ラッチとシグナル処理](part01-process-memory/07-latches-and-signals.md)

## 第2部　接続とプロトコル

8. [接続の確立と認証](part02-connection-protocol/08-connection-and-auth.md)
9. [フロントエンド／バックエンドプロトコルとメインループ](part02-connection-protocol/09-frontend-backend-protocol.md)

## 第3部　問い合わせ処理（フロントエンド）

10. [パーサ](part03-query-frontend/10-parser.md)
11. [アナライザ（意味解析）](part03-query-frontend/11-analyzer.md)
12. [リライタとルールシステム](part03-query-frontend/12-rewriter.md)
13. [プランナの全体像](part03-query-frontend/13-planner-overview.md)
14. [パス生成とコスト見積もり](part03-query-frontend/14-paths-and-costing.md)
15. [プランの実体化](part03-query-frontend/15-plan-creation.md)

## 第4部　エグゼキュータ

16. [エグゼキュータの骨格](part04-executor/16-executor-overview.md)
17. [スキャンノード](part04-executor/17-scan-nodes.md)
18. [結合ノード](part04-executor/18-join-nodes.md)
19. [集約、ソート、マテリアライズ](part04-executor/19-aggregation-sort.md)
20. [式評価と JIT](part04-executor/20-expression-evaluation.md)

## 第5部　ストレージとバッファ管理

21. [ストレージマネージャ](part05-storage-buffer/21-storage-manager.md)
22. [共有バッファとバッファ管理](part05-storage-buffer/22-buffer-manager.md)
23. [バッファ置換戦略とフリーリスト](part05-storage-buffer/23-buffer-replacement-strategy.md)
24. [ページとタプルのレイアウト](part05-storage-buffer/24-page-and-tuple-layout.md)

## 第6部　テーブルアクセスと MVCC

25. [テーブルアクセスメソッド](part06-table-mvcc/25-table-access-method.md)
26. [ヒープアクセス](part06-table-mvcc/26-heap-access.md)
27. [MVCC と可視性判定](part06-table-mvcc/27-mvcc-and-visibility.md)
28. [VACUUM と HOT](part06-table-mvcc/28-vacuum-and-hot.md)
29. [空き領域マップと可視性マップ](part06-table-mvcc/29-free-space-and-visibility-map.md)

## 第7部　インデックス

30. [インデックスアクセスメソッド](part07-indexes/30-index-access-method.md)
31. [B-tree](part07-indexes/31-btree.md)
32. [hash、GiST、GIN、BRIN](part07-indexes/32-other-indexes.md)

## 第8部　トランザクションと並行制御

33. [トランザクション管理](part08-transactions-concurrency/33-transaction-management.md)
34. [ロックマネージャ](part08-transactions-concurrency/34-lock-manager.md)
35. [軽量ロック（LWLock）](part08-transactions-concurrency/35-lightweight-locks.md)
36. [スピンロック](part08-transactions-concurrency/36-spinlocks.md)
37. [スナップショットと ProcArray](part08-transactions-concurrency/37-snapshots-and-procarray.md)

## 第9部　WAL とリカバリ

38. [WAL の仕組み](part09-wal-recovery/38-wal.md)
39. [チェックポイント](part09-wal-recovery/39-checkpoints.md)
40. [クラッシュリカバリと REDO](part09-wal-recovery/40-crash-recovery.md)
41. [レプリケーション](part09-wal-recovery/41-replication.md)

## 第10部　システムカタログと運用基盤

42. [システムカタログとキャッシュ](part10-catalog-utilities/42-system-catalogs-and-caches.md)
43. [バックグラウンドワーカーと autovacuum](part10-catalog-utilities/43-background-workers-autovacuum.md)
44. [統計情報とプランナ統計](part10-catalog-utilities/44-statistics-and-planner-stats.md)

## 付録

- [付録A　Linux カーネルの `PREEMPT_NONE` 廃止とスピンロックの性能問題](appendix/A01-preempt-none-and-spinlocks.md)

---

> 対象バージョンは PostgreSQL 18.4。
> 各章のコード引用は `REL_18_4` タグに固定した GitHub リンクから該当行を直接参照できる。
