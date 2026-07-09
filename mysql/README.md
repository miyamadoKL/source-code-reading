# MySQL 8.4.10 ソースコードリーディング

MySQL（[mysql/mysql-server](https://github.com/mysql/mysql-server)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「高速化、最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：8.4.10（LTS、コード引用はすべて [`mysql-8.4.10` タグ](https://github.com/mysql/mysql-server/tree/mysql-8.4.10)に固定）
- **ライセンス**：GPL-2.0（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：C++ と DB の基礎がある中級エンジニア
- **読み方**：SQL を解釈するサーバ層から InnoDB 内部へ基礎から順に積み上がる構成で、第0部から順に読むことを想定する。

コード引用は、`mysql-8.4.10` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
InnoDB を中心に深く読み、MyISAM など現代では主流でないストレージエンジンは `handler` の別実装として簡単に扱うにとどめる。

## 第0部　全体像と接続

1. [MySQL とは何か](part00-introduction/01-what-is-mysql.md)
2. [ソースツリーとビルド、クエリ処理の俯瞰](part00-introduction/02-source-tree-and-build.md)
3. [接続、スレッド、セッション](part00-introduction/03-connection-thread-session.md)
4. [接続の確立と認証、Classic Protocol](part00-introduction/04-connection-and-protocol.md)

## 第1部　SQL レイヤ

5. [パーサ](part01-sql-layer/05-parser.md)
6. [MEM_ROOT と文単位のメモリ寿命](part01-sql-layer/06-mem-root.md)
7. [クエリの解決と準備](part01-sql-layer/07-resolution-and-prepare.md)
8. [式評価（Item の実行時モデル）](part01-sql-layer/08-expression-evaluation.md)
9. [オプティマイザ（論理変換とクエリブロック）](part01-sql-layer/09-optimizer-transformations.md)
10. [オプティマイザ（join 順序とコストモデル）](part01-sql-layer/10-optimizer-join-cost.md)
11. [オプティマイザ（アクセスパスと range optimizer）](part01-sql-layer/11-optimizer-access-paths.md)
12. [統計情報とカーディナリティ推定](part01-sql-layer/12-statistics-and-cardinality.md)
13. [エグゼキュータ（イテレータ実行モデル）](part01-sql-layer/13-executor-iterators.md)
14. [エグゼキュータ（結合、ソート、集約）](part01-sql-layer/14-executor-join-sort-agg.md)
15. [ハンドラ API とストレージエンジンプラグイン](part01-sql-layer/15-handler-api.md)
16. [メタデータロック（MDL）](part01-sql-layer/16-metadata-locking.md)

## 第2部　InnoDB の基盤

17. [InnoDB アーキテクチャ概観](part02-innodb-foundation/17-innodb-architecture.md)
18. [テーブルスペースとファイル空間管理](part02-innodb-foundation/18-tablespace-and-fsp.md)
19. [ページとレコードのフォーマット](part02-innodb-foundation/19-page-and-record-format.md)
20. [バッファプール](part02-innodb-foundation/20-buffer-pool.md)
21. [ミニトランザクション](part02-innodb-foundation/21-mini-transaction.md)

## 第3部　インデックスと行操作

22. [B+tree インデックス](part03-index-row/22-btree-index.md)
23. [レコード検索とカーソル](part03-index-row/23-search-and-cursor.md)
24. [行の挿入、更新、削除](part03-index-row/24-row-dml.md)
25. [チェンジバッファ](part03-index-row/25-change-buffer.md)
26. [アダプティブハッシュインデックス](part03-index-row/26-adaptive-hash-index.md)
27. [大きな値の格納（LOB）](part03-index-row/27-lob.md)

## 第4部　トランザクションと並行制御

28. [トランザクション管理](part04-transaction-concurrency/28-transaction-management.md)
29. [MVCC とリードビュー](part04-transaction-concurrency/29-mvcc-and-read-view.md)
30. [undo ログとパージ](part04-transaction-concurrency/30-undo-and-purge.md)
31. [ロック](part04-transaction-concurrency/31-locking.md)

## 第5部　ログ、リカバリ、永続化

32. [redo ログ](part05-log-recovery/32-redo-log.md)
33. [ダブルライトバッファとページフラッシュ](part05-log-recovery/33-doublewrite-and-flush.md)
34. [チェックポイントとクラッシュリカバリ](part05-log-recovery/34-checkpoint-and-recovery.md)

## 第6部　ディクショナリ、DDL、複製、運用

35. [データディクショナリ](part06-dictionary-ddl-ops/35-data-dictionary.md)
36. [オンライン DDL とインスタント DDL](part06-dictionary-ddl-ops/36-online-and-instant-ddl.md)
37. [バイナリログとレプリケーション](part06-dictionary-ddl-ops/37-binlog-and-replication.md)
38. [Performance Schema と監視](part06-dictionary-ddl-ops/38-performance-schema.md)
39. [他のストレージエンジン](part06-dictionary-ddl-ops/39-other-storage-engines.md)
40. [グループレプリケーション](part06-dictionary-ddl-ops/40-group-replication.md)

---

> 対象バージョンは MySQL 8.4.10（LTS）。
> 各章のコード引用は `mysql-8.4.10` タグに固定した GitHub リンクから該当行を直接参照できる。
