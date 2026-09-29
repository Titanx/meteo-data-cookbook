# 数据获取 · 卫星与遥感

**状态**: 🟡 部分可用 — Himawari / GOES / GK2A / GLM 跑通；FY-4 LMI 与 GPM IMERG 受凭证与入口限制，
部分通道未验证（见下表）。

**用途**: 拉取静止卫星多通道辐射、闪电（GLM / LMI）与地形水体数据，落盘供雷暴、辐照与地形联动分析。

**入口检查**:
1. 先查 `data/` 下是否已有目标产品的分片或解析结果（himawari/、goes19/、gk2a/、glm/、aster/、imerg/）
2. 无 → 按下方选源；**凡需登录的一律先确认凭证可用**

## 选源

| 目标 | 脚本 | 凭证 | 状态 |
|------|------|------|------|
| 亚太静止卫星多通道 | `references/himawari9_segment_pipeline.py`、`references/test_himawari.py`、`references/test_himawari_s3.py` | 无 | ✅ |
| 美国静止卫星（ABI 辐射） | `references/goes19_pipeline.py` | 无 | ✅ |
| 美国闪电（GLM L2） | `references/download_glm_l2.py`、`references/parse_glm.py` | 无 | ✅ |
| 韩日静止卫星（GK2A AMI） | `references/download_gk2a.py` | 需 key | ✅ |
| 中国闪电（FY-4A LMI） | `references/download_fy4_lmi.py`、`references/download_fy4_lmi_ftp.py`、`references/parse_fy4_lmi.py` | 需注册 | 🟡 入口受限 |
| 降水（GPM IMERG） | `references/test_imerg_download.py`、`references/debug_imerg_search.py` | 需 Earthdata 登录 | 🟡 检索接口有坑 |
| 地形与水体系 | `references/download_aster_gdem.py` | 需 Earthdata 登录 | ✅ |
| 平台可达性探活 | `references/test_cma_api.py` | 视入口 | 🟡 |

## 使用

```powershell
# 依赖（首次）
pip install requests pandas numpy xarray netCDF4
# 可选：satpy（通道解析）

# 免凭证：Himawari 分片
python skills/data-fetch-satellite/references/himawari9_segment_pipeline.py

# 需登录的源：凭证走环境变量
$env:EARTHDATA_TOKEN = "<your-token>"
python skills/data-fetch-satellite/references/download_aster_gdem.py
```

## 产出

| 文件（包根 data/ 下） | 内容 |
|----------------------|------|
| himawari/、goes19/scan_*/、gk2a/ir105/ | 原始分片（按通道/时间目录） |
| glm/l2/、fy4/lmi/ | 闪电事件点（解析后 csv/nc） |
| aster/gdem/、aster/wbd/ | 地形高程 / 水体边界 |

## 数据源与已知局限

| 数据 | 状态 | 已知限制 |
|------|------|----------|
| Himawari-8/9 | ✅ | 目录按通道+日期分片，命名规则必须按流程拼，错一位就 404 |
| GOES-16/18/19 | ✅ | 公开桶可匿名读，目录层级深 |
| GK2A | ✅ | 需 key；有限流 |
| FY-4A LMI | 🟡 | 部分入口不可达（内网要求 / API 受限 / 镜像不支持该产品） |
| GPM IMERG | 🟡 | 检索接口参数隐晦，需先探活再批量 |
| ASTER GDEM / WBD | ✅ | 分幅下载后需拼接，注意图幅编号 |

## 失败处理

- 卫星桶返回 403 → 先跑 `skills/data-fetch-radar/references/test_radar_all_anonymous.py` 同族的匿名访问探活，区分"桶策略变更"与"本机网络问题"
- 分片列目录为空 → 先确认时间戳与通道目录名两处，再怀疑网络
- 需登录的源拿不到凭证 → **不要绕**，在报告里显式标注该产品缺失，改用免凭证替代（如 ERA5 再分析代替卫星辐照）

> 引用知识（kb/）:
> - `[MTD-20260812-001]` 气象雷达数据匿名获取综合指南
> - `[PIT-20260907-001]` CMA 气象数据访问陷阱（内网 / API 受限 / 不支持该产品）
> - `[RCP-20260718-001]` 葵花8/9 卫星数据下载流程
> - `[RCP-20260720-001]` GOES-16/18/19 卫星数据下载流程
> - `[RCP-20260911-001]` GK2A (GEO-KOMPSAT-2A) AMI 卫星数据下载流程
> - `[RCP-20260907-002]` GOES GLM 闪电数据下载流程
> - `[RCP-20260907-003]` FY-4A LMI 闪电数据下载流程
> - `[RCP-20260907-001]` GPM IMERG 降水数据下载流程
> - `[RCP-20260907-004]` ASTER GDEM 地形与水体数据下载流程
