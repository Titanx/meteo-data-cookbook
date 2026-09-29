"""Open-Meteo Seasonal 45天集合预报下载 (西班牙光伏区)
输出: data/openmeteo_seasonal_spain/{站点}_seasonal_45d.json + 汇总 CSV
用法: python scripts/data_download/download_spain_seasonal.py
"""
import json
from pathlib import Path

import pandas as pd
import requests

OUT = Path(r"c:\work\meteo\data\openmeteo_seasonal_spain")
OUT.mkdir(parents=True, exist_ok=True)

SITES = {
    "Andalucia_Sevilla":         (37.40, -5.60),
    "Andalucia_Cordoba":         (37.90, -4.60),
    "Extremadura_Badajoz":       (38.85, -6.40),
    "Extremadura_Caceres":       (39.50, -6.30),
    "CastillaLaMancha_CReal":    (38.95, -3.90),
    "CastillaLaMancha_Toledo":   (39.90, -3.05),
    "Murcia":                    (37.90, -1.40),
    "Aragon_Zaragoza":           (41.55, -1.00),
    "CastillaLeon_Valladolid":   (41.50, -4.90),
}
DAILY = ["shortwave_radiation_sum", "temperature_2m_max", "temperature_2m_min",
         "precipitation_sum"]
records = []

for name, (lat, lon) in SITES.items():
    r = requests.get("https://seasonal-api.open-meteo.com/v1/seasonal",
                     params={"latitude": lat, "longitude": lon, "daily": DAILY,
                             "forecast_days": 45, "timezone": "Europe/Madrid"},
                     timeout=60)
    if r.status_code != 200:
        print(f"[{name}] 失败 HTTP {r.status_code}: {r.text[:120]}")
        continue
    d = r.json()
    (OUT / f"{name}_seasonal_45d.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
    day = d["daily"]
    nm = len([k for k in day if k.startswith("shortwave_radiation_sum_member")])
    sw = day.get("shortwave_radiation_sum")
    records.append({"site": name, "lat": lat, "lon": lon, "n_days": len(day["time"]),
                    "start": day["time"][0], "end": day["time"][-1], "n_members": nm,
                    "sw_mean": round(sum(sw) / len(sw), 1)})
    print(f"[{name}] OK: {len(day['time'])}天 {day['time'][0]}~{day['time'][-1]}, "
          f"成员 {nm}, 日短波均值 {records[-1]['sw_mean']} MJ/m2")

pd.DataFrame(records).to_csv(OUT / "seasonal_45d_summary.csv", index=False)
print(f"\n→ {OUT}")
