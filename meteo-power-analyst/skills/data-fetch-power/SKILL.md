# 数据获取 · 电力市场

**状态**: ✅ 可用 — ERCOT（GridStatus 通道）、ENTSO-E Transparency、Energy-Charts、GEM 电站库均跑通；
ESIOS / REE 官方接口被域名级 WAF 封锁，已改用 ENTSO-E 替代口径。
风电场级开源数据集（ENGIE La Haute Borne / Kelmarsh）已跑通并落盘。

**用途**: 拉取电价、负荷、发电构成、机组名录与装机，落盘为可对齐的日/小时面板，供出力与缺口链路使用；
另含风电场级 SCADA / 并网点实测数据，用于风机级建模与短期功率预测。

**入口检查**:
1. 先查 `data/` 下是否已有对应面板（如 entsoe/、spain/、ercot/、energy_charts/、gem/）→ 有则直接用
2. 无 / 过期 → 按下方选源；**优先免凭证源**

## 选源（按可达性排序）

| 目标 | 首选脚本 | 备选 | 说明 |
|------|----------|------|------|
| 欧洲电价 / 发电构成 | `references/download_spain_ec_history.py`、`references/download_france_ec_power.py` | `references/download_spain_entsoe.py` | 免凭证优先；ENTSO-E 需 token |
| 跨境邻居量 | `references/download_neighbour_ec_price.py`、`references/download_neighbour_entsoe.py` | — | 用于"区域过剩"通道 |
| 西班牙多源对照 | `references/download_spain_data.py`、`references/download_spain_data_multi.py` | `references/download_spain_esios.py` | ESIOS 已被 WAF 封锁，仅留作探活 |
| ERCOT 电价 / SPP | `references/download_ercot_prices.py`、`references/download_ercot_spp.py` | — | 走 GridStatus 通道，勿直连官网 |
| 机组名录与装机 | `references/prep_spain_pv_fleet.py`、`references/prep_spain_pv_fleet_multi.py`、`references/prep_ercot_wind_fleet.py`、`references/prep_france_pv_fleet.py` | — | 从 GEM 电站库派生代表点位 |
| 代表点位（含 share 权重） | `references/prep_spain_nwp_hubs.py` | — | 点位 + 覆盖率必须写进报告 |
| 面板拼装 | `references/build_spain_entsoe_panel.py` | — | 价格/发电/负荷三表对齐 |
| 风电 SCADA（法国） | `references/download_engie_la_haute_borne.py` | — | ENGIE La Haute Borne，经 NREL/OpenOA 镜像（官网已下线） |
| 风电 SCADA（英国） | `references/download_kelmarsh_zenodo.py` | — | Kelmarsh，Zenodo 记录 16807551，6×Senvion MM92，2016–2024 |
| 风电数据体检 | `references/check_windfarm_integrity.py` | — | 按"每 10 分钟一个点"核对行数/时区/缺测 |
| 凭证与连通自检 | `references/test_entsoe_api.py`、`references/test_esios_api.py` | — | 换 token / 换区域前先跑 |

## 使用

```powershell
# 依赖（首次）
pip install requests pandas numpy

# 凭证走环境变量，禁止写进脚本
$env:ENTSOE_TOKEN = "<your-token>"

# 免凭证：欧洲电价与发电构成
python skills/data-fetch-power/references/download_spain_ec_history.py

# ENTSO-E 官方口径对照
python skills/data-fetch-power/references/download_spain_entsoe.py
```

## 产出

