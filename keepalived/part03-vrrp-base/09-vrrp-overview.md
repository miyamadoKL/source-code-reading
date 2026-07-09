# 第9章 VRRP の概要と vrrp.c

> 本章で読むソース
>
> - [`keepalived/vrrp/vrrp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp.c#L6-L9)
> - [`keepalived/vrrp/vrrp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp.c#L1883-L1887)

## この章の狙い

`vrrp.c` が担うプロトコル処理の全体像と、マスタ遷移の入口関数を把握する。

## 前提

VRRP の Master/Backup と priority を理解していること。

## プロトコル目的

[`keepalived/vrrp/vrrp.c` L6-L9](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp.c#L6-L9)

```c
 * Part:        VRRP implementation of VRRPv2 as specified in rfc2338.
 *              VRRP is a protocol which elect a master server on a LAN. If the
 *              master fails, a backup server takes over.
 *              The original implementation has been made by jerome etienne.
```

## マスタ化の入口

[`keepalived/vrrp/vrrp.c` L1883-L1887](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp.c#L1883-L1887)

```c
/* becoming master */
static void
vrrp_state_become_master(vrrp_t * vrrp)
{
	++vrrp->stats->become_master;
```

`vrrp_state_goto_master` が状態を `VRRP_STATE_MAST` に設定し、仮想 IP 設定と GARP 送信をスケジュールする。

## 高速化・最適化の工夫

受信パスはカーネルフィルタと raw/socket の組み合わせで不要パケットを捨てる。
同期グループは1つの広告処理で複数 instance を更新し、syscall 回数を抑える。

## まとめ

`vrrp.c` は keepalived の中核で、状態機械とパケット処理の大半を含む。

## 関連する章

- [第11章 状態遷移](11-vrrp-state-machine.md)
- [第10章 VRRP 子プロセス](10-vrrp-daemon.md)
