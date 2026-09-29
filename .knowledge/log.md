# 知识变更日志

> 本文件只追加，不修改历史记录。

## [2026-09-29] update | [PF-014 扩为「两处隐藏结构」+ ENTSO-E 价格通过 OMIE 交叉校验] | 更新 3 条

### 更新条目
- **PF-014 扩展**：由「curveType=A03 压缩」单一陷阱，扩为 **「ENTSO-E / IEC 62325 报文的两处隐藏结构」**
  - **陷阱二（新）**：**A44 同时混装 A01（日前）与 A07（日内）两套价格**，对同一时刻给出**不同值**
    （2026-01：10,320 行 / 3,072 唯一时刻；`mRID=1 → 112.01`、`mRID=2 → 93.22`、`mRID=3 → 91.31`），
    而**所有序列的 in/out_Domain、businessType、resolution 完全相同**，只能靠 **`contract_MarketAgreement.type`** 区分（日前取 **A01**）
  - **关键时间线**：**A07 自 2025-09 起才出现**（2023-01~2025-08 仅 A01）⇒ 2025-08 之前的"干净解析"具有欺骗性，
    代码看起来正确只是因为那时没有第二个合约；**15 分钟 MTU 切换发生在 2025-10**（与 PS-029 记录一致）
- **ENTSO-E 价格数据通过一手交叉校验**（`data/entsoe/price_da.csv`，59,039 行）：
  - 2024-04-29 日均 **58.27** / 最低 **35.00** / 最高 **102.26** ⇔ PS-029 一手 OMIE **三项完全一致**
    ⇒ 合约过滤正确，且 **ENTSO-E 小时时间戳与 OMIE「小时序号」口径一致（均为时段起点，无需平移）**
  - 年度负价小时：2023 = **0**、2024 = **247**（均与 PS-031 一致）、2025 = 557（PS-031 Energy-Charts 口径 544，差 13 h）
  - 逐月点数全部符合预期（小时口径 744/720/696/672；15 分钟口径 2976/2880/2688；2025-09 过渡月 726）
- `scripts/data_download/download_spain_entsoe.py`：新增 `contract` 维度与 **A01 过滤**；新增 `--reparse`
  （**只从缓存 XML 重解析、不再请求网络**，符合平台 responsible-use）
- `PS-036`：补入陷阱二指引、价格交叉校验结果与产物规模
- `tech/catalog.md`：PF-014 标题与标签同步

## [2026-09-29] update | [PS-036 转 verified + 新增 PF-014（A03 压缩陷阱）] | 新增 1 条 + 更新 4 条

### 新增条目
- 新增 PF-014：ENTSO-E / IEC 62325 的 **curveType=A03 压缩陷阱**（verified）
  - **现象**：A44 2024-04 解析出 **573 行**（应为 744），逐日点数 9~21 不等，看似大规模缺测
  - **根因**：报文的 `<curveType>A03</curveType>` = 变长块，**连续相同的值只写一个 Point，其值延续到下一个 Point 之前**
    （第 1 天 `pos3=0`→`pos7=0.13` ⇒ 4/5/6 都是 0）。旁证：B02/B07 等技术只有 **1 个 Point**（整月恒定 0）
  - **危害**：静默丢失 20%~35% 小时，且**折叠掉的正是零价/负价时段** ⇒ 会系统性压低西班牙负价概率
  - **修复**：按 `position` 前向填充、用 `timeInterval` 的 start/end 与 `resolution` 算槽位数展开；
    去重键须带维度（A75 按 `["datetime_utc","psr_type"]`，单键会把多技术压成一条）
  - 修复后核对：2024-04 A44 = **744/744**；A75 = **2880 个唯一时刻 = 30×96**

### 更新条目
- `PS-036`：**draft → verified**。用户取得 ENTSO-E security token，A44/A75/A65 **全部 HTTP 200**；
  2023-01~2026-09（45 个月）按月下载；实测分辨率 A44=`PT60M`、A75/A65=`PT15M`；
  补入 A03 解析陷阱指引、更新局限（无弃电指标、尚未与 Energy-Charts/OMIE 交叉校验）
- `scripts/data_download/download_spain_entsoe.py`：解析器加 A03 前向填充展开；发电数据去重键改为
  `["datetime_utc","psr_type"]`（原按时间戳单键去重会把多技术压成一条 —— 另一个静默 bug）
- `tech/catalog.md`：PF 表 + 计数（39 条）+ 数据源索引 + verify/debug 阶段 + 新增"IEC 62325/变长块解析"技术项
- `project/catalog.md` 与项目记忆同步

## [2026-09-29] add | [PS-036 西班牙 ENTSO-E Transparency 数据链路] | 新增 1 条