| 文件（包根 data/ 下） | 内容 |
|----------------------|------|
| energy_charts/*.json / *.csv | 各国价格与发电构成（免凭证口径） |
| entsoe/price_da.csv、gen_by_type.csv、load.csv | ENTSO-E 官方口径三表 |
| spain/spain_pv_hourly_*.csv、ercot/wind_power_hourly_*.csv | 派生出力序列 |
| gem/*_hubs*.csv | 代表点位与 share 权重 |
| windfarm/la_haute_borne/*.csv | 法国 4 台 Senvion MM82 SCADA（10 分钟）+ 电站数据 + ERA5/MERRA2 再分析 |
| windfarm/kelmarsh/*.zip | 英国 6 台 Senvion MM92 SCADA（10 分钟，2016–2024，逐年 zip）+ 并网点/PMU 数据 |

## 数据源与已知局限

| 数据 | 状态 | 已知限制 |
|------|------|----------|
| ERCOT | ✅ 跑通 | 官网直连被反爬 + 中国 IP 不可达，必须走 GridStatus |
| ENTSO-E Transparency | ✅ 跑通 | 报文有两处隐藏结构，不按引用知识处理会静默丢量 |
| Energy-Charts（Fraunhofer ISE） | ✅ 跑通 | 免凭证首选，可作 ENTSO-E 的校验口径 |
| GEM 电站数据库 | ✅ 跑通 | 月度版本，路径含月份，需按版本拼 |
| ESIOS / REE | ❌ 封锁 | 域名级 WAF 全面 403，token 有效也进不去 → 改用 ENTSO-E |
| ENGIE La Haute Borne | ✅ 跑通 | 官方门户 `opendata-renewables.engie.com` 已下线（NXDOMAIN），只能走 NREL/OpenOA 镜像（2014–2015 快照） |
| Kelmarsh（Zenodo） | ✅ 跑通 | 本机 DNS 把裸域 `zenodo.org` 解析到 0.0.0.0；且 Zenodo 会限并发、链路中途挂死，见失败处理 |

## 失败处理

- ESIOS 返回 403 → **立即停手换源**，不要反复重试或换 UA（属域名级封锁，不是请求头问题）
- ENTSO-E 解析后量级明显偏小 → 按引用知识检查 `curveType` 压缩与合约类型混装
- 电价出现重复时间戳 → 先确认时区口径（tz-naive vs tz-aware），再决定是否去重
- 裸域 `zenodo.org` 解析到 `0.0.0.0`（0 字节/连不上）→ 不要在脚本里换 URL，改用进程内 `socket.getaddrinfo` 别名补丁把裸域指向 `www.zenodo.org` 的 IP（见 `download_kelmarsh_zenodo.py`）
- Zenodo **多进程并发**下载会出现 0 字节 `.part`（被限流）→ 改成单进程串行 + 断点续传
- Zenodo 大文件下到一半**连接挂死**（文件长时间不增长）→ 把 urlopen 读超时压到 45s，靠 `.part` 续传恢复；不要盲目加长超时
- ENGIE 门户打不开 → 属官网下线，直接换 NREL/OpenOA 的 `la_haute_borne.zip` 镜像，不要反复重试
- 风电 SCADA 行数对不上（看上去缺 10%+）→ 先确认原生时间步长（10 分钟 ≠ 每行 1 分钟），别按 1440 行/天算

> 引用知识（kb/）:
> - `[PIT-20260723-001]` ERCOT 官网反爬虫屏蔽与中国 IP 不可访问陷阱
> - `[PIT-20260929-001]` REE/ESIOS 域名级 WAF 封锁
> - `[PIT-20260929-002]` ENTSO-E / IEC 62325 报文的两处隐藏结构
> - `[PIT-20260724-001]` Pandas 时区 tz-naive 与 tz-aware 比较错误
> - `[RCP-20260723-001]` ERCOT 电力市场数据下载流程
> - `[RCP-20260929-005]` 西班牙 ENTSO-E Transparency 数据链路（替代 ESIOS）
> - `[RCP-20261002-001]` 风电场级开源数据集下载流程（La Haute Borne / Kelmarsh）
> - `[PIT-20261002-001]` 裸域被 DNS 屏蔽 + 并发限流 + 链路挂死：Zenodo 批量下载的三重坑
> - `[PIT-20261002-002]` 注释行就是表头：Greenbyte 导出的 CSV 用 `# ` 开头做表头，且字段含逗号
> - `[PIT-20261002-003]` 风电场 SCADA 的时间口径：10 分钟步长、本地时 vs UTC、首年不从 1 月 1 日起
> - `[MTD-20260907-001]` 气象数据 API 凭证安全管理实践
