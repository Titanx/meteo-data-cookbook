# 团队约定

> 本目录存放气象团队共享的工作约定与规范，对所有项目自动生效。

## 数据文件命名约定

| 数据类型 | 命名模式 | 示例 |
|----------|---------|------|
| 探空廓线 | `sounding_{站号}_{YYYYMMDD}{HH}Z.csv` | `sounding_72249_2026071300Z.csv` |
| Meteostat 观测 | `{ICAO}_{YYYY}.csv` | `ZSSS_2025.csv` |
| ERCOT 电价 | `ercot_{市场}_{枢纽}_{起始YYYYMM}_{结束YYYYMM}.csv` | `ercot_DAM_HB_NORTH_202501_202607.csv` |
| SURFRAD 辐射 | `{站代码}{YY}.dat` | `bon25.dat` |
| NEXRAD 雷达分块 | `{SID}_{Volume}_{ChunkID}` | `KFWS_999_D00` |
| 分析报告 | `{主题}_analysis_report.html` | `sounding_analysis_report.html` |
| 深度分析 | `{主题}_deep_analysis.html` | `sounding_deep_analysis.html` |

## 脚本命名约定

| 类型 | 前缀 | 示例 |
|------|------|------|
| 数据下载 | `download_{数据源}_{细节}.py` | `download_ercot_spp.py` |
| 数据测试 | `test_{数据源}.py` | `test_meteostat.py` |
| 数据检查 | `check_{内容}_{维度}.py` | `check_data_integrity.py` |
| 分析脚本 | `{主题}_analysis.py` | `thunderstorm_ercot_analysis.py` |
| 管道流程 | `{数据源}_pipeline.py` | `goes19_pipeline.py` |

## 知识库条目约定

| 条目类型 | 前缀 | 编号规则 |
|----------|------|----------|
| 最佳实践/指南 | GL- | 自增 (GL-001 ~ GL-999) |
| 已知陷阱 | PF- | 自增 (PF-001 ~ PF-999) |
| 技术流程 | PS- | 自增 (PS-001 ~ PS-999) |
| 项目决策 | DEC- | 自增 (DEC-001 ~ DEC-999) |
| 模型/方法 | MD- | 自增 (MD-001 ~ MD-999) |

## Git 提交约定

- 提交信息格式：`[类型] 简短描述`
- 类型：`feat`（新功能）、`fix`（修复）、`data`（数据更新）、`docs`（文档）、`refactor`（重构）
- 示例：`feat: 探空数据并行下载脚本`，`data: 更新德州探空分析结果`

## 变量单位约定

| 变量 | 单位 | 说明 |
|------|------|------|
| 温度 | °C | 气温、露点、湿球温度 |
| 气压 | hPa (= mbar) | 站压、海平面气压 |
| 风速 | m/s | 风速标量 |
| 风向 | Degrees | 0=北, 90=东, 顺时针 |
| 降水 | mm/hour 或 mm/day | 小时或日累计 |
| 辐照度 | W/m² | GHI/DNI/DHI 等 |
| 电价 | $/MWh | ERCOT 结算点电价 |
| 功率 | MW | 发电/负荷 |
| DCAPE/CAPE | J/kg | 对流有效位能 |

## 数据目录结构约定

```
data/
├── {数据源}/
│   ├── {站点ID或区域}/
│   │   ├── {数据文件}
│   │   └── ...
│   ├── _download_summary.json    # 下载摘要
│   └── _station_info.json        # 站点元数据
```

## API Key 安全约定

- API Key 存入环境变量，不硬编码在脚本中
- 环境变量命名：`$env:{数据源大写}_API_KEY`
- 示例：`$env:GRIDSTATUS_API_KEY`, `$env:EIA_API_KEY`
- 不提交 `.env` 文件到版本控制