# 气象知识全景目录

> 最后更新: 2026-09-07
> 总计: 25 条知识（全部 verified）

## 统计概览

| 分类 | 数量 | verified |
|------|------|----------|
| 最佳实践 (tech/guidelines/) | 6 | 6 |
| 已知陷阱 (tech/pitfalls/) | 9 | 9 |
| 技术流程 (tech/processes/) | 9 | 9 |
| 参数清单 (tech/) | 1 | 1 |
| **合计** | **25** | **25** |

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
- **再分析数据**：Open-Meteo API（ERA5 后端）、NASA POWER（MERRA-2 + CERES）使用
- **探空数据**：怀俄明大学 WSGI 接口探空廓线数据下载与热力指数提取
- **降水数据**：GPM IMERG 全球卫星降水产品（30 分钟/日/月，1998 年至今），NASA Earthdata 认证下载
- **电力市场**：ERCOT 电力市场数据获取（EIA API + GridStatus.io API）
- **地表辐射**：SURFRAD 实测辐射数据下载与处理
- **AWS Open Data**：NOAA 卫星/雷达数据通过 AWS S3 匿名访问
- **地形数据**：ASTER GDEM v3 30m 数字高程模型 + ASTWBD 水体分类数据
- **联动分析**：雷暴事件 × 电力市场联动分析
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
│ 怀俄明探空  │ (PS-011)    │              │雷暴联动  │ GCP   │
│ (PS-008)    │ FY-4 LMI    │              │ (PS-007) │(GL-008)│
│             │ (PS-012)    │              │          │       │
│             │ IMERG降水   │  ASTER地形   │          │       │
│             │ (PS-010)    │  (PS-013)    │          │       │
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
```

## 变更历史

详见 [log.md](log.md)。