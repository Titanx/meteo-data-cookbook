"""GonshoreWT2024 全球陆上风机点位 shapefile 字段级体检。

用途：下载 Zenodo doi:10.5281/zenodo.18984175 的 GonshoreWT2024.zip 解压后，
对 .shp/.shx/.dbf 做一致性核对：三处点数、几何类型与 Z/M、经纬度范围、
重复坐标、Nation/landtype 计数、可选 bbox 内点数。
纯标准库实现（不依赖 geopandas/pyshp）。

用法：
    python skills/data-fetch-power/references/inspect_gonshorewt2024.py \
        --base <解压目录>/GonshoreWT2024 \
        [--bbox -106.6 -93.5 25.5 36.5]

详见 kb/recipes/RCP-20261127-001。
"""
import argparse
import math
import struct
from collections import Counter, defaultdict


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True,
                   help="shapefile 路径前缀（不含 .shp/.dbf/.shx 扩展名）")
    p.add_argument("--bbox", nargs=4, type=float, metavar=("LON_MIN", "LON_MAX", "LAT_MIN", "LAT_MAX"),
                   default=None, help="可选：统计该经纬度框内的点数（注意不是真实边界）")
    return p.parse_args()


def read_points(path_shp):
    with open(path_shp, "rb") as f:
        h = f.read(100)
        magic = struct.unpack(">i", h[0:4])[0]
        if magic != 9994:
            raise SystemExit("不是 shapefile（magic=%d）" % magic)
        shptype = struct.unpack("<i", h[32:36])[0]
        bbox = struct.unpack("<4d", h[36:68])
        pts = []
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            clen = struct.unpack(">i", hdr[4:8])[0]
            body = f.read(clen * 2)
            st = struct.unpack("<i", body[0:4])[0]
            if st == 1:  # Point
                x, y = struct.unpack("<2d", body[4:20])
                z = m = None
            elif st == 11:  # PointZ: X, Y, Z, M
                x, y, z, m = struct.unpack("<4d", body[4:36])
            else:
                raise SystemExit("不支持的 shape type %d（本流程只处理 Point/PointZ）" % st)
            pts.append((x, y, z, m))
    return shptype, bbox, pts


def read_dbf(path_dbf):
    with open(path_dbf, "rb") as f:
        d = f.read()
    nrec = struct.unpack("<I", d[4:8])[0]
    hlen, rlen = struct.unpack("<HH", d[8:12])
    fields = []
    i = 32
    while d[i] != 13:
        fd = d[i:i + 32]
        fields.append((fd[:11].decode("ascii").rstrip("\x00"), chr(fd[11]), fd[16]))
        i += 32
    recs = []
    for k in range(nrec):
        rec = d[hlen + k * rlen: hlen + (k + 1) * rlen]
        off = 1  # 跳过删除标记字节
        row = {}
        for name, _typ, width in fields:
            row[name] = rec[off:off + width].decode("utf-8", "replace").strip()
            off += width
        recs.append(row)
    return nrec, fields, recs


def main():
    args = parse_args()
    shptype, bbox, pts = read_points(args.base + ".shp")
    print("shape_type", shptype, "(1=Point, 11=PointZ)")
    print("SHP 头 bbox", tuple(round(v, 4) for v in bbox))

    with open(args.base + ".shx", "rb") as f:
        shx = f.read()
    shx_count = (len(shx) - 100) // 8
    print("SHX 记录数", shx_count, "/ SHP 实际点数", len(pts))

    zs = [p[2] for p in pts if p[2] is not None]
    ms = [p[3] for p in pts if p[3] is not None]
    if zs:
        print("Z 唯一值数", len(set(zs)), "min", min(zs), "max", max(zs))
        print("M 唯一值数", len(set(ms)), "min", min(ms), "max", max(ms))

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    print("经度范围 %.4f ~ %.4f / 纬度范围 %.4f ~ %.4f" % (min(xs), max(xs), min(ys), max(ys)))
    bad = sum(1 for x, y, _, _ in pts if not (-180 <= x <= 180 and -90 <= y <= 90))
    print("越界经纬度", bad)

    exact = Counter((p[0], p[1]) for p in pts)
    dup_exact = sum(c - 1 for c in exact.values() if c > 1)
    dup_4 = sum(c - 1 for c in Counter((round(p[0], 4), round(p[1], 4)) for p in pts).values() if c > 1)
    print("完全同坐标重复行 %d（占 %.2f%%）/ 按 1e-4 度(约11m)重复行 %d"
          % (dup_exact, 100.0 * dup_exact / len(pts), dup_4))

    nrec, fields, recs = read_dbf(args.base + ".dbf")
    print("DBF 记录数", nrec, "字段", fields)
    if nrec != len(pts):
        print("!! DBF 与 SHP 记录数不一致")
    for col in ("Nation", "landtype"):
        if col in {f[0] for f in fields}:
            cnt = Counter(r[col] for r in recs)
            print("TOP %s" % col, cnt.most_common(10))

    if args.bbox:
        lon0, lon1, lat0, lat1 = args.bbox
        box = [(p, r) for p, r in zip(pts, recs) if lon0 <= p[0] <= lon1 and lat0 <= p[1] <= lat1]
        print("bbox %s 内点数 %d" % (args.bbox, len(box)))
        print("bbox 内国家分布", Counter(r["Nation"] for _, r in box).most_common(8))


if __name__ == "__main__":
    main()
