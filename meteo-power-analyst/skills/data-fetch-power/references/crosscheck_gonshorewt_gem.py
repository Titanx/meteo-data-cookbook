"""GEM 电站清单 × GonshoreWT2024 风机点位 空间交叉核验。

用途：对 GEM ERCOT 风电场清单（场站级，含容量）逐场找最近的 GonshoreWT2024
风机点位，输出最近距离的分位数与各阈值命中率，用于坐标级交叉核验。
注意：两套数据可能共享 OSM 类上游，高一致率只能算交叉一致性，不是独立验证。

纯标准库实现（0.05 度桶索引 + 平面近似距离，对场站级近邻搜索足够）。

用法：
    python skills/data-fetch-power/references/crosscheck_gonshorewt_gem.py \
        --base <解压目录>/GonshoreWT2024 \
        --gem data/gem/ercot_wind_plants_2026.csv

详见 kb/recipes/RCP-20261127-001。
"""
import argparse
import csv
import math
import struct
from collections import defaultdict

KM_PER_DEG_LAT = 110.574


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True, help="GonshoreWT2024 shapefile 路径前缀（不含扩展名）")
    p.add_argument("--gem", required=True, help="GEM 风电场清单 CSV（列：name/lat/lon/capacity_mw）")
    p.add_argument("--thresholds", nargs="*", type=float, default=[0.3, 1.0, 2.0, 5.0],
                   help="命中率阈值（km），默认 0.3 1 2 5")
    return p.parse_args()


def load_points(path_shp):
    buckets = defaultdict(list)
    with open(path_shp, "rb") as f:
        f.read(100)
        n = 0
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            clen = struct.unpack(">i", hdr[4:8])[0]
            body = f.read(clen * 2)
            st = struct.unpack("<i", body[0:4])[0]
            if st == 1:
                x, y = struct.unpack("<2d", body[4:20])
            elif st == 11:
                x, y = struct.unpack("<2d", body[4:20])
            else:
                raise SystemExit("不支持的 shape type %d" % st)
            buckets[(int(math.floor(y / 0.05)), int(math.floor(x / 0.05)))].append((x, y))
            n += 1
    return n, buckets


def nearest_km(lon, lat, buckets, radius_km=5.0):
    bi = int(math.floor(lat / 0.05))
    bj = int(math.floor(lon / 0.05))
    span = max(1, int(radius_km / 5.0) + 1)
    best = float("inf")
    coslat = math.cos(math.radians(lat))
    for i in range(bi - span, bi + span + 1):
        for j in range(bj - span, bj + span + 1):
            for x, y in buckets.get((i, j), ()):
                dx = (x - lon) * 111.32 * coslat
                dy = (y - lat) * KM_PER_DEG_LAT
                d = math.hypot(dx, dy)
                if d < best:
                    best = d
    return best


def main():
    args = parse_args()
    n, buckets = load_points(args.base + ".shp")
    print("GWT 点数", n)

    with open(args.gem, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    cap = sum(float(r["capacity_mw"]) for r in rows if r.get("capacity_mw"))
    print("GEM 场站数 %d，容量合计 %.1f MW" % (len(rows), cap))

    dists = []
    misses = []
    for r in rows:
        lon, lat = float(r["lon"]), float(r["lat"])
        d = nearest_km(lon, lat, buckets)
        dists.append(d)
        if d > max(args.thresholds):
            misses.append((r["name"], round(d, 1)))
    dists.sort()

    def pct(q):
        return dists[min(len(dists) - 1, int(len(dists) * q))]

    print("最近距离 中位 %.2f km / p90 %.2f km / max %.2f km" % (pct(0.5), pct(0.9), dists[-1]))
    for t in args.thresholds:
        c = sum(1 for d in dists if d <= t)
        print("  <= %.1f km: %d / %d（%.1f%%）" % (t, c, len(rows), 100.0 * c / len(rows)))
    if misses:
        print("超出最大阈值的场站：", misses)


if __name__ == "__main__":
    main()
