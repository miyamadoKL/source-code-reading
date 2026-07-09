# 第24章 metrics と OTLP

> 本章で読むソース
>
> - [`daemon/command/metrics.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/metrics.go)
> - [`daemon/command/daemon.go`](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/daemon.go)

## この章の狙い

Prometheus 互換 metrics エンドポイントと OTLP 設定の入口を理解する。

## 前提

Prometheus の `/metrics` を知っていること。

## metrics サーバ

`startMetricsServer` は別ポートで HTTP サーバを立ち上げ、`go-metrics` ハンドラを公開する。

[`daemon/command/metrics.go` L14-L36](https://github.com/moby/moby/blob/docker-v29.6.1/daemon/command/metrics.go#L14-L36)

```go
func startMetricsServer(addr string) error {
	if addr == "" {
		return nil
	}
	if err := allocateDaemonPort(addr); err != nil {
		return err
	}
	l, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	mux := http.NewServeMux()
	mux.Handle("/metrics", gometrics.Handler())
	go func() {
		log.G(context.TODO()).Infof("metrics API listening on %s", l.Addr())
		srv := &http.Server{
			Handler:           mux,
			ReadHeaderTimeout: 5 * time.Minute,
		}
		if err := srv.Serve(l); err != nil && !errors.Is(err, net.ErrClosed) {
```

## OTLP

`setOTLPProtoDefault` と tracing 設定は `daemonCLI.start` 内で初期化される。

## 高速化・最適化の工夫

metrics はメイン API ソケットと分離し、スクレイプ負荷がコンテナ操作 API に波及しない。

## まとめ

可観測性は別リスナと OpenTelemetry 設定で dockerd に取り込まれる。

## 関連する章

- [第8章 events](../part02-core/08-events-bus.md)
