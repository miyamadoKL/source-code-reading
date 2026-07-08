# Apache Flink ソースコードリーディング

Apache Flink（[apache/flink](https://github.com/apache/flink)）のソースコードを読み解き、分散ストリーム処理エンジンの内部構造を日本語で解説するドキュメントである。

- **対象バージョン**：2.3.0（コード引用はすべて [`release-2.3.0` タグ](https://github.com/apache/flink/tree/release-2.3.0)に固定）
- **想定読者**：Java と分散システムの基礎があり、ストリーム処理エンジンの内部実装を読み解きたい中級エンジニア
- **読み方**：第0部の全体像から、コア基盤（第1部）、グラフ生成（第2部）、スケジューリング（第3部）、タスク実行（第4部）、ネットワーク（第5部）、状態とチェックポイント（第6部）、Table と SQL（第7部）、高度なトピック（第8部）へと基礎から順に読み進める。

コード引用は「GitHub リンク行＋コードブロック」の2点セットで示し、行番号は `release-2.3.0` の実ソースに固定している。

## 第0部　全体像

1. [Flink とは何か：アーキテクチャと実行モデル](part00-overview/01-what-is-flink.md)
2. [クラスタ起動とジョブ投入：ClusterEntrypoint と Dispatcher](part00-overview/02-cluster-entrypoint.md)

## 第1部　コア基盤

3. [メモリ管理：MemorySegment とマネージドメモリ](part01-core/03-memory-segment.md)
4. [型システムとシリアライゼーション](part01-core/04-type-serialization.md)
5. [設定、プラグイン、クラスローダー](part01-core/05-configuration-classloader.md)

## 第2部　ジョブグラフの生成

6. [DataStream API と Transformation](part02-graph/06-datastream-transformation.md)
7. [StreamGraph の生成](part02-graph/07-streamgraph.md)
8. [JobGraph への変換とオペレーターチェイン](part02-graph/08-jobgraph-chaining.md)
9. [ExecutionGraph の構築](part02-graph/09-executiongraph.md)

## 第3部　スケジューリングと資源管理

10. [JobMaster とスケジューラ](part03-scheduling/10-jobmaster-scheduler.md)
11. [スロット管理と ResourceManager](part03-scheduling/11-slot-resourcemanager.md)
12. [TaskExecutor とタスクのデプロイ](part03-scheduling/12-taskexecutor-deploy.md)

## 第4部　タスク実行

13. [StreamTask と mailbox 実行モデル](part04-task-execution/13-streamtask-mailbox.md)
14. [演算子と UDF の実行](part04-task-execution/14-operators-udf.md)
15. [ウォーターマークとタイマー](part04-task-execution/15-watermark-timer.md)

## 第5部　ネットワークスタック

16. [ResultPartition と InputGate](part05-network/16-resultpartition-inputgate.md)
17. [クレジットベースフロー制御とバッファ管理](part05-network/17-credit-flow-buffers.md)
18. [シャッフルサービスとデータ交換](part05-network/18-shuffle-service.md)

## 第6部　状態とチェックポイント

19. [状態バックエンド：Keyed State と ForSt](part06-state-checkpoint/19-state-backend.md)
20. [チェックポイントの調整：CheckpointCoordinator](part06-state-checkpoint/20-checkpoint-coordinator.md)
21. [バリアのアラインメントと非アラインドチェックポイント](part06-state-checkpoint/21-checkpoint-alignment.md)
22. [リカバリと状態の再配分](part06-state-checkpoint/22-recovery-rescale.md)

## 第7部　Table と SQL

23. [Table API と SQL パーサーの Calcite 統合](part07-table-sql/23-table-parser-calcite.md)
24. [論理プランと最適化ルール](part07-table-sql/24-logical-optimize.md)
25. [物理プランと ExecNode](part07-table-sql/25-physical-execnode.md)
26. [コード生成と table-runtime 演算子](part07-table-sql/26-codegen-runtime.md)

## 第8部　高度なトピック

27. [新しい Source API：FLIP-27](part08-advanced/27-source-api-flip27.md)
28. [Sink とコネクタ基盤](part08-advanced/28-sink-connector.md)

---

> 本書は Apache Flink 2.3.0（タグ `release-2.3.0`）を対象に、全9部28章で構成する。
