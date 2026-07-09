# 第22章 seccomp と cgroup

> 本章で読むソース
>
> - [`daemon/daemon_unix.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/daemon_unix.go)

## この章の狙い

デフォルト seccomp プロファイルの読み込みと cgroup 関連設定の入口を理解する。

## 前提

seccomp と cgroup v2 を知っていること。

## setupSeccompProfile

`default`/`unconfined`/カスタムパスの3分岐で seccomp の扱いを決める。
`default` と `unconfined` はパス種別だけを保持し、カスタムパスだけファイルを読み込んでプロファイル本体を保持する。

[`daemon/daemon_unix.go` L1605-L1618](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/daemon_unix.go#L1605-L1618)

```go
func (daemon *Daemon) setupSeccompProfile(cfg *config.Config) error {
	switch profile := cfg.SeccompProfile; profile {
	case "", config.SeccompProfileDefault:
		daemon.seccompProfilePath = config.SeccompProfileDefault
	case config.SeccompProfileUnconfined:
		daemon.seccompProfilePath = config.SeccompProfileUnconfined
	default:
		daemon.seccompProfilePath = profile
		b, err := os.ReadFile(profile)
		if err != nil {
			return fmt.Errorf("opening seccomp profile (%s) failed: %v", profile, err)
		}
		daemon.seccompProfile = b
	}
	return nil
}
```

## cgroup

コンテナ作成時に `HostConfig.Resources` が cgroup 制限へ変換され、containerd OCI spec に載る。

## 高速化・最適化の工夫

カスタム seccomp は起動時に一度だけ読み込み、コンテナごとのファイル I/O を避ける。

## まとめ

セキュリティプロファイルは Daemon 起動時に解決し、ランタイム spec へ注入される。

## 関連する章

- [第10章 コンテナ作成](../part03-containerd/10-container-create.md)
