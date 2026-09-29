# 数据获取 · 数值预报与再分析

**状态**: ✅ 可用 — 脚本在原仓库端到端跑通（Open-Meteo archive / forecast / seasonal / previous-runs、NASA POWER）。
本包 `data/` 与 `output/` 为空的生成目录，首跑需重新取数；脚本内路径已对齐到包根。

**用途**: 拉取历史气象真值、短期数值预报（含 D1~D7 逐 lead 归档）与 45 天季节预报，落盘供出力建模与预警链路使用。

**入口检查（避免重复拉取）**:
1. 先查 `data/` 下是否已有目标区域的 npz / csv（如 openmeteo_nwp_*/、openmeteo_seasonal/）→ 有则直接用
2. 无 / 过期 → 按下方"取哪一支"选脚本

## 取哪一支

| 要什么 | 脚本 | 说明 |
|--------|------|------|
| 历史气象真值（再分析归档） | `references/download_spain_ghi_archive.py`、`references/download_france_ghi_archive.py` | 按代表点位批量拉辐照 |
| 短期预报逐小时变量 | `references/download_hrrr_temp_2025_2026.py`、`references/download_hrrr_wind_2025_2026.py`、`references/download_hrrr_temp_july2022.py` | 温度与 80m 风，供光伏/风电链路 |
| **D1~D7 逐 lead 归档** | `references/download_spain_nwp_prevruns.py`、`references/download_france_nwp_prevruns.py` | previous-runs 口径；**必须先做逐 lead 同质性检查** |
| 45 天季节预报（多成员） | `references/download_seasonal_forecast.py`、`references/download_spain_seasonal.py` | 多成员集合；配套 `references/verify_seasonal_vs_gfs.py` 做精度核验 |
| 卫星同化日/小时序列 | `references/download_nasa_power_ercot_pv.py`、`references/test_nasa_power.py` | NASA POWER，免凭证 |
| 日温（按站点） | `references/download_spain_temperature.py` | 西班牙侧历史日温 |
| 连通性与参数自检 | `references/test_openmeteo.py`、`references/test_openmeteo_hrrr.py`、`references/list_power_params.py` | 换区域 / 换变量前先跑 |

## 使用

```powershell
# 依赖（首次）
pip install requests pandas numpy

# 免凭证连通性自检（换区域前先跑）
python skills/data-fetch-nwp/references/test_openmeteo.py

# 拉 ES 侧 D1~D7 逐 lead 归档
python skills/data-fetch-nwp/references/download_spain_nwp_prevruns.py

# 45 天季节预报
python skills/data-fetch-nwp/references/download_spain_seasonal.py
```

## 产出

| 文件（包根 data/ 下） | 内容 |
|----------------------|------|
| openmeteo_nwp_*/es_ghi_archive.npz、fr_ghi_archive.npz | 逐点位历史辐照序列 |
| openmeteo_nwp_*/*_prevruns*.csv | D1~D7 逐 lead 预报归档 |
| openmeteo_seasonal/* | 逐站点 45 天多成员预报（json）与汇总 csv |
| openmeteo_temperature_spain/daily_temp.json | 西班牙日温 |

## 数据源与已知局限

| 数据 | 状态 | 已知限制 |
|------|------|----------|
| Open-Meteo Archive / Forecast | ✅ 跑通 | 再分析网格，**不能当站点实测**；多模式并存，必须显式指定 model |
| Open-Meteo Previous Runs（D1~D7） | ✅ 跑通 | **逐 lead 同质性有陷阱**，见下方引用知识 |
| Open-Meteo Seasonal | ✅ 跑通 | 季节尺度，不可当日尺度用 |
| NASA POWER | ✅ 跑通 | 卫星同化，点位代表性有限 |

## 失败处理

- previous-runs 拉完必做同质性筛查：按 segment 分别统计逐 lead 偏差，**发现早期/后期段符号不一致就把主分析截断到稳定档位**（本项目实践截到 D1~D3）
- 任一站点返回空 → 先跑自检脚本确认接口可达，再逐点重试；不要直接丢掉空点，会静默缩小样本
- 季节预报成员数不足 50 → 报告里标注实际成员数，不做隐含补齐

> 引用知识（kb/）:
> - `[MTD-20260718-001]` Open-Meteo API 使用指南（含 HRRR/GFS 等 NWP 预报）
> - `[MTD-20260720-001]` NASA POWER 卫星同化数据使用指南
> - `[PIT-20260929-003]` 历史预报归档（previous-runs）的逐 lead 同质性陷阱
> - `[MTD-20260907-001]` 气象数据 API 凭证安全管理实践
> - `[RCP-20260916-001]` S2S 季节尺度预报获取与精度核验流程
> - `[DEC-20260930-002]` 负价预警主口径取 ex-ante（可运营），"同期上界"只作诊断