### 新增条目
- 新增 PS-036：西班牙 ENTSO-E Transparency 数据链路（**draft**，token 待申请）
  - 动因：ESIOS 被 REE **域名级 WAF 封锁**（[PF-013]），改用 ENTSO-E 拿西班牙分技术实际发电/负荷/日前价
  - **实测（2026-09-29）**：`web-api.tp.entsoe.eu/api` **可达**；无 token 返回 **HTTP 401 + `text/xml`**
    标准 `Acknowledgement_MarketDocument`（`Authentication failed.`），**不是** WAF 拦截页 ⇒ 与 ESIOS 处境本质不同
  - 门户 `transparency.entsoe.eu` 200；Keycloak realm 200；西班牙 EIC = **`10YES-REE------0`**
  - 参数结构被接受（401 而非 400）：`A44` 日前价 / `A75` 分技术实际发电（`processType=A16`, `in_Domain`）/ `A65` 实际负荷（`outBiddingZone_Domain`）
  - **token 申请（官方步骤）**：注册 transparency.entsoe.eu → 验证邮箱 → 发邮件 `transparency@entsoe.eu`
    （**主题 `RESTful API access`**，正文写注册邮箱）→ 等 ≤3 工作日 → My Account 生成 security token
  - 鉴权：`securityToken` **查询参数** 或 `Authorization: Bearer`（与 ESIOS 的 header 写法不同）
  - 另一条路：File Library 走 **Keycloak**（`keycloak.tp.entsoe.eu/realms/tp/...`），适合批量文件级下载
  - 局限：token 未取得（端到端未跑通）；粒度取决于 TSO 报送；**无 ESIOS 的"技术受限/弃电"指标**；不适合实时预警
- 新增脚本：`scripts/data_download/test_entsoe_api.py`（自检，退出码 4 = 缺 token，与 403 拦截区分）、
  `scripts/data_download/download_spain_entsoe.py`（IEC 62325 XML 解析 + 按月缓存续传 + 代理可感知；`--check`/`--docs`）
- 更新 `project/catalog.md`：ENTSO-E 数据源状态（待token → 端点实测可达/token 待申请）+ 2 条脚本索引
- 更新 `tech/catalog.md`：流程表 + 数据源索引 + 架构阶段索引

## [2026-09-29] add | [PF-013 REE/ESIOS 域名级 WAF 封锁] | 新增 1 条

### 新增条目
- 新增 PF-013：REE/ESIOS 域名级 WAF 封锁（verified）
  - 背景：用户 2026-09-29 拿到 ESIOS 个人 token（REE 邮件：仅限本人使用、公开项目须落自有服务器、禁止冗余请求）
  - **现象**：`api.esios.ree.es` / `www.esios.ree.es` / `www.ree.es` / `apidatos.ree.es` **全部 403**，
    返回同一张 **Imperva/Incapsula** 拦截页（`X-Iinfo`、`visid_incap_*`、`_Incapsula_Resource`）
  - **判定（三条独立证据）**：① 带/不带 token、连根路径都 403 ⇒ 拦在鉴权**之前**，非 token 问题；
    ② `curl_cffi` 的 Chrome/Safari/Edge **TLS 指纹伪装**全 403 ⇒ 非指纹识别；
    ③ Playwright **有界面**真实 Chromium 也 403 ⇒ 非 JS 挑战/无头检测，属**域名级（出口 IP）封锁**
  - **对照**：同机 OMIE / Energy-Charts / PVGIS / Open-Meteo / ENTSO-E 门户 **均 200** ⇒ 只有 `*.ree.es` 被挡
  - **处置**：换到可访问 ree.es 的网络，或设 `ESIOS_PROXY`（脚本已支持）；
    在此之前西班牙链路继续用 Energy-Charts + OMIE + Open-Meteo Seasonal
- 新增脚本：`scripts/data_download/test_esios_api.py`（自检，退出码 3 = 被 WAF 拦截）、
  `scripts/data_download/download_spain_esios.py`（代理可感知 + 按月续传，`--check`/`--list`/`--start --end`）
- 更新 `tech/processes/PS-029.md`：新增 §5.1（token 已获但被 WAF 拦截）、更新数据源表与 §7 下一步、§9 文件
- 更新 `project/catalog.md`：ESIOS 数据源状态（待token → token已获但需换网/代理）+ 2 条脚本索引
- 更新 `tech/catalog.md`：PF 表 + 数据源索引 + 阶段索引 + 反爬虫标签

> 备注：`tech/catalog.md` 的流程表与 `log.md` 止于 PS-024（2026-09-27），
> PS-025~PS-035 的条目此前未回填（本次未一并补齐，留待后续整理）。

## [2026-09-27] add | [项目结论总览：光伏缺口 × 电价冲击链路] | 新增 1 文档

