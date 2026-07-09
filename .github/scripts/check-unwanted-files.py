#!/usr/bin/env python3
"""不要ファイルの混入を検査する。

検査対象:
- 追跡中の WRITING_GUIDE / writing-guide ファイルがないこと
- Markdown 地の文にローカル絶対パス（/home/<user>/, /Users/<user>/, ~/oss/ 等）がないこと
- 「ローカル参照元」行が成果物に残っていないこと

systemd の `src/home/` のような OSS 内パスは除外する。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MARKDOWNLINT_CONFIG = Path(".markdownlint-cli2.jsonc")
SKIP_DIRS = {".git", ".github", ".codex", "node_modules", ".wiki", ".claude"}

WRITING_GUIDE_NAMES = {
    "WRITING_GUIDE.md",
    ".writing-guide.md",
    "writing-guide.md",
}

# /home/<user>/ or /Users/<user>/ — not src/home/ in GitHub URLs
LOCAL_ABS_RE = re.compile(
    r"(?<![\w./])/(?:home|Users)/[a-zA-Z0-9._-]+/"
)
# 開発者のローカルツールパス（~/oss/ 等）。~/.ssh/ のような一般説明は除外。
TILDE_PATH_RE = re.compile(
    r"~/(?!\.ssh|\.gnupg|\.config|\.local)(?:oss|[a-zA-Z0-9._-]+)/"
)
LOCAL_REF_RE = re.compile(r"ローカル参照元")


def discover_doc_dirs() -> list[Path]:
    if not MARKDOWNLINT_CONFIG.is_file():
        return [Path(".")]
    text = MARKDOWNLINT_CONFIG.read_text(encoding="utf-8")
    dirs: list[Path] = []
    for m in re.finditer(r'"([^"]+)/\*\*/\*\.md"', text):
        dirs.append(Path(m.group(1)))
    return dirs or [Path(".")]


def git_tracked_writing_guides() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*WRITING*", "*writing-guide*"],
        capture_output=True,
        check=False,
    )
    if out.returncode != 0:
        return []
    return [p.decode() for p in out.stdout.split(b"\0") if p]


def iter_markdown_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
    return files


def scan_markdown(path: Path) -> list[str]:
    violations: list[str] = []
    in_code = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if LOCAL_ABS_RE.search(line):
            violations.append(f"{path}:{lineno}: local absolute path")
        if TILDE_PATH_RE.search(line):
            violations.append(f"{path}:{lineno}: tilde path")
        if LOCAL_REF_RE.search(line):
            violations.append(f"{path}:{lineno}: ローカル参照元")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dirs",
        nargs="*",
        help="検査対象ディレクトリ（省略時は markdownlint 設定から自動検出）",
    )
    args = parser.parse_args()
    roots = [Path(d) for d in args.dirs] if args.dirs else discover_doc_dirs()

    errors: list[str] = []

    for tracked in git_tracked_writing_guides():
        base = Path(tracked).name
        if base in WRITING_GUIDE_NAMES or "writing-guide" in tracked:
            errors.append(f"TRACKED-GUIDE {tracked}")

    for md in iter_markdown_files(roots):
        errors.extend(scan_markdown(md))

    if errors:
        print("UNWANTED-FILE CHECK FAILED", file=sys.stderr)
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    print(f"OK unwanted-files ({len(iter_markdown_files(roots))} markdown files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
