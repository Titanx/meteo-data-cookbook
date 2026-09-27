# 气象知识全景目录

> 最后更新: 2026-09-27
> 总计: 35 条知识（34 verified + 1 draft）

## 统计概览

| 分类 | 数量 | verified |
|------|------|----------|
| 最佳实践 (tech/guidelines/) | 6 | 6 |
| 已知陷阱 (tech/pitfalls/) | 9 | 9 |
| 技术流程 (tech/processes/) | 19 | 18 (PS-020 draft) |
| 参数清单 (tech/) | 1 | 1 |
| **合计** | **35** | **34** |

## 快速导航

- [技术知识目录](tech/catalog.md)
- [项目特有知识目录](project/catalog.md)
- [团队约定](conventions/README.md)

## 领域说明

本知识库聚焦气象数据下载与处理，覆盖以下知识范围：

- **地面观测**：Meteostat、NOAA ISD 等地面气象站数据获取与处理
- **卫星数据**：葵花 8/9（Himawari）、GOES-16/18/19 静止气象卫星数据下载与真彩色合成
- **雷达数据**：NEXRAD WSR-88D 天气雷达实时分块数据获取、RainViewer 全球拼图、GCP 公开数据集
- **数值预报 (NWP)**：HRRR 3km CONUS、GFS/NAM/NBM 等模式预报数据，Open-Meteo API 匿名获取
- **S2S 季节尺度预报**：ECMWF EC46/SEAS5 45 天~7 个月集合预报，Open-Meteo seasonal API，ERA5 逐时效核验；WMO S2S 数据库（ECDS）多中心回算
- **再分析数据**：Open-Meteo API（ERA5 后端）、NASA POWER（MERRA-2 + CERES）使用
- **探空数据**：怀俄明大学 WSGI 接口探空廓线数据下载与热力指数提取
- **降水数据**：GPM IMERG 全球卫星降水产品（30 分钟/日/月，1998 年至今），NASA Earthdata 认证下载
- **高分辨率降水**：MRMS 多雷达多传感器 QPE（1 km/小时，AWS S3 归档 2020-2023 + NCEP 官网实时），ERCOT 裁剪
- **太阳辐照度**：NSRDB v3.2.2 GOES 版（5 min/2 km GHI/DNI/DHI），TB 级 HDF5 S3 懒读取（h5coro/h5py+fsspec），ERCOT 像素定位；分块批量提取 + pvlib PVWatts 出力建模 + EIA-930 验证（小时 r=0.998）
- **电力市场**：ERCOT 电力市场数据获取（EIA API + GridStatus.io API）
- **地表辐射**：SURFRAD 实测辐射数据下载与处理
- **AWS Open Data**：NOAA 卫星/雷达数据通过 AWS S3 匿名访问
- **地形数据**：ASTER GDEM v3 30m 数字高程模型 + ASTWBD 水体分类数据
- **联动分析**：雷暴事件 × 电力市场联动分析；光伏缺口 × 电价冲击推演（晴空反事实 + RTM 弹性标定，HRRR 温度修复 + USCRN 地面验证）；RTM 尾部尖峰弹性标定与极端场景外推（15min 口径 + 分位数回归 + 凸性检验 + 尾部概率）
- **电站数据库**：GEM/WRI 全球电站数据库（坐标、装机、业主），绕过注册的 CDN 直链
- **数据处理**：satpy/pyresample 卫星数据处理、pandas 数据分析、线程池并行下载
- **凭证安全**：netrc/.env 管理 API 凭证，禁止硬编码，.gitignore 防护

## 数据源图谱

```
┌─────────────────────────────────────────────────────────────┐
│                     气象数据源全景                            │
├─────────────┬─────────────┬──────────────┬──────────┬───────┤
│  地面观测    │  卫星遥感   │  再分析/同化  │  电力市场 │ 雷达   │
├─────────────┼─────────────┼──────────────┼──────────┼───────┤
│ Meteostat   │ Himawari-9  │ Open-Meteo   │ EIA API  │NEXRAD │
│ (GL-005)    │ (PS-003)    │ (GL-004)     │ (PS-006) │ chunks│
│             │ GOES-19     │ NASA POWER   │GridStatus│(PS-009)│
│ SURFRAD     │ (PS-004)    │ (GL-006)     │ (PS-006) │RainView│
│ (PS-005)    │ GOES GLM    │              │          │(GL-008)│
│ 怀俄明探空  │ (PS-011)    │  MRMS QPE    │雷暴联动  │ GCP   │
│ (PS-008)    │ FY-4 LMI    │  (PS-018)    │ (PS-007) │(GL-008)│
│             │ (PS-012)    │              │          │       │
│  NSRDB辐照  │ IMERG降水   │  ASTER地形   │          │       │
│  (PS-019)   │ (PS-010)    │  (PS-013)    │          │       │
└─────────────┴─────────────┴──────────────┴──────────┴───────┘
```

## 知识图谱（条目间引用关系）

