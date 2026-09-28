# 项目知识清单（当前项目特有）

> 最后更新: 2026-09-27
> 本分类记录气象项目特有的知识，跨项目通用知识见 tech/ 目录
> **结论总览**: [光伏缺口 × 电价冲击链路](conclusions_solar_price.md)（PS-021~024 跨条目结论、已修正结论、口径规范）

## 项目数据源索引

| 数据源 | 类型 | 覆盖区域 | 时间范围 | 脚本 | 数据目录 | 状态 |
|--------|------|----------|----------|------|----------|------|
| Meteostat | 地面观测 | 中国46机场 | 2025-2026 | `download_china_airports_2025.py` 等 | `data/meteostat/` | 活跃 |
| Meteostat | 地面观测 | 东亚东南亚115机场 | 2025-2026 | `download_east_southeast_asia_*.py` | `data/meteostat/east_southeast_asia/` | 活跃 |
| Meteostat | 地面观测 | 美洲85机场 | 2025-2026 | `download_americas_airports_2025_2026.py` | `data/meteostat/americas/` | 活跃 |
| 怀俄明大学 WSGI | 探空廓线 | 德州3站 + 东亚7站 | 2026-07-13 ~ 2026-08-11 | `download_sounding_parallel.py` | `data/sounding/` | 活跃 |
| NEXRAD L2 实时分块 | 天气雷达 | ERCOT 18站 | 实时（秒级延迟） | `test_radar_all_anonymous.py` | 无持久数据 | 已验证 |
| Open-Meteo HRRR | NWP 数值预报 | ERCOT 6站（CONUS全境） | 实时预报+历史2018起 | `test_openmeteo_hrrr.py` | `data/openmeteo_hrrr_results.json` | 已验证 |
| Open-Meteo S2S (EC46/SEAS5) | 45天延伸期集合预报 | ERCOT 6站 | 未来6周~7个月+历史回导 | `verify_seasonal_vs_gfs.py` | `data/openmeteo_seasonal/` | 已验证 |
| GPM IMERG | 卫星降水 | ERCOT 区域 | 历史1998至今（延迟4h~3.5月） | `test_imerg_download.py` | `data/imerg/` | 已验证 |
| RainViewer API | 雷达拼图 | 全球含德州 | 实时（5分钟延迟） | `test_radar_all_anonymous.py` | 无持久数据 | 已验证 |
| GOES-19 | 卫星云图 | 美洲全圆盘 | 2026-07-20 | `goes19_pipeline.py` | `data/goes19/` | 已验证 |
| Himawari-9 | 卫星云图 | 东亚区域 | 2025-11 ~ 2026-07 | `himawari9_segment_pipeline.py` | `data/himawari9/` | 活跃 |
| SURFRAD | 地表辐射 | 美国7站 | 2025-2026 | `surfrad_pipeline.py` | `data/surfrad/` | 已验证 |
| Open-Meteo ERA5 | 再分析 | 北京测试 | 2025-06 | `test_openmeteo.py` | `data/openmeteo/` | 已验证 |
| NASA POWER | 卫星同化 | 全球 | 即时 | `test_nasa_power.py` | 无持久数据 | 已验证 |
| EIA API v2 | 电力负荷/发电 | ERCOT | 2025-01 ~ 2026-09 | `download_ercot_prices.py` | `data/ercot/` | 活跃 |
| GridStatus.io | 电价 | ERCOT 4枢纽+4负荷区+120资源节点 | 2025-01 ~ 2026-09 | `download_ercot_spp.py` | `data/ercot/` | 活跃 |
| **GEM 电站数据库** | **电站坐标/装机** | **全球 (ERCOT 474 座)** | **2026-08 快照** | **`gem_ercot_*.py`** | **`data/gem/`** | **已验证** |
| **GOES GLM** | **卫星闪电** | **ERCOT 区域** | **2026-09-07** | **`download_glm_l2.py`** | **`data/glm/l2/`** | **已验证** |
| **FY-4 LMI** | **卫星闪电** | **中国区域** | **2019-2023 (订正集)** | **`download_fy4_lmi.py`** | **—** | **已验证** |
| **ASTER GDEM** | **地形高程** | **ERCOT 154 tiles** | **静态** | **`download_aster_gdem.py`** | **`data/aster/gdem/`** | **已验证** |
| **ASTWBD** | **水体分类** | **ERCOT 154 tiles** | **静态** | **`download_aster_gdem.py`** | **`data/aster/wbd/`** | **已验证** |
| **MRMS QPE** | **雷达定量降水** | **ERCOT 1070×1330 (1km)** | **归档 2020-10~2023-07 + 官网近10天** | **`test_mrms_download.py`** | **`data/mrms/`** | **已验证** |
| **NSRDB v3.2.2** | **太阳辐照度 (GHI/DNI/DHI)** | **ERCOT 330,096 像素 (5min/2km)** | **1998~2022 (逐年 h5, 懒读取)** | **`test_nsrdb_meta.py`** | **`data/nsrdb/`** | **已验证** |
| **NSRDB 2022-07 提取** | **56 电站辐照 (5min)** | **ERCOT 光伏 (10.66 GW)** | **2022-07 全月** | **`download_nsrdb_ercot_july2022.py`** | **`data/nsrdb/ercot_solar_irradiance_2022-07.nc`** | **已完成** |
| **HRRR 2m 温度 (历史)** | **NWP 分析温度** | **ERCOT 56 光伏电站** | **2022-07 全月** | **`download_hrrr_temp_july2022.py`** | **`data/nsrdb/hrrr_t2m_2022-07.npz`** | **已完成** |
| **USCRN subhourly** | **地面基准实测 (5min 辐照/气温)** | **德州 8 站** | **2022-07 全月** | **`download_uscrn_tx_july2022.py`** | **`data/uscrn/`** | **已完成** |
| **WMO S2S 库** | **多中心延伸期回算** | **全球 (13 中心)** | **1981/1996 起 + 2015 起实时** | **`test_nsrdb_mrms_s2s.py`** | **—** | **调研完成, 待注册** |
| **HRRR 2m 温度 (2025-26)** | **NWP 分析温度** | **ERCOT 141 光伏电站** | **2025-01-01 ~ 2026-09-06** | **`download_hrrr_temp_2025_2026.py`** | **`data/nsrdb/hrrr_t2m_2025_2026.npz`** | **已完成** |
| **GEM 按年电站清单** | **光伏电站坐标/容量** | **ERCOT ≥100MW** | **2025/2026 快照 (141 座, 30.89 GW)** | **`match_nsrdb_ercot_solar_annual.py`** | **`data/nsrdb/ercot_solar_plants_pixels_{年}.csv`** | **已完成** |
| **物理晴空反事实 (2025-26)** | **pvlib Solis 晴空出力** | **ERCOT 141 电站聚合** | **2025-01-01 ~ 2026-09-06 (小时)** | **`clearsky_counterfactual_2025_2026.py`** | **`data/nsrdb/pv_clearsky_hourly_2025_2026.csv`** | **已完成** |

