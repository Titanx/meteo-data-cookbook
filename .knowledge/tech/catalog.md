# 技术知识清单（跨项目通用）

## 最佳实践 (guidelines/)

| ID | 标题 | 成熟度 | 标签 | 适用阶段 | 最后引用 |
|----|------|--------|------|----------|----------|
| GL-004 | Open-Meteo API 使用指南 | verified | openmeteo, api, era5, forecast, free | implement, verify | 2026-07-18 |
| GL-005 | Meteostat 地面观测数据使用指南 | verified | meteostat, observation, surface, station, china, batch-download, asia, americas, real-time | implement, verify | 2026-07-20 |

## 已知陷阱 (pitfalls/)

| ID | 标题 | 成熟度 | 标签 | 适用阶段 | 最后引用 |
|----|------|--------|------|----------|----------|
| PF-004 | Meteostat 区域数据下载陷阱（中国/亚洲/美洲） | verified | meteostat, china, asia, americas, station-density, data-gap, myanmar, vietnam | implement, verify | 2026-07-20 |

## 技术流程 (processes/)

| ID | 标题 | 成熟度 | 标签 | 适用阶段 | 最后引用 |
|----|------|--------|------|----------|----------|
| PS-003 | 葵花8/9 卫星数据下载流程 | verified | himawari, satellite, aws-s3, anonymous, noaa, hsd, 葵花, real-time | architect, implement | 2026-07-20 |
| PS-004 | GOES-16/18/19 卫星数据下载流程 | verified | goes, satellite, aws-s3, anonymous, noaa, abi, netcdf, 美洲 | architect, implement | 2026-07-20 |
| PS-005 | SURFRAD 地表辐射实测数据下载流程 | verified | surfrad, noaa, radiation, ghi, dni, dhi, realtime, 实测, 辐照, 匿名访问 | architect, implement | 2026-07-20 |