```
GL-004 Open-Meteo  ──→  GL-005 Meteostat
                           │
GL-005 Meteostat  ────→  PF-004 区域陷阱
                           │
GL-006 NASA POWER  ────→  PS-005 SURFRAD（实测验证基准）
                           │
GL-007 探空热力指数  ───→  PF-008 SSL证书
                           ├──→ PF-009 分辨率差异
                           └──→ PF-010 CAPE缺失
                           │
GL-008 雷达数据匿名获取 ──→  PS-009 unidata chunks
                           ├──→ PF-011 官方桶限制
                           │
PS-003 葵花9  ──────────→  PS-004 GOES-19（东西半球对应）
                           │
PS-006 ERCOT  ──────────→  PF-005 反爬虫屏蔽
                           ├──→ PF-006 时区问题
                           ├──→ PS-007 雷暴联动
                           │
PS-007 雷暴联动  ───────→  PF-007 高风区阈值
                           ├──→ PF-006 时区问题
                           │
PS-008 探空下载  ───────→  PF-008 SSL证书
                           ├──→ PF-009 分辨率差异
                           └──→ PF-010 CAPE缺失
                           │
PS-009 unidata chunks  ──→  PF-011 官方桶限制
                           ├──→ GL-008 雷达综合指南
                           │
PF-008 SSL证书  ─────────→  PF-009 分辨率差异
                           │
PF-006 时区问题  ────────→  跨多数据源通用陷阱
                           │
PF-011 官方桶限制  ──────→  GL-008 替代方案
                           ├──→ PS-009 unidata chunks
                           │
PS-010 IMERG 降水  ───────→  GL-009 凭证安全 (netrc)
                           │
PS-011 GOES GLM 闪电  ────→  PS-012 FY-4 LMI (中国对应)
                           │
PS-012 FY-4 LMI  ─────────→  PF-012 CMA 数据访问陷阱
                           │
PS-013 ASTER 地形  ───────→  GL-009 凭证安全 (netrc)
                           ├──→ PS-010 IMERG (同 Earthdata)
                           └──→ PS-011 GLM (地形×闪电)
                           │
GL-009 凭证安全  ─────────→  PS-006 ERCOT (.env)
                           ├──→ PS-010 IMERG (netrc)
                           ├──→ PS-013 ASTER (netrc)
                           │
PF-012 CMA 陷阱  ─────────→  PS-012 FY-4 LMI (替代方案)
                           ├──→ GL-004 Open-Meteo (NWP 替代)
                           └──→ PS-008 探空 (怀俄明替代)
                           │
PS-016 GEM电站×电价  ────→  PS-006 ERCOT (电价/发电数据)
                           ├──→ PS-007 雷暴联动 (交叉方法)
                           ├──→ PF-005 反爬虫 (GEM CDN 绕过注册)
                           └──→ PF-006 时区问题 (多源对齐)
                           │
PS-017 S2S季节预报  ────→  GL-004 Open-Meteo (端点/模型)
                           ├──→ PS-006 ERCOT (出力/电价链路)
                           ├──→ PS-010 IMERG (降水实测交叉)
                           ├──→ PS-018 MRMS (高分辨率降水核验基准)
                           └──→ ERA5 再分析 (实测基准, GL-004/archive-api)
                           │
PS-018 MRMS QPE  ────────→  GL-008 雷达匿名获取 (同雷达体系)
                           ├──→ PS-010 IMERG (1km vs 10km 互补)
                           └──→ PS-007 雷暴联动 (极端降水核验)
                           │
PS-019 NSRDB 懒读取  ────→  PS-005 SURFRAD (实测验证基准)
                           ├──→ GL-006 NASA POWER (同化对照)
                           ├──→ PS-016 GEM (光伏电站坐标映射)
                           └──→ PS-006 ERCOT (pvlib 出力链路)
                           │
PS-020 WMO S2S 库  ──────→  PS-017 (多窗口重采样的数据基础)
                           └──→ GL-009 凭证安全 (ECDS API key)
                           │
PS-021 NSRDB×pvlib 出力  →  PS-019 (懒读取/像素定位前置)
                           ├──→ PS-016 GEM (电站坐标映射)
                           ├──→ PS-006 ERCOT (EIA-930 验证基准)
                           └──→ PS-022 光伏缺口×电价 (下游推演)
                           │
PS-022 光伏缺口×电价  ──→  PS-021 (出力底模 + 温度修复前置)
                           ├──→ PS-019 NSRDB (辐照提取)
                           ├──→ PS-016 GEM (电站坐标)
                           ├──→ PS-006 ERCOT (EIA-930/RTM 电价)
                           ├──→ PS-017 S2S (季节预报辐照推广方向)
                           ├──→ PS-007 雷暴联动 (事件口径交叉)
                           └──→ PS-023 RTM 尾部尖峰弹性 (口径复核 + 分位外推)
                           │
PS-023 RTM 尾部弹性  ──→  PS-022 (晴空反事实 + 弹性基线复核)
                           ├──→ PS-006 ERCOT (GridStatus 15min RTM)
                           ├──→ PS-019 NSRDB (反事实辐照来源)
                           └──→ PS-021 pvlib (出力底模)
```

## 变更历史

详见 [log.md](log.md)。