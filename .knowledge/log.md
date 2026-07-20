# 知识变更日志

> 本文件只追加，不修改历史记录。

## [2026-07-20] cleanup | [清理 draft 条目] | 删除全部 13 个 draft 条目，仅保留 5 个 verified 条目；清理所有残留引用 | #d1e7f3a5

- 用户决定：draft 状态条目（框架占位、未实测验证）不发布到 GitHub，全部删除
- 删除 13 个 draft 文件：DEC-001/002、GL-001/002/003、PF-001/002/003、MD-001/002/003、PS-001/002
- 保留 5 个 verified 条目：GL-004、GL-005、PF-004、PS-003、PS-004
- 重写 tech/catalog.md：移除 decisions/ 和 models/ 空章节，仅保留 guidelines/、pitfalls/、processes/
- 清理 5 个 verified 文件中对已删除条目的引用（GL-004、GL-005、PF-004、PS-003、PS-004 的"相关知识"及正文内联引用）
- 更新 GL-005：新增第 13 节"数据实时性实测"，修正"1-7天延迟"为"小时数据延迟约12分钟"
- 知识库条目数：18 → 5（全部 verified）

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
