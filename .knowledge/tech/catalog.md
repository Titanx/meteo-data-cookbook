# 技术知识清单（跨项目通用）

> 最后更新: 2026-09-29
> 总计: 54 条（53 verified + 1 draft）

## 最佳实践 (guidelines/)

| ID | 标题 | 成熟度 | 标签 | 适用阶段 | 最后引用 |
|----|------|--------|------|----------|----------|
| GL-004 | Open-Meteo API 使用指南 | verified | openmeteo, api, era5, forecast, free, no-api-key | implement, verify | 2026-07-18 |
| GL-005 | Meteostat 地面观测数据使用指南 | verified | meteostat, observation, surface, station, python, no-api-key, china, batch-download, asia, americas, real-time | implement, verify | 2026-07-20 |
| GL-006 | NASA POWER 卫星同化数据使用指南 | verified | nasa-power, ceres, merra-2, satellite, reanalysis, radiation, ghi, dni, dhi, no-api-key, free | implement, verify | 2026-07-21 |
| GL-007 | 探空数据热力指数提取与 DCAPE 分析指南 | verified | sounding, dcape, cape, thermodynamic, wyoming, wsgi, html-parsing, regex | implement, verify, analyze | 2026-08-11 |
| GL-008 | 气象雷达数据匿名获取综合指南 | verified | radar, nexrad, rainviewer, iem, gcp, nws, nomads, hrrr, anonymous, ercot, texas | architect, implement | 2026-08-12 |
| GL-009 | 气象数据 API 凭证安全管理实践 | verified | security, credentials, netrc, env, api-key, earthdata, eia, gridstatus, gitignore, best-practice | architect, implement | 2026-09-07 |

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
| PF-011 | NEXRAD 官方 S3 桶匿名访问限制与替代方案 | verified | nexrad, radar, s3, aws, anonymous, access-denied, forbidden, unidata, gcp, alternative | architect, implement | 2026-08-12 |
| PF-012 | CMA 气象数据访问陷阱：CMADaaS 需内网、data.cma.cn API 受限、nmc-met-io 不支持 LMI | verified | cma, cmadaas, data.cma.cn, nmc-met-io, fy4, lmi, vpn, intranet, china, api, authentication, python | architect, implement | 2026-09-07 |
| PF-013 | REE/ESIOS 域名级 WAF 封锁：api.esios.ree.es 全站 403（token 有效也进不去） | verified | esios, ree, spain, imperva, incapsula, waf, anti-scraping, 403, geoblock, china-ip-block, api, token, proxy | architect, implement | 2026-09-29 |
| PF-014 | ENTSO-E / IEC 62325 报文的两处隐藏结构：curveType=A03 压缩 与 A01/A07 合约混装 | verified | entsoe, transparency-platform, iec62325, xml, curvetype, a03, variable-sized-block, forward-fill, contract-market-agreement, a01, a07, day-ahead, intraday, parsing, silent-data-loss, spain | implement, verify, debug | 2026-09-29 |

## 技术流程 (processes/)

