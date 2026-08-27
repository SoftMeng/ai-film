"""Find short-drama markdown files by frontmatter tags / type / applicable."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from drama_yaml import parse as yaml_parse

DEFAULT_ROOT = ROOT / "短剧"


def _match(meta: dict, args: argparse.Namespace) -> bool:
    if args.tag:
        tags = meta.get("tags", []) or []
        if not isinstance(tags, list):
            tags = [tags]
        if args.tag not in tags:
            return False
    if args.type:
        if meta.get("type") != args.type:
            return False
    if args.applicable:
        applicable = meta.get("applicable", "") or ""
        if args.applicable not in applicable:
            return False
    return True


def scan(root: Path, args: argparse.Namespace) -> list[Path]:
    if not root.exists():
        return []
    matches: list[Path] = []
    for md in sorted(root.rglob("*.md")):
        try:
            meta, _ = yaml_parse(md.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not meta:
            continue
        if _match(meta, args):
            matches.append(md)
    return matches


def self_check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "短剧"
        (root / "a").mkdir(parents=True)
        (root / "a" / "x.md").write_text(
            "---\ntype: 指纹\ntags: [drama, fingerprint]\napplicable: 所有\n---\n# x",
            encoding="utf-8",
        )
        (root / "a" / "y.md").write_text(
            "---\ntype: 剧本\ntags: [drama, play]\n---\n# y",
            encoding="utf-8",
        )
        (root / "z.md").write_text(
            "---\ntype: 指纹\ntags: [drama, fingerprint]\n---\n# z",
            encoding="utf-8",
        )

        ns1 = argparse.Namespace(tag="fingerprint", type=None, applicable=None)
        results = scan(root, ns1)
        assert len(results) == 2, f"tag scan: expected 2, got {len(results)}"

        ns2 = argparse.Namespace(tag=None, type="剧本", applicable=None)
        results = scan(root, ns2)
        assert len(results) == 1 and results[0].name == "y.md"

        ns3 = argparse.Namespace(tag=None, type=None, applicable="不存在")
        results = scan(root, ns3)
        assert results == []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="匹配 frontmatter tags 包含该值")
    parser.add_argument("--type", help="匹配 frontmatter type 精确等于该值")
    parser.add_argument("--applicable", help="匹配 frontmatter applicable 包含该子串")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="扫描根目录")
    parser.add_argument("--count", action="store_true", help="只输出文件数")
    args = parser.parse_args(argv)

    self_check()
    matches = scan(args.root, args)

    if args.count:
        print(len(matches))
    else:
        for path in matches:
            print(path)

    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(main())