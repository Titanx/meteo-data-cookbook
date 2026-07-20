# 知识变更日志

> 本文件只追加，不修改历史记录。

## [2026-07-21] update | [GL-006 NASA POWER 参数完整清单] | 通过官方 API 端点查询全部 1660 个参数，补充到 GL-006 | #a7c3e9f1

- 发现 POWER 官方参数查询端点：`/api/system/manager/parameters?community=RE&temporal=HOURLY&metadata=true`
- 端点来源：nasapower R 包源码（`query_parameters` 函数）
- 参数总数：HOURLY 105、DAILY 152、MONTHLY 1388、CLIMATOLOGY 1634，不重复 1660 个
- 三社区 AG/RE/SB 参数数完全一致
- HOURLY 105 个核心参数按 14 个类别归类（温度 6、湿度 5、气压 3、风 13、降水蒸发 9、全天空辐射 13、晴空辐射 10、其他辐射 12、云 5、气溶胶 3、太阳几何 1、冰雪 2、土壤水文 14、对流层边界层 4）
- DAILY 额外 48 个参数含 max/min/range 统计、度日（HDD/CDD）、生长度日（GDD）、IMERG 降水
- MONTHLY/CLIMATOLOGY 参数爆炸原因：SI_TILTED/SI_TRACKER 倾斜面×追踪器组合、SG_SZA/SAA 逐小时、连续无太阳天数
- 纠正之前"猜测参数名批量测试"的错误方法（只找到 18 个，大量 422 错误）
- GL-006 新增第 8 节"参数完整清单"，原 8-10 节顺延为 9-11 节
- 来源更新：增加参数查询端点、nasapower R 包链接、查询脚本路径
- 新增脚本：scripts/data_download/list_power_params.py
- 完整参数清单归档：.knowledge/tech/nasa_power_params.md

## [2026-07-20] cleanup | [清理 draft 条目] | 删除全部 13 个 draft 条目，仅保留 5 个 verified 条目；清理所有残留引用 | #d1e7f3a5

- 用户决定：draft 状态条目（框架占位、未实测验证）不发布到 GitHub，全部删除
- 删除 13 个 draft 文件：DEC-001/002、GL-001/002/003、PF-001/002/003、MD-001/002/003、PS-001/002
- 保留 5 个 verified 条目：GL-004、GL-005、PF-004、PS-003、PS-004
- 重写 tech/catalog.md：移除 decisions/ 和 models/ 空章节，仅保留 guidelines/、pitfalls/、processes/
- 清理 5 个 verified 文件中对已删除条目的引用（GL-004、GL-005、PF-004、PS-003、PS-004 的"相关知识"及正文内联引用）
- 更新 GL-005：新增第 13 节"数据实时性实测"，修正"1-7天延迟"为"小时数据延迟约12分钟"
- 知识库条目数：18 → 5（全部 verified）

## [2026-07-20] add | [PS-005 SURFRAD 地表辐射实测] | 新增 SURFRAD 下载流程条目，7 站点实测验证 | #e2f4a8b1

- 新增 PS-005：SURFRAD 地表辐射实测数据下载流程（verified）
- 2026-07-20 实测：7 站点 × 7 天 = 63 文件，63,715 条 1 分钟记录
- 数据量评估：2025-2026 全部 7 站 = 3562 文件，1.14 GB
- 实时性：realtime 目录当天实时追加，历史目录延迟 4 天
- 历史起始：最早 1995 年（bon/fpk/gwn），全历史约 15-20 GB
- 数据格式：48 列文本，含 GHI/DNI/DHI/长波/UV-B/PAR/气象，缺失值 -9999.9
- 关键发现：列顺序是 year jday month day（jday 在第 2 列），不是 year month day jday
- 更新 catalog.md、README.md（条目清单、数据源覆盖、特色内容、知识库结构）
- 复制脚本到 scripts/data_download/（surfrad_pipeline.py, surfrad_assessment.py）
- 知识库条目数：5 → 6（全部 verified）

## [2026-07-20] add | [GL-006 NASA POWER 卫星同化数据] | 新增 NASA POWER 使用指南，与 SURFRAD 实测对比验证 | #f3a5c9d2

