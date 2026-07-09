# 第19章 IPVS ラッパー

> 本章で読むソース
>
> - [`keepalived/check/ipvswrapper.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/ipvswrapper.c)
> - [`keepalived/check/libipvs.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/libipvs.c)

## この章の狙い

チェック結果が IPVS プールの重みと可用性に反映される経路を追う。

## 前提

`ipvsadm` とカーネル IPVS の関係を知っていること。

## ipvswrapper

`ipvswrapper.c` は virtual server と real server の追加削除、重み更新をまとめる。

## libipvs

`libipvs.c` は netlink IPVS ファミリへの薄いラッパである。

## 高速化・最適化の工夫

複数チェック失敗を集約してから1回の netlink 更新にまとめ、システムコールを削減する。

## まとめ

LVS 連携は check 子の主目的であり、ipvswrapper がカーネル API を隠蔽する。

## 関連する章

- [第17章 check デーモン](17-check-daemon.md)
