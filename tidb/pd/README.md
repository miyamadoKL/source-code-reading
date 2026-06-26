# PD（Placement Driver）ソースコードリーディング

PD（[tikv/pd](https://github.com/tikv/pd)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「分散スケジューリングを支える工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：8.5.6（コード引用はすべて [`v8.5.6` タグ](https://github.com/tikv/pd/tree/v8.5.6)に固定）
- **想定読者**：Go と分散システムの基礎がある中級エンジニア
- **読み方**：TSO とクラスタメタデータの基盤から、スケジューリングフレームワーク、組み込みスケジューラ、高可用性と運用まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v8.5.6` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
PD は TiDB エコシステムのクラスタマネージャであり、TSO の発行、Region メタデータの管理、スケジューリング指示の生成を担う。

## 第0部　全体像

1. [PD とは何か](part00-overview/01-what-is-pd.md)
2. [サーバーアーキテクチャ](part00-overview/02-server-architecture.md)
3. [TiDB、TiKV との関係](part00-overview/03-relationship-with-tidb-tikv.md)

## 第1部　TSO

4. [TSO の仕組みと GlobalAllocator](part01-tso/04-tso-and-global-allocator.md)
5. [タイムスタンプの永続化と安全性](part01-tso/05-tso-persistence.md)
6. [Local TSO とマイクロサービス化](part01-tso/06-local-tso-and-microservice.md)

## 第2部　クラスタメタデータ

7. [Store の管理とストアハートビート](part02-metadata/07-store-management.md)
8. [Region メタデータと RegionTree](part02-metadata/08-region-and-region-tree.md)
9. [Region ハートビートと統計収集](part02-metadata/09-region-heartbeat.md)

## 第3部　スケジューリング基盤

10. [Coordinator とスケジューリングループ](part03-scheduling/10-coordinator.md)
11. [Operator と Step](part03-scheduling/11-operator-and-step.md)
12. [OperatorController と完了追跡](part03-scheduling/12-operator-controller.md)
13. [Placement Rules と制約充足](part03-scheduling/13-placement-rules.md)

## 第4部　組み込みスケジューラとチェッカー

14. [balance-leader スケジューラ](part04-schedulers/14-balance-leader.md)
15. [balance-region スケジューラ](part04-schedulers/15-balance-region.md)
16. [hot-region スケジューラと統計](part04-schedulers/16-hot-region.md)
17. [ReplicaChecker と RuleChecker](part04-schedulers/17-replica-and-rule-checker.md)
18. [MergeChecker と分割・結合](part04-schedulers/18-merge-checker.md)

## 第5部　高可用性と運用

19. [etcd とリーダー選出](part05-ha-ops/19-etcd-and-leader-election.md)
20. [ストレージ層（etcd と LevelDB）](part05-ha-ops/20-storage.md)
21. [マイクロサービスアーキテクチャ](part05-ha-ops/21-microservice.md)
22. [PD Client とサービスディスカバリ](part05-ha-ops/22-pd-client.md)
23. [pd-ctl と運用](part05-ha-ops/23-pd-ctl-and-ops.md)

---

> 対象バージョンは PD 8.5.6。
> 各章のコード引用は `v8.5.6` タグに固定した GitHub リンクから該当行を直接参照できる。
