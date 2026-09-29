# kb/examples/ — 样例与速查（不分级）

回答"**具体长什么样**"。
不是可执行流程（那是 recipes/），也不是原理（那是 methods/），而是**可以直接照抄的形状**：速查矩阵、报告骨架、字段样张。

本目录**不参与成熟度分级**，只计入条目数。样例会随项目演进更新，因此每个文件顶部标"最后同步"日期。

## 收录判据

- 形状是"表 / 骨架 / 字段样张"，而不是一段推导（→ methods/）或一套流程（→ recipes/）
- 被至少一个 skill 或条目引用；没人引用的孤立样张请放 raw/，不要放这里
- 会随项目演进变化 → 顶部标"最后同步"

## 登记表

| 文件 | 说明 | 支撑范围 |
|------|------|----------|
| [datasource_matrix.md](datasource_matrix.md) | 数据源速查矩阵：变量 / 获取方式 / 凭证 / 已知限制 | 各 data-fetch-* skill 选源；限制列直接引用 PIT 条目 |
| [report_outline_standard.md](report_outline_standard.md) | 标准分析报告骨架：章节顺序 + 每节要素 + 交付校验项 | skills/report-builder |

## 使用规则

- 新增样例：放本目录 → 在登记表加一行 → 同步 `kb/catalog.md` 的 examples 计数 → 跑 `python kb/kb_lint.py`
- 样例与条目冲突时，**以条目 + raw/ 原件为准，改样例不改条目**
- 本目录不放脚本；脚本一律进 `skills/*/references/`
