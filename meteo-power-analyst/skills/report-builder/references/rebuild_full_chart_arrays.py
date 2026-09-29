import json, math
from pathlib import Path

VER = Path(r"c:\work\meteo\data\openmeteo_seasonal\verif")
series_dir = VER / "series"

# 从各站 chii序列汇总 lead 1-37 的 GFS/SEA/ERA, 池化6站计算 MAE
wind = {}   # lead -> list[era, sea, gfs] (pooled)
precip = {}
for f in series_dir.glob("*.json"):
    d = json.loads(f.read_text(encoding="utf-8"))
    for i, t in enumerate(d["time"], start=1):
        e = d["wind_era"][i-1]; s = d["wind_sea"][i-1]; g = d["wind_gfs"][i-1]
        wind.setdefault(i, []).append((e, s, g))
        ep = d["precip_era"][i-1]; sp = d["precip_sea"][i-1]; gp = d["precip_gfs"][i-1]
        precip.setdefault(i, []).append((ep, sp, gp))

def mae(pairs, s_idx):
    vals = [abs(p[s_idx] - p[0]) for p in pairs if p[s_idx] is not None and p[0] is not None]
    return round(sum(vals)/len(vals), 3) if vals else None

rows = []
for lead in range(1, 38):
    rows.append({
        "lead": lead,
        "SEA_wind_MAE": mae(wind[lead], 1),
        "GFS_wind_MAE": mae(wind[lead], 2),
        "SEA_precip_MAE": mae(precip[lead], 1),
        "GFS_precip_MAE": mae(precip[lead], 2),
    })
(VER / "chart_arrays_full.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
print(json.dumps([r["lead"] for r in rows]))
print("GFS wind lead1-5:", [r["GFS_wind_MAE"] for r in rows[:5]])
print("GFS precip lead1-5:", [r["GFS_precip_MAE"] for r in rows[:5]])