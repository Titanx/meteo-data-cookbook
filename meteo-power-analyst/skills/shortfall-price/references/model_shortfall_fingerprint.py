"""缺口"工况指纹": 外生 vs 内生缺口的分位特征对比 (ERCOT × 西班牙)
动机: PS-032 已证"外生缺口→正、内生缺口→负"只是方向相容, 且仅"内生→负"稳健。
      本流程把符号落到**可观测工况**上：按缺口分位分组, 看各组的小时价格中位、低价/负价频率、
      需求(负荷)中位与时段 —— 检验"内生缺口 = 供给过剩标记"这一机制本身。
样本: ERCOT 2025/2026 (光伏取白天 solar>50; 风电取全时段);
      西班牙 2023/2024/2025 (光伏取白天 act>50, 含"无负价→负价常态化"的时间截面)。
输出: data/ercot/shortfall_fingerprint.csv (分位明细) + ..._summary.csv (首末档对比)
用法: python scripts/analysis/model_shortfall_fingerprint.py
"""
import os

import numpy as np
import pandas as pd

D_E = r"c:\work\meteo\data\ercot"
D_N = r"c:\work\meteo\data\nsrdb"
D_S = r"c:\work\meteo\data\spain"
OUT = os.path.join(D_E, "shortfall_fingerprint.csv")
OUT_S = os.path.join(D_E, "shortfall_fingerprint_summary.csv")
BINS = 10
ROWS, SUMS = [], []


def fingerprint(market, tech, cause, gapname, gap, price, dem, hour, year, unit):
    v = pd.Series(gap).values
    order = pd.Series(v).rank(method="first").values
    b = np.ceil(order / (len(v) / BINS)).astype(int)
    b[b < 1] = 1
    b = np.clip(b, 1, BINS)
    d = pd.DataFrame({"gap": v, "price": np.asarray(price), "dem": np.asarray(dem),
                      "hour": np.asarray(hour), "bin": b})
    for k in range(1, BINS + 1):
        s = d[d["bin"] == k]
        ROWS.append({"market": market, "tech": tech, "cause": cause, "gap": gapname,
                     "year": year, "bin": k, "n": len(s),
                     "gap_lo": s["gap"].min(), "gap_hi": s["gap"].max(),
                     "gap_med": s["gap"].median(),
                     "price_med": s["price"].median(),
                     "low_freq": (s["price"] < 5).mean() * 100,
                     "neg_freq": (s["price"] < 0).mean() * 100,
                     "dem_med": s["dem"].median(), "hour_med": s["hour"].median()})
    lo, hi = d[d["bin"] <= 2], d[d["bin"] >= BINS - 1]
    SUMS.append({"market": market, "tech": tech, "cause": cause, "gap": gapname,
                 "year": year, "n": len(d), "unit": unit,
                 "corr_gap_price": pd.Series(v).corr(pd.Series(np.asarray(price))),
                 "lo_price_med": lo["price"].median(), "hi_price_med": hi["price"].median(),
                 "lo_low_freq": (lo["price"] < 5).mean() * 100,
                 "hi_low_freq": (hi["price"] < 5).mean() * 100,
                 "lo_neg_freq": (lo["price"] < 0).mean() * 100,
                 "hi_neg_freq": (hi["price"] < 0).mean() * 100,
                 "lo_dem_med": lo["dem"].median(), "hi_dem_med": hi["dem"].median(),
                 "lo_hour_med": lo["hour"].median(), "hi_hour_med": hi["hour"].median()})


