"""GEM 西班牙光伏电站清单 → 容量加权代表点位 (供 PVGIS 辐照下载)
口径: GEM global solar, country=Spain, status=operating, start-year <= 目标年
      按网格聚合去重, 每格取容量加权质心, 作为 PVGIS 采样点
输出: data/gem/spain_solar_hubs_{year}.csv (name, lat, lon, capacity_mw, n_units)
用法: python scripts/data_download/prep_spain_pv_fleet.py 2023
"""
import sys

import numpy as np
import pandas as pd

GEM = r"c:\work\meteo\data\gem\gem_solar_2026-08.csv"
OUT = r"c:\work\meteo\data\gem\spain_solar_hubs_{year}.csv"


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    g = pd.read_csv(GEM, low_memory=False)
    sp = g[(g["country-area1"] == "Spain") &
           (g["status"].str.lower() == "operating") &
           (g["start-year"] <= year)].copy()
    sp = sp.dropna(subset=["Latitude", "Longitude", "capacity"])
    print(f"西班牙 operating & start-year<={year}: {len(sp)} 座, "
          f"{sp['capacity'].sum()/1000:.2f} GW")

    for grid in (1.0, 0.75, 0.5, 0.35):
        k = (np.round(sp["Latitude"] / grid).astype(int).astype(str) + "_" +
             np.round(sp["Longitude"] / grid).astype(int).astype(str))
        print(f"  grid {grid}° → {k.nunique()} 个网格")

    GRID = 0.5
    sp["gk"] = (np.round(sp["Latitude"] / GRID).astype(int).astype(str) + "_" +
                np.round(sp["Longitude"] / GRID).astype(int).astype(str))
    rows = []
    for gk, sub in sp.groupby("gk"):
        cap = float(sub["capacity"].sum())
        rows.append({"name": sub["name"].iloc[0],
                     "lat": round(float(np.average(sub["Latitude"], weights=sub["capacity"])), 4),
                     "lon": round(float(np.average(sub["Longitude"], weights=sub["capacity"])), 4),
                     "capacity_mw": cap, "n_units": len(sub)})
    df = pd.DataFrame(rows).sort_values("capacity_mw", ascending=False).reset_index(drop=True)
    df.to_csv(OUT.format(year=year), index=False)
    print(f"\n[{year}] {len(df)} 个采样点, 总容量 {df['capacity_mw'].sum()/1000:.2f} GW")
    print(f"  单点容量: P50 {df['capacity_mw'].median():.0f} / max {df['capacity_mw'].max():.0f} MW")
    print(f"  前5: " + ", ".join(f"{r['name'][:22]}({r['capacity_mw']:.0f}MW)"
                                for _, r in df.head(5).iterrows()))
    print(f"→ {OUT.format(year=year)}")


if __name__ == "__main__":
    main()