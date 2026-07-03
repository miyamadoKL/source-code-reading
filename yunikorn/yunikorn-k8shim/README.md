# Apache YuniKorn k8shim ソースコードリーディング

Apache YuniKorn k8shim（[apache/yunikorn-k8shim](https://github.com/apache/yunikorn-k8shim)）のソースコードを読み解き、Kubernetes 連携レイヤーが「何のために、どういう処理を行うか」と「Kubernetes クラスタでのリソース管理を支える工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：v1.8.0（コード引用はすべて [`v1.8.0` タグ](https://github.com/apache/yunikorn-k8shim/tree/v1.8.0)に固定）
- **想定読者**：Go と Kubernetes の基礎がある中級エンジニア
- **読み方**：全体像からキャッシュ層、Kubernetes 連携、統合と設定まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v1.8.0` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
YuniKorn k8shim は Kubernetes 向けのスケジューラ連携レイヤーであり、Pod の監視、Admission Controller によるメタデータ注入、Scheduler Plugin モードによる Kubernetes Scheduling Framework 連携を実現する。

## 第0部 イントロダクション

1. [yunikorn-k8shim の全体像](part00-intro/01-overview.md)
2. [起動とイベントディスパッチ](part00-intro/02-startup-and-dispatcher.md)

## 第1部 キャッシュと状態管理

3. [Context とキャッシュレイヤー](part01-cache/03-context-and-cache.md)
4. [アプリケーション状態機械](part01-cache/04-application-state-machine.md)
5. [タスク状態管理とプレースホルダー](part01-cache/05-task-and-placeholder.md)

## 第2部 Kubernetes 連携

6. [K8s API クライアントと Informer](part02-k8s/06-k8s-client-and-informer.md)
7. [Admission Controller](part02-k8s/07-admission-controller.md)
8. [Scheduler Plugin モード](part02-k8s/08-scheduler-plugin.md)

## 第3部 統合と設定

9. [scheduler-interface と core 連携](part03-integration/09-scheduler-interface.md)
10. [設定管理](part03-integration/10-configuration.md)

---

> 全4部10章。
> 対象バージョンは Apache YuniKorn k8shim v1.8.0。
> 各章のコード引用は `v1.8.0` タグに固定した GitHub リンクから該当行を直接参照できる。
