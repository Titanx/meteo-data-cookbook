# 气象 × 电力市场 知识全景目录

> 最后更新: 2026-09-30
> 总计: 61 条知识（60 verified + 1 draft）

## 统计概览

| 分类 | 数量 | verified |
|------|------|----------|
| 最佳实践 (tech/guidelines/) | 6 | 6 |
| 已知陷阱 (tech/pitfalls/) | 12 | 12 |
| 技术流程 (tech/processes/) | 42 | 41（PS-020 draft） |
| 参数清单 (tech/) | 1 | 1 |
| **合计** | **61** | **60** |

## 快速导航

- [技术知识目录](tech/catalog.md)（跨项目通用：指南 / 陷阱 / 流程）
- [项目特有知识目录](project/catalog.md)（数据源索引 / 数据量 / 脚本索引 / 待办）
- [光伏缺口 × 电价链路结论总览](project/conclusions_solar_price.md)（结论、已修正结论、口径规范）
- [团队约定](conventions/README.md)

## 领域说明

本知识库聚焦两条链路：**气象数据获取与处理**，以及**电力市场（ERCOT / 西班牙 / 法国）的"缺口 → 电价"分析**。

- **地面观测**：Meteostat（全球 246 机场）、SURFRAD（美国 7 站地表辐射）、USCRN（德州 8 站 5 min 基准）
- **卫星数据**：葵花 8/9（Himawari）、GOES-16/18/19、GK2A AMI 静止卫星数据下载与真彩色合成
- **卫星闪电**：GOES GLM（美洲）、FY-4A LMI（中国区域，含公开订正集）
- **降水数据**：GPM IMERG（30 分钟/日/月，1998 年至今）、MRMS QPE（1 km/小时，S3 归档 + 官网实时）
- **雷达数据**：NEXRAD WSR-88D 实时分块（unidata）、GCP 公开数据集归档、RainViewer 全球拼图
- **太阳辐照度**：NSRDB v3.2.2（5 min/2 km GHI/DNI/DHI，TB 级 HDF5 懒读取）、PVGIS、NASA POWER
- **数值预报 (NWP)**：HRRR 3 km CONUS、GFS/NAM/NBM、ECMWF IFS，Open-Meteo 免注册获取
- **历史预报归档**：Open-Meteo `previous-runs`（真正带 lead 的 D1–D7 历史预报，用于回测；⚠️ 逐 lead 同质性陷阱 PF-015）
- **S2S 季节尺度预报**：ECMWF EC46/SEAS5（46 天~7 个月，51 成员），WMO S2S 数据库（ECDS）多中心回算
- **再分析数据**：Open-Meteo Archive（ERA5，1940 至今）、NASA POWER（MERRA-2 + CERES）
- **探空数据**：怀俄明大学 WSGI 接口探空廓线下载与热力指数（DCAPE）提取
- **地形数据**：ASTER GDEM v3（30 m DEM）+ ASTWBD 水体分类
- **电站数据库**：GEM / WRI 全球电站（坐标、装机、业主、投产年），按年回推容量清单
- **电力市场（美国）**：ERCOT 电价（GridStatus.io 4 枢纽 + 4 负荷区 + 120 资源节点）、负荷与分燃料发电（EIA API v2）
- **电力市场（欧洲）**：Energy-Charts（Fraunhofer ISE，免注册）、ENTSO-E Transparency（官方口径）、OMIE（一手校验基准）、ESIOS/REE（⚠️ 本机被域名级 WAF 封锁，PF-013）
- **联动分析**：雷暴 × 电价；光伏/风电缺口 × 电价弹性；缺口持续时间（小时/跨日）；缺口工况指纹（外生 vs 内生）；季节预报 → 缺口风险概率化；日尺度转移函数与 45 天展望
- **西班牙负价链**（PS-029 ~ PS-044）：光伏份额阈值 → 正午窗口 → 跨境区域过剩 → 可预报性检验 → NWP 短期预报 → D-1 预警
- **数据处理**：satpy/pyresample 卫星处理、pandas 多源对齐、线程池并行下载、HDF5 懒读取、分块缓存与断点续传
- **凭证安全**：netrc / `.env` / 环境变量管理 API 凭证，禁止硬编码，`.gitignore` 防护

