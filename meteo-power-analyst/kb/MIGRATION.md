# MIGRATION.md — 旧 knowledge 条目 ↔ 新 kb/ 条目对照

本包的 kb 条目由 `c:\work\meteo\.knowledge\tech\` 迁移而来（2026-09-30）。
迁移为**机械搬运**：正文原样保留，仅转写 frontmatter 并重编 ID；
条目正文内出现的旧式 ID（如「见 PS-035」）未改写，按本表对照。

| 旧 ID | 新 ID | 类型 | 标题 |
|-------|-------|------|------|
| GL-004 | `methods/MTD-20260718-001` | method | Open-Meteo API 使用指南（含 HRRR/GFS 等 NWP 预报） |
| GL-005 | `methods/MTD-20260718-002` | method | Meteostat 地面观测数据使用指南 |
| GL-006 | `methods/MTD-20260720-001` | method | NASA POWER 卫星同化数据使用指南 |
| GL-007 | `methods/MTD-20260811-001` | method | 探空数据热力指数提取与 DCAPE 分析指南 |
| GL-008 | `methods/MTD-20260812-001` | method | 气象雷达数据匿名获取综合指南 |
| GL-009 | `methods/MTD-20260907-001` | method | 气象数据 API 凭证安全管理实践 |
| PF-004 | `pitfalls/PIT-20260719-001` | pitfall | Meteostat 区域数据下载陷阱（中国/亚洲/美洲） |
| PF-005 | `pitfalls/PIT-20260723-001` | pitfall | ERCOT 官网反爬虫屏蔽与中国 IP 不可访问陷阱 |
| PF-006 | `pitfalls/PIT-20260724-001` | pitfall | Pandas 时区 tz-naive 与 tz-aware 比较错误 |
| PF-007 | `pitfalls/PIT-20260724-002` | pitfall | 雷暴检测在高风区绝对阈值失效 |
| PF-008 | `pitfalls/PIT-20260811-001` | pitfall | 怀俄明大学探空接口迁移与 SSL 证书问题 |
| PF-009 | `pitfalls/PIT-20260811-002` | pitfall | 探空数据区域分辨率差异与标准化比较 |
| PF-010 | `pitfalls/PIT-20260811-003` | pitfall | 探空 WSGI 格式中 CAPE 缺失与 HTML 热力指数提取 |
| PF-011 | `pitfalls/PIT-20260812-001` | pitfall | NEXRAD 官方 S3 桶匿名访问限制与替代方案 |
| PF-012 | `pitfalls/PIT-20260907-001` | pitfall | CMA 气象数据访问陷阱：CMADaaS 需内网、data.cma.cn API 受限、nmc-met-io 不支持 LMI |
| PF-013 | `pitfalls/PIT-20260929-001` | pitfall | REE/ESIOS 域名级 WAF 封锁：api.esios.ree.es 全站 403（token 有效也进不去） |
| PF-014 | `pitfalls/PIT-20260929-002` | pitfall | ENTSO-E / IEC 62325 报文的两处隐藏结构：curveType=A03 压缩 与 A01/A07 合约混装 |
| PF-015 | `pitfalls/PIT-20260929-003` | pitfall | 历史预报归档（previous-runs）的逐 lead 同质性陷阱 |
| PS-003 | `recipes/RCP-20260718-001` | recipe | 葵花8/9 卫星数据下载流程 |
| PS-004 | `recipes/RCP-20260720-001` | recipe | GOES-16/18/19 卫星数据下载流程 |
| PS-005 | `recipes/RCP-20260720-002` | recipe | SURFRAD 地表辐射实测数据下载流程 |
| PS-006 | `recipes/RCP-20260723-001` | recipe | ERCOT 电力市场数据下载流程 |
| PS-007 | `recipes/RCP-20260724-001` | recipe | 雷暴事件 × 电力市场联动分析流程 |
| PS-008 | `recipes/RCP-20260811-001` | recipe | 探空廓线数据下载流程（怀俄明大学 WSGI） |
| PS-009 | `recipes/RCP-20260812-001` | recipe | NEXRAD 雷达实时分块数据下载流程（unidata chunks） |
| PS-010 | `recipes/RCP-20260907-001` | recipe | GPM IMERG 降水数据下载流程 |
| PS-011 | `recipes/RCP-20260907-002` | recipe | GOES GLM 闪电数据下载流程 |
| PS-012 | `recipes/RCP-20260907-003` | recipe | FY-4A LMI 闪电数据下载流程 |
| PS-013 | `recipes/RCP-20260907-004` | recipe | ASTER GDEM 地形与水体数据下载流程 |
| PS-014 | `recipes/RCP-20260909-001` | recipe | ASTER 地形与 GLM 闪电分布联动分析流程 |
| PS-015 | `recipes/RCP-20260911-001` | recipe | GK2A (GEO-KOMPSAT-2A) AMI 卫星数据下载流程 |
| PS-016 | `recipes/RCP-20260911-002` | recipe | GEM 电站数据库下载与 ERCOT 电价联动分析流程 |
| PS-017 | `recipes/RCP-20260916-001` | recipe | S2S 季节尺度预报获取与精度核验流程（EC46/SEAS5 vs GFS 10天） |
| PS-018 | `recipes/RCP-20260927-001` | recipe | MRMS 雷达定量降水 (QPE) 下载与 ERCOT 裁剪流程 |
| PS-019 | `recipes/RCP-20260927-002` | recipe | NSRDB 太阳辐照度数据 S3 懒读取与 ERCOT 像素定位流程 |
| PS-020 | `recipes/RCP-20260927-003` | recipe | WMO S2S 数据库获取路径（ECDS，多中心延伸期回算） |
| PS-021 | `recipes/RCP-20260927-004` | recipe | NSRDB 辐照批量提取与 pvlib 光伏出力建模验证流程 |
| PS-022 | `recipes/RCP-20260927-005` | recipe | 光伏缺口 × 电价冲击推演流程（晴空反事实 + RTM 弹性标定） |
| PS-023 | `recipes/RCP-20260927-006` | recipe | RTM 尾部尖峰弹性标定与极端场景外推（分位数回归 + 凸性检验） |
| PS-024 | `recipes/RCP-20260927-007` | recipe | 光伏缺口口径统一：物理晴空反事实 vs P95 数据驱动包络 |
| PS-025 | `recipes/RCP-20260928-001` | recipe | 光伏缺口的持续时间维度建模（2025/2026 ERCOT，物理晴空反事实口径） |
| PS-026 | `recipes/RCP-20260928-002` | recipe | 光伏缺口的日际/跨日持续时间维度建模（2025/2026 ERCOT，物理晴空反事实） |
| PS-027 | `recipes/RCP-20260928-003` | recipe | 季节预报 → 光伏缺口风险概率化（Open-Meteo Seasonal，未来45天，50成员） |
| PS-028 | `recipes/RCP-20260928-004` | recipe | 风电缺口 × 电价：风功率物理链路与"风光不对称"（2025/2026 ERCOT） |
| PS-029 | `recipes/RCP-20260929-001` | recipe | 西班牙电力市场数据源调研（ESIOS / OMIE / PVGIS / ENTSO-E） |
| PS-030 | `recipes/RCP-20260928-005` | recipe | 西班牙光伏最小链路（免注册数据源复刻 pvlib 出力建模） |
| PS-031 | `recipes/RCP-20260928-006` | recipe | 西班牙光伏链路多年份市场区间对比（2023 vs 2024 vs 2025） |
| PS-032 | `recipes/RCP-20260928-007` | recipe | 缺口成因判据 · 可逆性检验（ERCOT × 西班牙） |
| PS-033 | `recipes/RCP-20260929-002` | recipe | 缺口"工况指纹"：外生 vs 内生（ERCOT × 西班牙） |
| PS-034 | `recipes/RCP-20260929-003` | recipe | 缺口 → 电价：日尺度转移函数与 45 天展望（含"预报桥"可行性判定） |
| PS-035 | `recipes/RCP-20260929-004` | recipe | 西班牙 负价概率：季节预报链路（未来 45 天） |
| PS-036 | `recipes/RCP-20260929-005` | recipe | 西班牙 ENTSO-E Transparency 数据链路（替代 ESIOS） |
| PS-037 | `recipes/RCP-20260929-006` | recipe | 西班牙链路 · ENTSO-E 官方口径复核 + 2026 样本外检验 |
| PS-038 | `recipes/RCP-20260929-007` | recipe | 西班牙负价模型 v3 · 趋势 / logit / 强度（修 PS-037 的三个遗留问题） |
| PS-039 | `recipes/RCP-20260929-008` | recipe | 西班牙负价"爆发阈值"模型（12 年历史，替代线性趋势外推） |
| PS-040 | `recipes/RCP-20260929-009` | recipe | 西班牙负价：正午窗口份额 vs 月度份额（机制定位与外推边界） |
| PS-041 | `recipes/RCP-20260929-010` | recipe | 西班牙负价的跨境结构：ES–FR 耦合与"区域过剩" |
| PS-042 | `recipes/RCP-20260929-011` | recipe | 法国正午负价的可预报化："区域过剩"能预报吗？ |
| PS-043 | `recipes/RCP-20260929-012` | recipe | 用真实 NWP 预报填法国侧：短期（D-1~D-7）能恢复"区域过剩"通道吗？ |
| PS-044 | `recipes/RCP-20260929-013` | recipe | 补齐 ES 侧 NWP：D-1/D-3 西班牙负价日预警能建起来吗？ |

## 迁移时发现的成熟度冲突（已按索引取值）

| 条目 | 正文头声明 | 旧索引 tech/catalog.md 声明 | 取值 |
|------|-----------|--------------------------|------|
| PS-012 | draft | verified | **verified** |

处置：以索引为准（索引是本项目维护的权威成熟度来源）；
迁移后条目正文头仍保留原声明，属已知的原文残留，后续修订条目时应同步。

## 迁移时的路径改写（保证包内自洽）

| 条目 | 处理 | 原写法 |
|------|------|--------|
| GL-004 | 改为纯文本 | data/openmeteo_hrrr_results.json（原文为行内代码写法） |
| GL-004 | 链接改为纯文本 | processes/PS-017.md（原文为行内代码写法） |
| GL-005 | 改为纯文本 | data/meteostat/china_2025/（原文为行内代码写法） |
| GL-005 | 改为纯文本 | data/meteostat/china_2026/（原文为行内代码写法） |
| GL-006 | 改为纯文本 | .knowledge/tech/nasa_power_params.md（原文为行内代码写法） |
| GL-006 | 改为纯文本 | data/surfrad/bon25182.dat（原文为行内代码写法） |
| GL-007 | 改为纯文本 | analysis/sounding_station_stats.csv（原文为行内代码写法） |
| GL-007 | 改为纯文本 | analysis/sounding_timeseries.csv（原文为行内代码写法） |
| GL-007 | 改为纯文本 | analysis/sounding_deep_analysis.html（原文为行内代码写法） |
| GL-007 | 链接改为纯文本 | pitfalls/PF-008.md（原文为行内代码写法） |
| GL-007 | 链接改为纯文本 | pitfalls/PF-009.md（原文为行内代码写法） |
| GL-007 | 链接改为纯文本 | pitfalls/PF-010.md（原文为行内代码写法） |
| GL-007 | 链接改为纯文本 | processes/PS-008.md（原文为行内代码写法） |
| PF-005 | 改为纯文本 | electricity/rto/（原文为行内代码写法） |
| PF-008 | 链接改为纯文本 | ../processes/PS-008.md（原文为行内代码写法） |
| PF-008 | 链接改为纯文本 | ../guidelines/GL-007.md（原文为行内代码写法） |
| PF-009 | 链接改为纯文本 | ../processes/PS-008.md（原文为行内代码写法） |
| PF-009 | 链接改为纯文本 | ../guidelines/GL-007.md（原文为行内代码写法） |
| PF-010 | 链接改为纯文本 | ../guidelines/GL-007.md（原文为行内代码写法） |
| PF-010 | 链接改为纯文本 | ../processes/PS-008.md（原文为行内代码写法） |
| PF-013 | 改为纯文本 | data/esios/（原文为行内代码写法） |
| PF-015 | 改为纯文本 | project/catalog.md（原文为行内代码写法） |
| PS-003 | 改为纯文本 | 0600/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | 0610/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | 0620/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | AHI-L1b-FLDK/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | AHI-L1b-Japan/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | AHI-L1b-Target/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | AHI-L2-FLDK-Clouds/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | AHI-L2-FLDK-ISatSS/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | AHI-L2-FLDK-RainfallRate/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | AHI-L2-FLDK-SST/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | AHI-L2-FLDK-Winds/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | data/himawari/（原文为行内代码写法） |
| PS-003 | 改为纯文本 | satpy/readers/core/yaml_reader.py（原文为行内代码写法） |
| PS-003 | 改为纯文本 | data/himawari/HS_H08_20251126_0000_B01_FLDK_R10_S0110.DAT.bz2（原文为行内代码写法） |
| PS-004 | 改为纯文本 | ABI-L1b-RadF/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | ABI-L1b-RadC/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | ABI-L1b-RadM/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | ABI-L2-ACM/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | ABI-L2-ACHA/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | ABI-L2-AOD/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | ABI-L2-FDCC/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | GLM-L2-LCFA/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | data/goes19/scan_20260720_013019/（原文为行内代码写法） |
| PS-004 | 改为纯文本 | AHI-L1b-FLDK/（原文为行内代码写法） |
| PS-005 | 改为纯文本 | realtime/{station}/（原文为行内代码写法） |
| PS-005 | 改为纯文本 | {station}/{YYYY}/（原文为行内代码写法） |
| PS-005 | 改为纯文本 | data/surfrad/（原文为行内代码写法） |
| PS-006 | 改为纯文本 | electricity/rto/region-data/data/（原文为行内代码写法） |
| PS-006 | 改为纯文本 | electricity/rto/fuel-type-data/data/（原文为行内代码写法） |
| PS-007 | 改为纯文本 | data/meteostat/americas/{year}/hourly_{ICAO}.csv（原文为行内代码写法） |
| PS-008 | 链接改为纯文本 | ../pitfalls/PF-008.md（原文为行内代码写法） |
| PS-008 | 链接改为纯文本 | ../pitfalls/PF-009.md（原文为行内代码写法） |
| PS-008 | 链接改为纯文本 | ../pitfalls/PF-010.md（原文为行内代码写法） |
| PS-008 | 链接改为纯文本 | ../guidelines/GL-007.md（原文为行内代码写法） |
| PS-010 | 改为纯文本 | data/imerg/（原文为行内代码写法） |
| PS-011 | 改为纯文本 | s3://noaa-goes18/GLM-L2-LCFA/2026/250/00/（原文为行内代码写法） |
| PS-013 | 改为纯文本 | data/aster/gdem/（原文为行内代码写法） |
| PS-013 | 改为纯文本 | data/aster/wbd/（原文为行内代码写法） |
| PS-014 | 改为纯文本 | data/analysis/terrain_lightning_stats.csv（原文为行内代码写法） |
| PS-014 | 改为纯文本 | data/analysis/terrain_lightning_summary.csv（原文为行内代码写法） |
| PS-014 | 改为纯文本 | data/analysis/terrain_lightning_density.png（原文为行内代码写法） |
| PS-014 | 改为纯文本 | data/analysis/terrain_lightning_scatter.png（原文为行内代码写法） |
| PS-014 | 改为纯文本 | data/analysis/terrain_lightning_elev_profile.png（原文为行内代码写法） |
| PS-014 | 改为纯文本 | data/glm/l2/（原文为行内代码写法） |
| PS-014 | 改为纯文本 | data/aster/gdem/（原文为行内代码写法） |
| PS-014 | 改为纯文本 | data/aster/wbd/（原文为行内代码写法） |
| PS-015 | 改为纯文本 | AMI/L1B/FD/{YYYYMM}/{DD}/{HH}/（原文为行内代码写法） |
| PS-015 | 改为纯文本 | data/gk2a/ir105/（原文为行内代码写法） |
| PS-015 | 改为纯文本 | data/gk2a/wv073/（原文为行内代码写法） |
| PS-016 | 改为纯文本 | integrated-power/{YYYY-MM}-v2/integrated_map_{YYYY-MM}-v2.csv（原文为行内代码写法） |
| PS-016 | 改为纯文本 | data/gem/（原文为行内代码写法） |
| PS-016 | 改为纯文本 | output/ercot_plants_lz_mapping.csv（原文为行内代码写法） |
| PS-016 | 改为纯文本 | output/ercot_hourly_gen_price.csv（原文为行内代码写法） |
| PS-016 | 改为纯文本 | output/storm_plant_cross.csv（原文为行内代码写法） |
| PS-016 | 改为纯文本 | output/gem_ercot_price_analysis/（原文为行内代码写法） |
| PS-017 | 改为纯文本 | data/openmeteo_seasonal/seasonal_45d_summary.csv（原文为行内代码写法） |
| PS-017 | 改为纯文本 | data/openmeteo_seasonal/{站点}_seasonal_45d.json（原文为行内代码写法） |
| PS-017 | 改为纯文本 | data/openmeteo_seasonal/verif/error_by_lead.csv（原文为行内代码写法） |
| PS-017 | 改为纯文本 | data/openmeteo_seasonal/verif/chart_arrays_full.json（原文为行内代码写法） |
| PS-017 | 改为纯文本 | output/seasonal_forecast_accuracy/（原文为行内代码写法） |
| PS-018 | 改为纯文本 | CONUS/MultiSensor_QPE_01H_Pass2_00.00/（原文为行内代码写法） |
| PS-019 | 改为纯文本 | data/nsrdb/nsrdb_v322_meta_raw.bin（原文为行内代码写法） |
| PS-019 | 改为纯文本 | data/nsrdb/nsrdb_v322_meta_all.npz（原文为行内代码写法） |
| PS-019 | 改为纯文本 | data/nsrdb/nsrdb_v322_ercot_pixels.npz（原文为行内代码写法） |
| PS-021 | 改为纯文本 | data/nsrdb/ercot_solar_plants_pixels.csv（原文为行内代码写法） |
| PS-021 | 改为纯文本 | data/nsrdb/ercot_solar_irradiance_2022-07.nc（原文为行内代码写法） |
| PS-021 | 改为纯文本 | data/nsrdb/ercot_pv_power_2022-07.csv（原文为行内代码写法） |
| PS-021 | 改为纯文本 | output/nsrdb_pvlib_2022-07/nsrdb_pvlib_ercot_2022-07.html（原文为行内代码写法） |
| PS-022 | 改为纯文本 | data/ercot/price_elasticity_2025.csv（原文为行内代码写法） |
| PS-022 | 改为纯文本 | data/nsrdb/hrrr_t2m_2022-07.npz（原文为行内代码写法） |
| PS-022 | 改为纯文本 | data/nsrdb/pv_drop_events_2022-07.csv（原文为行内代码写法） |
| PS-022 | 改为纯文本 | data/nsrdb/pv_counterfactual_hourly_2022-07.csv（原文为行内代码写法） |
| PS-022 | 改为纯文本 | data/nsrdb/pv_event_price_impact_2022-07.csv（原文为行内代码写法） |
| PS-022 | 改为纯文本 | output/pv_event_price_impact_2022-07/pv_event_price_impact_ercot_2022-07.html（原文为行内代码写法） |
| PS-023 | 改为纯文本 | data/ercot/price_elasticity_tail.csv（原文为行内代码写法） |
| PS-023 | 改为纯文本 | data/nsrdb/pv_event_price_impact_tail_2022-07.csv（原文为行内代码写法） |
| PS-023 | 改为纯文本 | output/price_tail_elasticity/ercot_rtm_tail_elasticity.html（原文为行内代码写法） |
| PS-024 | 改为纯文本 | data/nsrdb/ercot_solar_plants_pixels_{2025,2026}.csv（原文为行内代码写法） |
| PS-024 | 改为纯文本 | data/nsrdb/hrrr_t2m_2025_2026.npz（原文为行内代码写法） |
| PS-024 | 改为纯文本 | data/nsrdb/pv_clearsky_hourly_2025_2026.csv（原文为行内代码写法） |
| PS-024 | 改为纯文本 | data/ercot/shortfall_physical_2025_2026.csv（原文为行内代码写法） |
| PS-024 | 改为纯文本 | data/ercot/shortfall_definition_comparison.csv（原文为行内代码写法） |
| PS-024 | 改为纯文本 | data/nsrdb/pv_event_price_impact_physical_2022-07.csv（原文为行内代码写法） |
| PS-024 | 改为纯文本 | output/shortfall_unification/ercot_shortfall_unification.html（原文为行内代码写法） |
| PS-025 | 改为纯文本 | data/ercot/shortfall_physical_2025_2026.csv（原文为行内代码写法） |
| PS-025 | 改为纯文本 | data/ercot/shortfall_duration_2025_2026.csv（原文为行内代码写法） |
| PS-025 | 改为纯文本 | output/shortfall_duration/index.html（原文为行内代码写法） |
| PS-026 | 改为纯文本 | data/ercot/shortfall_physical_2025_2026.csv（原文为行内代码写法） |
| PS-026 | 改为纯文本 | data/ercot/shortfall_duration_crossday_2025_2026.csv（原文为行内代码写法） |
| PS-026 | 改为纯文本 | output/shortfall_duration_crossday/index.html（原文为行内代码写法） |
| PS-027 | 改为纯文本 | data/openmeteo_seasonal/seasonal_shortfall_risk.csv|_weekly.csv|seasonal_streak_risk.csv（原文为行内代码写法） |
| PS-027 | 改为纯文本 | output/seasonal_shortfall_risk/index.html（原文为行内代码写法） |
| PS-028 | 改为纯文本 | news/WIND-Bench_arXiv2026/（原文为行内代码写法） |
| PS-028 | 改为纯文本 | data/gem/ercot_wind_plants_{2025,2026}.csv（原文为行内代码写法） |
| PS-028 | 改为纯文本 | data/nsrdb/hrrr_wind80m_2025_2026.npz（原文为行内代码写法） |
| PS-028 | 改为纯文本 | data/ercot/wind_power_hourly_2025_2026.csv（原文为行内代码写法） |
| PS-028 | 改为纯文本 | data/ercot/wind_shortfall_2025_2026.csv（原文为行内代码写法） |
| PS-028 | 改为纯文本 | data/ercot/wind_elasticity_2025.csv（原文为行内代码写法） |
| PS-028 | 改为纯文本 | output/wind_shortfall_elasticity/index.html（原文为行内代码写法） |
| PS-029 | 改为纯文本 | output/espana_esios_survey/index.html（原文为行内代码写法） |
| PS-030 | 改为纯文本 | data/gem/spain_solar_hubs_2023.csv（原文为行内代码写法） |
| PS-030 | 改为纯文本 | data/nasa_power/spain_pv_hubs_2023.npz（原文为行内代码写法） |
| PS-030 | 改为纯文本 | data/pvgis/spain_sarah3_top12_2023.json（原文为行内代码写法） |
| PS-030 | 改为纯文本 | data/energy_charts/es_2023.csv（原文为行内代码写法） |
| PS-030 | 改为纯文本 | data/spain/spain_pv_hourly_2023.csv（原文为行内代码写法） |
| PS-030 | 改为纯文本 | output/spain_minchain/index.html（原文为行内代码写法） |
| PS-031 | 改为纯文本 | data/gem/spain_solar_hubs_multi.csv（原文为行内代码写法） |
| PS-031 | 改为纯文本 | data/nasa_power/spain_pv_hubs_multi_{年}.npz（原文为行内代码写法） |
| PS-031 | 改为纯文本 | data/spain/spain_regime_summary.csv（原文为行内代码写法） |
| PS-031 | 改为纯文本 | output/spain_regime/index.html（原文为行内代码写法） |
| PS-032 | 改为纯文本 | data/nasa_power/ercot_pv_plants.npz（原文为行内代码写法） |
| PS-032 | 改为纯文本 | data/ercot/ercot_pv_potential_2025_2026.csv（原文为行内代码写法） |
| PS-032 | 改为纯文本 | data/ercot/reversibility_matrix.csv（原文为行内代码写法） |
| PS-032 | 改为纯文本 | output/reversibility_shortfall/index.html（原文为行内代码写法） |
| PS-033 | 改为纯文本 | data/ercot/shortfall_fingerprint.csv（原文为行内代码写法） |
| PS-033 | 改为纯文本 | data/ercot/shortfall_fingerprint_summary.csv（原文为行内代码写法） |
| PS-033 | 改为纯文本 | output/shortfall_fingerprint/index.html（原文为行内代码写法） |
| PS-034 | 改为纯文本 | data/ercot/forecast_bridge_calibration.csv（原文为行内代码写法） |
| PS-034 | 改为纯文本 | data/ercot/forecast_price_outlook.csv（原文为行内代码写法） |
| PS-034 | 改为纯文本 | output/forecast_price_bridge/index.html（原文为行内代码写法） |
| PS-035 | 改为纯文本 | data/gem/spain_solar_hubs_multi.csv（原文为行内代码写法） |
| PS-035 | 改为纯文本 | data/spain/spain_regime_hourly_{2023,2024,2025}.csv（原文为行内代码写法） |
| PS-035 | 改为纯文本 | data/spain/spain_negprice_calibration.csv（原文为行内代码写法） |
| PS-035 | 改为纯文本 | data/spain/spain_negprice_outlook.csv（原文为行内代码写法） |
| PS-035 | 改为纯文本 | output/spain_negprice_forecast/index.html（原文为行内代码写法） |
| PS-036 | 改为纯文本 | data/entsoe/price_da.csv（原文为行内代码写法） |
| PS-036 | 改为纯文本 | data/entsoe/gen_by_type.csv（原文为行内代码写法） |
| PS-036 | 改为纯文本 | data/entsoe/load.csv（原文为行内代码写法） |
| PS-036 | 改为纯文本 | data/entsoe/{price_da,gen_by_type,load}.csv（原文为行内代码写法） |
| PS-037 | 改为纯文本 | data/entsoe/{price_da,gen_by_type,load}.csv（原文为行内代码写法） |
| PS-037 | 改为纯文本 | data/spain/spain_regime_hourly_{2023,2024,2025}.csv（原文为行内代码写法） |
| PS-037 | 改为纯文本 | data/openmeteo_temperature_spain/daily_temp.json（原文为行内代码写法） |
| PS-037 | 改为纯文本 | data/gem/spain_solar_hubs_multi.csv（原文为行内代码写法） |
| PS-037 | 改为纯文本 | output/spain_entsoe_verification/index.html（原文为行内代码写法） |
| PS-037 | 改为纯文本 | data/spain/spain_official_{daily,quintile,yearly}.csv（原文为行内代码写法） |
| PS-037 | 改为纯文本 | data/spain/spain_negprice_v2_{skill,outlook}.csv（原文为行内代码写法） |
| PS-037 | 改为纯文本 | data/spain/spain_entsoe_hourly.csv（原文为行内代码写法） |
| PS-038 | 改为纯文本 | data/spain/spain_official_daily.csv（原文为行内代码写法） |
| PS-038 | 改为纯文本 | data/openmeteo_temperature_spain/daily_temp.json（原文为行内代码写法） |
| PS-038 | 改为纯文本 | data/gem/spain_solar_hubs_multi.csv（原文为行内代码写法） |
| PS-038 | 改为纯文本 | output/spain_negprice_v3/index.html（原文为行内代码写法） |
| PS-038 | 改为纯文本 | data/spain/spain_negprice_v3_{skill,skill_train23,reliability,outlook,scenarios}.csv（原文为行内代码写法） |
| PS-039 | 改为纯文本 | data/spain/spain_long_panel.csv（原文为行内代码写法） |
| PS-039 | 改为纯文本 | data/spain/spain_negprice_threshold{,_fit}.csv（原文为行内代码写法） |
| PS-039 | 改为纯文本 | output/spain_negprice_threshold/index.html（原文为行内代码写法） |
| PS-039 | 改为纯文本 | data/entsoe/{doc}.csv（原文为行内代码写法） |
| PS-040 | 改为纯文本 | data/entsoe/raw/（原文为行内代码写法） |
| PS-040 | 改为纯文本 | data/spain/spain_noon_panel.csv（原文为行内代码写法） |
| PS-040 | 改为纯文本 | data/spain/spain_noon_threshold{,_fit}.csv（原文为行内代码写法） |
| PS-040 | 改为纯文本 | output/spain_negprice_noon/index.html（原文为行内代码写法） |
| PS-041 | 改为纯文本 | data/spain/spain_xborder_daily.csv（原文为行内代码写法） |
| PS-041 | 改为纯文本 | data/spain/spain_xborder_{model,oos,mechanism,coef,corr,negday_means}.csv（原文为行内代码写法） |
| PS-041 | 改为纯文本 | output/spain_negprice_xborder/index.html（原文为行内代码写法） |
| PS-042 | 改为纯文本 | data/energy_charts/fr_public_power_{2023..2026}.json（原文为行内代码写法） |
| PS-042 | 改为纯文本 | data/spain/france_noon_panel.csv（原文为行内代码写法） |
| PS-042 | 改为纯文本 | output/spain_negprice_frforecast/index.html（原文为行内代码写法） |
| PS-043 | 改为纯文本 | data/gem/france_solar_hubs_2024.csv（原文为行内代码写法） |
| PS-043 | 改为纯文本 | data/openmeteo_nwp_france/fr_ghi_archive.npz（原文为行内代码写法） |
| PS-043 | 改为纯文本 | data/spain/france_nwp_panel.csv（原文为行内代码写法） |
| PS-043 | 改为纯文本 | output/spain_negprice_nwpfr/index.html（原文为行内代码写法） |
| PS-044 | 改为纯文本 | data/gem/spain_solar_hubs_nwp.csv（原文为行内代码写法） |
| PS-044 | 改为纯文本 | data/openmeteo_nwp_spain/es_ghi_archive.npz（原文为行内代码写法） |
| PS-044 | 改为纯文本 | data/spain/spain_nwp_panel.csv（原文为行内代码写法） |
| PS-044 | 改为纯文本 | output/spain_negprice_d1warning/index.html（原文为行内代码写法） |
