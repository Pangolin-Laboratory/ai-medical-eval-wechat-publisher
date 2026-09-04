from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


PLACEHOLDERS = ("TODO", "TBD", "待替换", "校样")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a WeChat medical-evaluation card package.")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--copy", type=Path)
    parser.add_argument("--logo", type=Path)
    parser.add_argument("--expected-cards", type=int, default=9)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=1500)
    parser.add_argument("--max-copy-chars", type=int, default=900)
    args = parser.parse_args()

    errors: list[str] = []
    directory = args.directory.resolve()
    cards = sorted(
        path for path in directory.glob("[0-9][0-9]_*.png")
        if not path.name.startswith("00_")
    )
    expected_prefixes = [f"{i:02d}_" for i in range(1, args.expected_cards + 1)]
    if len(cards) != args.expected_cards:
        errors.append(f"expected {args.expected_cards} cards, found {len(cards)}")
    if [path.name[:3] for path in cards] != expected_prefixes:
        errors.append("card prefixes are not a complete ordered sequence")

    contact = list(directory.glob("00_*.png"))
    if len(contact) != 1:
        errors.append(f"expected one 00_ contact sheet, found {len(contact)}")

    for path in cards:
        with Image.open(path) as image:
            if image.size != (args.width, args.height):
                errors.append(f"{path.name}: size {image.size}, expected {(args.width, args.height)}")
            if image.mode != "RGB":
                errors.append(f"{path.name}: mode {image.mode}, expected RGB")
        if path.stat().st_size < 10_000:
            errors.append(f"{path.name}: suspiciously small file")

    if args.copy:
        text = args.copy.read_text(encoding="utf-8")
        if len(text) > args.max_copy_chars:
            errors.append(f"copy has {len(text)} characters, limit is {args.max_copy_chars}")
        for marker in PLACEHOLDERS:
            if marker in text:
                errors.append(f"copy still contains placeholder marker: {marker}")

    markdown_files = list(directory.glob("*.md"))
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        for marker in PLACEHOLDERS:
            if marker in text:
                errors.append(f"{path.name} contains placeholder marker: {marker}")

    if args.logo:
        with Image.open(args.logo) as logo:
            if logo.mode != "RGBA":
                errors.append(f"logo mode is {logo.mode}, expected RGBA")
            else:
                lo, hi = logo.getchannel("A").getextrema()
                if lo != 0 or hi != 255:
                    errors.append(f"logo alpha extrema are {(lo, hi)}, expected (0, 255)")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    print(f"- {len(cards)} cards at {args.width}x{args.height}, RGB")
    print("- contact sheet present")
    if args.copy:
        print(f"- copy length {len(args.copy.read_text(encoding='utf-8'))}/{args.max_copy_chars}")
    if args.logo:
        print("- logo RGBA alpha verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
