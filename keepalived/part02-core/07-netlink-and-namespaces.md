# 第7章 netlink とネットワーク名前空間

> 本章で読むソース
>
> - [`keepalived/core/keepalived_netlink.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/keepalived_netlink.c)
> - [`keepalived/core/namespaces.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/namespaces.c)

## この章の狙い

仮想 IP やルートをカーネルに反映する netlink ラッパと、network namespace 切替を理解する。

## 前提

rtnetlink（`RTM_NEWADDR` 等）の概念を知っていること。

## netlink ラッパ

`keepalived_netlink.c` はアドレス、リンク、ルート、ルールの追加削除を共通化する。
VRRP と check の双方から呼ばれ、エラー時の `netlink_error_ignore` で冪等削除を支援する。

## 名前空間

`namespaces.c` は `net_namespace` 設定に従い `setns` を実行し、子プロセスを対象 namespace で起動する。
親は mount namespace と pid namespace の組み合わせを扱う。

## 高速化・最適化の工夫

netlink ソケットはプロセスごとに保持し、バッチ的な `sendmsg` で複数属性を一度に送る。
namespace 切替は起動時に固定し、ホットパスでは再 `setns` しない。

## まとめ

カーネル操作は keepalived 全体で netlink 層に集約される。

## 関連する章

- [第13章 仮想 IP](../part04-vrrp-net/13-vrrp-ipaddress-if.md)
- [第14章 ルート](../part04-vrrp-net/14-vrrp-iproute-iprule.md)
