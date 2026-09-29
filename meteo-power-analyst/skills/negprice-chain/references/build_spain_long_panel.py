# -*- coding: utf-8 -*-
"""西班牙 2015-2026 逐月长面板构建 (PS-039)

输入:
  · 日前价   data/entsoe/raw/price_da_YYYY-MM.csv   (2015-2022 小时; 2025-10 起 15 分钟)
  · 负荷     data/entsoe/raw/load_YYYY-MM.csv       (2015-2022 小时; 2023 起 15 分钟)
  · 光伏     data/energy_charts/es_public_power_YYYY.json (2015-2022 小时; 2023 起 15 分钟)
输出:
  data/spain/spain_long_panel.csv  (逐月: 负价h/零价h/最低价/均价/光伏TWh/负荷TWh/光伏占比)

⚠ 三源分辨率都随年份变化, 一律先重采样到小时再聚合, 否则 2023+ 能量虚增 4 倍。
用法: python skills/negprice-chain/references/build_spain_long_panel.py
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd

RAW = r"c:\work\meteo\data\entsoe\raw"
EC = r"c:\work\meteo\data\energy_charts"
OUT = r"c:\work\meteo\data\spain\spain_long_panel.csv"


def hourly_from_csv(path, valcol):
    d = pd.read_csv(path)
    if d.empty or valcol not in d.columns:
        return None
    t = pd.to_datetime(d["datetime_utc"], utc=True).dt.tz_localize(None)
    s = pd.Series(d[valcol].values, index=t).sort_index()
    s = s[~s.index.duplicated()]
    return s.resample("1h").mean()


def main():
    # ---- 价格 / 负荷: 逐月缓存 ----
    rows = {}
    for f in sorted(glob.glob(os.path.join(RAW, "price_da_*.csv"))):
        ym = re.search(r"price_da_(\d{4}-\d{2})", f).group(1)
        s = hourly_from_csv(f, "price_eur_mwh")
        if s is None or s.empty:
            continue
        p = pd.Period(ym, freq="M")
        s = s[(s.index >= p.start_time) & (s.index <= p.end_time)]
        if len(s) == 0:
            continue
        rows.setdefault(ym, {})
        rows[ym].update({"n_h_price": len(s), "neg_h": int((s < 0).sum()),
                         "zero_h": int((s == 0).sum()), "min_price": float(s.min()),
                         "mean_price": float(s.mean())})

    for f in sorted(glob.glob(os.path.join(RAW, "load_*.csv"))):
        ym = re.search(r"load_(\d{4}-\d{2})", f).group(1)
        s = hourly_from_csv(f, "load_mw")
        if s is None or s.empty:
            continue
        p = pd.Period(ym, freq="M")
        s = s[(s.index >= p.start_time) & (s.index <= p.end_time)]
        s = s[s > 0]           # ENTSO-E 用 0 表示缺测 (见 PS-036)
        if len(s) == 0:
            continue
        rows.setdefault(ym, {})
        rows[ym].update({"n_h_load": len(s), "load_TWh": float(s.sum()) / 1e6})

    # ---- 光伏: Energy-Charts 逐年 JSON ----
    sol = {}
    for y in range(2015, 2027):
        f = os.path.join(EC, "es_public_power_%d.json" % y)
        if not os.path.exists(f):
            continue
        j = json.loads(open(f, encoding="utf-8").read())
        data = None
        for p in j.get("production_types", []):
            if p.get("name") == "Solar":
                data = p["data"]
        if data is None:
            continue
        s = pd.Series([np.nan if x is None else float(x) for x in data],
                      index=pd.to_datetime(j["unix_seconds"], unit="s", utc=True)).sort_index()
        s = s[~s.index.duplicated()].resample("1h").mean()
        g = s.groupby([s.index.year, s.index.month]).sum() / 1e6
        # ⚠ 必须**累加**而非覆盖: Energy-Charts 的 start/end 按**当地时间**解释,
        #   所以 start=2016-01-01 会带回 2015-12-31 23:00 UTC 那一小时,
        #   覆盖写会把上一年的 12 月值冲成 ~0 (本流程踩过: 2015-12 由 0.443 变 2e-05 TWh)
        for (yy, mm), v in g.items():
            k = "%04d-%02d" % (yy, mm)
            sol[k] = sol.get(k, 0.0) + float(v)

    panel = pd.DataFrame([{"ym": k, **v} for k, v in rows.items()]).set_index("ym").sort_index()
    panel["solar_TWh"] = pd.Series(sol)
    panel["solar_share"] = panel["solar_TWh"] / panel["load_TWh"]

    full = pd.period_range("2015-01", "2026-09", freq="M").astype(str)
    miss_load = [m for m in full if m not in panel.index or pd.isna(panel.loc[m, "load_TWh"])]
    miss_price = [m for m in full if m not in panel.index or pd.isna(panel.loc[m, "neg_h"])]
    print("目标月份 %d 个 (2015-01 ~ 2026-09)" % len(full))
    print("缺负荷: %d 个 -> %s" % (len(miss_load), miss_load[:12] + (["..."] if len(miss_load) > 12 else [])))
    print("缺价格: %d 个" % len(miss_price))
    print("已有负荷 %d 月, 已有价格 %d 月, 已有光伏 %d 月"
          % (panel["load_TWh"].notna().sum(), panel["neg_h"].notna().sum(), panel["solar_TWh"].notna().sum()))

    panel_out = panel.reindex(full)
    panel_out.index.name = "ym"
    panel_out.reset_index().to_csv(OUT, index=False)
    print("\n→ %s" % OUT)
    print("\n可用月份概览(按年):")
    have = panel_out[panel_out["neg_h"].notna() & panel_out["solar_TWh"].notna()]
    g = have.groupby([int(m[:4]) for m in have.index]).agg(
        月数=("solar_TWh", "size"),
        负价h=("neg_h", "sum"), 零价h=("zero_h", "sum"),
        光伏TWh=("solar_TWh", "sum"), 负荷TWh=("load_TWh", "sum"))
    g["光伏占比%"] = (g["光伏TWh"] / g["负荷TWh"] * 100).round(1)
    print(g.round(1).to_string())


if __name__ == "__main__":
    main()
