"""The README's opening walkthrough must run, and its relative links must resolve."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
MARKDOWN = [README, *sorted((ROOT / "docs").rglob("*.md"))]


def test_readme_walkthrough_runs() -> None:
    text = README.read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)
    walkthrough = blocks[:3]  # the three layers of the opening problem
    assert "SearchAlgorithms.lower_bound" in walkthrough[0]
    namespace: dict[str, object] = {}
    for block in walkthrough:
        exec(compile(block, "<README>", "exec"), namespace)
    result = namespace["result"]
    assert result.status.value == "FAILURE"  # type: ignore[attr-defined]
    assert result.errors[0].code == "PRECONDITION_FAILED"  # type: ignore[attr-defined]
    assert namespace["index"] == 1
    assert namespace["scale"][namespace["index"]] == (500, 4.2)  # type: ignore[index]


def test_relative_markdown_links_resolve() -> None:
    broken = []
    for path in MARKDOWN:
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (path.parent / target).exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    assert not broken, broken
