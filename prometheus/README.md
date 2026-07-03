# Prometheus ソースコードリーディング

Prometheus（[prometheus/prometheus](https://github.com/prometheus/prometheus)）のソースコードを読み解き、スクレイピング、時系列データベース、PromQL、アラート、リモート連携が「何のために、どういう処理を行うか」と「高速化、最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：v3.12.0（コード引用はすべて [`v3.12.0` タグ](https://github.com/prometheus/prometheus/tree/v3.12.0)に固定）
- **想定読者**：Go と分散システムの基礎がある中級エンジニア
- **読み方**：スクレイピングからストレージ、クエリ、ルール、外部連携へと積み上がる構成で、第0部から順に読むことを想定する。

コード引用は、本文中の `[path L開始-L終了](https://github.com/prometheus/prometheus/blob/v3.12.0/...)` 形式のリンクから GitHub 上の該当箇所を直接参照できる。

## 第0部　概観

1. [アーキテクチャ全体像](part00-overview/01-architecture-overview.md)
2. [設定と起動フロー](part00-overview/02-config-and-startup.md)

## 第1部　スクレイピング

3. [スクレイピング機構](part01-scrape/03-scrape-mechanism.md)
4. [サービスディスカバリー](part01-scrape/04-service-discovery.md)

## 第2部　ストレージ（TSDB）

5. [TSDB アーキテクチャ](part02-tsdb/05-tsdb-architecture.md)
6. [Head と WAL](part02-tsdb/06-head-and-wal.md)
7. [ブロックフォーマットとコンパクション](part02-tsdb/07-block-format-and-compaction.md)
8. [クエリと読み出し](part02-tsdb/08-query-and-read.md)

## 第3部　PromQL

9. [PromQL パーサーと AST](part03-promql/09-promql-parser-and-ast.md)
10. [PromQL エンジン](part03-promql/10-promql-engine.md)
11. [関数とアグリゲーション](part03-promql/11-functions-and-aggregation.md)

## 第4部　ルールとアラート

12. [ルール評価](part04-rules/12-rule-evaluation.md)
13. [アラート通知](part04-rules/13-alert-notification.md)

## 第5部　外部連携

14. [リモート書き込み・読み出し](part05-external/14-remote-write-and-read.md)
15. [HTTP API](part05-external/15-http-api.md)
16. [promtool](part05-external/16-promtool.md)

---

> 執筆状況：全16章のうち執筆中（コミット前）
> コード引用はすべて [`v3.12.0`](https://github.com/prometheus/prometheus/tree/v3.12.0) タグに固定。