## 数据源图谱

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            气象 × 电力市场 数据源全景                          │
├────────────┬────────────┬─────────────┬──────────────┬────────────┬──────────┤
│  地面观测   │  卫星遥感   │ 再分析/NWP   │  电力市场     │   雷达     │ 其他      │
├────────────┼────────────┼─────────────┼──────────────┼────────────┼──────────┤
│ Meteostat  │Himawari-9  │Open-Meteo    │GridStatus.io │NEXRAD      │GEM 电站  │
│ (GL-005)   │(PS-003)    │ ERA5(G-004)  │ (PS-006)     │ chunks     │(PS-016)  │
│ SURFRAD    │GOES-19     │NASA POWER    │EIA API v2    │ (PS-009)   │ASTER 地形│
│ (PS-005)   │(PS-004)    │ (GL-006)     │ (PS-006)     │RainViewer  │(PS-013)  │
│ USCRN      │GK2A        │HRRR/GFS/NAM  │Energy-Charts │ (GL-008)   │           │
│ (PS-022)   │(PS-015)    │ (GL-004)     │ (PS-030/40)  │GCP 公开集  │           │
│怀俄明探空   │GOES GLM    │previous-runs │ENTSO-E       │ (GL-008)   │           │
│ (PS-008)   │(PS-011)    │ (PS-043/44)  │ (PS-036)     │MRMS QPE    │           │
│            │FY-4 LMI    │seasonal      │OMIE / ESIOS  │ (PS-018)   │           │
│            │(PS-012)    │ (PS-017/027) │ (PS-029)     │            │           │
│            │IMERG 降水   │NSRDB 辐照    │              │            │           │
│            │(PS-010)    │ (PS-019)     │              │            │           │
└────────────┴────────────┴─────────────┴──────────────┴────────────┴──────────┘
```

## 知识图谱（条目间引用关系）

```
GL-004 Open-Meteo ──→ GL-005 Meteostat ──→ PF-004 区域陷阱
       │
       ├──→ PS-017 S2S 季节预报 ──→ PS-020 WMO S2S 库
       ├──→ PS-022/024/027 缺口链路 ──→ PS-034 日尺度转移函数
       └──→ PS-043/044 previous-runs 历史预报归档 ──→ PF-015 lead 同质性

GL-006 NASA POWER ──→ PS-005 SURFRAD（实测验证基准）

GL-007 探空热力指数 ──→ PF-008 SSL 证书 / PF-009 分辨率差异 / PF-010 CAPE 缺失
GL-008 雷达匿名获取 ──→ PS-009 unidata chunks ──→ PF-011 官方桶限制
GL-009 凭证安全 ──→ PS-006 ERCOT(.env) / PS-010 IMERG(netrc) / PS-013 ASTER(netrc)

PS-003 葵花9 ──→ PS-004 GOES-19（东西半球对应）
PS-006 ERCOT ──→ PF-005 反爬虫屏蔽 / PF-006 时区问题 / PS-007 雷暴联动
PS-007 雷暴联动 ──→ PF-007 高风区阈值
PS-008 探空下载 ──→ PF-008 / PF-009 / PF-010
PS-010 IMERG ──→ PS-011 GLM 闪电 ──→ PS-012 FY-4 LMI ──→ PF-012 CMA 陷阱
PS-013 ASTER 地形 ──→ PS-014 地形 × 闪电

PS-016 GEM × 电价 ──→ PS-019 NSRDB 懒读取 ──→ PS-021 NSRDB×pvlib 出力建模
PS-021 ──→ PS-022 光伏缺口×电价 ──→ PS-023 RTM 尾部弹性
        └──→ PS-024 缺口口径统一 ──→ PS-025/026 缺口持续时间
PS-027 季节预报 → 缺口概率化 ──→ PS-034 转移函数与 45 天展望
PS-028 风电缺口×电价 ──→ PS-032/033 成因判据与工况指纹

PS-029 西班牙数据源调研 ──→ PS-030 光伏最小链路 ──→ PS-031 多年市场区间
PS-031 ──→ PS-032 判据可逆性 ──→ PS-033 工况指纹
PS-035 西班牙负价季节预报 ──→ PS-037 官方口径复核 ──→ PS-038 负价模型 v3
PS-036 ENTSO-E 链路 ──→ PF-014 A03 压缩 + 合约混装
PS-039 爆发阈值（12 年）──→ PS-040 正午窗口份额
PS-040 ──→ PS-041 跨境结构 ES–FR ──→ PS-042 可预报化检验
PS-042 ──→ PS-043 真实 NWP 填法国侧 ──→ PS-044 补齐 ES 侧 NWP + D-1 预警
PF-013 REE WAF 封锁 ──→ PS-036（改走 ENTSO-E）
```

## 变更历史

详见 [log.md](log.md)。最近一轮为 2026-09-30 的知识库一致性 review（补齐根目录索引、脚本索引与 log 覆盖）。
