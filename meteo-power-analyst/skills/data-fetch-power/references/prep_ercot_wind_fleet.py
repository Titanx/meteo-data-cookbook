"""GEM ERCOT 风电场清单构建 (按年, 供风功率物理链路)
用途: 从 GEM wind 数据提取 ERCOT 区域已建成风电场, 按坐标去重聚合成机组点位,
      供 HRRR 80m 风速下载与风功率潜力计算
口径: 与 PS-021 光伏一致 —— bbox (lat 26~34, lon -107~-94) + status=operating
      + 排除墨西哥州; 风机容量不设下限 (风电单体可 <100MW)
输出: data/gem/ercot_wind_plants_{year}.csv (name, lat, lon, capacity_mw, n_units)
用法: python scripts/data_download/prep_ercot_wind_fleet.py 2025 2026
"""
import sys

import numpy as np
import pandas as pd

GEM = r"c:\work\meteo\data\gem\gem_wind_2026-08.csv"
OUT = r"c:\work\meteo\data\gem\ercot_wind_plants_{year}.csv"
MEX = ["Chihuahua", "Coahuila", "Nuevo León", "Tamaulipas", "Sonora"]
GRID = 0.10          # ~11 km 聚合, 合并同址机组


def main():
    years = [int(a) for a in sys.argv[1:]] or [2025, 2026]
    g = pd.read_csv(GEM, low_memory=False)
    base = (g["Latitude"].between(26, 34) & g["Longitude"].between(-107, -94) &
            (g["status"].str.lower() == "operating") &
            ~g["subnational"].isin(MEX))
    print(f"GEM wind 全库 {len(g)}, ERCOT bbox+operating {base.sum()} 机组, "
          f"{g.loc[base,'capacity'].sum()/1000:.1f} GW")

    for year in years:
        v = g[base & (g["start-year"] <= year)].copy()
        # 按 0.1° 网格去重聚合
        v["gk"] = (np.round(v["Latitude"] / GRID).astype(int).astype(str) + "_" +
                   np.round(v["Longitude"] / GRID).astype(int).astype(str))
        rows = []
        for k, sub in v.groupby("gk"):
            cap = sub["capacity"].sum()
            wla = np.average(sub["Latitude"], weights=sub["capacity"])
            wlo = np.average(sub["Longitude"], weights=sub["capacity"])
            rows.append({"name": sub["name"].iloc[0], "lat": round(wla, 4),
                         "lon": round(wlo, 4), "capacity_mw": float(cap),
                         "n_units": len(sub)})
        df = pd.DataFrame(rows).sort_values("capacity_mw", ascending=False) \
            .reset_index(drop=True)
        out = OUT.format(year=year)
        df.to_csv(out, index=False)
        print(f"[{year}] {len(v)} 机组 → {len(df)} 个点位 "
              f"({df['capacity_mw'].sum()/1000:.2f} GW, 去重前 {v['capacity'].sum()/1000:.2f} GW)"
              f" → {out}")
        print(f"      容量分位: P50 {df['capacity_mw'].median():.0f} "
              f"P90 {df['capacity_mw'].quantile(.9):.0f} max {df['capacity_mw'].max():.0f} MW")


if __name__ == "__main__":
    main()