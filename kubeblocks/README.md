# KubeBlocks ソースコードリーディング

KubeBlocks（[apecloud/kubeblocks](https://github.com/apecloud/kubeblocks)）のソースコードを読み解き、Kubernetes 上のデータベースオーケストレーションシステムが「何のために、どういう処理を行うか」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：v1.0.2（コード引用はすべて [`v1.0.2` タグ](https://github.com/apecloud/kubeblocks/tree/v1.0.2)に固定）
- **想定読者**：Go と Kubernetes の基礎がある中級エンジニア
- **読み方**：CRD 階層からコントローラ基盤、主要コントローラ、データ保護、運用拡張まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v1.0.2` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
KubeBlocks は Kubernetes の CRD とコントローラパターンを用いてデータベースのライフサイクルを管理する。

## 第0部 CRD 階層とデータモデル

1. [KubeBlocks の全体像と CRD 設計思想](part00-crd-overview/01-overview.md)
2. [ClusterDefinition と ComponentDefinition](part00-crd-overview/02-definitions.md)
3. [Cluster と Component の仕様](part00-crd-overview/03-cluster-and-component.md)
4. [InstanceSet: ポッド集合のワークロード抽象](part00-crd-overview/04-instanceset.md)

## 第1部 コントローラ基盤

5. [kubebuilderx: 拡張 Reconciler フレームワーク](part01-controller-base/05-kubebuilderx.md)
6. [graph エンジン: DAG による変換パイプライン](part01-controller-base/06-graph-engine.md)
7. [builder: リソース生成の統一インタフェース](part01-controller-base/07-builder.md)

## 第2部 主要コントローラ

8. [Cluster コントローラ: コンポーネントの編成](part02-main-controllers/08-cluster-controller.md)
9. [Component コントローラ: ワークロードの生成](part02-main-controllers/09-component-controller.md)
10. [InstanceSet コントローラ: ポッドライフサイクル管理](part02-main-controllers/10-instanceset-controller.md)
11. [Addon コントローラ: 機能拡張の動的ロード](part02-main-controllers/11-addon-controller.md)

## 第3部 データ保護

12. [Backup と Restore の CRD とコントローラ](part03-dataprotection/12-backup-restore.md)
13. [DataProtection の Action フレームワーク](part03-dataprotection/13-action-framework.md)

## 第4部 運用と拡張

14. [OpsRequest: データベース運用操作](part04-operations/14-opsrequest.md)
15. [パラメータ管理と動的再設定](part04-operations/15-parameter-management.md)
16. [kbagent: ライフサイクルアクション実行エージェント](part04-operations/16-kbagent.md)
17. [Component 合成: Definition から実行時コンポーネントへ](part04-operations/17-component-synthesis.md)

---

> 全4部17章。
> 対象バージョンは KubeBlocks v1.0.2。
> 各章のコード引用は `v1.0.2` タグに固定した GitHub リンクから該当行を直接参照できる。
> Kubernetes の基礎知識（Informer、CRD、コントローラパターン）は [kubernetes ドキュメント](../kubernetes/kubernetes/README.md) を前提とする。
