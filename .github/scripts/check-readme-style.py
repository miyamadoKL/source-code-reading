#!/usr/bin/env python3
"""OSS ごとの目次 README.md の体裁を検査する。

AGENTS.md §2「目次 README の体裁」で定めた共通の並びに従っているかを静的に確認する。
検査対象は「直下に README.md と part* サブディレクトリを持つディレクトリ」を OSS ドキュメント
とみなして自動検出する(入れ子も可。新しい OSS や入れ子の本を足しても自動で対象に入る)。
ルート README.md やエコシステムの目次(part* を持たない)は対象外。

検査項目:
  1. 部見出しは `## 第N部`(H2)。`### ` の部見出しを使わない。
  2. H2 見出しは `## 第N部 …` か `## 付録` だけ(`## 目次` や `## Appendix` 等を弾く)。
  3. 部番号が 0 から連番(`## 第0部`, `## 第1部`, …)で、欠けや重複や順序逆転がない。
  4. 末尾の脚注(`>` 引用ブロック)の直前に区切り線 `---` がある。
  5. 導入が箇条書き(対象バージョン / 想定読者 / 読み方)。
  6. 目次の章リンク(相対 .md、アンカー付きも可)がすべて実在する。
  7. 一文一行(地の文・箇条書き・脚注の1行に、行末以外の「。」を置かない)。

CI でもローカル(python3 .github/scripts/check-readme-style.py)でも同じ結果になる。
違反があれば GitHub Actions 用の ::error 注釈を出し、終了コード1で失敗する。
"""
import os
import re
import sys

INLINE_CODE = re.compile(r"`[^`]*`")
# 相対 .md リンク(http(s) を除く)。`foo.md` も `foo.md#anchor` も .md 部分だけ取る。
LINK_MD = re.compile(r"\]\((?!https?:)([^)#]*?\.md)(?:#[^)]*)?\)")
PERIOD_TAIL_OK = re.compile(r"[^)）」』】、，。\s]")  # 文末「。」の後に許す closing 以外の文字
HR = re.compile(r"---")  # 体裁は `---` 固定。`----` 等は許さない
PART_HEADING = re.compile(r"^## 第(\d+)部")


def find_oss_readmes():
    out = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".github", "node_modules")]
        if "README.md" in files and any(d.startswith("part") for d in dirs):
            out.append(os.path.normpath(os.path.join(root, "README.md")))
    return sorted(out)


def check_headings(text, errs):
    if re.search(r"^### ", text, re.M):
        errs.append("`### ` の見出しがある。部見出しは `## 第N部` を直接使う")
    h2 = re.findall(r"^## (.+?)\s*$", text, re.M)
    part_nums = []
    for h in h2:
        m = re.match(r"第(\d+)部", h)
        if m:
            part_nums.append(int(m.group(1)))
        elif h == "付録":
            continue
        else:
            errs.append(f"H2 見出しは `## 第N部` か `## 付録` のみ可。不正: `## {h}`")
    if not part_nums:
        errs.append("`## 第N部` の部見出しが見つからない")
    elif part_nums != list(range(len(part_nums))):
        errs.append(f"部番号が 0 からの連番でない(検出: {part_nums}、期待: {list(range(len(part_nums)))})")


def check_footer_hr(lines, errs):
    i = len(lines) - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    if i < 0 or not lines[i].lstrip().startswith(">"):
        errs.append("末尾に脚注(`>` 引用ブロック)がない")
        return
    j = i
    while j >= 0 and lines[j].lstrip().startswith(">"):
        j -= 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j < 0 or not HR.fullmatch(lines[j].strip()):
        errs.append("末尾の脚注(`>`)の直前に区切り線 `---` がない")


def check_ichibun(lines, errs):
    in_fence = False
    for i, raw in enumerate(lines, 1):
        s = raw.rstrip("\n")
        if s.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not s.strip() or s.lstrip().startswith("#") or HR.fullmatch(s.strip()):
            continue
        masked = INLINE_CODE.sub(" ", s)
        n = masked.count("。")
        if n >= 2 or (n == 1 and PERIOD_TAIL_OK.search(masked[masked.rfind("。") + 1:])):
            errs.append(f"一文一行に反する(行末以外に「。」がある) L{i}: {s.strip()[:60]}")


def check_readme(path):
    errs = []
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    base = os.path.dirname(path)

    check_headings(text, errs)
    check_footer_hr(lines, errs)
    for label in ("対象バージョン", "想定読者", "読み方"):
        if not re.search(rf"^- \*\*{label}\*\*", text, re.M):
            errs.append(f"導入の箇条書きに `- **{label}**` がない")
    for rel in LINK_MD.findall(text):
        if not os.path.exists(os.path.normpath(os.path.join(base, rel))):
            errs.append(f"リンク先が存在しない: {rel}")
    check_ichibun(lines, errs)
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
