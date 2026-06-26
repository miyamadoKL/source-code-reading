# TiKV（分散 KV）ソースコードリーディング

TiKV（[tikv/tikv](https://github.com/tikv/tikv)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「分散環境での最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：8.5.6（コード引用はすべて [`v8.5.6` タグ](https://github.com/tikv/tikv/tree/v8.5.6)に固定）
- **想定読者**：Rust と分散システムの基礎がある中級エンジニア
- **読み方**：ストレージエンジンから Raft、Percolator のサーバ側、コプロセッサ、運用まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v8.5.6` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
TiKV は TiDB エコシステムの分散ストレージ層であり、下層のストレージエンジンには RocksDB を使うため、LSM-tree の機構は既存の RocksDB 編へクロスリンクする。

## 第0部　全体像

1. [TiKV とは何か](part00-overview/01-what-is-tikv.md)
2. [アーキテクチャ、Store と Region と Peer](part00-overview/02-architecture.md)
3. [gRPC サービスとリクエストの流れ](part00-overview/03-grpc-and-request-flow.md)

## 第1部　ストレージエンジン

4. [ストレージエンジン抽象（engine_traits）](part01-engine/04-engine-traits.md)
5. [RocksDB 統合とカラムファミリ](part01-engine/05-engine-rocks-and-cf.md)
6. [Raft ログエンジン](part01-engine/06-raft-log-engine.md)

## 第2部　Raft とマルチラフト

7. [raftstore の全体像](part02-raft/07-raftstore-overview.md)
8. [Region と Peer](part02-raft/08-region-and-peer.md)
9. [提案と適用](part02-raft/09-propose-and-apply.md)
10. [リース読みと ReadIndex](part02-raft/10-lease-read.md)
11. [分割、マージ、スナップショット、メンバ変更](part02-raft/11-split-merge-snapshot.md)

## 第3部　トランザクション（Percolator サーバ側）

12. [MVCC のエンコード](part03-txn/12-mvcc-encoding.md)
13. [Prewrite（第1相）](part03-txn/13-prewrite.md)
14. [Commit と MVCC 読み取り](part03-txn/14-commit-and-read.md)
15. [悲観ロックと concurrency_manager](part03-txn/15-pessimistic-lock.md)
16. [resolved_ts と GC](part03-txn/16-resolved-ts-and-gc.md)

## 第4部　読み取りとコプロセッサ

17. [read pool とスナップショット読み取り](part04-coprocessor/17-read-pool-and-snapshot.md)
18. [コプロセッサ](part04-coprocessor/18-coprocessor.md)
19. [コプロセッサの式評価とベクトル化](part04-coprocessor/19-coprocessor-vectorization.md)

## 第5部　スケジューリングと運用

20. [スケジューラと latch](part05-ops/20-scheduler-and-latch.md)
21. [PD との連携](part05-ops/21-pd-integration.md)
22. [sst_importer と CDC、backup](part05-ops/22-sst-import-and-cdc.md)

---

> 対象バージョンは TiKV 8.5.6。
> 各章のコード引用は `v8.5.6` タグに固定した GitHub リンクから該当行を直接参照できる。
