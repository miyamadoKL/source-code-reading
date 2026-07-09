# nginx ソースコードリーディング

nginx（[nginx/nginx](https://github.com/nginx/nginx)）のソースコードを読み解き、イベント駆動アーキテクチャの Web サーバーおよびリバースプロキシがどのように実装されているかを日本語で解説するドキュメントである。

- **対象バージョン**：1.31.2（コード引用はすべて [`release-1.31.2` タグ](https://github.com/nginx/nginx/tree/release-1.31.2)に固定）
- **ライセンス**：BSD-2-Clause（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：C と Linux ネットワークプログラミングの基礎がある中級エンジニア
- **読み方**：全体像からコア基盤、イベント駆動エンジン、HTTP エンジン、upstream、HTTP/2、HTTP/3 まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`release-1.31.2` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。

## 第0部　全体像

1. [nginx とは何かとプロセスモデル](part00-overview/01-what-is-nginx-and-process-model.md)
2. [モジュールアーキテクチャ](part00-overview/02-module-architecture.md)

## 第1部　コア基盤

3. [メモリプールとバッファ](part01-core/03-memory-pool-and-buffer.md)
4. [コアデータ構造](part01-core/04-core-data-structures.md)
5. [設定ファイルのパース](part01-core/05-configuration-parsing.md)
6. [共有メモリとスラブアロケータ](part01-core/06-shared-memory-and-slab.md)

## 第2部　イベント駆動エンジン

7. [イベントループとタイマー](part02-event/07-event-loop-and-timers.md)
8. [接続管理と epoll](part02-event/08-connection-and-epoll.md)

## 第3部　HTTP エンジン

9. [HTTP リクエストの受理とパース](part03-http/09-http-request-parsing.md)
10. [フェーズエンジンと location 検索](part03-http/10-phase-engine-and-location.md)
11. [フィルタチェーンと output chain](part03-http/11-filter-chain-and-output-chain.md)
12. [変数と rewrite](part03-http/12-variables-and-rewrite.md)

## 第4部　upstream とプロキシ

13. [upstream 機構](part04-upstream/13-upstream-mechanism.md)
14. [ロードバランシング](part04-upstream/14-load-balancing.md)
15. [proxy のバッファリングとキャッシュ](part04-upstream/15-proxy-buffering-and-cache.md)

## 第5部　HTTP/2 と HTTP/3

16. [HTTP/2](part05-http2-http3/16-http2.md)
17. [QUIC トランスポート](part05-http2-http3/17-quic-transport.md)
18. [HTTP/3](part05-http2-http3/18-http3.md)

---

> 全6部18章。
> 対象バージョンは nginx 1.31.2。
> mail と stream サブシステムは本書の対象外である。
