---
name: meteo-power-analyst
description: 气象 × 电力市场分析专家（发电缺口 → 电价 → 负价预警）。Use this skill when: (1) 下载/核对气象数据（数值预报、再分析、卫星、雷达、地面站、探空） (2) 下载/核对电力市场数据（ERCOT、ENTSO-E、Energy-Charts、GEM 机组库） (3) 把气象数据转成光伏/风电出力（pvlib 物理链路、晴空反事实） (4) 识别"发电缺口"并建模其持续时间、可逆性与工况指纹 (5) 标定缺口 → 电价的弹性与转移函数（含尾部尖峰） (6) 建负电价（负价）概率模型与 D-1/D-3 日预警 (7) 做概率预报的校准与样本外检验 (8) 产出单文件 HTML 分析报告 (9) 把本轮研究经验沉淀成知识条目、维护知识库一致性 (10) 不确定该走哪个流程、或要回溯某一轮研究的原始过程时需要分诊导航。
---

# 气象 × 电力市场分析专家（缺口 → 电价 → 负价预警）

主线变量链：**气象 → 发电出力（光伏 / 风电）→ 净负荷与"缺口" → 电价（负价与尖峰）**。
覆盖市场：美国 ERCOT、西班牙、法国、欧洲跨境耦合。

本包采用"渐进披露 · 混合知识库/技能库"三层架构（架构原件见 `raw/FRAMEWORK.md`）：
**能力层 `skills/` 回答"现在就做"；知识层 `kb/` 回答"为什么"；原始材料层 `raw/` 是出土的土壤。**

## 分诊树（先确认手上有什么，再选路径）

```
要做什么 / 手上有什么？
│
├─ 要数据，还没拿到
│   ├─ 气象：数值预报 / 再分析 / 季节预报        → skills/data-fetch-nwp/SKILL.md
│   ├─ 气象：静止卫星 / 闪电 / 降水 / 地形        → skills/data-fetch-satellite/SKILL.md
│   ├─ 气象：地面站 / 辐射实测 / 探空廓线          → skills/data-fetch-ground/SKILL.md
│   ├─ 气象：雷达（NEXRAD / MRMS）                → skills/data-fetch-radar/SKILL.md
│   └─ 电力：电价 / 负荷 / 发电构成 / 机组名录     → skills/data-fetch-power/SKILL.md
│
├─ 手上有气象数据，要变成发电出力
│   └─ 光伏 / 风电出力、晴空反事实（缺口上限）      → skills/pv-power-model/SKILL.md
│
├─ 手上有出力 / 负荷 / 电价，要问"缺口 → 电价"
│   ├─ 缺口多大、能持续多久、可不可逆、什么成因     → skills/shortfall-price/SKILL.md
│   └─ 负价概率、日预警、跨境"区域过剩"通道        → skills/negprice-chain/SKILL.md
│
├─ 手上已有结论，要出报告
│   └─ 单文件 HTML 报告                          → skills/report-builder/SKILL.md
│
├─ 要沉淀经验 / 检查知识库一致性
│   └─ 条目落位、写条、跑 lint                    → skills/kb-capture/SKILL.md
│
├─ 问原理 / 概念（"负价为什么产生""为什么要逐 lead 查同质性"）
│   └─ 查知识层总目录 → kb/catalog.md → 分类 catalog → 单条
│
├─ 要选源 / 想知道某个数据源能不能拿
│   └─ 数据源速查矩阵                            → kb/examples/datasource_matrix.md
│
└─ 要回溯原始过程（"上一轮到底打印了什么、试错了什么"）
    ├─ 不确定查哪份                            → raw/README.md（登记表看"支撑范围"列）
    └─ 逐轮研究流水                            → raw/research-log/（一轮一个文件）
```

⚠️ **入口检查**：问题不涉及气象数据、电力市场或发电出力时，直接说明不适用，不要往下套链路。
⚠️ **raw 层只读且不常读**：raw/ 是保存原始研究记录的土壤，日常分析不读它；引用时只给文件名 + 日期/章节定位，不复述内容。条目与原文冲突时以 raw 原件为准，修正条目后重跑 lint。
⚠️ **数据纪律**：宁可无数据，不可假数据——受限或缺失的数据项在结论中显式标注，不留空猜。

