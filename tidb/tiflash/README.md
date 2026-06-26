# TiFlash（列指向 OLAP）ソースコードリーディング

TiFlash（[pingcap/tiflash](https://github.com/pingcap/tiflash)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「分析クエリを速くする工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：8.5.6（コード引用はすべて [`v8.5.6` タグ](https://github.com/pingcap/tiflash/tree/v8.5.6)に固定）
- **想定読者**：C++ と列指向データベースの基礎がある中級エンジニア
- **読み方**：列指向ストレージ DeltaTree から Raft learner、クエリ実行エンジン、MPP まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v8.5.6` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
TiFlash は TiDB エコシステムの列指向 OLAP エンジンであり、TiKV から Raft learner として複製を受けて行データを列指向に変換し、MPP で分析クエリを高速化する。

## 第0部　全体像

1. [TiFlash とは何か](part00-overview/01-what-is-tiflash.md)
2. [ClickHouse 派生のアーキテクチャ](part00-overview/02-architecture.md)
3. [TiDB、TiKV との関係（MPP と learner replica）](part00-overview/03-relationship-with-tidb-tikv.md)

## 第1部　列指向ストレージ DeltaTree

4. [なぜ列指向が OLAP に速いか](part01-deltatree/04-why-columnar.md)
5. [DeltaMergeStore 概観](part01-deltatree/05-deltamergestore.md)
6. [Segment](part01-deltatree/06-segment.md)
7. [Delta レイヤと ColumnFile](part01-deltatree/07-delta-and-columnfile.md)
8. [Stable レイヤと DTFile](part01-deltatree/08-stable-and-dtfile.md)
9. [Delta Merge と MVCC](part01-deltatree/09-delta-merge-and-mvcc.md)
10. [PageStorage](part01-deltatree/10-pagestorage.md)

## 第2部　Raft learner と書き込み経路

11. [KVStore と Region](part02-raft-learner/11-kvstore-and-region.md)
12. [Raft log の適用と行から列への変換](part02-raft-learner/12-apply-and-row-to-column.md)
13. [learner read と読み取り一貫性](part02-raft-learner/13-learner-read.md)

## 第3部　クエリ実行エンジン

14. [ベクトル化実行（Block、IColumn、DataType）](part03-engine/14-vectorized-block.md)
15. [パイプライン実行モデル（Operators）](part03-engine/15-pipeline-operators.md)
16. [集約と join の列指向実装](part03-engine/16-aggregation-and-join.md)
17. [式評価](part03-engine/17-expression-evaluation.md)

## 第4部　MPP

18. [MPP とは](part04-mpp/18-what-is-mpp.md)
19. [MPPTask と Exchange](part04-mpp/19-mpptask-and-exchange.md)
20. [MPP の実行フローと TiDB 連携](part04-mpp/20-mpp-flow-and-tidb.md)

## 第5部　分析最適化と運用

21. [フィルタ押し下げと late materialization](part05-ops/21-pushdown-and-late-materialization.md)
22. [S3 disaggregated と GC、運用](part05-ops/22-disaggregated-and-ops.md)

---

> 対象バージョンは TiFlash 8.5.6。
> 各章のコード引用は `v8.5.6` タグに固定した GitHub リンクから該当行を直接参照できる。
