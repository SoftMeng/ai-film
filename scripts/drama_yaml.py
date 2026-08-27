"""Minimal YAML frontmatter parser/dumper (stdlib only)."""

from __future__ import annotations

from typing import Tuple


def parse(text: str) -> Tuple[dict, str]:
    """Parse `---` frontmatter; return (meta_dict, body_str)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta_text = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta: dict = {}
    current_key: str | None = None
    for line in meta_text.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") or line.startswith("- "):
            value = line.lstrip(" -").strip()
            if current_key is not None:
                meta.setdefault(current_key, []).append(value)
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                meta[key] = []
                current_key = key
            else:
                meta[key] = value
                current_key = None
    return meta, body


def dump(meta: dict, body: str = "") -> str:
    """Serialize meta + body back to frontmatter-formatted text."""
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sample = """---
type: 测试
applicable: 所有
tags:
  - a
  - b
beat: 期待
---

# 正文
内容
"""
    meta, body = parse(sample)
    assert meta == {"type": "测试", "applicable": "所有", "tags": ["a", "b"], "beat": "期待"}
    assert body.startswith("# 正文")
    out = dump(meta, body)
    meta2, body2 = parse(out)
    assert meta == meta2
    print("yaml self-check OK")