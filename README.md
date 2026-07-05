# source-code-reading

著名な OSS のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「高速化・最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメント群を収めたリポジトリである。

特定バージョンに固定した GitHub リンクでソースを引用し、基礎から順に積み上がる構成で、対象 OSS の内部実装を読んで理解できることを目指す。

## 収録ドキュメント

| OSS | 対象バージョン | 概要 | 入口 |
|---|---|---|---|
| [RocksDB](rocksdb/README.md) | v11.1.1 | LSM-tree ベースの組み込み永続キーバリューストア。全11部・52章。 | [目次](rocksdb/README.md) |
| [Valkey](valkey/README.md) | 9.1.0 | RESP プロトコルで話すインメモリのデータ構造ストア。全10部・52章。 | [目次](valkey/README.md) |
| [PostgreSQL](postgresql/README.md) | 18.4 | MVCC と WAL を備えるリレーショナルデータベース。全11部・44章と付録。 | [目次](postgresql/README.md) |
| [MySQL](mysql/README.md) | 8.4.10 | プラガブルなストレージエンジンを持つリレーショナルデータベース。InnoDB を中心に詳説。全7部・40章。 | [目次](mysql/README.md) |
| [TiDB エコシステム](tidb/README.md) | 8.5.6 | MySQL 互換の分散 SQL データベース。計算層（TiDB）、分散 KV（TiKV）、列指向 OLAP（TiFlash）を分冊で読む。 | [目次](tidb/README.md) |
| [Trino](trino/README.md) | 482 | MPP 分散 SQL クエリエンジン。パーサーからプランナー、実行エンジン、Connector まで全7部28章。 | [目次](trino/README.md) |
| [StarRocks](starrocks/README.md) | 4.1.1 | MPP 分散分析データベース。Cascades CBO、ベクトル化パイプライン実行、列指向ストレージ、Lake モードまで全10部27章。 | [目次](starrocks/README.md) |
| [Apache Iceberg](iceberg/README.md) | 1.11.0 | Open Table Format の仕様と参照実装。型、スナップショット、マニフェスト、カタログ、Spark/Flink 連携まで全11部24章。 | [目次](iceberg/README.md) |
| [OpenSSH](openssh/README.md) | V_10_3_P1 | SSH プロトコルの標準実装。トランスポート層、認証、チャネル、権限分離まで全5部12章。 | [目次](openssh/README.md) |
| [Prometheus](prometheus/README.md) | v3.12.0 | プル型監視システムと時系列データベース。スクレイプ、TSDB、PromQL、アラート、リモート連携まで全6部16章。 | [目次](prometheus/README.md) |
| [nginx](nginx/README.md) | 1.31.2 | イベント駆動の Web サーバーとリバースプロキシ。コア基盤、イベントエンジン、HTTP エンジン、upstream、HTTP/2、HTTP/3 まで全6部18章。 | [目次](nginx/README.md) |
| [Apache Spark](spark/README.md) | v4.1.2 | 分散データ処理フレームワーク。RDD、スケジューリング、Catalyst/Tungsten、Structured Streaming、PySpark、Kubernetes/YuniKorn 連携まで全10部28章。 | [目次](spark/README.md) |
| [YuniKorn エコシステム](yunikorn/README.md) | v1.8.0 | Kubernetes 向けユニバーサルリソーススケジューラ。core（キュー階層、プレイスメント、プリエンプション）を分冊で読む。全6部17章。 | [目次](yunikorn/README.md) |
| [Kubernetes](kubernetes/README.md) | v1.36.2 | コンテナオーケストレーター。apiserver、scheduler、controller-manager、kubelet、kube-proxy、ストレージ、client-go、RBAC まで分冊で読む。全8部23章。 | [目次](kubernetes/README.md) |
| [KubeBlocks](kubeblocks/README.md) | v1.0.2 | Kubernetes 上のデータベース運用オペレーター。CRD 3層モデル、graph エンジン、InstanceSet、DataProtection、kbagent まで全5部17章。 | [目次](kubeblocks/README.md) |
| [Apache Kafka](kafka/README.md) | 4.3.1 | 分散イベントストリーミングプラットフォーム。ネットワーク層、プロデューサー、ログストレージ、レプリケーション、KRaft、コンシューマー、各種 Coordinator まで全8部24章。 | [目次](kafka/README.md) |
| [Ceph](ceph/README.md) | 20.2.2 | 統合分散ストレージ。共通基盤、Messenger、CRUSH、Monitor/Paxos、OSD/PG、BlueStore、Objecter/RBD/CephFS/RGW まで全8部26章。 | [目次](ceph/README.md) |

今後、他の OSS のソースコード読解ドキュメントを `<oss-name>/` 配下に追加していく。

## このリポジトリの方針

- 各 OSS は専用ディレクトリ（例 `rocksdb/`）に格納し、その配下の `README.md` を目次とする。
- コード引用はバージョン固定の GitHub リンク（例 `.../blob/v11.1.1/...#Lxx-Lyy`）から該当箇所を直接参照できる。引用元のローカルパスは含めない。
- 想定読者は対象分野の基礎があるエンジニア。概念から実装の細部、最適化の工夫まで踏み込む。
- 日本語の技術文書としての規範に従う（一文一行、用語統一、過剰な演出の排除）。

## 引用とライセンス

各ドキュメントは対象 OSS のソースコードを引用する。引用部分の著作権およびライセンスは、各 OSS の規定に従う。
