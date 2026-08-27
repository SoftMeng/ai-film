"""Strong-typed schema for short-drama JSON input with friendly error messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

VALID_BEATS = {"期待", "紧张", "释放", "留白", "收束"}
VALID_SWITCHES = {"缓切", "硬切", "接切"}

REQUIRED_TOP_KEYS = {"短剧名", "characters", "scene", "plot", "feel_arc", "shots"}
REQUIRED_CHARACTER_KEYS = {"年龄段", "脸型关键词", "发型关键词", "肤色关键词", "身高气质"}
REQUIRED_SHOT_KEYS = {"镜号", "节拍", "转场", "空间", "动作"}


@dataclass(frozen=True)
class Character:
    年龄段: str
    脸型关键词: str
    发型关键词: str
    肤色关键词: str
    身高气质: str
    标志特征: str = ""


@dataclass(frozen=True)
class Shot:
    镜号: int
    节拍: str
    转场: str
    空间: str
    动作: str
    对白: str = ""


@dataclass(frozen=True)
class DramaConfig:
    短剧名: str
    主角: Character
    配角: List[Character]
    scene: str
    plot: str
    feel_arc: List[str]
    shots: List[Shot]
    extras: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        for shot in self.shots:
            if shot.镜号 < 1:
                raise ValueError(f"shot.镜号必须 >= 1，得到 {shot.镜号}")
            if shot.节拍 not in VALID_BEATS:
                raise ValueError(f"shot {shot.镜号}: 非法节拍 {shot.节拍!r}，合法值 {sorted(VALID_BEATS)}")
            if shot.转场 not in VALID_SWITCHES:
                raise ValueError(f"shot {shot.镜号}: 非法转场 {shot.转场!r}，合法值 {sorted(VALID_SWITCHES)}")


def _missing(dotted_path: str) -> ValueError:
    return ValueError(
        f"缺少字段 {dotted_path}；参考 scripts/demo-deepnight.json"
    )


def from_dict(data: dict) -> DramaConfig:
    """Convert raw JSON dict to DramaConfig; fail-fast with friendly path messages."""
    if not isinstance(data, dict):
        raise _missing("顶层必须是 JSON object")

    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            raise _missing(key)

    characters = data["characters"]
    if not isinstance(characters, dict):
        raise _missing("characters (object)")
    if "主角" not in characters:
        raise _missing("characters.主角")

    主角_data = characters["主角"]
    if not isinstance(主角_data, dict):
        raise _missing("characters.主角 (object)")
    for k in REQUIRED_CHARACTER_KEYS:
        if k not in 主角_data:
            raise _missing(f"characters.主角.{k}")

    配角_data = characters.get("配角", [])
    if not isinstance(配角_data, list):
        raise _missing("characters.配角 (array)")
    for i, c in enumerate(配角_data):
        if not isinstance(c, dict):
            raise _missing(f"characters.配角[{i}] (object)")

    shots = data["shots"]
    if not isinstance(shots, list) or not shots:
        raise _missing("shots (非空 array)")
    for i, s in enumerate(shots):
        if not isinstance(s, dict):
            raise _missing(f"shots[{i}] (object)")
        for k in REQUIRED_SHOT_KEYS:
            if k not in s:
                raise _missing(f"shots[{i}].{k}")

    feel_arc = data["feel_arc"]
    if not isinstance(feel_arc, list):
        raise _missing("feel_arc (array)")

    schema_keys = REQUIRED_TOP_KEYS
    extras = dict(data.get("extras", {}))
    for k, v in data.items():
        if k not in schema_keys and k != "extras":
            extras[k] = v

    return DramaConfig(
        短剧名=data["短剧名"],
        主角=Character(**主角_data),
        配角=[Character(**c) for c in 配角_data],
        scene=data["scene"],
        plot=data["plot"],
        feel_arc=feel_arc,
        shots=[Shot(**s) for s in shots],
        extras=extras,
    )


if __name__ == "__main__":
    sample = {
        "短剧名": "测试",
        "characters": {
            "主角": {
                "年龄段": "25",
                "脸型关键词": "瓜子",
                "发型关键词": "短发",
                "肤色关键词": "自然黄",
                "身高气质": "沉稳",
            }
        },
        "scene": "x",
        "plot": "y",
        "feel_arc": ["期待"],
        "shots": [{"镜号": 1, "节拍": "期待", "转场": "缓切", "空间": "巷口", "动作": "走"}],
    }
    cfg = from_dict(sample)
    cfg.validate()
    if cfg.extras != {}:
        raise SystemExit(f"self-check FAILED: extras expected empty, got {cfg.extras}")

    extras_input = dict(sample, extras={"系列": "test", "custom": 1})
    cfg2 = from_dict(extras_input)
    if cfg2.extras != {"系列": "test", "custom": 1}:
        raise SystemExit(f"self-check FAILED: extras mismatch: {cfg2.extras}")

    bad = dict(sample)
    del bad["feel_arc"]
    try:
        from_dict(bad)
        raise SystemExit("self-check FAILED: missing field not detected")
    except ValueError as e:
        if "feel_arc" not in str(e):
            raise SystemExit(f"self-check FAILED: unexpected msg: {e}")

    print("schema self-check OK")