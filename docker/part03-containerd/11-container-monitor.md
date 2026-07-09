# 第11章 実行監視と health

> 本章で読むソース
>
> - [`daemon/container/health.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container/health.go)

## この章の狙い

コンテナのヘルスチェック状態と監視ゴルーチンの停止経路を理解する。

## 前提

Dockerfile の `HEALTHCHECK` を知っていること。

## Health 構造体

`Health` は API 型を埋め込み、`stop` チャネルで監視ループを終了させる。

[`daemon/container/health.go` L11-L16](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/container/health.go#L11-L16)

```go
type Health struct {
	container.Health
	stop chan struct{} // Write struct{} to stop the monitor
	mu   sync.Mutex
}
```

## 監視とイベント

ヘルス状態の変化は events バスへ流れ、オーケストレータが `unhealthy` を検知できる。

## 高速化・最適化の工夫

`stop` チャネルは構造体送信のみで監視を打ち切り、コンテナ削除時のゴルーチンリークを防ぐ。

## まとめ

ランタイム監視はコンテナオブジェクトに閉じ、Daemon は状態を API とイベントで公開する。

## 関連する章

- [第8章 events](../part02-core/08-events-bus.md)
