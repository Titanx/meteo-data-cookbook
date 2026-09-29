# 气象 × 电力市场数据实战指南

> 基于 2026-07-18 ~ 2026-09-30 的一手实测验证。覆盖 40 余个数据源：地面观测、卫星遥感、雷达、再分析与 NWP、S2S 季节预报、电站清单，以及 ERCOT / 西班牙 / 法国电力市场。
> 知识库现有 **61 条条目（60 verified + 1 draft）**、约 8,800 行 Markdown、147 个脚本、26 份可独立打开的分析报告。

现有开源项目要么是工具库（satpy / meteostat），要么是数据源索引（awesome-meteorology），本项目的定位是**第三层：实战经验沉淀**——怎么下、踩过什么坑、实测数据是多少、以及这些数据最终推演出了什么结论。

## 为什么需要这个项目

| 已有项目类型 | 代表 | 覆盖了什么 | 没覆盖什么 |
|------------|------|-----------|-----------|
| 工具库 | satpy / meteostat / MetPy | API 和代码 | 使用陷阱、实测数据 |
| 数据源索引 | awesome-meteorology / open-earth-data-guide | "在哪下" | "怎么下、踩过什么坑" |
| **本项目** | — | — | **下载流程 + 陷阱 + 实测验证 + 链路结论** |

## 知识库结构

```
meteo-data-cookbook/
├── README.md                       # 本文件
├── RELEASE_NOTES_v0.1.0.md         # 历史发布说明（v0.1.0）
├── LICENSE                         # MIT
├── .gitignore
├── .knowledge/                     # 知识库主体（67 个 md，约 8,800 行）
│   ├── catalog.md                  # 全景目录（统计 + 数据源图谱 + 知识图谱）
│   ├── log.md                      # 变更日志（只追加）
│   ├── conventions/
│   │   └── README.md               # 团队约定（命名 / 单位 / 凭证 / 目录）
│   ├── tech/                       # 跨项目通用知识
│   │   ├── catalog.md              # 技术条目索引（按主题 / 阶段 / 数据源）
│   │   ├── nasa_power_params.md    # NASA POWER 全部 1660 参数清单
│   │   ├── guidelines/             # 最佳实践   GL-004 ~ GL-009
│   │   ├── pitfalls/               # 已知陷阱   PF-004 ~ PF-015
│   │   └── processes/              # 技术流程   PS-003 ~ PS-044
│   └── project/                    # 本项目特有知识
│       ├── catalog.md              # 数据源索引 / 数据量汇总 / 脚本索引 / 待办
│       └── conclusions_solar_price.md  # 光伏缺口 × 电价链路的结论总览
├── scripts/
│   ├── data_download/              # 79 个取数脚本（只落原始格式）
│   └── analysis/                   # 68 个建模与报告脚本
├── output/                         # 26 份自包含 HTML 报告（不纳入 git）
└── news/                           # 论文与数据源调研笔记
```

> `data/` 与 `output/` 目录不纳入 git（可通过脚本重新生成）。

## 条目总览

### 最佳实践（guidelines，6 条全部 verified）

| ID | 标题 | 核心内容 |
|----|------|---------|
| GL-004 | Open-Meteo API 使用指南（含 HRRR/GFS 等 NWP） | 免 key；ERA5 归档 / 实时预报 / 历史预报 / 季节预报四类端点；HRRR 3 km 实测 80 m 风与 GHI 可用 |
| GL-005 | Meteostat 地面观测数据使用指南 | 246 机场 847 CSV 180.4 MB；站点 ID 复用 3–5x 提速；小时数据延迟仅 12 分钟 |
| GL-006 | NASA POWER 卫星同化数据使用指南 | CERES + MERRA-2 多源；辐射延迟 3–4 月；GHI MAE 38.6 W/m²（对 SURFRAD 实测） |
| GL-007 | 探空数据热力指数提取与 DCAPE 分析指南 | WSGI HTML 解析；DCAPE 稳健而 CAPE 常缺；标准气压层插值 |
| GL-008 | 气象雷达数据匿名获取综合指南 | NEXRAD unidata chunks / GCP 公开集 / RainViewer / NWS 四路对比 |
| GL-009 | 气象数据 API 凭证安全管理实践 | netrc / `.env` / 环境变量；禁止硬编码；`.gitignore` 防护 |

