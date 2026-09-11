# 项目知识清单（当前项目特有）

> 最后更新: 2026-09-11
> 本分类记录气象项目特有的知识，跨项目通用知识见 tech/ 目录

## 项目数据源索引

| 数据源 | 类型 | 覆盖区域 | 时间范围 | 脚本 | 数据目录 | 状态 |
|--------|------|----------|----------|------|----------|------|
| Meteostat | 地面观测 | 中国46机场 | 2025-2026 | `download_china_airports_2025.py` 等 | `data/meteostat/` | 活跃 |
| Meteostat | 地面观测 | 东亚东南亚115机场 | 2025-2026 | `download_east_southeast_asia_*.py` | `data/meteostat/east_southeast_asia/` | 活跃 |
| Meteostat | 地面观测 | 美洲85机场 | 2025-2026 | `download_americas_airports_2025_2026.py` | `data/meteostat/americas/` | 活跃 |
| 怀俄明大学 WSGI | 探空廓线 | 德州3站 + 东亚7站 | 2026-07-13 ~ 2026-08-11 | `download_sounding_parallel.py` | `data/sounding/` | 活跃 |
| NEXRAD L2 实时分块 | 天气雷达 | ERCOT 18站 | 实时（秒级延迟） | `test_radar_all_anonymous.py` | 无持久数据 | 已验证 |
| Open-Meteo HRRR | NWP 数值预报 | ERCOT 6站（CONUS全境） | 实时预报+历史2018起 | `test_openmeteo_hrrr.py` | `data/openmeteo_hrrr_results.json` | 已验证 |
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
| 合计 | ~2,600+ | ~9.4 GB | ~2.7M | — |

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
| `test_cma_api.py` | CMA data.cma.cn API 连接测试 | data.cma.cn | 需CMA账号 |

### 分析脚本 (analysis/)

| 脚本 | 用途 | 输入 | 输出 |
|------|------|------|------|
| `sounding_analysis.py` | 探空基础分析(加载/插值/统计) | 探空CSV | HTML报告 + CSV |
| `sounding_deep_analysis.py` | 探空深度分析(统计检验/趋势) | 探空CSV | HTML报告 |
| `thunderstorm_ercot_analysis.py` | 雷暴×电价联动分析 | Meteostat + ERCOT | HTML报告 + CSV事件表 |
| `gem_ercot_lz_analysis.py` | 电站-LZ映射 + 装机结构分析 | GEM CSV | HTML报告 + CSV |
| `gem_ercot_deep_dive.py` | 发电×电价×事件三层深度分析 | GEM + ERCOT + EIA | HTML报告 + CSV |
| `gem_storm_cross.py` | 雷暴×电站坐标空间交叉 | Meteostat + GEM | CSV |

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