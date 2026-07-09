# 第6章 NewDaemon と Daemon 構造体

> 本章で読むソース
>
> - [`daemon/daemon.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/daemon.go)

## この章の狙い

`NewDaemon` がストレージ、containerd、ネットワーク、イメージストアを順に初期化する流れを追う。

## 前提

[第4章](../part01-command/04-daemon-config.md)。

## NewDaemon の入口

`NewDaemon` はレジストリサービス作成、設定検証、ID マッピング、ランタイムディレクトリ準備のあと `Daemon` 構造体を組み立てる。

[`daemon/daemon.go` L847-L916](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/daemon.go#L847-L916)

```go
func NewDaemon(ctx context.Context, config *config.Config, pluginStore *plugin.Store, authzMiddleware *authorization.Middleware) (_ *Daemon, retErr error) {
	registryService, err := registry.NewService(config.ServiceOptions)
	if err != nil {
		return nil, err
	}

	if err := verifyDaemonSettings(config); err != nil {
		return nil, err
	}

	d := &Daemon{
		PluginStore: pluginStore,
		startupDone: make(chan struct{}),
	}
	cfgStore := &configStore{
		Config:   *config,
		Runtimes: rts,
	}
	d.configStore.Store(cfgStore)
```

## 初期化の塊

同一関数内で containerd 接続、graphdriver、イメージストア、libnetwork、volume サービスが立ち上がる。
失敗時は defer で部分初期化を巻き戻す。

## 高速化・最適化の工夫

`startupDone` チャネルで起動完了を一度だけ通知し、依存コンポーネントの待ち合わせコストを固定する。

## まとめ

`NewDaemon` は dockerd が API を受け付け可能になる境界である。

## 関連する章

- [第9章 containerd](../part03-containerd/09-containerd-client.md)
