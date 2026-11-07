#!/usr/bin/env python3
"""Print the CHANGELOG section for a tag, e.g. ``python tools/release_notes.py v0.1.0``."""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def main() -> int:
    version = sys.argv[1].removeprefix("v")
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(rf"^## \[?{re.escape(version)}\]?.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if match is None:
        print(f"No CHANGELOG entry for {version}", file=sys.stderr)
        return 1
    print(match.group(1).strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
