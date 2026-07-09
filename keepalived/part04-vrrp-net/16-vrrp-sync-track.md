# 第16章 同期グループとトラッキング

> 本章で読むソース
>
> - [`keepalived/vrrp/vrrp_sync.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_sync.c)
> - [`keepalived/vrrp/vrrp_track.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_track.c)

## この章の狙い

複数 instance を同一マスタ状態に揃える同期と、interface/script トラックを理解する。

## 前提

[第11章](../part03-vrrp-base/11-vrrp-state-machine.md) の `vrrp_sync_can_goto_master`。

## 同期グループ

`vrrp_sync_backup` は同期グループ内の他 instance を BACKUP へ揃える。
1台が Backup 化したとき、グループ全体の状態を整合させる。

[`keepalived/vrrp/vrrp_sync.c` L140-L158](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_sync.c#L140-L158)

```c
void
vrrp_sync_backup(vrrp_t *vrrp)
{
	vrrp_sgroup_t *sgroup = vrrp->sync;
	vrrp_t *isync;

	if (GROUP_STATE(sgroup) == VRRP_STATE_BACK)
		return;

	log_message(LOG_INFO, "VRRP_Group(%s) Syncing instances to BACKUP state"
			    , GROUP_NAME(sgroup));

	list_for_each_entry(isync, &sgroup->vrrp_instances, s_list) {
		if (isync == vrrp || isync->state == VRRP_STATE_BACK)
			continue;

		isync->wantstate = VRRP_STATE_BACK;
```

## トラック

`vrrp_set_effective_priority` は `total_priority` から effective priority を再計算し、変更時だけログする。
`track_interface`、`track_script`、`track_bfd` の減点はこの合算に入る。

[`keepalived/vrrp/vrrp_track.c` L582-L608](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_track.c#L582-L608)

```c
void
vrrp_set_effective_priority(vrrp_t *vrrp)
{
	uint8_t new_prio;
	// ... (中略) ...
	if (vrrp->total_priority < 1)
		new_prio = 1;
	else if (vrrp->total_priority >= VRRP_PRIO_OWNER)
		new_prio = VRRP_PRIO_OWNER - 1;
	else
		new_prio = (uint8_t)vrrp->total_priority;

	if (vrrp->effective_priority == new_prio)
		return;

	vrrp->effective_priority = new_prio;
```

## 高速化・最適化の工夫

トラック結果はイベント駆動で再計算し、ポーリング間隔を最小化する。

## まとめ

同期とトラックは運用要件をコードで表現する層である。

## 関連する章

- [第22章 BFD 連携](../part06-bfd/22-bfd-integration.md)