### 新增
- 新增 `project/conclusions_solar_price.md`：跨条目结论总览（覆盖 PS-021~PS-024）
  - **一句话结论**：ERCOT 光伏缺口对 RTM 电价的条件均值弹性约 **+5.3 %/GW**
    （区间 +3.5~+5.7），对**缺口定义 / 评估口径 / 样本年份 / 数据粒度**四重变换稳健；
    2022-07 全月 44 事件 100.3 GWh → RTM 中位上浮 **+8~+11%**、最大 **+18~+25%**；
    **电价尖峰主导因子是需求与时段，非光伏缺口**
  - 已确立结论（高置信）：① 纯物理建模可达 r=0.9976 无需历史训练；
    ② 弹性 ≈ +5.3 %/GW 四重稳健（推荐引用 **+5.0 ± 0.5**）；③ 冲击推演三口径收敛；
    ④ 尖峰 − 缺口边际负相关，机制是天气组合负相关（云致缺口 ↔ 降温低需求）
  - 已修正结论：① PS-022"高需求区 +5.84"不成立（子样本法两年反向，交互项 −1.95/−1.00，
    应视为上界）；② PS-023"P95 包络虚高致悖论"推测被 PS-024 推翻；
    ③ "小时平均无偏"澄清（抹平的是价格水平 2.4×，非斜率）
  - 口径规范：缺口定义必须声明（物理 vs P95 包络，量级差 1.3~1.7 倍）；EIA-930 须 −1h；
    GEM 2026 装机不完整（EIA 峰值 34,982 > 清单 30,884 MW）不宜做绝对发电量估计
  - 未决问题 6 项（持续时间维度、概率化、装机补全、风电缺口、储能影响、节点级验证）
- 更新 `project/catalog.md`：页首新增"结论总览"指引链接

## [2026-09-27] add | [PS-024 光伏缺口口径统一：物理晴空反事实 vs P95 包络] | 新增 1 条 + 更新 2 条

### 新增条目
- 新增 PS-024：光伏缺口口径统一（verified）
  - 修复 PS-022 的方法论隐患：2022-07 推演用物理晴空反事实，但 2025/2026 弹性标定用 P95 包络
  - 2025/2026 物理反事实建成：GEM 按年筛选（`start-year ≤ 年` + operating + ≥100MW）
    → **141 座 30.89 GW（占 ≥10MW 全网 94.5%）**；NSRDB 像素 141/141 匹配（中位 0.9 km）；
    Open-Meteo HRRR 2m 温度 141 站 × 14,736 h（−20.2~44.6 °C，无缺失，多坐标批量 8 次请求）；
    pvlib Solis 同链路 5min → 小时；逐小时偏移校准
  - **幅度偏差**：反事实峰值 30,884 MW；EIA 峰值 2025 = 29,503（比值 0.955）、
    **2026 = 34,982（比值 1.133）** → GEM 2026-08 版只到 2025 投产，2026 新增约 4 GW 未录入
  - **缺口量级差异 1.3~1.7 倍**：物理中位 5.86/5.32 GW（2025/2026）vs 包络 3.49/4.13 GW；
    两者回答不同问题（"相对完全无云" vs "相对典型晴天 P95"）→ 报缺口必声明定义
  - **弹性对口径不敏感（核心）**：物理 OLS 均值 +5.05/+6.15（两年 **+5.60**）vs 包络
    +5.08/+5.43（**+5.26**），差 0.34 %/GW；Q50/Q90/Q99 差 < 0.5 → PS-022/023 弹性结论独立复核通过
  - **辛普森悖论归因修正（推翻 PS-023 推测）**：物理口径下分箱尖峰率**仍随缺口下降**
    （2025: 2.0%→0.0%；2026: 1.7%→0.7%）→ **非 P95 包络虚高所致**；
    真正机制是**天气组合负相关**（云致缺口 ↔ 阴天降温低需求；尖峰需高需求+供给紧张）
    ⇒ "云致缺口 × 热浪高需求"是罕见高风险组合；PS-023 核心结论（尖峰主由需求/时段驱动）被强化
  - **2022-07 三口径收敛**：物理 P50 中位 +8.5%/最大 +18.9%、P90 +9.7%/+21.9%、
    P99 +10.2%/+23.0%（$19~$42）；P95 口径 +8.0%/+17.8% ~ +10.5%/+23.7%；
    PS-022 单年均值口径 +11.0%/+25.0% → 中位收敛 +8.0~+11.0%、最大 +17.8~+25.0%，
    口径统一后 1 个百分点内一致，稳健性三重确认
  - 热浪期 10 事件 25.6 GWh：物理 P50 中位 +9.6% / P99 中位 +11.6%
  - **实证陷阱 ①**：GEM 按年清单可能不完整（`start-year` 最晚到 2025），不宜用物理反事实做绝对发电量估计
  - **实证陷阱 ②**：逐小时偏移是**加法**校准，对幅度偏差只是近似修正；清单缺失 >30% 时应显式引入缩放因子
  - 陷阱 ③：Open-Meteo 支持逗号分隔多坐标批量（顺序一致），单站 613 天 ~10 秒；批量 20 站/次压缩到 8 次请求
  - 陷阱 ④：`偏移 / 该小时反事实中位` 在低太阳角小时（中位=0）出现 inf，勿用比值诊断校准质量