### 已知陷阱（pitfalls，12 条全部 verified）

| ID | 标题 | 一句话 |
|----|------|-------|
| PF-004 | Meteostat 区域数据下载陷阱 | 中国西部站点稀疏需 200 km 半径；多机场共用一站；港澳台部分站仅半年数据 |
| PF-005 | ERCOT 官网反爬虫与中国 IP 不可访问 | 官网完全屏蔽；改走 EIA（负荷/发电）+ GridStatus（电价） |
| PF-006 | Pandas 时区 tz-naive 与 tz-aware 比较错误 | 多源合并必先统一 UTC；`tz_localize` 与 `tz_convert` 不可混用 |
| PF-007 | 雷暴检测在高风区绝对阈值失效 | 达拉斯 31% 小时超 20 m/s，"绝对阈值 + 静风"逻辑检测到 0 个事件 |
| PF-008 | 怀俄明探空接口迁移与 SSL 证书问题 | 旧 CGI 404 迁 WSGI；出口代理替换证书需局部跳校验 |
| PF-009 | 探空数据区域分辨率差异 | 美国站 4,216–6,585 行 vs 中国站 140–155 行；廓线须先插值到标准层 |
| PF-010 | 探空 WSGI 格式 CAPE 缺失与 HTML 提取 | 用 DCAPE；去标签后正则取值 |
| PF-011 | NEXRAD 官方 S3 桶匿名访问限制 | `noaa-nexrad-level2` Access Denied；改 unidata / GCP |
| PF-012 | CMA 气象数据访问陷阱 | CMADaaS 需内网；网站账号与 API 账号分裂；`nmc-met-io` 不支持 LMI |
| PF-013 | REE/ESIOS 域名级 WAF 封锁 | `*.ree.es` 全族 403 且拦截发生在鉴权之前；TLS 指纹伪装无效 |
| PF-014 | ENTSO-E / IEC 62325 报文的两处隐藏结构 | `curveType=A03` 变长块压缩（一个月少解析 171 小时）+ A01/A07 合约混装 |
| PF-015 | 历史预报归档的逐 lead 同质性陷阱 | D7 在归档早段偏差 +142.6 W/m²；用前必做逐 lead × 分段筛查 |

### 技术流程（processes，42 条，PS-020 为 draft）

