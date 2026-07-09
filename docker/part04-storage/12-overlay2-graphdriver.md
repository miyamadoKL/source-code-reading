# 第12章 graphdriver と overlay2

> 本章で読むソース
>
> - [`daemon/graphdriver/overlay2/overlay.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/graphdriver/overlay2/overlay.go)

## この章の狙い

Linux 既定の overlay2 ドライバ登録と機能検出を理解する。

## 前提

overlayfs の lowerdir/upperdir を知っていること。

## ドライバ登録

`init` が `graphdriver.Register` で overlay2 をプラグイン登録する。

[`daemon/graphdriver/overlay2/overlay.go` L118-L128](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/graphdriver/overlay2/overlay.go#L118-L128)

```go
func init() {
	graphdriver.Register(driverName, Init)
}

func Init(home string, options []string, idMap user.IdentityMapping) (graphdriver.Driver, error) {
	opts, err := parseOptions(options)
	if err != nil {
		return nil, err
	}
```

## レイヤ操作

`Driver` は create/remove/diff を通じてイメージレイヤとコンテナ RW 層を管理する。

## 高速化・最適化の工夫

既存 `home` ディレクトリで overlay 対応を先に検出し、不適合 FS では早期に `ErrIncompatibleFS` を返す。

## まとめ

ストレージの書き込み可能層は graphdriver が抽象化する。

## 関連する章

- [第13章 image store](13-image-layer.md)