- 新增 GL-006：NASA POWER 卫星同化数据使用指南（verified）
- 数据源：CERES 卫星反演（辐射）+ MERRA-2 再分析（气象）+ GPM IMERG（降水）
- API 实测：免 key 免注册，hourly 240 条 + daily 10 条，HTTP 200
- 关键发现：辐射延迟 3-4 个月（2026-07 数据缺失），气象延迟约 2 天
- 单位陷阱：hourly GHI 是 Wh/m²（= W/m²），daily 是 kW·h/m²/day
- 与 SURFRAD 实测对比（Bondville 2025-07-01~10，240 小时）：
  - GHI: MAE=38.6 W/m², RMSE=68.0 W/m², BIAS=-23.3 W/m²（轻度低估）
  - 温度: MAE=1.4°C（精度优秀）
- 与 Open-Meteo（ERA5）对比：POWER 空间分辨率粗（0.5°-1° vs 0.25°），但辐射来自卫星观测可交叉验证
- 更新 catalog.md、README.md（条目清单 7 条、知识库结构图）
- 新增脚本：test_nasa_power.py（含 SURFRAD 对比）
- 知识库条目数：6 → 7（全部 verified）

## [2026-07-18] update | [葵花数据下载方式修正] | 修正 PS-003，发现 AWS S3 匿名访问方式，无需注册 | #c4f9b3e8

- 用户反馈：葵花数据可直接通过 AWS S3 下载，无需注册
- 实测验证 AWS S3 匿名访问（noaa-himawari8 bucket）：✅ 成功
- 实测下载文件：HS_H08_20251126_0000_B01_FLDK_R10_S0110.DAT.bz2 (2.74 MB)
- 发现 8 类产品：L1b(FLDK/Japan/Target) + L2(云/降水/SST/风/图像)
- 重写 PS-003：以 AWS S3 为推荐方式，JAXA FTP 降级为备选
- 更新 PS-003 标签：增加 aws-s3, anonymous, noaa
- 新增测试脚本：scripts/data_download/test_himawari_s3.py
- 教训：应优先调研公开数据源（AWS Open Datasets）再推荐需要注册的方案

## [2026-07-18] ingest | [气象数据接口实测验证] | 实测 Open-Meteo、Meteostat、葵花8/9 三个数据接口，沉淀 3 条验证知识 | #b7e2a8f1

- 实测 Open-Meteo API：实时预报(168h) + 历史 ERA5(17天) 均成功
- 实测 Meteostat 库：日数据(30条) + 小时数据(168条) + 站点查询 均成功
- 实测葵花8/9 FTP：服务器可达(TCP 连接成功)，完整下载需注册账号
- 新增 tech/guidelines/GL-004 Open-Meteo API 使用指南 (verified)
- 新增 tech/guidelines/GL-005 Meteostat 地面观测数据使用指南 (verified)
- 新增 tech/processes/PS-003 葵花8/9 卫星数据下载流程 (verified)
- 测试脚本归档: scripts/data_download/test_openmeteo.py, test_meteostat.py, test_himawari.py
- 测试数据归档: data/openmeteo/, data/meteostat/
- 更新 catalog.md 统计：13 → 16 条知识
- 更新 tech/catalog.md 新增 3 条条目索引

## [2026-07-18] ingest | [气象知识库初始化] | 初始化气象领域知识库，创建 13 条种子知识 | #a3f1c2d4

- 创建 .knowledge/ 目录结构（conventions/、tech/、project/）
- 新增 tech/decisions/DEC-001 气象数据存储格式选型
- 新增 tech/decisions/DEC-002 数值天气预报模式选择
- 新增 tech/guidelines/GL-001 气象数据可视化配色规范
- 新增 tech/guidelines/GL-002 气象代码编写与版本控制规范
- 新增 tech/guidelines/GL-003 气象数据下载与缓存策略
- 新增 tech/pitfalls/PF-001 GRIB2 数据解码常见错误
- 新增 tech/pitfalls/PF-002 数值模式积分不稳定问题
- 新增 tech/pitfalls/PF-003 气象数据时区与时间格式陷阱
- 新增 tech/models/MD-001 气象要素数据模型
- 新增 tech/models/MD-002 GRIB2 文件结构模型
- 新增 tech/models/MD-003 NetCDF 气象数据模型
- 新增 tech/processes/PS-001 数值天气预报业务流程
- 新增 tech/processes/PS-002 气象数据质量控制流程
- 初始化 catalog.md 全景目录
- 初始化 tech/catalog.md 与 project/catalog.md 分类清单
