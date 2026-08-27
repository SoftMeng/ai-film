"""Create a new short-drama project directory with placeholder JSON / md skeletons."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAMA_ROOT = ROOT / "短剧"

FINGERPRINT_FIELDS = [
    "年龄段",
    "脸型关键词",
    "发型关键词",
    "肤色关键词",
    "身高气质",
    "标志特征",
]

PLAY_SKELETON = """## who

TODO: 主角 + 配角（参考 短剧/形象指纹.md）

## where

TODO: 开篇空间 + 转折空间

## what

TODO: 一句话概括剧情

## feel-arc

TODO: 节拍走向（参考 短剧/情绪节拍库.md）
"""


def next_index() -> int:
    if not DRAMA_ROOT.exists():
        DRAMA_ROOT.mkdir(parents=True, exist_ok=True)
        return 1
    nums: list[int] = []
    for child in DRAMA_ROOT.iterdir():
        if child.is_dir():
            m = re.match(r"^(\d{3})-", child.name)
            if m:
                nums.append(int(m.group(1)))
    return (max(nums) if nums else 0) + 1


def fingerprint_skeleton() -> dict:
    return {"主角": {k: None for k in FINGERPRINT_FIELDS}, "配角": []}


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="短剧名（中文/英文）")
    args = parser.parse_args(argv)

    idx = next_index()
    drama_dir = DRAMA_ROOT / f"{idx:03d}-{args.name}"
    if drama_dir.exists():
        raise SystemExit(f"已存在：{drama_dir}")

    (drama_dir / "shots").mkdir(parents=True)
    write_json(drama_dir / "形象.json", fingerprint_skeleton())
    write_json(drama_dir / "节拍.json", {"shots": []})
    write_json(drama_dir / "转场.json", {"shots": []})
    (drama_dir / "剧本.md").write_text(PLAY_SKELETON, encoding="utf-8")

    print(f"created: {drama_dir}")
    for name in ["形象.json", "节拍.json", "转场.json", "剧本.md", "shots/"]:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())