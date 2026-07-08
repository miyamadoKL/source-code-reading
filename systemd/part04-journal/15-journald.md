# 第15章 journald の書き込みとローテーション

> 本章で読むソース
>
> - [`src/journal/journald.c`](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald.c)
> - [`src/journal/journald-manager.c`](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-manager.c)
> - [`src/journal/journald-sync.c`](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-sync.c)

## この章の狙い

`systemd-journald` は、システム中のログを受け取り、第14章のジャーナルファイルへ書き込むデーモンである。
本章では、journald が入力をどう受けて書き込み、ファイルがいっぱいになったときどうローテーションし、ディスクへの同期をどうまとめて効率化するかを追う。
同期完了を外部に返す仕組みも読む。

## 前提

- 第14章のジャーナルファイルフォーマット（`journal_file_append_entry()`）を理解していること
- 第4章の `sd-event`（イベントループとタイマーソース）を把握していること
- ソケット（AF_UNIX の datagram と stream）の基本を知っていること

## デーモンの骨格

journald の本体はマネージャーオブジェクトを生成し、イベントループを回す。
`manager_init()` でソケットとファイルを開き、起動時にランタイムジャーナルの内容を永続ジャーナル（`/var/log/journal`）へ流し込む。

[`src/journal/journald.c` L55-L71](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald.c#L55-L71)

```c
        r = manager_new(&m);
        if (r < 0)
                return log_oom();

        r = manager_set_namespace(m, namespace);
        if (r < 0)
                return r;

        manager_load_config(m);

        r = manager_init(m);
        if (r < 0)
                return r;

        manager_vacuum(m, /* verbose= */ false);
        manager_flush_to_var(m, /* require_flag_file= */ true);
        manager_flush_dev_kmsg(m);
```

イベントループは通常の `sd_event` 一巡に加え、保持期間（`MaxRetentionSec=`）に達したファイルの vacuum を自前のタイマー計算で挟む。

[`src/journal/journald.c` L100-L124](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald.c#L100-L124)

```c
                if (m->config.max_retention_usec > 0 && m->oldest_file_usec > 0) {
                        /* Calculate when to rotate the next time */
                        t = usec_sub_unsigned(usec_add(m->oldest_file_usec, m->config.max_retention_usec), n);

                        /* The retention time is reached, so let's vacuum! */
                        if (t <= 0) {
                                log_info("Retention time reached, vacuuming.");
                                manager_vacuum(m, /* verbose= */ false);
                                continue;
                        }
                } else
                        t = USEC_INFINITY;
        // ... (中略) ...
        r = sd_event_run(m->event, t);
```

ログ入力は複数の経路から来る。
`sd_journal_send()` が使う native ソケット、互換の syslog ソケット、`/dev/kmsg`、そしてサービスの標準出力を運ぶ stream ソケットである。
どの経路も最終的に整形されたフィールド配列を作り、書き込み処理に渡す。

## エントリの書き込み

`manager_write_to_journal()` が、整形済みフィールドを実際のファイルへ書く。
まず UID ごとに分かれたジャーナルファイルを引き当て、書き込む前にローテーションが必要かを判定する。

[`src/journal/journald-manager.c` L970-L1006](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-manager.c#L970-L1006)

```c
        f = manager_find_journal(m, uid);
        if (!f)
                return;

        if (journal_file_rotate_suggested(f, m->config.max_file_usec, LOG_DEBUG)) {
                // ... (中略) ...
                manager_rotate_journal(m, TAKE_PTR(f), uid);
                manager_vacuum(m, /* verbose= */ false);
                vacuumed = true;

                f = manager_find_journal(m, uid);
                if (!f)
                        return;
        }

        m->last_realtime_clock = ts->realtime;

        r = journal_file_append_entry(
                        f,
                        ts,
                        /* boot_id= */ NULL,
                        iovec, n,
                        &m->seqnum->seqnum,
                        &m->seqnum->id,
                        /* ret_object= */ NULL,
                        /* ret_offset= */ NULL);
        if (r >= 0) {
                manager_schedule_sync(m, priority);
                return;
        }
```

書き込みが成功したら、後述の同期をスケジュールして終わる。
時刻が過去へ飛んだ場合は、二分探索の前提（時刻順）が崩れるため、書き込み前に即座にローテーションして新しいファイルを始める。

## エラー駆動のローテーション

`journal_file_append_entry()` が失敗しても、多くのエラーは致命的ではなく、ファイルを切り替えれば続行できる。
`shall_try_append_again()` が、どのエラーでローテーションして再試行すべきかを判定する。

[`src/journal/journald-manager.c` L873-L878](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-manager.c#L873-L878)

```c
        case -E2BIG:           /* Hit configured limit          */
        case -EFBIG:           /* Hit fs limit                  */
        case -EDQUOT:          /* Quota limit hit               */
        case -ENOSPC:          /* Disk full                     */
                log_debug_errno(r, "%s: Allocation limit reached, rotating.", f->path);
                return true;
```

設定サイズ超過、ディスク満杯、破損、時刻の逆行など、多様な原因がここで「ローテーションすべき」と分類される。
分類が真なら一度だけローテーションして再試行し、それでも駄目なら諦める。

## ローテーションの実体

ローテーションは、書き込み中のファイルを archived 状態にして閉じ、新しいファイルを開く操作である。
`manager_rotate()` は、システムジャーナルとランタイムジャーナル、そして開いている全ユーザージャーナルを順に切り替える。

[`src/journal/journald-manager.c` L718-L738](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-manager.c#L718-L738)

```c
        /* First, rotate the system journal (either in its runtime flavour or in its runtime flavour) */
        (void) manager_do_rotate(m, &m->runtime_journal, "runtime", /* seal= */ false, /* uid= */ 0);
        (void) manager_do_rotate(m, &m->system_journal, "system", m->config.seal, /* uid= */ 0);

        /* Then, rotate all user journals we have open (keeping them open) */
        ORDERED_HASHMAP_FOREACH_KEY(f, k, m->user_journals) {
                r = manager_do_rotate(m, &f, "user", m->config.seal, PTR_TO_UID(k));
                // ... (中略) ...
        }
        // ... (中略) ...
        manager_process_deferred_closes(m);
```

個々の切り替えは `manager_do_rotate()` が担い、`journal_file_rotate()` を呼ぶ。
このとき古いファイルは即座には閉じず、`deferred_closes` 集合に入れて後で閉じる。

[`src/journal/journald-manager.c` L563-L576](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-manager.c#L563-L576)

```c
        log_debug("Rotating journal file %s.", (*f)->path);

        r = journal_file_rotate(f, m->mmap, manager_get_file_flags(m, seal), m->config.compress.threshold_bytes, m->deferred_closes);
        if (r < 0) {
                // ... (中略) ...
        }

        manager_add_acls(*f, uid);
        return r;
```

古いファイルを閉じるにはディスクへの完全な同期（offlining）が要る。
これを同期的に行うと書き込み経路が待たされるため、閉じる処理を遅延させて書き込みの手を止めない。

保持期間や容量超過に対しては vacuum が働く。
`journal_directory_vacuum()` が古いファイルを削除し、次に vacuum すべき時刻の基準となる最古ファイルの時刻を更新する。

[`src/journal/journald-manager.c` L804-L806](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-manager.c#L804-L806)

```c
        r = journal_directory_vacuum(storage->path, storage->space.limit,
                                     storage->metrics.n_max_files, m->config.max_retention_usec,
                                     &m->oldest_file_usec, verbose);
```

## ディスク同期のスケジューリング

ログを一件書くたびに `fsync` を呼ぶと、ディスクへの同期が律速になる。
journald は同期をまとめる。
`manager_schedule_sync()` は、緊急度の高いメッセージだけ即座に同期し、それ以外は設定間隔（`SyncIntervalSec=`）のタイマーで後からまとめて同期する。

[`src/journal/journald-manager.c` L1866-L1905](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-manager.c#L1866-L1905)

```c
        if (priority <= LOG_CRIT) {
                /* Immediately sync to disk when this is of priority CRIT, ALERT, EMERG */
                manager_sync(m, /* wait= */ false);
                return 0;
        }
        // ... (中略) ...
        if (m->sync_scheduled)
                return 0;

        if (m->config.sync_interval_usec > 0) {

                if (!m->sync_event_source) {
                        r = sd_event_add_time_relative(
                                        m->event,
                                        &m->sync_event_source,
                                        CLOCK_MONOTONIC,
                                        m->config.sync_interval_usec, 0,
                                        manager_dispatch_sync, m);
                        // ... (中略) ...
                }
                // ... (中略) ...
                m->sync_scheduled = true;
        }
```

タイマーが発火すると `manager_sync()` が全ファイルを offline へ落とし、同期を完了させる。

[`src/journal/journald-manager.c` L771-L790](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-manager.c#L771-L790)

```c
        if (m->system_journal) {
                r = journal_file_set_offline(m->system_journal, wait);
                // ... (中略) ...
        }

        ORDERED_HASHMAP_FOREACH(f, m->user_journals) {
                r = journal_file_set_offline(f, wait);
                // ... (中略) ...
        }

        r = sd_event_source_set_enabled(m->sync_event_source, SD_EVENT_OFF);
        // ... (中略) ...
        m->sync_scheduled = false;
```

`sync_scheduled` フラグで、間隔内に何度書き込んでもタイマーは一度しか張られないようにしている。

## 同期完了の応答

`journalctl --sync` のようなコマンドは、「今この瞬間までに届いたログがすべてディスクに載った」ことを待つ。
journald は、入力を強制的に汲み尽くさずに、この条件の成立を検出する。
`sync_req_new()` のコメントが、五つの判定手段を説明する。

[`src/journal/journald-sync.c` L208-L235](https://github.com/systemd/systemd/blob/v261.1/src/journal/journald-sync.c#L208-L235)

```c
        /* We use five distinct mechanisms to determine when the synchronization request is complete:
         *
         * 1. For the syslog/native AF_UNIX/SOCK_DGRAM sockets we look at the datagram timestamps: once the
         *    most recently seen datagram on the socket is newer than the timestamp when we initiated the
         *    sync request we know that all previously enqueued messages have been processed by us.
         *
         * 2. For established stream AF_UNIX/SOCK_STREAM sockets we have no timestamps. For them we take the
         *    SIOCINQ counter at the moment the synchronization request was enqueued. And once we processed
         *    the indicated number of input bytes we know that anything further was enqueued later than the
         *    original synchronization request we started from.
```

datagram ソケットには受信時刻があるので、要求時刻より新しい datagram を見た時点で「それ以前の分は処理済み」とわかる。
stream ソケットには時刻がないので、要求時点の未処理バイト数（`SIOCINQ`）を数え、そのバイト数を処理し終えた時点で完了とみなす。
さらに、いずれの判定にも漏れがあった場合の安全網として、最も低い優先度のアイドルハンドラを置く。
このハンドラが呼ばれた時点で保留 IO が一つもないことが保証されるため、確実に応答を返せる。

## 最適化: 同期のバッチ化と遅延クローズ

journald の書き込み経路が速いのは、ディスク待ちを書き込みの都度発生させないためだ。

第一が同期のバッチ化である。
通常のメッセージは即座に `fsync` せず、設定間隔のタイマーで一括して同期する。
`sync_scheduled` フラグにより、間隔内の複数の書き込みは一回の同期に畳まれる。
緊急度が `CRIT` 以上のメッセージだけは即座に同期し、失われて困るログの耐久性は落とさない。
これにより、大量のログを受けても同期の回数を書き込み件数ではなく時間間隔に比例させられる。

第二がローテーション時の遅延クローズである。
古いファイルを閉じる同期処理は重いため、閉じる対象を `deferred_closes` に積んで後で処理する。
書き込み経路はローテーション直後もブロックせずに新しいファイルへ進める。

同期完了の判定も、入力を汲み尽くすのではなく時刻とバイト数の比較で行うため、待機のためだけに余分な IO を起こさない。

## まとめ

`systemd-journald` は複数の入力経路からログを受け、UID ごとに分かれたジャーナルファイルへ書き込むデーモンである。
書き込み前に `journal_file_rotate_suggested()` でローテーションの要否を判定し、書き込み失敗時も `shall_try_append_again()` の分類に従ってローテーションして再試行する。
ローテーションは古いファイルを archived にして遅延クローズへ回し、書き込みを止めない。
ディスク同期は緊急メッセージだけ即座に行い、それ以外は間隔タイマーで一括同期してディスク待ちの回数を抑える。
同期完了の応答は、datagram の時刻と stream のバイト数とアイドルハンドラを組み合わせ、入力を汲み尽くさずに検出する。

## 関連する章

- 第14章：ジャーナルファイルフォーマット（`journal_file_append_entry()` の内部）
- 第4章：`sd-event`（同期タイマーと入力ソースを回すイベントループ）
- 第24章：Varlink（同期要求を運ぶプロトコル）
