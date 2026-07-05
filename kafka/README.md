# Apache Kafka ソースコードリーディング

Apache Kafka（[apache/kafka](https://github.com/apache/kafka)）のソースコードを読み解き、分散ログの実装と高速化の工夫を日本語で解説するドキュメントである。

- **対象バージョン**：4.3.1（コード引用はすべて [`4.3.1` タグ](https://github.com/apache/kafka/tree/4.3.1)に固定）
- **想定読者**：Java/Scala と分散システムの基礎がある中級エンジニア
- **読み方**：ネットワーク層から始め、プロデューサー・ログストレージ・レプリケーション・KRaft・コンシューマーと下から積み上げて読む

コード引用は「バージョン固定の GitHub リンク」＋「コードブロック」の2点セットで示す。
本書は ZooKeeper を廃止した KRaft 専用アーキテクチャ（4.x 系）を前提とする。

## 第0部　全体像

1. [Kafka のアーキテクチャと KRaft 時代のブローカー起動](part00-overview/01-architecture-kraft.md)

## 第1部　ネットワーク層とリクエスト処理

2. [SocketServer とリアクター（Acceptor と Processor）](part01-network/02-socketserver.md)
3. [RequestChannel と KafkaRequestHandler の処理パイプライン](part01-network/03-request-pipeline.md)
4. [KafkaApis による API ディスパッチ](part01-network/04-kafkaapis.md)

## 第2部　プロデューサークライアント

5. [RecordAccumulator と BufferPool によるバッチング](part02-producer/05-record-accumulator.md)
6. [Sender と冪等プロデューサー](part02-producer/06-sender-idempotence.md)

## 第3部　ログストレージ

7. [レコードフォーマットと MemoryRecords / FileRecords](part03-storage/07-record-format.md)
8. [LogSegment とインデックス](part03-storage/08-logsegment-index.md)
9. [UnifiedLog と LocalLog の追記と読み出し](part03-storage/09-unifiedlog.md)
10. [LogManager とログのライフサイクル](part03-storage/10-logmanager.md)
11. [LogCleaner によるコンパクション](part03-storage/11-logcleaner.md)
12. [ProducerStateManager と冪等・トランザクション状態](part03-storage/12-producer-state.md)

## 第4部　レプリケーション

13. [Partition と ISR、High Watermark](part04-replication/13-partition-isr.md)
14. [ReplicaManager による produce と fetch](part04-replication/14-replicamanager.md)
15. [ReplicaFetcherThread とフォロワー複製](part04-replication/15-replica-fetcher.md)
16. [Purgatory と DelayedOperation](part04-replication/16-purgatory.md)

## 第5部　KRaft（合意とメタデータ）

17. [KafkaRaftClient によるリーダー選出とログ複製](part05-kraft/17-raft-client.md)
18. [QuorumController とメタデータログ](part05-kraft/18-quorum-controller.md)
19. [MetadataImage と Delta のブローカー反映](part05-kraft/19-metadata-image.md)

## 第6部　コンシューマーとコーディネーター

20. [AsyncKafkaConsumer とフェッチパイプライン](part06-consumer/20-consumer-fetch.md)
21. [新 Group Coordinator と GroupMetadataManager](part06-consumer/21-group-coordinator.md)
22. [コンシューマーグループのリバランスとアサイン](part06-consumer/22-rebalance-assign.md)

## 第7部　トランザクションと Share

23. [Transaction Coordinator と Exactly-Once Semantics](part07-txn-share/23-transaction-coordinator.md)
24. [Share Coordinator とキュー型コンシューム（KIP-932）](part07-txn-share/24-share-coordinator.md)

---

> 全8部24章。
> コード引用は `4.3.1` タグに固定している。
