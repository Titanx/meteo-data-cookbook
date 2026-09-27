# 新数据源调研：MRMS / NSRDB / WMO S2S（2026-09-27）

> 三源均为此前未调研的数据，目标是增强 ERCOT 天气-电力分析链路的三个薄弱环节：
> 高精度降水核验、光伏辐照基准、延伸期预报稳健性检验。

## 一句话结论

| 数据源 | 成熟度 | 核心价值 | 状态 |
|--------|--------|----------|------|
| **MRMS QPE** | verified | 1 km 逐小时雷达融合降水，比 IMERG 精一个量级，极端天气核验基准 | 实测通过，可直接投产 |
| **NSRDB v3.2.2** | verified | 5 min / 2 km GHI/DNI/DHI，光伏建模标准数据；ERCOT 像素索引已建成 | 全链路打通（含像素定位） |
| **WMO S2S 库** | draft | 13 中心多年回算，把 PS-017 单窗口精度核验升级为统计检验 | 门户可达，待注册实测 |

## MRMS（多雷达多传感器定量降水）— PS-018

- **通道**：AWS S3 `noaa-mrms-pds` 匿名归档（2020-10-14 ~ 2023-07-10，恰好 1000 天，须 continuation-token 翻页）+ NCEP 官网滚动 ~10 天（滞后 ~1 天）；两通道间有历史空档
- **产品**：`MultiSensor_QPE_01H_Pass2`（再处理最优版）
- **坑**：GRIB2 经度是 **0-360 约定**（ERCOT = 253.3~266.6），负经度匹配得到 0 格点；cfgrib 中参数名显示 unknown，取第一个 data_vars
- **实测**：ERCOT 裁剪 1070×1330 格点；2023-07-10 21Z 捕捉 33.3 mm/h 对流核心（8377 格点 >1 mm），09Z 全域无雨，日变化合理
- **与现有链路衔接**：替代/补充 IMERG（PS-010）做雷暴-电价联动（PS-007）的降水实测端

## NSRDB（国家太阳辐射数据库）— PS-019

- **难点**：单年文件 1.5~2.4 TB，必须懒读取；`developer.nrel.gov` 在当前网络 DNS 不通，S3 匿名（`nrel-pds-nsrdb`）是唯一路径
- **懒读取**：h5coro（HTTPDriver + `credentials=None` + 128 KB 缓存行——默认 4 MB 跨境必超时；不支持 compound meta 和属性）
- **重大发现**：v3.2.2 名为 "CONUS" 实为 **GOES-East+West 全视域**（lat 14.5~49.4 含墨西哥、lon -160~-60 含夏威夷~波多黎各），像素 0 位于夏威夷海域——任何区域提取必须先过 meta 空间过滤
- **像素定位（当场解决）**：meta 为 compound（h5coro 读不了），改用 h5py 取磁盘偏移（连续存储 offset=2636192）→ requests Range 流式下载 346.8 MB → numpy 本地解析 → **ERCOT 330,096 像素**（德州 163,017），索引已缓存 `data/nsrdb/nsrdb_v322_ercot_pixels.npz`
- **端到端验证**：奥斯汀像素 (30.38N, -97.89W) 1月1日峰值 410 W/m²、7月1日 995 W/m² @ 12:15 LST——时刻与量级和天文完全自洽，确认值即 W/m²、time_index 为 UTC
- **与现有链路衔接**：接 pvlib 出力链路（PS-006/GEM 光伏电站 474 座坐标映射），替代 NASA POWER 同化值做光伏建模基准

## WMO S2S 数据库（多中心延伸期回算）— PS-020

- **动机**：PS-017 的 Open-Meteo 核验是单窗口（EC46 历史成员仅保留一个月，lead 1~5 缺测），无法做多初始化统计
- **内容**：13 个 NWP/研究中心（ECMWF/NOAA/CMA/JMA/KMA/ECCC 等）34~65 天集合回算，实时存档 2015 起、回算多从 1981/1996 起，分 fixed 与 on-the-fly 两类
- **访问**：2026-04-21 起迁移至 **ECDS**（`ecds.ecmwf.int`，CDS-API 风格 + OGC processes 端点）；门户与 API catalog 实测 HTTP 200，中国网络直连可达；**需注册 ECMWF 账号**（免费）
- **下一步**：注册后拉 ECMWF（与 EC46 同源）+ NCEP（与 GFS 同源）回算，按 ERCOT 6 站 ≥20 个初始化日期做逐 lead 统计，附集合离散度置信带

## 知识库同步

- 新增 PS-018 / PS-019（verified）、PS-020（draft）
- 更新 tech/catalog.md、根 catalog.md（29 → 32 条）、log.md、project/catalog.md
- 新增脚本：`test_mrms_download.py`、`test_nsrdb_h5coro.py`、`test_nsrdb_meta.py`、`test_nsrdb_mrms_s2s.py`
- 新增数据：`data/mrms/`（ERCOT 裁剪样例）、`data/nsrdb/`（meta 全缓存 + 像素索引 npz）

## 待办

1. **NSRDB ERCOT 辐照批量提取**（中）：按像素索引用 h5coro 拉子时段 GHI/DNI/DHI → pvlib 出力 → 与 ERCOT 光伏节点电价联动
2. **WMO S2S 注册与回算获取**（中）：注册 ECDS，实测 API 拉取，升级 PS-017 核验
3. MRMS 历史回补按需批量下载（归档窗口内任意日期均可达）
