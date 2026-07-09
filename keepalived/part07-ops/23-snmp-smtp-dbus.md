# 第23章 SNMP、SMTP、D-Bus

> 本章で読むソース
>
> - [`keepalived/core/snmp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/snmp.c)
> - [`keepalived/core/smtp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/smtp.c)
> - [`keepalived/vrrp/vrrp_dbus.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_dbus.c)

## この章の狙い

監視と通知の周辺機能を理解する。

## 前提

SNMP MIB と SMTP アラートの用途を知っていること。

## SNMP

`snmp.c` と `vrrp_snmp.c` は VRRP 統計を AgentX 経由で公開する。

## SMTP

`smtp.c` は状態遷移時のメール通知を非同期で送る。

## D-Bus

`vrrp_dbus.c` は systemd 連携や外部コントロール用のインタフェースを提供する（ビルド時）。

## 高速化・最適化の工夫

SMTP は専用スレッド相当のキューで送り、VRRP ループをブロックしない。

## まとめ

運用可観測性はコアと VRRP に分散実装されている。

## 関連する章

- [第11章 状態遷移](../part03-vrrp-base/11-vrrp-state-machine.md)
