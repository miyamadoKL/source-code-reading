# 第34章 他のストレージエンジン

> **本章で読むソース**
>
> - [`storage/myisam/ha_myisam.cc`](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/myisam/ha_myisam.cc)
> - [`storage/heap/ha_heap.cc`](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/heap/ha_heap.cc)
> - [`storage/heap/ha_heap.h`](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/heap/ha_heap.h)
> - [`storage/csv/ha_tina.cc`](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/csv/ha_tina.cc)
> - [`storage/csv/ha_tina.h`](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/csv/ha_tina.h)
> - [`storage/federated/ha_federated.cc`](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.cc)
> - [`storage/federated/ha_federated.h`](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.h)

## この章の狙い

第11章で、SQL 層はストレージエンジンを `handler` という抽象クラス越しに呼ぶことを読んだ。
第12章以降は、その `handler` を実装する一エンジン InnoDB を中核として深く読んできた。
本章は最後に視点を戻し、InnoDB 以外のエンジンが同じ `handler` をどう実装しているかを軽く読む。

対象は **MyISAM**、**MEMORY**（コード上は HEAP）、**CSV**（コード上は TINA）、**FEDERATED** の4つである。
いずれも `handler` を継承し、第11章で読んだ `write_row` や `rnd_next` といった同じ仮想メソッドを埋める。
FEDERATED は前の3つと違い、ローカルにデータを一切持たず、`handler` の呼び出しをリモートの MySQL サーバへの SQL に翻訳して中継するプロキシ型のエンジンである。
ところが4つとも、InnoDB が持つトランザクション、行ロック、クラッシュリカバリのいずれも持たない。
本章では、各エンジンが `handlerton` のフラグと `table_flags()` で「自分は何をしないか」をどう宣言しているかを読み、InnoDB がなぜ既定になったかを最後に振り返る。

## 前提

第11章で、エンジン1種類につき1個の関数表 `handlerton` と、開いているテーブル1つにつき1個の `handler` という2層構造を読んだ。
プラグイン初期化 `ha_initialize_handlerton` が空の `handlerton` を確保し、各エンジンの `init` 関数がそこへ自分の関数を詰める流れも読んだ。
本章の3エンジンも、InnoDB の `innodb_init` と同じ位置にある `myisam_init`、`heap_init`、`tina_init_func` で自分の `handlerton` を埋める。

`handler` には、エンジンの能力を呼び出し側へ伝える `table_flags()` という仮想メソッドがある。
SQL 層はこのビットマスクを見て、たとえばトランザクションを開始してよいか、自動採番列を使えるかを判断する。
本章で繰り返し現れる `HA_NO_TRANSACTIONS` は、このマスクに立つ「このエンジンはトランザクションを実装しない」フラグである。

## MyISAM、非トランザクションのファイルベースエンジン

MyISAM は、InnoDB が既定になる前の MySQL で長く既定だったエンジンである。
テーブル定義を別にすれば、データを `.MYD` ファイルに、インデックスを `.MYI` ファイルに分けて格納する。
この2つの拡張子は、`handlerton` の `file_extensions` に登録される配列にそのまま現れる。

