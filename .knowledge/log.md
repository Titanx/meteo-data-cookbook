# 知识变更日志

> 本文件只追加，不修改历史记录。

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