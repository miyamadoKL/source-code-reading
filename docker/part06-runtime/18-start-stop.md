# 第18章 start と stop

> 本章で読むソース
>
> - [`daemon/start.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/start.go)
> - [`daemon/stop.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/stop.go)

## この章の狙い

コンテナ起動準備と停止処理のエントリポイントを理解する。

## 前提

[第10章](../part03-containerd/10-container-create.md)。

## containerStart

ストレージとネットワークを整え、シグナル待ちの状態まで進める。

[`daemon/start.go` L72-L96](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/start.go#L72-L96)

```go
func (daemon *Daemon) containerStart(ctx context.Context, daemonCfg *configStore, container *container.Container, checkpoint string, checkpointDir string, resetRestartManager bool) (retErr error) {
	ctx, span := otel.Tracer("").Start(ctx, "daemon.containerStart", trace.WithAttributes(append(
		labelsAsOTelAttributes(container.Config.Labels),
		attribute.String("container.ID", container.ID),
	)...))
	// ... (中略) ...
	container.Lock()
	defer container.Unlock()

	if container.State.RemovalInProgress || container.State.Dead {
		return errdefs.Conflict(errors.New("container is marked for removal and cannot be started"))
	}
```

## ContainerStop

既に停止済みなら `NotModified` を返し、API 側で 304 相当を表現する。

[`daemon/stop.go` L25-L40](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/stop.go#L25-L40)

```go
func (daemon *Daemon) ContainerStop(ctx context.Context, name string, options backend.ContainerStopOptions) error {
	ctr, err := daemon.GetContainer(name)
	if err != nil {
		return err
	}
	if !ctr.State.IsRunning() {
		return errdefs.NotModified(errors.New("container is already stopped"))
	}
	err = daemon.containerStop(ctx, ctr, options)
```

## 高速化・最適化の工夫

start/stop ともコンテナ mutex で直列化し、並行 API 呼び出しの状態競合を防ぐ。

## まとめ

ランタイム遷移は Daemon メソッドが orchestrate し、containerd がプロセスを操作する。

## 関連する章

- [第19章 exec](19-exec-attach.md)