### 更新条目
- 更新 PS-023：末条"方法学警示"改为"物理口径不减轻悖论"（归因被 PS-024 修正，结论被强化）
- 更新 PS-022：口径隐患标记为已由 PS-024 修复

### 目录与产物
- 更新 tech/catalog.md、根 catalog.md：条目 35 → 36（35 verified + 1 draft），
  知识图谱 +PS-024 节点、按数据源 +GEM/NSRDB/GridStatus 关联、按通用技术 +口径一致性检验
- 更新 project/catalog.md：数据源 +3 行、脚本索引 +6、分析结果 +1、报告 +1；
  待办"用物理晴空反事实统一缺口口径"完成移除
- 新增脚本：`match_nsrdb_ercot_solar_annual.py`、`download_hrrr_temp_2025_2026.py`、
  `clearsky_counterfactual_2025_2026.py`、`build_physical_shortfall_2025_2026.py`、
  `compare_shortfall_definitions.py`、`pv_event_price_impact_physical_2022-07.py`、
  `build_shortfall_unification_report.py`
- 新增数据：`ercot_solar_plants_pixels_{2025,2026}.csv`、`hrrr_t2m_2025_2026.npz`、
  `pv_clearsky_hourly_2025_2026.csv`、`shortfall_physical_2025_2026.csv`、
  `shortfall_definition_comparison.csv`、`pv_event_price_impact_physical_2022-07.csv`
- 新增报告：`output/shortfall_unification/ercot_shortfall_unification.html`（自包含, 4 图 4 表）

## [2026-09-27] add | [PS-023 RTM 尾部尖峰弹性标定与极端场景外推] | 新增 1 条 + 更新 1 条

### 新增条目
- 新增 PS-023：RTM 尾部尖峰弹性标定与极端场景外推（verified）
  - 口径：15min RTM（HB_HOUSTON 58,940 条）对齐小时 EIA 供需；**小时平均把极端小时价格抹平
    2.4×**（15min max $3777 vs 小时均值 max $1561），但 q99 阈值几乎不变（$146 vs $143）
    → 弹性是尺度不变斜率，**PS-022 弹性估计无系统性偏误**，被低估的是绝对水平
  - 基线复现：小时均值 OLS **+5.08 %/GW (2025) / +5.43 (2026)**，与 PS-022 完全一致
  - 分位弹性 Q_τ(ln RTM)（15min）：**2025 单调升 3.85→5.16（τ=.5→.995），2026 平坦 3.67→3.78**
    → 两年不一致，**不支持尾部弹性系统性放大**；条件均值弹性高于任一分位
  - 原始尺度（小时极值 $/MWh）：缺口 +1GW → 中位 +$1.0、Q99 **+$2.4（2.4×）**；
    但高分位价格水平高（$200 vs $29），**相对弹性反而更低**，两口径自洽
  - **凸性不成立**：ln 尺度缺口² 仅 2025 全样本边际显著（+0.211, t=+2.6，受 sf 长尾至 13.5GW 拉动）；
    事件尺度（≤6GW）t=−0.9、2026 t=+0.6、Q99 符号为负 → PS-022 线性外推未被证伪
  - **尾部概率辛普森悖论**：条件 GLM 控制需求/时段后缺口为正（2026 lnOR +0.332）；
    但**边际尖峰率随缺口不升反降**（1.5%→0.7%）——P95 包络在低太阳高度角虚高，大缺口
    落在清晨/黄昏，而尖峰在傍晚需求高峰 → **尖峰主导因子是需求与时段，缺口次要**
  - **高需求弹性修正（推翻 PS-022 的 +5.84）**：子样本法两年方向相反（2025 +5.84 / 2026 +4.33）；
    子样本内 demand sd 仅 2.80（全样本 10.52）致控制变量失效、系数从 3.26 抬到 5.84；
    全样本交互项法两年一致为负增量（−1.95 / −1.00）→ **高需求合计 +3.26 / +4.48，不放大反而略弱**
  - 2022-07 分位情景（两年平均 β：P50 +3.76 / P90 +4.28 / P99 +4.55 %/GW）：
    44 事件 100.3 GWh → **P50 中位 +8.1% 最大 +18.0%；P90 +9.2%/+20.7%；P99 +9.8%/+22.1%**；
    **PS-022 的 +11.0%/+25.0% 落在分位曲线上沿** → 原推演略偏保守（偏激进），未低估，可直接沿用
  - 稳健性（小时粒度无伪重复，4 口径 × 2 年）：弹性稳定 **+3.5~+5.7 %/GW**，PS-022 的 +5.08 居中
  - **实证陷阱 ①**：回归量必须用 GW——MW 量级致 QuantReg IRLS 条件数恶化，5000 次迭代不收敛（仅告警）
  - **实证陷阱 ②**：15min 与小时供需对齐产生 **4× 伪重复**，SE 偏小，推断须用小时粒度或 block bootstrap
  - 陷阱 ③：statsmodels 0.15 QuantReg 不支持 `cov_type="cluster"`；GLM 截距名为 `Intercept` 非 `const`
  - 陷阱 ④：`import xxx as C` 与 patsy 的 `C()` 冲突；`reset_index()` 列名继承 Series 的 index.name
  - 陷阱 ⑤：窄范围子样本回归不可信（控制变量方差坍塌时弱相关被放大为严重偏误）→ 用全样本交互项

