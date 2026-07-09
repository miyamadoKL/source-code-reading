# 第18章 TCP、HTTP、UDP チェック

> 本章で読むソース
>
> - [`keepalived/check/check_tcp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_tcp.c)
> - [`keepalived/check/check_http.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_http.c)
> - [`keepalived/check/check_udp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_udp.c)

## この章の狙い

代表的な L4/L7 ヘルスチェックの実装パターンを理解する。

## 前提

非同期 connect と HTTP ステータスコードを知っていること。

## TCP/UDP

`check_tcp.c`/`check_udp.c` はソケットを非ブロッキングで開き、タイムアウトをスケジューラに任せる。

## HTTP

`check_http.c` はリクエスト組み立て、正規表現によるレスポンス検証、リトライをサポートする。

## 高速化・最適化の工夫

同一ホストへのチェックは connection pooling 相当の再利用を避けつつ、FD 数上限で暴走を防ぐ。

## まとめ

チェック種別ごとにファイルが分かれ、共通の checker フレームワークに載る。

## 関連する章

- [第17章 check デーモン](17-check-daemon.md)
