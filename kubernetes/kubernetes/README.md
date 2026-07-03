# Kubernetes 本体 ソースコードリーディング

Kubernetes 本体（[kubernetes/kubernetes](https://github.com/kubernetes/kubernetes)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「大規模分散システムを支える工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：v1.36.2（コード引用はすべて [`v1.36.2` タグ](https://github.com/kubernetes/kubernetes/tree/v1.36.2)に固定）
- **想定読者**：Go と分散システムの基礎がある中級エンジニア
- **読み方**：全体像からコントロールプレーン、ノード、ネットワーク、ストレージ、拡張基盤、セキュリティまで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v1.36.2` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
Kubernetes は宣言的なコンテナオーケストレーションシステムであり、API サーバー、スケジューラ、コントローラマネージャ、kubelet、kube-proxy が連携して動作する。

## 第0部 イントロダクション

1. [Kubernetes の全体像](part00-intro/01-overview.md)
2. [起動とブートストラップ](part00-intro/02-startup.md)

## 第1部 API サーバー

3. [kube-apiserver のアーキテクチャ](part01-apiserver/03-apiserver-architecture.md)
4. [etcd ストレージと Cacher](part01-apiserver/04-etcd-and-cacher.md)
5. [API リクエスト処理](part01-apiserver/05-api-request-processing.md)

## 第2部 スケジューラ

6. [kube-scheduler の全体像](part02-scheduler/06-scheduler-overview.md)
7. [スケジューリングフレームワーク](part02-scheduler/07-scheduling-framework.md)
8. [スケジューリングプラグイン](part02-scheduler/08-scheduling-plugins.md)

## 第3部 コントローラマネージャ

9. [kube-controller-manager のアーキテクチャ](part03-controller-manager/09-controller-manager-architecture.md)
10. [主要コントローラ（ReplicaSet, Deployment, StatefulSet）](part03-controller-manager/10-workload-controllers.md)
11. [主要コントローラ（Job, CronJob, DaemonSet）](part03-controller-manager/11-batch-and-daemon-controllers.md)

## 第4部 kubelet

12. [kubelet のアーキテクチャとメインループ](part04-kubelet/12-kubelet-architecture.md)
13. [Pod ライフサイクルと CRI](part04-kubelet/13-pod-lifecycle-and-cri.md)
14. [ボリューム管理とリソース管理](part04-kubelet/14-volume-and-resource-management.md)

## 第5部 ネットワーク

15. [kube-proxy のアーキテクチャ](part05-network/15-kube-proxy-architecture.md)
16. [iptables/IPVS/nftables モード](part05-network/16-proxy-modes.md)

## 第6部 ストレージ

17. [PV/PVC 管理と Attach/Detach](part06-storage/17-pv-pvc-and-attach-detach.md)
18. [CSI 連携](part06-storage/18-csi-integration.md)

## 第7部 拡張基盤

19. [client-go と Informer](part07-extension/19-client-go-and-informer.md)
20. [CRD と Aggregation](part07-extension/20-crd-and-aggregation.md)
21. [Admission Webhook](part07-extension/21-admission-webhook.md)

## 第8部 セキュリティ

22. [Authentication と Authorization](part08-security/22-authentication-and-authorization.md)
23. [RBAC と ServiceAccount](part08-security/23-rbac-and-service-account.md)

---

> 全8部23章。
> 対象バージョンは Kubernetes v1.36.2。
> 各章のコード引用は `v1.36.2` タグに固定した GitHub リンクから該当行を直接参照できる。
> staging/ 配下のコードも `kubernetes/kubernetes` リポジトリ内のパスで引用する。