| ID | 标题 | 阶段 |
|----|------|------|
| PS-003 | 葵花 8/9 卫星数据下载流程 | 数据获取 |
| PS-004 | GOES-16/18/19 卫星数据下载流程 | 数据获取 |
| PS-005 | SURFRAD 地表辐射实测数据下载流程 | 数据获取 |
| PS-006 | ERCOT 电力市场数据下载流程（含 Resource Node） | 数据获取 |
| PS-007 | 雷暴事件 × 电力市场联动分析流程 | 联动分析 |
| PS-008 | 探空廓线数据下载流程（怀俄明大学 WSGI） | 数据获取 |
| PS-009 | NEXRAD 雷达实时分块数据下载流程 | 数据获取 |
| PS-010 | GPM IMERG 降水数据下载流程 | 数据获取 |
| PS-011 | GOES GLM 闪电数据下载流程 | 数据获取 |
| PS-012 | FY-4A LMI 闪电数据下载流程 | 数据获取 |
| PS-013 | ASTER GDEM 地形与水体数据下载流程 | 数据获取 |
| PS-014 | ASTER 地形与 GLM 闪电分布联动分析流程 | 联动分析 |
| PS-015 | GK2A AMI 卫星数据下载流程 | 数据获取 |
| PS-016 | GEM 电站数据库下载与 ERCOT 电价联动分析流程 | 联动分析 |
| PS-017 | S2S 季节尺度预报获取与精度核验流程 | 预报核验 |
| PS-018 | MRMS 雷达定量降水下载与 ERCOT 裁剪流程 | 数据获取 |
| PS-019 | NSRDB 太阳辐照度 S3 懒读取与 ERCOT 像素定位流程 | 数据获取 |
| PS-020 | WMO S2S 数据库获取路径（ECDS 多中心回算）· draft | 预报获取 |
| PS-021 | NSRDB 辐照批量提取与 pvlib 光伏出力建模验证流程 | 出力建模 |
| PS-022 | 光伏缺口 × 电价冲击推演流程 | 缺口 → 电价 |
| PS-023 | RTM 尾部尖峰弹性标定与极端场景外推 | 缺口 → 电价 |
| PS-024 | 光伏缺口口径统一：物理晴空 vs P95 包络 | 缺口 → 电价 |
| PS-025 | 光伏缺口的持续时间维度建模 | 缺口 → 电价 |
| PS-026 | 光伏缺口的日际/跨日持续时间建模 | 缺口 → 电价 |
| PS-027 | 季节预报 → 光伏缺口风险概率化 | 概率化 |
| PS-028 | 风电缺口 × 电价：风功率物理链路与"风光不对称" | 缺口 → 电价 |
| PS-029 | 西班牙电力市场数据源调研 | 西班牙链路 |
| PS-030 | 西班牙光伏最小链路（免注册复刻 pvlib 出力建模） | 西班牙链路 |
| PS-031 | 西班牙光伏链路多年份市场区间对比 | 西班牙链路 |
| PS-032 | 缺口成因判据 · 可逆性检验（ERCOT × 西班牙） | 判据检验 |
| PS-033 | 缺口"工况指纹"：外生 vs 内生 | 判据检验 |
| PS-034 | 缺口 → 电价：日尺度转移函数与 45 天展望 | 概率化 |
| PS-035 | 西班牙负价概率：季节预报链路（未来 45 天） | 负价预报 |
| PS-036 | 西班牙 ENTSO-E Transparency 数据链路 | 数据获取 |
| PS-037 | 西班牙链路 · 官方口径复核 + 2026 样本外检验 | 负价预报 |
| PS-038 | 西班牙负价模型 v3 · 趋势 / logit / 强度 | 负价预报 |
| PS-039 | 西班牙负价"爆发阈值"模型（12 年历史） | 负价预报 |
| PS-040 | 西班牙负价 · 正午窗口份额 vs 月度份额 | 负价预报 |
| PS-041 | 西班牙负价的跨境结构 · ES–FR 耦合与"区域过剩" | 负价预报 |
| PS-042 | 法国正午负价的可预报化 | 可预报性 |
| PS-043 | 用真实 NWP 预报填法国侧（D-1~D-7） | 可预报性 |
| PS-044 | 补齐 ES 侧 NWP · D-1/D-3 西班牙负价日预警 | 可运营预警 |

## 数据源覆盖

