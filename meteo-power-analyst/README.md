# meteo-power-analyst — 气象 × 电力市场分析专家包

一个可被 LLM Agent 直接使用的气象 × 电力市场分析技能包：给定气象数据或电力市场数据，
沿 **气象 → 发电出力 → 缺口 → 电价（负价 / 尖峰）** 变量链完成取数、体检、建模、概率校准，
并产出单文件 HTML 报告。

架构采用"渐进披露 · 混合知识库/技能库"三层设计（架构原件见 `raw/FRAMEWORK.md`）。
本包从既有研究仓库（知识库目录 + scripts + data + output 四部分）**机械迁移**而来：
知识条目原样搬运并重编 ID，脚本按能力域归入 10 个 skill，迁移过程与对照表见 `kb/MIGRATION.md`。
**原仓库结构保持不变**，本目录是并列的新架构。

## 它能做什么

- **取数**：数值预报（含 D1~D7 逐 lead 归档）、再分析、45 天季节预报、静止卫星与闪电、雷达、地面站与探空、
  电价与发电构成、机组名录
- **出力建模**：NSRDB 懒读取 + pvlib 物理链路、风功率链路、晴空反事实（缺口上限）、ILR 与温度降额敏感性
- **缺口分析**：口径统一、持续时间（日内 / 跨日）、可逆性判据、工况指纹（外生 vs 内生）
- **缺口 → 电价**：常规段与尾部尖峰弹性标定、日尺度转移函数、45 天展望
- **负价预警**：西班牙 / 法国负价概率模型、跨境"区域过剩"通道、ES 侧 D-1/D-3 日预警、概率校准与样本外检验
- **产出**：单文件 HTML 报告（内嵌图表库与字体，零外部依赖）
- **知识沉淀**：结论、坑、决策、流程、样例分层入库，引用可达性由 lint 兜底

## 三层架构

| 层 | 位置 | 职责 | 读取时机 |
|----|------|------|----------|
| 能力层 | `skills/` | "现在就做"：怎么调、什么参数、产出什么格式 | 按分诊树路由进对应 skill |
| 知识层 | `kb/` | "为什么"：原理、决策理由、坑、流程、样例 | skill 内引用时按需下钻 |
| 原始材料层 | `raw/` | **"出处"：原始研究记录的土壤（流水账、调研笔记、架构说明），只读** | 溯源 / 写新条目 / 怀疑条目记错时 |

```
meteo-power-analyst/
├── SKILL.md                第0层：分诊树（唯一需要通读的路由文件）
├── README.md               本文件
├── data/                   取数产出（生成目录，可重建，不进版本库）
├── output/                 报告产出（单文件 HTML，生成目录）
├── raw/                    原始材料层（只读；**仅本地保留，不进版本库**）
│   ├── README.md              登记表（查哪份材料看这里）
│   ├── topics/                按话题切分的原始记录（17 个话题，本层主体）
│   ├── research-log/          时间序流水（整轮完整版的过程记录）
│   ├── raw-archive/           未加工原件（会话记忆 / 项目记忆 / 旧变更日志）
│   ├── surveys/               外部调研原始笔记
│   ├── FRAMEWORK.md           三层架构与渐进披露说明
│   └── release-notes_v0.1.0.md  早期能力清单（历史存档）
├── skills/                 能力层（10 个）
│   ├── data-fetch-nwp/        数值预报与再分析（Open-Meteo / NASA POWER）
│   ├── data-fetch-satellite/  静止卫星、闪电、降水、地形
│   ├── data-fetch-ground/     地面站、辐射实测、探空
│   ├── data-fetch-radar/      雷达（探活与单点验证）
│   ├── data-fetch-power/      电价、负荷、发电构成、机组名录
│   ├── pv-power-model/        辐照 → 出力、晴空反事实
│   ├── shortfall-price/       缺口识别 → 电价弹性
│   ├── negprice-chain/        负价概率与 D-1/D-3 预警
│   ├── report-builder/        单文件 HTML 报告
│   └── kb-capture/            知识沉淀与 lint
└── kb/                     知识层（63 条）
    ├── catalog.md              总目录（类型/领域/统计）
    ├── kb_lint.py              引用可达性 + 索引一致性检查（七项）
    ├── MIGRATION.md            旧 ID ↔ 新 ID 对照、成熟度冲突、路径改写记录
    ├── methods/ decisions/ experiments/ pitfalls/ recipes/
    ├── examples/               速查矩阵与报告骨架
    └── templates/              新条目空白模板
```

## 版本控制策略

| 层 | 是否进版本库 | 原因 |
|----|-------------|------|
| `skills/` `kb/` | ✅ 进 | 都是可复用资产，需要跨机器同步与评审 |
| `raw/` | ❌ **只留本地** | 含会话记录、研究流水与外部素材，实测**带过 API key**；`.gitignore` 已按 `raw/` 整体排除 |
| `data/` `output/` | ❌ 不进 | 生成目录，脚本可重建 |

