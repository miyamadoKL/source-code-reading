# 第3章 cobra CLI と DaemonRunner

> 本章で読むソース
>
> - [`daemon/command/docker.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/docker.go)

## この章の狙い

`NewDaemonRunner` が cobra コマンドを組み立て、標準入出力へログを接続する流れを理解する。

## 前提

[第2章](../part00-overview/02-dockerd-startup.md)。

## DaemonRunner

`NewDaemonRunner` はログ形式を初期化し、`newDaemonCommand` で得た cobra コマンドに stdout/stderr を束ねる。

[`daemon/command/docker.go` L100-L117](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/docker.go#L100-L117)

```go
func NewDaemonRunner(stdout, stderr io.Writer) (Runner, error) {
	err := log.SetFormat(log.TextFormat)
	if err != nil {
		return nil, err
	}

	initLogging(stdout, stderr)

	cmd, err := newDaemonCommand()
	if err != nil {
		return nil, err
	}
	cmd.SetOut(stdout)
	cmd.SetErr(stderr)

	return daemonRunner{cmd}, nil
}
```

## フラグ登録

`installConfigFlags` と `installServiceFlags` が `dockerd --config-file` 等を cobra に載せる。
詳細は [第4章](04-daemon-config.md)。

## 高速化・最適化の工夫

cobra の `SilenceUsage` を有効にし、起動失敗時に巨大な usage を毎回出力しない。

## まとめ

CLI 層は薄く、設定と起動本体は `daemonOptions` と `daemonCLI` に委譲する。

## 関連する章

- [第4章 設定](04-daemon-config.md)
