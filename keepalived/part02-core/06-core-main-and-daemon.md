# 第6章 core main とデーモン起動

> 本章で読むソース
>
> - [`keepalived/core/main.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/main.c#L2437-L2440)
> - [`keepalived/core/main.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/main.c#L514-L575)

## この章の狙い

親プロセスにおける `keepalived_main` と `start_keepalived` の責務を分離して理解する。

## 前提

[第2章](../part00-overview/02-startup-and-process-model.md) を読んでいること。

## エントリ

[`keepalived/core/main.c` L2437-L2440](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/main.c#L2437-L2440)

```c
/* Entry point */
int
keepalived_main(int argc, char **argv)
{
```

以降でログ、権限、設定ファイルパス、ネットワーク名前空間の初期化を行う。

## 子の起動

[`keepalived/core/main.c` L514-L575](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/main.c#L514-L575) の `start_keepalived` が Checker、VRRP、BFD 子を順に起動する（第2章引用と同一）。

## 高速化・最適化の工夫

親プロセスはネットワーク I/O をほぼ行わず、設定と監視に専念する。
リロードは親が新設定を読み、子へデータを渡して再起動または差分適用する。

## まとめ

`core/main.c` はオーケストレータであり、プロトコル処理は子に委譲される。

## 関連する章

- [第17章 check デーモン](../part05-check/17-check-daemon.md)
- [第10章 VRRP 子プロセス](../part03-vrrp-base/10-vrrp-daemon.md)
