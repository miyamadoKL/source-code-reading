# Linux カーネル セキュリティ

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の LSM フレームワーク、capabilities、seccomp、Landlock、keys を読み解く分冊である。
DAC の上に積まれる権限モデルと、各強制機構がカーネル経路にどう差し込まれるかをソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md)、[プロセスとスケジューラ](../sched/README.md)、[namespace と cgroup](../ns-cgroup/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  層構造と `cred` を押さえてから LSM フレームワーク、capabilities、seccomp、Landlock、keys へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。

本分冊の委譲境界は次のとおりである。

- **SELinux 本体**：カーネル側 `security/selinux/` のポリシー評価・ AVC・label 管理の詳細は扱わない。
  LSM 登録とフック接続点のみ概観し、ポリシー言語・ userspace 運用は [SELinux userspace](../../selinux/README.md) 分冊へ委譲する。
- **BPF LSM**：`security/bpf/hooks.c` は LSM フック登録の薄い層に留まる。
  BPF プログラムのロード、verifier、map、JIT は [BPF とトレーシング](../bpf/README.md) 分冊へ委譲し、本分冊では LSM フックとの接点のみ触れる。
- **cgroup / namespace 連携**：device cgroup（`security/device_cgroup.c`）、user namespace の map 詳細、cgroup v2 階層は [namespace と cgroup](../ns-cgroup/README.md) 分冊へ委譲する。
  本分冊では `security_capable` や LSM フックが user namespace をどう参照するかに焦点を当てる。
- **integrity / IMA / EVM / IPE**：`security/integrity/`、`security/ipe/` は本分冊の範囲外とする。
- **個別 LSM の深掘り**：AppArmor、SMACK、TOMOYO、Yama 等は「LSM の実装例」として第1部で概観に留め、個別ポリシーエンジンの詳細は扱わない。
- **keys のハードウェア backend**：trusted-keys（TPM、TEE、CAAM 等）と encrypted-keys の個別ドライバは key type 概観に留め、プラットフォーム固有実装は深掘りしない。

## 第0部　セキュリティ基盤

1. [カーネルセキュリティの層構造と判定経路](part00-foundation/01-security-layers-overview.md)
2. [`cred` と権限判定の入口](part00-foundation/02-cred-capable-entry.md)

## 第1部　LSM フレームワーク

3. [LSM フック定義と静的呼び出し機構](part01-lsm/03-lsm-hooks-static-calls.md)
4. [LSM 登録、`lsm=` ブート順序、lockdown](part01-lsm/04-lsm-init-order-lockdown.md)
5. [`security_*` ラッパとフック実行規約](part01-lsm/05-security-wrappers-call-convention.md)
6. [blob 割り当てと `lsm_*_alloc`](part01-lsm/06-lsm-blob-alloc.md)
7. [主要 LSM の概観と SELinux カーネル接続点](part01-lsm/07-lsm-implementations-selinux-bridge.md)

## 第2部　capabilities

8. [capability ビットマップと `capget`/`capset`](part02-capabilities/08-capability-bitmap-syscalls.md)
9. [`commoncap` と VFS file capabilities](part02-capabilities/09-commoncap-file-caps.md)

## 第3部　seccomp

10. [seccomp モードとフィルタチェーン](part03-seccomp/10-seccomp-modes-filter-chain.md)
11. [BPF フィルタ検証、`seccomp_run_filters`、キャッシュ](part03-seccomp/11-seccomp-bpf-verify-run-cache.md)
12. [`SECCOMP_RET_USER_NOTIF` と supervisor API](part03-seccomp/12-seccomp-user-notif-supervisor.md)

## 第4部　Landlock

13. [Landlock ruleset と domain](part04-landlock/13-landlock-ruleset-domain.md)
14. [Landlock FS アクセス制御](part04-landlock/14-landlock-fs-access.md)
15. [Landlock ネットワーク制御と `landlock_*` syscalls](part04-landlock/15-landlock-net-syscalls.md)

## 第5部　keys

16. [`struct key` と keyring 階層](part05-keys/16-key-keyring-hierarchy.md)
17. [`keyctl` システムコール群](part05-keys/17-keyctl-syscalls.md)
18. [`request_key` と key type の概観](part05-keys/18-request-key-types-overview.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> seccomp が利用する BPF 命令セットの一般論は [BPF とトレーシング](../bpf/README.md) を参照する。
