#!/usr/bin/env python3
"""OSS ごとの目次 README.md の体裁を検査する。

AGENTS.md §2「目次 README の体裁」で定めた共通の並びに従っているかを静的に確認する。
検査対象は「直下に README.md と part* サブディレクトリを持つトップレベルのディレクトリ」を
OSS ドキュメントとみなして自動検出する(新しい OSS を足しても自動で対象に入る)。
ルート README.md(リポジトリ全体の入口)は対象外。

検査項目:
  1. 部見出しは `## 第N部`(H2)。`### ` の部見出しや `## 目次` ラッパーを使わない。
  2. 部見出し `## 第…部` が少なくとも1つある。
  3. 末尾の脚注の前に区切り線 `---` がある。
  4. 導入が箇条書き(対象バージョン / 想定読者 / 読み方)。
  5. 目次の章リンク(相対 .md)がすべて実在する。
  6. 一文一行(地の文・箇条書き・脚注の1行に文末「。」を2つ以上、または行末以外に「。」を置かない)。

CI でもローカル(python3 .github/scripts/check-readme-style.py)でも同じ結果になる。
違反があれば GitHub Actions 用の ::error 注釈を出し、終了コード1で失敗する。
"""
import glob
import os
import re
import sys

INLINE_CODE = re.compile(r"`[^`]*`")
LINK_MD = re.compile(r"\]\((?!https?:)([^)#]+\.md)\)")
PERIOD_TAIL_OK = re.compile(r"[^)）」』】、，。\s]")  # 文末「。」の後に許す closing 以外の文字


def find_oss_readmes():
    out = []
    for d in sorted(glob.glob("*/")):
        d = d.rstrip("/")
        readme = os.path.join(d, "README.md")
        if os.path.exists(readme) and glob.glob(os.path.join(d, "part*")):
            out.append(readme)
    return out


def check_ichibun(lines):
    """一文一行に反する行番号(1始まり)を返す。コードフェンス内は無視する。"""
    bad = []
    in_fence = False
    for i, raw in enumerate(lines, 1):
        s = raw.rstrip("\n")
        if s.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not s.strip() or s.lstrip().startswith("#") or re.fullmatch(r"-{3,}\s*", s.strip()):
            continue
        masked = INLINE_CODE.sub(" ", s)
        n = masked.count("。")
        if n >= 2:
            bad.append(i)
        elif n == 1:
            tail = masked[masked.rfind("。") + 1:]
            if PERIOD_TAIL_OK.search(tail):
                bad.append(i)
    return bad


def check_readme(path):
    """違反メッセージのリストを返す(空なら合格)。"""
    errs = []
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines(keepends=True)
    base = os.path.dirname(path)

    # 1. 部見出しのレベルと目次ラッパー
    if re.search(r"^### ", text, re.M):
        errs.append("`### ` の見出しがある。部見出しは `## 第N部` を直接使う")
    if re.search(r"^## 目次\s*$", text, re.M):
        errs.append("`## 目次` ラッパー見出しがある。部見出しを `## 第N部` で直接置く")

    # 2. 部見出しの存在
    if not re.search(r"^## 第.+部", text, re.M):
        errs.append("`## 第N部` の部見出しが見つからない")

    # 3. 区切り線
    if not re.search(r"^-{3,}\s*$", text, re.M):
        errs.append("末尾の脚注の前に置く区切り線 `---` がない")

    # 4. 箇条書き導入
    for label in ("対象バージョン", "想定読者", "読み方"):
        if not re.search(rf"^- \*\*{label}\*\*", text, re.M):
            errs.append(f"導入の箇条書きに `- **{label}**` がない")

    # 5. 章リンクの実在
    for rel in LINK_MD.findall(text):
        if not os.path.exists(os.path.normpath(os.path.join(base, rel))):
            errs.append(f"リンク先が存在しない: {rel}")

    # 6. 一文一行
    for ln in check_ichibun(lines):
        errs.append(f"一文一行に反する(行末以外に「。」がある) L{ln}: {lines[ln-1].strip()[:60]}")

    return errs


def main():
    readmes = find_oss_readmes()
    if not readmes:
        print("OSS の README.md が見つからない")
        return 1
    total = 0
    for path in readmes:
        errs = check_readme(path)
        if errs:
            total += len(errs)
            for e in errs:
                print(f"::error file={path}::{e}")
            print(f"----- {path}: {len(errs)} 件 -----")
    print(f"検査した目次 README: {len(readmes)} / 違反: {total}")
    if total == 0:
        print("すべての目次 README が AGENTS.md §2 の体裁に従っています。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
