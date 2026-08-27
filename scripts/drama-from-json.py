"""Bootstrap a short-drama project from a DramaConfig JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from drama_schema import DramaConfig, from_dict
from drama_yaml import dump as yaml_dump


def _load_module(name: str):
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location(name, Path(__file__).parent / f"{name}.py")
    module = _ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_drama_new = _load_module("drama-new")
next_index = _drama_new.next_index
DRAMA_ROOT = _drama_new.DRAMA_ROOT

_drama_shot = _load_module("drama-shot")
render_shot = _drama_shot.render_shot


def _validate_arc(drama: DramaConfig) -> None:
    beats = [s.节拍 for s in drama.shots]
    if beats != drama.feel_arc:
        raise SystemExit(
            f"feel_arc {drama.feel_arc} 与 shots[].节拍 {beats} 不一致"
        )


def _character_dict(c) -> dict:
    return {
        "年龄段": c.年龄段,
        "脸型关键词": c.脸型关键词,
        "发型关键词": c.发型关键词,
        "肤色关键词": c.肤色关键词,
        "身高气质": c.身高气质,
        "标志特征": c.标志特征,
    }


def _build_dir(drama: DramaConfig) -> Path:
    idx = next_index()
    drama_dir = DRAMA_ROOT / f"{idx:03d}-{drama.短剧名}"
    if drama_dir.exists():
        raise SystemExit(f"已存在：{drama_dir}")
    (drama_dir / "shots").mkdir(parents=True)
    return drama_dir


def _write_state(drama_dir: Path, drama: DramaConfig) -> None:
    (drama_dir / "形象.json").write_text(
        json.dumps(
            {
                "主角": _character_dict(drama.主角),
                "配角": [_character_dict(c) for c in drama.配角],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (drama_dir / "节拍.json").write_text(
        json.dumps(
            {"shots": [{"镜号": s.镜号, "节拍": s.节拍} for s in drama.shots]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (drama_dir / "转场.json").write_text(
        json.dumps(
            {"shots": [{"镜号": s.镜号, "转场": s.转场} for s in drama.shots]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_play_md(drama_dir: Path, drama: DramaConfig) -> None:
    meta = {
        "type": "剧本",
        "applicable": drama_dir.name,
        "scene": drama.scene,
        "plot": drama.plot,
        "feel_arc": drama.feel_arc,
        "tags": ["drama", "play"],
    }
    body = (
        f"## who\n\n"
        f"{drama.主角.年龄段}，{drama.主角.脸型关键词}脸型，"
        f"{drama.主角.发型关键词}，{drama.主角.肤色关键词}，"
        f"{drama.主角.身高气质}。\n\n"
        f"## where\n\n{drama.scene}\n\n"
        f"## what\n\n{drama.plot}\n\n"
        f"## feel-arc\n\n"
        f"{' → '.join(drama.feel_arc)}\n"
    )
    (drama_dir / "剧本.md").write_text(yaml_dump(meta, body), encoding="utf-8")


def _write_shots(drama_dir: Path, drama: DramaConfig) -> list[Path]:
    paths: list[Path] = []
    for shot in drama.shots:
        out_path, _ = render_shot(drama_dir, shot.镜号)
        paths.append(out_path)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path, help="DramaConfig JSON 文件路径")
    args = parser.parse_args(argv)

    data = json.loads(args.json_path.read_text(encoding="utf-8"))
    drama = from_dict(data)
    drama.validate()
    _validate_arc(drama)

    drama_dir = _build_dir(drama)
    _write_state(drama_dir, drama)
    _write_play_md(drama_dir, drama)
    shot_paths = _write_shots(drama_dir, drama)

    print(f"created: {drama_dir}")
    for name in ["形象.json", "节拍.json", "转场.json", "剧本.md"]:
        print(f"  - {name}")
    print(f"  - shots/: {len(shot_paths)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())