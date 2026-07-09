# 第17章 ネットワーク接続

> 本章で読むソース
>
> - [`daemon/container_operations.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container_operations.go)

## この章の狙い

実行中と停止中で分岐する `ConnectToNetwork` の挙動を理解する。

## 前提

`docker network connect` の API を知っていること。

## ConnectToNetwork

停止中は設定だけ更新し、実行中は libnetwork エンドポイントを実際に作成する。

[`daemon/container_operations.go` L1050-L1067](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container_operations.go#L1050-L1067)

```go
func (daemon *Daemon) ConnectToNetwork(ctx context.Context, ctr *container.Container, idOrName string, endpointConfig *networktypes.EndpointSettings) error {
	if endpointConfig == nil {
		endpointConfig = &networktypes.EndpointSettings{}
	}
	ctr.Lock()
	defer ctr.Unlock()

	if !ctr.State.Running {
		if ctr.State.RemovalInProgress || ctr.State.Dead {
			return errRemovalContainer(ctr.ID)
		}

		n, err := daemon.FindNetwork(idOrName)
		if err == nil && n != nil {
			if err := daemon.runInNetNS(func() error {
				return daemon.updateNetworkConfig(ctr, n, endpointConfig)
```

## 高速化・最適化の工夫

停止中の接続は netlink 操作を避け、次回 start まで設定だけ保持する。

## まとめ

ネットワーク接続はコンテナロック下で状態と libnetwork を同期する。

## 関連する章

- [第15章 network 設定](15-network-settings.md)
