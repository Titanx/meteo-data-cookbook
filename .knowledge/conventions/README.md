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
| Energy-Charts 年度整块 | `{国家代码}_public_power_{YYYY}.json` | `es_public_power_2025.json`、`fr_public_power_2026.json` |
| ENTSO-E 月缓存 | `{内容}_{YYYY-MM}.csv` / `.xml` | `price_da_2026-01.csv`、`load_2025-11.xml` |
| NWP 历史预报归档（previous-runs） | `{国家代码}_nwp_prevruns_{起始日期}_{结束日期}.npz` | `fr_nwp_prevruns_2025-06-26_2025-12-22.npz` |
| ERA5 实测归档 | `{国家代码}_ghi_archive.npz` | `es_ghi_archive.npz` |
| 汇成日面板 | `{国家或域}_{主题}_panel.csv` | `spain_nwp_panel.csv`、`france_noon_panel.csv` |
| 模型中间产物 | `{流程前缀}_{设定或指标}.csv` | `spain_nwp_warning.csv`、`france_nwp_leadcheck.csv` |
| 分析报告 | `output/{report-name}/index.html` | `output/spain_negprice_d1warning/index.html` |
| 深度分析 | `{主题}_deep_analysis.html` | `sounding_deep_analysis.html` |

约定：**原始响应按源原样落盘**（JSON / XML / npz / nc），口径修正（变长块展开、合约过滤、重采样、时区归一）一律发生在派生层；派生 CSV 只作消费层，可随时重算。

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
| 最佳实践/指南 | GL- | 自增 (GL-004 ~ GL-999，GL-001~003 预留) |
| 已知陷阱 | PF- | 自增 (PF-004 ~ PF-999，PF-001~003 预留) |
| 技术流程 | PS- | 自增 (PS-003 ~ PS-999，PS-001~002 预留) |
| 项目决策 | DEC- | 预留，尚未启用 |
| 模型/方法 | MD- | 预留，尚未启用 |

成熟度三档：`draft`（单人经验，仅供参考）→ `verified`（至少一个项目验证，可作决策参考）→ `proven`（至少两个项目验证，可作团队标准）。当前知识库的模型类内容以 PS（流程）承载，尚未单独拆出 MD 条目。

报告产物约定：每个报告一个目录 `output/{report-name}/`，入口固定为 `index.html`，目录内自带字体与图表库，**零外部依赖**，可独立打开或拷贝分发。`output/` 不纳入版本控制。

## Git 提交约定

- 提交信息格式：`[类型] 简短描述`
- 类型：`feat`（新功能）、`fix`（修复）、`data`（数据更新）、`docs`（文档）、`refactor`（重构）
- 示例：`feat: 探空数据并行下载脚本`，`data: 更新德州探空分析结果`
- 当前实践：流程类提交以**流程号开头**并把关键结论写进正文，便于日后按 ID 检索，例如
  `PS-044 补齐ES侧NWP: 西班牙侧自身可预报(...), 但对负价日增量小且不稳定(...)`；
  知识库文档变更仍用 `docs:` 前缀。
- 不提交 `data/`、`output/`、`.env`、`__pycache__/`（见 `.gitignore`）。

## 变量单位约定

| 变量 | 单位 | 说明 |
|------|------|------|
| 温度 | °C | 气温、露点、湿球温度 |
| 气压 | hPa (= mbar) | 站压、海平面气压 |
| 风速 | m/s | 风速标量 |
| 风向 | Degrees | 0=北, 90=东, 顺时针 |
| 降水 | mm/hour 或 mm/day | 小时或日累计 |
| 辐照度 | W/m² | GHI/DNI/DHI 等 |
| 电价（ERCOT） | $/MWh | ERCOT 结算点电价 |
| 电价（欧洲） | €/MWh | 西班牙/法国/葡萄牙日前价（OMIE 一手口径） |
| 功率 | MW | 发电/负荷 |
| 能量 | GWh / TWh | 日发电量、月/年能量 |
| 份额 | 比值 ∈ [0, 1] | 光伏/需求；写"55%"与 0.55 等价，文中需一致 |
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