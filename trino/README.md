# Trino ソースコードリーディング

Trino（[trinodb/trino](https://github.com/trinodb/trino)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「分散 SQL クエリエンジンを支える工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：482（コード引用はすべて [`482` タグ](https://github.com/trinodb/trino/tree/482)に固定）
- **ライセンス**：Apache-2.0（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：Java と分散システムの基礎がある中級エンジニア
- **読み方**：全体像からパース、プランニング、実行エンジン、データ表現、コネクタ、運用まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`482` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
Trino は Coordinator と Worker からなる MPP（Massively Parallel Processing）アーキテクチャの分散 SQL クエリエンジンであり、多種多様なデータソースに対して高速な対話型クエリを提供する。

## 第0部　全体像

1. [Trino とは何か](part00-overview/01-what-is-trino.md)
2. [サーバーアーキテクチャ](part00-overview/02-server-architecture.md)
3. [Plugin と SPI](part00-overview/03-plugin-and-spi.md)

## 第1部　パースと意味解析

4. [SQL パーサーと AST](part01-parsing/04-sql-parser-and-ast.md)
5. [Analyzer と意味解析](part01-parsing/05-analyzer.md)

## 第2部　プランニングと最適化

6. [LogicalPlanner と IR](part02-planning/06-logical-planner-and-ir.md)
7. [Iterative Optimizer と Rule](part02-planning/07-iterative-optimizer.md)
8. [述語プッシュダウンと結合最適化](part02-planning/08-predicate-and-join-optimization.md)
9. [コスト見積もりと統計情報](part02-planning/09-cost-and-statistics.md)
10. [分散プラン生成と Exchange](part02-planning/10-distributed-plan.md)

## 第3部　分散実行エンジン

11. [クエリライフサイクルと DispatchManager](part03-execution/11-query-lifecycle.md)
12. [Stage と Task のスケジューリング](part03-execution/12-stage-and-task-scheduling.md)
13. [Driver と Operator パイプライン](part03-execution/13-driver-and-operator.md)
14. [HashJoin と LookupSource](part03-execution/14-hash-join.md)
15. [集約と Window 関数](part03-execution/15-aggregation-and-window.md)
16. [Exchange と OutputBuffer](part03-execution/16-exchange-and-output-buffer.md)
17. [メモリ管理と Spill](part03-execution/17-memory-and-spill.md)
18. [Fault Tolerant Execution](part03-execution/18-fault-tolerant-execution.md)

## 第4部　データ表現と型システム

19. [Page と Block のデータモデル](part04-data/19-page-and-block.md)
20. [型システムと関数レジストリ](part04-data/20-type-system-and-functions.md)

## 第5部　コネクタとデータソース

21. [Connector SPI の詳細](part05-connector/21-connector-spi-detail.md)
22. [Hive Connector と Metastore](part05-connector/22-hive-connector.md)
23. [Iceberg Connector](part05-connector/23-iceberg-connector.md)
24. [Delta Lake Connector](part05-connector/24-delta-lake-connector.md)
25. [JDBC Connector ファミリーと Pushdown](part05-connector/25-jdbc-connector.md)
26. [Kafka Connector](part05-connector/26-kafka-connector.md)

## 第6部　運用と可観測性

27. [リソースグループとクエリキューイング](part06-ops/27-resource-groups.md)
28. [障害検出とセキュリティ](part06-ops/28-failure-detection-and-security.md)

---

> 全7部28章。
> 対象バージョンは Trino 482。
> 各章のコード引用は `482` タグに固定した GitHub リンクから該当行を直接参照できる。
