# 第20章 その他チェックと BFD 連携

> 本章で読むソース
>
> - [`keepalived/check/check_misc.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_misc.c)
> - [`keepalived/check/check_bfd.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_bfd.c)
> - [`keepalived/check/check_file.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_file.c)

## この章の狙い

スクリプト、ファイル、BFD ベースのチェックを理解する。

## 前提

[第5章](../part01-foundation/05-memory-signals-process.md) の `process.c`。

## misc と file

`check_misc.c` は外部スクリプトの終了コードで up/down を判定する。
`check_file.c` は inode 変化やサイズしきい値を監視する。

## BFD

`check_bfd.c` は BFD 子からのパイプイベントで real server を落とす。

## 高速化・最適化の工夫

スクリプト実行は `process` 層でタイムアウトと並列度を制限する。

## まとめ

柔軟な運用要件は misc/file/bfd チェックで吸収される。

## 関連する章

- [第22章 BFD 連携](../part06-bfd/22-bfd-integration.md)
