# -*- coding: utf-8 -*-
"""风电场数据完整性核验：La Haute Borne + Kelmarsh。

核对项：
  1. 行数是否符合"机组数 × 时段 × 每天 144 条（原生 **10 分钟** 步长）"的理论值
     —— 注意别按"每分钟一条 / 1440 行一天"算，否则完整度会被算成 ≈36%
  2. 时间戳时区口径（本地时 vs UTC）——两个数据集口径不同，是常见对齐陷阱
     （La Haute Borne：SCADA 是本地时含 DST `+01:00`/`+02:00`，而 plant_data 是 UTC）
  3. 缺测率（La Haute Borne 空值计 NaN；Kelmarsh 由 Greenbyte 显式写 NaN）
  4. Kelmarsh：Greenbyte CSV 的表头是**最后一行以 `# ` 开头的行**，且字段带引号含逗号，
     必须用 csv.reader 解析（`split(",")` 会把 299 列切成 464）
"""
from __future__ import annotations

import csv
import io
import os
import sys
import zipfile
from collections import defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LHB = r"c:\work\meteo\data\windfarm\la_haute_borne"
KEL = r"c:\work\meteo\data\windfarm\kelmarsh"
DAY = 144  # 原生步长 10 分钟


def lhb_scada() -> None:
    p = os.path.join(LHB, "la-haute-borne-data-2014-2015.csv")
    print("=== La Haute Borne — 机组级 SCADA ===")
    per_t = defaultdict(lambda: defaultdict(int))
    na = defaultdict(int)
    tot = 0
    tz = set()
    with open(p, encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            tot += 1
            t = row["Wind_turbine_name"]
            per_t[t][row["Date_time"][:4]] += 1
            tz.add(row["Date_time"][-6:])
            if row["P_avg"] in ("", "NaN"):
                na[t] += 1
    print(f"  总行数 {tot:,}；时区后缀 {sorted(tz)}")
    print(f"  机组数 {len(per_t)}")
    for t in sorted(per_t):
        y14, y15 = per_t[t].get("2014", 0), per_t[t].get("2015", 0)
        exp = 365 * DAY
        print(f"    {t}: 2014={y14:,}/{exp:,}({y14/exp*100:.1f}%) "
              f"2015={y15:,}/{exp:,}({y15/exp*100:.1f}%)  P 缺测={na[t]}")


def lhb_plant() -> None:
    p = os.path.join(LHB, "plant_data.csv")
    print("\n=== La Haute Borne — 场站级 plant_data ===")
    n = 0
    yrs = defaultdict(int)
    with open(p, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            n += 1
            yrs[row["time_utc"][:4]] += 1
    print(f"  行数 {n:,}；时区口径 UTC（time_utc）")
    for y in sorted(yrs):
        print(f"    {y}: {yrs[y]:,} 行（理论 {365*144 if y!='2016' else 366*144:,}）")


def lhb_reanalysis() -> None:
    print("\n=== La Haute Borne — 同址再分析 ===")
    for fn, col in (("era5_wind_la_haute_borne.csv", "datetime"),
                    ("merra2_la_haute_borne.csv", "datetime")):
        p = os.path.join(LHB, fn)
        n, first, last = 0, None, None
        with open(p, encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                if first is None:
                    first = row[col]
                last = row[col]
                n += 1
        print(f"  {fn}: {n:,} 行  {first} → {last}")


def kelmarsh() -> None:
    D = KEL
    print("=== Kelmarsh — 已落盘文件 ===")
    for fn in sorted(os.listdir(D)):
        print(f"  {fn:44s} {os.path.getsize(os.path.join(D, fn))/1e6:9.2f} MB")


def kelmarsh_scada() -> None:
    """逐年解析 SCADA zip：行数 / 步长 / 首末时间 / 逐列非空率分布。"""
    D = KEL
    zips = sorted(f for f in os.listdir(D)
                  if f.startswith("Kelmarsh_SCADA_") and f.endswith(".zip"))
    print(f"\n=== Kelmarsh — SCADA 逐年体检（{len(zips)} 个年包）===")
    if not zips:
        print("  （暂无完整年包，等待下载完成）")
        return
    for z in zips:
        with zipfile.ZipFile(os.path.join(D, z)) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with zf.open(name) as raw:
                tw = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
                header, n, first, last, prev = None, 0, None, None, None
                steps: dict[int, int] = defaultdict(int)
                nonnull = None
                comments: list[str] = []
                for line in tw:
                    s = line.rstrip("\r\n")
                    if not s:
                        continue
                    # Greenbyte：开头是若干注释行，**表头本身也在注释块内**（最后一行），
                    # 且注释行不保证都是 "# "（有的写成 "#," 的分组行）
                    if s.startswith("#"):
                        comments.append(s)
                        continue
                    if header is None:
                        row = next(csv.reader([s]))
                        # 注释块里挑"字段数与数据行相同"的**最后一行**当表头
                        best = comments[-1]
                        for c in reversed(comments):
                            if len(next(csv.reader([c]))) == len(row):
                                best = c
                                break
                        header = next(csv.reader([best]))
                        if header and header[0].startswith("#"):
                            header[0] = header[0].lstrip("#").strip()
                        nonnull = [0] * len(header)
                    else:
                        row = next(csv.reader([s]))
                    n += 1
                    t = row[0]
                    if first is None:
                        first = t
                    for i, v in enumerate(row):
                        if i == 0:            # 第 0 列是时间戳，不计入信号非空率
                            continue
                        if i < len(nonnull) and v not in ("", "NaN"):
                            nonnull[i] += 1
                    if prev is not None:
                        d = (datetime.fromisoformat(t.strip())
                             - datetime.fromisoformat(prev.strip())).total_seconds()
                        steps[int(d)] += 1
                    prev = t
                    last = t
        ncol = len(header) if header else 0
        sig = sum(1 for c in (nonnull or []) if ncol and c >= n * 0.999)
        lo = sum(1 for c in (nonnull or []) if ncol and 0 < c < n * 0.1)
        mid = sum(1 for c in (nonnull or []) if ncol and n * 0.1 <= c < n * 0.5)
        hi = sum(1 for c in (nonnull or []) if ncol and n * 0.5 <= c < n * 0.999)
        empty = sum(1 for c in (nonnull or []) if c == 0)
        top = sorted(steps.items(), key=lambda kv: -kv[1])[:2]
        print(f"\n  {z}")
        print(f"    行数 {n:,}  列数 {ncol}（含时间戳列）")
        print(f"    {first} → {last}")
        print(f"    步长分布 {top}")
        print(f"    列非空分布: 近乎无缺 {sig} / <10% {lo} / 10-50% {mid} "
              f"/ 50-99.9% {hi} / 全空 {empty}")


def kelmarsh_static() -> None:
    D = KEL
    for fn in ("Kelmarsh_WT_static.csv", "Kelmarsh_WT_dataSignalMapping.csv"):
        p = os.path.join(D, fn)
        if not os.path.exists(p):
            continue
        print(f"\n=== Kelmarsh — {fn} ===")
        with open(p, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i > 8:
                    print("    …")
                    break
                print("    " + line.rstrip())


if __name__ == "__main__":
    lhb_scada()
    lhb_plant()
    lhb_reanalysis()
    kelmarsh()
    kelmarsh_static()
    if "--scada" in sys.argv:
        kelmarsh_scada()
