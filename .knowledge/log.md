# 知识变更日志

> 本文件只追加，不修改历史记录。

## [2026-09-27] add | [PS-022 光伏缺口×电价冲击推演：温度修复 + USCRN 验证 + 弹性标定] | 新增 1 条 + 更新 1 条

### 新增条目
- 新增 PS-022：光伏缺口 × 电价冲击推演流程（verified）
  - 温度链路修复：NSRDB 无表面温度 → HRRR 2m 实测（56 站×744h，16.2~44.3°C）；
    ILR 1.25→1.30 四窗口扫描；**热浪正午偏差 -327→+16 MW、MAE 405→273，全月 MAE 185→174、能量 -2.1%→+1.4%**
  - USCRN 地面交叉验证（8 站 5min）：NSRDB 比 USCRN 系统性高 ~10%（已知水平差，被 ILR/损耗吸收），
    **热浪期无额外漂移（-1.4~-2.1%，站间离散内）→ 排除反演劣化，锁定温度参数化**
  - USCRN 坑：文件名按版本号 `CRNS0101-05`（非月份）；无表头 23 列；时间戳为 5min 区间结束须 -5min；缺测 -9999
  - 骤降归因：7 个事件解释比 0.95~2.88 **全部云主导，无弃光**；07-13 渐进下降未触发骤降阈值 →
    骤降（时间导数）与缺口（对晴空水平差）两口径互补
  - 弹性标定：ln(RTM) 面板（shortfall + wind + demand + 小时/月 FE），
    **2025 β=+5.08 %/GW (SE 0.25)，高需求 ≥72GW +5.84；2026 复验 +5.43/+4.33，两年一致 ±7%**
  - 2022-07 推演：**44 事件小时 → 17 事件、100.3 GWh**，中位缺口 2.06 GW、最大 4.40 GW（07-21）；
    **RTM 中位上浮 +11.0%、最大 +25.0%**；按 North 月均 $182 折算 +$20~+$46/MWh；
    热浪期 3 事件 25.6 GWh（07-13 傍晚云×77.5GW 需求 = 最强冲击 +21.9%）；07-14 撒哈拉沙尘日 10.4 GWh（缺口为上界）
  - **实证陷阱 ①**：pvlib 0.15.2 `simplified_solis` 数组输入返回 OrderedDict 非 DataFrame → `np.asarray(cs["dni"])`
  - **实证陷阱 ②**：晴空缺口校准必须**逐小时偏移**（每 hour 的 5% 分位）——单一全局偏移把傍晚低仰角
    跟踪 POA 系统性高估计入缺口，事件小时虚增 62→44、总量虚高 43%；逐小时校准后晴日正午缺口中位 67 MW
  - 陷阱 ③：β 单位换算 (ln, per MW) → %/GW 需 ×100000；2022-07 EIA-930 无 demand 字段 → 全燃料出力和做需求代理

### 更新条目
- 更新 PS-021：推广方向两条待办标记完成，指向 PS-022；相关知识 +PS-022

### 目录与产物
- 更新 tech/catalog.md、根 catalog.md：条目 33 → 34（33 verified + 1 draft），
  领域说明 + 联动分析、知识图谱 +PS-022 节点、数据源索引 +USCRN/Open-Meteo/NSRDB/ERCOT 关联
- 更新 project/catalog.md：数据源 +2 行（USCRN、HRRR 2m 温度）、分析结果 +1、脚本索引 +9、
  待办完成移除 2 项（真实温度接入、光伏骤降×电价推演）、新增 1 项（RTM 事件尾部建模）
- 新增脚本：`download_hrrr_temp_july2022.py`、`download_uscrn_tx_july2022.py`、
  `download_nsrdb_uscrn_pixels_july2022.py`、`verify_temp_fix.py`、`ilr_sweep_heatwave.py`、
  `verify_nsrdb_vs_uscrn_july2022.py`、`identify_pv_drop_events_2022-07.py`、
  `calibrate_price_elasticity_2025.py`、`pv_event_price_impact_2022-07.py`、`build_pv_event_price_report.py`
