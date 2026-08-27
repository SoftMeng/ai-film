"""Scan product files for internal codes that must not leak to the public-facing prompt."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

RULES: list[tuple[str, re.Pattern[str]]] = [
    ("内部编号", re.compile(r"No\d{4}")),
    ("镜头模板编号", re.compile(r"模板\s?\d")),
    ("节奏组合名", re.compile(r"嘉桐摇|香菜摇|手枪连招")),
    ("原子动作代号", re.compile(r"胯画八|抬手画圈|顶胯定格")),
    (
        "内部文件路径",
        re.compile(
            r"化妆间/|虚拟演员/|动作库/|舞蹈库/|镜头叙事库/|对白灵感库/|背景库/"
        ),
    ),
]

DEFAULT_TARGETS: list[Path] = [Path("创意MV"), Path("短剧")]


def scan_text(text: str) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for label, pattern in RULES:
            if pattern.search(line):
                hits.append((line_no, label, line.rstrip()))
    return hits


def scan_path(target: Path) -> list[str]:
    reports: list[str] = []
    if target.is_dir():
        files = sorted(target.rglob("*.txt"))
    elif target.is_file():
        files = [target]
    else:
        return reports
    for file_path in files:
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="gbk", errors="ignore")
        for line_no, label, _line in scan_text(content):
            reports.append(f"{file_path}:{line_no}:{label}")
    return reports


def self_check() -> None:
    clean_sample = (
        "【整体风格】电影感都市夜景，写实质感，避免霓虹赛博朋克风格。\n"
        "中速律动 BPM 100-120。\n"
        "【镜头 1】中近景，镜头轻微推进。\n"
        "亚洲女性，短发齐耳，米白色丝质衬衫。\n"
    )
    dirty_sample = clean_sample + "参考 No0008 与 模板 5 的节奏感。\n"

    clean_hits = scan_text(clean_sample)
    dirty_hits = scan_text(dirty_sample)

    if clean_hits:
        raise SystemExit(f"self-check FAILED: clean sample produced hits: {clean_hits}")
    if not dirty_hits or not any(h[1] == "内部编号" for h in dirty_hits):
        raise SystemExit(f"self-check FAILED: dirty sample missed No0008: {dirty_hits}")
    if not any(h[1] == "镜头模板编号" for h in dirty_hits):
        raise SystemExit(f"self-check FAILED: dirty sample missed 模板 5: {dirty_hits}")

    with tempfile.TemporaryDirectory() as tmp:
        dirty_file = Path(tmp) / "dirty.txt"
        dirty_file.write_text(
            "【整体风格 · 节拍：紧张】\n参考 No0008 与 模板 5 的节奏感。\n",
            encoding="utf-8",
        )
        file_reports = scan_path(dirty_file)
        labels = [r.rsplit(":", 1)[-1] for r in file_reports]
        if "内部编号" not in labels:
            raise SystemExit(
                f"self-check FAILED: scan_path missed 内部编号: {file_reports}"
            )
        if "镜头模板编号" not in labels:
            raise SystemExit(
                f"self-check FAILED: scan_path missed 镜头模板编号: {file_reports}"
            )


def resolve_targets(args: argparse.Namespace) -> list[Path]:
    if args.target is not None:
        return [args.target]
    return [t for t in DEFAULT_TARGETS if t.exists()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="单文件或单目录（不传则扫默认产物目录）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="显式扫所有默认产物目录（创意MV/ + 短剧/）",
    )
    args = parser.parse_args(argv)

    self_check()
    targets = resolve_targets(args)

    reports: list[str] = []
    for target in targets:
        reports.extend(scan_path(target))

    if reports:
        print("\n".join(reports))
        print(f"FAIL ({len(reports)} hits)")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())