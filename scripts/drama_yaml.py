"""Minimal YAML 1.2 subset parser/dumper (stdlib only)."""

from __future__ import annotations

import re
from typing import Any, Tuple


class YAMLError(Exception):
    def __init__(self, msg: str, line_no: int = 0):
        super().__init__(f"line {line_no}: {msg}" if line_no else msg)
        self.line_no = line_no


_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+([eE][-+]?\d+)?$|^-?\d+[eE][-+]?\d+$")


def _scalar(token: str) -> Any:
    if token == "" or token.lower() in ("null", "~"):
        return None
    lo = token.lower()
    if lo == "true":
        return True
    if lo == "false":
        return False
    if token.startswith('"') and token.endswith('"') and len(token) >= 2:
        inner = token[1:-1]
        out: list[str] = []
        i = 0
        while i < len(inner):
            c = inner[i]
            if c == "\\" and i + 1 < len(inner):
                nxt = inner[i + 1]
                mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "0": "\0"}
                out.append(mapping.get(nxt, nxt))
                i += 2
            else:
                out.append(c)
                i += 1
        return "".join(out)
    if token.startswith("'") and token.endswith("'") and len(token) >= 2:
        return token[1:-1]
    if token.startswith("[") and token.endswith("]"):
        return _parse_inline_list(token[1:-1])
    if token.startswith("{") and token.endswith("}"):
        return _parse_inline_map(token[1:-1])
    if _INT_RE.match(token):
        return int(token)
    if _FLOAT_RE.match(token):
        return float(token)
    return token


def _parse_inline_list(body: str) -> list[Any]:
    items: list[Any] = []
    depth = 0
    current: list[str] = []
    in_str = False
    quote = ""
    i = 0
    while i < len(body):
        c = body[i]
        if in_str:
            current.append(c)
            if c == "\\" and i + 1 < len(body):
                current.append(body[i + 1])
                i += 2
                continue
            if c == quote:
                in_str = False
                quote = ""
            i += 1
            continue
        if c in ("'", '"'):
            in_str = True
            quote = c
            current.append(c)
        elif c in ("[", "{"):
            depth += 1
            current.append(c)
        elif c in ("]", "}"):
            depth -= 1
            current.append(c)
        elif c == "," and depth == 0:
            items.append(_scalar("".join(current).strip()))
            current = []
        else:
            current.append(c)
        i += 1
    last = "".join(current).strip()
    if last:
        items.append(_scalar(last))
    return items


def _parse_inline_map(body: str) -> dict:
    items = _parse_inline_list(body)
    out: dict = {}
    for i in range(0, len(items), 2):
        out[str(items[i])] = items[i + 1]
    return out


