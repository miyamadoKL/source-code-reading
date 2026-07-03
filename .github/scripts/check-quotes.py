#!/usr/bin/env python3
"""コード引用の行番号照合と章間リンクの検査。

ドキュメント中の GitHub 引用リンク（blob/<tag>/<path>#L<a>-L<b>）の直後にある
コードブロックを、ローカルに展開したソースツリーの該当行と突き合わせる。
併せて .md への相対リンクが実在ファイルを指すかも検査する。

使い方:
  python3 .github/scripts/check-quotes.py <docs_dir> <local_src_dir> <owner/repo> <tag>
例:
  python3 .github/scripts/check-quotes.py openssh ~/oss/openssh-portable-V_10_3_P1 openssh/openssh-portable V_10_3_P1

終了コード: 不一致・リンク切れがあれば 1。
注意: 章冒頭の「本章で読むソース」のようなコードブロックを伴わないリンク一覧は照合対象外。
"""
import glob
import os
import re
import sys


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    docs_dir, src_dir, repo, tag = sys.argv[1:5]
    src_dir = os.path.expanduser(src_dir)
    link_re = re.compile(
        rf"github\.com/{re.escape(repo)}/blob/{re.escape(tag)}/([\w./+-]+)#L(\d+)(?:-L(\d+))?"
    )
    rel_re = re.compile(r"\]\(([^)#\s]+\.md)\)")
    total = ok = bad = nofile = broken = 0
    for md in sorted(glob.glob(f"{docs_dir}/**/*.md", recursive=True)):
        text = open(md).read()
        lines = text.splitlines()
        # 相対リンク検査
        for m in rel_re.finditer(text):
            target = m.group(1)
            if target.startswith("http"):
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(md), target))
            if not os.path.isfile(resolved):
                broken += 1
                print(f"BROKEN-LINK {md} -> {target}")
        # 引用照合
        i = 0
        while i < len(lines):
            m = link_re.search(lines[i])
            if not m or lines[i].lstrip().startswith(">"):
                # 章冒頭の「本章で読むソース」一覧（blockquote）は照合対象外
                i += 1
                continue
            rel, a = m.group(1), int(m.group(2))
            b = int(m.group(3) or m.group(2))
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                if link_re.search(lines[j]):
                    break
                j += 1
            block = []
            if j < len(lines) and lines[j].startswith("```") and not lines[j].startswith("```mermaid"):
                k = j + 1
                while k < len(lines) and not lines[k].startswith("```"):
                    block.append(lines[k])
                    k += 1
            quoted = [q.strip() for q in block if q.strip() and "中略" not in q and not q.strip().startswith("//")]
            if not quoted:
                i += 1
                continue
            total += 1
            path = os.path.join(src_dir, rel)
            if not os.path.isfile(path):
                nofile += 1
                print(f"NOFILE {md}:{i + 1} {rel}")
                i += 1
                continue
            src = open(path, errors="replace").read().splitlines()
            seg = [s.strip() for s in src[a - 1:b] if s.strip()]
            matched = sum(1 for q in quoted if q in seg)
            ratio = matched / len(quoted)
            if ratio >= 0.7:
                ok += 1
            else:
                bad += 1
                print(f"BAD({ratio:.0%}) {md}:{i + 1} {rel}#L{a}-L{b} 引用{len(quoted)}行中{matched}行のみ一致")
            i += 1
    print(f"引用 {total} 件: OK {ok} / 不一致 {bad} / ファイル無し {nofile} / リンク切れ {broken}")
    return 1 if (bad or nofile or broken) else 0


if __name__ == "__main__":
    sys.exit(main())
