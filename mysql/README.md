# MySQL 8.4.10 ソースコードリーディング

MySQL 8.4.10（LTS）のソースコードを日本語で読み解くドキュメントである。
対象は GitHub タグ `mysql-8.4.10`。
コード引用はこのタグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。

MySQL は、SQL を解釈するサーバ層と、データの格納を担うプラガブルなストレージエンジンの二層からなる。
本書は、接続から構文解析、最適化、実行までのサーバ層をたどったうえで、現在のデファクトであるストレージエンジン **InnoDB** の実装を中心に深掘りする。
バッファプール、B+tree インデックス、トランザクションと MVCC、ロック、redo／undo ログ、クラッシュリカバリといった InnoDB の中核を、実コードに即して読む。
MyISAM など現代では主流でないストレージエンジンは、`handler` の別実装として軽く触れるにとどめる。

## 第0部　全体像と接続

1. [MySQL とは何か](part00-introduction/01-what-is-mysql.md)
2. [ソースツリーとビルド、クエリ処理の俯瞰](part00-introduction/02-source-tree-and-build.md)
3. [接続、スレッド、セッション](part00-introduction/03-connection-thread-session.md)

## 第1部　SQL レイヤ

4. [パーサ](part01-sql-layer/04-parser.md)
5. [クエリの解決と準備](part01-sql-layer/05-resolution-and-prepare.md)
6. [オプティマイザ（論理変換とクエリブロック）](part01-sql-layer/06-optimizer-transformations.md)
7. [オプティマイザ（join 順序とコストモデル）](part01-sql-layer/07-optimizer-join-cost.md)
8. [オプティマイザ（アクセスパスと range optimizer）](part01-sql-layer/08-optimizer-access-paths.md)
9. [エグゼキュータ（イテレータ実行モデル）](part01-sql-layer/09-executor-iterators.md)
10. [エグゼキュータ（結合、ソート、集約）](part01-sql-layer/10-executor-join-sort-agg.md)
11. [ハンドラ API とストレージエンジンプラグイン](part01-sql-layer/11-handler-api.md)

## 第2部　InnoDB の基盤

12. [InnoDB アーキテクチャ概観](part02-innodb-foundation/12-innodb-architecture.md)
13. [テーブルスペースとファイル空間管理](part02-innodb-foundation/13-tablespace-and-fsp.md)
14. [ページとレコードのフォーマット](part02-innodb-foundation/14-page-and-record-format.md)
15. [バッファプール](part02-innodb-foundation/15-buffer-pool.md)
16. [ミニトランザクション](part02-innodb-foundation/16-mini-transaction.md)

## 第3部　インデックスと行操作

17. [B+tree インデックス](part03-index-row/17-btree-index.md)
18. [レコード検索とカーソル](part03-index-row/18-search-and-cursor.md)
19. [行の挿入、更新、削除](part03-index-row/19-row-dml.md)
20. [チェンジバッファ](part03-index-row/20-change-buffer.md)
21. [アダプティブハッシュインデックス](part03-index-row/21-adaptive-hash-index.md)
22. [大きな値の格納（LOB）](part03-index-row/22-lob.md)

## 第4部　トランザクションと並行制御

23. [トランザクション管理](part04-transaction-concurrency/23-transaction-management.md)
24. [MVCC とリードビュー](part04-transaction-concurrency/24-mvcc-and-read-view.md)
25. [undo ログとパージ](part04-transaction-concurrency/25-undo-and-purge.md)
26. [ロック](part04-transaction-concurrency/26-locking.md)

## 第5部　ログ、リカバリ、永続化

27. [redo ログ](part05-log-recovery/27-redo-log.md)
28. [ダブルライトバッファとページフラッシュ](part05-log-recovery/28-doublewrite-and-flush.md)
29. [チェックポイントとクラッシュリカバリ](part05-log-recovery/29-checkpoint-and-recovery.md)

## 第6部　ディクショナリ、DDL、複製、運用

30. [データディクショナリ](part06-dictionary-ddl-ops/30-data-dictionary.md)
31. [オンライン DDL とインスタント DDL](part06-dictionary-ddl-ops/31-online-and-instant-ddl.md)
32. [バイナリログとレプリケーション](part06-dictionary-ddl-ops/32-binlog-and-replication.md)
33. [Performance Schema と監視](part06-dictionary-ddl-ops/33-performance-schema.md)
34. [他のストレージエンジン](part06-dictionary-ddl-ops/34-other-storage-engines.md)

> 対象バージョンは MySQL 8.4.10（LTS）。
> 各章のコード引用は `mysql-8.4.10` タグに固定した GitHub リンクから該当行を直接参照できる。