**提交前闸门**（顺手跑一下，退出码 1 = 有凭据被跟踪）：

```
python meteo-power-analyst/skills/kb-capture/references/secret_scan.py
```

它做两道检查：① 若存在 `.env`，把其中的值当已知密钥在包内**逐值精确搜索**（零误报，主力检查）；
② 识别常见密钥形态（赋值型长值、URL 里的 token、`EA_`/`sk-`/`ghp_` 等前缀、JWT）。
刻意不把裸的 64 位十六进制当密钥——会话摘要的 `summary_digest` 正是这种形态，会大量误报。

凭据一律走 `.env`（已被忽略），脚本只读环境变量，禁止硬编码。

## 快速开始

**给 Agent 用**（TRAE / Claude Code 等）：把本目录作为技能包加载，从 `SKILL.md` 的分诊树进入——
按"手上有什么输入"选路径，分析流程在 `skills/*/SKILL.md`，原理与坑经 `kb/catalog.md` 逐层下钻。

**手动跑数据**：

```
pip install requests pandas numpy
python skills/data-fetch-nwp/references/test_openmeteo.py   # 免凭证连通性自检
python skills/data-fetch-nwp/references/download_spain_nwp_prevruns.py
```

**检查知识库一致性**（改动任何条目或 SKILL.md 后执行）：

```
python kb/kb_lint.py
```

## 能力层状态

**单一事实源是 [SKILL.md](SKILL.md) 的状态表**（含验证内容与升级/降级规则），此处不重复维护，避免两表漂移。
概览：10 个 skill 中 7 个 ✅、3 个 🟡（卫星侧的凭证受限通道、雷达仅探活、知识沉淀流程无自动化）。

知识层：methods×6 / decisions×3 / pitfalls×12 / recipes×42 / experiments×0 / examples×2，其中 verified 62 条。
代表性条目：

- `DEC-20260930-001` 缺口口径取"物理晴空反事实"，不取"P95 数据驱动包络"
- `DEC-20260930-003` 评预报量效益必须先建持续性基线，且基线不塞冗余日历变量
- `PIT-20260929-003` 历史预报归档（previous-runs）的逐 lead 同质性陷阱
- `RCP-20260929-013` 补齐 ES 侧 NWP：D-1/D-3 西班牙负价日预警
- `RCP-20260927-007` 光伏缺口口径统一：物理晴空反事实 vs P95 数据驱动包络

## 数据源与已知局限

完整的选源矩阵见 `kb/examples/datasource_matrix.md`（含每源的限制与对应坑条目）。要点：

| 数据 | 状态 |
|------|------|
| Open-Meteo（再分析 / 预报 / D1~D7 归档 / 季节） | ✅ 免凭证；归档需做逐 lead 同质性检查 |
| NASA POWER | ✅ 免凭证；卫星同化，点位代表性有限 |
| ERCOT | ✅ 必须走 GridStatus，官网直连不可用 |
| ENTSO-E Transparency | ✅ 需 token；报文有隐藏结构 |
| Energy-Charts (Fraunhofer ISE) | ✅ 免凭证，可做 ENTSO-E 校验口径 |
| ESIOS / REE | ❌ 域名级 WAF 全面 403，已改用 ENTSO-E |
| NSRDB / pvlib | ✅ 出力结论强依赖装机侧假设 |
| 静止卫星（Himawari / GOES / GK2A / GLM） | ✅ 免凭证；FY-4 LMI 与 GPM IMERG 受入口限制 🟡 |
| 雷达（NEXRAD / MRMS） | 🟡 可用性以逐次探活为准 |

纪律：**宁可无数据，不可假数据**——受限或缺失的数据项在结论中显式标注"数据缺失"，不留空猜。

## 知识条目维护约定

- ID：`<PREFIX>-<YYYYMMDD>-<NNN>.md`，前缀 ∈ MTD / DEC / EXP / PIT / RCP
- 成熟度：draft（单次经验）→ verified（≥1 次实际验证）→ proven（≥2 次）
- 衰减：draft 6 个月未引用归档；verified 9 个月降 draft；proven 12 个月降 verified
- 新条目从 `kb/templates/` 拷模板，写完到对应 `catalog.md` 登记一行，然后跑 lint
- 原始研究记录进 `raw/research-log/`，命名 `YYYY-MM-DD_<主题>.md`，**只增不改**

## 启用为 TRAE 技能（可选）

本包默认作为项目资产放在本目录。若希望 TRAE 自动触发：

```
New-Item -ItemType SymbolicLink -Path "c:\Users\44263\.trae-cn\skills\meteo-power-analyst" -Target "<本目录绝对路径>"
```

（Windows 建符号链接需管理员权限；或直接复制整个目录。）

## 免责声明

本包为气象 × 电力市场分析流程的工程化实现，用于研究与学习，不构成任何交易建议。