## 数据量汇总

| 数据源 | 文件数 | 数据量 | 行数 | 备注 |
|--------|--------|--------|------|------|
| Meteostat 全球 | 847 | 180.4 MB | 606,069 | 246机场×2025-2026 |
| 探空廓线 | 556 | — | 842,249 | 10站×30天×2时次 |
| NEXRAD 雷达 (unidata chunks) | — | — | — | 18站×实时体扫（秒级延迟） |
| ERCOT 枢纽电价 | 8 | — | 273,216 | 4枢纽×DAM+RTM×1.5年 |
| ERCOT Resource Node | 8 | — | ~448,000 | 8节点×RTM×1.5年 |
| ERCOT 负荷/发电 | 38 | 42.6 MB | 171,231 | 19个月×2路由 |
| SURFRAD | 63 | ~21 MB | 63,715 | 7站×7天 |
| GOES-19 | 3 | 281.4 MB | — | 全圆盘真彩色 |
| IMERG | 2 | 38.7 MB | — | 30分钟+日产品各1 |
| GOES GLM | 180 | ~54 MB | — | 1小时×20秒文件 |
| ASTER GDEM | 308 | 2.89 GB | — | 154 tiles×dem+num |
| ASTER WBD | 308 | 5.59 GB | — | 154 tiles×dem+att |
| GEM 电站数据库 | 7 | ~110 MB | 217,604 | GEM 6 + WRI 1 |
| Open-Meteo S2S 季节预报 | 12+ | ~小 | — | 45天×6站 raw+verif序列 |
| MRMS QPE 样例 | 5 | ~7 MB | 1.42M 格点/时次 | ERCOT 裁剪 1070×1330, 2 个时次 |
| NSRDB meta 缓存 | 3 | ~356 MB | 284 万像素 | raw.bin + 全域npz + ERCOT索引npz (330,096像素) |
| NSRDB 2022-07 辐照提取 | 1 | 6.1 MB | 56 站 × 8928 × 3 分量 | ercot_solar_irradiance_2022-07.nc (5min GHI/DNI/DHI) |
| HRRR 2m 温度 2022-07 | 2 | ~0.4 MB | 744h × 56 站 | npz + csv |
| USCRN 2022-07 | 9 | 38 MB | 8 站 × 8928 步 × 23 列 | 5min 辐照/气温地面基准 |
| 合计 | ~2,620+ | ~9.9 GB | ~2.7M+ | — |

