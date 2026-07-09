# 第5章 HTTP ルーターと API ハンドラ

> 本章で読むソース
>
> - [`daemon/server/router/router.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/server/router/router.go)
> - [`daemon/command/daemon.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go)

## この章の狙い

Engine API が `Router` インタフェースで束ねられ、HTTP メソッドとパスへマップされる仕組みを理解する。

## 前提

REST と Unix ソケット上の HTTP を知っていること。

## Router インタフェース

各サブシステムは `Routes()` で `Route` スライスを返し、メソッドとパスとハンドラを宣言する。

[`daemon/server/router/router.go` L5-L18](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/server/router/router.go#L5-L18)

```go
type Router interface {
	Routes() []Route
}

type Route interface {
	Handler() httputils.APIFunc
	Method() string
	Path() string
}
```

## ルーター組み立て

`buildRouters` はコンテナ、イメージ、ネットワーク等のルーターを連結し、ミドルウェアを挟んで API サーバへ渡す。

## 高速化・最適化の工夫

認可ミドルウェアはルーター登録時に一度だけ組み立て、リクエストごとのプラグイン探索を避ける。

## まとめ

HTTP API は細かい `Route` の集合として拡張可能に保たれる。

## 関連する章

- [第18章 start/stop](../part06-runtime/18-start-stop.md)