| 分组 | 数据源 | 访问方式 | 实测要点 |
|------|--------|---------|---------|
| 地面观测 | Meteostat / SURFRAD / USCRN | 免注册 | 246 机场 180.4 MB；小时延迟 12 分钟；美洲质量优于亚洲 |
| 静止卫星 | Himawari-8/9、GOES-16/18/19、GK2A | AWS S3 匿名 | FLDK 分段下载省 80%；真彩色手动 RGB + gamma |
| 卫星闪电 | GOES GLM、FY-4A LMI | 匿名 S3 / NSMC | 中国区域用公开订正集 2019–2023 |
| 卫星降水 | GPM IMERG、MRMS QPE | Earthdata / 匿名 S3 | IMERG 延迟 4 h~3.5 月；MRMS 1 km/小时可裁剪 ERCOT |
| 雷达 | NEXRAD（unidata / GCP）、RainViewer | 匿名 S3 / gsutil | 官方桶已关匿名；unidata 仅保留近期体扫 |
| 辐照 | NSRDB v3.2.2、PVGIS、NASA POWER | 匿名 S3 / 免注册 | NSRDB 5 min/2 km；与 EIA-930 小时 r=0.9976 |
| 再分析 | Open-Meteo Archive（ERA5） | 免注册 | 1940 至今，约 5 天延迟 |
| NWP | HRRR 3 km、GFS/NAM/NBM、ECMWF IFS | 免注册 | HRRR 提供 80 m 风与 GHI，无 100/120 m 层 |
| 历史预报归档 | Open-Meteo `previous-runs` | 免注册 | D1–D7 真 lead；归档起点 2024-07-01；须筛查同质性 |
| 季节预报 | Open-Meteo seasonal（EC46 + SEAS5） | 免注册 | 51 成员，46 天~7 个月 |
| 地形 | ASTER GDEM / ASTWBD | Earthdata netrc | ERCOT 154 tiles，合计 8.5 GB |
| 电站清单 | GEM global solar / wind（+ WRI） | CSV 快照 | 可绕过注册直取；2026 年装机不完整 |
| 美国电力市场 | GridStatus.io、EIA API v2 | API key | 4 枢纽 + 4 负荷区 + 120 节点；ERCOT 官网对中国 IP 全封 |
| 欧洲电力市场 | Energy-Charts、ENTSO-E、OMIE、ESIOS | 免注册 / token | EC 与官方 A44 逐位等价（r=0.999984）；ESIOS 本机不可达 |

完整的数据量、文件数与逐源状态见 [.knowledge/project/catalog.md](.knowledge/project/catalog.md)。

## 分析链路与报告产物

项目有两条主链路，结论与口径规范统一收在 [conclusions_solar_price.md](.knowledge/project/conclusions_solar_price.md)。

**ERCOT 缺口 → 电价**：NSRDB + pvlib 出力建模 → 物理晴空反事实缺口 → RTM 弹性标定 → 尾部尖峰与极端情景 → 季节预报概率化。结论：ERCOT 日尺度"预报桥"不成立（R² 0.016）。

**西班牙负价链（PS-029 ~ PS-044，八轮收敛）**：光伏份额阈值（θ=16%，季节依赖）→ 正午窗口（72% 负价小时落在当地 10–16h）→ 跨境区域过剩（FR 同窗口负价小时 corr +0.620）→ 可预报性检验（同期共振而非预报技能）→ NWP 短期预报（法国侧可预报但通道不增益）→ 以持续性为骨架的 D-1 预警（2026 AUC 0.838，概率前 30 日命中率 93.3%）。

