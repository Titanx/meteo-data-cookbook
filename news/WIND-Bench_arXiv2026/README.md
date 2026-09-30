# WIND-Bench 论文调研（arXiv 2026）

> 调研日期: 2026-09-27
> 论文: WIND-Bench: A Benchmark Dataset for In-Situ Near-Surface Wind Speed Observations Across the Conterminous United States
> 类型: 基准数据集论文（非模型论文，无复现需求）

## 论文元信息

| 项目 | 内容 |
|------|------|
| 作者 | Kyla Bazlen, Grant Buster*, Brandon Benton, Lauren North, Ansley Baring, David D. Turner, Emily Wells, Laura Vimmerstedt |
| 机构 | NSF ASCEND Engine / National Laboratory of the Rockies (NLR) / NOAA GSL / CIRA |
| 期刊 | arXiv 预印本 2026（arXiv:2609.12228，34 页），正式稿 2026-08 投稿期刊 |
| 通讯 | Grant.Buster@nlr.gov |
| 论文链接 | https://arxiv.org/abs/2609.12228 |
| 本地 PDF | `wind_bench_2609.12228.pdf` (11 MB) |
| 全文提取 | `paper_fulltext.txt`（p23-28 参考文献，p29-34 补充表 S1） |

## 一句话总结

基于 NOAA MADIS 观测网（METAR + Mesonet）构建的 **CONUS 2021-2025 逐小时近地面（1.5-10 m）风速/风向/阵风/温度/相对湿度质量控制基准数据集**，核心创新是**用 HRRR f02 预报替代空间一致性检查做质量控制**——既剔除传感器故障，又保留复杂地形下真实的高风速观测（MADIS L3 会误拒 48% 的高风速观测）。

## 核心数字

| 指标 | 数值 |
|------|------|
| 站点总数（2021-2025 CONUS） | 42,348 个 MADIS 站（单年最多 32,520） |
| 时间范围 | 2021-2025，逐小时 |
| 变量 | 风速、风向、阵风、温度、相对湿度（观测高度 1.5-10 m） |
| 风速物理上限 | 50 m/s（不适用于飓风/龙卷风研究） |
| 高风速保留率（>10 m/s, Colorado 2021） | WIND-Bench 96.7% vs MADIS L3 52.0% |
| Boulder Marshall Fire 风暴（2021-12-30 14MST） | MADIS L3 拒 33/66 站，WIND-Bench 仅拒 4/66 |
| HRRR f02 风速 RMSE（METAR 站） | 1.47-1.92 m/s（按气候区分区域） |
| HRRR f02 风速 MBE | 全 CONUS 系统性高估（METAR +0.39~+0.59，Mesonet 最高 +2.66 m/s） |

## 数据与代码可用性

| 资源 | 链接 | 状态 |
|------|------|------|
| 数据集（OEDI, CC-BY 4.0） | https://data.openei.org/submissions/8729 | 已验证可达 |
| 年度 NetCDF 直链（5 文件共 25.33 GiB） | `https://data.openei.org/files/8729/wind_bench_conus_v1.0.0_{2021..2025}.nc` | 2021: 4.65 GiB, 2022: 4.89 GiB, 2023: 5.17 GiB, 2024: 5.30 GiB, 2025: 5.32 GiB |
| 官方代码（下载/处理/QC 流水线） | https://github.com/NatLabRockies/madis | 网络受限未能 clone，待后续验证 |
| 原始数据归档 | https://madis-data.ncep.noaa.gov/madisPublic1/data/archive | MADIS 公开归档 |

> **单位说明**（2026-09-30 第三方实测更正）：上表数值单位是 **GiB**（1024 进制），原写"GB"会把体积低估约 7%。实测 `Content-Length`：2021 = 4,998,110,374 B = 4.65 GiB（5.00 GB）、2025 = 5,709,140,150 B = 5.32 GiB（5.71 GB）。做磁盘/带宽规划时按 5 GiB/年 ≈ 26 GiB 总量估算。

## 数据格式

- 年度 NetCDF 文件，float32 精度
- 坐标系 WGS 84，时间 UTC
- 站元数据：网络、数据提供者、站型、站号、站名（视可得性）

## 与本项目的关联（ERCOT 风电/光伏分析）

1. **替代/补充 ERA5 作实测基准**：PS-017 用 ERA5 再分析核验 45 天季节预报精度，WIND-Bench 提供真正的地面观测基准（含阵风），且专门解决"高风速被误杀"问题——ERCOT 属 South 气候区（Mesonet 3,416 站 + METAR 383 站），风电大发期的高风速观测对预报核验至关重要。
2. **验证 Open-Meteo HRRR 风速预报**：论文给出 HRRR f02 全 CONUS 分区 RMSE/MBE，可直接对照我们 Open-Meteo HRRR（GL-004）在德州站点的误差量级；其"HRRR 系统性高估 10m 风速"结论对风电出力换算有直接参考价值。
3. **MADIS 成为可用新数据源**：论文证实 MADIS 公开归档可匿名下载且含 Mesonet 子网（RAWS 等），比 Meteostat 机场站密度高一个量级（CONUS 4 万+ 站 vs 85 站）。
4. **质量控制方法论可借鉴**：HRRR 参考预报 + 变点检测（Ruptures）+ MAD 稳健统计的组合，可迁移到我们自有观测数据（SURFRAD/探空/雷达）的 QC。

## 目录内容

| 文件 | 说明 |
|------|------|
| `wind_bench_2609.12228.pdf` | 论文原文（权威来源） |
| `paper_fulltext.txt` | pdfplumber 提取全文 |
| `paper_notes.md` | 精读笔记：数据集构成、QC 流水线、验证结论、关键公式解读 |
| `extract_text.py` | 文本提取脚本 |
| `README.md` | 本文件 |
