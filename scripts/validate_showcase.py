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


def check_markdown_links(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")
    for _, target in pattern.findall(text):
        target = target.strip().split()[0].strip("<>")
        parsed = urlparse(target)
        if parsed.scheme in {"http", "https", "mailto"} or target.startswith("#"):
            continue
        relative = target.split("#", 1)[0]
        if relative:
            check((path.parent / relative).resolve().exists(), f"Broken relative link in {path.relative_to(ROOT)}: {target}")


def main() -> int:
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    check(len(skills) == 3, f"Expected 3 skills, found {len(skills)}")
    for path in skills:
        content = path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\nname:\s*([a-z0-9-]+)\s*\ndescription:\s*(.+?)\s*\n---", content, re.S)
        check(match is not None, f"Invalid skill frontmatter: {path.relative_to(ROOT)}")
        if match:
            check(match.group(1) == path.parent.name, f"Skill folder/name mismatch: {path.relative_to(ROOT)}")
            check(len(match.group(2)) <= 1024, f"Skill description exceeds 1024 characters: {path.relative_to(ROOT)}")

    json_files = sorted(ROOT.rglob("*.json"))
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            ERRORS.append(f"Invalid JSON {path.relative_to(ROOT)}: {exc}")

    required = [
        "README.md", "VERSION", "RELEASE_NOTES.md", "LICENSE", "CONTRIBUTING.md",
        "SECURITY.md", "SUPPORT.md", "docs/GOVERNED_AGENT_BASICS.md",
        "docs/PUBLIC_RELEASE_CHECKLIST.md", "docs/BRAND_AND_USAGE.md",
        "workflows/product-to-content.json", "scripts/validate_showcase.py",
        ".github/workflows/validate.yml", ".github/workflows/release.yml",
    ]
    for relative in required:
        check((ROOT / relative).is_file(), f"Missing required file: {relative}")

    banned_parts = {"sources", "internal", "private-records", "client-data", ".env"}
    banned_suffixes = {".pdf", ".zip", ".tar", ".gz"}
    secret_patterns = (
        r"gh[pousr]_[A-Za-z0-9]{30,}",
        r"sk-[A-Za-z0-9_-]{24,}",
        r"AKIA[0-9A-Z]{16}",
    )
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        check(not any(part.lower() in banned_parts for part in relative.parts), f"Private path is not allowed: {relative}")
        check(path.suffix.lower() not in banned_suffixes, f"Private source/archive file is not allowed: {relative}")
        if path.suffix.lower() in {".md", ".json", ".py", ".yml", ".yaml", ".svg"}:
            body = path.read_text(encoding="utf-8", errors="replace")
            for pattern in secret_patterns:
                check(re.search(pattern, body) is None, f"Possible credential pattern in {relative}")

    for path in ROOT.rglob("*.md"):
        check_markdown_links(path)

    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    check("not a guarantee of viral" in readme, "README must state that viral performance is not guaranteed")
    check("human approval" in readme, "README must explain human approval")
    check("https://github.com/hmzainjamil/ugc-ninja-agent-starter" in readme, "README must include the public clone URL")

    if ERRORS:
        for error in ERRORS:
            print(f"ERROR: {error}")
        print(f"RESULT: FAIL ({len(ERRORS)} issue(s))")
        return 1

    print(f"skills={len(skills)} json_files={len(json_files)}")
    print("PASS: public showcase structure, skill metadata, JSON, links and release-safety checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
