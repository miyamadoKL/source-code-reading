# ProxySQL ソースコードリーディング

ProxySQL（[sysown/proxysql](https://github.com/sysown/proxysql)）のソースコードを読み解き、MySQL/PostgreSQL 向け高性能プロキシの実装と高速化の工夫を日本語で解説するドキュメントである。

- **対象バージョン**：3.0.9（コード引用はすべて [`v3.0.9` タグ](https://github.com/sysown/proxysql/tree/v3.0.9)に固定）
- **ライセンス**：GPL-3.0（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：C++ と分散システムまたは RDBMS の基礎がある中級エンジニア
- **読み方**：起動とスレッドモデルから始め、プロトコル、セッションとクエリ処理、バックエンド接続プール、高可用性、管理層と下から積み上げて読む

コード引用は「バージョン固定の GitHub リンク」＋「コードブロック」の2点セットで示す。
本書は MySQL 経路を主軸に据え、PostgreSQL 経路は差分として第7部で扱う。

## 第0部　全体像

1. [ProxySQL のアーキテクチャと起動シーケンス](part00-overview/01-architecture.md)

## 第1部　スレッドとネットワーク層

2. [スレッドモデルと MySQL_Thread のイベントループ](part01-thread/02-thread-model.md)
3. [MySQL_Data_Stream による接続の状態機械とバッファリング](part01-thread/03-data-stream.md)

## 第2部　プロトコル層

4. [MySQL プロトコルの解析と生成](part02-protocol/04-mysql-protocol.md)
5. [認証ハンドシェイクとユーザー認証](part02-protocol/05-authentication.md)
6. [PostgreSQL プロトコル対応](part02-protocol/06-pgsql-protocol.md)

## 第3部　セッションとクエリ処理

7. [MySQL_Session の状態機械](part03-session/07-session-state-machine.md)
8. [クエリのライフサイクルとコマンドディスパッチ](part03-session/08-query-lifecycle.md)
9. [Query Processor とルーティングルール](part03-session/09-query-processor.md)
10. [クエリダイジェストとトークナイザ](part03-session/10-query-digest.md)
11. [Query Cache](part03-session/11-query-cache.md)
12. [プリペアドステートメントの管理](part03-session/12-prepared-statement.md)

## 第4部　バックエンドと接続プール

13. [Hostgroups Manager とサーバー管理](part04-backend/13-hostgroups-manager.md)
14. [コネクションプールと多重化](part04-backend/14-connection-pool.md)
15. [バックエンド接続の状態機械](part04-backend/15-backend-connection.md)
16. [トランザクション境界と接続の持続性](part04-backend/16-transaction-persistence.md)

## 第5部　高可用性とモニタリング

17. [MySQL Monitor によるヘルスチェック](part05-ha/17-monitor.md)
18. [レプリケーション監視とホストグループの自動調整](part05-ha/18-replication-monitoring.md)
19. [GTID トラッキングと因果整合性リード](part05-ha/19-gtid-causal-reads.md)

## 第6部　管理と設定とクラスタ

20. [Admin インターフェイスと SQLite 設定バックエンド](part06-admin/20-admin-interface.md)
21. [設定のマルチレイヤ管理](part06-admin/21-config-layers.md)
22. [ProxySQL Cluster による設定同期](part06-admin/22-cluster-sync.md)
23. [クエリログとロギング](part06-admin/23-logging.md)

## 第7部　PostgreSQL サポートと拡張

24. [PostgreSQL サポートの全体像とセッション処理](part07-pgsql/24-pgsql-support.md)
25. [ClickHouse と SQLite3 サーバーの統合](part07-pgsql/25-other-backends.md)

---

> 本書は執筆進行中である。
> コード引用は `v3.0.9` タグに固定し、行番号は実ソースと照合している。
