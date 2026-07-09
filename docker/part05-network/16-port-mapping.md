# 第16章 ポートマッピング

> 本章で読むソース
>
> - [`daemon/container.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container.go)
> - [`daemon/network.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/network.go)
> - [`daemon/daemon_unix.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/daemon_unix.go)

## この章の狙い

`PortBindings` と `PublishAllPorts` が検証され、libnetwork へどう渡されるかを読む。

## 前提

[第15章](15-network-settings.md)の `connectToNetwork` を理解していること。

## 検証

`validatePortBindings` はポート番号0や不正形式を拒否する。

[`daemon/container.go` L333-L342](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container.go#L333-L342)

```go
func validatePortBindings(ports networktypes.PortMap) error {
	for port := range ports {
		if !port.IsValid() || port.Num() == 0 {
			return errors.Errorf("invalid port specification: %q", port.String())
		}

		for _, pb := range ports[port] {
			if pb.HostPort == "" {
				continue
			}
```

作成時にも `verifyContainerSettings` から呼ばれる。

[`daemon/container.go` L279-L281](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container.go#L279-L281)

```go
	if err := validatePortBindings(hostConfig.PortBindings); err != nil {
		return warnings, err
	}
```

## host ネットワークとの衝突

host モードでは公開ポート設定は破棄され、warning になる。

[`daemon/daemon_unix.go` L669-L671](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/daemon_unix.go#L669-L671)

```go
	if hostConfig.NetworkMode.IsHost() && len(hostConfig.PortBindings) > 0 {
		warnings = append(warnings, "Published ports are discarded when using host network mode")
	}
```

## PublishAllPorts

`network.go` は ExposedPorts 全体をポートマップに展開し、バインディング未指定エントリを作る。

[`daemon/network.go` L1049-L1061](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/network.go#L1049-L1061)

```go
	ports := c.HostConfig.PortBindings
	if c.HostConfig.PublishAllPorts && len(c.Config.ExposedPorts) > 0 {
		ports = maps.Clone(c.HostConfig.PortBindings)
		if ports == nil {
			ports = networktypes.PortMap{}
		}
		for p := range c.Config.ExposedPorts {
			if _, exists := ports[p]; !exists {
				ports[p] = nil
			}
		}
	}
```

## API 型

`ContainerStopOptions` とは別に、ポートは `networktypes.PortMap` でホスト IP とポートを保持する。

[`daemon/container_operations.go` L111-L114](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container_operations.go#L111-L114)

```go
	portBindings := make(networktypes.PortMap, len(ctr.HostConfig.PortBindings))
	for p, b := range ctr.HostConfig.PortBindings {
		portBindings[p] = slices.Clone(b)
	}
```

```mermaid
flowchart LR
  HC[HostConfig PortBindings] --> VAL[validatePortBindings]
  VAL --> MERGE[ExposedPorts マージ]
  MERGE --> LN[libnetwork portmapper]
  LN --> HOST[ホストで待受]
```

## 高速化・最適化の工夫

空 HostPort はエフェメラル割り当てへ委譲し、ユーザー指定が無い公開ポートも動的にバインドできる。
host モードではポートマッピング処理自体をスキップし、不要な iptables 更新を避ける。

`validatePortBindings` は空 HostPort をエフェメラル割り当てとして許容する。

[`daemon/container.go` L339-L342](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container.go#L339-L342)

```go
		for _, pb := range ports[port] {
			if pb.HostPort == "" {
				continue
			}
```

## sandbox への変換

`connectToNetwork` 前段で `PortBindings` をコピーし、expose だけのポートへ nil エントリを補う。

[`daemon/container_operations.go` L111-L132](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container_operations.go#L111-L132)

```go
	portBindings := make(networktypes.PortMap, len(ctr.HostConfig.PortBindings))
	for p, b := range ctr.HostConfig.PortBindings {
		portBindings[p] = slices.Clone(b)
	}

	for p := range ctr.Config.ExposedPorts {
		if _, ok := portBindings[p]; !ok {
			// Create nil entries for exposed but un-mapped ports.
			portBindings[p] = nil
		}
	}

	var (
		publishedPorts []types.PortBinding
		exposedPorts   []types.TransportPort
	)
	for port, bindings := range portBindings {
		protocol := types.ParseProtocol(string(port.Proto()))
		exposedPorts = append(exposedPorts, types.TransportPort{
			Proto: protocol,
			Port:  port.Num(),
		})
```

## まとめ

ポート公開は設定検証のあと libnetwork がホスト側マッピングを張る。

## 関連する章

- [第15章 ネットワーク設定](15-network-settings.md)
- [第18章 start/stop](../part06-runtime/18-start-stop.md)
