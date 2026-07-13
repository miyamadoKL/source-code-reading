# 第15章 Mem 値の表現と型アフィニティ

> **本章で読むソース**
>
> - [src/vdbeInt.h](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbeInt.h)
> - [src/vdbe.h](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbe.h)
> - [src/vdbemem.c](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbemem.c)
> - [src/vdbe.c](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbe.c)
> - [src/utf.c](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/utf.c)

## この章の狙い

第13章では `aMem[]` がレジスタとして動くことを見た。
本章ではその要素である **Mem** の内部表現を読む。
1つの SQL 値が整数、実数、文字列、BLOB、NULL の複数表現を同時に持てる設計と、所有権フラグ、列 **アフィニティ** による型変換、比較時の変換規則を追う。

## 前提

公開 API の `sqlite3_value` は VDBE 内部では `Mem` として扱われる。
`vdbe.h` は `typedef struct sqlite3_value Mem` と宣言し、実体の定義は `vdbeInt.h` の `struct sqlite3_value` である。

[src/vdbe.h L33-L33](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbe.h#L33-L33)

```c
typedef struct sqlite3_value Mem;
```

[src/vdbeInt.h L232-L256](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbeInt.h#L232-L256)

```c
struct sqlite3_value {
  union MemValue {
    double r;           /* Real value used when MEM_Real is set in flags */
    i64 i;              /* Integer value used when MEM_Int is set in flags */
    int nZero;          /* Extra zero bytes when MEM_Zero and MEM_Blob set */
    const char *zPType; /* Pointer type when MEM_Term|MEM_Subtype|MEM_Null */
    FuncDef *pDef;      /* Used only when flags==MEM_Agg */
  } u;
  char *z;            /* String or BLOB value */
  int n;              /* Number of characters in string value, excluding '\0' */
  u16 flags;          /* Some combination of MEM_Null, MEM_Str, MEM_Dyn, etc. */
  u8  enc;            /* SQLITE_UTF8, SQLITE_UTF16BE, SQLITE_UTF16LE */
  u8  eSubtype;       /* Subtype for this value */
  /* ShallowCopy only needs to copy the information above */
  sqlite3 *db;        /* The associated database connection */
  int szMalloc;       /* Size of the zMalloc allocation */
  u32 uTemp;          /* Transient storage for serial_type in OP_MakeRecord */
  char *zMalloc;      /* Space to hold MEM_Str or MEM_Blob if szMalloc>0 */
  void (*xDel)(void*);/* Destructor for Mem.z - only valid if MEM_Dyn */
#ifdef SQLITE_DEBUG
  Mem *pScopyFrom;    /* This Mem is a shallow copy of pScopyFrom */
  u16 mScopyFlags;    /* flags value immediately after the shallow copy */
  u8  bScopy;         /* The pScopyFrom of some other Mem *might* point here */
#endif
};
```

`flags` の下位6ビット（`MEM_AffMask`）が型を表し、上位ビットが所有権や付加属性を表す。

[src/vdbeInt.h L309-L340](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbeInt.h#L309-L340)

```c
#define MEM_Undefined 0x0000   /* Value is undefined */
#define MEM_Null      0x0001   /* Value is NULL (or a pointer) */
#define MEM_Str       0x0002   /* Value is a string */
#define MEM_Int       0x0004   /* Value is an integer */
#define MEM_Real      0x0008   /* Value is a real number */
#define MEM_Blob      0x0010   /* Value is a BLOB */
#define MEM_IntReal   0x0020   /* MEM_Int that stringifies like MEM_Real */
#define MEM_AffMask   0x003f   /* Mask of affinity bits */

#define MEM_FromBind  0x0040   /* Value originates from sqlite3_bind() */
#define MEM_Cleared   0x0100   /* NULL set by OP_Null, not from data */
#define MEM_Term      0x0200   /* String in Mem.z is zero terminated */
#define MEM_Zero      0x0400   /* Mem.i contains count of 0s appended to blob */
#define MEM_Subtype   0x0800   /* Mem.eSubtype is valid */
#define MEM_TypeMask  0x0dbf   /* Mask of type bits */

#define MEM_Dyn       0x1000   /* Need to call Mem.xDel() on Mem.z */
#define MEM_Static    0x2000   /* Mem.z points to a static string */
#define MEM_Ephem     0x4000   /* Mem.z points to an ephemeral string */
#define MEM_Agg       0x8000   /* Mem.z points to an agg function context */

#define VdbeMemDynamic(X)  \
  (((X)->flags&(MEM_Agg|MEM_Dyn))!=0)
```

## 所有権とメモリ解放

`MEM_Static` は呼び出し側が寿命を保証する文字列を指す。
`MEM_Ephem` はページやレコードバッファ上の短命データを指し、書き換え前に `sqlite3VdbeMemMakeWriteable` で `zMalloc` へコピーする。
`MEM_Dyn` は `xDel` による解放が必要である。

[src/vdbemem.c L390-L407](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbemem.c#L390-L407)

```c
int sqlite3VdbeMemMakeWriteable(Mem *pMem){
  assert( pMem!=0 );
  assert( pMem->db==0 || sqlite3_mutex_held(pMem->db->mutex) );
  assert( !sqlite3VdbeMemIsRowSet(pMem) );
  if( (pMem->flags & (MEM_Str|MEM_Blob))!=0 ){
    if( ExpandBlob(pMem) ) return SQLITE_NOMEM;
    if( pMem->szMalloc==0 || pMem->z!=pMem->zMalloc ){
      int rc = vdbeMemAddTerminator(pMem);
      if( rc ) return rc;
    }
  }
  pMem->flags &= ~MEM_Ephem;
#ifdef SQLITE_DEBUG
  pMem->pScopyFrom = 0;
#endif

  return SQLITE_OK;
}
```

`sqlite3VdbeMemRelease` は `MEM_Dyn`/`MEM_Agg` の外部バッファと `zMalloc` を解放する。
`MEM_Dyn`/`MEM_Agg` があるときは `vdbeMemClearExternAndSetNull` が `flags` を `MEM_Null` にする。
`zMalloc` だけを持つ場合は `vdbeMemClear` が `zMalloc` を解放して `z` を 0 にするだけで、`flags` は変更しない。

[src/vdbemem.c L566-L615](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbemem.c#L566-L615)

```c
static SQLITE_NOINLINE void vdbeMemClearExternAndSetNull(Mem *p){
  assert( p->db==0 || sqlite3_mutex_held(p->db->mutex) );
  assert( VdbeMemDynamic(p) );
  if( p->flags&MEM_Agg ){
    sqlite3VdbeMemFinalize(p, p->u.pDef);
    assert( (p->flags & MEM_Agg)==0 );
    testcase( p->flags & MEM_Dyn );
  }
  if( p->flags&MEM_Dyn ){
    assert( p->xDel!=SQLITE_DYNAMIC && p->xDel!=0 );
    p->xDel((void *)p->z);
  }
  p->flags = MEM_Null;
}

static SQLITE_NOINLINE void vdbeMemClear(Mem *p){
  if( VdbeMemDynamic(p) ){
    vdbeMemClearExternAndSetNull(p);
  }
  if( p->szMalloc ){
    sqlite3DbFreeNN(p->db, p->zMalloc);
    p->szMalloc = 0;
  }
  p->z = 0;
}

void sqlite3VdbeMemRelease(Mem *p){
  assert( sqlite3VdbeCheckMemInvariants(p) );
  if( VdbeMemDynamic(p) || p->szMalloc ){
    vdbeMemClear(p);
  }
}
```

## 表現の追加と文字列化

整数や実数から文字列表現を作るときは `sqlite3VdbeMemStringify` が `zMalloc` を確保し `MEM_Str` を立てる。
BLOB には適用されず、NULL にも呼ばれない。

[src/vdbemem.c L471-L479](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbemem.c#L471-L479)

```c
int sqlite3VdbeMemStringify(Mem *pMem, u8 enc, u8 bForce){
  const int nByte = 32;

  assert( pMem!=0 );
  assert( pMem->db==0 || sqlite3_mutex_held(pMem->db->mutex) );
  assert( !(pMem->flags&MEM_Zero) );
  assert( !(pMem->flags&(MEM_Str|MEM_Blob)) );
  assert( pMem->flags&(MEM_Int|MEM_Real|MEM_IntReal) );
  assert( !sqlite3VdbeMemIsRowSet(pMem) );
  assert( EIGHT_BYTE_ALIGNMENT(pMem) );
```

## applyAffinity と OP_Affinity

列アフィニティは `SQLITE_AFF_INTEGER`、`SQLITE_AFF_REAL`、`SQLITE_AFF_TEXT` などの1文字コードで表される。
`applyAffinity` は数値アフィニティで文字列を `applyNumericAffinity` へ回し、TEXT アフィニティで数値を `sqlite3VdbeMemStringify` してから整数と実数のフラグを落とす。

[src/vdbe.c L397-L428](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbe.c#L397-L428)

```c
static void applyAffinity(
  Mem *pRec,          /* The value to apply affinity to */
  char affinity,      /* The affinity to be applied */
  u8 enc              /* Use this text encoding */
){
  if( affinity>=SQLITE_AFF_NUMERIC ){
    assert( affinity==SQLITE_AFF_INTEGER || affinity==SQLITE_AFF_REAL
             || affinity==SQLITE_AFF_NUMERIC || affinity==SQLITE_AFF_FLEXNUM );
    if( (pRec->flags & MEM_Int)==0 ){ /*OPTIMIZATION-IF-FALSE*/
      if( (pRec->flags & (MEM_Real|MEM_IntReal))==0 ){
        if( pRec->flags & MEM_Str ) applyNumericAffinity(pRec,1);
      }else if( affinity<=SQLITE_AFF_REAL ){
        sqlite3VdbeIntegerAffinity(pRec);
      }
    }
  }else if( affinity==SQLITE_AFF_TEXT ){
    if( 0==(pRec->flags&MEM_Str) ){ /*OPTIMIZATION-IF-FALSE*/
      if( (pRec->flags&(MEM_Real|MEM_Int|MEM_IntReal)) ){
        testcase( pRec->flags & MEM_Int );
        testcase( pRec->flags & MEM_Real );
        testcase( pRec->flags & MEM_IntReal );
        sqlite3VdbeMemStringify(pRec, enc, 1);
      }
    }
    pRec->flags &= ~(MEM_Real|MEM_Int|MEM_IntReal);
  }
}
```

**OP_Affinity** は `p4.z` の文字列をレジスタ列 `p1` から `p2` 個に順に適用する。
REAL アフィニティでは6バイトに収まる整数を `MEM_IntReal` に格納し、高精度を保ちつつ実数として扱う経路がある。

[src/vdbe.c L3404-L3439](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbe.c#L3404-L3439)

```c
case OP_Affinity: {
  const char *zAffinity;   /* The affinity to be applied */

  zAffinity = pOp->p4.z;
  assert( zAffinity!=0 );
  assert( pOp->p2>0 );
  assert( zAffinity[pOp->p2]==0 );
  pIn1 = &aMem[pOp->p1];
  while( 1 /*exit-by-break*/ ){
    assert( pIn1 <= &p->aMem[(p->nMem+1 - p->nCursor)] );
    assert( zAffinity[0]==SQLITE_AFF_NONE || memIsValid(pIn1) );
    applyAffinity(pIn1, zAffinity[0], encoding);
    if( zAffinity[0]==SQLITE_AFF_REAL && (pIn1->flags & MEM_Int)!=0 ){
      if( pIn1->u.i<=140737488355327LL && pIn1->u.i>=-140737488355328LL ){
        pIn1->flags |= MEM_IntReal;
        pIn1->flags &= ~MEM_Int;
      }else{
        pIn1->u.r = (double)pIn1->u.i;
        pIn1->flags |= MEM_Real;
        pIn1->flags &= ~(MEM_Int|MEM_Str);
      }
    }
    REGISTER_TRACE((int)(pIn1-aMem), pIn1);
    zAffinity++;
    if( zAffinity[0]==0 ) break;
    pIn1++;
  }
  break;
}
```

## 比較時の型変換

`OP_Eq` などの比較 opcode は、まず `pOp->p5` のアフィニティに従いオペランドを変換してから `sqlite3MemCompare` を呼ぶ。
比較後は `flags` を元に戻し、レジスタの恒久表現を壊さない。

[src/vdbe.c L2346-L2409](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbe.c#L2346-L2409)

```c
    affinity = pOp->p5 & SQLITE_AFF_MASK;
    if( affinity>=SQLITE_AFF_NUMERIC ){
      if( (flags1 | flags3)&MEM_Str ){
        if( (flags1 & (MEM_Int|MEM_IntReal|MEM_Real|MEM_Str))==MEM_Str ){
          applyNumericAffinity(pIn1,0);
          assert( flags3==pIn3->flags || CORRUPT_DB );
          flags3 = pIn3->flags;
        }
        if( (flags3 & (MEM_Int|MEM_IntReal|MEM_Real|MEM_Str))==MEM_Str ){
          applyNumericAffinity(pIn3,0);
        }
      }
    }else if( affinity==SQLITE_AFF_TEXT && ((flags1 | flags3) & MEM_Str)!=0 ){
      // ... (中略) ...
        sqlite3VdbeMemStringify(pIn3, encoding, 1);
        // ... (中略) ...
    }
    assert( pOp->p4type==P4_COLLSEQ || pOp->p4.pColl==0 );
    res = sqlite3MemCompare(pIn3, pIn1, pOp->p4.pColl);
  }

  /* Undo any changes made by applyAffinity() to the input registers. */
  assert( (pIn3->flags & MEM_Dyn) == (flags3 & MEM_Dyn) );
  pIn3->flags = flags3;
  assert( (pIn1->flags & MEM_Dyn) == (flags1 & MEM_Dyn) );
  pIn1->flags = flags1;
```

複数列のソートキー比較は **OP_Compare** が `KeyInfo` の照合順序と昇降順フラグを見ながら `sqlite3MemCompare` を繰り返す。

[src/vdbe.c L2490-L2550](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/vdbe.c#L2490-L2550)

```c
case OP_Compare: {
  int n;
  int i;
  int p1;
  int p2;
  const KeyInfo *pKeyInfo;
  u32 idx;
  CollSeq *pColl;    /* Collating sequence to use on this term */
  int bRev;          /* True for DESCENDING sort order */
  u32 *aPermute;     /* The permutation */
  // ... (中略) ...
  n = pOp->p3;
  pKeyInfo = pOp->p4.pKeyInfo;
  // ... (中略) ...
  for(i=0; i<n; i++){
    idx = aPermute ? aPermute[i] : (u32)i;
    // ... (中略) ...
    pColl = pKeyInfo->aColl[i];
    bRev = (pKeyInfo->aSortFlags[i] & KEYINFO_ORDER_DESC);
    iCompare = sqlite3MemCompare(&aMem[p1+idx], &aMem[p2+idx], pColl);
    VVA_ONLY( iCompareIsInit = 1; )
    if( iCompare ){
      // ... (中略) ...
      if( bRev ) iCompare = -iCompare;
      break;
    }
  }
  assert( pOp[1].opcode==OP_Jump );
  break;
}
```

## utf.c による符号化変換

`sqlite3VdbeMemTranslate` は `Mem.enc` と要求符号化が異なるとき、UTF-16 同士ならバイトスワップだけで済ませ、それ以外はバッファを再確保して変換する。

[src/utf.c L242-L288](https://github.com/sqlite/sqlite/blob/version-3.53.3/src/utf.c#L242-L288)

```c
SQLITE_NOINLINE int sqlite3VdbeMemTranslate(Mem *pMem, u8 desiredEnc){
  sqlite3_int64 len;          /* Maximum length of output string in bytes */
  unsigned char *zOut;        /* Output buffer */
  unsigned char *zIn;         /* Input iterator */
  unsigned char *zTerm;       /* End of input */
  unsigned char *z;           /* Output iterator */
  unsigned int c;

  assert( pMem->db==0 || sqlite3_mutex_held(pMem->db->mutex) );
  assert( pMem->flags&MEM_Str );
  assert( pMem->enc!=desiredEnc );
  assert( pMem->enc!=0 );
  assert( pMem->n>=0 );

  if( pMem->enc!=SQLITE_UTF8 && desiredEnc!=SQLITE_UTF8 ){
    u8 temp;
    int rc;
    rc = sqlite3VdbeMemMakeWriteable(pMem);
    if( rc!=SQLITE_OK ){
      assert( rc==SQLITE_NOMEM );
      return SQLITE_NOMEM_BKPT;
    }
    zIn = (u8*)pMem->z;
    zTerm = &zIn[pMem->n&~1];
    while( zIn<zTerm ){
      temp = *zIn;
      *zIn = *(zIn+1);
      zIn++;
      *zIn++ = temp;
    }
    pMem->enc = desiredEnc;
    goto translate_out;
  }
```

## 処理の流れ

格納時と比較時では型変換の経路が分かれる。
INSERT では `OP_Affinity` から `OP_MakeRecord` へ進み、比較 opcode は一時変換のあと `flags` を復元する。
`OP_Compare` は `KeyInfo` に従い各レジスタを `sqlite3MemCompare` へ直接渡し、`applyNumericAffinity` や `Stringify`、および `flags` 復元を行わない。

```mermaid
flowchart TD
  subgraph storage [格納時]
    A1[OP_Column で Mem をレジスタへ] --> B1[OP_Affinity で applyAffinity]
    B1 --> C1[OP_MakeRecord でシリアル化]
  end
  subgraph compare [比較時]
    D1[OP_Eq 系: 一時 affinity 適用] --> E1[sqlite3MemCompare]
    E1 --> F1[flags 復元]
    G1[OP_Compare: KeyInfo に従い直接 sqlite3MemCompare] --> H1[OP_Jump で分岐]
  end
```

## 高速化と最適化の工夫

`applyAffinity` の `OPTIMIZATION-IF-FALSE` 分岐は、すでに `MEM_Int` や `MEM_Str` を持つレジスタへの無駄な変換をスキップする。
`OP_Eq` は比較のためだけに型を変え、直後に `flags` を復元するので、以降の opcode が元の表現を再利用できる。
`MEM_IntReal` は整数精度とコンパクト格納を保ちつつ manifest type を REAL として扱う。
`sqlite3_value_type` は `MEM_IntReal` を `SQLITE_FLOAT` に写し、比較や実数取得でも実数相当となる。
`OP_MakeRecord` では整数ペイロードとしてコンパクト直列化できる。

## まとめ

Mem は `flags` と `u` 共用体で複数表現を同居させ、`MEM_Dyn`/`MEM_Ephem`/`MEM_Static` が所有権を区別する。
列アフィニティは `applyAffinity` と **OP_Affinity** で適用され、比較 opcode は一時変換のあと `sqlite3MemCompare` へ進む。
符号化の違いは `utf.c` の `sqlite3VdbeMemTranslate` が吸収する。

## 関連する章

- [第13章 VDBE バイトコードエンジン](13-vdbe-engine.md)（`OP_Column` と `aMem`）
- [第14章 VDBE プログラムの構築](14-vdbe-build.md)（レジスタ割り当て）
- [第16章 外部マージソート](16-external-sort.md)（ソートキーとしての Mem）
