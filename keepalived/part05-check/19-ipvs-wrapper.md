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

`ipvs_talk` はコマンド種別に応じて `ipvs_add_service` や `ipvs_add_dest` を呼び、real server の up/down を反映する。

[`keepalived/check/ipvswrapper.c` L167-L188](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/ipvswrapper.c#L167-L188)

```c
static int
ipvs_talk(int cmd, ipvs_service_t *srule, ipvs_dest_t *drule, ipvs_daemon_t *daemonrule, bool ignore_error)
{
	int result = -1;

	if (no_ipvs)
		return result;

	switch (cmd) {
		case IP_VS_SO_SET_ADD:
			result = ipvs_add_service(srule);
			break;
		case IP_VS_SO_SET_DEL:
			result = ipvs_del_service(srule);
			break;
```

## libipvs

`ipvs_init` は netlink 版 IPVS が使えるとき `ipvs_getinfo` を試し、失敗時は従来の `IPPROTO_RAW` ソケットへ落とす。

[`keepalived/check/libipvs.c` L454-L470](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/libipvs.c#L454-L470)

```c
int ipvs_init(
				      bool retry)
{
	ipvs_func = ipvs_init;

#ifdef LIBIPVS_USE_NL
	if (try_nl)
		return ipvs_getinfo(retry);

	try_nl = false;
#endif
```

## 高速化・最適化の工夫

同一 real server への連続更新は checker 層で状態変化時だけ `ipvs_talk` を呼び、不要な netlink 更新を避ける。

## まとめ

LVS 連携は check 子の主目的であり、ipvswrapper がカーネル API を隠蔽する。

## 関連する章

- [第17章 check デーモン](17-check-daemon.md)
