# Docker Engine（Moby）ソースコードリーディング

Docker Engine（[moby/moby](https://github.com/moby/moby)）のソースコードを読み解き、dockerd、containerd 連携、ストレージ、ネットワーク、ランタイムを日本語で解説するドキュメントである。

- **対象バージョン**：29.6.1（コード引用はすべて [`docker-v29.6.1` タグ](https://github.com/moby/moby/tree/docker-v29.6.1)に固定）
- **ライセンス**：Apache-2.0（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：Go、Linux コンテナ、OCI の基礎があり、dockerd の内部をソースから追いたい中級エンジニア。
- **読み方**：第0部から順に読むと、起動、Daemon コア、containerd、ストレージ、ネットワーク、実行、ビルド、運用へ段階的に積み上がる。

コード引用は GitHub の固定タグ URL とコードブロックの2点セットで示す。
v29 以降の Engine リリースは `docker-vX.Y.Z` 形式のタグで公開される。

## 第0部　概観

1. [Docker Engine と Moby v2 の全体像](part00-overview/01-docker-engine-overview.md)
2. [dockerd 起動と reexec](part00-overview/02-dockerd-startup.md)

## 第1部　コマンドと API 基盤

3. [cobra CLI と DaemonRunner](part01-command/03-cobra-cli.md)
4. [config.Config と設定読み込み](part01-command/04-daemon-config.md)
5. [HTTP ルーターと API ハンドラ](part01-command/05-http-router.md)

## 第2部　Daemon コア

6. [NewDaemon と Daemon 構造体](part02-core/06-new-daemon.md)
7. [コンテナストアと restore](part02-core/07-container-store.md)
8. [events バス](part02-core/08-events-bus.md)

## 第3部　containerd 連携

9. [containerd クライアント初期化](part03-containerd/09-containerd-client.md)
10. [コンテナ作成パイプライン](part03-containerd/10-container-create.md)
11. [実行監視と health](part03-containerd/11-container-monitor.md)

## 第4部　ストレージ

12. [graphdriver と overlay2](part04-storage/12-overlay2-graphdriver.md)
13. [image store と layer](part04-storage/13-image-layer.md)
14. [volume サービス](part04-storage/14-volumes.md)

## 第5部　ネットワーク

15. [network 設定とモード](part05-network/15-network-settings.md)
16. [ポート公開とプロキシ](part05-network/16-port-mapping.md)
17. [ネットワーク接続](part05-network/17-network-connect.md)

## 第6部　ランタイム

18. [start と stop](part06-runtime/18-start-stop.md)
19. [exec と attach](part06-runtime/19-exec-attach.md)
20. [logging driver](part06-runtime/20-logging-drivers.md)

## 第7部　ビルドとセキュリティ

21. [BuildKit 統合](part07-build-sec/21-buildkit.md)
22. [seccomp と cgroup](part07-build-sec/22-seccomp-cgroup.md)

## 第8部　運用

23. [認証と authorization プラグイン](part08-ops/23-auth-plugins.md)
24. [metrics と OTLP](part08-ops/24-metrics-otel.md)

---

> 対象は moby/moby の dockerd 本体である。
> docker/cli クライアント実装と integration テストは本書の範囲外とする。
> 引用タグは GitHub 上の `docker-v29.6.1` を用いる（`v29.6.1` ではない）。
