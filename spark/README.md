# Apache Spark ソースコードリーディング

Apache Spark（[apache/spark](https://github.com/apache/spark)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「分散データ処理フレームワークを支える工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：v4.1.2（コード引用はすべて [`v4.1.2` タグ](https://github.com/apache/spark/tree/v4.1.2)に固定）
- **ライセンス**：Apache-2.0（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：Scala と分散システムの基礎がある中級エンジニア
- **読み方**：全体像からコア（RDD・スケジューリング・実行）、SQL（Catalyst・Tungsten・AQE）、Structured Streaming、PySpark、Kubernetes 連携まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v4.1.2` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
Apache Spark は RDD を基盤とする分散データ処理フレームワークであり、SQL エンジン（Catalyst/Tungsten）、Structured Streaming、PySpark、Kubernetes 連携を含む統合プラットフォームである。

## 第0部　イントロダクション

1. [Apache Spark の全体像とアーキテクチャ](part00-intro/01-overview-and-architecture.md)
2. [SparkContext とアプリケーションライフサイクル](part00-intro/02-sparkcontext-and-lifecycle.md)

## 第1部　コア: RDD とデータ抽象化

3. [RDD の設計と実装](part01-rdd/03-rdd-design-and-implementation.md)
4. [RDD の変換とアクション](part01-rdd/04-rdd-transformations-and-actions.md)
5. [共有変数: Broadcast と Accumulator](part01-rdd/05-shared-variables.md)

## 第2部　コア: ジョブスケジューリング

6. [DAGScheduler: ステージ構築とジョブスケジューリング](part02-scheduling/06-dagscheduler.md)
7. [TaskScheduler: タスク分散とリソース割り当て](part02-scheduling/07-taskscheduler.md)
8. [スケジューラバックエンドとクラスタマネージャインタフェース](part02-scheduling/08-scheduler-backends.md)

## 第3部　コア: タスク実行

9. [Executor: タスク実行エンジン](part03-execution/09-executor.md)
10. [タスクのメモリ管理と GC](part03-execution/10-task-memory-and-gc.md)
11. [シャッフルの書き込みと読み出し](part03-execution/11-shuffle-write-and-read.md)

## 第4部　コア: ストレージとメモリ

12. [BlockManager: ブロックの保存と取得](part04-storage/12-blockmanager.md)
13. [Unified Memory Manager](part04-storage/13-unified-memory-manager.md)
14. [ディスクストアとメモリストア](part04-storage/14-disk-and-memory-store.md)

## 第5部　SQL: Catalyst フレームワーク

15. [Catalyst: 論理プランと解析](part05-catalyst/15-catalyst-logical-plan-and-analysis.md)
16. [Catalyst: クエリ最適化](part05-catalyst/16-catalyst-query-optimization.md)
17. [Catalyst: 物理プラン生成](part05-catalyst/17-catalyst-physical-planning.md)

## 第6部　SQL: Tungsten と実行

18. [Tungsten: オフヒープメモリと Whole-Stage Code Generation](part06-tungsten/18-tungsten-offheap-and-wscg.md)
19. [SQL 実行エンジン: オペレータと内部データ型](part06-tungsten/19-sql-execution-engine.md)
20. [Adaptive Query Execution](part06-tungsten/20-adaptive-query-execution.md)

## 第7部　Structured Streaming

21. [Structured Streaming: マイクロバッチ実行モデル](part07-streaming/21-structured-streaming-microbatch.md)
22. [Structured Streaming: ステート管理とフォールトトレランス](part07-streaming/22-structured-streaming-state.md)

## 第8部　PySpark 連携

23. [PySpark: Py4J ゲートウェイと Python API 設計](part08-pyspark/23-pyspark-py4j-gateway.md)
24. [PySpark: Arrow 連携と Spark Connect](part08-pyspark/24-pyspark-arrow-and-connect.md)

## 第9部　リソースマネージャ: Kubernetes

25. [Kubernetes: Spark on K8s アーキテクチャ](part09-kubernetes/25-spark-on-k8s-architecture.md)
26. [Kubernetes: Pod ライフサイクルとフィーチャーステップ](part09-kubernetes/26-k8s-pod-lifecycle.md)
27. [Kubernetes: YuniKorn 連携](part09-kubernetes/27-k8s-yunikorn-integration.md)

## 第10部　リソースマネージャ: YARN

28. [YARN 連携の概要](part10-yarn/28-yarn-overview.md)

---

> 全10部28章。
> 対象バージョンは Apache Spark v4.1.2。
> 各章のコード引用は `v4.1.2` タグに固定した GitHub リンクから該当行を直接参照できる。
