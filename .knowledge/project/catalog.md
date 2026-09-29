# 项目知识清单（当前项目特有）

> 最后更新: 2026-09-29
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
| **Open-Meteo Seasonal (西班牙)** | **45天延伸期集合预报 (逐日短波/气温)** | **西班牙 9 光伏区** | **未来45天** | **`download_spain_seasonal.py`** | **`data/openmeteo_seasonal_spain/`** | **已验证(免注册)** |
| **Open-Meteo Archive 温度 (西班牙)** | **逐日 Tmax/Tmin/Tmean (历史/当期)** | **西班牙 9 光伏区** | **2022-12-01 ~ 2026-09-28** | **`download_spain_temperature.py`** | **`data/openmeteo_temperature_spain/daily_temp.json`** | **已验证(免注册)** |
| GPM IMERG | 卫星降水 | ERCOT 区域 | 历史1998至今（延迟4h~3.5月） | `test_imerg_download.py` | `data/imerg/` | 已验证 |
| RainViewer API | 雷达拼图 | 全球含德州 | 实时（5分钟延迟） | `test_radar_all_anonymous.py` | 无持久数据 | 已验证 |
| GOES-19 | 卫星云图 | 美洲全圆盘 | 2026-07-20 | `goes19_pipeline.py` | `data/goes19/` | 已验证 |
| Himawari-9 | 卫星云图 | 东亚区域 | 2025-11 ~ 2026-07 | `himawari9_segment_pipeline.py` | `data/himawari9/` | 活跃 |
| SURFRAD | 地表辐射 | 美国7站 | 2025-2026 | `surfrad_pipeline.py` | `data/surfrad/` | 已验证 |
| Open-Meteo ERA5 | 再分析 | 北京测试 | 2025-06 | `test_openmeteo.py` | `data/openmeteo/` | 已验证 |
| NASA POWER | 卫星同化/再分析 | 全球 | 逐小时 2001~至今 | `download_spain_data.py` | `data/nasa_power/` | 活跃 |
| **Energy-Charts (Fraunhofer ISE)** | **实际发电分技术/负荷/电价** | **欧洲各国(含西班牙)** | **2015~至今 (2015-2022 小时; 2023 起 15min)** | **`download_spain_data.py`, `download_spain_ec_history.py`(12年分技术发电)** | **`data/energy_charts/`** | **已验证(免注册); ⚠`start/end` 按当地时间, 跨年请求会带回上一年最后 1h(按月聚合须累加)** |
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
| **GEM 风电清单 (按年)** | **风电场坐标/容量** | **ERCOT bbox (165 点位)** | **2025/2026 快照 (37.93 GW)** | **`prep_ercot_wind_fleet.py`** | **`data/gem/ercot_wind_plants_{年}.csv`** | **已完成** |
| **HRRR 80m 风速 (2025-26)** | **NWP 轮毂高度风速** | **ERCOT 165 风电点位** | **2025-01-01 ~ 2026-09-06** | **`download_hrrr_wind_2025_2026.py`** | **`data/nsrdb/hrrr_wind80m_2025_2026.npz`** | **已完成** |
| **OMIE 日前市场文件** | **电价 (ES+PT, 小时/15min)** | **伊比利亚** | **历史至今 (日文件, D-1 13:30发布)** | **`build_spain_market_survey_report.py`** | **无持久数据** | **已验证(免注册)** |
| **PVGIS 5.3 API** | **逐小时辐照 G(i)+气温+风速** | **欧洲(SAHARA3)/全球(ERA5)** | **2005-2023** | **—** | **无持久数据** | **已验证(免注册)** |
| **ESIOS API** | **实时分技术发电/需求/PVPC** | **西班牙** | **指标而异** | **`download_spain_esios.py`** | **`data/esios/`** | **token已获(09-29); 本机被域名级WAF拦截(见PF-013), 需换网/代理** |
| **ENTSO-E Transparency** | **泛欧分技术发电/负荷/日前价/风光预测** | **欧洲 bidding zones（西班牙 10YES-REE------0）** | **2015-01-01 至今（实测可用；日前价与负荷已全回填 **2015-01~2026-09 共 141 月**，分技术发电 A75 仅 **2023-01~2026-09**）** | **`download_spain_entsoe.py`** | **`data/entsoe/`** | **已验证(09-29); 价格过一手OMIE校验; ⚠须处理 A03 压缩 + A01/A07 合约过滤(PF-014); ⚠2015-2023 负价恒为 0(首次负价 2024-04-01); ⚠合并 CSV 的跨度=最后一次下载批次, 回填后须用全区间重跑(PS-039 §8-6)** |

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
| **ENTSO-E 西班牙** | **657** | **~0.4 GB** | **304.2 万行** | **合并表: 日前价 129,167 行(2015-01~2026-09, 2025-10 起 15min) / 分技术发电 2,654,432 行(2023-01~2026-09) / 负荷 217,279 行(2015-01~2026-09); raw 月缓存 642 文件(321 csv + 321 xml)** |
| 合计 | ~3,280+ | ~10.3 GB | ~5.8M+ | — |

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
| 季节预报→缺口概率化 (PS-027) | `output/seasonal_shortfall_risk/index.html` | EC46/SEAS5 50成员辐照聚合→未来45天光伏缺口概率先验; **关键校准**: 季节逐日短波重度平滑致绝对τ阈值下缺日近乎0(伪结论), 改用历史τ分布(602天)Q25/Q10作轻缺/重缺相对阈值; 初始窗口(秋): τ中位0.68~0.76≈常年(near-normal), 轻缺日均~7%/重缺~2%, 无成员≥5天连阴, **"缺∧热"危险云系季节缺席**(峰值P~2%, 10/01后=0); 概率未校准欠发散, 只宜读风险排序 | 2026-09-28 |
| 风电缺口×电价 (PS-028) | `output/wind_shortfall_elasticity/index.html` | 物理风功率链路: HRRR 80m+标准曲线(η=0.90), 165点位37.9GW, **r=0.956/能量比1.02/CF 0.355vs0.346**; **风光不对称(核心)**: 光伏缺口→电价 **+4.5~+5.7%/GW**(外生云缺), 风电"潜力−实际"缺口→ **−2.8~−3.3%/GW** 且**控实际风电后≈0**(内生弃风); 高缺口小时<$5负价占比13% vs 低缺口2%(6~7倍)+高风低需求夜间 ⇒ 缺口=供给过剩标记非缺电; **低风异常弹性 +7.4%/GW**(SE 0.17)才是风电的"天气供给缺口"类比物 ⇒ 不能把光伏弹性套到风电 | 2026-09-28 |
| 西班牙市场数据调研 (PS-029) | `output/espana_esios_survey/index.html` | 实测: **OMIE免注册可用**(2024-04-29日均58.27€/MWh与公开报道吻合, MTU已由24→96点15min)、**PVGIS API免注册可用**(SARAH3 2005-2023逐小时)、**ESIOS匿名403需邮件token**; 西班牙=最极端高可再生市场(2025风21.6%+光18.4%, 负价2024年247h/2025年477~798h, 弃电1.6%→3.2%、2025-07峰值11%)⇒PS-028"缺口=内生弃风"的极端检验样本; **结构差异**: 西班牙分区+日前为主无ERCOT式RTM, "缺口→实时尖峰"须改口径; ⚠二手报道称4-29最高97.9(22h)与原始文件不符(实为08h 102.26) | 2026-09-28 |
| 西班牙光伏最小链路 (PS-030) | `output/spain_minchain/index.html` | 全免注册复刻 pvlib 链路(GEM+NASA POWER+Energy-Charts/OMIE): 120点/26.65GW, **r=0.9845/标定后年能量比0.979**(潜力39.6 vs 实际40.4 TWh), CF 0.170vs0.173, 月比0.878-1.197; **核心: ERCOT 标定参数不可移植** — ILR 1.30→高估50%(比值1.496), 西班牙需 **ILR≈0.85**; 电价"光伏水平−2.52%/GW"与ERCOT −4.9 同号; 缺口系数(−53.7)是共线性伪象不可解读; 2023无负价+伊比利亚例外机制 ⇒ 弹性仅方向参考 | 2026-09-28 |
| 西班牙光伏多年市场区间对比 (PS-031) | `output/spain_regime/index.html` | 同链路跑 2023/2024/2025: 装机26.6→31.3GW, **负价小时 0→247→544**(2024与公开统计完全一致), 标定ILR 0.85→0.95→1.05(仍远低于ERCOT 1.30); **核心: 高缺口小时负价频率 0%→27.6%→55.5%**(低缺口仅0~0.2%)+高缺口组负荷更低 ⇒ 缺口=内生过剩标记(与PS-028 ERCOT风电同构); **同一市场晴空缺口弹性恒正(+1.6~+2.8) vs 天气缺口恒负(−6.4~−0.1)** ⇒ 升级PS-028判据: 决定缺口符号的是**成因(外生供给损失 vs 内生供给过剩)而非电源类型**; 光伏水平弹性 −3.42→−4.86€/MWh per GW 随渗透率增强 | 2026-09-28 |
| 缺口成因判据可逆性检验 (PS-032) | `output/reversibility_shortfall/index.html` | 把PS-031判据放进**6个「市场×技术×成因」格子**做双向检验: **缺口单独时外生全正(+1.8~+8.1%/GW)、内生全负(−4.3~−27.7%/GW)** ⇒ 符号随成因变不随电源变(同市场内光伏/风电各两号, 同技术光伏跨市场两号); **补齐ERCOT光伏内生缺口**(新增 NASA POWER全天候辐照+pvlib重建潜力, 136点/30.89GW, 标定ILR 1.30与PS-021一致, r=0.976/0.980); **可逆性边界**: 控制出力水平后外生6估计中5个转负(正号只是"出力↓→电价↑"镜像, 风电低风异常corr−0.70), **仅"内生缺口→负"设定稳健**且与水平近正交(ERCOT光伏corr≈0); ⚠NASA POWER hourly默认LST需显式`time-standard=UTC`(否则r从0.98塌到0.31) | 2026-09-28 |
| 缺口工况指纹 (PS-033) | `output/shortfall_fingerprint/index.html` | 把PS-032符号落到可观测工况(缺口十分位分组→低价/负价频率+需求+时段): **内生缺口=供给过剩标记坐实** — ERCOT光伏最高两档负价频率 **0.0%→16.0%**(需求同向 60.5→51.7GW)、风电0.7%→5.5%、西班牙光伏2025达**33.4%**; **外生缺口不含过剩信号** — ERCOT风电低风异常高的小时负价**6.4%→0.1%**+价格中位21.2→34.3(corr+0.25, 真稀缺), ERCOT光伏晴空缺口两年不稳定(corr−0.06/+0.02); **时间截面**: 西班牙内生高缺口档负价频率 **0%(2023零负价)→15.7%(2024)→33.4%(2025)** 与负价小时0→247→544同步 ⇒ 标记随市场成熟增强 | 2026-09-29 |
| 缺口→电价 日尺度转移函数与45天展望 (PS-034) | `output/forecast_price_bridge/index.html` | 把PS-027季节预报接PS-032/033判据: **ERCOT"预报桥"不成立** — 季节预报的云量缺口在日尺度对电价近乎无信息(**R²=0.016**, corr+0.13)且**不标记负价**(+0.06), 因缺口与需求强负相关(五分位需求63.8→55.6GW, 云来天凉→PS-024天气负相关在日尺度重演); 白天溢价=−0.40+9.15×缺口分数; **唯一可用负价曲线在西班牙** — gap_w最高档**P(负价日) 52%(2024)/77%(2025)**(R²0.49/0.42, 2023年0%), 但缺西班牙季节预报; ERCOT 45天展望: 溢价中位+1.18$/MWh(P10−0.37~P90+3.54), 第1周热日叠加多云最高+2.0; 判定: 要建可用预警需①小时级②需求/温度预报③选负价常态市场 | 2026-09-29 |
| 西班牙负价概率季节预报链路 (PS-035) | `output/spain_negprice_forecast/index.html` | **补上PS-034缺的西班牙季节预报并建成完整链路**: Open-Meteo Seasonal(9光伏区×50成员×45天, 2026-09-29~11-12) 逐日短波→fleet τ(31.3GW, k=1.053尺度校正)→**可预报指数 S = 晴空气候(doy)×τ/负荷气候(月,工作日)** →标定 P(负价日); **跨年 AUC 0.722/0.721 双向一致**(2024↔2025) ⇒ S有真实排序能力; S五分位负价日占比 **0/6/27/32/26%**(Q1–Q5, 高档32% vs 全年基准18%); **季节偏差校正为必需一步** — 原始曲线用于当前秋季窗口高估近一倍(14.9% vs 实测7.8%) ⇒ 截距 −0.072→−0.143; 未来45天负价日概率均值**8.2%**(W1 10.5%→W7 2.0%随入秋走低); 对照PS-034: 同一"预报桥"思路在西班牙成立而在ERCOT失效 ⇒ **可预报性取决于驱动是否外生且可算** | 2026-09-29 |
| ENTSO-E 官方口径复核 + 2026 样本外 (PS-037) | `output/spain_entsoe_verification/index.html` | **换官方源不改变结论, 但暴露模型设定不足**: Energy-Charts ≡ ENTSO-E **逐位相同**(4变量×3年 r=1.000000/MAE=0/能量比1.000000, 2025光伏 r=0.999995) ⇒ PS-030~035 本就站在官方 TSO 口径上; **PS-035 单因子 S 在全新 2026 失效 (AUC 0.491≈无技能)**, 因 2026 起负荷通道主导(逐年 corr(负荷,负价日) −0.41→−0.51→**−0.59**, 资源通道 +0.18→−0.11), 而 S 只用月度负荷气候代理负荷; 改两因子(τ + **温度驱动负荷预报**, 2024–2026.09 标定 n=1001: P=+1.6487+0.0402×S−0.0588×负荷GW, 拟合AUC 0.809) 后 **2026 AUC 回 0.733**(含实际负荷 0.811); 官方口径逐年负价日率 **0%→12.6%→24.2%→42.3%**; 季节偏差仍为 **低估春(4–5月 70/42, 62/47)高估秋(10–11月 8/32, 2/21, 偏差+21.9pp)**, 校正后未来45天负价日概率 **6.8%**(原始25.9%, 校正后P10全为0) ⇒ **与PS-035的8.2%差1.4pp, 结论稳健于模型设定但前提是必须做季节校正**; ⚠跨年比较 pot_cs 须重新定标否则 τ 饱和到1 (2026用2025形状模板+年能量比合成) | 2026-09-29 |
| 西班牙负价模型 v3 · 趋势/logit/强度 (PS-038) | `output/spain_negprice_v3/index.html` | **修 PS-037 三个遗留问题**: ①**趋势项修好水位** — 负价日率 0→12.6→24.2→**42.4%**, 不加趋势时 2026 预测均仅 0.103, 加趋势回到 **0.459**(Brier **0.305→0.206**), 代价是 AUC 略降(0.819→0.785/0.814→0.762, 排序 vs 校准权衡); ②**logit 修好 P10 退化** — 不再 clip, 可做 Brier/可靠性, P10 不再为 0; ③**"负价小时强度"信息量最大** — 泊松对数链接 2026 AUC **0.900**(train23-25)/0.885(train24-25), 为全部设定最高, 但水平需重标定(0.52 vs 实际 2.76 h/日)且过度离散(≈2.7); ⚠**自由季节谐波过拟合** — 训练年 AUC 0.916/0.953 但 2026 掉到 0.762 且预测均 0.576 vs 实际 0.424(中高档严重过度自信), 证实"2 年秋季不足以学出季节形状", 由此解释 PS-035"只平移截距"反而更稳; **关键诊断: 2026 季节形状与往年完全不同**(峰值在 2–5月 78.6/61.3/70.0/61.3%, 而 9月仅 13.8% ⇒ 2026 的"高"集中在冬春而非秋季); **45天三情景**: A趋势口径 62.0%(上界) / B秋季残差口径 21.4% / C同年比例口径 11.3%(10-11月÷全年 0.261/0.271 × 42.4%) ⇒ **PS-035 的 8.2% 与 PS-037 的 6.8% 都落在 C 之下**(隐含"秋季继续异常偏弱"); 真正不确定性来自**口径选择(相差5倍)而非集合离散度**(成员 P10–P90 仅几 pp) | 2026-09-29 |
| 西班牙负价"爆发阈值"模型 (PS-039) | `output/spain_negprice_threshold/index.html` | **负价是阈值过程, 不是线性时间过程**: 用 2015-2026 **141 个月**长面板(零缺口), 以**光伏发电÷需求(光伏份额)**为驱动; **阈值 θ=16.0%**(月度), 超阈值斜率 **379 h/单位份额**, → **MAE 11.0 vs 线性趋势 17.5 h/月**(R² 0.339 vs 0.214) ⇒ PS-038 的线性趋势应被份额阈值取代; **阈值随季节变**: 春季(4-5月)约 **25-26%**(2023 份额24.8%→0h, 2024 27.4%→71h/月), 秋季(10-11月)仅 **10.5%**(专用拟合 n=22 R²=0.875; 2024 份额13.8%→2.5h, 2025 19.3%→10.5h) ⇒ 用全年单一阈值判秋季会高估; **秋季2026外推**: 2025年10-11月光伏7.4/负荷38.5 TWh(份额19.3%) × 2026/2025的1-9月光伏+21.1%÷负荷+2.9% ⇒ **份额22.7%** ⇒ 负价日率 **8.6%(秋季阈值)~17.1%(全局阈值/月份FE)**; **情景从 6.8%–62.0%(9倍) 收敛到 8.6%–17.1%(约2倍), 中心9%–11%** ⇒ PS-035的8.2%与PS-037的6.8%从"离群偏低"变为区间下沿正常值, **PS-038情景A的62%被否掉**; ⚠12年价格里只有3年有负价(2015-2023恒为0), 扩样本买到的是**阈值位置**而非阈值以上斜率; 负荷已于 2026-09-29 回填完成(补齐2018-07~12), 补齐前后 θ 不变 | 2026-09-29 |

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
| `download_spain_seasonal.py` | Open-Meteo 45天集合预报下载(西班牙9光伏区, 50成员×45天) | Open-Meteo seasonal | 无key, 窗口 2026-09-29~11-12 |
| `test_esios_api.py` | ESIOS API 连通性 + WAF 判定自检(退出码3=被Imperva拦截) | ESIOS API | 需 ESIOS_API_TOKEN, 支持 ESIOS_PROXY |
| `download_spain_esios.py` | ESIOS 分技术出力/需求/电价下载(代理可感知+按月续传) | ESIOS API | `--check`/`--list`/`--start --end`; 需换网或代理(PF-013) |
| `test_entsoe_api.py` | ENTSO-E 连通性/鉴权自检(退出码4=缺token, 与403拦截区分) | ENTSO-E API | 需 ENTSOE_API_TOKEN; 无 token 亦可用于判断端点可达性 |
| `download_spain_entsoe.py` | ENTSO-E 西班牙 A44日前价/A75分技术发电/A65负荷下载(按月续传) | ENTSO-E API | `--check`/`--start --end`/`--docs`; 免注册但需免费 token(PS-036) |
| `download_spain_temperature.py` | 西班牙 9 光伏区逐日 Tmax/Tmin/Tmean 下载 | Open-Meteo Archive | 无key, 2022-12-01~2026-09-28, 1398 天(PS-037) |
| `verify_seasonal_vs_gfs.py` | 45天预报 vs ERA5/GFS10天 逐lead误差 | Open-Meteo seasonal+archive+historical | 无key |
| `prep_ercot_wind_fleet.py` | GEM 风电→ERCOT 点位清单(按年, 0.1°去重聚合) | GEM wind 2026-08 | 165 点位 37.9 GW |
| `prep_spain_pv_fleet.py` | GEM 光伏→西班牙采样点(按年, 网格聚合) | GEM solar 2026-08 | 212 点位 27.66 GW |
| `download_spain_data.py` | 西班牙三源下载(NASA POWER 辐照 + PVGIS 校验 + Energy-Charts 发电/电价) | NASA POWER / PVGIS / Energy-Charts | 全免注册 |
| `prep_spain_pv_fleet_multi.py` | GEM 光伏→西班牙多点位多年份容量清单(按年回推) | GEM solar 2026-08 | 120 点位, 2023/24/25 各 ~96% 覆盖 |
| `download_spain_data_multi.py` | 西班牙三年数据下载(NASA POWER + Energy-Charts) | NASA POWER / Energy-Charts | 全免注册, 2023-2025 |
| `download_nasa_power_ercot_pv.py` | ERCOT 光伏 136 点位 NASA POWER 逐时辐照/气温 | NASA POWER hourly | ⚠须 `time-standard=UTC`(默认LST), 2025-01~2026-09 |
| `download_hrrr_wind_2025_2026.py` | HRRR 80m 风速+2m 气温批量下载(165 点位) | Open-Meteo historical-forecast | 无key, 14,736h |
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
| `model_seasonal_shortfall_risk.py` | 季节预报50成员辐照→光伏缺口风险概率化(晴朗基准缓存+fleet加权+历史τ分布相对校准+连阴/危险组合) | seasonal JSON + 物理缺口CSV | seasonal_shortfall_risk*.csv + streak |
| `rebuild_full_chart_arrays.py` | 重建完整逐lead误差数组(含GFS lead1-5) | series JSON | chart_arrays_full.json |
| `nsrdb_pvlib_power.py` | NSRDB 辐照→pvlib PVWatts 出力→EIA-930 对比 | 辐照 nc + EIA CSV | 出力 CSV + 精度统计 |
| `nsrdb_eia_comparison.py` | 模型 vs 实际深入对比(昼夜/日能量/爬坡/事件日) | 出力 CSV | 对比摘要 md |
| `build_nsrdb_pvlib_report.py` | 生成 NSRDB+pvlib 验证 HTML 报告 | 出力 CSV + 辐照 nc | output/nsrdb_pvlib_2022-07/*.html |
| `build_seasonal_risk_report.py` | 生成季节缺口风险 HTML 报告(τ轨迹/逐周/连阴/明细) | seasonal_shortfall_risk*.csv + streak | output/seasonal_shortfall_risk/index.html |
| `model_wind_power_shortfall.py` | 风电缺口×电价: HRRR 80m→功率曲线→fleet潜力→缺口/低风异常→弹性(含机制检验A~F) | hrrr_wind80m npz + panel | wind_power_hourly / wind_shortfall / wind_elasticity csv |
| `build_wind_shortfall_report.py` | 生成风电缺口×电价 HTML 报告(双斜率/时段/负价频率/弹性表) | wind_power_hourly + wind_elasticity | output/wind_shortfall_elasticity/index.html |
| `build_spain_market_survey_report.py` | 西班牙市场数据调研报告(实时拉OMIE验证+数据源对比) | OMIE 公开文件 | output/espana_esios_survey/index.html |
| `model_spain_pv_power.py` | 西班牙光伏链路: NASA POWER→pvlib跟踪→fleet潜力→ILR标定→缺口→电价弹性 | nasa_power npz + energy_charts | data/spain/*.csv |
| `build_spain_minchain_report.py` | 西班牙最小链路 HTML 报告(月能量/ILR曲线/价格-出力) | data/spain/*.csv | output/spain_minchain/index.html |
| `model_spain_pv_regime.py` | 西班牙光伏多年市场区间: 逐年ILR标定→缺口/负价机制→晴空vs天气缺口弹性 | nasa_power multi npz + energy_charts | data/spain/spain_regime_*.csv |
| `build_spain_regime_report.py` | 西班牙多年对比 HTML 报告(负价/机制/弹性) | spain_regime_*.csv | output/spain_regime/index.html |
| `build_ercot_pv_potential.py` | ERCOT 光伏全天候潜力重建(NASA POWER → pvlib → PVWatts, ILR逐年标定) | nasa_power npz + panel | ercot_pv_potential_2025_2026.csv |
| `reversibility_test_shortfall.py` | 缺口成因判据可逆性检验(6格 × ln/水平 × 单独/+水平) | panels + spain_regime_hourly | reversibility_matrix.csv |
| `build_reversibility_report.py` | 可逆性检验 HTML 报告(矩阵/双斜率/边界) | reversibility_matrix.csv | output/reversibility_shortfall/index.html |
| `model_shortfall_fingerprint.py` | 缺口工况指纹: 分位分组→低价/负价频率/需求/时段(6指纹) | panels + pv_potential + spain_regime_hourly | shortfall_fingerprint{,_summary}.csv |
| `build_fingerprint_report.py` | 缺口工况指纹 HTML 报告(高档vs低档/时间截面) | shortfall_fingerprint_summary.csv | output/shortfall_fingerprint/index.html |
| `model_forecast_price_bridge.py` | 缺口→电价日尺度转移函数(ERCOT白天溢价 / 西班牙负价日) + 季节预报45天展望 | shortfall_physical + panels + seasonal_shortfall_risk | forecast_bridge_calibration.csv + forecast_price_outlook.csv |
| `build_forecast_bridge_report.py` | 转移函数与45天展望 HTML 报告 | forecast_bridge_calibration + outlook | output/forecast_price_bridge/index.html |
| `model_spain_negprice_forecast.py` | 西班牙负价日概率季节预报(S指数标定+τ尺度校正+季节偏差校正+逐成员45天传播) | seasonal_spain + spain_regime_hourly + spain_solar_hubs_multi | spain_negprice_calibration.csv + spain_negprice_outlook.csv |
| `build_spain_negprice_report.py` | 西班牙负价概率季节预报 HTML 报告(标定曲线/AUC/45天展望) | spain_negprice_calibration + outlook | output/spain_negprice_forecast/index.html |
| `verify_spain_entsoe_official.py` | ENTSO-E 官方口径逐日面板 + S 指数 + 2026 样本外/五分位/季节结构 | spain_entsoe_hourly + spain_regime_hourly + entsoe | spain_official_{daily,quintile,yearly}.csv |
| `model_spain_negprice_v2.py` | 负价日两因子模型(τ+S+温度驱动负荷) + 季节偏差校正 + 逐成员45天 | spain_official_daily + temp json + seasonal_spain + hubs | spain_negprice_v2_{skill,outlook}.csv |
| `build_spain_entsoe_verification_report.py` | 官方口径复核 + 2026 样本外 HTML 报告(比对/模型设定/五分位/展望) | spain_official_* + v2_* | output/spain_entsoe_verification/index.html |
| `model_spain_negprice_v3.py` | 负价 v3: 趋势项 + logit + 泊松强度 + 季节谐波; AUC/Brier/可靠性评估 + 三情景45天 | spain_official_daily + temp json + seasonal_spain + hubs | spain_negprice_v3_{skill,skill_train23,reliability,outlook,scenarios}.csv |
| `build_spain_negprice_v3_report.py` | 负价 v3 HTML 报告(逐月矩阵/设定比较/可靠性/三情景展望) | spain_negprice_v3_* | output/spain_negprice_v3/index.html |
| `build_spain_long_panel.py` | 西班牙 2015-2026 逐月长面板(价格/负荷/光伏 → 负价h/份额) | entsoe raw 月缓存 + energy_charts 年 JSON | spain_long_panel.csv |
| `model_spain_negprice_threshold.py` | 负价"爆发阈值"模型(折线阈值 θ 网格搜索/月份FE/样本外/秋季外推) | spain_long_panel.csv | spain_negprice_threshold{,_fit}.csv |
| `build_spain_threshold_report.py` | 阈值模型 HTML 报告(散点/季节阈值/情景收敛) | spain_negprice_threshold_* | output/spain_negprice_threshold/index.html |
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