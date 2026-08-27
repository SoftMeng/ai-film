#!/usr/bin/env python3
"""二维抽样：从虚拟演员池抽 1 + 从化妆间抽 1。演员与装扮完全解耦。

用法：
  python scripts/select_makeup.py                          # 演员 + 装扮都随机
  python scripts/select_makeup.py 演员=李小喵                # 指定演员
  python scripts/select_makeup.py 装扮=猫神Coser             # 指定装扮
  python scripts/select_makeup.py 演员=李小喵 装扮=猫神Coser   # 都指定
"""

import sys
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parent.parent
ACTORS = ROOT / "虚拟演员"
WARDROBE = ROOT / "化妆间"


def parse_args(argv):
    """解析 演员=xxx 装扮=yyy 参数。无前缀则视为演员名（向后兼容）。"""
    actor = None
    costume = None
    for arg in argv:
        if "=" in arg:
            k, v = arg.split("=", 1)
            if k == "演员":
                actor = v
            elif k == "装扮":
                costume = v
        else:
            actor = actor or arg
    return actor, costume


def list_actors():
    """列出所有演员人设文件（*.md，排除 README.md）。"""
    return sorted(p for p in ACTORS.glob("*.md") if p.stem != "README")


def list_costumes():
    """列出所有装扮文件（*.txt，排除 .DS_Store 与隐藏文件）。"""
    return sorted(
        p for p in WARDROBE.iterdir()
        if p.suffix == ".txt" and not p.name.startswith(".")
    )


def find(items, name):
    """按 stem 精确查找。"""
    for p in items:
        if p.stem == name:
            return p
    return None


def main():
    actor, costume = parse_args(sys.argv[1:])

    if not ACTORS.exists():
        print(f"虚拟演员目录不存在: {ACTORS}", file=sys.stderr)
        sys.exit(1)
    if not WARDROBE.exists():
        print(f"化妆间目录不存在: {WARDROBE}", file=sys.stderr)
        sys.exit(1)

    actors = list_actors()
    costumes = list_costumes()

    if not actors:
        print("虚拟演员池为空", file=sys.stderr)
        sys.exit(1)
    if not costumes:
        print("化妆间为空", file=sys.stderr)
        sys.exit(1)

    # 演员抽样
    if actor:
        actor_path = find(actors, actor)
        if actor_path is None:
            available = ", ".join(p.stem for p in actors)
            print(f"未找到演员: {actor}（可选: {available}）", file=sys.stderr)
            sys.exit(1)
    else:
        actor_path = random.choice(actors)

    # 装扮抽样（与演员完全解耦，可任意搭配）
    if costume:
        costume_path = find(costumes, costume)
        if costume_path is None:
            available = ", ".join(p.stem for p in costumes)
            print(f"未找到装扮: {costume}（可选: {available}）", file=sys.stderr)
            sys.exit(1)
    else:
        costume_path = random.choice(costumes)

    # 输出两行：第一行演员，第二行装扮
    print(actor_path)
    print(costume_path)


if __name__ == "__main__":
    main()
