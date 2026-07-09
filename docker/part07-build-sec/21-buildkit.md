# 第21章 BuildKit 統合

> 本章で読むソース
>
> - [`daemon/command/daemon.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go)

## この章の狙い

`initBuildkit` がセッションマネージャとビルドマネージャを立ち上げる流れを理解する。

## 前提

`docker build` と BuildKit の関係を知っていること。

## initBuildkit

BuildKit 初期化は `session.NewManager` と `dockerfile.NewBuildManager` から始まる。

[`daemon/command/daemon.go` L447-L509](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go#L447-L509)

```go
func initBuildkit(ctx context.Context, d *daemon.Daemon, cdiCache *cdi.Cache) (_ builderOptions, closeFn func(), _ error) {
	log.G(ctx).Info("Initializing buildkit")
	closeFn = func() {}

	sm, err := session.NewManager()
	if err != nil {
		return builderOptions{}, closeFn, errors.Wrap(err, "failed to create sessionmanager")
	}

	manager, err := dockerfile.NewBuildManager(d.BuilderBackend(), d.IdentityMapping())
	if err != nil {
		return builderOptions{}, closeFn, err
	}

	cfg := d.Config()

	bk, err := buildkit.New(ctx, buildkit.Opt{
		SessionManager:      sm,
		Root:                filepath.Join(cfg.Root, "buildkit"),
		// ... (中略) ...
	})
	if err != nil {
		return builderOptions{}, closeFn, errors.Wrap(err, "error creating buildkit instance")
	}

	bb, err := buildbackend.NewBackend(d.ImageService(), manager, bk, d.EventsService)
	if err != nil {
		return builderOptions{}, closeFn, errors.Wrap(err, "failed to create builder backend")
	}

	return builderOptions{
		backend:        bb,
		buildkit:       bk,
		sessionManager: sm,
	}, closeFn, nil
}
```

## バックエンド

`Daemon.BuilderBackend` がイメージとレイヤ操作を BuildKit へ露出する。

## 高速化・最適化の工夫

BuildKit は dockerd 内で builder として初期化され、session manager と builder backend を介してビルド処理を API ループから切り離す。

## まとめ

イメージビルドはレガシー builder ではなく BuildKit セッションが中心である。

## 関連する章

- [第13章 image store](../part04-storage/13-image-layer.md)
