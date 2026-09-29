# 气象 × 电力市场数据实战指南

> **本仓库已切换为三层架构**：能力层 `skills/` + 知识层 `kb/` + 原始材料层 `raw/`，
> 统一收在 **[meteo-power-analyst/](meteo-power-analyst/)** 目录下。
> 旧的 `.knowledge/` 与 `scripts/` 已退役（内容全部迁入新架构，见文末「迁移说明」）。

主线变量链：**气象 → 发电出力（光伏 / 风电）→ 净负荷与"缺口" → 电价（负价与尖峰）**。
覆盖市场：美国 ERCOT、西班牙、法国、欧洲跨境耦合。

## 从哪里开始

| 你的身份 / 目的 | 入口 |
|----------------|------|
| 让 Agent 干活（取数、建模、出报告） | [meteo-power-analyst/SKILL.md](meteo-power-analyst/SKILL.md) — 第 0 层分诊树，按"手上有什么输入"选路径 |
| 人读：了解这个包有什么、怎么用 | [meteo-power-analyst/README.md](meteo-power-analyst/README.md) |
| 查知识（原理 / 决策 / 坑 / 流程） | [meteo-power-analyst/kb/catalog.md](meteo-power-analyst/kb/catalog.md) |
| 看跨话题结论综述（缺口 × 电价链路） | [meteo-power-analyst/kb/CONCLUSIONS.md](meteo-power-analyst/kb/CONCLUSIONS.md) |
| 溯源（当时的过程、打印输出、报错原文） | `meteo-power-analyst/raw/`（**仅本地保留，不进版本库**） |

## 为什么用三层 + 渐进披露

知识总量已经超过 65 条条目、上万行，塞进单个 Skill 会挤占对话上下文，且问"葵花怎么下"时
ERCOT 电价全是噪声。本仓库的做法是：

1. **能力层**：`skills/<能力域>/SKILL.md` 说"现在就做——怎么调、什么参数、产出什么格式"，脚本进同目录 `references/`
2. **知识层**：`kb/` 回答"为什么"——原理（MTD）、决策（DEC）、坑（PIT）、流程（RCP）、样例（examples），
   条目之间用全 ID 互相联结，`kb/kb_lint.py` 兜住引用可达性与索引一致性
3. **原始材料层**：`raw/` 是"土壤"——会话记录、研究流水、外部素材，只读、日常不读

**分界线**：换个实现方式还成立的 → 知识层；跟着实现走的 → 能力层。
渐进披露四层：`SKILL.md` 分诊树 → `skills/*/SKILL.md` → `kb/*/catalog.md` → 单条条目。
这样无论知识长到多少条，单次对话的上下文消耗始终可控。

## 分析链路与报告产物

两条主链路，结论与口径规范统一收在 [kb/CONCLUSIONS.md](meteo-power-analyst/kb/CONCLUSIONS.md)。

**ERCOT 缺口 → 电价**：NSRDB + pvlib 出力建模 → 物理晴空反事实缺口 → RTM 弹性标定 →
尾部尖峰与极端情景 → 季节预报概率化。结论：ERCOT 日尺度"预报桥"不成立（R² 0.016）。

**西班牙负价链（八轮收敛）**：光伏份额阈值（θ≈16%，季节依赖）→ 正午窗口（72% 负价小时落在当地 10–16h）→
跨境区域过剩（FR 同窗口负价小时 corr +0.620）→ 可预报性检验（同期共振而非预报技能）→
NWP 短期预报（法国侧可预报但通道不增益）→ 以持续性为骨架的 D-1 预警（2026 AUC 0.838，概率前 30 日命中率 93.3%）。

