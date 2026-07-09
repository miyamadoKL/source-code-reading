# TiDB エコシステム ソースコードリーディング

TiDB は、MySQL 互換のインターフェースを持つ分散 SQL データベースである。
SQL を解釈する計算層、データを Raft で複製する分散キーバリューストア、分析を高速化する列指向エンジンが連携し、1つの HTAP データベースを構成する。
本ディレクトリは、その主要コンポーネントを構成要素ごとに分けて読み解く。
対象バージョンは 8.5.6 にそろえる。

## 収録ドキュメント

| コンポーネント | 役割 | 言語 | ライセンス |
|---|---|---|---|
| [TiDB（計算層）](tidb/README.md) | SQL の解析、最適化、分散実行を担う stateless な計算層 | Go | Apache-2.0 |
| [TiKV（分散 KV）](tikv/README.md) | Raft で複製する分散トランザクショナルキーバリューストア（下層に RocksDB） | Rust | Apache-2.0 |
| [TiFlash（列指向 OLAP）](tiflash/README.md) | Raft learner で複製を受け、分析クエリを高速化する列指向エンジン | C++ | Apache-2.0 |
| [PD（Placement Driver）](pd/README.md) | TSO 発行、Region メタデータ管理、スケジューリング指示を担うクラスタマネージャ | Go | Apache-2.0 |
| [TiCDC（CDC）](ticdc/README.md) | TiKV の変更ログをリアルタイムに下流（MySQL、Kafka、Cloud Storage 等）へ複製する変更データキャプチャ | Go | Apache-2.0 |

> 各コンポーネントのコード引用は、対応するリポジトリの `v8.5.6` タグに固定する。
> 引用部分の著作権は各プロジェクトの著作権者に帰属する（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
