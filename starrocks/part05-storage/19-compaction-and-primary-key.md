# 第19章 Compaction と Primary Key 更新

> **本章で読むソース**
>
> - [`be/src/storage/compaction.h`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction.h)
> - [`be/src/storage/compaction.cpp`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction.cpp)
> - [`be/src/storage/base_compaction.cpp`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/base_compaction.cpp)
> - [`be/src/storage/cumulative_compaction.cpp`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/cumulative_compaction.cpp)
> - [`be/src/storage/compaction_candidate.h`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_candidate.h)
> - [`be/src/storage/compaction_manager.h`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_manager.h)
> - [`be/src/storage/compaction_manager.cpp`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_manager.cpp)
> - [`be/src/storage/compaction_task.h`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_task.h)
> - [`be/src/storage/tablet_updates.h`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.h)
> - [`be/src/storage/tablet_updates.cpp`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp)
> - [`be/src/storage/delta_column_group.h`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/delta_column_group.h)
> - [`be/src/storage/persistent_index.h`](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/persistent_index.h)

## この章の狙い

書き込みのたびに Rowset が追加されるストレージ層では、Rowset の増加に伴い読み出し性能が劣化する。
Compaction は複数の Rowset をマージして1つにまとめ、読み出し時の走査コストを削減する。
本章ではまず non-PK テーブルの BaseCompaction と CumulativeCompaction を読み、次に Primary Key テーブル固有の更新管理と Compaction を追う。
最後に PersistentIndex のハッシュインデックスによる O(1) ポイント更新の仕組みを解説する。

## 前提

第16章で読んだとおり、Tablet は内部にバージョン管理された Rowset 群を保持する。
non-PK テーブル(Duplicate Key, Aggregate Key, Unique Key)では `_rs_version_map` で Rowset を管理し、Primary Key テーブルでは `TabletUpdates` が Rowset と PrimaryIndex を管理する。
Rowset は不変であり、Compaction は入力 Rowset 群のデータをマージして新しい Rowset を生成し、旧 Rowset を置き換える操作である。

## Compaction の目的

Rowset が増え続けると、読み出しクエリは大量の Segment を横断して走査しなければならない。
Compaction はこの断片化を解消する。
具体的には、複数の Rowset を1つにマージすることで Segment 数を減らし、走査コストを削減する。
削除済みデータの物理的な除去も同時に行い、ストレージ使用量を回収する。
Aggregate Key テーブルでは同一キーの値を集約し、Unique Key テーブルでは旧バージョンの行を除去する役割も持つ。

## BaseCompaction と CumulativeCompaction

non-PK テーブルでは2種類の Compaction を使い分ける。

### CumulativeCompaction

**CumulativeCompaction** は `cumulative_layer_point` 以降の小さな Rowset をマージする軽量な Compaction である。
`cumulative_layer_point` はバージョン空間の境界を示し、この値より小さいバージョンの Rowset は BaseCompaction の領域に属する。

候補 Rowset の選択は `pick_rowsets_to_compact()` で行われる。

