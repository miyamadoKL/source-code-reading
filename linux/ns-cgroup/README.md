# Linux カーネル namespace と cgroup

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の namespace 隔離と cgroup v2 資源制御を読み解く分冊である。
コンテナ実行の土台となる `nsproxy`、各 namespace、cgroup 階層、主要コントローラをソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md) と [プロセスとスケジューラ](../sched/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  nsproxy 基盤を押さえてから各 namespace、cgroup v2 コア、主要コントローラへ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
network namespace の詳細は network 分冊、memcg の charge 詳細は [mm 分冊 31 章](../mm/part05-advanced/31-memcg.md) へ委譲する。

## 第0部　隔離と資源制御の基盤

1. [隔離と資源制御の全体像](part00-foundation/01-isolation-overview.md)
2. [nsproxy と namespace のライフサイクル](part00-foundation/02-nsproxy-lifecycle.md)
3. [clone、unshare、setns の入口](part00-foundation/03-clone-unshare-setns.md)

## 第1部　各 namespace

4. [mount namespace と propagation](part01-namespaces/04-mount-namespace.md)
5. [PID namespace の階層と translation](part01-namespaces/05-pid-namespace.md)
6. [user namespace と uid map](part01-namespaces/06-user-namespace.md)
7. [UTS namespace](part01-namespaces/07-uts-namespace.md)
8. [IPC namespace](part01-namespaces/08-ipc-namespace.md)
9. [network namespace の概観](part01-namespaces/09-net-namespace-overview.md)
10. [time namespace](part01-namespaces/10-time-namespace.md)

## 第2部　cgroup v2 コア

11. [cgroup v2 階層と kernfs](part02-cgroup-core/11-cgroup-hierarchy-kernfs.md)
12. [css と cgroup_subsys のライフサイクル](part02-cgroup-core/12-css-lifecycle.md)
13. [タスクの cgroup 所属と migration](part02-cgroup-core/13-cgroup-attach-migration.md)
14. [cgroup namespace と rstat](part02-cgroup-core/14-cgroup-ns-rstat.md)

## 第3部　主要コントローラ

15. [cpu コントローラと sched 連携](part03-controllers/15-cpu-controller.md)
16. [memory コントローラと memcg 境界](part03-controllers/16-memory-controller.md)
17. [io コントローラ](part03-controllers/17-io-controller.md)
18. [pids コントローラ](part03-controllers/18-pids-controller.md)
19. [cpuset コントローラ](part03-controllers/19-cpuset-controller.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコンテナ基盤分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
