# 第4章 config.Config と設定読み込み

> 本章で読むソース
>
> - [`daemon/config/config.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/config/config.go)

## この章の狙い

`config.New` が埋めるデフォルト値と、`daemon.json` マージの入口を理解する。

## 前提

Linux のブリッジネットワークとログドライバの概念を知っていること。

## デフォルト設定

`config.New` はシャットダウンタイムアウト、ログドライバ、同時ダウンロード数、MTU 等の既定値を構造体に書き込む。

[`daemon/config/config.go` L334-L358](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/config/config.go#L334-L358)

```go
func New() (*Config, error) {
	cfg := &Config{
		CommonConfig: CommonConfig{
			ShutdownTimeout: DefaultShutdownTimeout,
			LogConfig: LogConfig{
				Type:   DefaultLogDriver,
				Config: make(map[string]string),
			},
			DaemonLogConfig: DaemonLogConfig{
				LogLevel:  "info",
				LogFormat: log.TextFormat,
			},
			MaxConcurrentDownloads: DefaultMaxConcurrentDownloads,
			MaxConcurrentUploads:   DefaultMaxConcurrentUploads,
			NetworkConfig: NetworkConfig{
				NetworkControlPlaneMTU: DefaultNetworkMtu,
				DefaultNetworkOpts:     make(map[string]map[string]string),
			},
```

## リロード

`daemonCLI.reloadConfig` は SIGHUP 等で設定を再読み込みし、`configStore` を差し替える。

## 高速化・最適化の工夫

`MaxConcurrentDownloads` でプル処理の並列度を上限し、ディスクとレジストリへの負荷を抑える。

## まとめ

実行時設定は `configStore` のスナップショットとして Daemon 全体に渡る。

## 関連する章

- [第6章 NewDaemon](../part02-core/06-new-daemon.md)