[`storage/myisam/ha_myisam.cc` L647-647](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/myisam/ha_myisam.cc#L647-L647)

```cpp
static const char *ha_myisam_exts[] = {".MYI", ".MYD", NullS};
```

データとインデックスを別ファイルに分ける構成は、1つのテーブルスペース内にクラスタ化インデックスとして行を畳み込む InnoDB（第13章、第14章）と対照的である。
MyISAM のデータファイル `.MYD` は行を順に並べた素朴な格納で、インデックス `.MYI` は B-tree のキーから `.MYD` 内の行位置を指す。

MyISAM がトランザクションを持たないことは、`handler` の構築時に `table_flags()` の元になる `int_table_flags` へ立てるビットで宣言される。
コンストラクタのフラグ列に `HA_NO_TRANSACTIONS` が並んでいる。

[`storage/myisam/ha_myisam.cc` L626-638](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/myisam/ha_myisam.cc#L626-L638)

```cpp
ha_myisam::ha_myisam(handlerton *hton, TABLE_SHARE *table_arg)
    : handler(hton, table_arg),
      file(nullptr),
      int_table_flags(
          HA_NULL_IN_KEY | HA_CAN_FULLTEXT | HA_CAN_SQL_HANDLER |
          HA_BINLOG_ROW_CAPABLE | HA_BINLOG_STMT_CAPABLE | HA_DUPLICATE_POS |
          HA_CAN_INDEX_BLOBS | HA_AUTO_PART_KEY | HA_FILE_BASED |
          HA_CAN_GEOMETRY | HA_NO_TRANSACTIONS | HA_CAN_BIT_FIELD |
          HA_CAN_RTREEKEYS | HA_COUNT_ROWS_INSTANT | HA_STATS_RECORDS_IS_EXACT |
          HA_CAN_REPAIR | HA_GENERATED_COLUMNS | HA_ATTACHABLE_TRX_COMPATIBLE |
          HA_SUPPORTS_DEFAULT_EXPRESSION),
      can_enable_indexes(true),
      ds_mrr(this) {}
```

`HA_NO_TRANSACTIONS` が立つので、SQL 層は MyISAM テーブルにコミットやロールバックを期待しない。
1文の `UPDATE` が途中でエラーになっても、それまでに書いた行は元に戻らない。
並行制御も行単位ではなくテーブル単位である。
ロックの登録メソッド `store_lock` は、テーブル1個分のロック構造 `file->lock` を1つだけ返すだけである。

[`storage/myisam/ha_myisam.cc` L1729-1735](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/myisam/ha_myisam.cc#L1729-L1735)

```cpp
THR_LOCK_DATA **ha_myisam::store_lock(THD *, THR_LOCK_DATA **to,
                                      enum thr_lock_type lock_type) {
  if (lock_type != TL_IGNORE && file->lock.type == TL_UNLOCK)
    file->lock.type = lock_type;
  *to++ = &file->lock;
  return to;
}
```

InnoDB がレコードロックやギャップロック（第26章）でテーブル内の特定の行だけをロックするのに対し、MyISAM が差し出すロックの粒度はテーブル全体である。
書き込み中は他のセッションがそのテーブルへ書けない。

行の挿入 `write_row` を見ると、自動採番列の更新を済ませたあと、MyISAM 内部の `mi_write` を呼ぶだけである。

[`storage/myisam/ha_myisam.cc` L819-831](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/myisam/ha_myisam.cc#L819-L831)

```cpp
int ha_myisam::write_row(uchar *buf) {
  ha_statistic_increment(&System_status_var::ha_write_count);

  /*
    If we have an auto_increment column and we are writing a changed row
    or a new row, then update the auto_increment value in the record.
  */
  if (table && table->next_number_field && buf == table->record[0]) {
    int error;
    if ((error = update_auto_increment())) return error;
  }
  return mi_write(file, buf);
}
```

ここには、InnoDB の `write_row`（第11章）が経由した redo ログへの記録やミニトランザクション（第16章）に当たる処理がない。
`mi_write` が `.MYD` と `.MYI` へ書くだけで、変更前の状態を残す undo ログ（第25章）も、書き込みをアトミックにまとめる仕組みもない。
このため、書き込みの途中でサーバが落ちると、`.MYI` のインデックスが `.MYD` の実データと食い違ったまま残りうる。
MyISAM のクラッシュ耐性が弱いのは、変更を1つの原子的な単位にまとめて永続化する機構を持たず、壊れたインデックスを起動時に自動で巻き戻せないからである。
壊れたテーブルは、`HA_CAN_REPAIR` フラグが示すとおり `REPAIR TABLE` で `.MYI` を作り直して直す、事後修復の設計になっている。

最後に、MyISAM をプラグインとして登録する `myisam_init` が、`handlerton` の各メンバを埋める。

[`storage/myisam/ha_myisam.cc` L1987-1997](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/myisam/ha_myisam.cc#L1987-L1997)

```cpp
  myisam_hton = (handlerton *)p;
  myisam_hton->state = SHOW_OPTION_YES;
  myisam_hton->db_type = DB_TYPE_MYISAM;
  myisam_hton->create = myisam_create_handler;
  myisam_hton->panic = myisam_panic;
  myisam_hton->close_connection = myisam_close_connection;
  myisam_hton->flags =
      HTON_CAN_RECREATE | HTON_SUPPORT_LOG_TABLES | HTON_SUPPORTS_PACKED_KEYS;
  myisam_hton->is_supported_system_table = myisam_is_supported_system_table;
  myisam_hton->file_extensions = ha_myisam_exts;
  myisam_hton->rm_tmp_tables = default_rm_tmp_tables;
```

InnoDB の `innodb_init`（第11章）が `commit`、`rollback`、`prepare`、`recover` などトランザクションと XA リカバリの関数ポインタを次々に埋めていたのと比べると、ここには `commit` も `recover` もない。
埋めていない関数ポインタは、`ha_initialize_handlerton` が確保したゼロ初期化のまま残る。
SQL 層は `handlerton` のメンバが空かどうかでエンジンの能力を判断するので、関数を登録しないこと自体が「このエンジンはコミットもリカバリもしない」という宣言になる。

## MEMORY、メモリ常駐で再起動に耐えない

MEMORY エンジンは、テーブルの全行をメモリ上に置く。
ソースのクラス名やファイル名は HEAP で、`handlerton` の `db_type` も `DB_TYPE_HEAP` である。
初期化 `heap_init` を見ると、`handlerton` に埋めるメンバが MyISAM よりさらに少ない。

[`storage/heap/ha_heap.cc` L60-67](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/heap/ha_heap.cc#L60-L67)

```cpp
  heap_hton = (handlerton *)p;
  heap_hton->state = SHOW_OPTION_YES;
  heap_hton->db_type = DB_TYPE_HEAP;
  heap_hton->create = heap_create_handler;
  heap_hton->panic = heap_panic;
  heap_hton->flags = HTON_CAN_RECREATE;

  return 0;
```

`file_extensions` の登録がないことに注意する。
MEMORY のテーブルはディスク上のデータファイルを持たず、行はプロセスのメモリ内にしか存在しない。
サーバを再起動すると、テーブル定義は残っても中身は空になる。
永続化の対象になるファイルがないので、クラッシュリカバリという問題自体が生じない。
この性質から、MEMORY は中間結果の保持や参照頻度の高い小さな表など、消えても再構築できる一時的な用途に向く。

MEMORY もトランザクションを持たない。
`table_flags()` のビットに `HA_NO_TRANSACTIONS` が立っている。
あわせて、固定長行を前提とする `HA_FAST_KEY_READ` や、可変長の大きな値を扱わない `HA_NO_BLOBS` も立っている。

[`storage/heap/ha_heap.h` L58-63](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/heap/ha_heap.h#L58-L63)

```cpp
  ulonglong table_flags() const override {
    return (HA_FAST_KEY_READ | HA_NO_BLOBS | HA_NULL_IN_KEY |
            HA_BINLOG_ROW_CAPABLE | HA_BINLOG_STMT_CAPABLE |
            HA_NO_TRANSACTIONS | HA_COUNT_ROWS_INSTANT |
            HA_STATS_RECORDS_IS_EXACT);
  }
```

このフラグの並びが、MEMORY の設計の要点をそのまま表している。
行は固定長で、既定のインデックスはハッシュである。
行を固定長にすると確保すべきバイト数が一定なので、確保と解放が単純な配列のように扱え、可変長の詰め物や断片化の管理が要らない。
既定のインデックスがハッシュであることは、`get_default_index_algorithm` が `HA_KEY_ALG_HASH` を返すことに現れる。

[`storage/heap/ha_heap.h` L48-57](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/heap/ha_heap.h#L48-L57)

```cpp
  enum ha_key_alg get_default_index_algorithm() const override {
    return HA_KEY_ALG_HASH;
  }
  bool is_index_algorithm_supported(enum ha_key_alg key_alg) const override {
    return key_alg == HA_KEY_ALG_BTREE || key_alg == HA_KEY_ALG_HASH;
  }
  /* Rows also use a fixed-size format */
  enum row_type get_real_row_type(const HA_CREATE_INFO *) const override {
    return ROW_TYPE_FIXED;
  }
```

ハッシュインデックスは等価検索を平均 O(1) で引ける代わりに、キーの順序を保たない。
`index_flags` がハッシュの場合に `HA_ONLY_WHOLE_INDEX` を返し、範囲走査用の `HA_READ_RANGE` を立てないのは、ハッシュでは範囲検索や順序走査ができないからである。

[`storage/heap/ha_heap.h` L64-68](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/heap/ha_heap.h#L64-L68)

```cpp
  ulong index_flags(uint inx, uint, bool) const override {
    return ((table_share->key_info[inx].algorithm == HA_KEY_ALG_BTREE)
                ? HA_READ_NEXT | HA_READ_PREV | HA_READ_ORDER | HA_READ_RANGE
                : HA_ONLY_WHOLE_INDEX | HA_KEY_SCAN_NOT_ROR);
  }
```

行を挿入する `write_row` も、メモリ上の構造へ書く `heap_write` を呼ぶだけである。

[`storage/heap/ha_heap.cc` L205-222](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/heap/ha_heap.cc#L205-L222)

```cpp
int ha_heap::write_row(uchar *buf) {
  int res;
  ha_statistic_increment(&System_status_var::ha_write_count);
  if (table->next_number_field && buf == table->record[0]) {
    if ((res = update_auto_increment())) return res;
  }
  res = heap_write(file, buf);
  if (!res &&
      (++records_changed * HEAP_STATS_UPDATE_THRESHOLD > file->s->records)) {
    /*
       We can perform this safely since only one writer at the time is
       allowed on the table.
    */
    file->s->key_stat_version++;
  }

  return res;
}
```

コメントの「only one writer at the time is allowed on the table」が、MEMORY も書き込みをテーブル単位で直列化していることを示す。
固定長行とハッシュインデックスでメモリ常駐を単純かつ高速にする代わりに、永続性を捨てる。
これが MEMORY のトレードオフであり、用途を一時データに限る理由でもある。

## CSV、プレーンテキストへの追記

CSV エンジンは、テーブルの行をそのままカンマ区切りのテキストファイルへ書く。
ソース上の名前は TINA で、データを `.CSV`、メタ情報を `.CSM` に分けて持つ。
初期化 `tina_init_func` の `handlerton` は MyISAM と似た構成だが、`HTON_NO_PARTITION` が立ち、パーティションを許さない。

[`storage/csv/ha_tina.cc` L182-189](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/csv/ha_tina.cc#L182-L189)

```cpp
  tina_hton->state = SHOW_OPTION_YES;
  tina_hton->db_type = DB_TYPE_CSV_DB;
  tina_hton->create = tina_create_handler;
  tina_hton->flags =
      (HTON_CAN_RECREATE | HTON_SUPPORT_LOG_TABLES | HTON_NO_PARTITION);
  tina_hton->file_extensions = ha_tina_exts;
  tina_hton->rm_tmp_tables = default_rm_tmp_tables;
  tina_hton->is_supported_system_table = tina_is_supported_system_table;
```

CSV の `table_flags()` も `HA_NO_TRANSACTIONS` を立てる。
さらに `HA_NO_AUTO_INCREMENT` が立ち、自動採番列も持たない。

[`storage/csv/ha_tina.h` L114-117](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/csv/ha_tina.h#L114-L117)

```cpp
  ulonglong table_flags() const override {
    return (HA_NO_TRANSACTIONS | HA_NO_AUTO_INCREMENT | HA_BINLOG_ROW_CAPABLE |
            HA_BINLOG_STMT_CAPABLE | HA_CAN_REPAIR);
  }
```

CSV はインデックスを一切持たない。
`index_flags` が常に0を返し、コメントが「We will never have indexes」と明言する。
インデックスがないので、行を探すには `.CSV` を先頭から走査するしかない。

行の挿入 `write_row` は、行をテキストへ整形してファイル末尾へ書き足す。
`encode_quote` が `record[0]` の各カラムをカンマ区切りのテキスト1行に組み立て、その文字列を `.CSV` へ追記する。

[`storage/csv/ha_tina.cc` L937-968](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/csv/ha_tina.cc#L937-L968)

```cpp
int ha_tina::write_row(uchar *buf) {
  int size;
  DBUG_TRACE;

  if (share->crashed) return HA_ERR_CRASHED_ON_USAGE;

  ha_statistic_increment(&System_status_var::ha_write_count);

  size = encode_quote(buf);

  if (!share->tina_write_opened)
    if (init_tina_writer()) return -1;

  /* use pwrite, as concurrent reader could have changed the position */
  if (mysql_file_write(share->tina_write_filedes,
                       pointer_cast<const uchar *>(buffer.ptr()), size,
                       MYF(MY_WME | MY_NABP)))
    return -1;

  /* update local copy of the max position to see our own changes */
  local_saved_data_file_length += size;

  /* update shared info */
  mysql_mutex_lock(&share->mutex);
  share->rows_recorded++;
  /* update status for the log tables */
  if (share->is_log_table) update_status();
  mysql_mutex_unlock(&share->mutex);

  stats.records++;
  return 0;
}
```

格納がプレーンテキストなので、`.CSV` ファイルは MySQL の外からもテキストエディタで読める。
データの取り込みや書き出しの中継には向くが、インデックスもトランザクションもないため、検索は毎回の全走査になり、書き込みの原子性も保証されない。

## FEDERATED、リモートのテーブルをプロキシする

FEDERATED は、ここまでの3エンジンと根本的に違う。
ローカルにデータファイルを一切持たず、行を保持するのは外部（foreign）の MySQL データベースである。
ソース冒頭の概要コメントが、この性質と動作の流れをそのまま説明している。

[`storage/federated/ha_federated.cc` L42-49](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.cc#L42-L49)

```cpp
  With MySQL Federated storage engine, there will be no local files
  for each table's data (such as .MYD). A foreign database will store
  the data that would normally be in this file. This will necessitate
  the use of MySQL client API to read, delete, update, insert this
  data. The data will have to be retrieve via an SQL call "SELECT *
  FROM users". Then, to read this data, it will have to be retrieved
  via mysql_fetch_row one row at a time, then converted from the
  column in this select into the format that the handler expects.
```

コメントが述べるとおり、データの読み書きは MySQL の client API を介してリモートへ SQL を送り、結果を1行ずつ受け取る。
FEDERATED の `handler` は、ローカルに格納する代わりに、各仮想メソッドをこのリモートへの SQL に翻訳する役割を負う。

`CREATE TABLE` が作るのは、`.frm` 相当のテーブル定義だけである。
テーブルの実体に相当するのは、接続先を指す接続文字列にすぎない。
接続文字列は `connection=scheme://user:password@host:port/database/tablename` の URL 形式か、`mysql.servers` に登録したサーバ名を `connection="server_name"` のように参照する形式を取る。
FEDERATED はこの接続情報を覚えるだけで、行そのものはローカルに置かない。

行の挿入を見ると、`write_row` がローカルへ書く代わりに `INSERT` 文を組み立ててリモートへ送る。
文の組み立ては `append_stmt_insert` が担い、`REPLACE INTO` や `INSERT IGNORE INTO`、`INSERT INTO` の語をクエリ文字列の先頭へ書き出す。

[`storage/federated/ha_federated.cc` L1651-1658](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.cc#L1651-L1658)

```cpp
  insert_string.length(0);

  if (replace_duplicates)
    insert_string.append(STRING_WITH_LEN("REPLACE INTO "));
  else if (ignore_duplicates && !insert_dup_update)
    insert_string.append(STRING_WITH_LEN("INSERT IGNORE INTO "));
  else
    insert_string.append(STRING_WITH_LEN("INSERT INTO "));
```

組み立てた `INSERT` 文は、`write_row` の末尾で `real_query` に渡してリモートへ送る。

[`storage/federated/ha_federated.cc` L1819-1821](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.cc#L1819-L1821)

```cpp
  } else {
    error = real_query(values_string.ptr(), values_string.length());
  }
```

`real_query` は MySQL の client API の `mysql_real_query` を呼ぶラッパーであり、ここでリモートのサーバへ SQL が中継される。
読み出しも同じ構図である。
全表走査の `rnd_init` は、あらかじめ用意した `SELECT * FROM` のクエリを `real_query` でリモートへ送り、結果セットを受け取って保持する。

[`storage/federated/ha_federated.cc` L2436-2441](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.cc#L2436-L2441)

```cpp
  if (scan) {
    if (real_query(share->select_query, strlen(share->select_query)) ||
        !(stored_result = store_result(mysql)))
      return stash_remote_error();
  }
  return 0;
```

1行ずつの読み出しは、`read_next` が結果セットから `mysql_fetch_row` で1行取り出し、内部の行フォーマットへ変換する。

[`storage/federated/ha_federated.cc` L2516-2517](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.cc#L2516-L2517)

```cpp
  /* Fetch a row, insert it back in a row format. */
  if (!(row = mysql_fetch_row(result))) return HA_ERR_END_OF_FILE;
```

エンジンの能力の宣言も、リモート任せという性質を反映している。
プラグイン初期化 `federated_db_init` は、`handlerton` の `flags` に `HTON_ALTER_NOT_SUPPORTED` と `HTON_NO_PARTITION` を立て、`ALTER TABLE` とパーティションを許さない。

[`storage/federated/ha_federated.cc` L501-507](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.cc#L501-L507)

```cpp
  handlerton *federated_hton = (handlerton *)p;
  federated_hton->state = SHOW_OPTION_YES;
  federated_hton->db_type = DB_TYPE_FEDERATED_DB;
  federated_hton->commit = federated_commit;
  federated_hton->rollback = federated_rollback;
  federated_hton->create = federated_create_handler;
  federated_hton->flags = HTON_ALTER_NOT_SUPPORTED | HTON_NO_PARTITION;
```

`table_flags()` も、他の3エンジンと同じく `HA_NO_TRANSACTIONS` を含む。

[`storage/federated/ha_federated.h` L148-157](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/storage/federated/ha_federated.h#L148-L157)

```cpp
  ulonglong table_flags() const override {
    /* fix server to be able to get remote server table flags */
    return (HA_PRIMARY_KEY_IN_READ_INDEX |
            HA_PRIMARY_KEY_REQUIRED_FOR_POSITION | HA_FILE_BASED |
            HA_AUTO_PART_KEY | HA_CAN_INDEX_BLOBS | HA_BINLOG_ROW_CAPABLE |
            HA_BINLOG_STMT_CAPABLE | HA_NO_PREFIX_CHAR_KEYS |
            HA_PRIMARY_KEY_REQUIRED_FOR_DELETE |
            HA_NO_TRANSACTIONS /* until fixed by WL#2952 */ |
            HA_PARTIAL_COLUMN_READ | HA_NULL_IN_KEY | HA_CAN_REPAIR);
  }
```

`HA_NO_TRANSACTIONS` が立つのは、FEDERATED がローカルにトランザクションを持たず、コミットやロールバックの可否をリモートのサーバに委ねるからである。
コメントの「until fixed by WL#2952」が示すとおり、`federated_db_init` も一度は `commit` と `rollback` の関数ポインタを埋めかけたあと、未完のため `nullptr` へ戻している。

他の3エンジンが、ファイル、メモリ、プレーンテキストのいずれかの形でローカルに行を格納するのに対し、FEDERATED は格納そのものを完全に他サーバへ委ねる。
ローカルに残るのは接続文字列と空の `handler` だけで、データの実体は1つも手元にない。
この点が、FEDERATED を他の3エンジンから際立たせている。

## InnoDB との対比、共通の口と異なる中身

ここまでの3エンジンは、第11章で読んだ `handler` の同じ仮想メソッド（`write_row`、`rnd_next`、`store_lock` など）を実装する。
SQL 層から見れば、どのエンジンのテーブルも同じ呼び出しで読み書きできる。
違いは、各エンジンが `handlerton` のフラグと `table_flags()` で宣言する能力にある。
この共通の口と異なる中身の関係を図にすると、次のようになる。

```mermaid
flowchart TD
    sql["SQL 層（エグゼキュータ）"]
    api["handler 抽象（仮想メソッド: write_row / rnd_next / store_lock）"]
    sql -->|"基底クラスポインタ越しに呼ぶ"| api

    api -.->|"仮想関数表で分岐"| innodb
    api -.-> myisam
    api -.-> heap
    api -.-> csv
    api -.-> federated

    innodb["InnoDB: トランザクション / 行ロック / クラッシュリカバリ あり"]
    myisam["MyISAM: 非トランザクション / テーブルロック / .MYD と .MYI"]
    heap["MEMORY（HEAP）: メモリ常駐 / 固定長行 / ハッシュ索引 / 再起動で消える"]
    csv["CSV（TINA）: プレーンテキスト / 索引なし / 全走査"]
    federated["FEDERATED: ローカル格納なし / リモートへ SQL 中継"]
```

破線が、第11章で読んだ仮想関数表による実行時分岐である。
SQL 層は実線の経路だけを知り、破線の先がどのエンジンかを意識しない。
MyISAM、MEMORY、CSV、FEDERATED はどれも `HA_NO_TRANSACTIONS` を立て、コミットやロールバックの関数を `handlerton` に登録しない点で共通する。
一方で InnoDB だけが、`commit`、`rollback`、`recover` を埋め、行ロックと redo／undo ログによる耐久性を持つ。

## まとめ

MyISAM、MEMORY、CSV、FEDERATED は、いずれも `handler` を継承して同じ仮想メソッドを実装するストレージエンジンである。
SQL 層は基底クラスのポインタ越しに同じ呼び出しでこれらを使い、実体の違いは仮想関数表が吸収する。
4つとも `table_flags()` に `HA_NO_TRANSACTIONS` を立て、トランザクション、行ロック、クラッシュリカバリのいずれも持たない点で、InnoDB と対照的である。

各エンジンは、能力を `handlerton` のフラグと埋める関数ポインタで宣言する。
MyISAM は `.MYD` と `.MYI` を分けたファイルベースで、テーブル単位のロックと事後修復の `REPAIR TABLE` を持つ。
MEMORY は固定長行とハッシュインデックスで行をメモリに置き、確保と検索を単純高速にする代わりに、再起動で中身を失う永続性とのトレードオフを取る。
CSV は行をプレーンテキストへ追記し、外部ツールと交換しやすい代わりに、インデックスを持たず検索は全走査になる。
FEDERATED は行をローカルに格納せず、`handler` の呼び出しを `INSERT` や `SELECT * FROM` の SQL に翻訳してリモートの MySQL サーバへ中継するプロキシであり、格納そのものを他サーバへ委ねる。

本書はサーバ層をたどったあと、InnoDB の実装を中心に深掘りしてきた。
最後にその選択の理由を一段落で振り返る。
InnoDB が既定のエンジンになったのは、耐久性と並行性を機構として備えるからである。
変更を redo ログとミニトランザクションで原子的に永続化し（第16章、第27章）、クラッシュ後はその redo を再適用して一貫した状態へ戻す（第29章）。
読み取りは MVCC とリードビューでロックを取らずに過去のバージョンを見せ（第24章）、書き込みは行単位のレコードロックとネクストキーロックで競合を最小化する（第26章）。
本章で読んだ3エンジンが捨てているこれらの機構こそ、多くのセッションが同じテーブルを安全に読み書きし、障害後もデータを失わないという、汎用データベースに求められる性質を支えている。

## 関連する章

- [第11章 ハンドラ API とストレージエンジンプラグイン](../part01-sql-layer/11-handler-api.md)：本章の3エンジンが実装する `handler` と `handlerton` の2層構造を読む。
- [第26章 ロック](../part04-transaction-concurrency/26-locking.md)：MyISAM のテーブルロックと対比される InnoDB の行単位ロックを読む。
- [第29章 チェックポイントとクラッシュリカバリ](../part05-log-recovery/29-checkpoint-and-recovery.md)：本章の3エンジンが持たないクラッシュリカバリを InnoDB がどう実装するかを読む。
