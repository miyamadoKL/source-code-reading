# TiCDC ソースコードリーディング

TiCDC（[pingcap/ticdc](https://github.com/pingcap/ticdc)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「変更データキャプチャを支える工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：8.5.6（コード引用はすべて [`v8.5.6` タグ](https://github.com/pingcap/ticdc/tree/v8.5.6)に固定）
- **想定読者**：Go と分散システムの基礎がある中級エンジニア
- **読み方**：全体像から LogService（イベント取得と蓄積）、Downstream Adapter（下流への書き込み）、スケジューリング、高可用性と運用まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`v8.5.6` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
TiCDC は TiDB エコシステムの変更データキャプチャ（CDC）コンポーネントであり、TiKV の変更ログをリアルタイムに下流（MySQL、Kafka、Cloud Storage 等）へ複製する。

## 第0部　全体像

1. [TiCDC とは何か](part00-overview/01-what-is-ticdc.md)
2. [サーバーアーキテクチャ](part00-overview/02-server-architecture.md)
3. [メッセージングとノード間通信](part00-overview/03-messaging.md)

## 第1部　LogService（イベント取得と蓄積）

4. [LogPuller と TiKV Change Feed](part01-logservice/04-logpuller.md)
5. [EventStore と Pebble](part01-logservice/05-eventstore.md)
6. [SchemaStore と DDL 追跡](part01-logservice/06-schemastore.md)
7. [EventService とイベント配信](part01-logservice/07-eventservice.md)

## 第2部　Downstream Adapter（下流への書き込み）

8. [Dispatcher と EventCollector](part02-downstream/08-dispatcher-and-eventcollector.md)
9. [MySQL Sink](part02-downstream/09-mysql-sink.md)
10. [Kafka Sink とコーデック](part02-downstream/10-kafka-sink-and-codec.md)
11. [Redo ログと耐障害性](part02-downstream/11-redo-log.md)

## 第3部　スケジューリング

12. [Coordinator と Changefeed 管理](part03-scheduling/12-coordinator.md)
13. [Maintainer とテーブルスケジューリング](part03-scheduling/13-maintainer.md)

## 第4部　高可用性と運用

14. [高可用性とフェイルオーバー](part04-ha-ops/14-high-availability.md)
15. [cdc cli と運用](part04-ha-ops/15-cdc-cli-and-ops.md)

---

> 対象バージョンは TiCDC 8.5.6。
> 各章のコード引用は `v8.5.6` タグに固定した GitHub リンクから該当行を直接参照できる。