def _strip_comment(line: str) -> str:
    in_str = False
    quote = ""
    out: list[str] = []
    i = 0
    while i < len(line):
        c = line[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < len(line):
                out.append(line[i + 1])
                i += 2
                continue
            if c == quote:
                in_str = False
                quote = ""
        else:
            if c in ("'", '"'):
                in_str = True
                quote = c
                out.append(c)
            elif c == "#":
                break
            else:
                out.append(c)
        i += 1
    return "".join(out).rstrip()


def _indent_of(line: str) -> int:
    n = 0
    for ch in line:
        if ch == " ":
            n += 1
        elif ch == "\t":
            n += 4
        else:
            break
    return n


def parse_block(lines: list[str], start: int, min_indent: int) -> Tuple[Any, int]:
    if start >= len(lines):
        return None, start
    line_no = start + 1
    line = lines[start]
    stripped = line.strip()

    if stripped.startswith("- "):
        seq: list[Any] = []
        while start < len(lines):
            stripped = lines[start].strip()
            if not stripped.startswith("- "):
                break
            item_content = lines[start][_indent_of(lines[start]) + 2 :]
            child_indent = min_indent + 2
            if not item_content.strip():
                start += 1
                if start < len(lines) and _indent_of(lines[start]) >= child_indent:
                    value, start = parse_block(lines, start, child_indent)
                else:
                    value = None
            elif item_content.lstrip().startswith(":"):
                key_part, _, rest = item_content.lstrip()[1:].partition(":")
                if not rest.strip() and not rest.startswith(" "):
                    inline: dict = {}
                    key = key_part.strip()
                    if key:
                        inline[key] = None
                    start += 1
                    while start < len(lines) and not lines[start].strip():
                        start += 1
                    if start < len(lines) and _indent_of(lines[start]) >= child_indent + 2:
                        sub_value, start = parse_block(lines, start, child_indent + 2)
                        inline[key] = sub_value
                    seq.append(inline)
                else:
                    inline = {}
                    if rest.strip() == "" or rest.lstrip().startswith(":"):
                        inline[key_part.strip()] = None
                        start += 1
                        if start < len(lines) and _indent_of(lines[start]) >= child_indent:
                            sub_value, start = parse_block(lines, start, child_indent)
                            inline[list(inline.keys())[0]] = sub_value
                    else:
                        inline[key_part.strip()] = _scalar(rest.strip())
                    seq.append(inline)
            else:
                value, start = parse_block(lines, start, child_indent - 2) if False else (
                    _scalar(item_content.strip()),
                    start + 1,
                )
                seq.append(value)
        return seq, start

    mapping: dict[str, Any] = {}
    while start < len(lines):
        stripped = lines[start].strip()
        if not stripped:
            start += 1
            continue
        if stripped.startswith("- "):
            break
        if ":" not in stripped:
            raise YAMLError(f"expected key:value, got {stripped!r}", line_no)
        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            start += 1
            while start < len(lines) and not lines[start].strip():
                start += 1
            if start < len(lines):
                next_indent = _indent_of(lines[start])
                if next_indent > min_indent:
                    sub_value, start = parse_block(lines, start, next_indent)
                else:
                    sub_value = None
            else:
                sub_value = None
            mapping[key] = sub_value
        else:
            mapping[key] = _scalar(rest)
            start += 1
        line_no = start + 1
    return mapping, start


def parse(text: str) -> Tuple[dict, str]:
    """Parse `---` frontmatter; return (meta_dict, body_str)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta_text = text[3:end]
    body = text[end + 4 :].lstrip("\n")

    lines = [_strip_comment(l) for l in meta_text.splitlines() if _strip_comment(l).strip()]
    if not lines:
        return {}, body
    try:
        result, _ = parse_block(lines, 0, 0)
        if not isinstance(result, dict):
            raise YAMLError("top-level must be a mapping", 1)
        return result, body
    except YAMLError:
        raise


def _scalar_repr(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if any(c in s for c in [":", "#", '"', "'", "\n"]) or s != s.strip() or s == "":
        escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return s


def dump(meta: dict, body: str = "") -> str:
    """Serialize meta + body back to frontmatter-formatted text."""
    lines = ["---"]

    def render(value: Any, indent: int) -> list[str]:
        pad = " " * indent
        if isinstance(value, dict):
            out: list[str] = []
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    out.append(f"{pad}{k}:")
                    out.extend(render(v, indent + 2))
                elif v is None:
                    out.append(f"{pad}{k}:")
                else:
                    out.append(f"{pad}{k}: {_scalar_repr(v)}")
            return out
        if isinstance(value, list):
            out = []
            for item in value:
                if isinstance(item, (dict, list)):
                    out.append(f"{pad}-")
                    out.extend(render(item, indent + 2))
                else:
                    out.append(f"{pad}- {_scalar_repr(item)}")
            return out
        return [f"{pad}{_scalar_repr(value)}"]

    for k, v in meta.items():
        if isinstance(v, (dict, list)):
            lines.append(f"{k}:")
            lines.extend(render(v, 2))
        elif v is None:
            lines.append(f"{k}:")
        else:
            lines.append(f"{k}: {_scalar_repr(v)}")
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    cases = [
        ("flat", "type: 入口\napplicable: 所有短剧\ntags: [drama, index]"),
        ("nested", "outer:\n  inner: value\n  list: [a, b]\nn: 1"),
        ("quoted", 'name: "with: colon"\nescape: "line\\nbreak"'),
        ("comment", "a: 1 # inline\n# full line\nb: 2"),
        ("multiline_list", "tags:\n  - one\n  - two\n  - three"),
        ("inline_list_quoted", 'tags: [drama, "with: colon", three]'),
    ]
    for name, src in cases:
        wrapped = "---\n" + src + "\n---\nbody"
        meta, body = parse(wrapped)
        if body != "body":
            raise SystemExit(f"{name}: body mismatch")
        out = dump(meta, body)
        meta2, _ = parse(out)
        if meta != meta2:
            raise SystemExit(f"{name}: round-trip mismatch")
    print("yaml self-check OK")