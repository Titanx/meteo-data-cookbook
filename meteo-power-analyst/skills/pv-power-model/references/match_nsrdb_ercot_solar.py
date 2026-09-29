"""GEM ERCOT 光伏电站 → NSRDB v3.2.2 像素匹配
用途: 2022 年已建成 ERCOT 光伏电站 (>=10MW) 匹配 NSRDB 最近像素, 生成提取索引
输入: data/gem/gem_solar_2026-08.csv, data/nsrdb/nsrdb_v322_ercot_pixels.npz
输出: data/nsrdb/ercot_solar_plants_pixels.csv
"""
import numpy as np
import pandas as pd

GEM_CSV = r"c:\work\meteo\data\gem\gem_solar_2026-08.csv"
PIX_NPZ = r"c:\work\meteo\data\nsrdb\nsrdb_v322_ercot_pixels.npz"
OUT_CSV = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels.csv"

# NSRDB v3.2.2 像素间距 ~0.02-0.03 度, 3 km 内视为同一位置
MAX_DIST_DEG = 0.05


def main():
    d = np.load(PIX_NPZ)
    pix_idx, pix_lat, pix_lon = d["index"], d["latitude"], d["longitude"]
    print(f"NSRDB ERCOT 像素: {len(pix_idx)}")

    g = pd.read_csv(GEM_CSV, low_memory=False)
    B = {"lat_min": 25, "lat_max": 34, "lon_min": -108, "lon_max": -93}
    m = ((g["Latitude"] >= B["lat_min"]) & (g["Latitude"] <= B["lat_max"]) &
         (g["Longitude"] >= B["lon_min"]) & (g["Longitude"] <= B["lon_max"]))
    op = g[m & (g["status"].str.lower() == "operating")].copy()
    v22 = op[(op["start-year"] <= 2022) &
             op["Latitude"].between(26, 34) & op["Longitude"].between(-107, -94) &
             ~op["subnational"].isin(["Chihuahua", "Coahuila"]) &
             (op["capacity"] >= 10)].copy()  # >=10MW, 小电站对验证无贡献
    print(f"2022 年已建成 ERCOT 光伏 (>=10MW): {len(v22)} 座, "
          f"{v22['capacity'].sum()/1000:.1f} GW")

    # 像素排序后用 searchsorted 做最近邻 (网格近规则, 逐站暴力搜索也仅 330k*153, 但排序二分更快)
    order = np.lexsort((pix_lon, pix_lat))
    slat, slon, sidx = pix_lat[order], pix_lon[order], pix_idx[order]

    rows = []
    for _, p in v22.iterrows():
        la, lo = p["Latitude"], p["Longitude"]
        # lat 窗口内找 lon 最近: 两步 searchsorted
        i0 = np.searchsorted(slat, la - MAX_DIST_DEG)
        i1 = np.searchsorted(slat, la + MAX_DIST_DEG)
        if i0 == i1:
            rows.append((p["name"], la, lo, p["capacity"], -1, np.nan, np.nan))
            continue
        d2 = (slat[i0:i1] - la) ** 2 + (slon[i0:i1] - lo) ** 2
        j = i0 + int(d2.argmin())
        dist_deg = float(np.sqrt(d2.min()))
        rows.append((p["name"], la, lo, p["capacity"], int(sidx[j]),
                     float(slat[j]), dist_deg))

    df = pd.DataFrame(rows, columns=["name", "lat", "lon", "capacity_mw",
                                     "nsrdb_index", "nsrdb_lat", "dist_deg"])
    ok = df[df["nsrdb_index"] >= 0]
    far = df[df["nsrdb_index"] < 0]
    print(f"匹配成功: {len(ok)} 座 ({ok['capacity_mw'].sum()/1000:.1f} GW), "
          f"匹配失败: {len(far)} 座")
    if len(ok):
        print(f"匹配距离(deg): max {ok['dist_deg'].max():.4f}, "
              f"中位 {ok['dist_deg'].median():.4f} (~{ok['dist_deg'].median()*111:.1f} km)")
    df.to_csv(OUT_CSV, index=False)
    print(f"已保存: {OUT_CSV}")
    print(f"nsrdb_index 范围: {ok['nsrdb_index'].min()} ~ {ok['nsrdb_index'].max()}")
    s = np.sort(ok["nsrdb_index"].values)
    runs = 1 + int((np.diff(s) > 8).sum())
    print(f"排序后索引合并为 ~{runs} 个连续段 (gap>8 切分)")


if __name__ == "__main__":
    main()