| 报告 | 目录（`output/`） | 对应流程 |
|------|------------------|---------|
| NSRDB + pvlib 光伏出力建模验证 | `nsrdb_pvlib_2022-07/` | PS-021 |
| 光伏缺口 × 电价冲击推演 | `pv_event_price_impact_2022-07/` | PS-022 |
| RTM 尾部尖峰弹性与极端场景外推 | `price_tail_elasticity/` | PS-023 |
| 光伏缺口口径统一 | `shortfall_unification/` | PS-024 |
| 缺口持续时间维度 | `shortfall_duration/` | PS-025 |
| 缺口日际/跨日持续时间 | `shortfall_duration_crossday/` | PS-026 |
| 季节预报 → 缺口风险概率化 | `seasonal_shortfall_risk/` | PS-027 |
| 风电缺口 × 电价 | `wind_shortfall_elasticity/` | PS-028 |
| 西班牙电力市场数据源调研 | `espana_esios_survey/` | PS-029 |
| 西班牙光伏最小链路 | `spain_minchain/` | PS-030 |
| 西班牙多年市场区间对比 | `spain_regime/` | PS-031 |
| 缺口成因判据可逆性检验 | `reversibility_shortfall/` | PS-032 |
| 缺口工况指纹 | `shortfall_fingerprint/` | PS-033 |
| 日尺度转移函数与 45 天展望 | `forecast_price_bridge/` | PS-034 |
| 西班牙负价概率季节预报 | `spain_negprice_forecast/` | PS-035 |
| ENTSO-E 官方口径复核 + 2026 样本外 | `spain_entsoe_verification/` | PS-037 |
| 西班牙负价模型 v3 | `spain_negprice_v3/` | PS-038 |
| 西班牙负价"爆发阈值"模型 | `spain_negprice_threshold/` | PS-039 |
| 西班牙负价 · 正午窗口份额 | `spain_negprice_noon/` | PS-040 |
| 西班牙负价 · 跨境结构 ES–FR | `spain_negprice_xborder/` | PS-041 |
| 法国正午负价的可预报化 | `spain_negprice_frforecast/` | PS-042 |
| 用真实 NWP 预报填法国侧 | `spain_negprice_nwpfr/` | PS-043 |
| 补齐 ES 侧 NWP · D-1/D-3 预警 | `spain_negprice_d1warning/` | PS-044 |
| GEM 电站 × ERCOT 电价三层联动 | `gem_ercot_price_analysis/` | PS-016 |
| 45 天季节预报精度核验 | `seasonal_forecast_accuracy/` | PS-017 |
| 数据知识总览（全项目汇总） | `data-knowledge-review/` | 汇总 |

> 表中 `output/` 指仓库根目录下的生成目录（不进版本库）；报告为单文件 HTML，零外部依赖，可直接打开或分发。
> 流程号 PS-0xx 是旧编号，与 kb 条目 ID 的对照见 `meteo-power-analyst/kb/MIGRATION.md`。

## 使用方法

**方式一：用 Coding Agent 打开（推荐）** —— 让 Agent 从 `meteo-power-analyst/SKILL.md` 的分诊树进入，
按需下钻到 skill 与 kb 条目，不必一次性加载全部知识。

**方式二：自己跑脚本**

```powershell
# 基础依赖
pip install requests pandas numpy

# 电力市场 / 建模链路另需
pip install pvlib h5py s3fs statsmodels scipy

# 免凭证连通性自检（换区域前先跑）
python meteo-power-analyst/skills/data-fetch-nwp/references/test_openmeteo.py
```

**方式三：只复用某段代码** —— 直接抄 `meteo-power-analyst/skills/*/references/` 下的脚本；
每个 skill 的 `SKILL.md` 写明了入口检查、产出与失败处理。

## 版本控制与凭据纪律

| 目录 | 是否进版本库 | 说明 |
|------|-------------|------|
| `meteo-power-analyst/skills/`、`kb/` | ✅ | 可复用资产，需跨机器同步 |
| `meteo-power-analyst/raw/` | ❌ | 含会话记录与研究流水，实测带过 API key，整层只留本地 |
| `data/`、`output/` | ❌ | 生成目录，脚本可重建 |

凭据只进 `.env`（已被忽略）或系统环境变量，**禁止硬编码**（教训见 `kb/pitfalls/PIT-20260930-001`）。
提交前跑两道闸门：

```powershell
python meteo-power-analyst/kb/kb_lint.py
python meteo-power-analyst/skills/kb-capture/references/secret_scan.py
```

## 迁移说明

旧结构（`.knowledge/` 知识库 + `scripts/` 脚本目录）已于 2026-09-30 退役，内容去向：

| 旧位置 | 新位置 |
|--------|--------|
| `.knowledge/tech/guidelines` `pitfalls` `processes`（60 条） | `kb/methods` `pitfalls` `recipes`（ID 重编，对照表 `kb/MIGRATION.md`） |
| `.knowledge/conventions/` | `kb/methods/MTD-20260930-001`（数据与知识库约定） |
| `.knowledge/tech/nasa_power_params.md` | `kb/examples/nasa_power_params.md` |
| `.knowledge/tech/catalog.md` 主题索引 | `kb/catalog.md` 的「主题索引」节 |
| `.knowledge/project/conclusions_solar_price.md` + `project/catalog.md` 待办 | `kb/CONCLUSIONS.md` |
| `.knowledge/log.md` | `raw/raw-archive/knowledge-log-legacy.md`（本地） |
| `.knowledge/` 整棵树 | `raw/raw-archive/legacy-knowledge/`（本地存档，保证不丢） |
| `scripts/data_download/` `analysis/`（147 个脚本） | `meteo-power-analyst/skills/*/references/` |

## 相关项目

- [satpy](https://github.com/pytroll/satpy) — 卫星数据处理库（本项目核心工具）
- [meteostat](https://github.com/meteostat/meteostat) — 地面观测数据 Python 库
- [pvlib](https://github.com/pvlib/pvlib-python) — 光伏出力建模库
- [GridStatus](https://github.com/gridstatus/gridstatus) — 美国电力市场数据客户端

## 许可证

MIT License，见 [LICENSE](LICENSE)。
