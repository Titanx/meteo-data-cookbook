# -*- coding: utf-8 -*-
"""NCEI Storm Events 完整性核验（下载后必跑）

检查:
  1. 清单登记的文件是否落盘、字节数与登记一致
  2. 每个文件能否 gz 解压 + 解析（行数/列数）
  3. 覆盖矩阵: 产品 × 年份
  4. details 的事件类型分布、ERCOT 相关州计数、时间列样例（校验当地时口径）
  5. 快照日一致性（同一年是否只有一个快照）

用法: python skills/data-fetch-ground/references/check_storm_events_integrity.py
"""
import os
import sys

import pandas as pd

ROOT = r"c:\work\meteo\data\storm_events"
MANIFEST = os.path.join(ROOT, "storm_events_manifest.csv")

ERCOT_STATES = {"TEXAS"}  # Storm Events 用全称
NEIGHBOR = {"OKLAHOMA", "NEW MEXICO", "ARKANSAS", "LOUISIANA"}


def main():
    if not os.path.exists(MANIFEST):
        print(f"清单不存在: {MANIFEST}"); return 1
    mf = pd.read_csv(MANIFEST)
    print("=" * 70)
    print(f"NCEI Storm Events 完整性核验  |  {len(mf)} 条登记")
    print("=" * 70)

    # 1. 落盘与字节
    miss, size_bad = [], []
    for _, r in mf.iterrows():
        p = os.path.join(ROOT, r["product"], r["filename"])
        if not os.path.exists(p):
            miss.append(r["filename"]); continue
        if os.path.getsize(p) != int(r["bytes"]):
            size_bad.append((r["filename"], os.path.getsize(p), int(r["bytes"])))
    print(f"[1] 落盘: {len(mf)-len(miss)}/{len(mf)} 存在"
          f"{'  ✗ 缺 ' + str(len(miss)) + ' 个' if miss else ''}")
    if miss:
        for n in miss[:10]:
            print(f"      缺: {n}")
    print(f"[1] 字节一致: {len(mf)-len(miss)-len(size_bad)}/{len(mf)}"
          f"{'  ✗ ' + str(len(size_bad)) + ' 个不符' if size_bad else ''}")
    for n, got, exp in size_bad[:10]:
        print(f"      不符: {n}  本地 {got} / 登记 {exp}")

    # 2/3. 逐文件解析 + 覆盖矩阵
    rows = []
    for _, r in mf.iterrows():
        p = os.path.join(ROOT, r["product"], r["filename"])
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_csv(p, compression="gzip", low_memory=False)
            rows.append({"product": r["product"], "year": int(r["year"]),
                         "snapshot": str(r["snapshot"]), "n_rows": len(df),
                         "n_cols": df.shape[1], "ok": True})
        except Exception as e:
            rows.append({"product": r["product"], "year": int(r["year"]),
                         "snapshot": str(r["snapshot"]), "n_rows": 0,
                         "n_cols": 0, "ok": False, "err": str(e)[:60]})
    rep = pd.DataFrame(rows)
    bad = rep[~rep["ok"]]
    print(f"[2] 解析成功: {len(rep)-len(bad)}/{len(rep)}"
          f"{'  ✗ ' + str(len(bad)) + ' 个失败' if len(bad) else ''}")
    for _, b in bad.head(10).iterrows():
        print(f"      失败: {b['product']} {b['year']}  {b.get('err','')}")

    print("[3] 覆盖矩阵（行数）:")
    piv = rep.pivot_table(index="year", columns="product", values="n_rows",
                          aggfunc="sum", fill_value=0)
    yrs = rep["year"]
    cols = [c for c in ["details", "fatalities", "locations"] if c in piv.columns]
    print(f"      年份范围 {yrs.min()} ~ {yrs.max()}，共 {len(piv)} 年  |  "
          f"总行数: " + ", ".join(f"{c}={int(piv[c].sum()):,}" for c in cols))
    print("      年份  " + "  ".join(f"{c:>12}" for c in cols))
    for y in piv.index:
        if y % 10 == 0 or y >= yrs.max() - 3:
            print(f"      {int(y)}  " + "  ".join(f"{int(piv.loc[y, c]):>12,}" for c in cols))

    # 4. details 深查（取最近 3 年）
    print("[4] details 抽样核验（最近 3 年）:")
    for y in sorted(rep[rep["product"] == "details"]["year"].unique())[-3:]:
        f = mf[(mf["product"] == "details") & (mf["year"] == y)]["filename"].iloc[0]
        df = pd.read_csv(os.path.join(ROOT, "details", f), compression="gzip", low_memory=False)
        tor = int((df["EVENT_TYPE"] == "Tornado").sum())
        tw = int((df["EVENT_TYPE"] == "Thunderstorm Wind").sum())
        texas = int((df["STATE"] == "TEXAS").sum())
        tx_tor = int(((df["STATE"] == "TEXAS") & (df["EVENT_TYPE"] == "Tornado")).sum())
        print(f"      {y}: {len(df):,} 行 | Tornado {tor:,} | ThunderstormWind {tw:,} | "
              f"TEXAS {texas:,}（其中龙卷 {tx_tor}）")
        if y == max(rep[rep["product"] == "details"]["year"]):
            print(f"        时间列样例: BEGIN_DATE_TIME={df['BEGIN_DATE_TIME'].iloc[0]!r}  "
                  f"CZ_TIMEZONE={df['CZ_TIMEZONE'].iloc[0]!r}  → **当地时，非 UTC**")
            print(f"        事件类型 Top8: " + ", ".join(
                f"{k}({v})" for k, v in df["EVENT_TYPE"].value_counts().head(8).items()))

    # 5. 结构断点（locations 自 1996 起；details 1995→1996 跳变）
    if {"details", "locations"}.issubset(piv.columns):
        loc_years = piv.index[piv["locations"] > 0]
        loc_start = int(loc_years[loc_years >= 1990].min()) if len(loc_years[loc_years >= 1990]) else None
        print(f"[6] 结构断点: locations 实质起始年 = {loc_start}"
              f"（1950–1995 无；{int(piv.loc[1995,'details']) if 1995 in piv.index else '-'}→"
              f"{int(piv.loc[1996,'details']) if 1996 in piv.index else '-'} 行 details 跳变）")

    # 7. 快照一致性
    snaps = mf.groupby(["product", "year"])["snapshot"].nunique()
    multi = snaps[snaps > 1]
    print(f"[7] 快照一致性: {'多快照年份 ' + str(len(multi)) + ' 个（本层目录按当前快照去重，正常）' if len(multi) else '每年单快照 ✓'}")
    print(f"      当前快照日（跨年不同，逐年冻结于各自重发布日）: details "
          f"{sorted(str(int(s)) for s in mf[mf['product']=='details']['snapshot'].unique())}")

    print("-" * 70)
    ok = (len(miss) == 0) and (len(size_bad) == 0) and len(bad) == 0
    print("结论: " + ("✅ 完整" if ok else "⚠ 存在问题，见上"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
