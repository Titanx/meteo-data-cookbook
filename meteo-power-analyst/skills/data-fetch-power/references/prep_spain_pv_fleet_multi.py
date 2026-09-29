"""GEM 西班牙光伏电站清单 → 容量加权代表点位 (多年份, 供 PVGIS/NASA POWER 下载)
口径: GEM global solar, country=Spain, status=operating; 按网格聚合去重
     输出同一组点位在 2023/2024/2025 三个年份的装机容量 (start-year <= 年)
     便于"同一位置跨年对比", 避免各年点位不同导致的口径漂移
输出: data/gem/spain_solar_hubs_multi.csv
用法: python skills/data-fetch-power/references/prep_spain_pv_fleet.py [nhub]
"""
import sys

import numpy as np
import pandas as pd

GEM = r"c:\work\meteo\data\gem\gem_solar_2026-08.csv"
OUT = r"c:\work\meteo\data\gem\spain_solar_hubs_multi.csv"
YEARS = [2023, 2024, 2025]
GRID = 0.5


def main():
    nhub = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    g = pd.read_csv(GEM, low_memory=False)
    sp = g[(g["country-area1"] == "Spain") &
           (g["status"].str.lower() == "operating")].copy()
    sp = sp.dropna(subset=["Latitude", "Longitude", "capacity"])
    print(f"西班牙 operating 全部: {len(sp)} 座, {sp['capacity'].sum()/1000:.2f} GW")
    for y in YEARS:
        v = sp[sp["start-year"] <= y]
        print(f"  start-year<={y}: {len(v)} 座, {v['capacity'].sum()/1000:.2f} GW")

    sp["gk"] = (np.round(sp["Latitude"] / GRID).astype(int).astype(str) + "_" +
                np.round(sp["Longitude"] / GRID).astype(int).astype(str))
    ref = sp[sp["start-year"] <= max(YEARS)]
    top = ref.groupby("gk")["capacity"].sum().sort_values(ascending=False).head(nhub).index
    print(f"\n0.5° 网格 {ref['gk'].nunique()} 个 → 取容量前 {nhub} 个")

    rows = []
    for gk in top:
        sub = sp[sp["gk"] == gk]
        cap_ref = sub["capacity"].sum()
        rec = {"name": sub["name"].iloc[0],
               "lat": round(float(np.average(sub["Latitude"], weights=sub["capacity"])), 4),
               "lon": round(float(np.average(sub["Longitude"], weights=sub["capacity"])), 4),
               "n_units": len(sub)}
        for y in YEARS:
            rec[f"cap_{y}"] = float(sub[sub["start-year"] <= y]["capacity"].sum())
        rows.append(rec)
    df = pd.DataFrame(rows).sort_values(f"cap_{max(YEARS)}", ascending=False).reset_index(drop=True)
    df.to_csv(OUT, index=False)
    tot_all = {y: sp[sp["start-year"] <= y]["capacity"].sum() for y in YEARS}
    print(f"\n{len(df)} 个采样点:")
    for y in YEARS:
        cov = df[f"cap_{y}"].sum() / tot_all[y]
        print(f"  {y}: 采样点合计 {df[f'cap_{y}'].sum()/1000:.2f} GW / 全清单 "
              f"{tot_all[y]/1000:.2f} GW = 覆盖率 {cov*100:.1f}%")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()