| ID | 标题 | 成熟度 | 标签 | 适用阶段 | 最后引用 |
|----|------|--------|------|----------|----------|
| PS-003 | 葵花8/9 卫星数据下载流程 | verified | himawari, satellite, aws-s3, anonymous, noaa, hsd, 葵花, real-time | architect, implement | 2026-07-20 |
| PS-004 | GOES-16/18/19 卫星数据下载流程 | verified | goes, satellite, aws-s3, anonymous, noaa, abi, netcdf, 美洲 | architect, implement | 2026-07-20 |
| PS-005 | SURFRAD 地表辐射实测数据下载流程 | verified | surfrad, noaa, radiation, ghi, dni, dhi, realtime, 实测, 辐照, 匿名访问 | architect, implement | 2026-07-20 |
| PS-006 | ERCOT 电力市场数据下载流程（含 Resource Node） | verified | ercot, texas, electricity, price, spp, dam, rtm, eia-api, gridstatus, lmp, fuel-mix, load, resource-node, wind, solar | architect, implement | 2026-08-06 |
| PS-007 | 雷暴事件 × 电力市场联动分析流程 | verified | thunderstorm, ercot, electricity-price, linkage-analysis, meteostat, load-zone, hub, wind-power, solar, statistical-test | architect, implement, verify | 2026-07-24 |
| PS-008 | 探空廓线数据下载流程（怀俄明大学 WSGI） | verified | sounding, wyoming, wsgi, radiosonde, atmospheric-profile, temperature, humidity, wind, parallel-download | architect, implement | 2026-08-11 |
| PS-009 | NEXRAD 雷达实时分块数据下载流程（unidata chunks） | verified | nexrad, radar, level2, s3, anonymous, unidata, chunks, real-time, texas, ercot, wsr-88d | architect, implement | 2026-08-12 |
| PS-010 | GPM IMERG 降水数据下载流程 | verified | imerg, gpm, precipitation, earthdata, nasa, satellite, 降水, ercot, hdf5, netcdf | architect, implement | 2026-09-07 |
| PS-011 | GOES GLM 闪电数据下载流程 | verified | glm, goes, lightning, satellite, aws-s3, anonymous, noaa, netcdf, 闪电, ercot, texas | architect, implement | 2026-09-07 |
| PS-012 | FY-4A LMI 闪电数据下载流程 | verified | fy4, lmi, lightning, satellite, china, nsmc, netcdf, 闪电, 风云四号, 中国区域 | architect, implement | 2026-09-07 |
| PS-013 | ASTER GDEM 地形与水体数据下载流程 | verified | aster, gdem, wbd, dem, terrain, water-body, earthdata, nasa, lp-daac, rasterio, tiff, ercot, texas | architect, implement | 2026-09-07 |
| PS-014 | ASTER 地形与 GLM 闪电分布联动分析流程 | verified | aster, gdem, wbd, glm, lightning, terrain, elevation, slope, water-body, correlation, ercot, texas, analysis, rasterio, matplotlib | architect, implement, analyze | 2026-09-09 |
| PS-015 | GK2A (GEO-KOMPSAT-2A) AMI 卫星数据下载流程 | verified | gk2a, geo-kompsat-2a, ami, satellite, s3, aws, korea, east-asia, china, geos, netcdf, satpy, himawari, fy-4, cross-validation | architect, implement | 2026-09-11 |
| PS-016 | GEM 电站数据库下载与 ERCOT 电价联动分析流程 | verified | gem, global-energy-monitor, power-plant, wind, solar, ercot, price, lmp, load-zone, correlation, capacity, storm, linkage-analysis, cross-validation | architect, implement, analyze | 2026-09-11 |
| PS-017 | S2S 季节尺度预报获取与精度核验流程（EC46/SEAS5 vs GFS 10天） | verified | s2s, subseasonal, seasonal, ecmwf, ec46, seas5, gfs, ensemble, forecast-accuracy, lead-time, era5, verification, ercot, wind, precip, openmeteo | architect, implement, verify, analyze | 2026-09-16 |
| PS-018 | MRMS 雷达定量降水 (QPE) 下载与 ERCOT 裁剪流程 | verified | mrms, radar, qpe, precipitation, noaa, s3, aws, anonymous, grib2, cfgrib, ercot, texas, multimission, near-realtime | architect, implement, verify, analyze | 2026-09-27 |
| PS-019 | NSRDB 太阳辐照度数据 S3 懒读取与 ERCOT 像素定位流程 | verified | nsrdb, nrel, solar, irradiance, ghi, dni, dhi, goes, h5coro, h5py, fsspec, s3, aws, anonymous, lazy-read, hdf5, ercot, texas, pv | architect, implement, verify, analyze | 2026-09-27 |
| PS-020 | WMO S2S 数据库获取路径（ECDS，多中心延伸期回算） | draft | s2s, wmo, subseasonal, reforecast, hindcast, ecds, ecmwf, ensemble, multi-model, lead-time, verification, openmeteo, ercot | architect, implement | 2026-09-27 |
| PS-021 | NSRDB 辐照批量提取与 pvlib 光伏出力建模验证流程 | verified | nsrdb, pvlib, pvwatts, solar, ghi, dni, dhi, poa, single-axis, tracking, eia-930, ercot, validation, power-modeling, ilr, h5py, fsspec, chunked-extraction | architect, implement, verify, analyze | 2026-09-27 |
| PS-022 | 光伏缺口 × 电价冲击推演流程（晴空反事实 + RTM 弹性标定） | verified | pv, solar, clearsky, counterfactual, shortfall, elasticity, rtm, price, panel-regression, hrrr, temperature, uscrn, ilr, eia-930, ercot, solis, event-attribution | implement, verify, analyze | 2026-09-27 |
| PS-023 | RTM 尾部尖峰弹性标定与极端场景外推（分位数回归 + 凸性检验） | verified | rtm, price, tail, spike, quantile-regression, elasticity, shortfall, pv, extreme-scenario, extrapolation, convexity, logistic, simpson-paradox, hac, ercot, gridstatus, eia-930 | implement, verify, analyze | 2026-09-27 |
| PS-024 | 光伏缺口口径统一：物理晴空反事实 vs P95 数据驱动包络 | verified | pv, solar, shortfall, counterfactual, clearsky, solis, pvlib, envelope, elasticity, rtm, price, simpson-paradox, hrrr, gem, nsrdb, eia-930, ercot, definition-consistency | implement, verify, analyze | 2026-09-27 |
| PS-025 | 光伏缺口的持续时间维度建模（2025/2026 ERCOT，物理晴空反事实口径） | verified | pv, solar, shortfall, duration, persistence, counterfactual, clearsky, rtm, price, multi-hour, physical, ercot | implement, verify, analyze | 2026-09-28 |
| PS-026 | 光伏缺口的日际/跨日持续时间建模（阈值敏感性与连阴聚簇） | verified | pv, solar, shortfall, duration, cross-day, threshold-sensitivity, cloud-streak, price, physical, ercot | implement, verify, analyze | 2026-09-28 |
| PS-027 | 季节预报 → 光伏缺口风险概率化（Open-Meteo Seasonal，50成员） | verified | seasonal, ensemble, openmeteo, ec46, seas5, pv, shortfall, risk, probability, tau, cloud-streak, calibration, ercot | architect, implement, verify, analyze | 2026-09-28 |
| PS-028 | 风电缺口 × 电价：风功率物理链路与"风光不对称"（2025/2026 ERCOT） | verified | wind, wind-power, shortfall, elasticity, hrrr, power-curve, gem, exogenous, endogenous, asymmetry, ercot | implement, verify, analyze | 2026-09-28 |
| PS-029 | 西班牙电力市场数据源调研（ESIOS / OMIE / PVGIS / ENTSO-E） | verified | spain, esios, omie, pvgis, entsoe, market-survey, data-source, negative-price, curtailment, day-ahead | architect, verify | 2026-09-28 |
| PS-030 | 西班牙光伏最小链路（免注册数据源复刻 pvlib 出力建模） | verified | spain, pv, pvlib, nasa-power, energy-charts, omie, ilr, calibration, shortfall, price-elasticity, no-api-key | implement, verify, analyze | 2026-09-28 |
| PS-031 | 西班牙光伏链路多年份市场区间对比（2023 vs 2024 vs 2025） | verified | spain, pv, multi-year, ilr, negative-price, curtailment, shortfall, clearsky-gap, weather-gap, elasticity, regime | implement, verify, analyze | 2026-09-28 |
| PS-032 | 缺口成因判据 · 可逆性检验（ERCOT × 西班牙） | verified | shortfall, causality, reversibility, exogenous, endogenous, panel-regression, two-way-test, wind, solar, ercot, spain | implement, verify, analyze | 2026-09-28 |
| PS-033 | 缺口"工况指纹"：外生 vs 内生（ERCOT × 西班牙） | verified | shortfall, fingerprint, decile, negative-price-frequency, demand, time-of-day, exogenous, endogenous, ercot, spain | implement, verify, analyze | 2026-09-29 |
| PS-034 | 缺口 → 电价：日尺度转移函数与 45 天展望（含"预报桥"可行性判定） | verified | shortfall, price, daily-transfer-function, seasonal-forecast, 45-day, outlook, negative-price, forecability, ercot, spain | architect, implement, verify, analyze | 2026-09-29 |
| PS-035 | 西班牙 负价概率：季节预报链路（未来 45 天） | verified | spain, negative-price, seasonal-forecast, ensemble, s-index, tau, calibration, season-bias, auc, 45-day-outlook | architect, implement, verify, analyze | 2026-09-29 |
| PS-036 | 西班牙 ENTSO-E Transparency 数据链路（替代 ESIOS） | verified | entsoe, transparency-platform, spain, generation-by-type, load, day-ahead-price, eic, iec62325, xml, api, token, proxy, alternative | architect, implement | 2026-09-29 |
| PS-037 | 西班牙链路 · ENTSO-E 官方口径复核 + 2026 样本外检验 | verified | spain, entsoe, official-tsd, cross-validation, out-of-sample, 2026, auc, two-factor, temperature-driven-load, season-bias, negative-price, pot-cs | implement, verify, analyze | 2026-09-29 |
| PS-038 | 西班牙负价模型 v3 · 趋势 / logit / 强度 | verified | spain, negative-price, logit, poisson, intensity, trend, seasonality, brier, reliability, calibration, out-of-sample, scenario-forecast | implement, verify, analyze | 2026-09-29 |
| PS-039 | 西班牙负价"爆发阈值"模型（12 年历史） | verified | spain, negative-price, threshold, hockey-stick, regime-shift, solar-share, penetration, long-panel, seasonal-threshold, scenario-convergence, out-of-sample, energy-charts | implement, verify, analyze | 2026-09-29 |

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
| Open-Meteo | [GL-004](guidelines/GL-004.md), [PS-017](processes/PS-017.md), [PS-022](processes/PS-022.md) |
| NASA POWER | [GL-006](guidelines/GL-006.md) |
| USCRN | **[PS-022](processes/PS-022.md)** |
| 怀俄明探空 | [GL-007](guidelines/GL-007.md), [PF-008](pitfalls/PF-008.md), [PF-009](pitfalls/PF-009.md), [PF-010](pitfalls/PF-010.md), [PS-008](processes/PS-008.md) |
| Himawari | [PS-003](processes/PS-003.md) |
| GOES | [PS-004](processes/PS-004.md) |
| **GOES GLM** | **[PS-011](processes/PS-011.md)** |
| **FY-4 LMI** | **[PS-012](processes/PS-012.md)** |
| **GPM IMERG** | **[PS-010](processes/PS-010.md)** |
| **ASTER GDEM/WBD** | **[PS-013](processes/PS-013.md)** |
| **CMA 数据** | **[PF-012](pitfalls/PF-012.md)** |
| **ESIOS / REE（西班牙电力）** | **[PF-013](pitfalls/PF-013.md)** |
| **ENTSO-E Transparency** | **[PS-036](processes/PS-036.md)**（西班牙链路，免注册但需免费 token）, **[PS-037](processes/PS-037.md)**（官方口径复核 + 2026 样本外）, **[PF-014](pitfalls/PF-014.md)** |
| SURFRAD | [PS-005](processes/PS-005.md) |
| **MRMS QPE** | **[PS-018](processes/PS-018.md)** |
| **NSRDB** | **[PS-019](processes/PS-019.md), [PS-022](processes/PS-022.md), [PS-023](processes/PS-023.md), [PS-024](processes/PS-024.md)** |
| **WMO S2S 库** | **[PS-020](processes/PS-020.md), PS-017** |
| **GridStatus RTM** | **[PS-023](processes/PS-023.md), [PS-024](processes/PS-024.md)** |
| ERCOT | [PS-006](processes/PS-006.md), [PF-005](pitfalls/PF-005.md), [PS-007](processes/PS-007.md), [PS-016](processes/PS-016.md), [PS-022](processes/PS-022.md), [PS-023](processes/PS-023.md), [PS-024](processes/PS-024.md) |
| **GEM 电站数据库** | **[PS-016](processes/PS-016.md), [PS-024](processes/PS-024.md)** |
| **NEXRAD 雷达** | **[GL-008](guidelines/GL-008.md), [PF-011](pitfalls/PF-011.md), [PS-009](processes/PS-009.md)** |
| **凭证安全** | **[GL-009](guidelines/GL-009.md)** |

