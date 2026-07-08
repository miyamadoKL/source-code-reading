# 第17章 hwdb とデバイス列挙

> 本章で読むソース
>
> - [`src/libsystemd/sd-hwdb/hwdb-internal.h`](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-hwdb/hwdb-internal.h)
> - [`src/libsystemd/sd-hwdb/sd-hwdb.c`](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-hwdb/sd-hwdb.c)
> - [`src/shared/hwdb-util.c`](https://github.com/systemd/systemd/blob/v261.1/src/shared/hwdb-util.c)
> - [`src/libsystemd/sd-device/device-enumerator.c`](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-device/device-enumerator.c)

## この章の狙い

udev がデバイスに属性を付けるとき、その多くはハードウェアデータベース（hwdb）から引く。
hwdb は「modalias のようなキー」から「プロパティの集合」への大きな辞書であり、高速な検索のために専用のバイナリ形式へコンパイルされる。
本章では、この辞書がどう trie にコンパイルされ、どう mmap して検索されるかを読む。
併せて、`/sys` を走査してデバイスを列挙する仕組みも追う。

## 前提

- 第16章の udev デーモンとルール適用を理解していること
- trie（プレフィックス木）とラディックス木の基本を知っていること
- mmap によるファイルの読み取り専用マッピングを把握していること

## hwdb のオンディスク形式

hwdb は trie（プレフィックス木）としてファイルに格納される。
先頭にヘッダがあり、署名、ツールバージョン、ルートノードのオフセット、ノード領域と文字列領域の長さを持つ。

[`src/libsystemd/sd-hwdb/hwdb-internal.h` L28-L47](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-hwdb/hwdb-internal.h#L28-L47)

```c
/* on-disk trie objects */
struct trie_header_f {
        uint8_t signature[8];

        /* version of tool which created the file */
        le64_t tool_version;
        le64_t file_size;

        /* size of structures to allow them to grow */
        le64_t header_size;
        le64_t node_size;
        le64_t child_entry_size;
        le64_t value_entry_size;

        /* offset of the root trie node */
        le64_t nodes_root_off;

        /* size of the nodes and string section */
        le64_t nodes_len;
        le64_t strings_len;
} _packed_;
```

各ノードは、そのノードまでの共通プレフィックス（`prefix_off` が指す文字列）、子ノードの配列、値の配列を持つ。
プレフィックスをノードに持たせることで、キーの共通部分を一つのノードにまとめる。

[`src/libsystemd/sd-hwdb/hwdb-internal.h` L49-L57](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-hwdb/hwdb-internal.h#L49-L57)

```c
struct trie_node_f {
        /* prefix of lookup string, shared by all children  */
        le64_t prefix_off;
        /* size of children entry array appended to the node */
        uint8_t children_count;
        uint8_t padding[7];
        /* size of value entry array appended to the node */
        le64_t values_count;
} _packed_;
```

## コンパイル: テキストから trie へ

`hwdb_update()` が、`.hwdb` テキストファイル群を読み込み、trie を組み立ててバイナリへ書き出す。
ファイルを優先度順に取り込み、各エントリを `trie_insert()` で木へ挿入する。

[`src/shared/hwdb-util.c` L633-L657](https://github.com/systemd/systemd/blob/v261.1/src/shared/hwdb-util.c#L633-L657)

```c
        FOREACH_ARRAY(i, files, n_files) {
                ConfFile *c = *i;

                log_debug("Reading file \"%s\" -> \"%s\"", c->original_path, c->resolved_path);
                RET_GATHER(ret, import_file(trie, c->fd, c->original_path, file_priority++, compat));
        }

        strbuf_complete(trie->strings);
        // ... (中略) ...
        (void) mkdir_parents_label(hwdb_bin, 0755);
        r = trie_store(trie, hwdb_bin, compat);
```

`trie_insert()` は、既存ノードのプレフィックスと挿入キーを一文字ずつ比較する。
途中で食い違うと、その位置でノードを分割する。
前半を共通プレフィックスとして残し、後半を新しい子ノードへ移す。

[`src/shared/hwdb-util.c` L200-L245](https://github.com/systemd/systemd/blob/v261.1/src/shared/hwdb-util.c#L200-L245)

```c
                for (p = 0; (c = trie->strings->buf[node->prefix_off + p]); p++) {
                        // ... (中略) ...
                        if (c == search[i + p])
                                continue;

                        /* split node */
                        new_child = new(struct trie_node, 1);
                        if (!new_child)
                                return -ENOMEM;

                        /* move values from parent to child */
                        *new_child = (struct trie_node) {
                                .prefix_off = node->prefix_off + p+1,
                                .children = node->children,
                                .children_count = node->children_count,
                                .values = node->values,
                                .values_count = node->values_count,
                        };
                        // ... (中略) ...
                }
                i += p;

                c = search[i];
                if (c == '\0')
                        return trie_node_add_value(trie, node, key, value, filename, file_priority, line_number, compat);
```

この分割により、木は共通プレフィックスをノード単位でまとめたラディックス木になる。
文字列は専用のストア（`strbuf`）に置き、同じ文字列は一度だけ格納する。

## 検索: mmap と trie 探索

コンパイル済みの `hwdb.bin` は、検索側で読み取り専用にメモリマップされる。

[`src/libsystemd/sd-hwdb/sd-hwdb.c` L426-L433](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-hwdb/sd-hwdb.c#L426-L433)

```c
        hwdb->map = mmap(NULL, hwdb->st.st_size, PROT_READ, MAP_SHARED, fileno(hwdb->f), 0);
        if (hwdb->map == MAP_FAILED)
                return log_debug_errno(errno, "Failed to map %s: %m", path);

        if (memcmp(hwdb->map, sig, sizeof(hwdb->head->signature)) != 0 ||
            (size_t) hwdb->st.st_size != le64toh(hwdb->head->file_size))
                return log_debug_errno(SYNTHETIC_ERRNO(EINVAL),
                                       "Failed to recognize the format of %s.", path);
```

検索は `sd_hwdb_get()` から `trie_search_f()` を呼ぶ。
ルートから始め、ノードのプレフィックスと検索キーを一文字ずつ照合しながら子へ降りる。
キーを末尾まで消費したノードの値が、そのキーに対応するプロパティである。

[`src/libsystemd/sd-hwdb/sd-hwdb.c` L318-L380](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-hwdb/sd-hwdb.c#L318-L380)

```c
        while (node) {
                const struct trie_node_f *child;
                size_t p = 0;

                if (node->prefix_off) {
                        const char *prefix;
                        char c;

                        prefix = trie_string(hwdb, node->prefix_off);
                        // ... (中略) ...
                        for (; (c = prefix[p]); p++) {
                                if (IN_SET(c, '*', '?', '['))
                                        return trie_fnmatch_f(hwdb, node, p, &buf, search + i + p, 0);
                                if (c != search[i + p])
                                        return 0;
                        }
                        i += p;
                }
                // ... (中略) ...
                if (search[i] == '\0') {
                        size_t n;

                        for (n = 0; n < le64toh(node->values_count); n++) {
                                err = hwdb_add_property(hwdb, trie_node_value(hwdb, node, n));
                                if (err < 0)
                                        return err;
                        }
                        return 0;
                }

                child = node_lookup_f(hwdb, node, search[i]);
                node = child;
                i++;
        }
```

hwdb のキーはワイルドカードを含みうる（例 `usb:v046DpC52B*`）。
プレフィックスに `*`、`?`、`[` が現れると、そこから先は `trie_fnmatch_f()` に切り替え、木を辿りながら組み立てたパターンを `fnmatch()` で照合する。

[`src/libsystemd/sd-hwdb/sd-hwdb.c` L289-L300](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-hwdb/sd-hwdb.c#L289-L300)

```c
        if (le64toh(node->values_count) != 0) {
                const char *line = linebuf_get(buf);
                if (!line)
                        return -EBADMSG;

                if (fnmatch(line, search, 0) == 0)
                        for (i = 0; i < le64toh(node->values_count); i++) {
                                err = hwdb_add_property(hwdb, trie_node_value(hwdb, node, i));
                                if (err < 0)
                                        return err;
                        }
        }
```

## デバイスの列挙

udev のもう一つの基盤が、`/sys` を走査して既存デバイスを列挙する `sd_device_enumerator` である。
起動時に既存デバイスへ uevent を合成し直す（coldplug）ときや、`udevadm trigger` のときに使う。

列挙の入口は `device_enumerator_scan_devices()` であり、マッチ条件に応じて走査方法を選ぶ。

[`src/libsystemd/sd-device/device-enumerator.c` L1000-L1015](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-device/device-enumerator.c#L1000-L1015)

```c
        if (!set_isempty(enumerator->match_tag)) {
                k = enumerator_scan_devices_tags(enumerator);
                if (k < 0)
                        r = k;
        } else if (enumerator->match_parent) {
                k = enumerator_scan_devices_children(enumerator);
                if (k < 0)
                        r = k;
        } else {
                k = enumerator_scan_devices_all(enumerator);
                if (k < 0)
                        r = k;
        }

        enumerator->scan_uptodate = true;
```

実際のディレクトリ走査は `enumerator_scan_dir_and_add_devices()` が行う。
`/sys` の該当ディレクトリを開き、各エントリからデバイスを構築し、マッチ条件を通ったものだけを集める。

[`src/libsystemd/sd-device/device-enumerator.c` L731-L761](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-device/device-enumerator.c#L731-L761)

```c
        FOREACH_DIRENT_ALL(de, dir, return -errno) {
                _cleanup_(sd_device_unrefp) sd_device *device = NULL;
                char syspath[strlen(path) + 1 + strlen(de->d_name) + 1];

                if (!relevant_sysfs_subdir(de))
                        continue;

                if (!match_sysname(enumerator, de->d_name))
                        continue;

                (void) sprintf(syspath, "%s%s", path, de->d_name);

                k = sd_device_new_from_syspath(&device, syspath);
                // ... (中略) ...
                k = test_matches(enumerator, device, MATCH_ALL & (~MATCH_SYSNAME)); /* sysname is already tested. */
                if (k <= 0) {
                        // ... (中略) ...
                }

                k = device_enumerator_add_device(enumerator, device);
```

列挙結果を最初に取り出すとき、デバイスは依存順にソートされる。

[`src/libsystemd/sd-device/device-enumerator.c` L1020-L1034](https://github.com/systemd/systemd/blob/v261.1/src/libsystemd/sd-device/device-enumerator.c#L1020-L1034)

```c
_public_ sd_device* sd_device_enumerator_get_device_first(sd_device_enumerator *enumerator) {
        assert_return(enumerator, NULL);

        if (device_enumerator_scan_devices(enumerator) < 0)
                return NULL;

        if (enumerator_sort_devices(enumerator) < 0)
                return NULL;

        enumerator->current_device_index = 0;
        // ... (中略) ...
        return enumerator->devices[0];
}
```

ソートは、親デバイスが子より先に来るように syspath の包含関係で並べる。
coldplug で親を先に処理すれば、子の処理時点で親がすでに初期化済みになる。

## 最適化: プレフィックス圧縮の trie と共有マッピング

hwdb の検索が速いのは、二つの機構が効くためだ。

第一がプレフィックス圧縮の trie である。
hwdb は数万件規模のキーを持つが、キーは `usb:` や `pci:` のような共通の接頭辞を大量に共有する。
ラディックス木は共通接頭辞を一つのノードにまとめるため、完全一致の通常枝では木の高さがキー長にほぼ比例する。
検索は先頭から一文字ずつ木を降りるだけなので、通常枝ではキー長中心に絞れる。
一方、`*`、`?`、`[` を含む枝では `trie_fnmatch_f()` が候補パターンを辿って `fnmatch()` するため、候補数の影響を受ける。
コンパイル時に文字列を重複排除して格納するため、同じ値やプレフィックスがファイル上で何度も書かれることもない。

第二が読み取り専用の共有マッピングである。
`hwdb.bin` は `MAP_SHARED | PROT_READ` で mmap されるため、複数のプロセスが同じ物理ページを共有する。
ファイルを読み込んでパースする段階がなく、mmap したメモリ上のオフセットを直接辿って検索する。
多数の udev ワーカーが同時に hwdb を引いても、辞書の実体はメモリ上に一つだけ載る。

## まとめ

hwdb は、modalias のようなキーからプロパティ集合への辞書を、プレフィックス圧縮した trie としてバイナリにコンパイルしたものである。
コンパイルはテキストを `trie_insert()` でラディックス木へ挿入し、文字列を重複排除して格納する。
検索は `hwdb.bin` を読み取り専用で mmap し、木を一文字ずつ降りて、ワイルドカードは `fnmatch()` へ切り替えて照合する。
デバイス列挙は `/sys` を走査してマッチするデバイスを集め、親が子より先に来るよう依存順でソートして返す。
プレフィックス圧縮で通常枝の探索をキー長中心に絞り、共有マッピングで多数のワーカーが辞書の実体を一つだけ共有する。

## 関連する章

- 第16章：udev デーモンのイベント処理（ワーカーが hwdb を引いてルールを適用する）
- 第12章：cgroup v2 統合（起動時に既存状態を状態機械へ反映する coldplug の考え方）
