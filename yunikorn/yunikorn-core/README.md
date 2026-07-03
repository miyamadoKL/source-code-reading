# Apache YuniKorn core ソースコードリーディング

Apache YuniKorn core（[apache/yunikorn-core](https://github.com/apache/yunikorn-core)）のソースコードを読み解き、スケジューリングエンジンが「何のために、どういう処理を行うか」と「マルチテナントなリソース管理を支える工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：v1.8.0（コード引用はすべて [`v1.8.0` タグ](https://github.com/apache/yunikorn-core/tree/v1.8.0)に固定）
- **想定読者**：Go と分散スケジューリングの基礎がある中級エンジニア
- **読み方**：全体像からスケジューラ核心、高度なスケジューリング、統合層、可観測性、共通基盤まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v1.8.0` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
YuniKorn core は Kubernetes 向けユニバーサルスケジューラの中核であり、キュー階層、プレイスメントルール、プリエンプション、リザベーションによるギャングスケジューリングを実現する。

## 第0部 イントロダクション

1. [YuniKorn core の全体像](part00-intro/01-overview.md)
2. [起動とサービス結合](part00-intro/02-startup.md)

## 第1部 スケジューラ核心

3. [スケジューリングサイクル](part01-scheduler-core/03-scheduling-cycle.md)
4. [キュー階層と共有ポリシー](part01-scheduler-core/04-queue-hierarchy.md)
5. [アプリケーションとアロケーションリクエスト](part01-scheduler-core/05-application-and-allocation.md)
6. [ノード管理](part01-scheduler-core/06-node-management.md)
7. [プレイスメントルール](part01-scheduler-core/07-placement-rules.md)

## 第2部 高度なスケジューリング

8. [リザベーションとギャングスケジューリング](part02-advanced-scheduling/08-reservation-and-gang.md)
9. [プリエンプション](part02-advanced-scheduling/09-preemption.md)
10. [ユーザー・グループリソース制限](part02-advanced-scheduling/10-user-group-limits.md)

## 第3部 統合層

11. [RMProxy と scheduler-interface](part03-integration/11-rmproxy-and-scheduler-interface.md)
12. [イベントハンドリングと設定管理](part03-integration/12-events-and-config.md)
13. [パーティション管理](part03-integration/13-partition-management.md)

## 第4部 可観測性

14. [メトリクス](part04-observability/14-metrics.md)
15. [WebService REST API](part04-observability/15-webservice.md)

## 第5部 共通基盤

16. [リソースモデル](part05-common/16-resource-model.md)
17. [セキュリティと ACL](part05-common/17-security-and-acl.md)

---

> 全6部17章。
> 対象バージョンは Apache YuniKorn core v1.8.0。
> 各章のコード引用は `v1.8.0` タグに固定した GitHub リンクから該当行を直接参照できる。
