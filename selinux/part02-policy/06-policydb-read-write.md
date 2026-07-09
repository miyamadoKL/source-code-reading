# 第6章 policydb の読み書き

> 本章で読むソース
>
> - [`libsepol/src/policydb.c`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/policydb.c)
> - [`libsepol/src/write.c`](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/write.c)

## この章の狙い

バイナリポリシーの読み込み `policydb_read` と書き出し `policydb_write` のフォーマット判定、互換性処理を追う。
checkpolicy 出力からカーネルロードまでのバイナリ I/O 経路を理解する。

## 前提

第3章の policydb 構造と第4章の avtab を読んでいること。

## policydb_read の入口

`policydb_read` はマジック番号と文字列長からポリシー種別を判定し、`policydb_compat` 情報を選ぶ。

[`libsepol/src/policydb.c` L4185-L4208](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/policydb.c#L4185-L4208)

```c
/*
 * Read the configuration data from a policy database binary
 * representation file into a policy database structure.
 */
int policydb_read(policydb_t * p, struct policy_file *fp, unsigned verbose)
{

	unsigned int i, j, r_policyvers;
	uint32_t buf[5], nprim;
	size_t len, nel;
	char *policydb_str;
	const struct policydb_compat_info *info;
	unsigned int policy_type, bufindex;
	ebitmap_node_t *tnode;
	int rc;

	/* Read the magic number and string length. */
	rc = next_entry(buf, fp, sizeof(uint32_t) * 2);
	if (rc < 0)
		return POLICYDB_ERROR;
	for (i = 0; i < 2; i++)
		buf[i] = le32_to_cpu(buf[i]);

	if (buf[0] == POLICYDB_MAGIC) {
		policy_type = POLICY_KERN;
```

`POLICYDB_MAGIC` と `POLICYDB_MOD_MAGIC` でカーネルポリシーとモジュールを区別する。

## policy_file 抽象化

読み書きは `struct policy_file` 経由で、stdio、メモリマップ、メモリバッファを共通化する。
checkpolicy の `-b` 入力は `PF_USE_MEMORY` でマップしたバッファを渡す。

[`checkpolicy/checkpolicy.c` L568-L577](https://github.com/SELinuxProject/selinux/blob/3.10/checkpolicy/checkpolicy.c#L568-L577)

```c
		policy_file_init(&pf);
		pf.type = PF_USE_MEMORY;
		pf.data = map;
		pf.len = sb.st_size;
		if (policydb_init(&policydb)) {
			fprintf(stderr, "%s:  policydb_init:  Out of memory!\n",
				argv[0]);
			exit(1);
		}
		ret = policydb_read(&policydb, &pf, 1);
```

## policydb_write

書き出し前に `unsupported_format` を検査し、互換性情報 `info` を選んでシリアライズする。

[`libsepol/src/write.c` L2228-L2245](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/write.c#L2228-L2245)

```c
 * Write the configuration data in a policy database
 * structure to a policy database binary representation
 * file.
 */
int policydb_write(policydb_t * p, struct policy_file *fp)
{
	unsigned int i, num_syms;
	uint32_t buf[32], config;
	size_t items, items2, len;
	const struct policydb_compat_info *info;
	struct policy_data pd;
	const char *policydb_str;

	if (p->unsupported_format)
		return POLICYDB_UNSUPPORTED;

	pd.fp = fp;
	pd.p = p;
```

checkpolicy は展開後 `policydb.policy_type = POLICY_KERN` に設定してから `policydb_write` する。

[`checkpolicy/checkpolicy.c` L678-L693](https://github.com/SELinuxProject/selinux/blob/3.10/checkpolicy/checkpolicy.c#L678-L693)

```c
		if (!cil) {
			if (!conf) {
				policydb.policy_type = POLICY_KERN;

				policy_file_init(&pf);
				pf.type = PF_USE_STDIO;
				pf.fp = outfp;
				if (sort) {
					ret = policydb_sort_ocontexts(&policydb);
					if (ret) {
						fprintf(stderr, "%s:  error sorting ocontexts\n",
						argv[0]);
						exit(1);
					}
				}
				ret = policydb_write(&policydb, &pf);
```

## バージョン互換

`policydb_compat` 配列はターゲットプラットフォームとシンボル数の組み合わせごとにエントリを持つ（第3章）。
古いバイナリを読むとき、未知フィールドは `handle_unknown` 設定に従って拒否または許容する。

```mermaid
flowchart LR
  BIN[バイナリファイル] --> READ[policydb_read]
  READ --> PDB[policydb_t メモリ]
  PDB --> WRITE[policydb_write]
  WRITE --> OUT[policy.N / module]
```

## policy_file と mmap

`policydb_read` は `policy_file` 経由でバイナリ先頭のマジックとバージョンを読み、`policydb_compat_info` でフィールド配置を決める。

[`libsepol/src/policydb.c` L4189-L4201](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/policydb.c#L4189-L4201)

```c
int policydb_read(policydb_t * p, struct policy_file *fp, unsigned verbose)
{

	unsigned int i, j, r_policyvers;
	uint32_t buf[5], nprim;
	size_t len, nel;
	char *policydb_str;
	const struct policydb_compat_info *info;
	unsigned int policy_type, bufindex;
	ebitmap_node_t *tnode;
	int rc;

	/* Read the magic number and string length. */
```

## 高速化・最適化の工夫

メモリマップ入力はコピーを避け、巨大ポリシーの読み込みを高速化する。
`policydb_sort_ocontexts` オプションで ocontext をソートし、カーネル側の線形探索を短くできる。

`policydb_write` は `policydb_compat_info` に従いシンボル数とフィールド配置をシリアライズする。

[`libsepol/src/write.c` L2232-L2242](https://github.com/SELinuxProject/selinux/blob/3.10/libsepol/src/write.c#L2232-L2242)

```c
int policydb_write(policydb_t * p, struct policy_file *fp)
{
	unsigned int i, num_syms;
	uint32_t buf[32], config;
	size_t items, items2, len;
	const struct policydb_compat_info *info;
	struct policy_data pd;
	const char *policydb_str;

	if (p->unsupported_format)
		return POLICYDB_UNSUPPORTED;
```

## まとめ

read と write は policydb の対称 API で、コンパイル成果物とカーネル入力の橋渡しになる。

## 関連する章

- [第3章 policydb](../part01-libsepol/03-policydb-overview.md)
- [第9章 checkpolicy](../part03-checkpolicy/09-checkpolicy-main.md)
