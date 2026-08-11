# 技术知识清单（跨项目通用）

> 最后更新: 2026-08-11
> 总计: 18 条（全部 verified）

## 最佳实践 (guidelines/)

| ID | 标题 | 成熟度 | 标签 | 适用阶段 | 最后引用 |
|----|------|--------|------|----------|----------|
| GL-004 | Open-Meteo API 使用指南 | verified | openmeteo, api, era5, forecast, free, no-api-key | implement, verify | 2026-07-18 |
| GL-005 | Meteostat 地面观测数据使用指南 | verified | meteostat, observation, surface, station, python, no-api-key, china, batch-download, asia, americas, real-time | implement, verify | 2026-07-20 |
| GL-006 | NASA POWER 卫星同化数据使用指南 | verified | nasa-power, ceres, merra-2, satellite, reanalysis, radiation, ghi, dni, dhi, no-api-key, free | implement, verify | 2026-07-21 |
| GL-007 | 探空数据热力指数提取与 DCAPE 分析指南 | verified | sounding, dcape, cape, thermodynamic, wyoming, wsgi, html-parsing, regex | implement, verify, analyze | 2026-08-11 |

## 已知陷阱 (pitfalls/)

| ID | 标题 | 成熟度 | 标签 | 适用阶段 | 最后引用 |
|----|------|--------|------|----------|----------|
| PF-004 | Meteostat 区域数据下载陷阱（中国/亚洲/美洲） | verified | meteostat, china, asia, americas, station-density, data-gap, radius, icao, myanmar, vietnam | implement, verify | 2026-07-20 |
| PF-005 | ERCOT 官网反爬虫屏蔽与中国 IP 不可访问陷阱 | verified | ercot, texas, electricity, price, imperva, incapsula, anti-scraping, china-ip-block, eia-api, gridstatus | architect, implement | 2026-07-23 |
| PF-006 | Pandas 时区 tz-naive 与 tz-aware 比较错误 | verified | python, pandas, timezone, tz-naive, tz-aware, datetime, multi-source, ercot, meteostat | implement, debug | 2026-07-24 |
| PF-007 | 雷暴检测在高风区绝对阈值失效 | verified | thunderstorm, wind-detection, texas, ercot, meteostat, threshold, spike, high-wind-region | architect, implement | 2026-07-24 |
| PF-008 | 怀俄明大学探空接口迁移与 SSL 证书问题 | verified | sounding, wyoming, ssl, certificate, china-network, server-migration, cgi-deprecated | implement, verify | 2026-08-11 |
| PF-009 | 探空数据区域分辨率差异与标准化比较 | verified | sounding, resolution, high-resolution, standard-level, interpolation, comparison, texas, china | implement, verify, analyze | 2026-08-11 |
| PF-010 | 探空 WSGI 格式中 CAPE 缺失与 HTML 热力指数提取 | verified | sounding, cape, dcape, wsgi, html-parsing, regex, missing-data, thermodynamic | implement, verify | 2026-08-11 |

## 技术流程 (processes/)

| ID | 标题 | 成熟度 | 标签 | 适用阶段 | 最后引用 |
|----|------|--------|------|----------|----------|
| PS-003 | 葵花8/9 卫星数据下载流程 | verified | himawari, satellite, aws-s3, anonymous, noaa, hsd, 葵花, real-time | architect, implement | 2026-07-20 |
| PS-004 | GOES-16/18/19 卫星数据下载流程 | verified | goes, satellite, aws-s3, anonymous, noaa, abi, netcdf, 美洲 | architect, implement | 2026-07-20 |
| PS-005 | SURFRAD 地表辐射实测数据下载流程 | verified | surfrad, noaa, radiation, ghi, dni, dhi, realtime, 实测, 辐照, 匿名访问 | architect, implement | 2026-07-20 |
| PS-006 | ERCOT 电力市场数据下载流程（含 Resource Node） | verified | ercot, texas, electricity, price, spp, dam, rtm, eia-api, gridstatus, lmp, fuel-mix, load, resource-node, wind, solar | architect, implement | 2026-08-06 |
| PS-007 | 雷暴事件 × 电力市场联动分析流程 | verified | thunderstorm, ercot, electricity-price, linkage-analysis, meteostat, load-zone, hub, wind-power, solar, statistical-test | architect, implement, verify | 2026-07-24 |
| PS-008 | 探空廓线数据下载流程（怀俄明大学 WSGI） | verified | sounding, wyoming, wsgi, radiosonde, atmospheric-profile, temperature, humidity, wind, parallel-download | architect, implement | 2026-08-11 |

## 参数清单

| 文件 | 说明 | 条目数 | 最后更新 |
|------|------|--------|----------|
| [nasa_power_params.md](nasa_power_params.md) | NASA POWER 全部 1660 个参数清单 | 1660 | 2026-07-21 |

## 编号索引（GL-001 ~ GL-003, PF-001 ~ PF-003, PS-001 ~ PS-002）

以下编号未使用，保留供未来扩展：

| 编号区间 | 用途 |
|---------|------|
| GL-001 ~ GL-003 | 预留（地面观测/再分析/卫星数据通用指南） |
| PF-001 ~ PF-003 | 预留（通用数据陷阱） |
| PS-001 ~ PS-002 | 预留（通用数据下载流程） |

## 主题分类索引

### 按数据源

| 数据源 | 相关条目 |
|--------|---------|
| Meteostat | [GL-005](guidelines/GL-005.md), [PF-004](pitfalls/PF-004.md) |
| Open-Meteo | [GL-004](guidelines/GL-004.md) |
| NASA POWER | [GL-006](guidelines/GL-006.md) |
| 怀俄明探空 | [GL-007](guidelines/GL-007.md), [PF-008](pitfalls/PF-008.md), [PF-009](pitfalls/PF-009.md), [PF-010](pitfalls/PF-010.md), [PS-008](processes/PS-008.md) |
| Himawari | [PS-003](processes/PS-003.md) |
| GOES | [PS-004](processes/PS-004.md) |
| SURFRAD | [PS-005](processes/PS-005.md) |
| ERCOT | [PS-006](processes/PS-006.md), [PF-005](pitfalls/PF-005.md), [PS-007](processes/PS-007.md) |

### 按处理阶段

| 阶段 | 相关条目 |
|------|---------|
| 架构设计 (architect) | PS-003, PS-004, PS-005, PS-006, PS-007, PS-008, PF-005, PF-007 |
| 实现开发 (implement) | 全部 |
| 验证测试 (verify) | GL-004, GL-005, GL-006, GL-007, PF-004, PF-008, PF-009, PF-010, PS-007, PS-008 |
| 数据分析 (analyze) | GL-007, PF-009, PS-007 |
| 调试修复 (debug) | PF-006 |

### 按通用技术

| 技术 | 相关条目 |
|------|---------|
| Python/pandas | PF-006 |
| 并行下载 | PS-008 |
| 正则表达式 | GL-007, PF-010 |
| CSS 去除 | PF-010 |
| 时区处理 | PF-006 |
| 插值 | PF-009 |
| 统计检验 | PS-007 |
| 反爬虫绕过 | PF-005 |
| SSL 证书 | PF-008 |
| 匿名 AWS S3 | PS-003, PS-004 |