# 第20章 logging driver

> 本章で読むソース
>
> - [`daemon/logger/factory.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/logger/factory.go)

## この章の狙い

ログドライバの登録と lookup の仕組みを理解する。

## 前提

json-file や journald ドライバを知っていること。

## ファクトリ

`RegisterLogDriver` で名前とコンストラクタを登録し、起動時に各ドライバが `init` から登録する。

[`daemon/logger/factory.go` L110-L114](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/logger/factory.go#L110-L114)

```go
func RegisterLogDriver(name string, c Creator) error {
	return factory.register(name, c)
}
```

## コンテナへの適用

コンテナ起動時に `LogDriver` が生成され、`LogCopier` が stdout/stderr を転送する。

## 高速化・最適化の工夫

ドライバ lookup は map 参照のみで、リクエストごとのプラグインスキャンを避ける。

## まとめ

ログはコンテナライフサイクルに紐づくプラガブルな `logger.Logger` として実装される。

## 関連する章

- [第4章 設定](../part01-command/04-daemon-config.md)
