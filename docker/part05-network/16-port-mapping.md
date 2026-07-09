# 第16章 ポート公開とプロキシ

> 本章で読むソース
>
> - [`daemon/container_operations.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container_operations.go)
> - [`daemon/container.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container.go)

## この章の狙い

`PortBindings` と `ExposedPorts` が libnetwork の公開ポートへ変換される過程を追う。

## 前提

`-p 8080:80` の内部表現を知っていること。

## ポートマップ構築

停止中コンテナでも設定を更新できるよう、バインディングをコピーしてから exposed を補完する。

[`daemon/container_operations.go` L111-L120](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container_operations.go#L111-L120)

```go
	portBindings := make(networktypes.PortMap, len(ctr.HostConfig.PortBindings))
	for p, b := range ctr.HostConfig.PortBindings {
		portBindings[p] = slices.Clone(b)
	}

	for p := range ctr.Config.ExposedPorts {
		if _, ok := portBindings[p]; !ok {
			portBindings[p] = nil
		}
	}
```

## 検証

`validatePortBindings` はホストポート範囲とプロトコルを検証する。

[`daemon/container.go` L333-L346](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container.go#L333-L346)

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
			if _, err := networktypes.ParsePortRange(pb.HostPort); err != nil {
				return errors.Errorf("invalid port specification: %q", pb.HostPort)
			}
```

## 高速化・最適化の工夫

空の `HostPort` はエフェメラル割当てへ委譲し、ユーザー指定がない場合の bind 試行を省略する。

## まとめ

ポート公開はネットワークサンドボックス作成時に一度だけ libnetwork へ渡される。

## 関連する章

- [第18章 start](../part06-runtime/18-start-stop.md)
