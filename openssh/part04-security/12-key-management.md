# 第12章 鍵管理

> 本章で読むソース
>
> - [`sshkey.h`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.h#L1-L344)
> - [`sshkey.c`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L1-L3692)
> - [`authfile.h`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfile.h#L1-L54)
> - [`authfile.c`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfile.c#L1-L514)
> - [`ssh-agent.c`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/ssh-agent.c#L1-L2624)
> - [`authfd.h`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfd.h#L1-L124)
> - [`krl.c`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/krl.c#L1-L1388)
> - [`krl.h`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/krl.h#L1-L67)
> - [`ssh-sk.h`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/ssh-sk.h#L1-L79)
> - [`ssh-sk.c`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/ssh-sk.c#L47-L50)

## この章の狙い

OpenSSH は認証と暗号化の基盤として複数の鍵タイプをサポートし、ファイルへの保存・読み込み、エージェント管理、失効、ハードウェアトークン対応までを一貫した API で提供する。
本章では、鍵のデータ構造、生成・署名・検証の流れ、ファイル形式、ssh-agent との通信、鍵失効リスト（KRL）、FIDO/U2F セキュリティキー対応を解説する。

## 前提

- 第5章（認証フレームワーク）と第6章（公開鍵認証）で SSH 認証プロトコルにおける鍵の使い方を理解していること
- 公開鍵暗号の基礎（RSA、ECDSA、Ed25519）の知識

## 鍵操作の全体フロー

```mermaid
graph LR
    G[sshkey_generate] --> S[sshkey_save_private<br/>authfile.c]
    S --> F[秘密鍵ファイル]
    F --> L[sshkey_load_private<br/>authfile.c]
    L --> M[メモリ上の sshkey]
    M --> SG[sshkey_sign]
    M --> V[sshkey_verify]
    M --> A[ssh_add_identity_constrained<br/>→ ssh-agent]
    A --> AG[ssh-agent 常駐]
    AG --> AS[ssh_agent_sign]
    F --> P[sshkey_load_public<br/>.pub ファイル]
```

## sshkey 構造体と鍵タイプ

[`sshkey.h` L117-L139](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.h#L117-L139) で定義される `struct sshkey` が、すべての鍵操作の中心データ構造である。

```c
// sshkey.h L117-L139
struct sshkey {
	int	 type;
	int	 flags;
	int	 ecdsa_nid;	/* NID of curve */
	EVP_PKEY *pkey;
	u_char	*ed25519_sk;
	u_char	*ed25519_pk;
	char	*sk_application;
	uint8_t	sk_flags;
	struct sshbuf *sk_key_handle;
	struct sshbuf *sk_reserved;
	struct sshkey_cert *cert;
	u_char	*shielded_private;
	size_t	shielded_len;
	u_char	*shield_prekey;
	size_t	shield_prekey_len;
};
```

型 `type` は [`sshkey.h` L59-L71](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.h#L59-L71) の列挙型で定められる。

```c
// sshkey.h L59-L71
enum sshkey_types {
	KEY_RSA,
	KEY_ECDSA,
	KEY_ED25519,
	KEY_RSA_CERT,
	KEY_ECDSA_CERT,
	KEY_ED25519_CERT,
	KEY_ECDSA_SK,
	KEY_ECDSA_SK_CERT,
	KEY_ED25519_SK,
	KEY_ED25519_SK_CERT,
	KEY_UNSPEC
};
```

各鍵タイプは対応する実装オブジェクト（`struct sshkey_impl`）を持ち、[`sshkey.c` L118-L150](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L118-L150) の `keyimpls[]` 配列に登録される。
`sshkey_sign` や `sshkey_verify` は、鍵の型から実装テーブルを検索して適切な関数ポインタを呼び出す。
このポリモーフィックな設計により、新しい鍵タイプの追加が `keyimpls[]` へのエントリ追加だけで済む。

**シールド（shielding）**: `shielded_private` フィールドは、メモリ上に長期間置かれる秘密鍵を暗号化して保護する仕組みである。
[`sshkey.c` L1632-L1705](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L1632-L1705) の `sshkey_shield_private` は、ランダムなプリキーから導出した鍵で秘密鍵を AES-256-CTR 暗号化し、署名の直前に [`sshkey_sign` の先頭](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L2199) で `sshkey_unshield_private` により復号する。
プリキー自体は `mmap(MAP_CONCEAL)` で割り当てられ、コアダンプやスワップに書き出されない。

## 鍵の生成

[`sshkey.c` L1494-L1518](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L1494-L1518) の `sshkey_generate` は、タイプとビット数を受け取り、対応する実装の `generate` 関数を呼び出す。

```c
// sshkey.c L1494-L1518
int
sshkey_generate(int type, u_int bits, struct sshkey **keyp)
{
	const struct sshkey_impl *impl;
	if (keyp == NULL || sshkey_type_is_cert(type))
		return SSH_ERR_INVALID_ARGUMENT;
	*keyp = NULL;
	if ((impl = sshkey_impl_from_type(type)) == NULL)
		return SSH_ERR_KEY_TYPE_UNKNOWN;
	if (impl->funcs->generate == NULL)
		return SSH_ERR_FEATURE_UNSUPPORTED;
	if ((k = sshkey_new(KEY_UNSPEC)) == NULL)
		return SSH_ERR_ALLOC_FAIL;
	k->type = type;
	if ((ret = impl->funcs->generate(k, bits)) != 0) {
		sshkey_free(k);
		return ret;
	}
	*keyp = k;
	return 0;
}
```

RSA の場合は OpenSSL の `EVP_PKEY_keygen`、Ed25519 の場合は OpenSSH 組み込みの `crypto_sign_ed25519_keypair`（`ed25519.o` 実装）が実際の生成処理を担う。
ECDSA は NIST P-256/P-384/P-521 の3種類の曲線をサポートし、`ecdsa_nid` で判別する。

## 署名と検証

[`sshkey.c` L2181-L2218](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L2181-L2218) の `sshkey_sign` は、署名前にシールドを解除し、FIDO 鍵の場合は `sshsk_sign` で、PKCS#11 鍵の場合は `pkcs11_sign` で、通常鍵の場合は対応する実装の `sign` 関数で署名を生成する。

```c
// sshkey.c L2181-L2218
int
sshkey_sign(struct sshkey *key,
    u_char **sigp, size_t *lenp,
    const u_char *data, size_t datalen,
    const char *alg, const char *sk_provider, const char *sk_pin, u_int compat)
{
	if ((r = sshkey_unshield_private(key)) != 0)
		return r;
	if (sshkey_is_sk(key)) {
		r = sshsk_sign(sk_provider, key, sigp, lenp, data,
		    datalen, compat, sk_pin);
	} else if ((key->flags & SSHKEY_FLAG_EXT) != 0) {
		r = pkcs11_sign(key, sigp, lenp, data, datalen,
		    alg, sk_provider, sk_pin, compat);
	} else {
		r = impl->funcs->sign(key, sigp, lenp, data, datalen,
		    alg, sk_provider, sk_pin, compat);
	}
	if (was_shielded && (r2 = sshkey_shield_private(key)) != 0)
		return r2;
	return r;
}
```

[`sshkey.c` L2224-L2240](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L2224-L2240) の `sshkey_verify` は、対応する実装の `verify` 関数を呼び出すだけである。
RSA の署名アルゴリズムは互換性のために `ssh-rsa`（SHA1）、`rsa-sha2-256`、`rsa-sha2-512` の3種類が存在し、`alg` パラメータで選択する。

```c
// sshkey.c L2224-L2240
int
sshkey_verify(const struct sshkey *key,
    const u_char *sig, size_t siglen,
    const u_char *data, size_t dlen, const char *alg, u_int compat,
    struct sshkey_sig_details **detailsp)
{
	const struct sshkey_impl *impl;
	if ((impl = sshkey_impl_from_key(key)) == NULL)
		return SSH_ERR_KEY_TYPE_UNKNOWN;
	return impl->funcs->verify(key, sig, siglen, data, dlen,
	    alg, compat, detailsp);
}
```

## 鍵ファイル形式

### OpenSSH 専用形式

[`sshkey.c` L67-L75](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L67-L75) に定義される定数が、OpenSSH 専用の秘密鍵ファイル形式（RFC なし）を規定する。

```c
// sshkey.c L67-L75
#define MARK_BEGIN		"-----BEGIN OPENSSH PRIVATE KEY-----\n"
#define MARK_END		"-----END OPENSSH PRIVATE KEY-----\n"
#define KDFNAME			"bcrypt"
#define AUTH_MAGIC		"openssh-key-v1"
#define SALT_LEN		16
#define DEFAULT_CIPHERNAME	"aes256-ctr"
#define	DEFAULT_ROUNDS		24
```

[`sshkey.c` L2816-L2915](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L2816-L2915) の `sshkey_private_to_blob2` が、この形式で秘密鍵をシリアライズする。
形式は、平文のヘッダ部（暗号名、KDF 名、KDF パラメータ、公開鍵のリスト）と暗号化された本体（秘密鍵＋コメント）から構成される。

パスフレーズによる保護は `bcrypt_pbkdf` で鍵を導出する。
`rounds`（デフォルト24）は bcrypt のコストパラメータで、値を大きくするほど総当たり攻撃に耐性が高まる。

### PEM / PKCS#8 形式

OpenSSL が有効な場合、[`sshkey.c` L3397-L3409](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L3397-L3409) で示される通り、従来の PEM 形式（`-----BEGIN RSA PRIVATE KEY-----`）や PKCS#8 形式（`-----BEGIN PRIVATE KEY-----`）でも入出力できる。

### 公開鍵ファイル（.pub）

公開鍵は `sshkey_write` で `ssh-rsa AAAAB3Nza... comment` の一行形式で保存される。

## authfile.c によるファイル入出力

[`authfile.c` L59-L78](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfile.c#L59-L78) の `sshkey_save_private` が秘密鍵のファイル保存を担当する。

```c
// authfile.c L59-L78
int
sshkey_save_private(struct sshkey *key, const char *filename,
    const char *passphrase, const char *comment,
    int format, const char *openssh_format_cipher, int openssh_format_rounds)
{
	if ((r = sshkey_private_to_fileblob(key, keyblob, passphrase, comment,
	    format, openssh_format_cipher, openssh_format_rounds)) != 0)
		goto out;
	if ((r = sshkey_save_private_blob(keyblob, filename)) != 0)
		goto out;
}
```

秘密鍵のファイルパーミッションは [`authfile.c` L81-L107](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfile.c#L81-L107) の `sshkey_perm_ok` で厳格にチェックされる。
ファイルが自分以外のユーザーから読み取り可能（`st_mode & 077` が非ゼロ）であれば、警告を出力して読み込みを拒否する。

[`authfile.c` L109-L131](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfile.c#L109-L131) の `sshkey_load_private_type` は、ファイルを開いてパーミッションチェックを行い、[`authfile.c` L141-L160](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfile.c#L141-L160) の `sshkey_load_private_type_fd` で実際のパースを実行する。
パスフレーズが間違っている場合は `SSH_ERR_KEY_WRONG_PASSPHRASE` を返す。

## ssh-agent: 鍵保持デーモン

`ssh-agent` は、ユーザーの秘密鍵をメモリ上に保持し、署名要求に応答する常駐デーモンである。

[`authfd.h` L43-L64](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfd.h#L43-L64) がエージェントとの通信 API を定義する。

```c
// authfd.h 主要 API
int	ssh_get_authentication_socket(int *fdp);
int	ssh_add_identity_constrained(int sock, struct sshkey *key,
    const char *comment, u_int life, u_int confirm, const char *provider,
    struct dest_constraint **dest_constraints, size_t ndest_constraints);
int	ssh_remove_identity(int sock, const struct sshkey *key);
int	ssh_agent_sign(int sock, const struct sshkey *key,
    u_char **sigp, size_t *lenp,
    const u_char *data, size_t datalen, const char *alg, u_int compat);
```

エージェントプロトコルは Unix ドメインソケット（`SSH_AUTH_SOCK` 環境変数で指定）を経由する。
`ssh-add` は `ssh_add_identity_constrained` で鍵を追加し、`ssh-keygen` などのツールは `ssh_agent_sign` で署名を依頼する。

[`authfd.h` L72-L123](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/authfd.h#L72-L123) には、エージェントプロトコルのメッセージ定数が定義されている。
`SSH2_AGENTC_SIGN_REQUEST`（13）や `SSH2_AGENTC_ADD_IDENTITY`（17）などの要求種別が、ソケット経由で送受信される。

`ssh-agent` はデフォルトで鍵をメモリ上に無期限で保持するが、`-t` オプションによる生存時間制限や、確認要求フラグ（`SSH_AGENT_CONSTRAIN_CONFIRM`）による利用時のタッチ確認もサポートする。
これらの制約は [`ssh-add(1)` で `-t` や `-c` オプションとして指定され、`ssh_add_identity_constrained` でエージェントに渡される。

## ssh-add: 鍵管理ツール

`ssh-add` はエージェントへの鍵追加・削除・一覧表示を行う。
[`ssh-add.c` L112-L128](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/ssh-add.c#L112-L128) の `delete_one` は、`ssh_remove_identity` でエージェントから鍵を削除する典型的な処理を示す。

```c
// ssh-add.c L112-L128
static int
delete_one(int agent_fd, const struct sshkey *key, const char *comment,
    const char *path, int qflag)
{
	if ((r = ssh_remove_identity(agent_fd, key)) != 0) {
		fprintf(stderr, "Could not remove identity \"%s\": %s\n",
		    path, ssh_err(r));
		return r;
	}
	if (!qflag) {
		fprintf(stderr, "Identity removed: %s %s (%s)\n", path,
		    sshkey_type(key), comment ? comment : "no comment");
	}
	return 0;
}
```

`ssh-add` は標準入力からの鍵読み取り（`delete_stdin`）やファイルからの公開鍵指定（`delete_file`）もサポートする。
`-L` オプションでエージェント内の全公開鍵を表示できる。

## 鍵失効リスト（KRL）

[`krl.c`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/krl.c#L1-L1388) は、**KRL（Key Revocation List）** の実装を提供する。
KRL は SSH 証明書や公開鍵を失効させるためのバイナリ形式で、`ssh-keygen -k` で生成される。

[`krl.h` L50-L63](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/krl.h#L50-L63) の API は、以下の4種類の失効指定をサポートする。

- `ssh_krl_revoke_cert_by_serial`: 証明書のシリアル番号で失効
- `ssh_krl_revoke_cert_by_serial_range`: シリアル番号の範囲で失効
- `ssh_krl_revoke_cert_by_key_id`: 鍵 ID 文字列で失効
- `ssh_krl_revoke_key_explicit`: 鍵の blob 自体で失効

[`krl.c` L48-L99](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/krl.c#L48-L99) で定義される内部データ構造は、RB 木（Red-Black Tree）を使用して失効エントリを管理する。
シリアル番号の範囲、鍵 ID、鍵 blob、SHA1/SHA256 フィンガープリントの各ツリーを持ち、効率的な検索を実現する。

```c
// krl.c L53-L99
struct revoked_serial {
	uint64_t lo, hi;
	RB_ENTRY(revoked_serial) tree_entry;
};
struct revoked_key_id {
	char *key_id;
	RB_ENTRY(revoked_key_id) tree_entry;
};
struct revoked_blob {
	u_char *blob;
	size_t len;
	RB_ENTRY(revoked_blob) tree_entry;
};
struct ssh_krl {
	uint64_t krl_version;
	uint64_t generated_date;
	uint64_t flags;
	char *comment;
	struct revoked_blob_tree revoked_keys;
	struct revoked_blob_tree revoked_sha1s;
	struct revoked_blob_tree revoked_sha256s;
	struct revoked_certs_list revoked_certs;
};
```

`ssh_krl_check_key` が、ある鍵が KRL に含まれているかを判定する関数である。
認証のたびに `authfile.c` の `sshkey_check_revoked` から呼び出される。

## FIDO/U2F セキュリティキー対応

[`ssh-sk.c`](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/ssh-sk.c#L1-L892) は、FIDO/U2F 規格に準拠したハードウェアセキュリティキー（YubiKey など）との連携を実現する。

[`ssh-sk.c` L56-L79](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/ssh-sk.c#L56-L79) の `struct sshsk_provider` は、セキュリティキーとの通信を抽象化する。
ミドルウェア（例: `libfido2`）は動的ロードされる。

```c
// ssh-sk.c L56-L79
struct sshsk_provider {
	char *path;
	void *dlhandle;
	int (*sk_enroll)(int alg, const uint8_t *challenge,
	    size_t challenge_len, const char *application, uint8_t flags,
	    const char *pin, struct sk_option **opts,
	    struct sk_enroll_response **enroll_response);
	int (*sk_sign)(int alg, const uint8_t *message, size_t message_len,
	    const char *application,
	    const uint8_t *key_handle, size_t key_handle_len,
	    uint8_t flags, const char *pin, struct sk_option **opts,
	    struct sk_sign_response **sign_response);
	int (*sk_load_resident_keys)(const char *pin, struct sk_option **opts,
	    struct sk_resident_key ***rks, size_t *nrks);
};
```

`ssh-sk.h` の `sshsk_enroll`、`sshsk_sign`、`sshsk_load_resident` が上位層に公開される。
`ssh-keygen -t ecdsa-sk` で FIDO 鍵を生成すると、秘密鍵の実体はセキュリティキー内部に生成され、ホストには **キーハンドル** だけが保存される。
署名のたびにキーハンドルがセキュリティキーに送られ、ユーザーのタッチ確認（`SSH_SK_USER_PRESENCE_REQD`）を経て署名が返される。

[`sshkey.c` L2201-L2213](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/sshkey.c#L2201-L2213) で `sshkey_is_sk(key)` が真の場合、`sshsk_sign` が呼ばれる。

```c
// sshkey.c L2201-L2213
	if (sshkey_is_sk(key)) {
		r = sshsk_sign(sk_provider, key, sigp, lenp, data,
		    datalen, compat, sk_pin);
	} else if ((key->flags & SSHKEY_FLAG_EXT) != 0) {
		r = pkcs11_sign(key, sigp, lenp, data, datalen,
		    alg, sk_provider, sk_pin, compat);
	} else {
		if (impl->funcs->sign == NULL)
			r = SSH_ERR_SIGN_ALG_UNSUPPORTED;
		else {
```

## まとめ

OpenSSH の鍵管理は、以下の層で構成される。

1. **sshkey** 層: 鍵の型に依存しない統一 API を提供する。実装テーブルにより、RSA・ECDSA・Ed25519・SK 鍵の追加が容易である
2. **authfile** 層: ファイル入出力とパーミッションチェックを担当する。bcrypt_pbkdf によるパスフレーズ保護が安全性の要である
3. **ssh-agent** 層: 秘密鍵をメモリに保持し、署名要求に応答する。プロセス分離により、利用中の鍵がファイルから盗まれるリスクを低減する
4. **KRL** 層: RB 木による高速な失効確認を提供する
5. **ssh-sk** 層: FIDO セキュリティキーとの連携により、秘密鍵をハードウェアに隔離する

特に、`sshkey_impl` によるポリモーフィックな設計と、シールドによるメモリ保護は、長期運用される sshd の鍵が攻撃者に奪取されるリスクを低減する工夫である。

## 関連する章

- 第3章（鍵交換）: 鍵交換プロトコルでの署名の使われ方
- 第5章（認証フレームワーク）: 公開鍵認証における鍵検証
- 第6章（公開鍵認証）: authorized_keys による鍵の許可
- 第11章（権限分離）: ホスト鍵の保護機構
