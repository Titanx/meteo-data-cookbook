# 数据获取 · 地面观测与探空

**状态**: ✅ 可用 — Meteostat 区域机场站、SURFRAD 辐射、**BSRN 全球基准辐射（PANGAEA 匿名）**、怀俄明大学探空廓线均跑通并做过完整性核验。

**用途**: 拉取地面站小时观测、地表辐射实测与探空廓线（含热力指数），
用于交叉验证卫星/再分析口径，以及雷暴与高影响天气的判据构建。

**入口检查**:
1. 先查 `data/` 下是否已有目标站点/年份的 csv（meteostat/、surfrad/、sounding/）
2. 无 → 先跑完整性核验脚本，确认既有数据的缺口模式，再决定补哪些年份

## 选源

| 目标 | 脚本 | 说明 |
|------|------|------|
| 亚洲机场站小时观测 | `references/download_china_airports_2025.py`、`references/download_china_airports_2026.py`、`references/download_east_china_airports_2026.py`、`references/download_japan_additional.py` | 分年份、分区域 |
| 东南亚补充站 | `references/download_east_southeast_asia_2025_2026.py`、`references/download_east_southeast_asia_supplement.py` | 与上者配合补齐覆盖 |
| 美洲机场站 | `references/download_americas_airports_2025_2026.py`、`references/download_uscrn_tx_july2022.py` | 含 USCRN 高质量站点 |
| 失败站点重试 | `references/retry_failed_airports.py` | 只重试，不重拉全部 |
| 地表辐射实测（美国） | `references/surfrad_pipeline.py`、`references/surfrad_assessment.py` | 分钟级辐射，站点少 |
| 地表辐射实测（全球基准） | `references/bsrn_pangaea_pipeline.py` | BSRN via PANGAEA，**匿名**；列结构逐站不同，按文件头解析 |
| 探空廓线 / 热力指数 | `references/download_sounding.py`、`references/download_sounding_parallel.py` | WSGI 口径；并行版用于批量 |
| 完整性核验 | `references/check_data_integrity.py`、`references/check_asia_integrity.py`、`references/check_noaa_isd_frequency.py` | **每次取数后必跑** |
| 实时性探活 | `references/check_meteostat_realtime.py`、`references/check_meteostat_realtime_americas.py`、`references/test_meteostat.py` | 判断站点是否有当期数据 |

## 使用

```powershell
# 依赖（首次）
pip install meteostat pandas numpy requests

# 取数前先看既有数据的缺口模式
python skills/data-fetch-ground/references/check_data_integrity.py

# 按区域拉取
python skills/data-fetch-ground/references/download_americas_airports_2025_2026.py

# 只重试失败站点
python skills/data-fetch-ground/references/retry_failed_airports.py

# BSRN（全球基准辐照，匿名）：先看覆盖矩阵，再按月取
python skills/data-fetch-ground/references/bsrn_pangaea_pipeline.py --coverage
python skills/data-fetch-ground/references/bsrn_pangaea_pipeline.py --list TAT 2026
python skills/data-fetch-ground/references/bsrn_pangaea_pipeline.py --get TAT 2026-08
```

## 产出

| 文件（包根 data/ 下） | 内容 |
|----------------------|------|
| meteostat/<区域>/<年份>/hourly_<ICAO>.csv | 逐站小时观测 |
| surfrad/<station>/*.dat | 分钟级辐射实测 |
| bsrn/<DOI>.txt | BSRN 月度数据集（PANGAEA textfile 原文；**列随站变**，按文件头解析） |
| sounding/*.csv | 探空廓线与热力指数（CAPE / DCAPE 等） |

## 数据源与已知局限

| 数据 | 状态 | 已知限制 |
|------|------|----------|
| Meteostat | ✅ | 区域批量下载有陷阱，见引用知识；站点稀疏区代表性差 |
| SURFRAD | ✅ | 站点极少（仅美国境内若干），只覆盖有限年份 |
| BSRN | ✅ | PANGAEA **匿名可取**（仅 ftp 通道需账号）；**列结构逐站逐年代不同、缺测为空字段、无 QC 列**；时效 1–3 个月；覆盖矩阵"有数据"含探空/臭氧等非辐射 LR |
| 怀俄明大学探空 | ✅ | 接口迁移过 + SSL 需处理；部分站点 WSGI 里没有 CAPE，需从 HTML 抽 |
| USCRN | ✅ | 站点质量高但分布固定 |

## 失败处理

- 批量拉取后**必须跑完整性核验**，否则站点缺失会被静默吞掉（表现为样本量悄悄变小、结论跟着偏）
- 某区域大面积失败 → 先怀疑区域参数写法（见 Meteostat 区域陷阱），不要逐个站点重试
- 探空某个站点取不到 CAPE → 先确认是否走了 HTML 抽取路径，再判定为真的缺测
- 区域分辨率不一致导致跨区比较失真 → 先做标准化再比
- BSRN 解析出一片 NaN → 先确认**该站本该有哪几列**（列结构逐站变，上行辐射未必有），再判缺测；**不要套 SURFRAD 的 `-9999.9` 判据**（BSRN 用空字段）
- BSRN 某站某年"没有数据" → 先分**辐射类 LR（LR0100/0300）**与探空/臭氧 LR，矩阵打勾不等于有辐照

> 引用知识（kb/）:
> - `[MTD-20260718-002]` Meteostat 地面观测数据使用指南
> - `[MTD-20260811-001]` 探空数据热力指数提取与 DCAPE 分析指南
> - `[PIT-20260719-001]` Meteostat 区域数据下载陷阱（中国/亚洲/美洲）
> - `[PIT-20260811-001]` 怀俄明大学探空接口迁移与 SSL 证书问题
> - `[PIT-20260811-002]` 探空数据区域分辨率差异与标准化比较
> - `[PIT-20260811-003]` 探空 WSGI 格式中 CAPE 缺失与 HTML 热力指数提取
> - `[RCP-20260720-002]` SURFRAD 地表辐射实测数据下载流程
> - `[RCP-20260930-001]` BSRN 地表辐照基准实测数据取数流程（PANGAEA 匿名通道）
> - `[RCP-20260811-001]` 探空廓线数据下载流程（怀俄明大学 WSGI）
