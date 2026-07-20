# Release v0.1.0 - 首次发布

**发布日期**: 2026-07-20
**代号**: "First Observations"（首批观测）

## 概述

气象数据下载实战指南首个公开发布版本。5 条知识条目全部基于 2026-07-18~20 的一手实测验证，覆盖卫星数据（葵花 9、GOES-19）和地面观测（Meteostat 246 机场）两大领域，包含 19 个可运行脚本。

## 包含的知识条目

### 最佳实践 (guidelines)

- **GL-004** Open-Meteo API 使用指南
  - 免 API key、ERA5 后端、历史 17 天 + 预报 168h、批量请求模板
  - 2026-07-18 实测验证

- **GL-005** Meteostat 地面观测数据使用指南
  - 246 机场 847 CSV 180.4MB 实测下载
  - 站点 ID 复用策略（3-5x 提速）
  - 逐级扩大半径搜索（中国西部 200km）
  - **小时数据延迟仅 12 分钟**（纠正"1-7 天延迟"旧认知）
  - 中国/亚洲/美洲三区域实测数据

### 已知陷阱 (pitfalls)

- **PF-004** Meteostat 区域数据下载陷阱（中国/亚洲/美洲）
  - 中国站点稀疏（北京 50km 仅 1 站）
  - 缅甸 2026 日数据严重缺失（31-38 天）
  - 越南 3 机场完全无数据（VVNB/VVBM/VVDL）
  - 日本/蒙古/朝鲜数据质量对比
  - 美洲数据质量优于亚洲（85/85 全成功）

### 技术流程 (processes)

- **PS-003** 葵花 8/9 卫星数据下载流程
  - AWS S3 匿名访问（`noaa-himawari9`）
  - FLDK 分段下载（华东区域省 80%）
  - 白天时次选择（UTC 02:00-05:00）
  - HSD → AHI-L1b-FLDK 目录迁移（2026-07-20 确认）
  - satpy 分段处理机制

- **PS-004** GOES-16/18/19 卫星数据下载流程
  - AWS S3 匿名访问（`noaa-goes19`）
  - ABI L1b RadF 产品
  - 真彩色合成（手动 RGB + gamma 2.2，不依赖 pyspectral）
  - C02 降采样避免内存溢出
  - 与 Himawari 对比

## 包含的脚本（19 个）

### 地面观测
| 脚本 | 用途 |
|------|------|
| test_meteostat.py | 单站测试 |
| download_china_airports_2026.py | 中国 46 机场 2026 数据 |
| download_china_airports_2025.py | 中国 46 机场 2025 数据 |
| download_east_china_airports_2026.py | 华东 12 机场 |
| download_east_southeast_asia_2025_2026.py | 东亚东南亚 115 机场 |
| download_east_southeast_asia_supplement.py | 亚洲补充 62 机场 |
| download_japan_additional.py | 日本补充 |
| download_americas_airports_2025_2026.py | 美洲 85 机场 |
| retry_failed_airports.py | 失败重试 |
| check_data_integrity.py | 中国数据完整性检验 |
| check_asia_integrity.py | 亚洲数据完整性检验 |
| check_meteostat_realtime.py | 实时性测试（亚洲） |
| check_meteostat_realtime_americas.py | 实时性测试（美洲） |
| check_noaa_isd_frequency.py | NOAA ISD 频率检验 |

### 卫星数据
| 脚本 | 用途 |
|------|------|
| test_openmeteo.py | Open-Meteo API 测试 |
| test_himawari.py | 葵花基本测试 |
| test_himawari_s3.py | AWS S3 匿名访问测试 |
| himawari9_segment_pipeline.py | 葵花 9 分段下载 + 真彩色 |
| goes19_pipeline.py | GOES-19 全圆盘 + 真彩色 |

## 关键实测数据

| 维度 | 数据 |
|------|------|
| 地面观测覆盖 | 246 机场，16 国，847 CSV，180.4 MB |
| 中国机场成功率 | 46/46 (100%) |
| 亚洲机场成功率 | 108/115 (94%) |
| 美洲机场成功率 | 85/85 (100%) |
| Meteostat 小时数据延迟 | 0.2 小时（12 分钟） |
| 葵花 9 实时性 | 10 分钟间隔，2026-07-20 02:02 UTC 验证 |
| GOES-19 真彩色 | 2026-07-20 01:30 UTC 生成成功 |
| 华东分段下载节省 | 80%（S0210+S0310 vs 全圆盘） |

## 已知限制

- 知识条目数为 5（已删除 13 个 draft 框架）
- 中国西部 Meteostat 站点稀疏，部分机场站点距离 >30km
- 缅甸/越南/东帝汶部分机场数据不完整或缺失
- NOAA ISD 2026 年数据尚未发布（数月延迟）
- 脚本路径假设从 `scripts/data_download/` 目录运行

## 后续计划

- 补充 ERA5 直接下载流程（CDS API）
- 补充 FY-4A/B 风云四号卫星数据下载
- 补充 WRF 数值模式搭建流程
- 将更多 draft 条目验证后发布

## 链接

- 仓库: https://github.com/Titanx/meteo-data-cookbook
- 知识库入口: [.knowledge/tech/catalog.md](.knowledge/tech/catalog.md)
- 问题反馈: https://github.com/Titanx/meteo-data-cookbook/issues
