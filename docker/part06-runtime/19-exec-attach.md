# 第19章 exec と attach

> 本章で読むソース
>
> - [`daemon/exec.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/exec.go)
> - [`daemon/attach.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/attach.go)

## この章の狙い

追加プロセス実行と標準入出力アタッチの入口を理解する。

## 前提

TTY とデタッチキーを知っていること。

## ContainerExecCreate

`ContainerExecCreate` は稼働中コンテナを取得し、ユーザー指定があればコンテナ内で先に解決する。

[`daemon/exec.go` L95-L115](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/exec.go#L95-L115)

```go
func (daemon *Daemon) ContainerExecCreate(name string, options *containertypes.ExecCreateRequest) (string, error) {
	cntr, err := daemon.getActiveContainer(name)
	if err != nil {
		return "", err
	}
	if user := options.User; user != "" {
		if _, err := getUser(cntr, user); err != nil {
			return "", errdefs.InvalidParameter(err)
		}
	}
```

## ContainerAttach

`ContainerAttach` はログ追従またはストリーム接続を `stream.AttachConfig` へ委譲する。

[`daemon/attach.go` L22-L38](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/attach.go#L22-L38)

```go
func (daemon *Daemon) ContainerAttach(prefixOrName string, req *backend.ContainerAttachConfig) error {
	keys := []byte{}
	var err error
	if req.DetachKeys != "" {
		keys, err = term.ToBytes(req.DetachKeys)
		if err != nil {
			return errdefs.InvalidParameter(errors.Errorf("Invalid detach keys (%s) provided", req.DetachKeys))
		}
	}

	ctr, err := daemon.GetContainer(prefixOrName)
	if err != nil {
		return err
	}
	if ctr.State.IsPaused() {
		return errdefs.Conflict(fmt.Errorf("container %s is paused, unpause the container before attach", prefixOrName))
	}
```

## 高速化・最適化の工夫

attach はコンテナの `StreamConfig` を再利用し、毎回新しいパイプを最小限だけ確保する。

## まとめ

exec/attach はメインプロセスとは別経路で containerd タスクを操作する。

## 関連する章

- [第20章 logging](20-logging-drivers.md)