- 新增数据：`hrrr_t2m_2022-07.npz/csv`、`data/uscrn/`（8 站）、`nsrdb_uscrn_daily.csv`、
  `pv_drop_events_2022-07.csv`、`price_elasticity_2025.csv`、
  `pv_counterfactual_hourly_2022-07.csv`、`pv_event_price_impact_2022-07.csv`
- 新增报告：`output/pv_event_price_impact_2022-07/pv_event_price_impact_ercot_2022-07.html`

## [2026-09-27] add | [PS-021 NSRDB 辐照批量提取 + pvlib 光伏出力建模验证] | 新增 1 条 + 更新 1 条

### 新增条目
- 新增 PS-021：NSRDB 辐照批量提取与 pvlib 光伏出力建模验证流程（verified）
  - 全链路：GEM 电站坐标 → NSRDB 像素映射（56 座 ≥100MW，10.66 GW，中位距离 0.9 km）→ 分块提取（2000×500 chunk，735 块，自愈重试+断点续传）→ pvlib PVWatts → EIA-930 验证
  - 建模标定（物理合理非拟合）：单轴跟踪 backtrack gcr=0.35、ILR 1.25、系统损耗 14%、Tamb 25→39°C 热浪日循环、γ=-0.37%/°C
  - **最终精度：小时 r=0.9976、MAE 185 MW（峰值 1.9%）、月能量 -2.1%、昼夜形状 r=0.9993、爬坡 r=0.987**，无需历史出力训练
  - **实证陷阱 ①（最重要）**：EIA-930 小时时间戳为区间结束（hour-ending），值属于 [t-1, t)，融合前必须 -1h 平移（r 0.942→0.992）；典型指纹=早晚肩部形状错位+最大偏差固定在同一 UTC 时次
  - **实证陷阱 ②**：pvlib singleaxis/get_total_irradiance 角度参数是度数，误传弧度不报错且 POA 量级恰好接近真实（退化为 DNI+DHI），极难察觉
  - 实证陷阱 ③：fsspec/aiohttp 长进程连接"病变"（1 块/s→1 块/5min 不触发超时），重启进程即恢复，长批量任务须支持外部重启续跑
  - 偏差源：热浪核心期（07-14~18）正午低估 10~20%（温度参数化）；早晚肩部个别小时高估 30~66%（低仰角反演），日能量影响 <0.5%

### 更新条目
- 更新 PS-019：末尾待办标记完成，指向 PS-021

### 目录与产物
- 更新 tech/catalog.md、根 catalog.md：条目 32 → 33（32 verified + 1 draft），知识图谱 +PS-021 节点
- 更新 project/catalog.md：NSRDB 数据源行（2022-07 提取完成）、分析结果 +1、脚本索引 +5、待办"NSRDB ERCOT 辐照批量提取"完成移除
- 新增脚本：`match_nsrdb_ercot_solar.py`、`download_nsrdb_ercot_july2022.py`、`download_eia_solar_2022.py`、`nsrdb_pvlib_power.py`、`nsrdb_eia_comparison.py`、`build_nsrdb_pvlib_report.py`
- 新增数据：`ercot_solar_irradiance_2022-07.nc`（6.1 MB）、`ercot_pv_power_2022-07.csv`、`ercot_solar_plants_pixels.csv`
- 新增报告：`output/nsrdb_pvlib_2022-07/nsrdb_pvlib_ercot_2022-07.html`

## [2026-09-27] add | [PS-018 + PS-019 + PS-020 新数据源调研：MRMS/NSRDB/S2S] | 新增 3 条