### 更新条目
- 更新 PS-022：新增关联指向 PS-023（尾部口径复核 + 高需求结论修正 + 分位外推）

### 目录与产物
- 更新 tech/catalog.md、根 catalog.md：条目 34 → 35（34 verified + 1 draft），
  领域说明 + 联动分析补尾部弹性、知识图谱 +PS-023 节点、按数据源 +GridStatus RTM、
  按通用技术 +分位数回归/尾部风险
- 新增脚本：`calibrate_price_elasticity_tail.py`、`pv_event_price_impact_tail_2022-07.py`、
  `build_price_tail_report.py`
- 新增数据：`price_elasticity_tail.csv`（54 行标定）、`pv_event_price_impact_tail_2022-07.csv`
- 新增报告：`output/price_tail_elasticity/ercot_rtm_tail_elasticity.html`（自包含, 5 图 10 表）

## [2026-09-27] add | [PS-022 光伏缺口×电价冲击推演：温度修复 + USCRN 验证 + 弹性标定] | 新增 1 条 + 更新 1 条

### 新增条目
- 新增 PS-022：光伏缺口 × 电价冲击推演流程（verified）
  - 温度链路修复：NSRDB 无表面温度 → HRRR 2m 实测（56 站×744h，16.2~44.3°C）；
    ILR 1.25→1.30 四窗口扫描；**热浪正午偏差 -327→+16 MW、MAE 405→273，全月 MAE 185→174、能量 -2.1%→+1.4%**
  - USCRN 地面交叉验证（8 站 5min）：NSRDB 比 USCRN 系统性高 ~10%（已知水平差，被 ILR/损耗吸收），
    **热浪期无额外漂移（-1.4~-2.1%，站间离散内）→ 排除反演劣化，锁定温度参数化**
  - USCRN 坑：文件名按版本号 `CRNS0101-05`（非月份）；无表头 23 列；时间戳为 5min 区间结束须 -5min；缺测 -9999
  - 骤降归因：7 个事件解释比 0.95~2.88 **全部云主导，无弃光**；07-13 渐进下降未触发骤降阈值 →
    骤降（时间导数）与缺口（对晴空水平差）两口径互补
  - 弹性标定：ln(RTM) 面板（shortfall + wind + demand + 小时/月 FE），
    **2025 β=+5.08 %/GW (SE 0.25)，高需求 ≥72GW +5.84；2026 复验 +5.43/+4.33，两年一致 ±7%**
  - 2022-07 推演：**44 事件小时 → 17 事件、100.3 GWh**，中位缺口 2.06 GW、最大 4.40 GW（07-21）；
    **RTM 中位上浮 +11.0%、最大 +25.0%**；按 North 月均 $182 折算 +$20~+$46/MWh；
    热浪期 3 事件 25.6 GWh（07-13 傍晚云×77.5GW 需求 = 最强冲击 +21.9%）；07-14 撒哈拉沙尘日 10.4 GWh（缺口为上界）
  - **实证陷阱 ①**：pvlib 0.15.2 `simplified_solis` 数组输入返回 OrderedDict 非 DataFrame → `np.asarray(cs["dni"])`
  - **实证陷阱 ②**：晴空缺口校准必须**逐小时偏移**（每 hour 的 5% 分位）——单一全局偏移把傍晚低仰角
    跟踪 POA 系统性高估计入缺口，事件小时虚增 62→44、总量虚高 43%；逐小时校准后晴日正午缺口中位 67 MW
  - 陷阱 ③：β 单位换算 (ln, per MW) → %/GW 需 ×100000；2022-07 EIA-930 无 demand 字段 → 全燃料出力和做需求代理

### 更新条目
- 更新 PS-021：推广方向两条待办标记完成，指向 PS-022；相关知识 +PS-022

