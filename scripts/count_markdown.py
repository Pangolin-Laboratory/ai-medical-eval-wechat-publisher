from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Count a UTF-8 Markdown deliverable exactly.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--max-chars", type=int, default=900)
    args = parser.parse_args()

    text = args.path.read_text(encoding="utf-8")
    total = len(text)
    cjk = sum("\u4e00" <= char <= "\u9fff" for char in text)
    print(f"TOTAL_CHARS={total}")
    print(f"CJK_CHARS={cjk}")
    print(f"LIMIT={args.max_chars}")
    if total > args.max_chars:
        print(f"FAIL: exceeds limit by {total - args.max_chars} characters")
        return 1
    print(f"PASS: {args.max_chars - total} characters remaining")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
