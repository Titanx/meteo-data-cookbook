# NASA POWER 全部参数清单

> 通过官方 API 端点 `https://power.larc.nasa.gov/api/system/manager/parameters` 查询
> 查询时间: 2026-07-21

## 总览

三个社区 AG（农业）/RE（可再生能源）/SB（可持续建筑）参数数**完全一致**：

| 时间分辨率 | 参数数 | 说明 |
|-----------|--------|------|
| HOURLY | 105 | 小时尺度核心参数，最常用 |
| DAILY | 152 | 日尺度，含 max/min/range 等统计量 |
| MONTHLY | 1388 | 月尺度，含大量太阳能工程衍生参数 |
| CLIMATOLOGY | 1634 | 气候态统计（2001-2020），最多 |
| **不重复总计** | **1660** | — |

## HOURLY 核心 105 参数分类

### 1. 温度 (6 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| T2M | °C | 2 米气温（干球） |
| T10M | °C | 10 米气温 |
| T2MDEW | °C | 2 米露点/霜点温度 |
| T2MWET | °C | 2 米湿球温度 |
| TS | °C | 地表皮肤温度 |
| TS_ADJ | °C | 地表温度（校正版） |

### 2. 湿度与水汽 (5 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| RH2M | % | 2 米相对湿度 |
| QV2M | g/kg | 2 米比湿 |
| QV10M | g/kg | 10 米比湿 |
| DISPH | m | 零平面位移高度 |
| RHOA | kg/m³ | 地面空气密度 |

### 3. 气压 (3 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| PS | kPa | 地面气压 |
| PSC | kPa | 校正气压（按高度调整） |
| SLP | kPa | 海平面气压 |

### 4. 风 (13 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| WS2M / WS10M / WS50M | m/s | 2/10/50 米风速 |
| WD2M / WD10M / WD50M | Degrees | 2/10/50 米风向 |
| U2M / U10M / U50M | m/s | 2/10/50 米东向风分量 |
| V2M / V10M / V50M | m/s | 2/10/50 米北向风分量 |
| WSC | m/s | 校正风速（按高度调整） |

### 5. 降水与蒸发 (9 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| PRECTOT | mm/hour | 总降水（小时速率） |
| PRECTOTCORR | mm/day | 校正降水 |
| PRECSNO | mm/day | 雪态降水 |
| PRECSNOLAND | mm/day | 陆面雪态降水 |
| EVLAND | mm/day | 陆面蒸发 |
| EVPTRNS | W/m² | 蒸散能量通量 |
| GWETPROF | 1 | 剖面土壤湿度 |
| GWETROOT | 1 | 根区土壤湿度 |
| GWETTOP | 1 | 表层土壤湿度 |

### 6. 辐射-全天空 AllSky (13 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| ALLSKY_SFC_SW_DWN | W/m² | **全天空短波下行辐照（GHI）** |
| ALLSKY_SFC_SW_DNI | W/m² | 全天空法向直接辐照（DNI） |
| ALLSKY_SFC_SW_DIFF | W/m² | 全天空散射辐照（DHI） |
| ALLSKY_SFC_SW_DIRH | W/m² | 全天空水平直接辐照 |
| ALLSKY_SFC_SW_UP | W/m² | 全天空短波上行辐照 |
| ALLSKY_SFC_LW_DWN | W/m² | 全天空长波下行辐照 |
| ALLSKY_SFC_LW_UP | W/m² | 全天空长波上行辐照 |
| ALLSKY_SFC_PAR_TOT | W/m² | 全天空光合有效辐射总量 |
| ALLSKY_SFC_PAR_DIFF | W/m² | 全天空散射 PAR |
| ALLSKY_SFC_PAR_DIRH | W/m² | 全天空水平直接 PAR |
| ALLSKY_SFC_UVA | W/m² | UVA 辐照 |
| ALLSKY_SFC_UVB | W/m² | UVB 辐照 |
| ALLSKY_SFC_UV_INDEX | W/m²×40 | UV 指数 |

### 7. 辐射-晴空 ClearSky (10 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| CLRSKY_SFC_SW_DWN | W/m² | 晴空短波下行辐照 |
| CLRSKY_SFC_SW_DNI | W/m² | 晴空法向直接辐照 |
| CLRSKY_SFC_SW_DIFF | W/m² | 晴空散射辐照 |
| CLRSKY_SFC_SW_DIRH | W/m² | 晴空水平直接辐照 |
| CLRSKY_SFC_SW_UP | W/m² | 晴空短波上行辐照 |
| CLRSKY_SFC_LW_DWN | W/m² | 晴空长波下行辐照 |
| CLRSKY_SFC_LW_UP | W/m² | 晴空长波上行辐照 |
| CLRSKY_SFC_PAR_TOT | W/m² | 晴空 PAR 总量 |
| CLRSKY_SFC_PAR_DIFF | W/m² | 晴空散射 PAR |
| CLRSKY_SFC_PAR_DIRH | W/m² | 晴空水平直接 PAR |

### 8. 辐射-其他 (12 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| TOA_SW_DWN | W/m² | 大气顶短波下行辐照 |
| TOA_SW_DNI | W/m² | 大气顶法向直接辐照 |
| LWLAND | W/m² | 陆面长波下行通量 |
| SWLAND | W/m² | 陆面短波下行通量 |
| ALLSKY_KT | 1 | 全天空晴空指数 |
| ALLSKY_NKT | 1 | 全天空归一化晴空指数 |
| CLRSKY_KT | 1 | 晴空晴空指数 |
| CLRSKY_NKT | 1 | 晴空归一化晴空指数 |
| ALLSKY_SRF_ALB | 1 | 全天空反照率 |
| CLRSKY_SRF_ALB | 1 | 晴空反照率 |
| SRF_ALB_ADJ | 1 | 校正反照率 |
| AIRMASS | 1 | 气团 |

