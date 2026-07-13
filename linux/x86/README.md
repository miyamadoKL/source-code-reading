# Linux カーネル x86-64 アーキテクチャ

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の x86-64 アーキテクチャ実装を読み解く分冊である。
`arch/x86/` を対象に、ブート（リアルモードからロングモードへ）、CPU 初期化、例外と割り込みの入口、システムコール、APIC、コンテキストスイッチ、ページテーブルと TLB、SMP ブート、投機実行緩和策までを、ハードウェアに最も近い層からソースを追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md) のブートと entry_64.S の概観を読み、C とアセンブリと計算機アーキテクチャの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  実行環境と記述子表を押さえてからブート、CPU 初期化、例外と syscall、APIC、コンテキストスイッチ、ページテーブル、SMP へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アセンブリ（`.S`）と C の両方を引用する。

本分冊の委譲境界は次のとおりである。

- **ブートと entry の概観**：起動シーケンスと `entry_64.S` の入口出口の概観、システムコールテーブルと `SYSCALL_DEFINE` は [全体像と横断基盤](../foundation/README.md) に委譲する。
  本分冊は入口時のレジスタ、スタック、`%gs`、`CR3`、`pt_regs`、復帰命令の選択をアーキ実装レベルで扱う。
- **汎用 IRQ 層**：`irq_desc` と generic な `irq_domain` の一般論は [割り込みと時間](../irq-time/README.md) に委譲する。
  本分冊は IO-APIC と Local APIC から vector domain、`irq_matrix`、`common_interrupt` への x86 側の接続を扱う。
- **汎用メモリ管理**：VMA 探索と `handle_mm_fault` 以降は [メモリ管理](../mm/README.md) に委譲する。
  本分冊は `exc_page_fault`、`CR2`、error code、kernel fault の fixup、ユーザー fault への引き渡しを扱う。
- **スケジューラ**：次タスクの選択と scheduler locking は [プロセスとスケジューラ](../sched/README.md) に委譲する。
  本分冊は `__switch_to` 以降のスタック、callee-saved レジスタ、TSS の RSP0、FS/GS、TLS、FPU 状態の更新を扱う。
- **範囲外**：個別デバイスドライバ、ACPI 本体、EFI stub 詳細、Xen と UM、32bit（ia32）の網羅、KVM（[仮想化（KVM）](../kvm/README.md) で扱う）。

## 第0部　実行環境と静的構造

1. [分冊の全体像と x86-64 実行環境](part00-foundation/01-overview-execution-environment.md)
2. [GDT と TSS とセグメント記述子と cpu_entry_area](part00-foundation/02-gdt-tss-cpu-entry-area.md)

## 第1部　ブート

3. [16ビット setup と保護モード移行](part01-boot/03-realmode-setup-protected-mode.md)
4. [圧縮カーネルの展開と再配置と64ビット入口](part01-boot/04-compressed-kernel-decompression.md)
5. [head_64.S の startup_64](part01-boot/05-head-64-startup.md)
6. [x86_64_start_kernel から start_kernel へ](part01-boot/06-x86-64-start-kernel.md)

## 第2部　CPU 初期化基盤

7. [CPU 識別と機能フラグ](part02-cpu-init/07-cpu-identification-features.md)
8. [per-CPU 領域と GS base](part02-cpu-init/08-percpu-gs-base.md)
9. [CPU ごとの記述子表と CR と MSR 初期化](part02-cpu-init/09-cpu-init-cr-msr.md)
10. [alternatives と static_call と text_poke](part02-cpu-init/10-alternatives-static-call.md)

## 第3部　例外と NMI と FRED

11. [IDT の構築と IDTENTRY 機構](part03-exceptions/11-idt-construction.md)
12. [通常例外の入口と本体](part03-exceptions/12-normal-exceptions.md)
13. [NMI と機械検査例外と IST と paranoid path](part03-exceptions/13-nmi-mce-ist-paranoid.md)
14. [FRED のイベント配送と従来 IDT 経路との差](part03-exceptions/14-fred.md)

## 第4部　システムコールとユーザー境界

15. [entry_SYSCALL_64 のアセンブリ経路](part04-syscall/15-entry-syscall-64.md)
16. [do_syscall_64 とディスパッチと戻り](part04-syscall/16-do-syscall-64-dispatch.md)
17. [vDSO と vsyscall](part04-syscall/17-vdso-vsyscall.md)

## 第5部　割り込みと APIC

18. [Local APIC の初期化と timer と IPI](part05-apic/18-local-apic-timer-ipi.md)
19. [割り込みベクタ割り当てと common_interrupt](part05-apic/19-vector-common-interrupt.md)
20. [IO-APIC と pin から vector domain への接続](part05-apic/20-io-apic.md)

## 第6部　コンテキストスイッチとタスク状態

21. [__switch_to_asm と __switch_to](part06-context-switch/21-switch-to.md)
22. [FS と GS と TLS と copy_thread](part06-context-switch/22-fs-gs-tls-copy-thread.md)
23. [FPU と SIMD XSAVE と条件付き復元](part06-context-switch/23-fpu-xsave.md)

## 第7部　仮想アドレスとページテーブル

24. [仮想アドレス配置と KASLR](part07-paging/24-virtual-address-layout-kaslr.md)
25. [4/5 レベルページテーブルとカーネルマッピング](part07-paging/25-page-tables-kernel-mapping.md)
26. [x86 ページフォールト入口](part07-paging/26-page-fault-entry.md)
27. [TLB flush と lazy TLB と PCID](part07-paging/27-tlb-pcid.md)
28. [KPTI とページテーブル分離](part07-paging/28-kpti.md)

## 第8部　SMP と緩和策

29. [SMP ブート BSP から AP 起動](part08-smp-mitigations/29-smp-boot.md)
30. [投機実行緩和策と実行時制御](part08-smp-mitigations/30-speculative-mitigations.md)

---

> 本分冊は執筆中である。
> コード引用は `gregkh/linux` の `v6.18.38` タグに固定し、7.x 系の大きな変化は `v7.1.3` タグへの固定リンク付きで注記する。
