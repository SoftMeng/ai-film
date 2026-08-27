"""Generate one shot file with fingerprint + beat + transition auto-injected from JSON state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from drama_yaml import dump as yaml_dump

TRANSITION_HINT = {
    "缓切": "延续上一镜的氛围与节奏，运镜速度与上一镜尾保持一致。",
    "硬切": "从上一镜尾的具体动作中途切入，不重复动作过程。",
    "接切": "从上一镜尾视线方向入画或走出。",
}

FIELD_TEMPLATE = {
    "年龄段": "年龄 {value}",
    "脸型关键词": "{value}脸型",
    "发型关键词": "{value}发型",
    "肤色关键词": "{value}肤色",
    "身高气质": "{value}气质",
    "标志特征": "标志：{value}",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_shot(shots: list[dict], idx: int) -> dict | None:
    for s in shots:
        if s.get("镜号") == idx:
            return s
    return None


def render_actor(fingerprint: dict) -> str:
    parts: list[str] = []
    main = fingerprint.get("主角", {})
    for field, value in main.items():
        if value is None or value == "":
            continue
        template = FIELD_TEMPLATE.get(field)
        if template:
            parts.append(template.format(value=value))
        else:
            parts.append(f"{field}：{value}")
    if not parts:
        return "TODO: 形象指纹未填写"
    return "\n".join(parts)


def render_shot(drama_dir: Path, idx: int) -> tuple[Path, str]:
    fingerprint = load_json(drama_dir / "形象.json")
    beats_data = load_json(drama_dir / "节拍.json")
    switches_data = load_json(drama_dir / "转场.json")

    beat_entry = get_shot(beats_data.get("shots", []), idx)
    switch_entry = get_shot(switches_data.get("shots", []), idx)

    beat_name = beat_entry.get("节拍") if beat_entry else None
    switch_name = switch_entry.get("转场") if switch_entry else None
    transition_hint = TRANSITION_HINT.get(switch_name, "TODO: 转场类型未填写")

    actor_lines = render_actor(fingerprint)
    beat_line = beat_name if beat_name else "TODO: 节拍未分配"

    meta = {
        "type": "shot",
        "applicable": drama_dir.name,
        "镜号": idx,
        "节拍": beat_line,
        "转场": switch_name or "TODO",
    }
    body = (
        f"【整体风格 · 节拍：{beat_line}】\n"
        f"TODO: 场景氛围与镜头描述\n\n"
        f"【镜头 {idx}】\n"
        f"{transition_hint}\n\n"
        f"【演员本体】\n{actor_lines}\n\n"
        f"【演员动作】\nTODO: 动作描述\n\n"
        f"【运镜节奏】\nTODO: 运镜描述\n"
    )
    content = yaml_dump(meta, body)

    shots_dir = drama_dir / "shots"
    shots_dir.mkdir(exist_ok=True)
    out_path = shots_dir / f"shot-{idx}.txt"
    out_path.write_text(content, encoding="utf-8")
    return out_path, beat_line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("drama_dir", type=Path, help="短剧目录路径")
    parser.add_argument("shot", type=int, help="镜号 N（>=1）")
    args = parser.parse_args(argv)

    if args.shot < 1:
        raise SystemExit(f"shot must be >= 1, got {args.shot}")

    out_path, beat = render_shot(args.drama_dir, args.shot)
    print(f"created: {out_path}")
    print(f"  镜号: {args.shot}")
    print(f"  节拍: {beat}")
    return 0


if __name__ == "__main__":
    sys.exit(main())