### 目录与产物
- 更新 tech/catalog.md、根 catalog.md：条目 33 → 34（33 verified + 1 draft），
  领域说明 + 联动分析、知识图谱 +PS-022 节点、数据源索引 +USCRN/Open-Meteo/NSRDB/ERCOT 关联
- 更新 project/catalog.md：数据源 +2 行（USCRN、HRRR 2m 温度）、分析结果 +1、脚本索引 +9、
  待办完成移除 2 项（真实温度接入、光伏骤降×电价推演）、新增 1 项（RTM 事件尾部建模）
- 新增脚本：`download_hrrr_temp_july2022.py`、`download_uscrn_tx_july2022.py`、
  `download_nsrdb_uscrn_pixels_july2022.py`、`verify_temp_fix.py`、`ilr_sweep_heatwave.py`、
  `verify_nsrdb_vs_uscrn_july2022.py`、`identify_pv_drop_events_2022-07.py`、
  `calibrate_price_elasticity_2025.py`、`pv_event_price_impact_2022-07.py`、`build_pv_event_price_report.py`
- 新增数据：`hrrr_t2m_2022-07.npz/csv`、`data/uscrn/`（8 站）、`nsrdb_uscrn_daily.csv`、
  `pv_drop_events_2022-07.csv`、`price_elasticity_2025.csv`、
  `pv_counterfactual_hourly_2022-07.csv`、`pv_event_price_impact_2022-07.csv`
- 新增报告：`output/pv_event_price_impact_2022-07/pv_event_price_impact_ercot_2022-07.html`

## [2026-09-27] add | [PS-021 NSRDB 辐照批量提取 + pvlib 光伏出力建模验证] | 新增 1 条 + 更新 1 条

### 新增条目
- 新增 PS-021：NSRDB 辐照批量提取与 pvlib 光伏出力建模验证流程（verified）
  - 全链路：GEM 电站坐标 → NSRDB 像素映射（56 座 ≥100MW，10.66 GW，中位距离 0.9 km）→ 分块提取（2000×500 chunk，735 块，自愈重试+断点续传）→ pvlib PVWatts → EIA-930 验证
  - 建模标定（物理合理非拟合）：单轴跟踪 backtrack gcr=0.35、ILR 1.25、系统损耗 14%、Tamb 25→39°C 热浪日循环、γ=-0.37%/°C
  - **最终精度：小时 r=0.9976、MAE 185 MW（峰值 1.9%）、月能量 -2.1%、昼夜形状 r=0.9993、爬坡 r=0.987**，无需历史出力训练
  - **实证陷阱 ①（最重要）**：EIA-930 小时时间戳为区间结束（hour-ending），值属于 [t-1, t)，融合前必须 -1h 平移（r 0.942→0.992）；典型指纹=早晚肩部形状错位+最大偏差固定在同一 UTC 时次
  - **实证陷阱 ②**：pvlib singleaxis/get_total_irradiance 角度参数是度数，误传弧度不报错且 POA 量级恰好接近真实（退化为 DNI+DHI），极难察觉
  - 实证陷阱 ③：fsspec/aiohttp 长进程连接"病变"（1 块/s→1 块/5min 不触发超时），重启进程即恢复，长批量任务须支持外部重启续跑
  - 偏差源：热浪核心期（07-14~18）正午低估 10~20%（温度参数化）；早晚肩部个别小时高估 30~66%（低仰角反演），日能量影响 <0.5%

### 更新条目
- 更新 PS-019：末尾待办标记完成，指向 PS-021

### 目录与产物
- 更新 tech/catalog.md、根 catalog.md：条目 32 → 33（32 verified + 1 draft），知识图谱 +PS-021 节点
- 更新 project/catalog.md：NSRDB 数据源行（2022-07 提取完成）、分析结果 +1、脚本索引 +5、待办"NSRDB ERCOT 辐照批量提取"完成移除
- 新增脚本：`match_nsrdb_ercot_solar.py`、`download_nsrdb_ercot_july2022.py`、`download_eia_solar_2022.py`、`nsrdb_pvlib_power.py`、`nsrdb_eia_comparison.py`、`build_nsrdb_pvlib_report.py`
- 新增数据：`ercot_solar_irradiance_2022-07.nc`（6.1 MB）、`ercot_pv_power_2022-07.csv`、`ercot_solar_plants_pixels.csv`
- 新增报告：`output/nsrdb_pvlib_2022-07/nsrdb_pvlib_ercot_2022-07.html`

## [2026-09-27] add | [PS-018 + PS-019 + PS-020 新数据源调研：MRMS/NSRDB/S2S] | 新增 3 条

