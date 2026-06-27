# Apache Iceberg ソースコードリーディング

Apache Iceberg（[apache/iceberg](https://github.com/apache/iceberg)）のソースコードを読み解き、Open Table Format の仕様が「何のために、どういう構造で実現されているか」と「大規模データレイクを支える設計上の工夫」を、仕様書と参照実装の両面からソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：1.11.0（コード引用はすべて [`apache-iceberg-1.11.0` タグ](https://github.com/apache/iceberg/tree/apache-iceberg-1.11.0)に固定）
- **想定読者**：Java と分散ストレージの基礎がある中級エンジニア
- **読み方**：仕様の全体像から型、パーティション、スナップショット、データ操作、スキャン、カタログ、ファイル I/O、拡張仕様、運用まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`apache-iceberg-1.11.0` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
Apache Iceberg は単独動作するソフトウェアではなく、大規模データ向けの Open Table Format の仕様とその参照実装であり、`api/` が公開インタフェース、`core/` が実装、`format/` が仕様書を担う。

## 第0部　全体像

1. [Iceberg とは何か](part00-overview/01-what-is-iceberg.md)
2. [テーブルメタデータとフォーマットバージョン](part00-overview/02-table-metadata.md)

## 第1部　型とスキーマ

3. [型システム](part01-type-and-schema/03-type-system.md)
4. [スキーマ進化](part01-type-and-schema/04-schema-evolution.md)

## 第2部　パーティショニング

5. [パーティション仕様と変換関数](part02-partitioning/05-partition-spec.md)
6. [ソート順序](part02-partitioning/06-sort-order.md)

## 第3部　スナップショットとマニフェスト

7. [スナップショットモデル](part03-snapshot/07-snapshot-model.md)
8. [マニフェストファイル](part03-snapshot/08-manifest-file.md)
9. [マニフェストリストとメタデータツリー](part03-snapshot/09-manifest-list.md)

## 第4部　データ操作

10. [追記と上書き](part04-data-operations/10-append-and-overwrite.md)
11. [行レベル更新と削除ファイル](part04-data-operations/11-row-level-deletes.md)
12. [コンパクションとファイルリライト](part04-data-operations/12-compaction-and-rewrite.md)

## 第5部　スキャンとフィルタリング

13. [式と述語](part05-scan/13-expressions-and-predicates.md)
14. [プランニングとスキャン](part05-scan/14-planning-and-scan.md)

## 第6部　カタログ

15. [カタログ抽象と TableOperations](part06-catalog/15-catalog-abstraction.md)
16. [REST カタログ](part06-catalog/16-rest-catalog.md)
17. [Hive、JDBC、Hadoop カタログ](part06-catalog/17-hive-jdbc-hadoop-catalog.md)

## 第7部　ファイル I/O とフォーマット統合

18. [FileIO 抽象とストレージ統合](part07-file-io/18-file-io.md)
19. [Parquet と ORC の読み書き](part07-file-io/19-parquet-and-orc.md)

## 第8部　拡張仕様

20. [Puffin 統計ファイル](part08-extensions/20-puffin-stats.md)
21. [View 仕様](part08-extensions/21-view-spec.md)

## 第9部　運用と観測

22. [メトリクス、イベント、暗号化](part09-ops/22-metrics-events-encryption.md)

---

> 全10部22章。
> コード引用は `apache-iceberg-1.11.0` タグに固定している。
> 引用コードの行末空白は `git diff --check` との整合のため rstrip で正規化している。
