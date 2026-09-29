# 缺口 × 电价

**状态**: ✅ 可用 — ERCOT 与西班牙两侧的缺口识别、持续时间、可逆性、工况指纹与电价弹性链路均跑通，
含尾部尖峰的分位数标定与极端场景外推。

**用途**: 回答"发电缺口是怎么产生的、能持续多久、可不可逆、对电价冲击多大"，
是"缺口 → 电价"链条的中段。

**入口检查**:
1. **先确认缺口口径**：本包统一用物理口径（晴空反事实 − 实际出力），见引用知识 DEC 条
2. 手上有出力序列与区域电价 → 直接进下方链路
3. 缺装机清单 → 回 `pv-power-model` 先把点位与装机补齐

## 分析链路

| 要回答 | 脚本 | 说明 |
|--------|------|------|
| 缺口有多大（口径统一） | `references/compare_shortfall_definitions.py` | 两种口径对照；**先跑这个** |
| 单次事件影响多大 | `references/identify_pv_drop_events_2022-07.py`、`references/pv_event_price_impact_2022-07.py`、`references/pv_event_price_impact_physical_2022-07.py`、`references/pv_event_price_impact_tail_2022-07.py` | 事件识别 + 电价冲击（逐步换成物理口径 / 尾部口径） |
| 缺口能持续多久 | `references/model_shortfall_duration_2025_2026.py`、`references/model_shortfall_duration_crossday.py` | 日内与跨日两个维度 |
| 成因是外生还是内生 | `references/model_shortfall_fingerprint.py`、`references/reversibility_test_shortfall.py` | 工况指纹 + 可逆性判据 |
| 电价弹性多大 | `references/calibrate_price_elasticity_2025.py`、`references/calibrate_price_elasticity_tail.py` | 常规段 + 尾部尖峰（分位数回归） |
| 缺口 → 电价转移函数 | `references/model_forecast_price_bridge.py` | 含"预报桥"可行性判定 |
| 季节尺度风险 | `references/model_seasonal_shortfall_risk.py` | 45 天展望 |
| 风电侧 | `references/model_wind_power_shortfall.py` | 风功率物理链路（风光不对称） |
| 机组级联动 | `references/gem_ercot_deep_dive.py`、`references/gem_ercot_lz_analysis.py`、`references/gem_storm_cross.py` | 把缺口落到具体机组与分区 |
| 天气成因 | `references/thunderstorm_ercot_analysis.py`、`references/terrain_lightning_analysis.py` | 雷暴/地形与缺口事件的联动 |

## 使用

```powershell
# 依赖（首次）
pip install pandas numpy statsmodels scipy

# 第一步：口径对照（决定后续所有数字）
python skills/shortfall-price/references/compare_shortfall_definitions.py

# 持续时间维度
python skills/shortfall-price/references/model_shortfall_duration_2025_2026.py
```

## 产出

| 文件（包根 data/ 下） | 内容 |
|----------------------|------|
| ercot/shortfall_definition_comparison.csv | 两种缺口口径对照 |
| ercot/shortfall_duration*.csv | 持续时间分布（日内 / 跨日） |
| ercot/shortfall_fingerprint*.csv | 工况指纹特征与汇总 |
| ercot/reversibility_matrix.csv | 可逆性矩阵 |
| ercot/price_elasticity*.csv、forecast_price_outlook.csv | 弹性标定与转移函数输出 |

## 已知局限

- 弹性标定强依赖样本期的极端事件个数：**样本里没有尖峰，就标不出尾部弹性**——此时只报常规段，不硬外推
- 可逆性判据是统计判据，不是物理判据；判"可逆"不等于"一定会恢复"
- 跨年份比较前必须做口径统一，否则"趋势"其实是口径漂移

## 失败处理

- 缺口序列出现大量负值 → 说明口径没统一（实际出力超过物理上限），回去查装机口径与辐照口径
- 弹性系数符号翻转 → 先查是否混入了限电/负价时段，再考虑分样本
- 极端场景外推结果离谱 → 检查凸性检验是否通过；不通过就只报区间不报点值

> 引用知识（kb/）:
> - `[DEC-20260930-001]` 缺口口径取"物理晴空反事实"，不取"P95 数据驱动包络"
> - `[RCP-20260927-005]` 光伏缺口 × 电价冲击推演流程（晴空反事实 + RTM 弹性标定）
> - `[RCP-20260927-006]` RTM 尾部尖峰弹性标定与极端场景外推（分位数回归 + 凸性检验）
> - `[RCP-20260927-007]` 光伏缺口口径统一：物理晴空反事实 vs P95 数据驱动包络
> - `[RCP-20260928-001]` 光伏缺口的持续时间维度建模
> - `[RCP-20260928-002]` 光伏缺口的日际/跨日持续时间维度建模
> - `[RCP-20260928-003]` 季节预报 → 光伏缺口风险概率化
> - `[RCP-20260928-004]` 风电缺口 × 电价：风功率物理链路与"风光不对称"
> - `[RCP-20260929-002]` 缺口"工况指纹"：外生 vs 内生
> - `[RCP-20260928-007]` 缺口成因判据 · 可逆性检验（ERCOT × 西班牙）
> - `[RCP-20260929-003]` 缺口 → 电价：日尺度转移函数与 45 天展望
> - `[RCP-20260724-001]` 雷暴事件 × 电力市场联动分析流程
> - `[RCP-20260911-002]` GEM 电站数据库下载与 ERCOT 电价联动分析流程
> - `[PIT-20260724-002]` 雷暴检测在高风区绝对阈值失效
> - `[RCP-20260909-001]` ASTER 地形与 GLM 闪电分布联动分析流程
