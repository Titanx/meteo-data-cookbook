import pandas as pd, numpy as np, json
from pathlib import Path

OUT = Path(r"c:\work\meteo\data\openmeteo_seasonal\verif")
m = pd.read_csv(OUT / "error_by_lead.csv")

def seg(df, lo, hi, col):
    s = df[(df["lead"] >= lo) & (df["lead"] <= hi)][col].dropna()
    return s

# 各模型有效段
sea_w = seg(m, 6, 37, "SEA_wind_MAE")
gfs_w = seg(m, 1, 10, "GFS_wind_MAE")
sea_p = seg(m, 6, 37, "SEA_precip_MAE")
gfs_p = seg(m, 1, 10, "GFS_precip_MAE")

meta = {
  "window": "2026-08-10 ~ 2026-09-15",
  "n_sites": 6, "n_days": 37,
  "sea_wind_MAE": round(float(sea_w.mean()), 2),
  "gfs_wind_MAE": round(float(gfs_w.mean()), 2),
  "sea_precip_MAE": round(float(sea_p.mean()), 2),
  "gfs_precip_MAE": round(float(gfs_p.mean()), 2),
  "sea_wind_RMSE": round(float(seg(m,6,37,"SEA_wind_RMSE").mean()), 2),
  "gfs_wind_RMSE": round(float(seg(m,1,10,"GFS_wind_RMSE").mean()), 2),
  "sea_precip_RMSE": round(float(seg(m,6,37,"SEA_precip_RMSE").mean()), 2),
  "gfs_precip_RMSE": round(float(seg(m,1,10,"GFS_precip_RMSE").mean()), 2),
}
# 重叠区 6-10 直接对比
ovl_w = m[(m.lead>=6)&(m.lead<=10)]
meta["ovl_w_sea"] = round(float(ovl_w["SEA_wind_MAE"].mean()),2)
meta["ovl_w_gfs"] = round(float(ovl_w["GFS_wind_MAE"].mean()),2)
meta["wind_ratio"] = round(meta["sea_wind_MAE"]/meta["gfs_wind_MAE"],2)

print(json.dumps(meta, ensure_ascii=False, indent=1))

# 导出为 js 数值数组(原始 + 滚动平均), 供 charts.js 直用
arr = m[["lead","SEA_wind_MAE","GFS_wind_MAE","SEA_precip_MAE","GFS_precip_MAE"]].fillna("null").to_dict("records")
(OUT / "chart_arrays.json").write_text(json.dumps(arr, ensure_ascii=False), encoding="utf-8")
print("\nchart_arrays.json rows:", len(arr))