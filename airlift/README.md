# Airlift ソースコードリーディング

Airlift（[airlift/airlift](https://github.com/airlift/airlift)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「高速化、最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：439（コード引用はすべて [`439` タグ](https://github.com/airlift/airlift/tree/439)に固定）
- **ライセンス**：Apache-2.0
- **想定読者**：Java と Guice によるサーバ構築の基礎がある中級エンジニア
- **読み方**：基礎から順に積み上がる構成で、第0部から順に読むことを想定する。

コード引用は、本文中の `[path L開始-L終了](https://github.com/airlift/airlift/blob/439/...)` 形式のリンクから GitHub 上の該当箇所を直接参照できる。
Airlift は Trino をはじめとする分散サービスの基盤フレームワークであり、本書は Guice による依存性注入とモジュール合成でサーバを組み立てる主要経路を追う。

## 第0部　全体像

1. [アーキテクチャ全体像とサーバ起動](part00-overview/01-architecture.md)

## 第1部　依存性注入とライフサイクル

2. [Bootstrap と Injector 構築](part01-di-lifecycle/02-bootstrap.md)
3. [ライフサイクル管理とリソース解放](part01-di-lifecycle/03-lifecycle.md)

## 第2部　設定

4. [設定の入力とバインド](part02-config/04-config-binding.md)
5. [設定メタデータと検証](part02-config/05-config-metadata.md)
6. [ConfigurationAwareModule](part02-config/06-config-aware-module.md)

## 第3部　JSON

7. [JsonCodec と JsonMapper](part03-json/07-json.md)

## 第4部　HTTP サーバ

8. [HttpServerModule と Provider](part04-http-server/08-http-server-module.md)
9. [HttpServerInfo とコネクタ](part04-http-server/09-http-server-info.md)
10. [HttpServer のハンドラ連鎖](part04-http-server/10-http-server-handlers.md)

## 第5部　JAX-RS

11. [JAX-RS 統合](part05-jaxrs/11-jaxrs.md)

## 第6部　HTTP クライアント

12. [Request と Response と URI](part06-http-client/12-request-response.md)
13. [ResponseHandler](part06-http-client/13-response-handler.md)
14. [HttpClientModule とフィルタ](part06-http-client/14-http-client-module.md)
15. [JettyHttpClient](part06-http-client/15-jetty-http-client.md)

## 第7部　ノードとサービスディスカバリ

16. [ノード識別とサービスアナウンス](part07-node-discovery/16-node-announce.md)
17. [サービス選択](part07-node-discovery/17-service-selector.md)

## 第8部　可観測性

18. [統計（1）facade と backend](part08-observability/18-stats-facade.md)
19. [統計（2）sketch と decay](part08-observability/19-stats-sketches.md)
20. [JMX と OpenMetrics 公開](part08-observability/20-jmx-openmetrics.md)
21. [トレーシングと OpenTelemetry](part08-observability/21-tracing.md)
22. [ログ](part08-observability/22-logging.md)

## 第9部　並行処理

23. [Future ユーティリティ](part09-concurrent/23-futures.md)
24. [Executor と backpressure](part09-concurrent/24-executors.md)

---

> 全24章。
> コード引用はすべて `439` タグに固定している。
