# 第5章 symtab と ebitmap

> 本章で読むソース
>
> - [`libsepol/src/symtab.c`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/symtab.c)
> - [`libsepol/src/ebitmap.c`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/ebitmap.c)
> - [`libsepol/include/sepol/policydb/symtab.h`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/include/sepol/policydb/symtab.h)

## この章の狙い

ポリシー内の名前解決に使う symtab と、型属性などの集合演算に使う ebitmap の実装を読む。
expand と optimize が型集合をどう扱うかの前提となる。

## 前提

第3章の `policydb_t.symtab[]` と `type_attr_map` を理解していること。

## symtab と hashtab

symtab は内部で hashtab を使い、djb2 風ハッシュと `strcmp` 比較でシンボル名を管理する。

[`libsepol/src/symtab.c` L18-L40](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/symtab.c#L18-L40)

```c
static unsigned int symhash(hashtab_t h, const_hashtab_key_t key)
{
	unsigned int hash = 5381;
	unsigned char c;

	while ((c = *(unsigned const char *)key++))
		hash = ((hash << 5) + hash) ^ c;

	return hash & (h->size - 1);
}

static int symcmp(hashtab_t h
		  __attribute__ ((unused)), const_hashtab_key_t key1,
		  const_hashtab_key_t key2)
{
	return strcmp(key1, key2);
}

int symtab_init(symtab_t * s, unsigned int size)
{
	s->table = hashtab_create(symhash, symcmp, size);
	if (!s->table)
		return -1;
```

`policydb_init` は `SYM_NUM` 種類の symtab を `symtab_sizes[]` に応じた初期サイズで初期化する（第3章）。

## ebitmap のノード構造

ebitmap は密なビット配列ではなく、`ebitmap_node_t` の連結リストで区間を表現する。
`ebitmap_or` は2つの集合の和をマージしながら新ノード列を構築する。

[`libsepol/src/ebitmap.c` L18-L42](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/ebitmap.c#L18-L42)

```c
int ebitmap_or(ebitmap_t * dst, const ebitmap_t * e1, const ebitmap_t * e2)
{
	const ebitmap_node_t *n1, *n2;
	ebitmap_node_t *new = NULL, **prev;

	ebitmap_init(dst);

	prev = &dst->node;
	n1 = e1->node;
	n2 = e2->node;
	while (n1 || n2) {
		new = (ebitmap_node_t *) malloc(sizeof(ebitmap_node_t));
		if (!new) {
			ebitmap_destroy(dst);
			return -ENOMEM;
		}
		if (n1 && n2 && n1->startbit == n2->startbit) {
			new->startbit = n1->startbit;
			new->map = n1->map | n2->map;
			n1 = n1->next;
			n2 = n2->next;
```

## 集合演算ファミリ

属性展開では和、積、差の演算が頻出する。

[`libsepol/src/ebitmap.c` L59-L69](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/ebitmap.c#L59-L69)

```c
int ebitmap_union(ebitmap_t * dst, const ebitmap_t * e1)
{
	ebitmap_t tmp;

	if (ebitmap_or(&tmp, dst, e1))
		return -1;
	ebitmap_destroy(dst);
	dst->node = tmp.node;
	dst->highbit = tmp.highbit;

	return 0;
}
```

[`libsepol/src/ebitmap.c` L72-L92](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/ebitmap.c#L72-L92)

```c
int ebitmap_and(ebitmap_t *dst, const ebitmap_t *e1, const ebitmap_t *e2)
{
	const ebitmap_node_t *n1, *n2;
	ebitmap_node_t *new = NULL, **prev;

	ebitmap_init(dst);

	prev = &dst->node;
	n1 = e1->node;
	n2 = e2->node;
	while (n1 && n2) {
		if (n1->startbit == n2->startbit) {
			if (n1->map & n2->map) {
				new = malloc(sizeof(ebitmap_node_t));
				if (!new) {
					ebitmap_destroy(dst);
					return -ENOMEM;
				}
				new->startbit = n1->startbit;
				new->map = n1->map & n2->map;
```

## policydb との接続

`type_attr_map` は属性から型集合への ebitmap 配列である。
`expand_convert_type_set` はルール中の型集合を具象型へ展開するとき ebitmap を走査する（第8章）。

```mermaid
flowchart LR
  ATTR[属性名] --> MAP[type_attr_map]
  MAP --> EB[ebitmap 型集合]
  EB --> EXP[expand TE ルール]
  EXP --> AVT[avtab エントリ]
```

## 比較と検証

`ebitmap_cmp` と `ebitmap_hamming_distance` はポリシー差分やテストで集合の一致を検証する。

[`libsepol/src/ebitmap.c` L235-L247](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/ebitmap.c#L235-L247)

```c
int ebitmap_hamming_distance(const ebitmap_t * e1, const ebitmap_t * e2)
{
	int rc;
	ebitmap_t tmp;
	int distance;
	if (ebitmap_cmp(e1, e2))
		return 0;
	rc = ebitmap_xor(&tmp, e1, e2);
	if (rc < 0)
		return -1;
	distance = ebitmap_cardinality(&tmp);
	ebitmap_destroy(&tmp);
	return distance;
}
```

## 高速化・最適化の工夫

疎な型 ID 空間を ebitmap の区間ノードで表現し、属性を持つ数千型規模でも無駄な密配列を避ける。
symtab の hashtab はシンボル名解決をパースと link のホットパスで O(1) 平均に保つ。

`ebitmap_set_bit` は区間ノードを挿入または更新し、疎なビット集合へ単一ビットを立てる。

[`libsepol/src/ebitmap.c` L369-L377](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/ebitmap.c#L369-L377)

```c
int ebitmap_set_bit(ebitmap_t * e, unsigned int bit, int value)
{
	ebitmap_node_t *n, *prev, *new;
	uint32_t startbit = bit & ~(MAPSIZE - 1);
	uint32_t highbit = startbit + MAPSIZE;

	if (highbit == 0) {
		ERR(NULL, "bitmap overflow, bit 0x%x", bit);
		return -EINVAL;
```

## まとめ

symtab が名前から ID へ、ebitmap が型集合の演算を担い、expand がその結果を avtab へ落とす。

## 関連する章

- [第3章 policydb](03-policydb-overview.md)
- [第8章 expand](../part02-policy/08-expand-optimize.md)
