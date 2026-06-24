# 第5章 内部キー形式 InternalKey

> **本章で読むソース**
>
> - [`db/dbformat.h`](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h)
> - [`db/lookup_key.h`](https://github.com/facebook/rocksdb/blob/v11.1.1/db/lookup_key.h)
> - [`db/dbformat.cc`](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.cc)

## この章の狙い

RocksDB はユーザーが渡したキーをそのまま格納せず、版を区別するためのトレーラを末尾に付けた内部キーへ変換して扱う。
本章では、内部キーが「ユーザーキー＋8バイトのトレーラ」というレイアウトを持つこと、トレーラに `SequenceNumber` と `ValueType` をどう詰めるか、内部キーをどの順序で並べると最新の版を先頭で拾えるかを読む。
あわせて、`Get` が探索に使う `LookupKey` が1本のバッファで3つの表現を兼ねる仕組みを見る。

## 前提

ユーザーキーと内部キーはどちらも [`rocksdb/slice.h`](https://github.com/facebook/rocksdb/blob/v11.1.1/include/rocksdb/slice.h) の `Slice`（先頭ポインタと長さの組）として受け渡される。
`Slice` の性質は前章で扱った（[第4章 Slice](../part01-data-model/04-slice.md)）。
内部キーのもう一方の構成要素である `SequenceNumber` は本章で説明する。

## ユーザーキーと内部キーの違い

RocksDB は同じユーザーキーに対する書き込みを上書きせず、新しいエントリとして追記していく。
`memtable` も `SST` も追記専用の構造であり、`Put` も `Delete` も「いつの操作か」を持った新しいレコードとして積み上がる。
このため、あるユーザーキーを読むときには、同じキーに対する複数の版のうちどれを採用すべきかを決められなければならない。

版を区別する手段が `SequenceNumber` である。
RocksDB は書き込みごとに単調増加する整数を割り当て、これを各エントリに埋め込む。
読み取り側はスナップショットを表す `SequenceNumber` を持ち、それ以下の版のうち最も新しいものを選ぶ。
この仕組みが多版同時実行制御（MVCC）であり、書き込みとスナップショット読み取りが互いをブロックせずに進める根拠になっている。

エントリには版の番号に加えて、そのレコードが何の操作だったかも必要になる。
`kTypeValue`（通常の値）と `kTypeDeletion`（削除マーカー）を区別できなければ、最新版が削除だったのか実在する値だったのかを判定できない。
そこで RocksDB は、ユーザーキーの末尾に `SequenceNumber` と操作種別（`ValueType`）を詰めた8バイトのトレーラを付け、これを**内部キー**（internal key）と呼ぶ。
`db/dbformat.h` の冒頭コメントが、この三要素がまとめて符号化されることを述べている。

[`db/dbformat.h` L28-L32](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L28-L32)

```cpp
// The file declares data structures and functions that deal with internal
// keys.
// Each internal key contains a user key, a sequence number (SequenceNumber)
// and a type (ValueType), and they are usually encoded together.
// There are some related helper classes here.
```

内部キーのバイト並びは次のとおりである。
ユーザーキーが先頭に来て、その後ろに固定長8バイトのトレーラが続く。

```text
+-----------------------------+---------------------------+
|          user_key           |   sequence(7B) | type(1B) |
|        (可変長)             |       8B のトレーラ        |
+-----------------------------+---------------------------+
```

トレーラを末尾に置く配置には実務上の効きどころがある。
ユーザーキーがバイト列の先頭から始まるので、先頭から `size - 8` バイトを切り出せばユーザーキーが得られる。
比較やプレフィックス判定はユーザーキーに対して行うことが多く、その取り出しがコピーなしの `Slice` 構築で済む。

## トレーラの中身：ValueType と SequenceNumber を8バイトに詰める

トレーラの下位1バイトは操作種別を表す `ValueType` である。
`ValueType` は `unsigned char` を基底とする列挙で、各操作に対応する値を持つ。

[`db/dbformat.h` L41-L78](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L41-L78)

```cpp
enum ValueType : unsigned char {
  kTypeDeletion = 0x0,
  kTypeValue = 0x1,
  kTypeMerge = 0x2,
  // ... (中略) ...
  kTypeSingleDeletion = 0x7,
  // ... (中略) ...
  kTypeRangeDeletion = 0xF,               // meta block
  // ... (中略) ...
  kTypeValuePreferredSeqno = 0x18,              // Value with a unix write time
  // ... (中略) ...
  kMaxValue = 0x7F  // Not used for storing records.
};
```

トレーラの残り7バイトが `SequenceNumber` である。
`SequenceNumber` は [`include/rocksdb/types.h` L22](https://github.com/facebook/rocksdb/blob/v11.1.1/include/rocksdb/types.h#L22) で `using SequenceNumber = uint64_t;` と定義された64ビット整数だが、トレーラに収める際は上位56ビットだけを使う。
下位8ビット（1バイト）を `ValueType` のために空けておくためである。
コメントと `kMaxSequenceNumber` の定義がこの境界を示す。

[`db/dbformat.h` L127-L134](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L127-L134)

```cpp
// We leave eight bits empty at the bottom so a type and sequence#
// can be packed together into 64-bits.
static const SequenceNumber kMaxSequenceNumber = ((0x1ull << 56) - 1);

static const SequenceNumber kDisableGlobalSequenceNumber =
    std::numeric_limits<uint64_t>::max();

constexpr uint64_t kNumInternalBytes = 8;
```

`kMaxSequenceNumber` が `2^56 - 1` であることが、`SequenceNumber` の有効幅が56ビット（7バイト）であることを定める。
これに下位8ビット（1バイト）の `ValueType` 領域を加えると64ビットになり、トレーラ全体が `kNumInternalBytes`（8バイト）にぴったり収まる。
言い換えると、トレーラは `(seq << 8) | type` という1個の `uint64_t` で表せる。

この詰め込みを行うのが `PackSequenceAndType`、ほどくのが `UnPackSequenceAndType` である。

[`db/dbformat.h` L180-L199](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L180-L199)

```cpp
// Pack a sequence number and a ValueType into a uint64_t
inline uint64_t PackSequenceAndType(uint64_t seq, ValueType t) {
  assert(seq <= kMaxSequenceNumber);
  // kTypeMaxValid is used in TruncatedRangeDelIterator, see its constructor.
  assert(IsExtendedValueType(t) || t == kTypeMaxValid);
  return (seq << 8) | t;
}

// Given the result of PackSequenceAndType, store the sequence number in *seq
// and the ValueType in *t.
inline void UnPackSequenceAndType(uint64_t packed, uint64_t* seq,
                                  ValueType* t) {
  *seq = packed >> 8;
  *t = static_cast<ValueType>(packed & 0xff);

  // Commented the following two assertions in order to test key-value checksum
  // on corrupted keys without crashing ("DbKvChecksumTest").
  // assert(*seq <= kMaxSequenceNumber);
  // assert(IsExtendedValueType(*t));
}
```

`PackSequenceAndType` は `seq` を8ビット左シフトして上位に置き、下位8ビットへ `t` を論理和で重ねる。
シフト前の `assert` が `seq <= kMaxSequenceNumber` を確かめるので、左シフトしても `seq` が下位8ビットへはみ出すことはない。
復元は逆順で、`packed >> 8` で `seq` を、`packed & 0xff` で `type` を取り出す。
この対称な2操作だけでトレーラを符号化と復号できることが、後で見る比較の高速化につながる。

## ValueType の種類と意味

`ValueType` は memtable や SST に積まれるレコードがどの操作だったかを表す。
内部キーに現れる主な種別は次のとおりである。

- **kTypeValue**：`Put` で書かれた通常の値。
- **kTypeDeletion**：`Delete` が置く削除マーカー。実体を持たず、対象キーが削除されたことだけを示す（tombstone と呼ばれる）。
- **kTypeMerge**：`Merge` で書かれたマージオペランド。読み取り時にマージ演算子で畳み込まれる。
- **kTypeSingleDeletion**：`SingleDelete` が置く単一削除マーカー。1回の `Put` に1回だけ対応する削除であることを前提とする。
- **kTypeRangeDeletion**：`DeleteRange` による範囲削除。これは個々のキーのトレーラではなく、SST のメタブロックに格納される（列挙のコメントに `meta block` とある）。

`kTypeColumnFamilyValue` や `kTypeBeginPrepareXID` のように `WAL only` と注記された種別もある。
これらは WAL レコードに付くタグであり、memtable や SST の内部キートレーラには現れない。
両者を振り分けるのが `IsValueType` と `IsExtendedValueType` である。

[`db/dbformat.h` L111-L125](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L111-L125)

```cpp
// Checks whether a type is an inline value type
// (i.e. a type used in memtable skiplist and sst file datablock).
inline bool IsValueType(ValueType t) {
  return t <= kTypeMerge || kTypeSingleDeletion == t || kTypeBlobIndex == t ||
         kTypeDeletionWithTimestamp == t || kTypeWideColumnEntity == t ||
         kTypeValuePreferredSeqno == t;
}

// Checks whether a type is from user operation
// kTypeRangeDeletion is in meta block so this API is separated from above
// kTypeMaxValid can be from keys generated by
// TruncatedRangeDelIterator::start_key()
inline bool IsExtendedValueType(ValueType t) {
  return IsValueType(t) || t == kTypeRangeDeletion || t == kTypeMaxValid;
}
```

`IsValueType` が真になる種別は memtable のスキップリストや SST のデータブロックに直接置けるもので、`IsExtendedValueType` はそこに範囲削除などを加えた集合である。
`PackSequenceAndType` の `assert` がこの集合を要求していたのは、内部キーに詰められる種別だけをトレーラへ書くという制約を実行時に確かめるためである。

これらの値が固定されている理由は、列挙の直前のコメントが述べている。

[`db/dbformat.h` L36-L40](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L36-L40)

```cpp
// Value types encoded as the last component of internal keys.
// DO NOT CHANGE THESE ENUM VALUES: they are embedded in the on-disk
// data structures.
// The highest bit of the value type needs to be reserved to SST tables
// for them to do more flexible encoding.
```

`ValueType` の値はディスク上のデータ構造に直接埋め込まれるので、変更すると過去に書いた SST を読めなくなる。
列挙値が飛び飛びでも 0x7F が `kMaxValue` で止まるのもこのためで、最上位ビットは SST 側の柔軟な符号化のために予約されている。
種別の意味そのものより、値が永続フォーマットの一部として凍結されている点が、この列挙を理解するうえで効いてくる。

## エンコードと分解：InternalKey と ParsedInternalKey

内部キーには符号化済みの形と、ほどいた形の2通りの表現がある。
ほどいた形が `ParsedInternalKey` で、ユーザーキーと `SequenceNumber` と `ValueType` を別々のフィールドに持つ。

[`db/dbformat.h` L139-L152](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L139-L152)

```cpp
// The data structure that represents an internal key in the way that user_key,
// sequence number and type are stored in separated forms.
struct ParsedInternalKey {
  Slice user_key;
  SequenceNumber sequence;
  ValueType type;

  ParsedInternalKey()
      : sequence(kMaxSequenceNumber),
        type(kTypeDeletion)  // Make code analyzer happy
  {}                         // Intentionally left uninitialized (for speed)
  // u contains timestamp if user timestamp feature is enabled.
  ParsedInternalKey(const Slice& u, const SequenceNumber& seq, ValueType t)
      : user_key(u), sequence(seq), type(t) {}
```

`ParsedInternalKey` を1本のバイト列に符号化するのが `AppendInternalKey` である。
ヘッダのコメントが、出力が「ユーザーキーの後ろにトレーラを付けた並び」になることを図で示している。

[`db/dbformat.h` L206-L211](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L206-L211)

```cpp
// Append the serialization of "key" to *result.
//
// input [internal key]: <user_key | seqno + type>
// output before: empty
// output:               <user_key | seqno + type>
void AppendInternalKey(std::string* result, const ParsedInternalKey& key);
```

すでに `result` の末尾にユーザーキーが置かれているなら、トレーラだけを足す `AppendInternalKeyFooter` が使える。

[`db/dbformat.h` L232-L239](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L232-L239)

```cpp
// Serialized internal key consists of user key followed by footer.
// This function appends the footer to *result, assuming that *result already
// contains the user key at the end.
//
// output before: <user_key>
// output after:  <user_key | seqno + type>
void AppendInternalKeyFooter(std::string* result, SequenceNumber s,
                             ValueType t);
```

符号化済みの内部キーを保持するのが `class InternalKey` で、内部状態は `std::string rep_` 1本だけである。

[`db/dbformat.h` L431-L443](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L431-L443)

```cpp
class InternalKey {
 private:
  std::string rep_;

 public:
  InternalKey() {}  // Leave rep_ as empty to indicate it is invalid
  InternalKey(const Slice& _user_key, SequenceNumber s, ValueType t) {
    AppendInternalKey(&rep_, ParsedInternalKey(_user_key, s, t));
  }
  InternalKey(const Slice& _user_key, SequenceNumber s, ValueType t, Slice ts) {
    AppendInternalKeyWithDifferentTimestamp(
        &rep_, ParsedInternalKey(_user_key, s, t), ts);
  }
```

コンストラクタは `AppendInternalKey` を呼んで `rep_` に符号化結果を書く。
`Encode()` は `rep_` をそのまま `Slice` として返し、`DecodeFrom()` は逆に外から受け取ったバイト列を `rep_` に複写する。
`user_key()` は `rep_` の先頭から `size - 8` バイトを `Slice` として返す（取り出し関数は後述）。

`rep_` が文字列1本で済む設計の効きどころが `ConvertFromUserKey` に表れている。

[`db/dbformat.h` L499-L509](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L499-L509)

```cpp
  // The underlying representation.
  // Intended only to be used together with ConvertFromUserKey().
  std::string* rep() { return &rep_; }

  const std::string* const_rep() const { return &rep_; }

  // Assuming that *rep() contains a user key, this method makes internal key
  // out of it in-place. This saves a memcpy compared to Set()/SetFrom().
  void ConvertFromUserKey(SequenceNumber s, ValueType t) {
    AppendInternalKeyFooter(&rep_, s, t);
  }
```

呼び出し側が `rep()` 経由でユーザーキーを直接 `rep_` に書き込んでおけば、`ConvertFromUserKey` はトレーラを追記するだけで内部キーが完成する。
コメントが述べるとおり、ユーザーキーをいったん別バッファに作ってから `Set` で複写する経路に比べ、`memcpy` を1回節約できる。

`InternalKey` には、あるユーザーキーに対する内部キーの上限と下限を作る補助もある。

[`db/dbformat.h` L445-L457](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L445-L457)

```cpp
  // sets the internal key to be bigger or equal to all internal keys with this
  // user key
  void SetMaxPossibleForUserKey(const Slice& _user_key) {
    AppendInternalKey(
        &rep_, ParsedInternalKey(_user_key, 0, static_cast<ValueType>(0)));
  }

  // sets the internal key to be smaller or equal to all internal keys with this
  // user key
  void SetMinPossibleForUserKey(const Slice& _user_key) {
    AppendInternalKey(&rep_, ParsedInternalKey(_user_key, kMaxSequenceNumber,
                                               kValueTypeForSeek));
  }
```

`SetMaxPossibleForUserKey` は `seq=0`、`type=0` を詰め、`SetMinPossibleForUserKey` は `seq=kMaxSequenceNumber`、`type=kValueTypeForSeek` を詰める。
なぜ最小の `seq` が最大の内部キーになり、最大の `seq` が最小の内部キーになるのかは、次に見る比較規則で明らかになる。

符号化済みの内部キーから各部分を取り出すのが `ExtractUserKey` と `ExtractInternalKeyFooter` である。

[`db/dbformat.h` L322-L329](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L322-L329)

```cpp
// Returns the user key portion of an internal key.
//
// input [internal key]: <user_key | seqno + type>
// output:               <user_key>
inline Slice ExtractUserKey(const Slice& internal_key) {
  assert(internal_key.size() >= kNumInternalBytes);
  return Slice(internal_key.data(), internal_key.size() - kNumInternalBytes);
}
```

[`db/dbformat.h` L363-L369](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L363-L369)

```cpp
// input [internal key]: <user_provided_key | ts | seqno + type>
// output:                                        <seqno + type>
inline uint64_t ExtractInternalKeyFooter(const Slice& internal_key) {
  assert(internal_key.size() >= kNumInternalBytes);
  const size_t n = internal_key.size();
  return DecodeFixed64(internal_key.data() + n - kNumInternalBytes);
}
```

`ExtractUserKey` は先頭から `size - 8` バイトを指す `Slice` を返すだけで、メモリの複写をしない。
内部キーの末尾8バイトが固定長トレーラだと分かっているので、ユーザーキー部分はゼロコピーで切り出せる。
`ExtractInternalKeyFooter` は末尾8バイトを `DecodeFixed64` で1個の `uint64_t` として読む。
このトレーラ整数の読み出しが、比較のたびに使われる。

## InternalKeyComparator の比較規則

内部キーの並び順を決めるのが `InternalKeyComparator::Compare` である。
コメントに並べる基準が明記されている。

[`db/dbformat.h` L1080-L1099](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L1080-L1099)

```cpp
inline int InternalKeyComparator::Compare(const Slice& akey,
                                          const Slice& bkey) const {
  // Order by:
  //    increasing user key (according to user-supplied comparator)
  //    decreasing sequence number
  //    decreasing type (though sequence# should be enough to disambiguate)
  int r = user_comparator_.Compare(ExtractUserKey(akey), ExtractUserKey(bkey));
  if (r == 0) {
    const uint64_t anum =
        DecodeFixed64(akey.data() + akey.size() - kNumInternalBytes);
    const uint64_t bnum =
        DecodeFixed64(bkey.data() + bkey.size() - kNumInternalBytes);
    if (anum > bnum) {
      r = -1;
    } else if (anum < bnum) {
      r = +1;
    }
  }
  return r;
}
```

比較はまずユーザーキーをユーザー指定コンパレータで比べ、ユーザーキーが昇順になるよう並べる。
ユーザーキーが等しいとき（`r == 0`）だけ、末尾8バイトのトレーラを `DecodeFixed64` で `uint64_t` として読み、その大小で順序を決める。
ここで `anum > bnum` のとき `-1` を返している。
トレーラ整数が大きいほど「小さい」と判定され、並べたときに前へ来る。
トレーラ整数による副順序は降順である。

降順にすると最新の版が先頭へ来る理由は、トレーラの詰め方にある。
`SequenceNumber` はトレーラの上位56ビットに入っているので、`seq` が新しいほどトレーラ整数も大きい。
降順で並べると大きいトレーラ整数が前に来るため、同じユーザーキーのエントリ群は新しい `seq` から順に並ぶ。
`Get` やイテレータはあるユーザーキーを順方向に走査して最初に当たったエントリを採用すればよく、それが見えている版のうち最新だと保証される。
以後の古い版は読み飛ばせるので、最新版の取得が走査の先頭1件で決まる。

この比較には分岐削減の工夫がある。
`seq` と `type` を別々のフィールドとして比べるなら、まず `seq` を比較し、等しければ `type` を比較する二段の分岐が要る。
ところがトレーラは `(seq << 8) | type` という1個の `uint64_t` なので、`DecodeFixed64` で読んだ8バイト整数を一度大小比較するだけで、`seq` 降順と `type` 降順のタイブレークが同時に決まる。
`seq` を上位、`type` を下位に置いた配置が、二段の比較を整数1回の比較へ畳み込んでいる。
`type` を除いて `seq` だけで比較したい場面のために、トレーラを `>> 8` してから比べる `CompareKeySeq`（[`db/dbformat.h` L1101 以降](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.h#L1101-L1118)）も用意されている。

## 探索キーと kValueTypeForSeek

あるスナップショット（`SequenceNumber`）で読みたいユーザーキーを探すとき、その読みたい位置に対応する内部キーを組み立てて二分探索のシーク先にする。
このとき詰める `ValueType` には、内部キーに現れる種別のうち最大の値を選ぶ必要がある。
理由を `kValueTypeForSeek` の定義に付いたコメントが説明している。

[`db/dbformat.cc` L22-L29](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.cc#L22-L29)

```cpp
// kValueTypeForSeek defines the ValueType that should be passed when
// constructing a ParsedInternalKey object for seeking to a particular
// sequence number (since we sort sequence numbers in decreasing order
// and the value type is embedded as the low 8 bits in the sequence
// number in internal keys, we need to use the highest-numbered
// ValueType, not the lowest).
const ValueType kValueTypeForSeek = kTypeValuePreferredSeqno;
```

同じユーザーキーと同じ `seq` でも、`type` が大きいほどトレーラ整数が大きく、比較順では前へ来る。
探索キーが目的の `seq` を持つ実エントリより確実に前（小さい側）に位置するためには、`type` を取りうる最大値にしておく必要がある。
そうすれば、その `seq` 以下で最も新しいエントリへ正しくシークできる。
`kValueTypeForSeek` は現状 `kTypeValuePreferredSeqno`（0x18）に割り当てられている。

先ほどの `SetMinPossibleForUserKey` が `seq=kMaxSequenceNumber`、`type=kValueTypeForSeek` を詰めていたのは、これと同じ理由である。
`seq` を最大、`type` を最大にすればトレーラ整数が最大になり、降順比較では最も前へ来る。
そのユーザーキーを持つどの内部キーよりも小さい（前にある）位置を表すので、「同一ユーザーキーで最小の内部キー」になる。

## LookupKey の3-in-1 レイアウト

`Get` がキーを探すとき、目的地によって要求されるキーの表現が異なる。
memtable は長さ接頭辞付きのキーを、SST 側のイテレータは内部キーを、ユーザー比較はユーザーキーを要求する。
これらを別々に作るとそのたびにコピーが要る。
`LookupKey` は1本のバッファにこの3表現を同居させ、住所の取り方だけで使い分ける。
そのレイアウトをヘッダのコメントが示す。

[`db/lookup_key.h` L46-L53](https://github.com/facebook/rocksdb/blob/v11.1.1/db/lookup_key.h#L46-L53)

```cpp
  // We construct a char array of the form:
  //    klength  varint32               <-- start_
  //    userkey  char[klength]          <-- kstart_
  //    tag      uint64
  //                                    <-- end_
  // The array is a suitable MemTable key.
  // The suffix starting with "userkey" can be used as an InternalKey.
```

バッファは先頭にユーザーキー長を `varint32` で書いた `klength`、続いてユーザーキー本体、末尾に8バイトの `tag`（トレーラ）という並びになる。
`start_` がバッファ先頭、`kstart_` がユーザーキー先頭、`end_` がバッファ末尾を指す。

```text
        start_                kstart_                       end_
          |                     |                            |
          v                     v                            v
        +---------------------+-------------------+----------+
        | klength (varint32)  | userkey (klength) | tag (8B) |
        +---------------------+-------------------+----------+

        |<----------- memtable_key() ------------------------>|
                              |<------ internal_key() ------->|
                              |<- user_key() ->|
```

3つのアクセサが、この同じバイト列の異なる範囲を `Slice` として返す。

[`db/lookup_key.h` L29-L44](https://github.com/facebook/rocksdb/blob/v11.1.1/db/lookup_key.h#L29-L44)

```cpp
  // Return a key suitable for lookup in a MemTable.
  Slice memtable_key() const {
    return Slice(start_, static_cast<size_t>(end_ - start_));
  }

  // Return an internal key (suitable for passing to an internal iterator)
  Slice internal_key() const {
    return Slice(kstart_, static_cast<size_t>(end_ - kstart_));
  }

  // Return the user key.
  // If user-defined timestamp is enabled, then timestamp is included in the
  // result.
  Slice user_key() const {
    return Slice(kstart_, static_cast<size_t>(end_ - kstart_ - 8));
  }
```

`memtable_key()` は `start_` から `end_` までの全体（長さ接頭辞を含む）、`internal_key()` は `kstart_` から `end_` まで（ユーザーキー＋トレーラ）、`user_key()` は `kstart_` から末尾8バイトを除いた範囲を返す。
3表現とも同じバッファの部分 `Slice` なので、表現を切り替えてもコピーは起きない。
これが `LookupKey` の効きどころで、1回のバッファ構築を3通りの用途に使い回している。

このバッファを組み立てるのがコンストラクタである。

[`db/dbformat.cc` L245-L269](https://github.com/facebook/rocksdb/blob/v11.1.1/db/dbformat.cc#L245-L269)

```cpp
LookupKey::LookupKey(const Slice& _user_key, SequenceNumber s,
                     const Slice* ts) {
  size_t usize = _user_key.size();
  size_t ts_sz = (nullptr == ts) ? 0 : ts->size();
  size_t needed = usize + ts_sz + 13;  // A conservative estimate
  char* dst;
  if (needed <= sizeof(space_)) {
    dst = space_;
  } else {
    dst = new char[needed];
  }
  start_ = dst;
  // NOTE: We don't support users keys of more than 2GB :)
  dst = EncodeVarint32(dst, static_cast<uint32_t>(usize + ts_sz + 8));
  kstart_ = dst;
  memcpy(dst, _user_key.data(), usize);
  dst += usize;
  if (nullptr != ts) {
    memcpy(dst, ts->data(), ts_sz);
    dst += ts_sz;
  }
  EncodeFixed64(dst, PackSequenceAndType(s, kValueTypeForSeek));
  dst += 8;
  end_ = dst;
}
```

先頭に `EncodeVarint32`（[`util/coding.h` L100](https://github.com/facebook/rocksdb/blob/v11.1.1/util/coding.h#L100) で宣言される可変長エンコード）でユーザーキー長を書き、`kstart_` を控える。
続いてユーザーキーを `memcpy` し、末尾に `EncodeFixed64(dst, PackSequenceAndType(s, kValueTypeForSeek))` で8バイトのトレーラを書く。
トレーラの `type` に `kValueTypeForSeek` を使うのは、前節の探索キーの理屈と同じで、目的の `seq` 以下で最新のエントリへ確実にシークするためである。

メモリ確保にも工夫がある。
`LookupKey` は `char space_[200]` をメンバとして持ち（[`db/lookup_key.h` L57](https://github.com/facebook/rocksdb/blob/v11.1.1/db/lookup_key.h#L57)）、必要量が200バイト以内なら `new` せずこのインラインバッファを使う。
短いキーの探索でヒープ確保が起きないので、`Get` のたびに動的確保するコストを避けられる。
長いキーのときだけ `new` し、デストラクタが `start_ != space_` を見て解放する（[`db/lookup_key.h` L64-L66](https://github.com/facebook/rocksdb/blob/v11.1.1/db/lookup_key.h#L64-L66)）。

`Get` がこの `LookupKey` をどう使って memtable と SST を順に探すかは、読み取りの章で扱う（[第23章 Get](../part04-read-path/23-get.md)）。

## まとめ

- 内部キーは「ユーザーキー＋8バイトのトレーラ」で、トレーラは上位56ビット（7バイト）の `SequenceNumber` と下位8ビット（1バイト）の `ValueType` を `(seq << 8) | type` で詰めた1個の `uint64_t` である。
- `ValueType` の値はディスクフォーマットの一部として凍結されており（`DO NOT CHANGE THESE ENUM VALUES`）、最上位ビットは SST 側の符号化に予約されている。
- `InternalKey` は符号化済みの形を `std::string rep_` 1本で保持し、`ParsedInternalKey` はそれをほどいた3フィールドの形である。`ExtractUserKey` は末尾8バイトを除いた範囲をゼロコピーで切り出す。
- `InternalKeyComparator` はユーザーキー昇順、同一キー内はトレーラ整数の降順で並べる。降順により最新の `seq` が先頭へ来るので、走査の先頭1件で最新版が取れる。`seq` を上位に置いた配置が、二段の比較を整数1回の比較へ畳み込んでいる。
- 探索キーは `type` に最大値 `kValueTypeForSeek`（`kTypeValuePreferredSeqno`）を使い、目的の `seq` 以下で最新のエントリへ確実にシークする。
- `LookupKey` は1本のバッファに `klength | userkey | tag` を並べ、`memtable_key` / `internal_key` / `user_key` を同じバイト列の部分 `Slice` として返す。短いキーはインラインバッファで処理しヒープ確保を避ける。

## 関連する章

- [第6章 DB と Options](../part01-data-model/06-db-and-options.md)：内部キーを使う DB 本体とその設定。
- [第23章 Get](../part04-read-path/23-get.md)：`LookupKey` と内部キーの比較規則が読み取り経路でどう働くか。
