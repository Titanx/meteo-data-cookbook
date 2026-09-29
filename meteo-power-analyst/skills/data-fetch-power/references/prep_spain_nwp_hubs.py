# -*- coding: utf-8 -*-
"""GEM 西班牙光伏电站清单 → 容量加权代表点位 (供 Open-Meteo NWP 下载) —— PS-044

口径: GEM global solar, country-area1 = Spain, status = operating, start-year <= 目标年
      按 1° 网格聚合, 每格取容量加权质心; 取容量最大的前 N 个点(控制请求数), 并报告容量覆盖率
      ⚠ 与 PS-030 的 0.5° / 212 点口径**不同**: 本流程只需要"全国辐照指数", 1°/24 点足够,
        且把请求数从 (212×5=1060) 压到 (24×5=120)。

输出: data/gem/spain_solar_hubs_nwp.csv (hub_id, name, lat, lon, capacity_mw, n_units, share)
用法: python scripts/data_download/prep_spain_nwp_hubs.py 2024 24
"""
import sys

import numpy as np
import pandas as pd

GEM = r"c:\work\meteo\data\gem\gem_solar_2026-08.csv"
OUT = r"c:\work\meteo\data\gem\spain_solar_hubs_nwp.csv"
TOPN = int(sys.argv[2]) if len(sys.argv) > 2 else 24


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    g = pd.read_csv(GEM, low_memory=False)
    sp = g[(g["country-area1"].astype(str).str.strip() == "Spain") &
           (g["status"].astype(str).str.lower() == "operating") &
           (g["start-year"] <= year)].copy()
    sp = sp.dropna(subset=["Latitude", "Longitude", "capacity"])
    tot = float(sp["capacity"].sum()) / 1000
    print("西班牙 operating & start-year<=%d: %d 座, %.2f GW" % (year, len(sp), tot))

    GRID = 1.0
    sp["gk"] = (np.round(sp["Latitude"] / GRID).astype(int).astype(str) + "_" +
                np.round(sp["Longitude"] / GRID).astype(int).astype(str))
    rows = []
    for _, sub in sp.groupby("gk"):
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
    df.to_csv(OUT)
    print("\n" + df.to_string())
    print("\n→ %s" % OUT)


if __name__ == "__main__":
    main()
