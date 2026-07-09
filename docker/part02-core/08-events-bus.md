# 第8章 events バス

> 本章で読むソース
>
> - [`daemon/events/events.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/events/events.go)

## この章の狙い

`docker events` が購読する pubsub バスの実装を理解する。

## 前提

publish/subscribe パターンを知っていること。

## Events 構造体

直近 256 件をリング的に保持し、新規購読者へスナップショットを渡してから live チャネルを開く。

[`daemon/events/events.go` L12-L29](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/events/events.go#L12-L29)

```go
const (
	eventsLimit = 256
	bufferSize  = 1024
)

type Events struct {
	mu     sync.Mutex
	events []eventtypes.Message
	pub    *pubsub.Publisher
}

func New() *Events {
	return &Events{
		events: make([]eventtypes.Message, 0, eventsLimit),
		pub:    pubsub.NewPublisher(100*time.Millisecond, bufferSize),
	}
}
```

## Subscribe

`Subscribe` はメトリクスを更新し、履歴コピーと `pub.Subscribe` を返す。
購読解除関数でリークを防ぐ。

## 高速化・最適化の工夫

Publisher に 100ms のバッファリングを設け、短時間のイベントバーストをまとめて配送する。

## まとめ

イベントは API 監視と内部メトリクスの共通バックボーンである。

## 関連する章

- [第24章 metrics](../part08-ops/24-metrics-otel.md)
