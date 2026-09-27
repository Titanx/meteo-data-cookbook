"""Open-Meteo Seasonal 45天集合预报下载 (ERCOT 关键站点)
输出: data/openmeteo_seasonal/{站点}_seasonal_45d.json + 聚合CSV
"""
import requests
import pandas as pd
import json
from pathlib import Path

OUT = Path(r"c:\work\meteo\data\openmeteo_seasonal")
OUT.mkdir(parents=True, exist_ok=True)

# ERCOT 关键位置 (风电带 + 负荷中心)
SITES = {
    "LZ_WEST_wind":       (32.4, -102.0),   # 西德州风电带
    "LZ_NORTH_wind":      (33.6, -98.5),    # 北德州风电
    "Dallas_DFW":         (32.895, -97.037),# 达拉斯
    "Houston":            (29.76, -95.37),  # 休斯顿
    "LZ_SOUTH_coast":     (31.0, -97.5),    # 南德州
    "LZ_HOUSTON_solar":   (29.3, -97.0),    # 休斯顿光伏区
}

DAILY = ["wind_speed_10m_mean", "wind_speed_10m_max", "wind_speed_10m_min",
         "precipitation_sum", "temperature_2m_max", "temperature_2m_min",
         "shortwave_radiation_sum", "snowfall_sum"]

records = []
for name, (lat, lon) in SITES.items():
    params = {
        "latitude": lat, "longitude": lon,
        "daily": DAILY,
        "forecast_days": 45, "timezone": "America/Chicago",
    }
    r = requests.get("https://seasonal-api.open-meteo.com/v1/seasonal",
                     params=params, timeout=30)
    if r.status_code != 200:
        print(f"[{name}] 失败 HTTP {r.status_code}: {r.text[:100]}")
        continue
    d = r.json()
    day = d["daily"]
    # 保存原始 JSON (含50成员)
    raw = OUT / f"{name}_seasonal_45d.json"
    raw.write_text(json.dumps(d, indent=1), encoding="utf-8")
    n = len(day["time"])
    rec = {
        "site": name, "lat": lat, "lon": lon,
        "n_days": n, "start": day["time"][0], "end": day["time"][-1],
        "wind_mean_avg": round(day["wind_speed_10m_mean"][0], 2),
        "wind_max_avg": round(day["wind_speed_10m_max"][0], 2),
        "precip_sum": round(sum(day["precipitation_sum"]), 1),
        "precip_days": sum(1 for p in day["precipitation_sum"] if p > 0.1),
        "n_members": len([k for k in day if k.startswith("wind_speed_10m_mean_member")]),
        "raw_file": f"{name}_seasonal_45d.json",
    }
    records.append(rec)
    print(f"[{name}] OK: {n}天 {rec['wind_mean_avg']}~{rec['wind_max_avg']} m/s, "
          f"降水{rec['precip_sum']}mm/{rec['precip_days']}天, 成员{rec['n_members']}")

df = pd.DataFrame(records)
df.to_csv(OUT / "seasonal_45d_summary.csv", index=False)
print(f"\n汇总 → {OUT / 'seasonal_45d_summary.csv'}")
print("原始JSON已保存（含50成员）")

# 打印聚合均值 (集合均值已在文件名_mean中)
print("\n=== 未来45天集合均值摘要 ===")
for _, r in df.iterrows():
    print(f"  {r['site']}: 风速平均 {r['wind_mean_avg']:.1f}~{r['wind_max_avg']:.1f} m/s | "
          f"降水 {r['precip_sum']}mm ({r['precip_days']}天)")