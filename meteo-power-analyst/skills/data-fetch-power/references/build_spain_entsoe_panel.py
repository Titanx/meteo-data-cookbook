# -*- coding: utf-8 -*-
"""ENTSO-E 原始三表 → 西班牙官方小时面板 + 与 Energy-Charts 口径对齐诊断 (PS-037)

链路: data/entsoe/{gen_by_type,load,price_da}.csv (15min, UTC)
      → 逐时均值 (光伏 B16 / 风电 B18+B19 / 负荷 / 日前价)
      → data/spain/spain_entsoe_hourly.csv (e_solar, e_wind, e_load, e_price)
      并与 data/spain/spain_regime_hourly_{年}.csv (PS-031 Energy-Charts 口径) 对齐诊断

用法: python skills/data-fetch-power/references/build_spain_entsoe_panel.py
"""
import os

import numpy as np
import pandas as pd

D_E = r"c:\work\meteo\data\entsoe"
D_S = r"c:\work\meteo\data\spain"
OUT = os.path.join(D_S, "spain_entsoe_hourly.csv")


def main():
    print("读取 ENTSO-E ...")
    g = pd.read_csv(os.path.join(D_E, "gen_by_type.csv"))
    l = pd.read_csv(os.path.join(D_E, "load.csv"))
    p = pd.read_csv(os.path.join(D_E, "price_da.csv"))
    for d in (g, l, p):
        d["t"] = pd.to_datetime(d["datetime_utc"], utc=True)
        d.drop(columns=["datetime_utc"], inplace=True)

    # 15min → 小时均值（UTC）
    solar = g[g["psr_type"] == "B16"].set_index("t")["gen_mw"].resample("h").mean()
    wind = g[g["psr_type"].isin(["B18", "B19"])].groupby("t")["gen_mw"].sum().resample("h").mean()
    loadh = l.set_index("t")["load_mw"].resample("h").mean()
    priceh = p.set_index("t")["price_eur_mwh"].resample("h").mean()

    E = pd.concat([solar.rename("e_solar"), wind.rename("e_wind"), loadh.rename("e_load"),
                   priceh.rename("e_price")], axis=1)
    E.index = E.index.tz_localize(None)
    # ⚠ 合并表的**跨度由各自下载批次决定**（价格/负荷已回填到 2015，但 A75 分技术发电只有 2023+），
    #   concat 会取并集 ⇒ 若直接落盘，外层会多出 2015–2022 的"全 NaN 光伏/风电"行，
    #   下游（PS-037 逐年统计）会混入空年份。本面板语义固定为 **2023-01 起**，显式裁剪。
    E = E[E.index.year >= 2023]
    print("ENTSO-E 小时面板:", E.shape, E.index.min(), "~", E.index.max())

    # ---- 与 Energy-Charts 口径对齐诊断 ----
    for y in (2023, 2024, 2025):
        f = os.path.join(D_S, f"spain_regime_hourly_{y}.csv")
        if not os.path.exists(f):
            continue
        C = pd.read_csv(f, index_col=0, parse_dates=True)
        C.columns = [c.strip() for c in C.columns]
        sub = E[E.index.year == y]
        m = C.join(sub, how="inner")
        print("\n" + "=" * 74)
        print("== %d  共同样本 %d 小时 ==" % (y, len(m)))
        for a, b, lbl in [("act", "e_solar", "光伏"), ("wind", "e_wind", "风电"),
                          ("load", "e_load", "负荷"), ("price", "e_price", "电价")]:
            if a not in m or b not in m:
                continue
            best, row = None, []
            for lag in (-2, -1, 0, 1, 2):
                mm = m[[a, b]].copy()
                mm[b] = mm[b].shift(lag)
                mm = mm.dropna()
                if len(mm) < 100:
                    continue
                r = mm[a].corr(mm[b])
                row.append("lag%+d r=%.3f" % (lag, r))
                if best is None or abs(r) > abs(best[1]):
                    best = (lag, r, mm)
            print("  %s(%s vs %s): 能量比 %.3f | %s" % (
                lbl, a, b, m[a].sum() / m[b].sum() if m[b].sum() else np.nan, " ".join(row)))
            if best:
                lag, r, mm = best
                mae = (mm[a] - mm[b]).abs().mean()
                print("     最佳 lag=%+d (r=%.3f): MAE %.0f MW, 均值 %s %.0f vs %s %.0f" %
                      (lag, r, mae, a, mm[a].mean(), b, mm[b].mean()))

    print("\n" + "=" * 74)
    print("ENTSO-E 年度统计:")
    print(E.groupby(E.index.year).agg(solar_TWh=("e_solar", lambda x: x.sum() / 1e3),
                                      wind_TWh=("e_wind", lambda x: x.sum() / 1e3),
                                      load_TWh=("e_load", lambda x: x.sum() / 1e3),
                                      price_mean=("e_price", "mean")).round(2).to_string())
    E.to_csv(OUT)
    print("\n→ %s" % OUT)


if __name__ == "__main__":
    main()
