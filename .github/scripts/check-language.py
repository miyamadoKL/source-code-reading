#!/usr/bin/env python3
"""Markdown の日本語地の文に混入したハングルと簡体字中国語を検査する。

対象は引数で渡したディレクトリ配下の `*.md` である。
引数を省略した場合は `.markdownlint-cli2.jsonc` の `"<dir>/**/*.md"` から既存 lint 対象の OSS ディレクトリを拾う。
コードブロック内は、引用元のコメントや文字列をそのまま載せることがあるため検査しない。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


MARKDOWNLINT_CONFIG = Path(".markdownlint-cli2.jsonc")
EXCLUDED_BASENAMES = {"WRITING_GUIDE.md", ".writing-guide.md", "writing-guide.md"}
SKIP_DIRS = {".git", ".github", ".codex", "node_modules"}

HANGUL_RE = re.compile(
    "["
    "\u1100-\u11ff"  # Hangul Jamo
    "\u3130-\u318f"  # Hangul Compatibility Jamo
    "\ua960-\ua97f"  # Hangul Jamo Extended-A
    "\uac00-\ud7af"  # Hangul Syllables
    "\ud7b0-\ud7ff"  # Hangul Jamo Extended-B
    "\uffa0-\uffdc"  # Halfwidth Hangul variants
    "]"
)

# 日本語の常用漢字と字形を共有しないものに絞る。
# `点` や `会` のように日本語として自然な字は含めない。
SIMPLIFIED_CHARS = "".join(
    sorted(
        set(
            "码实现场关联传线节应于员处见说语时东为义乐头"
            "发开过还这们个对从图层读调试测库块态类转压缩则备扩释权"
        )
    )
)
SIMPLIFIED_RE = re.compile(f"[{re.escape(SIMPLIFIED_CHARS)}]")

CHINESE_TERMS = (
    "源码",
    "期望状態",
    "假定配置",
    "实际",
    "字段",
)
TERM_RE = re.compile("|".join(re.escape(term) for term in CHINESE_TERMS))

FENCE_START_RE = re.compile(r"^\s*(```+|~~~+)")


@dataclass(frozen=True)
class Violation:
    path: Path
    line_no: int
    kind: str
    found: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Markdown の日本語地の文に混入したハングルと簡体字中国語を検査する。"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="検査対象のディレクトリまたは Markdown ファイル。省略時は既存 lint 対象の OSS ディレクトリ。",
    )
    return parser.parse_args()


def default_targets() -> list[Path]:
    if not MARKDOWNLINT_CONFIG.exists():
        return find_oss_dirs()

    text = MARKDOWNLINT_CONFIG.read_text(encoding="utf-8")
    dirs: list[Path] = []
    seen: set[Path] = set()
    for match in re.finditer(r'"([^"]+?)/\*\*/\*\.md"', text):
        path = Path(match.group(1))
        if path.exists() and path.is_dir() and path not in seen:
            dirs.append(path)
            seen.add(path)
    return dirs if dirs else find_oss_dirs()


def find_oss_dirs() -> list[Path]:
    out: list[Path] = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if "README.md" in files and any(d.startswith("part") for d in dirs):
            out.append(Path(root))
    return sorted(out)


def markdown_files(targets: list[Path]) -> tuple[list[Path], int]:
    files: list[Path] = []
    seen: set[Path] = set()
    target_errors = 0
    for target in targets:
        if target.is_file():
            candidates = [target] if target.suffix == ".md" else []
        elif target.is_dir():
            candidates = sorted(target.rglob("*.md"))
        else:
            print(f"::error file={target}::検査対象が存在しない")
            target_errors += 1
            continue

        for path in candidates:
            if path.name in EXCLUDED_BASENAMES or any(part in SKIP_DIRS for part in path.parts):
                continue
            norm = Path(os.path.normpath(path))
            if norm not in seen:
                files.append(norm)
                seen.add(norm)
    return sorted(files), target_errors


def prose_lines(path: Path):
    in_fence = False
    fence_char = ""
    fence_len = 0
    with path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            stripped = raw.lstrip()
            if not in_fence:
                match = FENCE_START_RE.match(raw)
                if match:
                    marker = match.group(1)
                    in_fence = True
                    fence_char = marker[0]
                    fence_len = len(marker)
                    continue
                yield line_no, raw.rstrip("\n")
                continue

            if stripped.startswith(fence_char * fence_len):
                in_fence = False
                fence_char = ""
                fence_len = 0


def unique_matches(pattern: re.Pattern[str], text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in pattern.finditer(text):
        found = match.group(0)
        if found not in seen:
            out.append(found)
            seen.add(found)
    return out


def check_file(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    for line_no, line in prose_lines(path):
        for found in unique_matches(HANGUL_RE, line):
            violations.append(Violation(path, line_no, "ハングル", found))
        for found in unique_matches(SIMPLIFIED_RE, line):
            violations.append(Violation(path, line_no, "簡体字の可能性", found))
        for found in unique_matches(TERM_RE, line):
            violations.append(Violation(path, line_no, "中国語由来の語彙", found))
    return violations


def report(violations: list[Violation]) -> None:
    for v in violations:
        print(f"::error file={v.path}::L{v.line_no}: {v.kind} `{v.found}` が残っています")


def main() -> int:
    args = parse_args()
    targets = [Path(p) for p in args.paths] if args.paths else default_targets()
    files, target_errors = markdown_files(targets)
    if not files:
        print("検査対象の Markdown ファイルが見つかりません。")
        return 1

    violations: list[Violation] = []
    for path in files:
        violations.extend(check_file(path))

    report(violations)
    print(f"検査した Markdown: {len(files)} / 違反: {len(violations)}")
    if target_errors or violations:
        return 1
    print("ハングル、簡体字中国語、既知の中国語由来語彙の混入は見つかりませんでした。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