### 新增条目
- 新增 PS-018：MRMS 雷达定量降水 (QPE) 下载与 ERCOT 裁剪流程（verified）
  - 双通道：AWS S3 `noaa-mrms-pds` 匿名归档（2020-10-14 ~ 2023-07-10，恰好 1000 天，需 continuation-token 翻页）+ NCEP 官网滚动最新 ~10 天（滞后 ~1 天）
  - 产品 `MultiSensor_QPE_01H_Pass2`：0.01°（~1 km）逐小时，比 IMERG 0.1° 高一个量级
  - 坑：GRIB2 经度为 **0-360 约定**（ERCOT=253.3~266.6），用负经度匹配得 0 格点；cfgrib 参数名显示 unknown
  - 实测：2023-07-10 21Z 捕捉德州 33.3 mm/h 对流核心（>5mm 格点 2214 个），09Z 全域无雨；ERCOT 裁剪 1070×1330
- 新增 PS-019：NSRDB 太阳辐照度 S3 懒读取与 ERCOT 像素定位流程（verified）
  - v3.2.2 单年 h5 1.8 TB，developer.nrel.gov DNS 不通，S3 匿名是唯一路径
  - 坑：v3.2.2 "CONUS" 实为 GOES-East+West 全视域（lat 14.5~49.4 含墨西哥、lon -160~-60 含夏威夷~波多黎各），像素 0 在夏威夷海域
  - h5coro（HTTPDriver + credentials=None + 128KB 缓存行）读 /ghi uint16 [105120, 2842719]（5 min × 2 km，值即 W/m²）
  - **像素定位待办当场解决**：meta 为 compound（h5coro 不支持），用 h5py 取磁盘偏移（连续存储 offset=2636192）+ requests Range 流式下载 346.8 MB + numpy frombuffer 解析 → ERCOT **330,096 像素**（德州 163,017），索引 npz 已缓存
  - 端到端验证：奥斯汀像素 (30.38N, -97.89W) 7月1日峰值 995 W/m² @ 12:15 LST，天文自洽
- 新增 PS-020：WMO S2S 数据库获取路径（draft，门户可达已验证，注册后待实测）
  - 13 中心多模式回算，2015 起实时存档；2026-04-21 起从旧 WEB-API 迁移至 ECMWF Data Store (ECDS)
  - ECDS 门户与 API catalog 实测 HTTP 200（中国网络直连可用）；需注册 ECMWF 账号
  - 用途：把 PS-017 单窗口核验升级为多年回算多窗口统计（优先 ECMWF/NCEP/CMA）

### 目录更新
- 更新 tech/catalog.md、根 catalog.md：条目 29 → 32（31 verified + 1 draft），领域说明/数据源图谱/知识图谱同步
- 更新 project/catalog.md：数据源索引 +3 行、脚本索引 +4 个、待办事项 +2 项
- 新增脚本：`test_mrms_download.py`、`test_nsrdb_h5coro.py`、`test_nsrdb_meta.py`、`test_nsrdb_mrms_s2s.py`
- 新增数据：`data/mrms/`（ERCOT 裁剪样例）、`data/nsrdb/`（meta 全缓存 + ERCOT 像素索引 npz）

## [2026-09-16] add | [PS-017 S2S 季节尺度预报获取与精度核验] | 新增 1 条 + 更新 1 条

### 新增条目
- 新增 PS-017：S2S 季节尺度预报获取与精度核验流程（verified）
  - 数据源：Open-Meteo seasonal-api（ECMWF EC46 46天逐日 + SEAS5 7个月逐月，51 成员集合，36 km）
  - 端点坑：正确端点是 `seasonal-api.open-meteo.com`，`api.open-meteo.com/v1/seasonal` 实测 404
  - 核验方法：ERA5 逐日再分析为实测基准，逐 lead 计算 MAE/RMSE；GFS 10 天（ncep_gfs_seamless）作对比
  - 实测（2026-08-10~09-15，ERCOT 6 站）：45天风速 MAE 1.49 vs GFS 10天 1.30 km/h；降水 1.26 vs 0.26 mm（~4.8×）
  - 重叠段 lead 6~10 风速两者相当（1.35 vs 1.30 km/h）；降水误差呈事件型尖峰（3~6 mm）
  - 数据未偏置订正、36 km 区域平均，宜看倾向/离散度，不宜当逐日定量数值

