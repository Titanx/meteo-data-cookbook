"""Seasonal 45天预报 vs ERA5实测 vs GFS 10天预报 误差随预报时效(lead time)对比
输出: data/openmeteo_seasonal/verif/
  - {site}_series.json   (每站点 ERA5 / Seasonal / GFS 逐日序列)
  - error_by_lead.csv    (合并6站点, 按 lead 天聚合 MAE/RMSE)
"""
import requests, json, math
import pandas as pd
from pathlib import Path

OUT = Path(r"c:\work\meteo\data\openmeteo_seasonal\verif")
VER = OUT / "series"; VER.mkdir(parents=True, exist_ok=True)

START, END = "2026-08-10", "2026-09-15"

SITES = {
    "LZ_WEST_wind":       (32.4, -102.0),
    "LZ_NORTH_wind":      (33.6, -98.5),
    "Dallas_DFW":         (32.895, -97.037),
    "Houston":            (29.76, -95.37),
    "LZ_SOUTH_coast":     (31.0, -97.5),
    "LZ_HOUSTON_solar":   (29.3, -97.0),
}
DAILY = ["wind_speed_10m_mean", "precipitation_sum"]
SEA = ["https://seasonal-api.open-meteo.com/v1/seasonal", {}]
GFS = ["https://historical-forecast-api.open-meteo.com/v1/forecast", {"models": "ncep_gfs_seamless"}]
ERA = ["https://archive-api.open-meteo.com/v1/archive", {}]


def fetch(host, params):
    r = requests.get(host, params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"{host} {r.status_code}: {r.text[:200]}")
    return r.json()


def get_series(host, p, lat, lon):
    params = {"latitude": lat, "longitude": lon,
              "daily": DAILY, "start_date": START, "end_date": END,
              "timezone": "America/Chicago"}
    params.update(p)
    return fetch(host, params)["daily"]


rows = []          # 合并到误差聚合
site_meta = []
for name, (lat, lon) in SITES.items():
    try:
        sea = get_series(*SEA, lat, lon)
        gfs = get_series(*GFS, lat, lon)
        era = get_series(*ERA, lat, lon)
    except Exception as e:
        print(f"[{name}] FAIL {e}")
        continue
    times = sea["time"]
    rec = {"site": name, "lat": lat, "lon": lon, "time": times}
    n = len(times)
    for lead, t in enumerate(times, start=1):
        sw = sea["wind_speed_10m_mean"][lead-1]
        gw = gfs["wind_speed_10m_mean"][lead-1]
        ew = era["wind_speed_10m_mean"][lead-1]
        sp = sea["precipitation_sum"][lead-1]
        gp = gfs["precipitation_sum"][lead-1]
        ep = era["precipitation_sum"][lead-1]
        rows.append({
            "site": name, "date": t, "lead": lead,
            "sea_wind": sw, "gfs_wind": gw, "era_wind": ew,
            "sea_precip": sp, "gfs_precip": gp, "era_precip": ep,
        })
    rec["wind_era"] = era["wind_speed_10m_mean"]
    rec["wind_sea"] = sea["wind_speed_10m_mean"]
    rec["wind_gfs"] = gfs["wind_speed_10m_mean"]
    rec["precip_era"] = era["precipitation_sum"]
    rec["precip_sea"] = sea["precipitation_sum"]
    rec["precip_gfs"] = gfs["precipitation_sum"]
    (VER / f"{name}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    site_meta.append({"site": name, "n_days": n})
    print(f"[{name}] OK {n}天")

df = pd.DataFrame(rows)


def agg(col_f, col_t):
    """按 lead 聚合 MAE/RMSE(合并6站点采样)"""
    out = []
    for lead, g in df.groupby("lead"):
        f = g[col_f]; t = g[col_t]
        pr = (f - t).dropna()
        if pr.empty:
            continue
        mae = pr.abs().mean()
        rmse = math.sqrt((pr ** 2).mean())
        out.append({"lead": int(lead), "date": g["date"].iloc[0],
                    "n": int(pr.size), "MAE": round(mae, 3), "RMSE": round(rmse, 3)})
    return pd.DataFrame(out)


sea_w = agg("sea_wind", "era_wind").rename(columns={"MAE": "SEA_wind_MAE", "RMSE": "SEA_wind_RMSE"})
gfs_w = agg("gfs_wind", "era_wind").rename(columns={"MAE": "GFS_wind_MAE", "RMSE": "GFS_wind_RMSE"})
sea_p = agg("sea_precip", "era_precip").rename(columns={"MAE": "SEA_precip_MAE", "RMSE": "SEA_precip_RMSE"})
gfs_p = agg("gfs_precip", "era_precip").rename(columns={"MAE": "GFS_precip_MAE", "RMSE": "GFS_precip_RMSE"})

m = sea_w.merge(gfs_w, on=["lead", "date", "n"], how="left")
m = m.merge(sea_p[["lead", "SEA_precip_MAE", "SEA_precip_RMSE"]], on="lead", how="left")
m = m.merge(gfs_p[["lead", "GFS_precip_MAE", "GFS_precip_RMSE"]], on="lead", how="left")
m.to_csv(OUT / "error_by_lead.csv", index=False)

# 简单总览
print("\n=== 风速 MAE (km/h), 按预报时效 ===")
print(m[["lead", "SEA_wind_MAE", "GFS_wind_MAE"]].to_string(index=False))
print("\n=== 降水 MAE (mm) ===")
print(m[["lead", "SEA_precip_MAE", "GFS_precip_MAE"]].to_string(index=False))

print(f"\n保存: {OUT / 'error_by_lead.csv'}")
print(f"站点序列: {VER / '*.json'}")