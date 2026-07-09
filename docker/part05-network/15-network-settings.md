# 第15章 network 設定とモード

> 本章で読むソース
>
> - [`daemon/network/settings.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/network/settings.go)
> - [`daemon/network/network_mode.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/network/network_mode.go)

## この章の狙い

コンテナに紐づく `Settings` とネットワークモードの解釈を理解する。

## 前提

bridge/host/none モードを知っていること。

## Settings

`Settings` はサンドボックス ID、接続ネットワーク、公開ポートマップを保持する。

[`daemon/network/settings.go` L12-L21](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/network/settings.go#L12-L21)

```go
type Settings struct {
	SandboxID        string
	SandboxKey       string
	Networks         map[string]*EndpointSettings
	Service          *clustertypes.ServiceConfig
	Ports            networktypes.PortMap
	HasSwarmEndpoint bool
}
```

## モード判定

`network_mode.go` は `HostConfig.NetworkMode` 文字列を解析し、libnetwork への接続方針を決める。

## 高速化・最適化の工夫

`Networks` map でエンドポイント設定を O(1) 参照し、再接続時の走査を抑える。

## まとめ

ネットワーク状態はコンテナメタデータと libnetwork サンドボックスの両方に反映される。

## 関連する章

- [第17章 ネットワーク接続](17-network-connect.md)
