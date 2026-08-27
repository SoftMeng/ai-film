---
type: 入口
applicable: 短剧/
tags: [drama, index]
---

## 这是什么

为 ai-film 工程补"短剧"生成机制——让多个 10 秒单镜头不再各自独立，而是拼出有角色、有剧情、有情绪的微短剧。

## 工作流（JSON 主导）

短剧生成不再读 5 个 markdown 拼产物，而是走 JSON 主导端到端：

```
AI 输出 DramaConfig JSON
        ↓
python3 scripts/drama-from-json.py <json>
        ↓
短剧/NNN-<名>/
├── 剧本.md            ← YAML frontmatter (type, scene, plot, feel_arc, tags)
├── 形象.json          ← 主角 + 配角指纹
├── 节拍.json          ← 镜号 → 节拍
├── 转场.json          ← 镜号 → 转场
└── shots/
    ├── shot-1.txt ← YAML frontmatter + 指纹/节拍/转场自动注入
    ├── shot-2.txt
    └── ... ↓
python3 scripts/drama-lint.py <dir>  ← CHECKS 注册表检查
```

## DramaConfig 字段

```python
@dataclass(frozen=True)
class DramaConfig:
    短剧名: str
    主角: Character           # 含 6 字段指纹
    配角: List[Character]
    scene: str
    plot: str
    feel_arc: List[str]      # 5 段：期待/紧张/释放/留白/收束
    shots: List[Shot]        # 含 镜号/节拍/转场/空间/动作/对白
    extras: Dict[str, Any]   # 任意扩展（缺字段 fail-fast，参考 scripts/demo-bestie.json）
```

字段缺失报友好错误（含完整路径），例如：

```
缺少字段 characters.主角.年龄段；参考 scripts/demo-bestie.json
```

## 4 机制文件 + YAML 索引

短剧机制由 4 个机制 markdown + YAML frontmatter 索引构成：

- [`形象指纹`](./形象指纹.md) — 6 字段指纹，全剧 N 镜头共用
- [`剧本层`](./剧本层.md) — 四段式（who/where/what/feel-arc），剧情驱动抽样
- [`情绪节拍库`](./情绪节拍库.md) — 5 节拍 + 弧线选用建议
- [`镜头切换`](./镜头切换.md) — 节拍 → 转场类型（缓切/硬切/接切）

AI 读取这些 markdown 前，先用 `python3 scripts/drama-find.py --tag <tag>` 找相关文件，只 Read 返回的文件。

## 与现有工程的关系

`短剧/` 是 `创意MV/` 的升级路径。现有 10s 单镜头机制（7 维矩阵、Seedance 中文结构、产物脱敏）保持不变；短剧机制建立其上，按需调用。

工程铁律（CLAUDE.md）依然生效：产物对外接口纯净、不读历史文件、多样性靠抽样。

## 不做什么

- 不重写 `创意MV/` 或 `指令/`
- 不新建评分体系（先让机制跑起来，反馈回路留待下一批）
- 不锁死节拍数量、镜头数量、角色数量——保持"机制可扩展"而非"规则收紧"
- 不要求每部短剧都走 5 镜 / 8 镜——3 镜 / 15 镜均可，节拍由故事决定