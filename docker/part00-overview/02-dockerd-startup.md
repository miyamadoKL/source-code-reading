# 第2章 dockerd 起動と reexec

> 本章で読むソース
>
> - [`daemon/command/daemon.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go)
> - [`daemon/command/docker.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/docker.go)

## この章の狙い

cobra ベースの CLI から `daemonCLI.start` が走るまでの起動シーケンスを理解する。
`reexec` が子プロセス用エントリをどう差し替えるかも押さえる。

## 前提

[第1章](01-docker-engine-overview.md) を読んでいること。

## cobra コマンド

`newDaemonCommand` は `dockerd [OPTIONS]` を定義し、`RunE` で `runDaemon` へ進む。
`--validate` 指定時は設定検証だけ行いプロセスを終了する。

[`daemon/command/docker.go` L26-L48](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/docker.go#L26-L48)

```go
	cmd := &cobra.Command{
		Use:           "dockerd [OPTIONS]",
		Short:         "A self-sufficient runtime for containers.",
		SilenceUsage:  true,
		SilenceErrors: true,
		Args:          NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			opts.flags = cmd.Flags()

			cli, err := newDaemonCLI(opts)
			if err != nil {
				return err
			}
			if opts.Validate {
				cmd.PrintErrln("configuration OK")
				return nil
			}

			return runDaemon(cmd.Context(), cli)
		},
```

## start の前半

`daemonCLI.start` はシステム要件、ログ、root 権限、データルート作成を順に確認する。
ここで失敗すると API サーバは起動しない。

[`daemon/command/daemon.go` L118-L161](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go#L118-L161)

```go
func (cli *daemonCLI) start(ctx context.Context) (retErr error) {
	if err := daemon.CheckSystem(); err != nil {
		return fmt.Errorf("system requirements not met: %w", err)
	}
	configureProxyEnv(ctx, cli.Config.Proxies)
	if err := configureDaemonLogs(ctx, cli.Config.DaemonLogConfig); err != nil {
		return fmt.Errorf("failed to configure daemon logging: %w", err)
	}

	log.G(ctx).Info("Starting up")
	// ... (中略) ...
	if runtime.GOOS == "linux" && os.Geteuid() != 0 {
		return errors.New("dockerd needs to be started with root privileges. To run dockerd in rootless mode as an unprivileged user, see https://docs.docker.com/go/rootless/")
	}

	if err := daemon.CreateDaemonRoot(cli.Config); err != nil {
		return err
	}
```

## reexec

`main` 先頭の `reexec.Init()` は、containerd やランタイムが fork した子が別の Go エントリを実行するときに早期 return する。
同一バイナリで複数役割を担うための仕組みである。

## 高速化・最適化の工夫

起動時に `ExecRoot` 等を一度だけ作成し、以後のコンテナ操作は既存ディレクトリを再利用する。

## まとめ

dockerd は薄い `main` と `daemon/command` に起動責務を分離し、`start` で前提条件を固めてから `NewDaemon` へ進む。

## 関連する章

- [第3章 cobra CLI](../part01-command/03-cobra-cli.md)
- [第6章 NewDaemon](../part02-core/06-new-daemon.md)