[`be/src/storage/cumulative_compaction.cpp` L95-L235](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/cumulative_compaction.cpp#L95-L235)

```cpp
Status CumulativeCompaction::pick_rowsets_to_compact() {
    std::vector<RowsetSharedPtr> candidate_rowsets;
    _tablet->pick_candicate_rowsets_to_cumulative_compaction(&candidate_rowsets);
    // ... (中略) ...
    int64_t prev_end_version = _tablet->cumulative_layer_point() - 1;
    for (const auto& rowset : candidate_rowsets) {
        // ... (中略) ...
    }
    // ... (中略) ...
    if (_input_rowsets.empty() && compaction_score >= config::min_cumulative_compaction_num_singleton_deltas) {
        _input_rowsets = transient_rowsets;
    }
    // ... (中略) ...
    return Status::OK();
}
```

選択ロジックの流れを整理する。

1. `cumulative_layer_point` より大きいバージョンの Rowset を候補として収集する(L115)
2. delete version を持つ Rowset に遭遇すると、そこで候補列を区切る(L132-L152)
3. すでに Compaction 済み(non-overlapping)の Rowset にも同様の区切りを入れる(L155-L171)
4. 候補数が `min_cumulative_compaction_num_singleton_deltas` 以上であれば実行対象とする(L84, L120, L184)

実行可否の判定は `fit_compaction_condition()` で行われる。

[`be/src/storage/cumulative_compaction.cpp` L81-L93](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/cumulative_compaction.cpp#L81-L93)

```cpp
bool CumulativeCompaction::fit_compaction_condition(const std::vector<RowsetSharedPtr>& rowsets,
                                                    int64_t compaction_score) {
    if (!rowsets.empty()) {
        if (compaction_score >= config::min_cumulative_compaction_num_singleton_deltas) {
            return true;
        }
        if (rowsets.front()->start_version() == _tablet->cumulative_layer_point()) {
            return true;
        }
    }

    return false;
}
```

`compaction_score` が閾値に達していなくても、候補 Rowset の合計サイズが一定以上であれば実行する分岐も存在する。
delete version で区切る理由は、delete predicate がバージョン境界をまたぐマージでは正しく適用できないためである。

### BaseCompaction

**BaseCompaction** は base rowset(バージョン0起点)とその上の cumulative rowset をまとめる大規模な Compaction である。
「CumulativeCompaction」で十分にまとめられた Rowset 群をさらに統合し、断片化を解消する。

[`be/src/storage/base_compaction.cpp` L75-L160](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/base_compaction.cpp#L75-L160)

```cpp
Status BaseCompaction::pick_rowsets_to_compact() {
    // ... (中略) ...
}

```

「BaseCompaction」の `pick_rowsets_to_compact()` は3つのトリガー条件を順に評価する。

1. **スコア閾値**(L109-L114)：cumulative rowset の compaction score が閾値を超えている
2. **累積/base サイズ比**(L116-L141)：cumulative rowset の合計サイズが base rowset のサイズに対して一定比率を超えている
3. **前回からの経過時間**(L143-L152)：前回の「BaseCompaction」から一定時間が経過している

いずれかの条件を満たせば実行対象となる。

入力 Rowset はすべて non-overlapping であることが要求される。

[`be/src/storage/base_compaction.cpp` L161-L168](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/base_compaction.cpp#L161-L168)

```cpp
Status BaseCompaction::_check_rowset_overlapping(const std::vector<RowsetSharedPtr>& rowsets) {
    for (auto& rs : rowsets) {
        if (rs->rowset_meta()->is_segments_overlapping()) {
            return Status::InternalError("base compaction segments overlapping error.");
        }
    }
    return Status::OK();
}
```

Segment が重複している Rowset を「BaseCompaction」に含めると、マージ時のキー順序保証が複雑化する。
そのため `_check_rowset_overlapping()` で事前に検証し、重複があれば「BaseCompaction」を中止する。

## CompactionManager によるスケジューリング

「Compaction」の候補管理と実行制御は `CompactionManager` が担う。

### 候補の管理

**CompactionCandidate** は Tablet, Compaction 種別, スコアを保持する構造体である。

[`be/src/storage/compaction_candidate.h` L27-L77](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_candidate.h#L27-L77)

```cpp
struct CompactionCandidate {
    // ... (中略) ...
};

```

候補はスコア降順でソートされた `std::set` に格納される。

[`be/src/storage/compaction_candidate.h` L81-L87](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_candidate.h#L81-L87)

```cpp
struct CompactionCandidateComparator {
    bool operator()(const CompactionCandidate& left, const CompactionCandidate& right) const {
        return left.score > right.score || (left.score == right.score && left.type > right.type) ||
               (left.score == right.score && left.type == right.type &&
                left.tablet->tablet_id() < right.tablet->tablet_id());
    }
};
```

`CompactionCandidateComparator` はスコアが高い候補を先頭に配置する。
`CompactionManager` はこの `std::set` を `_compaction_candidates` として保持する(compaction_manager.h L169)。

### スケジューリングループ

[`be/src/storage/compaction_manager.cpp` L71-L87](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_manager.cpp#L71-L87)

```cpp
void CompactionManager::_schedule() {
    // ... (中略) ...
}

```

`_schedule()` はループで候補キューからスコア最大の候補を取り出し、`submit_compaction_task()` で ThreadPool に投入する。
投入前に `_check_precondition()` で実行可否を検証する。

[`be/src/storage/compaction_manager.cpp` L247-L316](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_manager.cpp#L247-L316)

```cpp
bool CompactionManager::_check_precondition(const CompactionCandidate& candidate) {
    // ... (中略) ...
}

```

`_check_precondition()` は2つの制約を検証する。

- **ディスクごとの並行数制限**(L268-L276, L284-L290)：「CumulativeCompaction」と「BaseCompaction」のそれぞれについて、同一ディスク上で同時に実行できるタスク数を制限する。ディスク I/O の飽和を防ぐための設計である。
- **失敗後のインターバル**(L294-L312)：直前の Compaction が失敗した Tablet に対して、一定時間の再試行間隔を設ける。連続失敗によるリソース浪費を回避する。

候補の取り出しは `pick_candidate()` が行う。

[`be/src/storage/compaction_manager.cpp` L317-L344](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction_manager.cpp#L317-L344)

```cpp
bool CompactionManager::pick_candidate(CompactionCandidate* candidate) {
    std::lock_guard lg(_candidates_mutex);
    // ... (中略) ...
    auto iter = _compaction_candidates.begin();
    while (iter != _compaction_candidates.end()) {
        if (_check_compaction_disabled(*iter)) {
            _compaction_candidates.erase(iter++);
            continue;
        }
        if (_check_precondition(*iter)) {
            *candidate = *iter;
            _compaction_candidates.erase(iter);
            // ... (中略) ...
            return true;
        }
        iter++;
    }

    return false;
}
```

スコア降順の `std::set` から先頭の候補を取り出し、前提条件をチェックする。
条件を満たさなければ次の候補に進む。

```mermaid
flowchart TD
    A[候補キュー<br>スコア降順 std::set] --> B{pick_candidate}
    B --> C{_check_precondition}
    C -->|ディスク並行数超過| B
    C -->|失敗インターバル中| B
    C -->|OK| D[submit_compaction_task]
    D --> E[ThreadPool で実行]
    E --> F[do_compaction_impl]

```

## Compaction の実行フロー (non-PK)

候補が ThreadPool に投入されると、`do_compaction_impl()` が呼ばれる。

[`be/src/storage/compaction.cpp` L58-L161](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction.cpp#L58-L161)

```cpp
Status Compaction::do_compaction_impl() {
    // ... (中略) ...
}

```

処理は5つの段階に分かれる。

**1. 入力 Rowset の集計**(L61-L70)：入力 Rowset のサイズと行数を合算し、出力 Rowset の整合性チェックに使う。

**2. アルゴリズム選択**(L88-L93)：列数と Segment 数の積が閾値を超える場合は Vertical マージを選択する。
Horizontal マージは全列を同時に読み出すのに対し、Vertical マージは列グループごとに分けて読み出す。
列数が多いテーブルではメモリ消費を抑えるために Vertical マージが有利である。

**3. マージ実行**(L112-L121)：選択したアルゴリズムで入力 Rowset を読み出し、出力用の RowsetWriter に書き込む。

[`be/src/storage/compaction.h` L96-L99](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction.h#L96-L99)

```cpp
    Status _merge_rowsets_horizontally(size_t segment_iterator_num, Statistics* stats_output,
                                       const TabletSchemaCSPtr& tablet_schema);
    Status _merge_rowsets_vertically(size_t segment_iterator_num, Statistics* stats_output,
                                     const TabletSchemaCSPtr& tablet_schema);
```

Horizontal マージは `_merge_rowsets_horizontally()` を、Vertical マージは `_merge_rowsets_vertically()` を使う。
いずれも SegmentIterator で入力を読み出し、HeapMerge でキー順にマージして RowsetWriter に出力する。

**4. 出力 Rowset のビルド**(L127-L133)：RowsetWriter から最終的な Rowset オブジェクトを生成する。

**5. 行数整合性チェックと入れ替え**(L135-L138)：`check_correctness()` で入力の合計行数と出力の行数が一致するかを検証し、`modify_rowsets()` で Tablet のメタデータを更新する。

[`be/src/storage/compaction.cpp` L355-L371](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction.cpp#L355-L371)

```cpp
Status Compaction::modify_rowsets() {
    // ... (中略) ...
}

```

`modify_rowsets()` は Tablet のロックを取得し、入力 Rowset 群を出力 Rowset に置換する。
入力 Rowset は `_stale_rs_version_map` に移動し、進行中の読み取りが完了するまで保持される。

[`be/src/storage/compaction.cpp` L388-L400](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/compaction.cpp#L388-L400)

```cpp
Status Compaction::check_correctness(const Statistics& stats) {
    // ... (中略) ...
}

```

`check_correctness()` は入力と出力の行数を比較し、不一致があればエラーを返す。
Aggregate Key テーブルでは集約により行数が減るため、出力行数が入力行数以下であることだけを検証する。

```mermaid
flowchart LR
    subgraph 入力
        R1[Rowset 1]
        R2[Rowset 2]
        R3[Rowset 3]
    end

    R1 --> M{マージ<br>Horizontal<br>or Vertical}
    R2 --> M
    R3 --> M
    M --> W[RowsetWriter]
    W --> O[出力 Rowset]
    O --> CHK[check_correctness<br>行数検証]
    CHK --> MOD[modify_rowsets<br>メタ更新]

```

## Primary Key テーブルの更新管理 (TabletUpdates)

Primary Key テーブルでは `TabletUpdates` がバージョン管理と PrimaryIndex の更新を一元的に担う。

[`be/src/storage/tablet_updates.h` L108](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.h#L108)

```cpp
class TabletUpdates {
```

### EditVersionInfo によるバージョン管理

**EditVersionInfo** はバージョンごとの Rowset 一覧と DelVector を保持する。

[`be/src/storage/tablet_updates.h` L81-L106](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.h#L81-L106)

```cpp
struct EditVersionInfo {
    // ... (中略) ...
};

```

新しい書き込みが到着するたびに新しい「EditVersionInfo」が作成され、「TabletUpdates」のバージョン履歴に追加される。
Compaction も新しいバージョンを生成するため、通常の書き込みと Compaction は同じバージョン管理の枠組みで扱われる。

### 通常の書き込み (_apply_normal_rowset_commit)

[`be/src/storage/tablet_updates.cpp` L1341-L1898](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L1341-L1898)

```cpp
Status TabletUpdates::_apply_normal_rowset_commit(const EditVersionInfo& version_info, const RowsetSharedPtr& rowset) {
    // ... (中略) ...
    // 1. load upserts/deletes in rowset
    auto state_entry = manager->update_state_cache().get_or_create(
            strings::Substitute("$0_$1", tablet_id, rowset->rowset_id().to_string()));
    // ... (中略) ...
    // 2. load index
    auto index_entry = manager->index_cache().get_or_create(tablet_id);
    // ... (中略) ...
    if (rowset->has_data_files() || _tablet.get_enable_persistent_index()) {
        auto st = index.load(&_tablet);
        // ... (中略) ...
    }
    // ... (中略) ...
}
```

通常の Rowset コミットでは PrimaryIndex に対して upsert と delete を実行する。
新しい行のキーを PrimaryIndex に挿入し、同じキーの旧行が存在すれば DelVector に記録して論理削除する。
この Merge-on-Write 方式により、読み取り時のマージが不要になる。

### 列モード部分更新 (_apply_column_partial_update_commit)

[`be/src/storage/tablet_updates.cpp` L1128-L1277](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L1128-L1277)

```cpp
Status TabletUpdates::_apply_column_partial_update_commit(const EditVersionInfo& version_info,
                                                          const RowsetSharedPtr& rowset) {
    // ... (中略) ...
    // 1. load updates in rowset, prepare state for generating delta column group later.
    auto state_entry = manager->update_column_state_cache().get_or_create(
            strings::Substitute("$0_$1", tablet_id, rowset->rowset_id().to_string()));
    // ... (中略) ...
    // 2. load primary index, using it in finalize step.
    auto index_entry = manager->index_cache().get_or_create(tablet_id);
    // ... (中略) ...
    // 3. finalize and generate delta column group
    st = state.finalize(&_tablet, rowset.get(), rowset_id, index_meta, manager->mem_tracker(), new_del_vecs, index);
    // ... (中略) ...
}
```

列モード部分更新では、変更対象の列だけを Delta Column Group として別ファイルに書き出す。
全列を書き直す必要がないため、少数列の更新が高速になる。

## Delta Column Group

**Delta Column Group** は列モード部分更新で変更された列だけを記録する構造体である。

[`be/src/storage/delta_column_group.h` L35-L121](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/delta_column_group.h#L35-L121)

```cpp
class DeltaColumnGroup {
    // ... (中略) ...
};

```

内部には2つの主要なフィールドがある。

- `_column_uids`(L115)：更新された列の UID 一覧
- `_column_files`(L116)：データファイル名。`$rowsetid_$segid_$version_$seq.cols` という命名規則に従う

読み出し時には `get_column_idx()` で ColumnUID からファイル内のインデックスを解決する。

[`be/src/storage/delta_column_group.h` L51-L62](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/delta_column_group.h#L51-L62)

```cpp
    std::pair<int32_t, int32_t> get_column_idx(ColumnUID uid) const {
        for (int idx = 0; idx < _column_uids.size(); ++idx) {
            for (int cidx = 0; cidx < _column_uids[idx].size(); cidx++) {
                // ... (中略) ...
                if (_column_uids[idx][cidx] == uid) {
                    return std::pair<int32_t, int32_t>{std::pair{idx, cidx}};
                }
            }
        }
        return std::pair<int32_t, int32_t>{std::pair{-1, -1}};
    }
```

「Delta Column Group」は Compaction で統合される。
Compaction が実行されると、元の Segment データと「Delta Column Group」がマージされ、全列を含む新しい Segment が生成される。
これにより読み出し時の「Delta Column Group」参照コストが解消される。

## Primary Key Compaction

Primary Key テーブルの Compaction は `TabletUpdates` を経由して実行される。
non-PK テーブルとは異なり、PrimaryIndex の整合性を維持しながらマージを行う必要がある。

### 候補選択 (compaction)

[`be/src/storage/tablet_updates.cpp` L2977-L3105](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L2977-L3105)

```cpp
Status TabletUpdates::compaction(MemTracker* mem_tracker) {
    // ... (中略) ...
}

```

候補選択は貪欲法で行う。

[`be/src/storage/tablet_updates.cpp` L2954-L2964](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L2954-L2964)

```cpp
struct CompactionEntry {
    // ... (中略) ...
};

```

各 Rowset の `score_per_row` を計算し、スコアが高い順にソートする(L2954-L2963)。
スコアが高い Rowset から貪欲に選択し、合計サイズが上限に達するまで候補に追加する(L3052-L3076)。

### スコア計算 (_calc_compaction_score)

[`be/src/storage/tablet_updates.cpp` L3605-L3618](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L3605-L3618)

```cpp
void TabletUpdates::_calc_compaction_score(RowsetStats* stats) {
    if (stats->num_rows == 0) {
        stats->compaction_score = config::update_compaction_size_threshold;
        return;
    }
    // ... (中略) ...
    auto delete_bytes = (int64_t)(stats->byte_size * (double)stats->num_dels / stats->num_rows);
    stats->compaction_score =
            config::update_compaction_size_threshold * (stats->num_segments > 1 ? stats->num_segments - 1 : 1) +
            (cost_record_read + cost_record_write) * delete_bytes - cost_record_write * stats->byte_size;
}
```

スコアの計算式は次のとおりである(L3615-L3617)。

```text
score = size_threshold * (segments - 1) + (read_cost + write_cost) * delete_bytes - write_cost * total_bytes

```

Segment 数が多いほどスコアが高くなり、削除データが多いほど Compaction の効果が大きいため優先される。
一方、合計バイト数が大きい Rowset はコストが高いため、スコアを下げて過度な Compaction を避ける。

### レベル計算 (_calc_compaction_level)

[`be/src/storage/tablet_updates.cpp` L3581-L3603](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L3581-L3603)

```cpp
int32_t TabletUpdates::_calc_compaction_level(RowsetStats* stats) {
    if (stats->num_rows == 0) {
        return -1;
    }
    size_t new_rows = stats->num_rows - stats->num_dels;
    size_t new_bytes = stats->byte_size * new_rows / stats->num_rows;
    // ... (中略) ...
    if (new_bytes == 0) {
        return -1;
    } else if (new_bytes <= min_level_size) {
        return 0;
    } else if (new_bytes >= max_level_size) {
        return level_num;
    } else {
        auto x = (double)new_bytes / min_level_size;
        return log(x) / log((double)level_multiple);
    }
}
```

Size-tiered compaction の考え方で、Rowset のバイト数からレベルを算出する(L3588-L3602)。
同じレベルの Rowset 同士をマージ候補にすることで、書き込み増幅を抑制する。

### マージ実行 (_do_compaction)

[`be/src/storage/tablet_updates.cpp` L2043-L2148](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L2043-L2148)

```cpp
Status TabletUpdates::_do_compaction(std::unique_ptr<CompactionInfo>* pinfo, const vector<uint32_t>& all_rowset_ids) {
    // ... (中略) ...
    RowsetWriterContext context;
    context.rowset_id = StorageEngine::instance()->next_rowset_id();
    // ... (中略) ...
    context.is_pk_compaction = true;
    context.is_compaction = true;
    // ... (中略) ...
    st = compaction_merge_rowsets(_tablet, info->start_version.major_number(), input_rowsets, rowset_writer.get(), cfg,
                                  cur_tablet_schema);
    // ... (中略) ...
    // 4. commit compaction
    EditVersion version;
    RETURN_IF_ERROR(_commit_compaction(pinfo, *output_rowset, &version));
    // ... (中略) ...
    return Status::OK();
}
```

`_do_compaction()` は入力 Rowset をマージして出力 Rowset を生成し、`_commit_compaction()` でバージョンを進める。
RowsetWriter の構成(L2084-L2107)、マージの実行と出力 Rowset のビルド(L2112-L2134)、コミット(L2137)の順に進む。

### コミットと PrimaryIndex 更新 (_commit_compaction, _apply_compaction_commit)

[`be/src/storage/tablet_updates.cpp` L2197-L2332](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L2197-L2332)

```cpp
Status TabletUpdates::_commit_compaction(std::unique_ptr<CompactionInfo>* pinfo, const RowsetSharedPtr& rowset,
                                         EditVersion* commit_version) {
    // ... (中略) ...
    std::lock_guard wl(_lock);
    // ... (中略) ...
    // handle conflict between column mode partial update
    if (rowset->num_rows() > 0) {
        RETURN_IF_ERROR(_check_conflict_with_partial_update((*pinfo).get()));
    }
    // ... (中略) ...
    std::unique_ptr<EditVersionInfo> edit_version_info = std::make_unique<EditVersionInfo>();
    edit_version_info->version = EditVersion(edit_version_pb->major_number(), edit_version_pb->minor_number());
    // ... (中略) ...
    _edit_version_infos.emplace_back(std::move(edit_version_info));
    // ... (中略) ...
    return Status::OK();
}
```

`_commit_compaction()` は新しい「EditVersionInfo」を作成し、バージョン履歴に追加する。

[`be/src/storage/tablet_updates.cpp` L2356-L2667](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L2356-L2667)

```cpp
Status TabletUpdates::_apply_compaction_commit(const EditVersionInfo& version_info) {
    // ... (中略) ...
    // 1. load index
    std::lock_guard lg(_index_lock);
    auto index_entry = manager->index_cache().get_or_create(tablet_id);
    // ... (中略) ...
    // 2. iterator new rowset's pks, update primary index, generate delvec
    size_t total_deletes = 0;
    size_t total_rows = 0;
    // ... (中略) ...
    uint32_t max_src_rssid = 0;

    if (!use_light_apply_compaction) {
        // ... (中略) ...
        max_src_rssid = max_rowset_id + rowset->num_segments() - 1;

        for (size_t i = 0; i < _compaction_state->pk_cols.size(); i++) {
            // ... (中略) ...
            } else {
                // replace will not grow hashtable, so don't need to check memory limit
                st = index.try_replace(rssid, 0, *pk_col, max_src_rssid, &tmp_deletes);
                // ... (中略) ...
            }
            // ... (中略) ...
        }
        // ... (中略) ...
    }
    // ... (中略) ...
}
```

`_apply_compaction_commit()` は PrimaryIndex を使って、出力 Rowset のキーで旧エントリを置き換える。
処理の要点は次のとおりである。

1. PrimaryIndex をロードする(L2384-L2409)
2. 入力 Rowset の最大 rssid(`max_src_rssid`)を計算する(L2475-L2483)
3. 出力 Rowset のキーで `try_replace()` を呼ぶ(L2485-L2520)

`try_replace()` は PrimaryIndex 内の既存エントリの rssid が `max_src_rssid` 以下である場合にのみ置き換えを行う。
rssid が `max_src_rssid` より大きいエントリは、Compaction の実行中に到着した新しい書き込みに由来する。
このエントリを上書きすると新しいデータが失われるため、`max_src_rssid` による比較で保護する。
これが Primary Key Compaction と並行書き込みの整合性を保証する仕組みである。

### 列モード部分更新との競合検出

[`be/src/storage/tablet_updates.cpp` L2156-L2195](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L2156-L2195)

```cpp
Status TabletUpdates::_check_conflict_with_partial_update(CompactionInfo* info) {
    // ... (中略) ...
    // check edit version info from latest to info->start_version
    for (auto i = _edit_version_infos.rbegin(); i != _edit_version_infos.rend() && info->start_version < (*i)->version;
         i++) {
        // ... (中略) ...
        if (need_cancel) {
            std::string msg = strings::Substitute(
                    "compaction conflict with partial update failed, tabletid:$0 ver:$1-$2", _tablet.tablet_id(),
                    info->start_version.major_number(), (*i)->version.major_number());
            // ... (中略) ...
            return Status::Cancelled(msg);
        }
    }
    return Status::OK();
}
```

列モード部分更新と Compaction が同じ Rowset を対象にすると、「Delta Column Group」が不整合を起こす可能性がある。
`_check_conflict_with_partial_update()` は Compaction の入力 Rowset が部分更新中でないかを検証し、競合があれば Compaction をキャンセルする。

## PersistentIndex のハッシュインデックスによるポイント更新 O(1) 化

Primary Key テーブルの性能を支える中核が **PersistentIndex** である。
PrimaryIndex をディスクに永続化しつつ、キーの upsert と検索を O(1) で実行する。

### 階層構造

[`be/src/storage/persistent_index.h` L674-L962](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/persistent_index.h#L674-L962)

```cpp
class PersistentIndex {
    // ... (中略) ...
};

```

「PersistentIndex」は3層の階層で構成される。

- **L0** (`_l0`, ShardByLengthMutableIndex, L922)：インメモリのハッシュテーブル。書き込みはまず L0 に入る。
- **L1** (`_l1_vec`, ImmutableIndex, L928)：L0 がフラッシュされて生成されるオンディスクのインデックスファイル。
- **L2** (`_l2_vec`, ImmutableIndex, L938)：L1 が増えすぎた場合に major compaction で統合されるオンディスクファイル。

### IndexValue の構造

[`be/src/storage/persistent_index.h` L118-L129](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/persistent_index.h#L118-L129)

```cpp
struct IndexValue {
    // ... (中略) ...
};

```

**IndexValue** は8バイトの値で、上位32ビットに rssid(Rowset Segment ID)、下位32ビットに rowid を格納する。
この構造により、キーからデータの物理位置を1回のハッシュ探索で特定できる。

### MutableIndex (L0)

[`be/src/storage/persistent_index.h` L185-L299](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/persistent_index.h#L185-L299)

```cpp
class MutableIndex {
    // ... (中略) ...
};

```

**MutableIndex** は phmap(parallel hashmap)ベースのハッシュテーブルを内部に持つ。
phmap は Google の `absl::flat_hash_map` と同等の SIMD 最適化されたオープンアドレッシングハッシュテーブルであり、upsert, get, erase が平均 O(1) で動作する。
Primary Key の更新や検索が高速な理由は、この L0 のインメモリハッシュテーブルにある。

### L0 から L1 へのフラッシュと major compaction

L0 のサイズが閾値に達すると、ハッシュテーブルの内容がディスクにフラッシュされて L1 の ImmutableIndex ファイルになる。
L1 ファイルが増えすぎると `major_compaction()` で統合され、L2 ファイルが生成される。

[`be/src/storage/persistent_index.h` L787-L788](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/persistent_index.h#L787-L788)

```cpp
    Status major_compaction(DataDir* data_dir, int64_t tablet_id, std::shared_timed_mutex* mutex,
                            IOStat* stat = nullptr);
```

[`be/src/storage/persistent_index.h` L792](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/persistent_index.h#L792)

```cpp
    static double major_compaction_score(const PersistentIndexMetaPB& index_meta);
```

`major_compaction_score()` は L2 ファイルの書き込み増幅度を返す。
スコアが高いほど統合の効果が大きいことを示し、閾値を超えると PK Index の major compaction が実行される。

[`be/src/storage/tablet_updates.cpp` L4829-L4863](https://github.com/StarRocks/starrocks/blob/4.1.1/be/src/storage/tablet_updates.cpp#L4829-L4863)

```cpp
Status TabletUpdates::pk_index_major_compaction() {
    auto manager = StorageEngine::instance()->update_manager();
    auto index_entry = manager->index_cache().get_or_create(_tablet.tablet_id());
    // ... (中略) ...
    auto st = Status::OK();
    {
        std::lock_guard lg(_index_lock);
        st = index.load(&_tablet);
    }
    // ... (中略) ...
    st = index.major_compaction(_tablet.data_dir(), _tablet.tablet_id(), _tablet.updates()->get_index_lock(), &stat);
    if (st.ok()) {
        // reset score after major compaction finish
        _pk_index_write_amp_score.store(0.0);
        _extra_file_size_cache.pindex_size.store(stat.total_file_size);
    }
    return st;
}
```

`pk_index_major_compaction()` は「PersistentIndex」の major compaction を呼び出し、L1/L2 ファイルを統合する。

```mermaid
flowchart TD
    W[書き込み / upsert] --> L0["L0: MutableIndex<br>(インメモリ phmap)"]
    L0 -->|サイズ閾値超過| FL[フラッシュ]
    FL --> L1["L1: ImmutableIndex<br>(オンディスク)"]
    L1 -->|ファイル数増加| MC[major compaction]
    MC --> L2["L2: ImmutableIndex<br>(オンディスク, 統合済み)"]

    Q[キー検索] --> L0
    L0 -->|miss| L1
    L1 -->|miss| L2

```

キー検索時は L0 を最初に参照し、ヒットしなければ L1、L2 の順に探索する。
L0 はインメモリであるため、書き込み直後のキーは L0 へのハッシュ探索1回で解決する。
この階層構造は LSM-Tree と類似しているが、ポイント検索に特化したハッシュベースの設計により、B-Tree のような範囲スキャンではなく O(1) の更新と検索を実現している。

## まとめ

non-PK テーブルでは「CumulativeCompaction」が小さな Rowset を頻繁にまとめ、「BaseCompaction」が累積した Rowset を統合する。
CompactionManager がスコア降順の候補キューとディスクごとの並行数制限でスケジューリングを行い、過負荷を防ぐ。

Primary Key テーブルでは「TabletUpdates」が PrimaryIndex を使った Merge-on-Write と Compaction を統合的に管理する。
Compaction 中の新しい書き込みは `max_src_rssid` による比較で保護され、データの整合性が保証される。
列モード部分更新では「Delta Column Group」が変更列だけを記録し、全列の書き直しを回避する。

「PersistentIndex」の phmap ベースのハッシュテーブルが、Primary Key の upsert と検索を O(1) で実行する。
L0(インメモリ), L1, L2 の階層構造により、ディスク永続化と高速なポイント更新を両立させている。

## 関連する章

- 第16章「Tablet, Rowset とデータモデル」(Tablet と Rowset の構造、Primary Key テーブルの基本設計)
- 第17章「Segment ファイルフォーマット」(Compaction の入出力となる Segment の内部構造)
- 第18章「インデックスサブシステム」(Segment 内のインデックスと検索最適化)
