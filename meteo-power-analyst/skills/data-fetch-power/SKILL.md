# 数据获取 · 电力市场

**状态**: ✅ 可用 — ERCOT（GridStatus 通道）、ENTSO-E Transparency、Energy-Charts、GEM 电站库均跑通；
ESIOS / REE 官方接口被域名级 WAF 封锁，已改用 ENTSO-E 替代口径。

**用途**: 拉取电价、负荷、发电构成、机组名录与装机，落盘为可对齐的日/小时面板，供出力与缺口链路使用。

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

## 数据源与已知局限

| 数据 | 状态 | 已知限制 |
|------|------|----------|
| ERCOT | ✅ 跑通 | 官网直连被反爬 + 中国 IP 不可达，必须走 GridStatus |
| ENTSO-E Transparency | ✅ 跑通 | 报文有两处隐藏结构，不按引用知识处理会静默丢量 |
| Energy-Charts（Fraunhofer ISE） | ✅ 跑通 | 免凭证首选，可作 ENTSO-E 的校验口径 |
| GEM 电站数据库 | ✅ 跑通 | 月度版本，路径含月份，需按版本拼 |
| ESIOS / REE | ❌ 封锁 | 域名级 WAF 全面 403，token 有效也进不去 → 改用 ENTSO-E |

## 失败处理

- ESIOS 返回 403 → **立即停手换源**，不要反复重试或换 UA（属域名级封锁，不是请求头问题）
- ENTSO-E 解析后量级明显偏小 → 按引用知识检查 `curveType` 压缩与合约类型混装
- 电价出现重复时间戳 → 先确认时区口径（tz-naive vs tz-aware），再决定是否去重

> 引用知识（kb/）:
> - `[PIT-20260723-001]` ERCOT 官网反爬虫屏蔽与中国 IP 不可访问陷阱
> - `[PIT-20260929-001]` REE/ESIOS 域名级 WAF 封锁
> - `[PIT-20260929-002]` ENTSO-E / IEC 62325 报文的两处隐藏结构
> - `[PIT-20260724-001]` Pandas 时区 tz-naive 与 tz-aware 比较错误
> - `[RCP-20260723-001]` ERCOT 电力市场数据下载流程
> - `[RCP-20260929-005]` 西班牙 ENTSO-E Transparency 数据链路（替代 ESIOS）
> - `[MTD-20260907-001]` 气象数据 API 凭证安全管理实践
