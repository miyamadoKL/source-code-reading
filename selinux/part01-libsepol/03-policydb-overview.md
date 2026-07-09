# 第3章 policydb とポリシーデータ構造

> 本章で読むソース
>
> - [`libsepol/include/sepol/policydb/policydb.h`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/include/sepol/policydb/policydb.h)
> - [`libsepol/src/policydb.c`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/policydb.c)

## この章の狙い

`policydb_t` が保持するシンボル表、高レベルルール、コンパイル済み avtab の関係を読み、以降の link と expand がどのフィールドを書き換えるかを把握する。

## 前提

TE ルール、RBAC、MLS、条件付きポリシーの用語をざっくり知っていること。

## policydb_t の骨格

公開ヘッダの `policydb_t` はポリシー種別、MLS フラグ、シンボル表配列、コンパイル済みルール格納域を1構造体にまとめる。

[`libsepol/include/sepol/policydb/policydb.h` L512-L536](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/include/sepol/policydb/policydb.h#L512-L536)

```c
typedef struct policydb {
#define POLICY_KERN SEPOL_POLICY_KERN
#define POLICY_BASE SEPOL_POLICY_BASE
#define POLICY_MOD SEPOL_POLICY_MOD
	uint32_t policy_type;
	char *name;
	char *version;
	int  target_platform;

	/* Set when the policydb is modified such that writing is unsupported */
	int unsupported_format;

	/* Whether this policydb is mls, should always be set */
	int mls;

	/* symbol tables */
	symtab_t symtab[SYM_NUM];
#define p_commons symtab[SYM_COMMONS]
#define p_classes symtab[SYM_CLASSES]
#define p_roles symtab[SYM_ROLES]
#define p_types symtab[SYM_TYPES]
#define p_users symtab[SYM_USERS]
#define p_bools symtab[SYM_BOOLS]
#define p_levels symtab[SYM_LEVELS]
#define p_cats symtab[SYM_CATS]
```

カーネル向けバイナリでは `te_avtab` と `te_cond_avtab` が許可ベクタの本体になる。

[`libsepol/include/sepol/policydb/policydb.h` L568-L578](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/include/sepol/policydb/policydb.h#L568-L578)

```c
	/* compiled storage of rules - use for the kernel policy */

	/* type enforcement access vectors and transitions */
	avtab_t te_avtab;

	/* bools indexed by (value - 1) */
	cond_bool_datum_t **bool_val_to_struct;
	/* type enforcement conditional access vectors and transitions */
	avtab_t te_cond_avtab;
	/* linked list indexing te_cond_avtab by conditional */
	cond_list_t *cond_list;
```

オブジェクトコンテキスト（初期 SID、ポート、ノードなど）は `ocontexts` 配列に格納される。

[`libsepol/include/sepol/policydb/policydb.h` L586-L593](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/include/sepol/policydb/policydb.h#L586-L593)

```c
	/* security contexts of initial SIDs, unlabeled file systems,
	   TCP or UDP port numbers, network interfaces and nodes */
	ocontext_t *ocontexts[OCON_NUM];

	/* security contexts for files in filesystems that cannot support
	   a persistent label mapping or use another 
	   fixed labeling behavior. */
	genfs_t *genfs;
```

## 高レベルルールとモジュール

パース直後は `avrule_block_t` 連結リスト `global` に高レベル TE ルールが残る。
link と expand がこれを `te_avtab` へ落とす。

[`libsepol/include/sepol/policydb/policydb.h` L563-L566](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/include/sepol/policydb/policydb.h#L563-L566)

```c
	/* module rule storage */
	avrule_block_t *global;
	/* avrule_decl index used for link/expand */
	avrule_decl_t **decl_val_to_struct;
```

型属性の展開には `type_attr_map` と `attr_type_map` が使われる（optimize でも参照）。

[`libsepol/include/sepol/policydb/policydb.h` L602-L604](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/include/sepol/policydb/policydb.h#L602-L604)

```c
	ebitmap_t *type_attr_map;

	ebitmap_t *attr_type_map;	/* not saved in the binary policy */
```

## policydb_init

空の policydb を使う前に、各サブテーブルを初期状態へ整える。

[`libsepol/src/policydb.c` L931-L958](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/policydb.c#L931-L958)

```c
int policydb_init(policydb_t * p)
{
	int i, rc;

	memset(p, 0, sizeof(policydb_t));

	for (i = 0; i < SYM_NUM; i++) {
		p->sym_val_to_name[i] = NULL;
		rc = symtab_init(&p->symtab[i], symtab_sizes[i]);
		if (rc)
			goto err;
	}

	/* initialize the module stuff */
	for (i = 0; i < SYM_NUM; i++) {
		if (symtab_init(&p->scope[i], symtab_sizes[i])) {
			goto err;
		}
	}
	if ((p->global = avrule_block_create()) == NULL ||
	    (p->global->branch_list = avrule_decl_create(1)) == NULL) {
		goto err;
	}
	p->decl_val_to_struct = NULL;

	rc = avtab_init(&p->te_avtab);
	if (rc)
		goto err;
```

## ポリシー種別の違い

| policy_type | 用途 |
|---|---|
| `POLICY_KERN` | カーネルへロードするバイナリ |
| `POLICY_BASE` | モジュール方式のベース |
| `POLICY_MOD` | 単一モジュール |

`checkmodule` はモジュールを生成し、`semanage` は base と mod をストアで合成する（第7章、第17章）。

```mermaid
flowchart LR
  PARSE[パース結果 global] --> LINK[link_modules]
  LINK --> EXP[expand_module]
  EXP --> AVT[te_avtab]
  AVT --> WRITE[policydb_write]
```

## 高速化・最適化の工夫

シンボル値から構造体への逆引き配列（`type_val_to_struct` など）により、ルール展開時の ID 解決を O(1) 配列アクセスに落とす。
avtab は別構造として分離され、カーネルが直接読める密な形式へコンパイル時に一度だけ変換する。

## まとめ

policydb は「編集用の高レベル表現」と「カーネル向け te_avtab」の二層を1オブジェクトに保持する。
link と expand がその境界を越える処理である。

## 関連する章

- [第4章 avtab](04-avtab-sidtab.md)
- [第6章 読み書き](../part02-policy/06-policydb-read-write.md)
