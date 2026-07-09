# 第8章 expand と optimize

> 本章で読むソース
>
> - [`libsepol/src/expand.c`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/expand.c)
> - [`libsepol/src/optimize.c`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/optimize.c)

## この章の狙い

リンク済みポリシーをカーネル向けに展開する `expand_module` と、avtab を圧縮する `policydb_optimize` を読む。
checkpolicy パイプライン上の位置と、各段階が書き換える policydb フィールドを把握する。

## 前提

第7章の link_modules を読んでいること。

## expand_module

tunable の真偽に応じて avrule リストへルールを移し、展開状態 `expand_state_t` を初期化する。

[`libsepol/src/expand.c` L3110-L3138](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/expand.c#L3110-L3138)

```c
/* Linking should always be done before calling expand, even if
 * there is only a base since all optionals are dealt with at link time
 * the base passed in should be indexed and avrule blocks should be 
 * enabled.
 */
int expand_module(sepol_handle_t * handle,
		  policydb_t * base, policydb_t * out, int verbose, int check)
{
	int retval = -1;
	unsigned int i;
	expand_state_t state;
	avrule_block_t *curblock;

	discard_tunables(handle, base);

	expand_state_init(&state);

	state.verbose = verbose;
	state.typemap = NULL;
	state.base = base;
	state.out = out;
	state.handle = handle;
```

checkpolicy はパースと link のあと `expand_module` で別 policydb へ展開し、元の parse 用 policydb を破棄する。

[`checkpolicy/checkpolicy.c` L640-L651](https://github.com/SELinuxProject/selinux/blob/3.10/checkpolicy/checkpolicy.c#L640-L651)

```c
		if (!cil) {
			if (policydb_init(&policydb)) {
				fprintf(stderr, "%s:  policydb_init failed\n", argv[0]);
				exit(1);
			}
			if (expand_module(NULL, policydbp, &policydb, /*verbose=*/0, !disable_neverallow)) {
				fprintf(stderr, "Error while expanding policy\n");
				exit(1);
			}
			policydb.policyvers = policyvers ? policyvers : POLICYDB_VERSION_MAX;
			policydb_destroy(policydbp);
			policydbp = &policydb;
		}
```

## expand_avtab

展開の核心は高レベル avrule から `te_avtab` への変換である。
`expand_avtab` は型集合を具象型へ展開しながら avtab へ挿入する。

[`libsepol/src/expand.c` L3517-L3527](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/expand.c#L3517-L3527)

```c
int expand_avtab(policydb_t * p, avtab_t * a, avtab_t * expa)
{
	struct expand_avtab_data data;

	if (avtab_alloc(expa, MAX_AVTAB_SIZE)) {
		ERR(NULL, "Out of memory!");
		return -1;
	}

	data.expa = expa;
	data.p = p;
```

## policydb_optimize

`policydb_optimize` はカーネルポリシー種別だけを対象とし、型マップを構築して avtab を畳み込む。
ポリシーバージョン 20〜23 は属性配置の都合で最適化非対応とする。

[`libsepol/src/optimize.c` L445-L468](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/optimize.c#L445-L468)

```c
int policydb_optimize(policydb_t *p)
{
	struct type_vec *type_map;

	if (p->policy_type != POLICY_KERN)
		return -1;

	if (p->policyvers >= POLICYDB_VERSION_AVTAB && p->policyvers <= POLICYDB_VERSION_PERMISSIVE) {
		ERR(NULL, "Optimizing policy versions between 20 and 23 is not supported");
		return -1;
	}

	type_map = build_type_map(p);
	if (!type_map)
		return -1;

	optimize_avtab(p, type_map);
	optimize_cond_avtab(p, type_map);
```

checkpolicy の `-O` 相当で optimize フラグが立つと、書き出し前に呼ばれる。

[`checkpolicy/checkpolicy.c` L657-L663](https://github.com/SELinuxProject/selinux/blob/3.10/checkpolicy/checkpolicy.c#L657-L663)

```c
	if (optimize && policydbp->policy_type == POLICY_KERN) {
		ret = policydb_optimize(policydbp);
		if (ret) {
			fprintf(stderr, "%s:  error optimizing policy\n", argv[0]);
			exit(1);
		}
	}
```

```mermaid
flowchart LR
  LINK[link済み policydb] --> EXP[expand_module]
  EXP --> KERN[POLICY_KERN policydb]
  KERN --> OPT[policydb_optimize]
  OPT --> WRITE[policydb_write]
```

## expand_module の全体像

`expand_module` は tunable の真偽に応じて avrule リストを確定させ、avtab へ展開する。
link 済みベースだけを入力に取り、カーネル向け policydb を出力する。

[`libsepol/src/expand.c` L3115-L3127](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/expand.c#L3115-L3127)

```c
int expand_module(sepol_handle_t * handle,
		  policydb_t * base, policydb_t * out, int verbose, int check)
{
	int retval = -1;
	unsigned int i;
	expand_state_t state;
	avrule_block_t *curblock;

	/* Append tunable's avtrue_list or avfalse_list to the avrules list
	 * of its home decl depending on its state value, so that the effect
	 * rules of a tunable would be added to te_avtab permanently. Whereas
	 * the disabled unused branch would be discarded.
	 *
```

## 高速化・最適化の工夫

属性を含む型を具象型へ展開したあと、冗長 avtab エントリをマージしてカーネル側ハッシュ探索回数を減らす。
neverallow チェックを expand 時に残すことで、不正ポリシーの書き出しを防ぎつつコンパイル時に検証コストを集中させる。

## まとめ

expand が意味論を avtab へ落とし、optimize がランタイム向けに avtab を圧縮する。

## 関連する章

- [第7章 link](07-module-link.md)
- [第9章 checkpolicy](../part03-checkpolicy/09-checkpolicy-main.md)
