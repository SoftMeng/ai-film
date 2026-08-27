"""Strong-typed schema for short-drama JSON input."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

VALID_BEATS = {"期待", "紧张", "释放", "留白", "收束"}
VALID_SWITCHES = {"缓切", "硬切", "接切"}


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

    def validate(self) -> None:
        for shot in self.shots:
            if shot.镜号 < 1:
                raise ValueError(f"shot.镜号必须 >= 1")
            if shot.节拍 not in VALID_BEATS:
                raise ValueError(f"shot {shot.镜号}: 非法节拍 {shot.节拍}")
            if shot.转场 not in VALID_SWITCHES:
                raise ValueError(f"shot {shot.镜号}: 非法转场 {shot.转场}")


def from_dict(data: dict) -> DramaConfig:
    """Convert raw JSON dict to DramaConfig, fail-fast on missing keys."""
    characters = data["characters"]
    主角_data = characters["主角"]
    配角_data = characters.get("配角", [])
    return DramaConfig(
        短剧名=data["短剧名"],
        主角=Character(**主角_data),
        配角=[Character(**c) for c in 配角_data],
        scene=data["scene"],
        plot=data["plot"],
        feel_arc=data["feel_arc"],
        shots=[Shot(**s) for s in data["shots"]],
    )


if __name__ == "__main__":
    sample = {
        "短剧名": "测试",
        "characters": {"主角": {"年龄段": "25", "脸型关键词": "瓜子",
                          "发型关键词": "短发", "肤色关键词": "自然黄",
                          "身高气质": "沉稳"}},
        "scene": "x",
        "plot": "y",
        "feel_arc": ["期待"],
        "shots": [{"镜号": 1, "节拍": "期待", "转场": "缓切", "空间": "巷口", "动作": "走"}],
    }
    cfg = from_dict(sample)
    cfg.validate()
    print("schema self-check OK")