#!/usr/bin/env python3
"""Fingerprint of everything that decides how a video LOOKS: the generator skill and the render tool.

    python scripts/skill_hash.py            # prints a 16-char hash

The night job compares it with data/approval.json. Any change to the skill's scripts, assets or
references, or to the tool's source, gives a new hash, and the job goes back to making a short demo
for the owner to approve instead of publishing full videos. Examples, caches and tests are ignored.
"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARTS = [
    ROOT / ".claude/skills/code2video-resource-generator/scripts",
    ROOT / ".claude/skills/code2video-resource-generator/assets",
    ROOT / ".claude/skills/code2video-resource-generator/references",
    ROOT / ".claude/skills/code2video-resource-generator/SKILL.md",
    ROOT / "tools/code2video/src",
]
SKIP = {"node_modules", "__pycache__", ".pytest_cache", "examples"}


def files():
    for part in PARTS:
        if part.is_file():
            yield part
        elif part.is_dir():
            for f in sorted(part.rglob("*")):
                if f.is_file() and not (SKIP & set(f.parts)) and f.suffix not in (".pyc",):
                    yield f


def skill_hash():
    h = hashlib.sha256()
    for f in files():
        h.update(f.relative_to(ROOT).as_posix().encode())
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


if __name__ == "__main__":
    print(skill_hash())
    sys.exit(0)