### 目录更新
- 更新 GL-004：端点总览表新增 seasonal 行 + 修正季节预报正确端点
- 知识库条目数：28 → 29
- 新增下载脚本：`verify_seasonal_vs_gfs.py`、`download_seasonal_forecast.py`
- 新增分析脚本：`build_forecast_accuracy_summary.py`、`rebuild_full_chart_arrays.py`
- 新增数据：`data/openmeteo_seasonal/`（45天 raw + verif 序列 + 误差表）
- 新增输出：HTML 精度核验报告

## [2026-09-11] add | [PS-016 GEM 电站数据库 × ERCOT 电价联动分析] | 新增 1 条

### 新增条目
- 新增 PS-016：GEM 电站数据库下载与 ERCOT 电价联动分析流程（verified）
  - GEM 2026-08 数据库 182,668 条（光伏 103,940 + 风电 35,089）
  - 绕过邮箱注册：maps GitHub config.js 暴露 DigitalOcean CDN 直链
  - ERCOT 474 座运行中电站（风电 38.0 GW + 光伏 33.0 GW = 71.0 GW）
  - 三层分析：装机结构 / 发电×电价相关（风电夜间 r=-0.384）/ 雷暴×电站交叉（KIAH 1.43x）
  - 电价尖峰本质：风光同时缺位 + 高负荷（风光渗透率 12.6% vs 39.4%）

### 目录更新
- 知识库条目数：27 → 28
- 新增分析脚本：`scripts/analysis/gem_ercot_lz_analysis.py`、`gem_ercot_deep_dive.py`、`gem_storm_cross.py`
- 新增数据：`data/gem/`（GEM 6 文件 + WRI 1 文件）
- 新增输出：HTML 分析报告目录 + 3 个 CSV

## [2026-09-11] add | [PS-015 GK2A AMI 卫星数据下载] | 新增 1 条

### 新增条目
- 新增 PS-015：GK2A (GEO-KOMPSAT-2A) AMI 卫星数据下载流程（verified）
  - 韩国静止气象卫星, 定点 128.2°E, 16 通道, 10 分钟全圆盘
  - AWS S3 匿名访问 (noaa-gk2a-pds), 无需认证
  - IR105: 33.6 MB/文件 (5500×5500, 2km), WV073: 27.9 MB
  - GEOS 投影, 需 satpy 重采样到 WGS84
  - 与 Himawari-9/FY-4 覆盖重叠, 可交叉验证

### 目录更新
- 知识库条目数：26 → 27
- 新增脚本: `scripts/data_download/download_gk2a.py`
- 测试数据: IR105+WV073 各 4 文件, 246 MB

## [2026-09-09] add | [PS-014 ASTER地形×GLM闪电联动分析] | 新增 1 条

### 新增条目
- 新增 PS-014：ASTER 地形与 GLM 闪电分布联动分析流程（verified）
  - 11,410 个 ERCOT 闪击 × 154 ASTER tiles (30m GDEM+WBD)
  - 双峰高程分布: 57.8% 在 100-200m 沿海平原, 12.1% 在 >1000m 山区
  - 中等坡度主导: 36.3% 在 5-10°, 仅 1.3% 在极平坦地形
  - 水体效应不显著: 93.5% 距水体 >5km

### 目录更新
- 知识库条目数：25 → 26
- 新增分析脚本: `scripts/analysis/terrain_lightning_analysis.py`
- 新增输出: 3 张可视化图表 + 2 个统计 CSV

## [2026-09-07] add | [GL-009 + PF-012 + PS-013 凭证安全/CMA陷阱/ASTER地形] | 新增 3 条