| 报告 | 目录（`output/`） | 对应流程 |
|------|------------------|---------|
| NSRDB + pvlib 光伏出力建模验证 | `nsrdb_pvlib_2022-07/` | PS-021 |
| 光伏缺口 × 电价冲击推演 | `pv_event_price_impact_2022-07/` | PS-022 |
| RTM 尾部尖峰弹性与极端场景外推 | `price_tail_elasticity/` | PS-023 |
| 光伏缺口口径统一 | `shortfall_unification/` | PS-024 |
| 缺口持续时间维度 | `shortfall_duration/` | PS-025 |
| 缺口日际/跨日持续时间 | `shortfall_duration_crossday/` | PS-026 |
| 季节预报 → 缺口风险概率化 | `seasonal_shortfall_risk/` | PS-027 |
| 风电缺口 × 电价 | `wind_shortfall_elasticity/` | PS-028 |
| 西班牙电力市场数据源调研 | `espana_esios_survey/` | PS-029 |
| 西班牙光伏最小链路 | `spain_minchain/` | PS-030 |
| 西班牙多年市场区间对比 | `spain_regime/` | PS-031 |
| 缺口成因判据可逆性检验 | `reversibility_shortfall/` | PS-032 |
| 缺口工况指纹 | `shortfall_fingerprint/` | PS-033 |
| 日尺度转移函数与 45 天展望 | `forecast_price_bridge/` | PS-034 |
| 西班牙负价概率季节预报 | `spain_negprice_forecast/` | PS-035 |
| ENTSO-E 官方口径复核 + 2026 样本外 | `spain_entsoe_verification/` | PS-037 |
| 西班牙负价模型 v3 | `spain_negprice_v3/` | PS-038 |
| 西班牙负价"爆发阈值"模型 | `spain_negprice_threshold/` | PS-039 |
| 西班牙负价 · 正午窗口份额 | `spain_negprice_noon/` | PS-040 |
| 西班牙负价 · 跨境结构 ES–FR | `spain_negprice_xborder/` | PS-041 |
| 法国正午负价的可预报化 | `spain_negprice_frforecast/` | PS-042 |
| 用真实 NWP 预报填法国侧 | `spain_negprice_nwpfr/` | PS-043 |
| 补齐 ES 侧 NWP · D-1/D-3 预警 | `spain_negprice_d1warning/` | PS-044 |
| GEM 电站 × ERCOT 电价三层联动 | `gem_ercot_price_analysis/` | PS-016 |
| 45 天季节预报精度核验 | `seasonal_forecast_accuracy/` | PS-017 |
| 数据知识总览（全项目汇总） | `data-knowledge-review/` | 汇总 |

## 使用方法

### 方式一：用 Coding Agent 阅读整个项目（推荐）

