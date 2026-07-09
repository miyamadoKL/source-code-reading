# 第10章 コンテナ作成パイプライン

> 本章で読むソース
>
> - [`daemon/create.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/create.go)

## この章の狙い

API の `ContainerCreate` から `containerCreate` 内部実装への流れを追う。

## 前提

イメージ ID と `HostConfig` の関係を知っていること。

## 公開 API

`ContainerCreate` は `containerCreate` に設定スナップショットを渡す薄いラッパである。

[`daemon/create.go` L51-L70](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/create.go#L51-L70)

```go
func (daemon *Daemon) ContainerCreate(ctx context.Context, params backend.ContainerCreateConfig) (containertypes.CreateResponse, error) {
	return daemon.containerCreate(ctx, daemon.config(), createOpts{
		params: params,
	})
}

func (daemon *Daemon) containerCreate(ctx context.Context, daemonCfg *configStore, opts createOpts) (_ containertypes.CreateResponse, retErr error) {
	ctx, span := otel.Tracer("").Start(ctx, "daemon.containerCreate", trace.WithAttributes(
		labelsAsOTelAttributes(opts.params.Config.Labels)...,
	))
```

## 内部処理

`containerCreate` は設定検証のあと `daemon.create` へ委譲し、メタデータと rootfs 準備までを行って `CreateResponse` を返す。
containerd の `NewTask` と `tsk.Start` は `start` 経路で実行される。

## 高速化・最適化の工夫

OpenTelemetry スパンで作成フェーズを分割し、遅延のボトルネックを計測可能にする。

## まとめ

作成はメタデータと rootfs 準備まで、実行タスク作成は start に分離される。

## 関連する章

- [第18章 start](../part06-runtime/18-start-stop.md)