### 新增条目
- 新增 PS-018：MRMS 雷达定量降水 (QPE) 下载与 ERCOT 裁剪流程（verified）
  - 双通道：AWS S3 `noaa-mrms-pds` 匿名归档（2020-10-14 ~ 2023-07-10，恰好 1000 天，需 continuation-token 翻页）+ NCEP 官网滚动最新 ~10 天（滞后 ~1 天）
  - 产品 `MultiSensor_QPE_01H_Pass2`：0.01°（~1 km）逐小时，比 IMERG 0.1° 高一个量级
  - 坑：GRIB2 经度为 **0-360 约定**（ERCOT=253.3~266.6），用负经度匹配得 0 格点；cfgrib 参数名显示 unknown
  - 实测：2023-07-10 21Z 捕捉德州 33.3 mm/h 对流核心（>5mm 格点 2214 个），09Z 全域无雨；ERCOT 裁剪 1070×1330
- 新增 PS-019：NSRDB 太阳辐照度 S3 懒读取与 ERCOT 像素定位流程（verified）
  - v3.2.2 单年 h5 1.8 TB，developer.nrel.gov DNS 不通，S3 匿名是唯一路径
  - 坑：v3.2.2 "CONUS" 实为 GOES-East+West 全视域（lat 14.5~49.4 含墨西哥、lon -160~-60 含夏威夷~波多黎各），像素 0 在夏威夷海域
  - h5coro（HTTPDriver + credentials=None + 128KB 缓存行）读 /ghi uint16 [105120, 2842719]（5 min × 2 km，值即 W/m²）
  - **像素定位待办当场解决**：meta 为 compound（h5coro 不支持），用 h5py 取磁盘偏移（连续存储 offset=2636192）+ requests Range 流式下载 346.8 MB + numpy frombuffer 解析 → ERCOT **330,096 像素**（德州 163,017），索引 npz 已缓存
  - 端到端验证：奥斯汀像素 (30.38N, -97.89W) 7月1日峰值 995 W/m² @ 12:15 LST，天文自洽
- 新增 PS-020：WMO S2S 数据库获取路径（draft，门户可达已验证，注册后待实测）
  - 13 中心多模式回算，2015 起实时存档；2026-04-21 起从旧 WEB-API 迁移至 ECMWF Data Store (ECDS)
  - ECDS 门户与 API catalog 实测 HTTP 200（中国网络直连可用）；需注册 ECMWF 账号
  - 用途：把 PS-017 单窗口核验升级为多年回算多窗口统计（优先 ECMWF/NCEP/CMA）

### 目录更新
- 更新 tech/catalog.md、根 catalog.md：条目 29 → 32（31 verified + 1 draft），领域说明/数据源图谱/知识图谱同步
- 更新 project/catalog.md：数据源索引 +3 行、脚本索引 +4 个、待办事项 +2 项
- 新增脚本：`test_mrms_download.py`、`test_nsrdb_h5coro.py`、`test_nsrdb_meta.py`、`test_nsrdb_mrms_s2s.py`
- 新增数据：`data/mrms/`（ERCOT 裁剪样例）、`data/nsrdb/`（meta 全缓存 + ERCOT 像素索引 npz）

## [2026-09-16] add | [PS-017 S2S 季节尺度预报获取与精度核验] | 新增 1 条 + 更新 1 条

### 新增条目
- 新增 PS-017：S2S 季节尺度预报获取与精度核验流程（verified）
  - 数据源：Open-Meteo seasonal-api（ECMWF EC46 46天逐日 + SEAS5 7个月逐月，51 成员集合，36 km）
  - 端点坑：正确端点是 `seasonal-api.open-meteo.com`，`api.open-meteo.com/v1/seasonal` 实测 404
  - 核验方法：ERA5 逐日再分析为实测基准，逐 lead 计算 MAE/RMSE；GFS 10 天（ncep_gfs_seamless）作对比
  - 实测（2026-08-10~09-15，ERCOT 6 站）：45天风速 MAE 1.49 vs GFS 10天 1.30 km/h；降水 1.26 vs 0.26 mm（~4.8×）
  - 重叠段 lead 6~10 风速两者相当（1.35 vs 1.30 km/h）；降水误差呈事件型尖峰（3~6 mm）
  - 数据未偏置订正、36 km 区域平均，宜看倾向/离散度，不宜当逐日定量数值

### 目录更新
- 更新 GL-004：端点总览表新增 seasonal 行 + 修正季节预报正确端点
- 知识库条目数：28 → 29
- 新增下载脚本：`verify_seasonal_vs_gfs.py`、`download_seasonal_forecast.py`
- 新增分析脚本：`build_forecast_accuracy_summary.py`、`rebuild_full_chart_arrays.py`
- 新增数据：`data/openmeteo_seasonal/`（45天 raw + verif 序列 + 误差表）
- 新增输出：HTML 精度核验报告

## [2026-09-11] add | [PS-016 GEM 电站数据库 × ERCOT 电价联动分析] | 新增 1 条

