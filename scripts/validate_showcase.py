#!/usr/bin/env python3
"""Validate the public-safe UGC Ninja showcase before publishing or cloning."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def markdown_links(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"!?\\[[^\\]]*\\]\\(([^)]+)\\)", text):
        target = target.strip().split()[0].strip("<>")
        if not target or target.startswith("#"):
            continue
        parsed = urlparse(target)
        if parsed.scheme in {"http", "https", "mailto"}:
            continue
        local = target.split("#", 1)[0]
        if not local:
            continue
        check((path.parent / local).resolve().exists(), f"Broken relative link: {path.relative_to(ROOT)} -> {target}")


def main() -> int:
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    check(len(skills) == 3, f"Expected 3 showcase skills, found {len(skills)}")
    for path in skills:
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\\s*\\nname:\\s*([a-z0-9-]+)\\s*\\ndescription:\\s*(.+?)\\s*\\n---", text, re.S)
        check(bool(match), f"Invalid skill frontmatter: {path.relative_to(ROOT)}")
        if match:
            check(match.group(1) == path.parent.name, f"Skill name mismatch: {path.relative_to(ROOT)}")
            check(len(match.group(2)) <= 1024, f"Skill description too long: {path.relative_to(ROOT)}")

    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            ERRORS.append(f"Invalid JSON {path.relative_to(ROOT)}: {exc}")

    required = [
        "README.md", "VERSION", "RELEASE_NOTES.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md",
        "docs/GOVERNED_AGENT_BASICS.md", "docs/PUBLIC_RELEASE_CHECKLIST.md", "docs/BRAND_AND_USAGE.md",
        "workflows/product-to-content.json", "scripts/validate_showcase.py",
        ".github/workflows/validate.yml", ".github/workflows/release.yml",
    ]
    for rel in required:
        check((ROOT / rel).is_file(), f"Missing required path: {rel}")

    banned_parts = {"sources", "internal", "private-records", "client-data", ".env"}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        check(not any(part.lower() in banned_parts for part in rel.parts), f"Private path is not allowed: {rel}")
        check(path.suffix.lower() not in {".pdf", ".zip", ".tar", ".gz"}, f"Archive/source binary not allowed: {rel}")
        if path.suffix.lower() in {".md", ".json", ".py", ".yml", ".yaml", ".svg"}:
            body = path.read_text(encoding="utf-8", errors="replace")
            for pattern in (r"gh[pousr]_[A-Za-z0-9]{30,}", r"sk-[A-Za-z0-9_-]{24,}", r"AKIA[0-9A-Z]{16}"):
                check(not re.search(pattern, body), f"Possible credential pattern in {rel}")

    for path in ROOT.rglob("*.md"):
        markdown_links(path)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    check("not a guarantee of viral" in readme.lower(), "README must state that viral performance is not promised")
    check("human approval" in readme.lower(), "README must explain human approval")
    check("https://github.com/hmzainjamil/ugc-ninja-agent-starter" in readme, "README clone URL is not configured")

    if ERRORS:
        for error in ERRORS:
            print(f"ERROR: {error}")
        print(f"RESULT: FAIL ({len(ERRORS)} issue(s))")
        return 1

    print(f"skills={len(skills)} json_files={len(list(ROOT.rglob('*.json')))}")
    print("PASS: public showcase structure, skill metadata, JSON, links and release-safety checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
