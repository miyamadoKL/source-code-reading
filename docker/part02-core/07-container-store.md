# 第7章 コンテナストアと restore

> 本章で読むソース
>
> - [`daemon/container/memory_store.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container/memory_store.go)
> - [`daemon/container/container.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container/container.go)
> - [`daemon/daemon.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/daemon.go)

## この章の狙い

メモリ上のコンテナ索引と、再起動時の `restore` がどう連動するかを理解する。

## 前提

コンテナ ID と `config.json` の永続化を知っていること。

## memoryStore

`NewMemoryStore` は ID から `Container` への map を提供する。
API の一覧取得はこのストアを走査する。

[`daemon/container/memory_store.go` L13-L26](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container/memory_store.go#L13-L26)

```go
func NewMemoryStore() Store {
	return &memoryStore{
		s: make(map[string]*Container),
	}
}

func (c *memoryStore) Add(id string, cont *Container) {
	c.Lock()
	c.s[id] = cont
	c.Unlock()
}
```

## Container 構造体

`Container` は `State` を埋め込み、設定、マウント、ネットワーク設定、ログドライバへの参照を保持する。

[`daemon/container/container.go` L69-L86](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container/container.go#L69-L86)

```go
type Container struct {
	StreamConfig *stream.Config
	*State          `json:"State"`
	Root            string  `json:"-"`
	BaseFS          string  `json:"-"`
	ID              string
	Created         time.Time
	Path            string
	Args            []string
	Config          *containertypes.Config
	ImageID         image.ID `json:"Image"`
```

## restore

`Daemon.restore` はディスク上のコンテナメタデータを読み、稼働中だったものを containerd 側と再同期する。

## 高速化・最適化の工夫

`State` 埋め込みによりコンテナ本体の mutex で状態遷移を直列化し、細粒度ロックの複雑さを避ける。

## まとめ

実行時の真実はメモリストアと containerd の二層で保たれる。

## 関連する章

- [第10章 コンテナ作成](../part03-containerd/10-container-create.md)