def ercot():
    pan = pd.concat([pd.read_csv(os.path.join(D_E, f"ercot_hourly_panel_{y}.csv"),
                                 index_col=0, parse_dates=True) for y in (2025, 2026)])
    pan = pan[~pan.index.duplicated(keep="first")].sort_index()
    w = pd.read_csv(os.path.join(D_E, "wind_power_hourly_2025_2026.csv"),
                    index_col=0, parse_dates=True)
    pv = pd.read_csv(os.path.join(D_E, "ercot_pv_potential_2025_2026.csv"),
                     index_col=0, parse_dates=True)
    cs = pd.read_csv(os.path.join(D_N, "pv_clearsky_hourly_2025_2026.csv"),
                     index_col=0, parse_dates=True)
    cs.index = pd.to_datetime(cs.index, utc=True).tz_localize(None)
    cs = cs[~cs.index.duplicated(keep="first")]

    df = pd.DataFrame({"solar": pan["solar"], "wind": pan["wind"],
                       "demand": pan["demand"], "rtm": pan["rtm"]})
    df = df.join(w[["w_short", "w_drought"]], how="left")
    df = df.join(pv[["pv_gap_w"]], how="left").join(cs[["clearsky_mw"]], how="left")
    raw = df["clearsky_mw"] - df["solar"]
    off = raw.groupby(df.index.hour).quantile(0.05)
    df["pv_gap_cs"] = (raw - off.reindex(df.index.hour).values).clip(lower=0)

    print("=" * 100)
    print("ERCOT 缺口指纹 (价格 $/MWh; 低价<5, 负价<0)")
    for year in (2025, 2026):
        pvd = df[(df.index.year == year) & (df["solar"] > 50)].dropna(
            subset=["pv_gap_cs", "pv_gap_w", "rtm", "demand"])
        wd = df[df.index.year == year].dropna(
            subset=["w_short", "w_drought", "rtm", "demand"])
        for gapname, cause, sub in (("pv_gap_cs", "外生", pvd), ("pv_gap_w", "内生", pvd)):
            fingerprint("ERCOT", "PV", cause, gapname, sub[gapname], sub["rtm"],
                        sub["demand"], sub.index.hour, year, "$")
        for gapname, cause, sub in (("w_drought", "外生", wd), ("w_short", "内生", wd)):
            fingerprint("ERCOT", "Wind", cause, gapname, sub[gapname], sub["rtm"],
                        sub["demand"], sub.index.hour, year, "$")
    for r in SUMS:
        if r["market"] == "ERCOT":
            print(f"  {r['year']} {r['tech']:4s} {r['cause']}: 低价频率 {r['lo_low_freq']:.1f}%→{r['hi_low_freq']:.1f}% | "
                  f"负价 {r['lo_neg_freq']:.1f}%→{r['hi_neg_freq']:.1f}% | "
                  f"价格中位 {r['lo_price_med']:.1f}→{r['hi_price_med']:.1f} | "
                  f"需求中位 {r['lo_dem_med']:.0f}→{r['hi_dem_med']:.0f} | corr={r['corr_gap_price']:+.2f}")


def spain():
    print("=" * 100)
    print("西班牙 缺口指纹 (价格 €/MWh; 低价<5, 负价<0)")
    for year in (2023, 2024, 2025):
        p = os.path.join(D_S, f"spain_regime_hourly_{year}.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, index_col=0, parse_dates=True)
        d = d[d["act"] > 50].dropna(subset=["gap_cs", "gap_w", "price", "load"])
        for gapname, cause in (("gap_cs", "外生"), ("gap_w", "内生")):
            fingerprint("西班牙", "PV", cause, gapname, d[gapname], d["price"],
                        d["load"], d.index.hour, year, "€")
    for r in SUMS:
        if r["market"] == "西班牙":
            print(f"  {r['year']} 光伏 {r['cause']}: 低价频率 {r['lo_low_freq']:.1f}%→{r['hi_low_freq']:.1f}% | "
                  f"负价 {r['lo_neg_freq']:.1f}%→{r['hi_neg_freq']:.1f}% | "
                  f"价格中位 {r['lo_price_med']:.1f}→{r['hi_price_med']:.1f} | "
                  f"负荷中位 {r['lo_dem_med']:.0f}→{r['hi_dem_med']:.0f} | corr={r['corr_gap_price']:+.2f}")


if __name__ == "__main__":
    ercot()
    spain()
    pd.DataFrame(ROWS).to_csv(OUT, index=False)
    pd.DataFrame(SUMS).to_csv(OUT_S, index=False)
    print(f"\n→ {OUT}\n→ {OUT_S}")
