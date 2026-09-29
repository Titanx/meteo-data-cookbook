# 光伏与风电出力建模

**状态**: ✅ 可用 — NSRDB 懒读取 + pvlib 出力链路、装机清单匹配、晴空反事实与 ILR 敏感性均跑通，
并与地面实测做过交叉验证。

**用途**: 把辐照与气象变量转成机组/区域级发电出力，并给出"如果天气正常应该发多少"的上限，
是缺口识别的上游。

**入口检查**:
1. 先查 `data/` 下是否已有目标区域的辐照提取结果与出力序列（nsrdb/、spain/、ercot/）
2. 无 → 按下方顺序：**先建点位/装机清单，再提辐照，最后转出力**

## 建模链路（按顺序）

| 步骤 | 脚本 | 说明 |
|------|------|------|
| 1. 机组清单与点位 | `references/match_nsrdb_ercot_solar.py`、`references/match_nsrdb_ercot_solar_annual.py` | 把机组坐标匹配到辐照网格 |
| 2. 辐照提取 | `references/download_nsrdb_ercot_july2022.py`、`references/download_nsrdb_uscrn_pixels_july2022.py` | 按像素懒读取，避免全量下载 |
| 3. 辐照 → 出力 | `references/nsrdb_pvlib_power.py`、`references/model_spain_pv_power.py` | pvlib 物理链路 |
| 4. 区域级潜力 | `references/build_ercot_pv_potential.py` | 汇总到区域 |
| 5. **晴空反事实（缺口上限）** | `references/clearsky_counterfactual_2025_2026.py`、`references/build_physical_shortfall_2025_2026.py` | 缺口口径的核心，见引用知识 DEC 条 |
| 6. 敏感性 | `references/ilr_sweep_heatwave.py` | ILR / 高温降额对结论的影响 |
| 7. 多区域工况 | `references/model_spain_pv_regime.py` | 西班牙多年份对比 |
| 8. 外部一致性 | `references/nsrdb_eia_comparison.py`、`references/verify_nsrdb_vs_uscrn_july2022.py`、`references/download_eia_solar_2022.py` | 与 EIA 装机 / 地面实测交叉验证 |
| 9. 环境自检 | `references/test_nsrdb_meta.py`、`references/test_nsrdb_h5coro.py`、`references/test_nsrdb_extract_speed.py`、`references/test_nsrdb_mrms_s2s.py`、`references/verify_temp_fix.py` | 换环境/换版本后先跑 |

## 使用

```powershell
# 依赖（首次）
pip install pvlib pandas numpy h5py s3fs

# NSRDB 环境自检（换机器/换版本后必跑）
python skills/pv-power-model/references/test_nsrdb_meta.py

# 晴空反事实（缺口上限）
python skills/pv-power-model/references/clearsky_counterfactual_2025_2026.py
```

## 产出

| 文件（包根 data/ 下） | 内容 |
|----------------------|------|
| nsrdb/ercot_solar_plants_pixels*.csv | 机组 ↔ 辐照像素映射 |
| nsrdb/*_irradiance_*.nc、ercot_pv_power_*.csv | 提取的辐照与逐时出力 |
| nsrdb/pv_clearsky_hourly_*.csv | 晴空反事实（上限）序列 |
| ercot/shortfall_physical_*.csv | 物理口径缺口 |

## 数据源与已知局限

| 数据 | 状态 | 已知限制 |
|------|------|----------|
| NSRDB | ✅ | 元数据是二进制包，必须先建索引；历史区间未必覆盖最新年份 |
| pvlib | ✅ | 出力强依赖装机侧假设（ILR / 朝向 / 降额），**假设变了结论就变** |
| EIA 装机 | ✅ | 口径与区域运营商自家不同，只能做量级核对 |

## 失败处理

- 出力与实测长期同向偏差 → 先查温度降额与 ILR 假设，再看辐照口径
- 某年数据缺失（NSRDB 区间外）→ 显式标注该年不可用，不做插补外推
- 缺口的绝对值不稳定 → 回去检查装机清单的月度口径，而不是改模型系数

> 引用知识（kb/）:
> - `[DEC-20260930-001]` 缺口口径取"物理晴空反事实"，不取"P95 数据驱动包络"
> - `[MTD-20260720-001]` NASA POWER 卫星同化数据使用指南
> - `[RCP-20260927-002]` NSRDB 太阳辐照度数据 S3 懒读取与 ERCOT 像素定位流程
> - `[RCP-20260927-004]` NSRDB 辐照批量提取与 pvlib 光伏出力建模验证流程
> - `[RCP-20260927-007]` 光伏缺口口径统一：物理晴空反事实 vs P95 数据驱动包络
> - `[RCP-20260928-004]` 风电缺口 × 电价：风功率物理链路与"风光不对称"
