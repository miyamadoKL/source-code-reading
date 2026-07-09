# 第13章 image store と layer

> 本章で読むソース
>
> - [`daemon/images/service.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/images/service.go)

## この章の狙い

`ImageService` が layer store と content store をどう束ねるかを理解する。

## 前提

OCI イメージとレイヤの関係を知っていること。

## ImageService

イメージ操作は `ImageService` が layer/content/reference をまとめて扱う。

[`daemon/images/service.go` L73-L88](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/images/service.go#L73-L88)

```go
type ImageService struct {
	containers                containerStore
	distributionMetadataStore metadata.Store
	downloadManager           *xfer.LayerDownloadManager
	eventsService             *daemonevents.Events
	imageStore                image.Store
	layerStore                layer.Store
	pruneRunning              atomic.Bool
	referenceStore            refstore.Store
	registryService           distribution.RegistryResolver
	uploadManager             *xfer.LayerUploadManager
	leases                    leases.Manager
	content                   content.Store
```

## プルとプッシュ

`LayerDownloadManager` はレジストリからの取得を並列化し、レイヤをローカル store へ展開する。

## 高速化・最適化の工夫

`pruneRunning` で prune の重複実行を抑え、ディスク走査の競合を避ける。

## まとめ

イメージはメタデータストアとレイヤストアの二層で表現される。

## 関連する章

- [第12章 overlay2](12-overlay2-graphdriver.md)