## 关键分析结果

| 分析主题 | 输出文件 | 关键发现 | 日期 |
|----------|----------|----------|------|
| 探空区域对比 | `sounding_analysis_report.html` | 德州 DCAPE 1205 vs 东亚 1029 J/kg (高17%) | 2026-08-11 |
| 探空深度分析 | `sounding_deep_analysis.html` | 德州 DCAPE 高19%, p=6.51e-09, Cohen's d=0.525 | 2026-08-11 |
| 探空垂直廓线对比 | `sounding_analysis_report.html` | 德州边界层温度梯度更陡，低层更干 | 2026-08-11 |
| 探空30天趋势 | `sounding_timeseries.csv` | 德州 DCAPE +11.0 J/kg/天上升趋势(p<0.05) | 2026-08-11 |
| 雷暴×电价联动 | `thunderstorm_ercot_analysis.html` | 113事件, 22个电价尖峰, 光伏骤降主因 | 2026-07-24 |
| ERCOT Resource Node | 8节点RTM数据 | 风电均价低于HB_WEST(阻塞), 光伏负电价23.4% | 2026-08-06 |
| 德州vs东亚DCAPE日变化 | `sounding_deep_analysis.html` | 两区域日变化模式相反（当地傍晚vs早晨） | 2026-08-11 |
| NEXRAD 雷达15类数据源匿名测试 | `radar_test_results_comprehensive.json` | unidata chunks 18站全覆盖, 官方桶 Access Denied | 2026-08-12 |
| 中国机场Meteostat覆盖 | `check_data_integrity.py` | 46机场全部成功, 11机场综合评分"优" | 2026-07-19 |
| NASA POWER vs SURFRAD | `test_nasa_power.py` | GHI MAE 38.6 W/m², 温度 MAE 1.4°C | 2026-07-20 |
| GEM电站×ERCOT电价三层联动 | `gem_ercot_price_analysis.html` | 风电是电价压制因子(夜间r=-0.38), 尖峰=风光缺位+高负荷, KIAH雷暴传导1.43x | 2026-09-11 |
| 45天季节预报精度核验 | `seasonal_forecast_accuracy.html` | 45天风速MAE 1.49 vs GFS10天 1.30 km/h; 降水1.26 vs 0.26 mm(~5x); 降水误差事件型尖峰 | 2026-09-16 |
| NSRDB+pvlib 光伏出力建模验证 | `output/nsrdb_pvlib_2022-07/nsrdb_pvlib_ercot_2022-07.html` | 小时r=0.9976, MAE 185MW(峰值1.9%), 月能量-2.1%; EIA-930时间戳为区间结束须-1h; pvlib角度参数是度数 | 2026-09-27 |
| 光伏缺口×电价冲击推演 (PS-022) | `output/pv_event_price_impact_2022-07/pv_event_price_impact_ercot_2022-07.html` | 温度修复: HRRR实测温度使热浪正午偏差-327→+16MW, ILR 1.30, 全月MAE 174MW/能量+1.4%; USCRN验证NSRDB无热浪反演劣化(+10%水平差被标定吸收); 7骤降事件全云主导无弃光; 弹性β=+5.08%/GW(2025), 2026复验+5.43; 2022-07推演: 17事件/100.3GWh, RTM中位+11.0%/最大+25.0%(4.4GW), 热浪期25.6GWh | 2026-09-27 |
| RTM 尾部尖峰弹性 (PS-023) | `output/price_tail_elasticity/ercot_rtm_tail_elasticity.html` | 15min口径抹平极端小时价格2.4x($3777→$1561)但q99不变→弹性估计无偏; 分位弹性2025单调升3.85→5.16%/GW、2026平坦→尾部放大不稳健; 原始尺度尾部冲击2.4x($1.0→$2.4/GW)但相对弹性更低(自洽); 凸性不成立(仅2025全样本t=2.6); 边际尖峰率随缺口反降(辛普森悖论, 尖峰主由需求/时段驱动); **高需求+5.84被推翻**(子样本法两年反向2025+5.84/2026+4.33, 交互项−1.95/−1.00); 2022-07分位情景P50+8.1%/P90+9.2%/P99+9.8%(最大+22.1%), PS-022均值口径+11.0%/+25.0%落上沿(未低估) | 2026-09-27 |
| 缺口口径统一 (PS-024) | `output/shortfall_unification/ercot_shortfall_unification.html` | 2025/2026物理晴空反事实建成(141座30.89GW, 覆盖94.5%; HRRR 141站×14736h; GEM 2026-08版只到2025投产→2026比值1.133靠逐小时偏移吸收); **缺口量级差1.3~1.7x**(物理中位5.86/5.32GW vs 包络3.49/4.13GW); **弹性对口径不敏感**(物理OLS均值+5.60 vs 包络+5.26, 差0.34%/GW); **辛普森悖论归因被推翻**(物理口径下仍降2.0%→0.0%, 真因是天气组合负相关: 云致缺口↔降温低需求); 2022-07三口径收敛(P50+8.0~11.0%/最大+17.8~25.0%) | 2026-09-27 |
| 缺口持续时间维度 (PS-025) | `output/shortfall_duration/index.html` | 恶劣缺口(≥12GW≈39%舰队)298事件; **多小时持续常态**(≥2h承98%、≥3h承92%、≥4h承85%能量; 单发1h仅16%; 最长连续11h填满白天; 单日最大286GWh); **持续时间溢价跨年不稳健**(2025事件第5h较第1h约+9%、Q99累积+0.38%/GWh; 2026无)⇒逐小时弹性×缺口外推未因时间维度低估; **日际连阴聚簇最长25~26天**(周级低日照气候型, 指向储能充足性) | 2026-09-28 |
| 缺口日际/跨日持续 (PS-026) | `output/shortfall_duration_crossday/index.html` | **阈值敏感性**: 8~15GW下≥3h能量89~96%(多小时持续与阈值无关); **跨日持续时间溢价为负/不显著**(2025连阴序号−1.1%/天显著, 连阴后期价格走低=天气负相关日尺度重演); **危险云系(高缺×高需)日尺度常见但温和**: 占高缺日42%、价格仅1.2×良性($37vs$31)⇒持续时间不放大电价冲击, 尾部是特定极端小时×需求峰而非整个连阴云系 | 2026-09-28 |

