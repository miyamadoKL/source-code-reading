# TiDB（計算層）ソースコードリーディング

TiDB（[pingcap/tidb](https://github.com/pingcap/tidb)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「分散環境での最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：8.5.6（コード引用はすべて [`v8.5.6` タグ](https://github.com/pingcap/tidb/tree/v8.5.6)に固定）
- **想定読者**：Go と一般的な DB の基礎がある中級エンジニア
- **読み方**：接続から最適化、分散実行、トランザクション、オンライン DDL まで TiDB 固有の実装を中心に読む構成で、第0部から順に読むことを想定する。

コード引用は、`v8.5.6` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
MySQL 互換のため SQL レイヤの基礎は MySQL 編と重なるので軽く扱い、分散プランナ、コプロセッサ押し下げ、Percolator トランザクション、非同期オンライン DDL といった TiDB 固有の実装を中心に読む。

## 第0部　全体像と接続

1. [TiDB とは何か](part00-overview/01-what-is-tidb.md)
2. [エコシステムとアーキテクチャ](part00-overview/02-architecture.md)
3. [ソースツリーと、1クエリの一生](part00-overview/03-source-tree-and-query-flow.md)

## 第1部　SQL フロントエンド

4. [パーサと AST](part01-frontend/04-parser-and-ast.md)
5. [プリペアドステートメントとプランキャッシュ](part01-frontend/05-prepared-and-plan-cache.md)
6. [式、型、スキーマ参照](part01-frontend/06-expression-and-schema.md)

## 第2部　オプティマイザ

7. [論理プランと論理最適化（RBO）](part02-optimizer/07-logical-optimization.md)
8. [統計情報とカーディナリティ推定](part02-optimizer/08-statistics-and-cardinality.md)
9. [コストモデルと物理最適化（CBO）](part02-optimizer/09-physical-optimization.md)
10. [コプロセッサ押し下げ](part02-optimizer/10-coprocessor-pushdown.md)
11. [エンジン選択と MPP プラン](part02-optimizer/11-engine-selection-and-mpp.md)

## 第3部　エグゼキュータ

12. [ベクトル化実行モデル](part03-executor/12-vectorized-execution.md)
13. [分散読み取りと結果の合流](part03-executor/13-distributed-read.md)
14. [結合、集約、ソートの実行](part03-executor/14-join-agg-sort.md)

## 第4部　KV エンコードとトランザクション

15. [行とインデックスの KV エンコード](part04-txn/15-kv-encoding.md)
16. [KV 抽象とスナップショット](part04-txn/16-kv-abstraction-and-snapshot.md)
17. [トランザクション調停（楽観、悲観、TSO）](part04-txn/17-transaction-coordination.md)
18. [Percolator 2PC を unistore で読む](part04-txn/18-percolator-2pc-unistore.md)
19. [async commit、1PC、GC](part04-txn/19-async-commit-and-gc.md)

## 第5部　スキーマ管理と分散基盤

20. [非同期オンライン DDL](part05-ddl-infra/20-online-ddl.md)
21. [ADD INDEX のバックフィルと分散タスク](part05-ddl-infra/21-add-index-backfill.md)
22. [PD クライアントと domain](part05-ddl-infra/22-pd-client-and-domain.md)

---

> 対象バージョンは TiDB 8.5.6。
> 各章のコード引用は `v8.5.6` タグに固定した GitHub リンクから該当行を直接参照できる。
