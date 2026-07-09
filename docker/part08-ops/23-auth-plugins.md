# 第23章 認証と authorization プラグイン

> 本章で読むソース
>
> - [`daemon/command/daemon.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go)

## この章の狙い

`--authorization-plugin` で指定されたプラグインの検証とミドルウェア適用を理解する。

## 前提

Docker AuthZ プラグインの概念を知っていること。

## validateAuthzPlugins

起動時に各プラグインが AuthZ インタフェースを実装しているかを確認する。

[`daemon/command/daemon.go` L1063-L1071](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go#L1063-L1071)

```go
func validateAuthzPlugins(requestedPlugins []string, pg plugingetter.PluginGetter) error {
	for _, reqPlugin := range requestedPlugins {
		if _, err := pg.Get(reqPlugin, authorization.AuthZApiImplements, plugingetter.Lookup); err != nil {
			return err
		}
	}
	return nil
}
```

## ミドルウェア

`authorization.Middleware` は HTTP ハンドラ前にリクエスト可否を判定する。

## 高速化・最適化の工夫

プラグイン検証は起動とリロード時だけ行い、ホットパスではキャッシュ済みハンドラを使う。

## まとめ

認可はオプションのプラグイン層で拡張され、コア API は変更せずに制御できる。

## 関連する章

- [第5章 HTTP ルーター](../part01-command/05-http-router.md)
