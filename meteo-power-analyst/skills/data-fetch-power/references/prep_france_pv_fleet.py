# -*- coding: utf-8 -*-
"""GEM 法国光伏电站清单 → 容量加权代表点位 (供 Open-Meteo NWP 下载) —— PS-043

口径: GEM global solar, country-area1 = France, status = operating, start-year <= 目标年
      按 1° 网格聚合, 每格取容量加权质心; 取容量最大的前 N 个点(控制请求数), 并报告容量覆盖率
输出: data/gem/france_solar_hubs_{year}.csv (name, lat, lon, capacity_mw, n_units, share)
用法: python skills/data-fetch-power/references/prep_france_pv_fleet.py 2024
"""
import sys

import numpy as np
import pandas as pd

GEM = r"c:\work\meteo\data\gem\gem_solar_2026-08.csv"
OUT = r"c:\work\meteo\data\gem\france_solar_hubs_{year}.csv"
TOPN = int(sys.argv[2]) if len(sys.argv) > 2 else 20


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    g = pd.read_csv(GEM, low_memory=False)
    fr = g[(g["country-area1"].astype(str).str.strip() == "France") &
           (g["status"].astype(str).str.lower() == "operating") &
           (g["start-year"] <= year)].copy()
    fr = fr.dropna(subset=["Latitude", "Longitude", "capacity"])
    tot = float(fr["capacity"].sum()) / 1000
    print("法国 operating & start-year<=%d: %d 座, %.2f GW" % (year, len(fr), tot))

    GRID = 1.0
    fr["gk"] = (np.round(fr["Latitude"] / GRID).astype(int).astype(str) + "_" +
                np.round(fr["Longitude"] / GRID).astype(int).astype(str))
    rows = []
    for _, sub in fr.groupby("gk"):
        rows.append({"name": sub["name"].iloc[0],
                     "lat": round(float(np.average(sub["Latitude"], weights=sub["capacity"])), 4),
                     "lon": round(float(np.average(sub["Longitude"], weights=sub["capacity"])), 4),
                     "capacity_mw": float(sub["capacity"].sum()), "n_units": len(sub)})
    df = pd.DataFrame(rows).sort_values("capacity_mw", ascending=False).reset_index(drop=True)
    print("1° 网格 → %d 个点" % len(df))

    if len(df) > TOPN:
        keep = df.head(TOPN).copy()
        print("取容量前 %d 个点: 覆盖 %.1f%% 装机 (%.2f / %.2f GW)"
              % (TOPN, 100 * keep["capacity_mw"].sum() / df["capacity_mw"].sum(),
                 keep["capacity_mw"].sum() / 1000, df["capacity_mw"].sum() / 1000))
        df = keep
    df["share"] = (df["capacity_mw"] / df["capacity_mw"].sum()).round(5)
    df = df.reset_index(drop=True)
    df.index.name = "hub_id"
    df.to_csv(OUT.format(year=year))
    print("\n" + df.to_string())
    print("\n→ %s" % OUT.format(year=year))


if __name__ == "__main__":
    main()
