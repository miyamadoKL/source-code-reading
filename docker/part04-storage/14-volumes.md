# 第14章 volume サービス

> 本章で読むソース
>
> - [`daemon/volume/service/service.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/volume/service/service.go)

## この章の狙い

名前付きボリュームのドライバ登録とストア初期化を理解する。

## 前提

volume プラグインと bind mount の違いを知っていること。

## NewVolumeService

デフォルトドライバをセットアップし、永続ストアを `VolumesService` に載せる。

[`daemon/volume/service/service.go` L42-L53](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/volume/service/service.go#L42-L53)

```go
func NewVolumeService(root string, pg plugingetter.PluginGetter, rootIDs idtools.Identity, logger VolumeEventLogger) (*VolumesService, error) {
	ds := drivers.NewStore(pg)
	if err := setupDefaultDriver(ds, root, rootIDs); err != nil {
		return nil, err
	}

	vs, err := NewStore(root, ds, WithEventLogger(logger))
	if err != nil {
		return nil, err
	}
	return &VolumesService{vs: vs, ds: ds, eventLogger: logger}, nil
}
```

## イベント連携

ボリューム操作は `VolumeEventLogger` 経由で events へ流れる。

## 高速化・最適化の工夫

ドライバストアをプロセス寿命で共有し、プラグイン lookup を毎リクエストで繰り返さない。

## まとめ

永続データは graphdriver とは別の volume サブシステムが担う。

## 関連する章

- [第7章 コンテナストア](../part02-core/07-container-store.md)
