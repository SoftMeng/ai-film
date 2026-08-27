"""Lint a short-drama project via the CHECKS registry; each check returns a list of hits."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from drama_yaml import parse as yaml_parse  # noqa: E402

VALID_BEATS = {"期待", "紧张", "释放", "留白", "收束"}
VALID_SWITCHES = {"缓切", "硬切", "接切"}

CheckFn = Callable[[Path], list[str]]
CHECKS: list[CheckFn] = []


def register(check: CheckFn) -> CheckFn:
    """Decorator: add check function to CHECKS registry."""
    CHECKS.append(check)
    return check


def load_lint_rules() -> list[tuple[str, re.Pattern[str]]]:
    spec = importlib.util.spec_from_file_location("lint_output", SCRIPTS_DIR / "lint-output.py")
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load lint-output.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RULES


def _scan_text(text: str, rules: list[tuple[str, re.Pattern[str]]]) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for label, pattern in rules:
            if pattern.search(line):
                hits.append((line_no, label))
    return hits


def _shots_dir(drama_dir: Path) -> Path | None:
    p = drama_dir / "shots"
    return p if p.exists() else None


def _load_json(drama_dir: Path, name: str) -> dict:
    return json.loads((drama_dir / name).read_text(encoding="utf-8"))


def _read_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    return yaml_parse(text)


@register
def check_internal_codes(drama_dir: Path) -> list[str]:
    rules = load_lint_rules()
    shots = _shots_dir(drama_dir)
    if shots is None:
        return []
    reports: list[str] = []
    for shot in sorted(shots.glob("shot-*.txt")):
        for line_no, label in _scan_text(shot.read_text(encoding="utf-8"), rules):
            reports.append(f"{shot}:{line_no}:{label}")
    return reports


@register
def check_fingerprint_consistency(drama_dir: Path) -> list[str]:
    shots = _shots_dir(drama_dir)
    if shots is None:
        return []
    fingerprint = _load_json(drama_dir, "形象.json")
    non_empty = [
        v for v in fingerprint.get("主角", {}).values()
        if isinstance(v, str) and v.strip()
    ]
    if not non_empty:
        return []
    reports: list[str] = []
    for shot in sorted(shots.glob("shot-*.txt")):
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


@register
def check_beats_validity(drama_dir: Path) -> list[str]:
    beats = _load_json(drama_dir, "节拍.json")
    reports: list[str] = []
    for entry in beats.get("shots", []):
        beat = entry.get("节拍")
        if beat is None:
            continue
        if beat not in VALID_BEATS:
            reports.append(f"节拍.json:{entry.get('镜号', '?')}:非法节拍({beat})")
    return reports


@register
def check_switches_validity(drama_dir: Path) -> list[str]:
    switches = _load_json(drama_dir, "转场.json")
    reports: list[str] = []
    for entry in switches.get("shots", []):
        switch = entry.get("转场")
        if switch is None:
            continue
        if switch not in VALID_SWITCHES:
            reports.append(f"转场.json:{entry.get('镜号', '?')}:非法转场({switch})")
    return reports


@register
def check_frontmatter_play(drama_dir: Path) -> list[str]:
    return _check_one_frontmatter(drama_dir / "剧本.md", "剧本")


@register
def check_frontmatter_shots(drama_dir: Path) -> list[str]:
    shots = _shots_dir(drama_dir)
    if shots is None:
        return []
    reports: list[str] = []
    for shot in sorted(shots.glob("shot-*.txt")):
        reports.extend(_check_one_frontmatter(shot, "shot"))
    return reports


def _check_one_frontmatter(path: Path, expected_type: str) -> list[str]:
    if not path.exists():
        return [f"{path}:0:frontmatter缺失"]
    try:
        meta, _ = _read_frontmatter(path)
    except Exception as e:
        return [f"{path}:0:frontmatter解析失败({e})"]
    if not meta:
        return [f"{path}:0:frontmatter缺失"]
    actual_type = meta.get("type")
    if actual_type != expected_type:
        return [f"{path}:0:frontmatter type({actual_type}) != {expected_type}"]
    return []


def run_checks(drama_dir: Path) -> list[str]:
    """Run all registered CHECKS; aggregate reports; never throws."""
    out: list[str] = []
    for check in CHECKS:
        try:
            out.extend(check(drama_dir))
        except Exception as e:
            out.append(f"{drama_dir}:0:{check.__name__}() crashed: {e}")
    return out


def self_check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shots_dir = tmp_path / "shots"
        shots_dir.mkdir()

        fingerprint = {
            "主角": {
                "年龄段": "约 25 岁",
                "脸型关键词": "瓜子",
                "发型关键词": "齐耳短发",
                "肤色关键词": "自然黄",
                "身高气质": "沉稳内敛",
            },
            "配角": [],
        }
        beats = {"shots": [{"镜号": 1, "节拍": "期待"}]}
        switches = {"shots": [{"镜号": 1, "转场": "缓切"}]}
        (tmp_path / "形象.json").write_text(json.dumps(fingerprint, ensure_ascii=False), encoding="utf-8")
        (tmp_path / "节拍.json").write_text(json.dumps(beats, ensure_ascii=False), encoding="utf-8")
        (tmp_path / "转场.json").write_text(json.dumps(switches, ensure_ascii=False), encoding="utf-8")
        (tmp_path / "剧本.md").write_text(
            "---\ntype: 剧本\n---\n# body",
            encoding="utf-8",
        )
        (shots_dir / "shot-1.txt").write_text(
            "---\ntype: shot\n---\n"
            "【整体风格 · 节拍：期待】\nTODO\n\n"
            "【镜头 1】\n延续氛围\n\n"
            "【演员本体】\n约 25 岁\n瓜子脸型\n齐耳短发发型\n自然黄肤色\n沉稳内敛气质\n\n"
            "【演员动作】\nTODO\n\n"
            "【运镜节奏】\nTODO\n",
            encoding="utf-8",
        )

        clean = run_checks(tmp_path)
        if clean:
            raise SystemExit(f"self-check FAILED: clean drama produced hits: {clean}")

        (shots_dir / "shot-1.txt").write_text(
            "---\ntype: shot\n---\n参考 No0008 的节奏感。", encoding="utf-8"
        )
        dirty = run_checks(tmp_path)
        if not any("内部编号" in r for r in dirty):
            raise SystemExit("self-check FAILED: dirty shot not detected")

        bad_beats = {"shots": [{"镜号": 1, "节拍": "乱七八糟"}]}
        (tmp_path / "节拍.json").write_text(json.dumps(bad_beats, ensure_ascii=False), encoding="utf-8")
        bad = run_checks(tmp_path)
        if not any("非法节拍" in r for r in bad):
            raise SystemExit("self-check FAILED: invalid beat not detected")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("drama_dir", type=Path, help="短剧目录路径")
    args = parser.parse_args(argv)

    self_check()
    reports = run_checks(args.drama_dir)

    if reports:
        print("\n".join(reports))
        print(f"FAIL ({len(reports)} hits)")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())