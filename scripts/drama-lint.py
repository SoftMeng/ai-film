"""Lint a short-drama project: cross-shot consistency, beat/transition validity, internal-code leak."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"

VALID_BEATS = {"期待", "紧张", "释放", "留白", "收束"}
VALID_SWITCHES = {"缓切", "硬切", "接切"}


def load_lint_rules() -> list[tuple[str, re.Pattern[str]]]:
    spec = importlib.util.spec_from_file_location("lint_output", SCRIPTS_DIR / "lint-output.py")
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load lint-output.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RULES


def scan_text(text: str, rules: list[tuple[str, re.Pattern[str]]]) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for label, pattern in rules:
            if pattern.search(line):
                hits.append((line_no, label))
    return hits


def check_internal_codes(shots_dir: Path, rules: list) -> list[str]:
    reports: list[str] = []
    for shot in sorted(shots_dir.glob("shot-*.txt")):
        hits = scan_text(shot.read_text(encoding="utf-8"), rules)
        for line_no, label in hits:
            reports.append(f"{shot}:{line_no}:{label}")
    return reports


def check_fingerprint_consistency(
    shots_dir: Path, fingerprint: dict
) -> list[str]:
    main = fingerprint.get("主角", {})
    non_empty = [
        v for v in main.values() if isinstance(v, str) and v.strip()
    ]
    if not non_empty:
        return []
    reports: list[str] = []
    for shot in sorted(shots_dir.glob("shot-*.txt")):
        text = shot.read_text(encoding="utf-8")
        body_match = re.search(r"【演员本体】\n(.*?)\n\n", text, re.DOTALL)
        if not body_match:
            reports.append(f"{shot}:0:形象一致性")
            continue
        body = body_match.group(1)
        for value in non_empty:
            if value not in body:
                reports.append(f"{shot}:0:形象一致性(缺 {value})")
    return reports


def check_beats_validity(beats_data: dict) -> list[str]:
    reports: list[str] = []
    for entry in beats_data.get("shots", []):
        beat = entry.get("节拍")
        if beat is None:
            continue
        if beat not in VALID_BEATS:
            reports.append(f"节拍.json:{entry.get('镜号', '?')}:非法节拍({beat})")
    return reports


def check_switches_validity(switches_data: dict) -> list[str]:
    reports: list[str] = []
    for entry in switches_data.get("shots", []):
        switch = entry.get("转场")
        if switch is None:
            continue
        if switch not in VALID_SWITCHES:
            reports.append(f"转场.json:{entry.get('镜号', '?')}:非法转场({switch})")
    return reports


def self_check(rules: list) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shots_dir = tmp_path / "shots"
        shots_dir.mkdir()

        # Case 1: clean drama → PASS
        good_fingerprint = {
            "主角": {
                "年龄段": "约 25 岁",
                "脸型关键词": "瓜子",
                "发型关键词": "齐耳短发",
                "肤色关键词": "自然黄",
                "身高气质": "沉稳内敛",
                "标志特征": None,
            },
            "配角": [],
        }
        good_beats = {"shots": [{"镜号": 1, "节拍": "期待"}]}
        good_switches = {"shots": [{"镜号": 1, "转场": "缓切"}]}
        (shots_dir / "shot-1.txt").write_text(
            "【整体风格 · 节拍：期待】\n"
            "TODO\n\n"
            "【镜头 1】\n延续氛围\n\n"
            "【演员本体】\n年龄约 25 岁\n瓜子脸型\n齐耳短发发型\n自然黄肤色\n沉稳内敛气质\n\n"
            "【演员动作】\nTODO\n\n"
            "【运镜节奏】\nTODO\n",
            encoding="utf-8",
        )
        reports = (
            check_internal_codes(shots_dir, rules)
            + check_fingerprint_consistency(shots_dir, good_fingerprint)
            + check_beats_validity(good_beats)
            + check_switches_validity(good_switches)
        )
        if reports:
            raise SystemExit(f"self-check FAILED: clean drama produced hits: {reports}")

        # Case 2: dirty shot (No0008) → FAIL
        (shots_dir / "shot-1.txt").write_text(
            "【整体风格】参考 No0008 的节奏感。\n", encoding="utf-8"
        )
        dirty_reports = check_internal_codes(shots_dir, rules)
        if not dirty_reports:
            raise SystemExit("self-check FAILED: dirty shot not detected")

        # Case 3: invalid beat → FAIL
        bad_beats = {"shots": [{"镜号": 1, "节拍": "乱七八糟"}]}
        bad_reports = check_beats_validity(bad_beats)
        if not bad_reports:
            raise SystemExit("self-check FAILED: invalid beat not detected")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("drama_dir", type=Path, help="短剧目录路径")
    args = parser.parse_args(argv)

    rules = load_lint_rules()
    self_check(rules)

    drama_dir: Path = args.drama_dir
    shots_dir = drama_dir / "shots"
    fingerprint = json.loads((drama_dir / "形象.json").read_text(encoding="utf-8"))
    beats = json.loads((drama_dir / "节拍.json").read_text(encoding="utf-8"))
    switches = json.loads((drama_dir / "转场.json").read_text(encoding="utf-8"))

    if not shots_dir.exists():
        print("PASS (no shots yet)")
        return 0

    reports = (
        check_internal_codes(shots_dir, rules)
        + check_fingerprint_consistency(shots_dir, fingerprint)
        + check_beats_validity(beats)
        + check_switches_validity(switches)
    )

    if reports:
        print("\n".join(reports))
        print(f"FAIL ({len(reports)} hits)")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())