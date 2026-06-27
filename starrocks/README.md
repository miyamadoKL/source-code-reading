# StarRocks ソースコードリーディング

StarRocks（[StarRocks/starrocks](https://github.com/StarRocks/starrocks)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「MPP 分散分析データベースを支える工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：4.1.1（コード引用はすべて [`4.1.1` タグ](https://github.com/StarRocks/starrocks/tree/4.1.1)に固定）
- **想定読者**：Java、C++ と分散システムの基礎がある中級エンジニア
- **読み方**：全体像から SQL 解析、プランニング、実行エンジン、列指向データ、ストレージ、Lake モード、データ取り込み、運用まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`4.1.1` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
StarRocks は Apache Doris をフォークした MPP 分散分析データベースであり、FE（Java）が SQL 解析と Cascades CBO を、BE（C++）がベクトル化パイプライン実行と列指向ストレージを担う。

## 第0部　全体像

1. [StarRocks とは何か](part00-overview/01-what-is-starrocks.md)
2. [FE の起動とメタデータ管理](part00-overview/02-fe-startup-and-metadata.md)
3. [BE の起動とサービス層](part00-overview/03-be-startup-and-services.md)

## 第1部　SQL 解析

4. [SQL パーサーと AST](part01-sql-analysis/04-sql-parser-and-ast.md)
5. [Analyzer と意味解析](part01-sql-analysis/05-analyzer.md)

## 第2部　クエリ最適化

6. [Cascades オプティマイザと Memo](part02-planning/06-cascades-optimizer-and-memo.md)
7. [変換ルールと実装ルール](part02-planning/07-transformation-and-implementation-rules.md)
8. [コストモデルと統計情報](part02-planning/08-cost-model-and-statistics.md)
9. [分散プランと Fragment](part02-planning/09-distributed-plan-and-fragment.md)

## 第3部　パイプライン実行エンジン

10. [Pipeline 実行モデル](part03-execution/10-pipeline-execution-model.md)
11. [Scan オペレーターとデータアクセス](part03-execution/11-scan-operators.md)
12. [Join と RuntimeFilter](part03-execution/12-join-and-runtime-filter.md)
13. [Aggregate、Sort、Exchange](part03-execution/13-aggregate-sort-exchange.md)

## 第4部　列指向データモデル

14. [Column と Chunk](part04-data/14-column-and-chunk.md)
15. [式評価と関数](part04-data/15-expression-and-functions.md)

## 第5部　ストレージエンジン

16. [Tablet、Rowset とデータモデル](part05-storage/16-tablet-rowset-and-data-models.md)
17. [Segment ファイルフォーマット](part05-storage/17-segment-file-format.md)
18. [インデックスサブシステム](part05-storage/18-index-subsystem.md)
19. [Compaction と Primary Key 更新](part05-storage/19-compaction-and-primary-key.md)

## 第6部　Shared-Data アーキテクチャ

20. [Lake モードと StarOS 連携](part06-lake/20-lake-mode-and-staros.md)
21. [Lake トランザクションと Compaction](part06-lake/21-lake-transaction-and-compaction.md)

## 第7部　データ取り込みとマテリアライズドビュー

22. [ロードパス](part07-ingestion/22-load-paths.md)
23. [マテリアライズドビューとクエリリライト](part07-ingestion/23-materialized-view-and-rewrite.md)

## 第8部　ランタイムと運用

24. [メモリ管理とデータキャッシュ](part08-ops/24-memory-management-and-cache.md)
25. [Resource Group と Warehouse](part08-ops/25-resource-group-and-warehouse.md)
26. [Tablet スケジューラとレプリカ管理](part08-ops/26-tablet-scheduler-and-replica.md)

## 第9部　外部連携

27. [Connector と外部カタログ](part09-connector/27-connector-and-external-catalog.md)

---

> 全10部27章。
> コード引用は `4.1.1` タグに固定している。