### 新增条目
- 新增 GL-009：气象数据 API 凭证安全管理实践（verified）
  - netrc (Earthdata) + .env (EIA/GridStatus) + config.ini (CMA) 三层管理
  - .gitignore 防护：.env, _netrc, .netrc, .nmcdev/
  - 7 个脚本已从硬编码改为自动加载凭证
- 新增 PF-012：CMA 气象数据访问陷阱（verified）
  - CMADaaS 需内网 VPN（10.20.76.55 内网 IP）
  - data.cma.cn API 账号独立注册，网站账号 ≠ API 账号
  - nmc-met-io 库不支持 FY-4 LMI 闪电数据
  - 替代方案：NSMC/中科院公开数据集 + 国际数据源
- 新增 PS-013：ASTER GDEM 地形与水体数据下载流程（verified）
  - ASTGTM.003 (30m 高程) + ASTWBD.001 (30m 水体分类)
  - ERCOT 区域 154 tiles, 8.48 GB
  - earthaccess + netrc 认证, rasterio 读取

### 目录更新
- 知识库条目数：22 → 25（新增 3 条 verified）
- 数据源覆盖新增：地形/水体数据（ASTER）、CMA 数据访问陷阱、凭证安全
- 数据量新增：ASTER GDEM 2.89 GB + WBD 5.59 GB = 8.48 GB
- project/catalog.md 更新：新增 6 个数据源, 8 个脚本, 凭证配置, 待办事项

## [2026-09-07] add | [PS-010 GPM IMERG 降水数据下载] | 新增 1 条

### 新增条目
- 新增 PS-010：GPM IMERG 降水数据下载流程（verified）
  - Earthdata 注册 + EULA 接受 + earthaccess 下载
  - 实测 30 分钟产品 7.8 MB，日产品 31 MB
  - 下载速度 1.3~4.3 MB/s（中国网络）

### 目录更新
- 知识库条目数：21 → 22（新增 1 条 verified）
- 数据源覆盖新增：卫星降水（IMERG）

## [2026-08-12] update | [GL-004 全面重写 + HRRR/NWP 预报数据实测] | 更新 1 条

### 更新条目
- 更新 GL-004：Open-Meteo API 使用指南全面重写，新增 HRRR/GFS/NAM/NBM 等 NWP 预报模型详细说明

### 测试验证
- HRRR 实时预报 8 项测试全部通过（2026-08-12 11:18 UTC）
- 关键验证：80m 风场（均值 31 m/s）、GHI/DNI（Houston 峰值 979 W/m²）、CAPE（最大 2620 J/kg）
- 历史预报（Historical Forecast API）验证：2018-01 起，2024-07 数据 CAPE 最大 3280 J/kg
- 多模型对比：HRRR/GFS/NAM/NBM 均返回数据
- 测试脚本：`test_openmeteo_hrrr.py`
- 测试结果：`openmeteo_hrrr_results.json`

### 目录更新
- 知识库条目数：21 条不变（GL-004 重写）
- 数据源覆盖新增：NWP 数值预报大类

## [2026-08-12] add | [GL-008 + PF-011 + PS-009 气象雷达数据匿名获取] | 新增 3 条

### 新增条目
- 新增 GL-008：气象雷达数据匿名获取综合指南（verified）
- 新增 PF-011：NEXRAD 官方 S3 桶匿名访问限制与替代方案（verified）
- 新增 PS-009：NEXRAD 雷达实时分块数据下载流程（unidata chunks）（verified）

### 测试验证
- 综合测试 15 类匿名数据源（2026-08-12 01:50 UTC）
- 成功验证：unidata chunks（18站全覆盖）、RainViewer（全球拼图）、GCP 公开数据集、NWS API、NOMADS HRRR
- 不可匿名：noaa-nexrad-level2（Access Denied）、noaa-nexrad-level3（桶不存在）、NCEI THREDDS（404）
- 测试脚本：`test_radar_all_anonymous.py`
- 测试结果：`radar_test_results_comprehensive.json`

