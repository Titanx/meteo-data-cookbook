# 数据源速查矩阵

**最后同步**: 2026-10-03
**用途**: 选源时先查本表；"已知限制"列里的坑在对应 PIT 条目里有排查信号与绕法。
**口径提醒**: 本表只记"能不能拿、拿的时候会怎样"，不记具体数值结论。

## 1. 气象 · 再分析与数值预报

| 源 | 变量 | 获取方式 | 凭证 | 已知限制 |
|----|------|----------|------|----------|
| Open-Meteo Archive | 温度 / 风(10m/**100m**) / 辐射 / 降水，小时，**ERA5 后端 1940 起** | REST JSON | 无 | 再分析网格，**不能当站点实测**；**风速默认 km/h**，须传 `wind_speed_unit=ms`（量级陷阱）→ `[RCP-20261026-001]`、`[PIT-20261026-001]`；pre-1979 段同质性慎用 |
| Open-Meteo Forecast | 同上，D1 起 | REST JSON | 无 | 多模式并存，必须显式指定 model，否则默认口径漂移 |
| Open-Meteo Historical Forecast | 过去某段的"当时预报" | REST JSON | 无 | 归档口径随模式升级而变，跨年比较需先做同质性检查 |
| Open-Meteo Previous Runs | 同一预报的 D1~D7 归档 | REST JSON | 无 | **逐 lead 同质性有陷阱** → `[PIT-20260929-003]` |
| Open-Meteo Seasonal | 45 天，多成员 | REST JSON | 无 | 季节尺度，不可当日尺度用 → `[RCP-20260916-001]` |
| NASA POWER | 温度 / 辐照 / 风速，日或小时 | REST JSON / CSV | 无 | **辐照=CERES（SYN1deg/FLASHFlux）、气象=MERRA-2/GEOS-IT**；点位代表性有限；缺省 LST，须传 `time-standard=UTC` → `[MTD-20260720-001]` |
| Meteostat | 地面站小时观测（日/月也有） | Python 包 2.x（`daily()` 函数式）/ `data.meteostat.net/daily/{年}/{站}.csv.gz` | 无 | 域名迁到 data.meteostat.net（旧 bulk 停更）；**中国站日/小时 prcp 均 100% DWD MOSMIX 模式值，不可当雨量计观测**；美/澳日 prcp=ghcnd 观测、德=dwd_daily；日文件尾部 MOSMIX 填到今天+4~7 天；2.x 可 `providers=[GHCND]` 强制观测但滞后约 14 个月；区域批量下载陷阱 → `[MTD-20260718-002]`、`[PIT-20260719-001]`、`[PIT-20260930-007]` |
| IEM ASOS（机场逐时观测） | 温度 / 露点 / 湿度 / 风 / 阵风 / 小时降水 + **METAR 原文列** | HTTP GET（asos.py，单站整段一次请求） | 无 | **单位全英制**须换算；`missing=blank` 已废弃（422）；站清单端点改版需硬编码；近实时另走 aviationweather → `[RCP-20261016-001]`、`[PIT-20261016-001]` |
| SURFRAD | 地表辐照实测，分钟级 | HTTP 目录 | 无 | 只在美国境内（11 个站点目录），历史有限 → `[RCP-20260720-002]` |
| SOLRAD | 地表辐照实测，分钟级 | HTTP 目录 | 无 | NOAA GML 另一条网络，只在美国（9 个站点目录），目录结构与 SURFRAD 相同 → `[RCP-20260720-002]` |
| BSRN | 地表辐照实测，**基准级**，1–3 分钟 | PANGAEA（匿名）/ ftp（需账号） | **匿名**（仅 ftp 通道需向 WRMC 申请） | 覆盖矩阵 **78 个站行**、**20 站活跃到 2026**；**列结构逐站逐年代不同**（实测 16/21/29 列）、缺测为空字段、**无 QC 列**；时效 **1–3 个月** → `[RCP-20260930-001]` |
| 怀俄明大学探空 | 廓线热力指数（CAPE/DCAPE） | WSGI / HTML | 无 | 接口迁移 + SSL + 部分站点无 CAPE → `[PIT-20260811-001]`、`[PIT-20260811-003]` |
| **IGRA v2.2** | 全球探空廓线（温/风/湿，1905 起）+ 月平均 + 站史 | NCEI 定宽 ASCII + zip（匿名） | 无 | 站清单在 pub/data/igra/；全周期在 data-por/；-9999/-8888 双缺测码；延迟约 2 天；与怀俄明互补（无算好的指数） → `[RCP-20261025-001]`、`[PIT-20261025-001]` |
| **GHCNd** | 站点日值（降水/气温等） | HTTP 目录（NCEI WAF） | 无 | 站点最多（清单约 13 万站）；**日值记的是"当地日"**，与 UTC 口径直接比会系统性惩罚 → `[PIT-20261003-002]` |
| **GHCNh** | 站点小时值（降水/气温/风等） | AWS 公开桶 noaa-ghcnh-pds（NODD，匿名） | 无 | **不在 NCEI 的 data 路径下**，走 S3 桶；`precipitation` 是"自上次观测累积"、**时间戳非整点**、与 GHCNd **站点不等集** → `[PIT-20261003-003]` |
| **GSOD** | 站点日值摘要（降水/气温/风等） | HTTP 目录（NCEI） | 无 | 单站文件名是 **11 位无连字符**站号（与 GHCNd 命名习惯不同，带连字符会 404） |

## 1b. 观测型降水（站点与格点基准）

| 源 | 变量 | 获取方式 | 凭证 | 已知限制 |
|----|------|----------|------|----------|
| CPC-Gauge（CPC 统一雨量计分析） | 日降水，0.5° | ftp.cpc.ncep.noaa.gov 目录 | 无 | 文献常引的 downloads.psl.noaa.gov 实测 **502**，改走 ftp 镜像；历史段在 V1.0，近年在 RT |
| GPCC | 日/月降水格点 | opendata.dwd.de 目录 | 无 | 免注册；产品分档多（First Guess / Full Data / Monitoring），**别混档比** |
| CHIRPS v2.0 | 日降水，0.05°/0.25° | data.chc.ucsb.edu 目录 | 无 | 免注册；年文件约 63 MB 级 |
| SC-Earth | 站点日值（含风速），1950–2019 | Zenodo 4762586 | 无 | 16 个 nc / 23.3 GB；**Zenodo 需先过 DNS（裸域被屏蔽）** → `[PIT-20261002-001]` |
| GHCNdgp | 0.25° UTC 日降水，2020–2025 | Zenodo 21482358 | 无 | 单文件 tar.gz 约 249 MB；**专为 UTC 口径预报检验设计**，含逐站推断报告时间元数据 |
| WeatherReal-ISD | 站点小时，2021–2023 | GitHub microsoft/WeatherReal-Benchmark | 无 | 数据文件是 **Git LFS 指针**，真实文件约 546 MB；Synoptic 版本需联系厂商 |
| EM-Earth | 0.1° 逐小时 UTC，1950–2019 | FRDR（加拿大） | **Globus 登录** | 非匿名直连 |
| MSWEP | 多源融合降水，0.1° | gloh2o.org | **需注册** | CC-BY-NC，**禁商用** |
| IGLD（CMA 一体化陆面数据集） | 次小时站点观测 | data.cma.cn | **需注册** | 实测 API 连接超时，与 `[PIT-20260907-001]` 一致 |
| **TPDC（青藏高原科学数据中心）** | 中国区均一化格点（HCD01 七要素 1961–2022 日尺度 0.1°；同组前代 RH/WS 1979–2017 月尺度 0.25°） | SPA JSON API + HTTPS/FTP | **无**（开放获取） | <1GB 文件走 HTTPS（batchDownloadByFileId）字节可精确校验；**>1GB 仅 FTP** 且端口 21 对代理/海外出口 SYN 静默丢弃（需大陆直连）；真实 API 路径是**双层 file 前缀** → `[RCP-20261030-001]` |

## 1c. 海洋与沿海（offshore wind 备用）

| 源 | 变量 | 获取方式 | 凭证 | 已知限制 |
|----|------|----------|------|----------|
| NOAA CORA（Coastal Ocean Reanalysis） | 沿岸逐时水位 + 波浪 bulk 参数（Hs/Tp/DIR），1979 起 | AWS NODD 匿名桶（NetCDF + zarr + intake 目录） | **无** | GEC 域（东/湾/加勒比）1979–2022 ~500m；**PAC 域（西海岸/夏威夷/东南阿拉斯加）1979–2025 ~200m，2026-10 首发**；**模式再分析非观测**，v0.9/v1.0/v1.1 全弃用（v1.0 有错误长期趋势），官方 Known Issues 自曝 PAC 16hr 振荡伪影与 2009/2019 偏差数十分米；引用必须锁 v1.1.1 → survey `raw/surveys/cora_noaa_coastal_reanalysis_survey.md` |

## 2. 卫星与遥感

| 源 | 变量 | 获取方式 | 凭证 | 已知限制 |
|----|------|----------|------|----------|
| Himawari-8/9 | 多通道辐射，10 分钟 | JMA P-Tree，bz2 | 无 | 目录按通道/日期分片，命名规则需按 `[RCP-20260718-001]` 拼 |
| GOES-16/18/19 | ABI 辐射 + GLM 闪电 | AWS 公开桶 | 无 | 桶可匿名读；分片目录层级深 → `[RCP-20260720-001]`、`[RCP-20260907-002]` |
| GK2A | AMI 通道 | KMA API | 需 key | 凭证申请与限流 → `[RCP-20260911-001]` |
| FY-4A LMI | 闪电 | NSMC | 需注册 / 受限 | 部分入口不可达 → `[PIT-20260907-001]`、`[RCP-20260907-003]` |
| GPM IMERG | 降水 | NASA GES DISC | 需 Earthdata 登录 | 检索接口有坑 → `[RCP-20260907-001]` |
| ASTER GDEM / WBD | 地形与水体 | NASA Earthdata | 需登录 | 分幅下载后需拼接 → `[RCP-20260907-004]` |
| **OSTIA 海面温度/海冰（UKMO）** | L4 逐日 foundation SST + 海冰浓度 + error 场 | Copernicus Marine `copernicusmarine` 工具箱；PODAAC 镜像；NCEI THREDDS 匿名存档 | CMEMS 免费注册 / Earthdata / NCEI 匿名 | 0.05° 全球；**NRT(010_001) 只有滚动 2 年，1981 起长序列必须用 REP(010_011)**；2024-04 起 MOTU/OPeNDAP/FTP 全下线（旧 motu 教程全废）；analysis_error 2014-02 前高估；diurnal 版退役中；再分发需署名 → survey `raw/surveys/ostia_sst_sentinel_sar_wind_survey.md` |
| **Sentinel-1 SAR 海面风（OWI）** | L2 OCN OWI：10m 风速风向，**1km** 网格 | CDSE（下载需免费注册+token）；ASF（Earthdata+EULA） | 浏览匿名 / 下载需注册 | σ0→CMOD7（VV 高风 ~25m/s 饱和→交叉极化 VH 可到 50m/s），风向取 ECMWF 非反演；精度 ~1.5–2 m/s；比散射计 25km 细一量级、近岸主场；旧文档站 404 已迁 SentiWiki；自反演工具 openwind/grdwindinversion/SNAP（sarwind 库已死）→ 同上 survey |
| **PARDIG + SatWeave（Google DeepMind，2026-11-13 开源）** | PARDIG：AI 降水估计 15min/0.1°（NRT 2016→ 输入 HRES+SatWeave 11 通道；LR 1999–2023 输入 ERA5+GridSat-B1+LEO 微波）；SatWeave：5 颗静止星 17 谱段统一拼接 0.1°（2016–2025 30min / 2026→ 逐时 ~1h 延迟） | arXiv 2611.13941（论文）；GCS 匿名公开桶 pardig_1 / satweave_1（Zarr v3）；GEE 静态档；官方 Colab 入门指南 | **无（实测匿名拉样成功）** | 训练目标仅 GPM CORRA 星载雷达（地面站零参与→评估独立）；CSI 全面胜 IMERG-Final/MSWEP/ERA5：36,678 站 89.9% 胜 IMERG-Final（0.36 vs 0.28），1mm/h 0.48 vs 0.38，**25mm/h 极端 0.12 vs 现役 <0.03**，热带 +52%（反超仅中纬度高山站）；"1999 至 2026 历史档"是 LR+NRT 两版拼接（输入分辨率不同，跨边界注意断点）；**developers.google.com 超时 → developers.google.cn 镜像 200**；桶根 zarr.json 404 需子目录前缀；SatWeave GEO 覆盖 ±60–65°、部分波段非全星座；**实测坑：obstore 本机必须 skip_signature=True（默认走 GCE metadata 取 token）+ timeout 放宽；chunk key c/0/0/0（zarr v3 default encoding）；bytes+zstd 有压缩 → 读子域也要整 chunk 下载（SatWeave 波段 26MB→16.8MB 仅 1.5x，PARDIG 降水 19.7x 秒级可拉）；国内直连单流 ~0.03MB/s → 8 连接并发分片提速 5–8x 后两帧验证 86s；列桶 maxResults=1000 截断须 pageToken 或 startOffset；物理自洽通过（640nm 白天反射率 1.65–79.35%、降水 0–37.8mm/h）→ survey `raw/surveys/deepmind_pardig_satweave_survey.md`** |

## 3. 雷达

| 源 | 变量 | 获取方式 | 凭证 | 已知限制 |
|----|------|----------|------|----------|
| NEXRAD Level-2 | 体扫反射率 | AWS 桶 + unidata 分块 | 无 | 官方桶匿名访问受限，需走替代路径 → `[PIT-20260812-001]`、`[RCP-20260812-001]` |
| MRMS QPE | 定量降水估计，小时 | AWS 公开桶 | 无 | 需按 ERCOT 边界裁剪，见 `[RCP-20260927-001]` |

## 4. 电力市场与机组

| 源 | 变量 | 获取方式 | 凭证 | 已知限制 |
|----|------|----------|------|----------|
| ERCOT（GridStatus 通道） | 负荷 / 发电构成 / 电价 | Python 包 | 无 | 官网直连被反爬 + 中国 IP 不可达 → `[PIT-20260723-001]` |
| EIA API | 发电量 / 装机 | REST JSON | 需 key | 口径与 ERCOT 自家不同，交叉验证用 |
| ENTSO-E Transparency | 日前价 / 发电构成 / 负荷 | REST XML | 需 token | 报文两处隐藏结构 → `[PIT-20260929-002]`、`[RCP-20260929-005]` |
| Energy-Charts (Fraunhofer ISE) | 价格 / 发电构成，多国 | 公开 JSON | 无 | **免凭证首选**，可做 ENTSO-E 的校验口径 |
| ESIOS / REE | 西班牙官方口径 | REST | token（有效也进不去） | **域名级 WAF 全面 403** → `[PIT-20260929-001]`，改用 ENTSO-E 替代 |
| GEM 电站数据库 | 机组名录 / 位置 / 装机 | 公开 CSV | 无 | 月度版本，需按月份拼路径 → `[RCP-20260911-002]` |
| **AEMO NEMWEB（澳洲 NEM）** | 场站级 UIGF 官方预测（ELAV）/ 5min 全场站 SCADA 实测 / 区域电价（RRP、TOTALDEMAND） | Apache autoindex HTTP 目录（MMS 格式，zip 套 zip） | **无（匿名免注册）** | 全球最易程序化获取的市场数据之一，中国直连可达；**MMS 字符串字段带双引号必须剥除**（否则 to_datetime 全 NaN 静默清空）；实测表名 `UNIT_SCADA`（非 DISPATCH_UNIT_SCADA）、时间字段 `SETTLEMENTDATE`；UIGF 只取 `SCADA_TYPE=ELAV` 才是对账基准 → `[RCP-20261102-001]` |

## 5. 合成与派生数据

| 源 | 变量 | 获取方式 | 凭证 | 已知限制 |
|----|------|----------|------|----------|
| NSRDB | 高分辨率太阳辐照 | AWS 桶懒读取 | 无需注册 | 元数据为二进制包，需先建索引 → `[RCP-20260927-002]` |
| pvlib | 辐照 → 出力 | Python 包 | 无 | 需要装机侧假设（ILR/朝向），假设变了结论就变 |
| **IGCC 全球气候指标** | 11 项 IPCC AR6 指标（GHG→强迫→温度→归因→碳预算→极端/海平面），1750–2025 年度 | CDS retrieve（需账号）/ **Zenodo 匿名**（doi:10.5281/zenodo.21494229，与 CDS 同版本） | 无（Zenodo 通道） | 年度全球聚合，**无风速/风资源项**——只进气候叙事层；**缺风速资源趋势用 Open-Meteo Archive 补** → `[RCP-20261026-001]` |
| 站点代表点合成 | 省/区域级辐照代理 | 自建 | 无 | 覆盖率必须在报告里写明 → `[RCP-20260929-013]` |
| **TGW/reV 美国风光发电剖面（GODEEEP）** | CONUS 1/8°（≈12km）逐时风（80/100/125m）+光伏容量因子；历史 1980–2022 + 未来情景至 2099 | Zenodo index record 10214348 → **~70 个 hasPart 子记录**（变量×情景×20 年，单个 zip 30GB 级）或 tgw-data.msdlive.org 门户（TGW 原始 WRF 气象同站） | 无（匿名） | **母 DOI 只有 README，数据全在子记录**；按需挑选勿全下（TB 级），免全量读取管线 `[RCP-20261110-001]`（前 4MB raw → 前缀切片 18–63 步）；rcp45/85hotter 是 TGW 热力学外推非 CMIP6 原生情景；license 字段缺失；reV 模型估计非实测发电；Nature Energy 范本论文 s41560-026-02109-3 → survey `raw/surveys/nature_energy_resource_adequacy_tgw_rev_survey.md` |

## 使用纪律

- **宁可无数据，不可假数据**：受限源在结论里显式标注"数据缺失/骨架"，不留空猜
- 能用免凭证源就用（Open-Meteo、Energy-Charts、NASA POWER、GOES/Himawari 公开桶）
- 凭证一律走环境变量，禁止写进脚本 → `[MTD-20260907-001]`
