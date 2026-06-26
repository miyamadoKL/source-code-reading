# TiDB エコシステム ソースコードリーディング

TiDB は、MySQL 互換のインターフェースを持つ分散 SQL データベースである。
SQL を解釈する計算層、データを Raft で複製する分散キーバリューストア、分析を高速化する列指向エンジンが連携し、1つの HTAP データベースを構成する。
本ディレクトリは、その主要コンポーネントを構成要素ごとに分けて読み解く。
対象バージョンは 8.5.6 にそろえる。

## 収録ドキュメント

| コンポーネント | 役割 | 言語 | 入口 |
|---|---|---|---|
| [TiDB（計算層）](tidb/README.md) | SQL の解析、最適化、分散実行を担う stateless な計算層 | Go | [目次](tidb/README.md) |
| [TiKV（分散 KV）](tikv/README.md) | Raft で複製する分散トランザクショナルキーバリューストア（下層に RocksDB） | Rust | [目次](tikv/README.md) |
| [TiFlash（列指向 OLAP）](tiflash/README.md) | Raft learner で複製を受け、分析クエリを高速化する列指向エンジン | C++ | [目次](tiflash/README.md) |
| [PD（Placement Driver）](pd/README.md) | TSO 発行、Region メタデータ管理、スケジューリング指示を担うクラスタマネージャ | Go | [目次](pd/README.md) |
| [TiCDC（CDC）](ticdc/README.md) | TiKV の変更ログをリアルタイムに下流（MySQL、Kafka、Cloud Storage 等）へ複製する変更データキャプチャ | Go | [目次](ticdc/README.md) |

> 各コンポーネントのコード引用は、対応するリポジトリの `v8.5.6` タグに固定する。
