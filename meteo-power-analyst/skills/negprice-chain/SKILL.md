# 负价链路（西班牙 / 法国）

**状态**: ✅ 可用 — 西班牙负价的多代模型（趋势 / logit / 强度 / 爆发阈值 / 正午窗口份额 / 跨境耦合）
与法国侧归因均跑通，并完成 2026 样本外检验；ES 侧 D-1/D-3 预警已建成。

**用途**: 建"过剩 → 负价"的概率模型与日预警，输出可运营的 ex-ante 预警概率与可靠性校准。

**入口检查**:
1. **先确认口径**：报预警用 ex-ante；"同期上界"只作诊断，不进运营口径（见引用知识 DEC 条）
2. 先查 `data/` 下是否已有面板（spain/spain_*_panel.csv 等）→ 有则直接从建模脚本开始
3. 无面板 → 按"1. 建面板"顺序走

## 分析链路

### 1. 建面板

| 面板 | 脚本 | 说明 |
|------|------|------|
| 西班牙长历史 | `references/build_spain_long_panel.py` | 12 年跨度，用于阈值与年度趋势 |
| 西班牙正午窗口 | `references/build_spain_noon_panel.py` | 正午机制定位 |
| 西班牙 NWP 面板 | `references/build_spain_nwp_panel.py` | 含 D1~D7 逐 lead，**须先做同质性筛查** |
| 西班牙跨境日量 | `references/build_spain_xborder_daily.py` | ES–FR 耦合 |
| 法国正午面板 | `references/build_france_noon_panel.py` | 法国侧机制 |
| 法国 NWP 面板 | `references/build_france_nwp_panel.py` | 法国侧预报量 |

### 2. 建模（由简到繁，逐代保留）

| 代际 | 脚本 | 说明 |
|------|------|------|
| 基线 | `references/model_spain_negprice_forecast.py` | 持续性骨架 + 基础变量 |
| 线性趋势 | `references/model_spain_negprice_v2.py` | 见引用知识（趋势外推的边界） |
| 趋势 / logit / 强度 | `references/model_spain_negprice_v3.py` | 修前一版的三个遗留问题 |
| 爆发阈值 | `references/model_spain_negprice_threshold.py` | 用阈值替代线性外推 |
| 正午窗口份额 | `references/model_spain_noon_threshold.py` | 机制定位与外推边界 |
| 跨境耦合 | `references/model_spain_negprice_xborder.py` | "区域过剩"通道 |
| 法国侧可预报化 | `references/model_france_noon_neg.py`、`references/model_france_nwp_forecast.py` | 法国归因 + 真实 NWP |
| **ES 侧 D-1/D-3 预警** | `references/model_spain_nwp_warning.py` | 运营口径主产物；含规格对照与概率校准 |

### 3. 官方口径复核

`references/verify_spain_entsoe_official.py` — 用 ENTSO-E 官方口径复核自算负价标记与份额，并做样本外检验。

## 使用

```powershell
# 依赖（首次）
pip install pandas numpy statsmodels scipy

# 建 NWP 面板（内置逐 lead 同质性筛查）
python skills/negprice-chain/references/build_spain_nwp_panel.py

# 运营口径预警
python skills/negprice-chain/references/model_spain_nwp_warning.py
```

## 产出

| 文件（包根 data/ 下） | 内容 |
|----------------------|------|
| spain/spain_*_panel.csv | 各口径日面板 |
| spain/spain_negprice_v3_*.csv | 技能曲线、可靠性、展望、情景 |
| spain/spain_negprice_threshold*.csv | 阈值拟合与预警 |
| spain/spain_nwp_panel.csv | ES 侧含预报量的面板 |
| spain/spain_xborder_*.csv | 跨境模型、系数、相关、负价日均值 |

## 已知局限

- **法国侧信息在短期尺度上已接近用尽**：加真实 NWP 后增益很小，不要期待换更好的 NWP 能大幅提升
- 逐 lead 归档存在同质性断裂，主分析截断在稳定档位（本项目实践 D1~D3）
- 概率模型必须报校准后的可靠性：原始强度输出会系统性偏高，未校准不能直接当概率用
- 稀有事件（负价日）样本极少，任何模型都要给基线对照，否则"技能"其实是季节性

## 失败处理

- 面板里某年负价标记数量突变 → 先查该年数据源是否换过口径，不要当成机制变化
- 样本外指标低于基线 → 默认怀疑基线口径（尤其是塞了冗余日历变量的基线），见引用知识 DEC 条
- 校准后概率与实测频率仍差很远 → 检查是否把"原始强度"当成了概率直接输出

> 引用知识（kb/）:
> - `[DEC-20260930-002]` 负价预警主口径取 ex-ante（可运营），"同期上界"只作诊断
> - `[DEC-20260930-003]` 评预报量效益必须先建持续性基线，且基线不塞冗余日历变量
> - `[PIT-20260929-003]` 历史预报归档（previous-runs）的逐 lead 同质性陷阱
> - `[PIT-20260929-002]` ENTSO-E / IEC 62325 报文的两处隐藏结构
> - `[PIT-20260929-001]` REE/ESIOS 域名级 WAF 封锁
> - `[RCP-20260929-001]` 西班牙电力市场数据源调研
> - `[RCP-20260928-005]` 西班牙光伏最小链路（免注册数据源复刻 pvlib 出力建模）
> - `[RCP-20260928-006]` 西班牙光伏链路多年份市场区间对比
> - `[RCP-20260929-005]` 西班牙 ENTSO-E Transparency 数据链路（替代 ESIOS）
> - `[RCP-20260929-006]` 西班牙链路 · ENTSO-E 官方口径复核 + 样本外检验
> - `[RCP-20260929-007]` 西班牙负价模型 v3 · 趋势 / logit / 强度
> - `[RCP-20260929-008]` 西班牙负价"爆发阈值"模型
> - `[RCP-20260929-009]` 西班牙负价：正午窗口份额 vs 月度份额
> - `[RCP-20260929-010]` 西班牙负价的跨境结构：ES–FR 耦合与"区域过剩"
> - `[RCP-20260929-004]` 西班牙负价概率：季节预报链路（未来 45 天）
> - `[RCP-20260929-011]` 法国正午负价的可预报化
> - `[RCP-20260929-012]` 用真实 NWP 预报填法国侧
> - `[RCP-20260929-013]` 补齐 ES 侧 NWP：D-1/D-3 西班牙负价日预警