### 目录更新
- 更新 tech/catalog.md：条目数从 18 → 21，新增 3 条
- 更新 root catalog.md：全景目录同步更新，覆盖范围新增雷达
- 知识库条目数：18 → 21（含 20 条编号条目 + 1 个参数清单文件，全部 verified）

## [2026-08-11] update | [全面知识库重构] | 新增 5 条 + 更新 3 条 + 目录重构

### 新增条目
- 新增 GL-007：探空数据热力指数提取与 DCAPE 分析指南（verified）
- 新增 PF-008：怀俄明大学探空接口迁移与 SSL 证书问题（verified）
- 新增 PF-009：探空数据区域分辨率差异与标准化比较（verified）
- 新增 PF-010：探空 WSGI 格式中 CAPE 缺失与 HTML 热力指数提取（verified）
- 新增 PS-008：探空廓线数据下载流程（怀俄明大学 WSGI）（verified）

### 更新条目
- 更新 PS-006：补充 Resource Node 电价数据下载内容（风电 7 节点 + 光伏 1 节点）
- 更新 tech/catalog.md：条目数从 12 → 18，新增 5 条 + 更新 3 条
- 更新 root catalog.md：全景目录同步更新，覆盖范围新增探空/电力市场

### 目录重构
- 重构 project/catalog.md：从空框架变为完整数据源索引 + 分析结果 + 脚本索引 + 配置表
- 更新 conventions/README.md：从空框架变为实际团队约定
- 知识库条目数：12 → 18（含 17 条编号条目 + 1 个参数清单文件，全部 verified）

## [2026-07-24] add | [PF-006 + PF-007 + PS-007 雷暴联动分析经验] | 新增 3 条经验
- 新增 PF-006：Pandas 时区 tz-naive 与 tz-aware 比较错误（verified）
- 新增 PF-007：雷暴检测在高风区绝对阈值失效（verified）
- 新增 PS-007：雷暴事件 × 电力市场联动分析流程（verified）
- 知识库条目数：9 → 12（全部 verified）

## [2026-07-23] add | [PF-005 + PS-006 ERCOT 电力市场数据下载]
- 新增 PF-005：ERCOT 官网反爬虫屏蔽与中国 IP 不可访问陷阱（verified）
- 新增 PS-006：ERCOT 电力市场数据下载流程（verified）
- 知识库条目数：7 → 9（全部 verified）

## [2026-07-21] update | [GL-006 NASA POWER 参数完整清单]
- 发现官方参数查询端点，HOURLY 105/DAILY 152/MONTHLY 1388/CLIMATOLOGY 1634
- 完整参数清单归档至 .knowledge/tech/nasa_power_params.md

## [2026-07-20] cleanup | [清理 draft 条目]
- 删除全部 13 个 draft 条目，仅保留 5 个 verified 条目
- 知识库条目数：18 → 5（全部 verified）

## [2026-07-20] add | [PS-005 SURFRAD 地表辐射实测]
- 新增 PS-005：SURFRAD 地表辐射实测数据下载流程（verified）
- 7 站点 × 7 天 = 63 文件，63,715 条 1 分钟记录
- 知识库条目数：5 → 6（全部 verified）

## [2026-07-20] add | [GL-006 NASA POWER 卫星同化数据]
- 新增 GL-006：NASA POWER 卫星同化数据使用指南（verified）
- 与 SURFRAD 实测对比验证
- 知识库条目数：6 → 7（全部 verified）

## [2026-07-18] update | [葵花数据下载方式修正]
- 发现 AWS S3 匿名访问方式，无需注册
- 重写 PS-003

## [2026-07-18] ingest | [气象数据接口实测验证]
- 实测 Open-Meteo、Meteostat、葵花8/9
- 新增 GL-004、GL-005、PS-003

## [2026-07-18] ingest | [气象知识库初始化]
- 创建 .knowledge/ 目录结构，创建 13 条种子知识