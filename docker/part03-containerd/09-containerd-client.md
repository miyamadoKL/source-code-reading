# 第9章 containerd クライアント初期化

> 本章で読むソース
>
> - [`daemon/command/daemon.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go)

## この章の狙い

システム containerd を検出するか、管理下の containerd を起動する分岐を理解する。

## 前提

containerd のソケットアドレスを知っていること。

## initializeContainerd

既存の system containerd があればそのアドレスを採用し、なければ `supervisor.Start` で子プロセスを起動する。

[`daemon/command/daemon.go` L1145-L1166](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go#L1145-L1166)

```go
func (cli *daemonCLI) initializeContainerd(ctx context.Context) (func(time.Duration) error, error) {
	systemContainerdAddr, ok, err := systemContainerdRunning(honorXDG)
	if err != nil {
		return nil, errors.Wrap(err, "could not determine whether the system containerd is running")
	}
	if ok {
		cli.Config.ContainerdAddr = systemContainerdAddr
		return nil, nil
	}

	log.G(ctx).Info("containerd not running, starting managed containerd")
	opts, err := getContainerdDaemonOpts(cli.Config)
	// ... (中略) ...
	r, err := supervisor.Start(ctx, filepath.Join(cli.Config.Root, "containerd"), filepath.Join(cli.Config.ExecRoot, "containerd"), opts...)
	cli.Config.ContainerdAddr = r.Address()
```

## Daemon 側クライアント

`NewDaemon` 内で `containerd.Client` と libcontainerd ラッパが接続される。

## 高速化・最適化の工夫

外部 containerd を再利用し、二重起動と余分なスーパーバイザコストを避ける。

## まとめ

containerd は dockerd の下位ランタイム層であり、アドレス解決が起動の分岐点になる。

## 関連する章

- [第10章 コンテナ作成](10-container-create.md)
