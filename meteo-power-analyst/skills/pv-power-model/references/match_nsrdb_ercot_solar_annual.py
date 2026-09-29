"""GEM ERCOT 光伏电站 → NSRDB 像素匹配 (按年清单, 供多年份缺口标定)
用途: 生成指定年份"已建成"的 ERCOT 光伏电站清单 (与 PS-021 同口径: >=100MW)
      供 2025/2026 物理晴空反事实使用
输入: data/gem/gem_solar_2026-08.csv, data/nsrdb/nsrdb_v322_ercot_pixels.npz
输出: data/nsrdb/ercot_solar_plants_pixels_{year}.csv
用法: python scripts/data_download/match_nsrdb_ercot_solar_annual.py 2025 2026
"""
import sys

import numpy as np
import pandas as pd

GEM_CSV = r"c:\work\meteo\data\gem\gem_solar_2026-08.csv"
PIX_NPZ = r"c:\work\meteo\data\nsrdb\nsrdb_v322_ercot_pixels.npz"
OUT_TMPL = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels_{year}.csv"
MAX_DIST_DEG = 0.05
MIN_CAP = 100.0          # 与 PS-021 一致 (>=100MW)


def main():
    years = [int(a) for a in sys.argv[1:]] or [2025, 2026]

    d = np.load(PIX_NPZ)
    pix_idx, pix_lat, pix_lon = d["index"], d["latitude"], d["longitude"]
    order = np.lexsort((pix_lon, pix_lat))
    slat, slon, sidx = pix_lat[order], pix_lon[order], pix_idx[order]
    print(f"NSRDB ERCOT 像素: {len(pix_idx)}")

    g = pd.read_csv(GEM_CSV, low_memory=False)
    base = (g["Latitude"].between(26, 34) & g["Longitude"].between(-107, -94) &
            (g["status"].str.lower() == "operating") &
            ~g["subnational"].isin(["Chihuahua", "Coahuila"]) &
            (g["capacity"] >= MIN_CAP))

    for year in years:
        v = g[base & (g["start-year"] <= year)].copy()
        rows = []
        for _, p in v.iterrows():
            la, lo = p["Latitude"], p["Longitude"]
            i0 = np.searchsorted(slat, la - MAX_DIST_DEG)
            i1 = np.searchsorted(slat, la + MAX_DIST_DEG)
            if i0 == i1:
                rows.append((p["name"], la, lo, p["capacity"], -1, np.nan, np.nan))
                continue
            d2 = (slat[i0:i1] - la) ** 2 + (slon[i0:i1] - lo) ** 2
            j = i0 + int(d2.argmin())
            rows.append((p["name"], la, lo, p["capacity"], int(sidx[j]),
                         float(slat[j]), float(np.sqrt(d2.min()))))
        df = pd.DataFrame(rows, columns=["name", "lat", "lon", "capacity_mw",
                                         "nsrdb_index", "nsrdb_lat", "dist_deg"])
        ok = df[df["nsrdb_index"] >= 0].sort_values("nsrdb_index") \
            .reset_index(drop=True)
        out = OUT_TMPL.format(year=year)
        ok.to_csv(out, index=False)
        print(f"[{year}] {len(v)} 座满足条件 → 匹配成功 {len(ok)} 座 "
              f"({ok['capacity_mw'].sum()/1000:.2f} GW), "
              f"中位距离 {ok['dist_deg'].median()*111:.1f} km → {out}")


if __name__ == "__main__":
    main()
