# kb/ 知识层总目录 — 气象 × 电力市场分析

知识层回答"**为什么**"：原理、决策理由、坑、流程、样例。
分界线：**换一个实现方式还成立的 → 知识层；跟着实现走的 → 能力层（skills/）**。

## 类型定义

| 类型 | 前缀 | 回答的问题 | 判据 |
|------|------|-----------|------|
| method | MTD | 这个方法为什么成立、什么时候不成立 | 有原理、有局限边界 |
| decision | DEC | 为什么选 A 不选 B | 有当时的前提和被否决的方案 |
| experiment | EXP | 数据上谁更好 | 有可复现配置和对比数字 |
| pitfall | PIT | 什么情况下会踩坑、怎么发现、怎么绕 | 有排查信号 |
| recipe | RCP | 端到端怎么走 | 可勾选的 checklist |

外加 `examples/`（不分级）：回答"具体长什么样"。

> 本包 EXP 为空：模型对比数字都在 recipe 条目的"结论/主结果"节里，与流程强绑定（换流程不可复现），
> 按分层纪律留在流程条目内。DEC 已抽出跨流程反复生效的 3 条。详见 [experiments/catalog.md](experiments/catalog.md)。

## 领域枚举

- **气象要素域**: 太阳辐射（GHI/DNI/云）/ 温度 / 风 / 降水 / 闪电 / 地形
- **时间尺度**: 历史归档（再分析、实测）/ 短期预报（D1~D7）/ 延伸期与季节（15~45 天，多成员）
- **市场域**: 美国 ERCOT / 西班牙 / 法国 / 欧洲跨境耦合
- **变量链（本包主线）**: 气象 → 发电出力（光伏 / 风电）→ 净负荷与"缺口" → 电价（含负价与尖峰）
- **工程域**: 取数 / 面板构建 / 数据体检 / 建模 / 概率校准 / 单文件报告

## 统计（2026-09-30）

| 分类 | 条目数 | 成熟度分布 |
|------|--------|-----------|
| methods (MTD) | 6 | draft 0 / verified 6 / proven 0 |
| recipes (RCP) | 42 | draft 1 / verified 41 / proven 0 |
| decisions (DEC) | 3 | draft 0 / verified 3 / proven 0 |
| pitfalls (PIT) | 13 | draft 0 / verified 13 / proven 0 |
| experiments (EXP) | 0 | — |
| examples | 2 | — |

合计 64 条知识条目 + 2 个样例。其中 60 条由旧仓库知识库的 tech/ 子目录机械迁移而来（对照表见 [MIGRATION.md](MIGRATION.md)），4 条为迁移后新写：3 条决策（DEC-20260930-001~003）与 1 条坑（PIT-20260930-001，凭据硬编码与 raw 层外泄）。

## 分类入口

- [methods/catalog.md](methods/catalog.md)
- [decisions/catalog.md](decisions/catalog.md)
- [recipes/catalog.md](recipes/catalog.md)
- [pitfalls/catalog.md](pitfalls/catalog.md)
- [experiments/catalog.md](experiments/catalog.md)（暂空，见上方说明）
- [examples/README.md](examples/README.md)

## 原始材料层（raw/）

条目与原文冲突时，**以 raw/ 原件为准**，修正条目后重跑 `kb/kb_lint.py`。登记表见 [raw/README.md](../raw/README.md)。

> ⚠️ **raw/ 仅本地保留，不进版本库**：本层含会话记录与研究流水，实测带过 API key，`.gitignore` 已按 `raw/` 整体排除。

| 材料 | 支撑范围 |
|------|----------|
| [../raw/topics/](../raw/topics/) | **按话题切分的原始记录**（17 个话题）：当时的诉求 + 逐轮研究流水 + 结论去向 + 素材缺口 |
| [../raw/research-log/](../raw/research-log/) | 时间序流水：整轮完整版的过程记录（打印输出、试错、报错原文） |
| [../raw/raw-archive/](../raw/raw-archive/) | 未加工原件：Trae 会话记忆、项目记忆累计、旧知识变更日志全文 |
| [../raw/surveys/](../raw/surveys/) | 外部调研原始笔记（数据源调研、外部基准论文） |
| [../raw/FRAMEWORK.md](../raw/FRAMEWORK.md) | 三层架构、五类知识、lint 的架构依据 |
| [../raw/release-notes_v0.1.0.md](../raw/release-notes_v0.1.0.md) | 旧仓库首版能力清单（历史存档） |

## 条目模板

新条目从 `templates/` 拷对应类型模板，命名 `<PREFIX>-<YYYYMMDD>-<NNN>.md`，写完到分类 catalog 登记一行，然后跑 `python kb/kb_lint.py`。

## 维护纪律

- 跨条目引用一律用全 ID 加目录（如 `pitfalls/PIT-20260929-003`），不用简写
- 成熟度：draft（单次经验）→ verified（≥1 次验证）→ proven（≥2 次）；衰减：draft 6 个月未引用归档、verified 9 个月降 draft、proven 12 个月降 verified
- 引用知识只给 ID 和标题，不复述内容（渐进披露）
- 迁移残留：部分条目正文仍写旧式 ID（如"见 PS-035"），对照 [MIGRATION.md](MIGRATION.md) 换算