## 项目脚本索引

### 下载脚本 (data_download/)

| 脚本 | 用途 | 数据源 | 关键参数 |
|------|------|--------|----------|
| `download_sounding_parallel.py` | 探空并行下载(5线程) | 怀俄明大学 WSGI | `--region texas/asia --hours 0 12 --days 30` |
| `download_sounding.py` | 探空单线程下载(备用) | 怀俄明大学 WSGI | 同上 |
| `download_ercot_prices.py` | ERCOT 负荷/发电/燃料 | EIA API v2 | API key: $env:EIA_API_KEY |
| `download_ercot_spp.py` | ERCOT 电价/结算点 | GridStatus.io API | API key: $env:GRIDSTATUS_API_KEY |
| `goes19_pipeline.py` | GOES-19 卫星云图 | AWS S3 noaa-goes19 | `--region fulldisk/namerica/samerica` |
| `himawari9_segment_pipeline.py` | 葵花9 卫星云图 | AWS S3 noaa-himawari9 | 分段下载 S0210+S0310 |
| `surfrad_pipeline.py` | SURFRAD 辐射数据 | NOAA GML | `--days 7` |
| `test_openmeteo.py` | Open-Meteo API 测试 | Open-Meteo | 无key |
| `test_meteostat.py` | Meteostat 单站测试 | Meteostat | 无key |
| `test_nasa_power.py` | NASA POWER 测试 | NASA POWER | 无key |
| `download_china_airports_2025.py` | 中国46机场2025年 | Meteostat | ICAO列表 |
| `download_china_airports_2026.py` | 中国46机场2026年 | Meteostat | ICAO列表 |
| `download_east_southeast_asia_2025_2026.py` | 东亚东南亚115机场 | Meteostat | 16国ICAO |
| `download_americas_airports_2025_2026.py` | 美洲85机场 | Meteostat | 20国ICAO |
| `check_data_integrity.py` | 数据完整性检验 | Meteostat | 4维度 |
| `check_meteostat_realtime.py` | 实时性测试(亚洲) | Meteostat | 8站 |
| `check_meteostat_realtime_americas.py` | 实时性测试(美洲) | Meteostat | 10站 |
| `test_radar_all_anonymous.py` | 15类雷达数据源匿名可达性测试 | NEXRAD/RainViewer/GCP/IEM/NWS | 无key, 匿名S3 |
| `test_openmeteo_hrrr.py` | HRRR/GFS/NAM/NBM 预报数据测试 | Open-Meteo | 无key |
| `test_rainviewer_detail.py` | RainViewer API 详细测试 | RainViewer | 无key |
| `test_imerg_download.py` | IMERG 30分钟/日产品下载测试 | earthaccess + GES DISC | 需 Earthdata 账号 |
| `debug_imerg_search.py` | IMERG 搜索调试脚本 | earthaccess CMIP 搜索 | 需 Earthdata 账号 |
| `download_glm_l2.py` | GOES GLM L2 闪电数据下载 | AWS S3 noaa-goes{16/18/19} | 无key, 匿名S3 |
| `parse_glm.py` | GLM 闪电数据解析 | netCDF-4 | 闪击位置/能量提取 |
| `download_fy4_lmi.py` | FY-4 LMI 闪电数据下载指引 | NSMC / 中科院数据集 | NSMC注册或公开下载 |
| `parse_fy4_lmi.py` | FY-4 LMI 数据解析 | NetCDF | 事件位置/辐射强度 |
| `download_aster_gdem.py` | ASTER GDEM v3 + ASTWBD 地形/水体 | NASA LP DAAC (Earthdata) | netrc 认证 |
| `download_seasonal_forecast.py` | Open-Meteo 45天集合预报下载(6站,含50成员) | Open-Meteo seasonal | 无key |
| `verify_seasonal_vs_gfs.py` | 45天预报 vs ERA5/GFS10天 逐lead误差 | Open-Meteo seasonal+archive+historical | 无key |
| `test_cma_api.py` | CMA data.cma.cn API 连接测试 | data.cma.cn | 需CMA账号 |
| `test_nsrdb_mrms_s2s.py` | 三源连通性探测 (NSRDB/MRMS/S2S) | AWS S3 + ECDS | 无key, 匿名S3 |
| `test_nsrdb_h5coro.py` | NSRDB h5coro 部分读取 + 日循环量纲验证 | nrel-pds-nsrdb S3 | 无key, 懒读取 |
| `test_nsrdb_meta.py` | NSRDB meta 流式下载 + ERCOT 像素定位 | nrel-pds-nsrdb S3 | 无key, 生成像素索引 npz |
| `test_mrms_download.py` | MRMS QPE 归档列举+下载+ERCOT裁剪 | noaa-mrms-pds S3 + NCEP | 无key, cfgrib |
| `match_nsrdb_ercot_solar.py` | GEM 光伏电站→NSRDB 像素映射 | GEM + NSRDB 像素索引 | 100 座, 中位距离 0.9km |
| `download_nsrdb_ercot_july2022.py` | NSRDB 2022-07 辐照分块提取 (自愈+断点续传) | nrel-pds-nsrdb S3 | 无key, 735 chunks × GHI/DNI/DHI |
| `download_eia_solar_2022.py` | EIA-930 2022-07 燃料类型 (验证基准) | EIA API v2 | API key: $env:EIA_API_KEY |
| `download_hrrr_temp_july2022.py` | HRRR 2m 温度 56 电站 (温度链路修复) | Open-Meteo historical (ncep_hrrr_conus) | 无key, 744h×56站 |
| `download_uscrn_tx_july2022.py` | USCRN 德州 8 站 5min 地面基准 | NOAA NCEI subhourly01 | CRNS0101-05-2022, 无表头 23 列 |
| `download_nsrdb_uscrn_pixels_july2022.py` | USCRN 站点的 NSRDB 像素辐照提取 | nrel-pds-nsrdb S3 | 无key, 最近像素匹配 |
| `download_hrrr_temp_2025_2026.py` | HRRR 2m 温度多年份下载 (多坐标批量) | Open-Meteo historical-forecast | 141 站 × 614 天, 20 站/批 |
| `match_nsrdb_ercot_solar_annual.py` | GEM 按年 ERCOT 光伏清单 + NSRDB 像素匹配 | GEM 2026-08 + 像素索引 | `start-year ≤ 年`, ≥100MW |