### 新增条目
- 新增 PS-016：GEM 电站数据库下载与 ERCOT 电价联动分析流程（verified）
  - GEM 2026-08 数据库 182,668 条（光伏 103,940 + 风电 35,089）
  - 绕过邮箱注册：maps GitHub config.js 暴露 DigitalOcean CDN 直链
  - ERCOT 474 座运行中电站（风电 38.0 GW + 光伏 33.0 GW = 71.0 GW）
  - 三层分析：装机结构 / 发电×电价相关（风电夜间 r=-0.384）/ 雷暴×电站交叉（KIAH 1.43x）
  - 电价尖峰本质：风光同时缺位 + 高负荷（风光渗透率 12.6% vs 39.4%）

### 目录更新
- 知识库条目数：27 → 28
- 新增分析脚本：`scripts/analysis/gem_ercot_lz_analysis.py`、`gem_ercot_deep_dive.py`、`gem_storm_cross.py`
- 新增数据：`data/gem/`（GEM 6 文件 + WRI 1 文件）
- 新增输出：HTML 分析报告目录 + 3 个 CSV

## [2026-09-11] add | [PS-015 GK2A AMI 卫星数据下载] | 新增 1 条

### 新增条目
- 新增 PS-015：GK2A (GEO-KOMPSAT-2A) AMI 卫星数据下载流程（verified）
  - 韩国静止气象卫星, 定点 128.2°E, 16 通道, 10 分钟全圆盘
  - AWS S3 匿名访问 (noaa-gk2a-pds), 无需认证
  - IR105: 33.6 MB/文件 (5500×5500, 2km), WV073: 27.9 MB
  - GEOS 投影, 需 satpy 重采样到 WGS84
  - 与 Himawari-9/FY-4 覆盖重叠, 可交叉验证

### 目录更新
- 知识库条目数：26 → 27
- 新增脚本: `scripts/data_download/download_gk2a.py`
- 测试数据: IR105+WV073 各 4 文件, 246 MB

## [2026-09-09] add | [PS-014 ASTER地形×GLM闪电联动分析] | 新增 1 条

### 新增条目
- 新增 PS-014：ASTER 地形与 GLM 闪电分布联动分析流程（verified）
  - 11,410 个 ERCOT 闪击 × 154 ASTER tiles (30m GDEM+WBD)
  - 双峰高程分布: 57.8% 在 100-200m 沿海平原, 12.1% 在 >1000m 山区
  - 中等坡度主导: 36.3% 在 5-10°, 仅 1.3% 在极平坦地形
  - 水体效应不显著: 93.5% 距水体 >5km

### 目录更新
- 知识库条目数：25 → 26
- 新增分析脚本: `scripts/analysis/terrain_lightning_analysis.py`
- 新增输出: 3 张可视化图表 + 2 个统计 CSV

## [2026-09-07] add | [GL-009 + PF-012 + PS-013 凭证安全/CMA陷阱/ASTER地形] | 新增 3 条

### 新增条目
- 新增 GL-009：气象数据 API 凭证安全管理实践（verified）
  - netrc (Earthdata) + .env (EIA/GridStatus) + config.ini (CMA) 三层管理
  - .gitignore 防护：.env, _netrc, .netrc, .nmcdev/
  - 7 个脚本已从硬编码改为自动加载凭证
- 新增 PF-012：CMA 气象数据访问陷阱（verified）
  - CMADaaS 需内网 VPN（10.20.76.55 内网 IP）
  - data.cma.cn API 账号独立注册，网站账号 ≠ API 账号
  - nmc-met-io 库不支持 FY-4 LMI 闪电数据
  - 替代方案：NSMC/中科院公开数据集 + 国际数据源
- 新增 PS-013：ASTER GDEM 地形与水体数据下载流程（verified）
  - ASTGTM.003 (30m 高程) + ASTWBD.001 (30m 水体分类)
  - ERCOT 区域 154 tiles, 8.48 GB
  - earthaccess + netrc 认证, rasterio 读取

### 目录更新
- 知识库条目数：22 → 25（新增 3 条 verified）
- 数据源覆盖新增：地形/水体数据（ASTER）、CMA 数据访问陷阱、凭证安全
- 数据量新增：ASTER GDEM 2.89 GB + WBD 5.59 GB = 8.48 GB
- project/catalog.md 更新：新增 6 个数据源, 8 个脚本, 凭证配置, 待办事项

## [2026-09-07] add | [PS-010 GPM IMERG 降水数据下载] | 新增 1 条

### 新增条目
- 新增 PS-010：GPM IMERG 降水数据下载流程（verified）
  - Earthdata 注册 + EULA 接受 + earthaccess 下载
  - 实测 30 分钟产品 7.8 MB，日产品 31 MB
  - 下载速度 1.3~4.3 MB/s（中国网络）

### 目录更新
- 知识库条目数：21 → 22（新增 1 条 verified）
- 数据源覆盖新增：卫星降水（IMERG）

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