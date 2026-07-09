# YuniKorn エコシステム ソースコードリーディング

YuniKorn は、Kubernetes 向けのユニバーサルリソーススケジューラである。
スケジューラ本体（core）、Kubernetes 連携（k8shim）、Web UI（web）が連携し、マルチテナントなリソース管理を実現する。
本ディレクトリは、その主要コンポーネントを構成要素ごとに分けて読み解く。
対象バージョンは v1.8.0 にそろえる。

## 収録ドキュメント

| コンポーネント | 役割 | 言語 | ライセンス |
|---|---|---|---|
| [YuniKorn core](yunikorn-core/README.md) | スケジューリングエンジン本体。キュー階層、プレイスメント、プリエンプションを担う | Go | Apache-2.0 |
| [YuniKorn k8shim](yunikorn-k8shim/README.md) | Kubernetes 連携レイヤー。Pod 監視、Admission Controller、Scheduler Plugin モードを担う | Go | Apache-2.0 |

> 各コンポーネントのコード引用は、対応するリポジトリの `v1.8.0` タグに固定する。
> 引用部分の著作権は各プロジェクトの著作権者に帰属する（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