**推荐用 TRAE、Cursor、Claude Code 等 coding agent 直接打开本项目仓库**，让 AI 按需检索知识库。原因见下方[设计理念：为什么不是 Skill](#设计理念为什么不是-skill)。

**给 coding agent 的提示词示例**：

```
我要下载葵花9卫星的华东区域数据，请阅读 .knowledge/tech/processes/PS-003.md
和 .knowledge/tech/pitfalls/PF-004.md，给我一个完整的下载方案，包括：
1. 需要下载哪些分段
2. 选什么时次
3. 怎么用 satpy 处理
4. 有什么坑要避开
```

```
我要用历史预报做一次 D-1~D-7 回测，请阅读 .knowledge/tech/pitfalls/PF-015.md
和 .knowledge/tech/processes/PS-044.md，告诉我：
1. 用哪个端点、哪些参数
2. 取数前必须先做哪项筛查
3. 结论可以引用到什么程度
```

```
我要复现西班牙负价链的最新结论，请阅读
.knowledge/project/conclusions_solar_price.md 的 §2.18 与 §4，
告诉我当前基线 AUC、可用口径和不能外推的边界。
```

**纯人工阅读**也可：先看 [.knowledge/catalog.md](.knowledge/catalog.md) 了解全貌，再按需点进具体条目。

### 方式二：运行脚本下载数据

```bash
git clone https://github.com/Titanx/meteo-data-cookbook.git
cd meteo-data-cookbook

# 基础依赖（Python 3.9+）
pip install meteostat boto3 satpy pyresample pyproj numpy pandas matplotlib pillow
# 电力市场 / 建模链路另需
pip install requests statsmodels pvlib h5py fsspec openmeteo-requests
```

```bash
cd scripts/data_download/

# 地面观测（Meteostat）
python download_china_airports_2026.py
python download_east_southeast_asia_2025_2026.py
python download_americas_airports_2025_2026.py
python check_data_integrity.py

# 卫星（AWS S3 匿名）
python himawari9_segment_pipeline.py
python goes19_pipeline.py

# 电力市场
python download_ercot_prices.py      # EIA：负荷 / 分燃料发电
python download_ercot_spp.py         # GridStatus：枢纽与节点电价
python download_spain_entsoe.py      # ENTSO-E：西班牙日前价 / 分技术发电 / 负荷
python download_neighbour_ec_price.py  # Energy-Charts：ES / FR / PT 电价

# NWP 与历史预报归档
python download_spain_nwp_prevruns.py
python download_spain_ghi_archive.py
```

### 方式三：复用代码到自己的项目

| 用途 | 依赖库 | 安装 |
|------|--------|------|
| 地面观测下载 | `meteostat` | `pip install meteostat` |
| AWS S3 匿名访问 | `boto3` | `pip install boto3` |
| 卫星数据处理 | `satpy`, `pyresample` | `pip install satpy` |
| 再分析数据 | `requests` / `openmeteo-requests` | `pip install openmeteo-requests` |
| 光伏出力建模 | `pvlib` | `pip install pvlib` |
| 强度 / 概率模型 | `statsmodels` | `pip install statsmodels` |

```python
# AWS S3 匿名访问（葵花 / GOES 通用）
import boto3
from botocore import UNSIGNED
from botocore.config import Config
s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

# Meteostat 批量下载（站点 ID 复用优化）
from meteostat import Daily
from datetime import datetime
df = Daily("54511", datetime(2026, 1, 1), datetime(2026, 7, 19)).fetch()
```

## 设计理念：为什么不是 Skill

有人会问：为什么不把这些知识做成一个 coding agent 的 Skill（一次性加载所有上下文），而要维护一个分文件的 Markdown 知识库？

**答案是：气象与电力市场知识太庞杂，必须用渐进式披露（progressive disclosure）结构。**

| 问题 | 说明 |
|------|------|
| **上下文爆炸** | 目前 61 条已约 8,800 行，塞进单个 Skill 会挤占对话的有效上下文 |
| **信噪比下降** | 用户问"葵花怎么下"时，ERCOT 电价、西班牙负价链的内容全是噪声 |
| **维护困难** | 单文件改一处要重新审阅全文，分文件可独立迭代 |
| **验证成本高** | Skill 无法区分 verified 与 draft，知识库可通过成熟度标记分级 |

本项目采用三层渐进式披露：

```
第 1 层：catalog.md（索引）
  ↓ 按需选择
第 2 层：具体条目（GL-005.md / PS-044.md / PF-015.md ...）
  ↓ 条目内部再分层
第 3 层：背景 → 接口 → 代码示例 → 实测结果 → 陷阱 → 适用场景
```

**coding agent 天然适配这个结构**：先读 `catalog.md`（几十行），再只读取相关的 1–2 个条目（几百行），条目内部分层让它能直接定位到"代码示例"或"陷阱"段落。无论知识库增长到多少条，单次对话的上下文消耗始终可控——这也是为什么**推荐用 coding agent 打开本项目**而不是做成 Skill。

### 知识库 vs Skill 的选择标准

| 场景 | 适合 Skill | 适合知识库 |
|------|-----------|-----------|
| 知识总量 < 200 行，规则性强 | 是 | 过度设计 |
| 知识总量 > 500 行，领域庞杂 | 上下文爆炸 | 是 |
| 需要区分成熟度（draft / verified / proven） | 否 | 是 |
| 需要独立迭代各条目 | 否 | 是 |
| 需要 agent 按需检索 | 否 | 是 |

## 相关项目

- [satpy](https://github.com/pytroll/satpy) — 卫星数据处理库（本项目核心工具）
- [meteostat](https://github.com/meteostat/meteostat) — 地面观测数据 Python 库
- [open-earth-data-guide](https://github.com/wait4xx/open-earth-data-guide) — 中文地球系统数据源索引（互补关系）
- [awesome-meteorology](https://github.com/jeffreyspringer/awesome-meteorology) — 气象领域 awesome list

## 许可证

[MIT License](LICENSE) — 内容可自由引用，脚本可自由使用。

## 来源

所有条目基于 2026-07-18 ~ 2026-09-30 的实际下载与建模测试，非文档摘抄。取数脚本归档于 `scripts/data_download/`，建模与报告脚本归档于 `scripts/analysis/`。