### 按处理阶段

| 阶段 | 相关条目 |
|------|---------|
| 架构设计 (architect) | PS-003, PS-004, PS-005, PS-006, PS-007, PS-008, PS-009, PS-010, PS-011, PS-012, PS-013, PS-018, PS-019, PS-020, PS-027, PS-029, PS-034, PS-035, PS-036, PF-005, PF-007, PF-011, PF-012, PF-013, GL-008, GL-009 |
| 实现开发 (implement) | 全部 |
| 验证测试 (verify) | GL-004, GL-005, GL-006, GL-007, GL-008, GL-009, PF-004, PF-008, PF-009, PF-010, PF-011, PF-012, PF-014, PS-007, PS-008, PS-009, PS-010, PS-013, PS-018, PS-019, PS-022, PS-023, PS-024, PS-025, PS-026, PS-027, PS-028, PS-029, PS-030, PS-031, PS-032, PS-033, PS-034, PS-035, PS-037, PS-038, PS-039 |
| 数据分析 (analyze) | GL-007, PF-009, PS-007, PS-016, PS-017, PS-018, PS-019, PS-022, PS-023, PS-024, PS-025, PS-026, PS-027, PS-028, PS-030, PS-031, PS-032, PS-033, PS-034, PS-035, PS-037, PS-038, PS-039 |
| 调试修复 (debug) | PF-006, PF-014 |

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
| 反爬虫绕过 | PF-005, PF-013 |
| SSL 证书 | PF-008 |
| 匿名 AWS S3 | PS-003, PS-004, PS-009, PS-018, PS-019, PF-011 |
| GCP 公开数据集 | GL-008 |
| HTTP API | GL-008, GL-004, GL-005 |
| 雷达数据处理 | GL-008, PS-009, PF-011 |
| Earthdata 认证 | GL-009, PS-010, PS-013, PF-012 |
| 凭证安全 | GL-009, PF-012 |
| 地形/水体数据 | PS-013 |
| GRIB2 处理 | PS-018 |
| HDF5 懒读取 (TB级) | PS-019 |
| 电力/光伏建模 | PS-019, PS-021, PS-022, PS-023, PS-024 |
| 统计建模 (面板回归/弹性) | PS-022, PS-023, PS-024 |
| 分位数回归/尾部风险 | PS-023 |
| 口径一致性检验 | PS-024 |
| CMA 数据访问 | PF-012, PS-012 |
| IEC 62325 / 变长块解析 | PF-014, PS-036 |
| 季节/延伸期预报概率化 | PS-017, PS-027, PS-034, PS-035, PS-037, PS-038, PS-039 |
| 样本外检验 / AUC 排序评估 | PS-035, PS-037, PS-038, PS-039 |
| 概率校准评估 (Brier/可靠性) | PS-038 |
| **阈值/结构断点建模** | **PS-039** |
| **长历史面板构建 (12 年)** | **PS-039** |
| 缺口成因与工况识别 | PS-028, PS-031, PS-032, PS-033 |
| 西班牙电力市场链路 | PS-029, PS-030, PS-031, PS-035, PS-036, PS-037, PS-038, PS-039, PF-013 |