### 9. 云 (5 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| CLOUD_AMT | % | 云量 |
| CLOUD_BT | °C | 云底温度 |
| CLOUD_TT | °C | 云顶温度 |
| CLOUD_OD | 1 | 云光学厚度 |
| CLOUD_PHASE | 1 | 云相态 |

### 10. 气溶胶 (3 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| AOD_55 | 1 | 550 nm 气溶胶光学厚度 |
| AOD_55_ADJ | 1 | 校正气溶胶光学厚度 550 nm |
| AOD_84 | 1 | 840 nm 气溶胶光学厚度 |

### 11. 太阳几何 (1 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| SZA | Degrees | 太阳天顶角 |

### 12. 冰雪 (2 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| FRSEAICE | 1 | 海冰覆盖比例 |
| FRSNO | 1 | 陆面积雪覆盖比例 |

### 13. 其他 (23 个)

| 参数名 | 单位 | 说明 |
|--------|------|------|
| TSOIL1 ~ TSOIL6 | °C | 土壤温度（6 层） |
| SFMC | m³/m³ | 表层土壤水分 |
| RZMC | m³/m³ | 根区土壤水分 |
| PRMC | m³/m³ | 剖面土壤水分 |
| SFMC_PRCNTL / RZMC_PRCNTL / PRMC_PRCNTL | % | 土壤水分百分位 |
| SNODP | cm | 雪深 |
| PW | cm | 可降水量 |
| TQV | kg/m² | 柱可降水总量 |
| TO3 | Dobsons | 臭氧柱总量 |
| TROPPB | kPa | 对流层顶气压 |
| TROPQ | g/kg | 对流层顶比湿 |
| TROPT | °C | 对流层顶温度 |
| PBLTOP | kPa | 行星边界层顶气压 |
| TSURF | °C | 陆面/雪面温度 |
| Z0M | m | 地面粗糙度 |
| ORIGINAL_ALLSKY_SFC_SW_DIFF | W/m² | 原始全天空散射（未校正） |
| ORIGINAL_ALLSKY_SFC_SW_DIRH | W/m² | 原始全天空水平直接（未校正） |

## DAILY 额外 48 参数

### 统计量（max/min/range）

- T2M_MAX / T2M_MIN / T2M_RANGE
- T10M_MAX / T10M_MIN / T10M_RANGE
- TS_MAX / TS_MIN / TS_RANGE
- WS2M_MAX / WS_MIN / WS_RANGE（2/10/50m）
- CLOUD_BT_MAX/MIN, CLOUD_TT_MAX/MIN

### 度日（建筑/能源）

- HDD0 / HDD10 / HDD18_3（采暖度日）
- CDD0 / CDD10 / CDD18_3（制冷度日）

### 生长度日（农业）

- GDD4_4 / GDD7_2 / GDD10 / GDD13_3 / GDD15_6

### 天数统计

- CLRSKY_DAYS（晴空天数）
- FROST_DAYS（霜冻天数）

### 其他

- CLOUD_AMT_DAY / CLOUD_AMT_NIGHT（白天/夜间云量）
- MIDDAY_INSOL（正午辐照）
- IMERG_PRECTOT / IMERG_PRECTOT_COUNT / IMERG_PRECLIQUID_PROB（GPM IMERG 降水产品）
- GWM_HEIGHT / GWM_HEIGHT_ANOMALY（地下水水位）

## MONTHLY / CLIMATOLOGY 特点

MONTHLY（1388 个）和 CLIMATOLOGY（1634 个）参数数量庞大，主要因为：

1. **太阳能工程衍生参数**：SI_TILTED_AVG/MAX/MIN × {HORIZONTAL, LATITUDE, LAT_MINUS15, LAT_PLUS15, OPTIMAL, VERTICAL} + SI_TRACKER × {DUAL, HSATEW, HSATNS, PSAT, VSAT}，组合爆炸
2. **逐小时太阳几何**：SG_SZA_00 ~ SG_SZA_23、SG_SAA_00 ~ SG_SAA_23（24 小时逐时值）
3. **连续无太阳天数统计**：EQUIV_NO_SUN_CONSEC_01/03/07/14/21/MONTH（1/3/7/14/21 天/月窗口）
4. **太阳能盈余/赤字**：SURPLUS_INSOL_CONSEC_*, SOLAR_DEFICITS_CONSEC_*, MAX_SOLAR_DEFICIT 等

## 数据源说明

| 参数类型 | 主要数据源 |
|---------|-----------|
| 辐射（ALLSKY/CLRSKY） | CERES SYN1deg（卫星反演，延迟 3-4 月） |
| 气象（温/湿/压/风） | MERRA-2 / GEOS-IT（再分析，延迟 2 天） |
| 降水 | GPM IMERG（卫星反演） |
| 气溶胶 | MERRA-2 + MISR |
| 土壤/地表 | MERRA-2 |

## 常用查询示例

```python
import requests

# 查询 RE 社区 HOURLY 所有可用参数
url = ("https://power.larc.nasa.gov/api/system/manager/parameters?"
       "user=nasapower4r&community=RE&temporal=HOURLY&metadata=true")
resp = requests.get(url, timeout=60)
params = resp.json()  # dict: {param_name: {name, units, definition, ...}}

# 查询单个参数详情
url = ("https://power.larc.nasa.gov/api/system/manager/parameters/T2M?"
       "user=nasapower4r")
```