## 能力层状态（诚实标记）

| 工具 | 状态 | 说明 |
|------|------|------|
| skills/data-fetch-nwp | ✅ | Open-Meteo archive / forecast / seasonal / previous-runs、NASA POWER 均跑通 |
| skills/data-fetch-power | ✅ | ERCOT（走 GridStatus）、ENTSO-E、Energy-Charts、GEM 跑通；ESIOS 被 WAF 封锁已弃用 |
| skills/data-fetch-satellite | 🟡 | Himawari / GOES / GK2A / GLM 跑通；FY-4 LMI 与 GPM IMERG 受凭证与入口限制 |
| skills/data-fetch-ground | ✅ | Meteostat / SURFRAD / 探空跑通，含完整性核验 |
| skills/data-fetch-radar | 🟡 | 只含探活与单点验证；正式取数见引用流程 |
| skills/pv-power-model | ✅ | NSRDB 懒读取 + pvlib 链路、晴空反事实、ILR 敏感性跑通 |
| skills/shortfall-price | ✅ | 缺口口径、持续时间、可逆性、指纹、弹性（含尾部）跑通 |
| skills/negprice-chain | ✅ | 西班牙多代模型 + 法国归因 + ES 侧 D-1/D-3 预警跑通，含样本外检验 |
| skills/report-builder | ✅ | 本包全部主题报告由这批脚本产出（单文件 HTML） |
| skills/kb-capture | 🟡 | `kb/kb_lint.py` 可用；"写条目"是人机协作流程，无自动化脚本 |

**脚本迁移说明**：能力层脚本从原仓库机械搬运而来，逻辑已验证；本包 `data/` 与 `output/` 为空的生成目录，首跑需重新取数。
状态升级规则：端到端跑通一次并核验产出后，把 🟡 改 ✅ 并写清用什么数据、什么核验手段；失效时诚实降回 🟡。

## 知识层入口

- 总目录：`kb/catalog.md`（类型定义、领域枚举、统计）
- 五类知识：`kb/methods/` `kb/decisions/` `kb/experiments/` `kb/pitfalls/` `kb/recipes/`
- 速查与样张：`kb/examples/`
- 旧 ID 对照（迁移残留）：`kb/MIGRATION.md`
- 引用格式（能力层 → 知识层，只给 ID 和标题，不复述内容）：

```markdown
> 引用知识（kb/）:
> - `[RCP-20260929-013]` 补齐 ES 侧 NWP：D-1/D-3 西班牙负价日预警
```

## 原始材料层入口（raw/）

| 材料 | 路由场景 |
|------|----------|
| `raw/topics/` | **首选入口**：按话题切分的原始记录（17 个话题，含当时的诉求、研究流水、结论去向、素材缺口） |
| `raw/research-log/` | 时间序流水：整轮完整版的过程记录（打印输出、试错、报错原文） |
| `raw/raw-archive/` | 未加工原件：Trae 会话记忆、项目记忆累计、旧知识变更日志全文 |
| `raw/surveys/` | 外部调研原始笔记（数据源调研、外部基准论文） |
| `raw/FRAMEWORK.md` | 查架构设计（三层结构、五类知识、lint、成熟度） |
| `raw/release-notes_v0.1.0.md` | 早期能力清单（历史存档） |
| `raw/README.md` | 不确定查哪份时看登记表"支撑范围"列 |

> ⚠️ **raw 层仅本地保留，不进版本库**：本层含会话记录与研究流水，实测带过 API key，
> `.gitignore` 已按 `raw/` 整体排除。跨机器同步时它不会跟着走，这是有意的。

## 改动纪律

每次改动知识库或任何 `SKILL.md` 之后，跑一次：

```
python kb/kb_lint.py
```

退出码 0=通过、1=有问题。条目刚起步、尚未被引用时加 `--allow-orphans`。
**漏登记是最危险的问题**——条目在硬盘上但目录没收录，agent 就永远找不到它。