### 分析脚本 (analysis/)

| 脚本 | 用途 | 输入 | 输出 |
|------|------|------|------|
| `sounding_analysis.py` | 探空基础分析(加载/插值/统计) | 探空CSV | HTML报告 + CSV |
| `sounding_deep_analysis.py` | 探空深度分析(统计检验/趋势) | 探空CSV | HTML报告 |
| `thunderstorm_ercot_analysis.py` | 雷暴×电价联动分析 | Meteostat + ERCOT | HTML报告 + CSV事件表 |
| `gem_ercot_lz_analysis.py` | 电站-LZ映射 + 装机结构分析 | GEM CSV | HTML报告 + CSV |
| `gem_ercot_deep_dive.py` | 发电×电价×事件三层深度分析 | GEM + ERCOT + EIA | HTML报告 + CSV |
| `gem_storm_cross.py` | 雷暴×电站坐标空间交叉 | Meteostat + GEM | CSV |
| `build_forecast_accuracy_summary.py` | 季节预报精度汇总统计(各段MAE/重叠区对比) | verif CSV | 汇总JSON + stdout |
| `rebuild_full_chart_arrays.py` | 重建完整逐lead误差数组(含GFS lead1-5) | series JSON | chart_arrays_full.json |
| `nsrdb_pvlib_power.py` | NSRDB 辐照→pvlib PVWatts 出力→EIA-930 对比 | 辐照 nc + EIA CSV | 出力 CSV + 精度统计 |
| `nsrdb_eia_comparison.py` | 模型 vs 实际深入对比(昼夜/日能量/爬坡/事件日) | 出力 CSV | 对比摘要 md |
| `build_nsrdb_pvlib_report.py` | 生成 NSRDB+pvlib 验证 HTML 报告 | 出力 CSV + 辐照 nc | output/nsrdb_pvlib_2022-07/*.html |
| `verify_temp_fix.py` | 温度参数化 vs HRRR 实测温度分窗对比 | 出力 CSV ×2 | 分窗指标表 (stdout) |
| `ilr_sweep_heatwave.py` | ILR 四窗口扫描 (热浪/非热浪×正午/全月) | 辐照 nc + EIA CSV | 最优 ILR=1.30 |
| `verify_nsrdb_vs_uscrn_july2022.py` | NSRDB×USCRN 交叉验证 (反演劣化排除) | USCRN CSV + NSRDB 提取 | nsrdb_uscrn_daily.csv |
| `identify_pv_drop_events_2022-07.py` | 光伏骤降事件归因 (云主导判定) | 出力 CSV | pv_drop_events_2022-07.csv |
| `calibrate_price_elasticity_2025.py` | RTM 缺口弹性面板标定 (2025/2026) | EIA-930 + GridStatus RTM | price_elasticity_2025.csv |
| `pv_event_price_impact_2022-07.py` | 晴空反事实缺口×电价冲击推演主脚本 | 辐照 nc + HRRR npz + EIA CSV | 逐时反事实表 + 事件冲击 CSV |
| `build_pv_event_price_report.py` | 生成缺口×电价冲击 HTML 报告 | 反事实/事件/弹性 CSV | output/pv_event_price_impact_2022-07/*.html |
| `calibrate_price_elasticity_tail.py` | RTM 尾部尖峰弹性标定 (分位回归+凸性+尾部概率+高需求交互+稳健性) | EIA-930 + GridStatus 15min RTM | price_elasticity_tail.csv |
| `pv_event_price_impact_tail_2022-07.py` | 2022-07 分位情景推演 (P50/P90/P99 上浮) | 晴空反事实 CSV + 分位弹性 | pv_event_price_impact_tail_2022-07.csv |
| `build_price_tail_report.py` | 生成尾部弹性 HTML 报告 | 标定 CSV + 事件 CSV + RTM | output/price_tail_elasticity/*.html |
| `clearsky_counterfactual_2025_2026.py` | 2025/2026 物理晴空反事实 (pvlib Solis 同链路) | 电站清单 + HRRR npz | pv_clearsky_hourly_2025_2026.csv |
| `build_physical_shortfall_2025_2026.py` | 逐小时偏移校准, 构造物理缺口 | 晴空反事实 + panel CSV | shortfall_physical_2025_2026.csv |
| `compare_shortfall_definitions.py` | 两口径对比 (弹性/尾部概率/分箱尖峰率) | 两口径缺口 + 15min RTM | shortfall_definition_comparison.csv |
| `pv_event_price_impact_physical_2022-07.py` | 统一口径的 2022-07 分位情景推演 | 2022 反事实 + 口径对比 CSV | pv_event_price_impact_physical_2022-07.csv |
| `build_shortfall_unification_report.py` | 生成口径统一 HTML 报告 | 缺口/对比/推演 CSV | output/shortfall_unification/*.html |

## 关键配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Git 路径 | `C:\Program Files\Git\cmd\git.exe` | 不在 PATH 中 |
| GridStatus API Key | `.env` 文件自动加载 | 250次/月, 50万行/月 |
| EIA API Key | `.env` 文件自动加载 | 免费注册 |
| Earthdata 凭证 | `~/_netrc` (Windows) / `~/.netrc` (Linux) | netrc 自动读取, 见 GL-009 |
| CMA NSMC 凭证 | `~/.nmcdev/config.ini` | nmc-met-io 配置 |
| SSL 证书 | `ssl.CERT_NONE` | 中国网络访问 HTTPS 需跳过验证 |
| 并行下载线程 | 5 (ThreadPoolExecutor) | 600请求从7h降至36min |
| 探空断点续传 | 检查文件存在自动跳过 | — |
| 单价、电价、功率 | 单位：$、$/MWh、MW | — |

## 待办事项

| 事项 | 优先级 | 计划时间 | 说明 |
|------|--------|---------|------|
| 下载剩余风电节点RTM (YCAT_WND_RN, YNG_WND_ALL) | 中 | 2026-10-01 | 10月额度重置后, 当前已达500K行限额 |
| 下载89个光伏节点RTM | 中 | 2026-10-01 | 10月额度重置后, 本月已耗尽 |
| 更新探空数据范围 | 低 | 滚动 | 按需下载新日期数据 |
| 联动分析：探空DCAPE × ERCOT电价 | 中 | 待定 | 探空DCAPE作为雷暴潜势指标，与电价波动关联 |
| 联动分析：ASTER地形 × 闪电分布 | 低 | 待定 | 地形高程与GLM闪电空间分布关联 |
| RTM 事件尾部建模 (稀缺定价 >$1000) | ~~低~~ 已完成 | 2026-09-27 | 已完成 → PS-023: 15min 口径 + 分位数回归 + 尾部概率 + 凸性检验; 高需求放大结论被推翻 |
| 用物理晴空反事实统一缺口口径 | ~~中~~ 已完成 | 2026-09-27 | 已完成 → PS-024: 2025/2026 物理反事实建成, 弹性对口径不敏感(差 0.34 %/GW), 但**悖论归因被推翻**(非包络虚高, 属天气组合负相关) |
| WMO S2S 库注册与回算获取 | 中 | 待定 | 注册 ECMWF/ECDS 账号, 拉取 ECMWF/NCEP 回算, 升级 PS-017 为多窗口统计 (PS-020) |
| 延伸期预报精度多窗口重采样 | 低 | 待定 | 由单窗口扩为多窗口、多初始化 hindcast，附集合离散度置信带 (PS-017/PS-020) |