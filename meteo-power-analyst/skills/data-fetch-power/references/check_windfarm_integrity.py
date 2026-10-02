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
from itertools import chain

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
    """逐年解析 SCADA zip：行数 / 首末时间 / 原生步长 / 逐列非空率分布。

    性能：整个文件只用**一个** csv.reader 流式解析（逐行新建 reader 会慢一个量级）；
    原生步长只取前两行之差，避免对每一行做 datetime 解析。
    写盘中间结果到 _kelmarsh_scada.tsv，供生成 README 表格。
    """
    D = KEL
    zips = sorted(f for f in os.listdir(D)
                  if f.startswith("Kelmarsh_SCADA_") and f.endswith(".zip"))
    print(f"\n=== Kelmarsh — SCADA 逐年体检（{len(zips)} 个年包）===")
    if not zips:
        print("  （暂无完整年包，等待下载完成）")
        return
    rows_out = []
    for z in zips:
        year = z.split("_")[2]
        with zipfile.ZipFile(os.path.join(D, z)) as zf:
            csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            # 2016–2022：一个年包 = 一个宽表 CSV；
            # 2023–2024：一个年包 = 6 台机 × (Turbine_Data + Status)，取第 1 台的 Turbine_Data
            name = next((n for n in csvs if "Turbine_Data" in n), csvs[0])
            with zf.open(name) as raw:
                tw = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
                comments: list[str] = []
                first_data = None
                for line in tw:
                    if line.startswith("#"):
                        comments.append(line.rstrip("\r\n"))
                        continue
                    first_data = line
                    break
                if first_data is None or not comments:
                    print(f"  {z}: 结构异常（无注释/无数据），跳过")
                    continue
                reader = csv.reader(chain([first_data], tw))
                row0 = next(reader)
                # 注释块里挑"字段数与数据行相同"的**最后一行**当表头
                best = comments[-1]
                for c in reversed(comments):
                    if len(next(csv.reader([c]))) == len(row0):
                        best = c
                        break
                header = next(csv.reader([best]))
                if header and header[0].startswith("#"):
                    header[0] = header[0].lstrip("#").strip()
                ncol = len(header)
                nonnull = [0] * ncol
                n = 0
                first = last = prev = None
                step = None
                blocks = 1
                # 2023/2024 的 Turbine_Data 是"累积快照堆叠"：文件里有多块，
                # 每块都从 1 月 1 日起、长度递增。遇到时间戳回跳就**清零重来**，
                # 这样最终统计的正好是最后（最完整）那一块。
                for row in chain([row0], reader):
                    if not row or not row[0]:
                        continue
                    t = row[0]
                    if prev is not None and t < prev:
                        blocks += 1
                        n = 0
                        nonnull = [0] * ncol
                        first = prev = None
                        step = None
                    if first is None:
                        first = t
                    elif step is None:
                        step = (datetime.fromisoformat(t.strip())
                                - datetime.fromisoformat(first.strip())).total_seconds()
                    for i in range(1, min(len(row), ncol)):
                        v = row[i]
                        if v and v != "NaN":
                            nonnull[i] += 1
                    last = t
                    prev = t
                    n += 1
        sig = sum(1 for c in nonnull if c >= n * 0.999)
        part = sum(1 for c in nonnull if 0 < c < n * 0.999)
        empty = sum(1 for c in nonnull if c == 0)
        span_days = (datetime.fromisoformat(last.strip())
                     - datetime.fromisoformat(first.strip())).total_seconds() / 86400
        exp = round(span_days * DAY) + 1          # 时间跨度内的理论行数（含首行）
        pct = n / exp * 100
        rows_out.append((year, n, ncol, int(step), sig, part, empty,
                         first, last, round(pct, 2), blocks, len(csvs)))
        print(f"  {year}: 行数 {n:,}  列数 {ncol}  步长 {int(step)}s  "
              f"近乎无缺 {sig} / 部分缺 {part} / 全空 {empty}  "
              f"（{first} → {last}，里程 {pct:.1f}%，块数 {blocks}，CSV {len(csvs)} 个）",
              flush=True)

    out = os.path.join(KEL, "kelmarsh_scada_体检.tsv")
    with open(out, "w", encoding="utf-8") as f:
        f.write("year\trows\tcols\tstep\tfull\tpart\tempty\tfirst\tlast\tpct\t"
                "blocks\tcsvs\n")
        for r in rows_out:
            f.write("\t".join(str(x) for x in r) + "\n")
    print(f"  （明细已写入 {out}）")


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
