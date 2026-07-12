# Linux カーネル BPF とトレーシング

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の BPF 仮想マシン、verifier、map、JIT、トレーシング基盤を読み解く分冊である。
ユーザー空間から `bpf` システムコールでプログラムをロードし、カーネル内で安全に実行し、tracepoint や ftrace、kprobes、perf と接続するまでをソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md)、[同期と RCU](../locking/README.md)、[割り込みと時間](../irq-time/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読み、BPF コアと verifier を押さえてから map、BTF、アタッチ、トレーシング基盤へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。
XDP/tc の networking 詳細は network 分冊、perf のアーキ依存は x86-64 分冊へ委譲する。

## 第0部　概観

1. [BPF サブシステムの全体像](part00-overview/01-bpf-subsystem-overview.md)
2. [BPF オブジェクトと bpf コマンド](part00-overview/02-bpf-objects-and-commands.md)

## 第1部　BPF コア

3. [bpf システムコールとコマンド配線](part01-core/03-bpf-syscall-dispatch.md)
4. [bpf_prog_load とプログラムオブジェクト](part01-core/04-bpf-prog-load.md)
5. [インタプリタと bpf_prog_run](part01-core/05-interpreter-bpf-prog-run.md)
6. [x86 BPF JIT](part01-core/06-x86-bpf-jit.md)

## 第2部　verifier

7. [verifier の状態機械と命令探索](part02-verifier/07-verifier-state-exploration.md)
8. [レジスタ型と値追跡](part02-verifier/08-verifier-register-types.md)
9. [境界検査とポインタ種別](part02-verifier/09-verifier-bounds-pointers.md)
10. [liveness と到達不能除去](part02-verifier/10-verifier-liveness-dead-code.md)

## 第3部　map

11. [HASH map と RCU 参照](part03-maps/11-hashtab-rcu.md)
12. [ARRAY map と per-CPU](part03-maps/12-arraymap-percpu.md)
13. [LPM trie と map 種別の概観](part03-maps/13-lpm-trie-maps-overview.md)

## 第4部　BTF とアタッチ

14. [BTF と型情報](part04-btf-attach/14-btf-type-info.md)
15. [tracing プログラムのアタッチ](part04-btf-attach/15-tracing-program-attach.md)
16. [cgroup と networking プログラムの境界](part04-btf-attach/16-cgroup-networking-boundary.md)

## 第5部　トレーシング基盤

17. [tracepoint と静的パッチ](part05-tracing/17-tracepoint-static-patch.md)
18. [tracing ring buffer](part05-tracing/18-ring-buffer.md)
19. [ftrace と動的トレース](part05-tracing/19-ftrace-dynamic-trace.md)
20. [trace event と trace コア](part05-tracing/20-trace-events-core.md)
21. [kprobes と optimized kprobe](part05-tracing/21-kprobes-optimized.md)
22. [perf events と BPF の接点](part05-tracing/22-perf-events-bpf.md)

---

> 本分冊は Linux カーネル読解ドキュメント群の横断分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
