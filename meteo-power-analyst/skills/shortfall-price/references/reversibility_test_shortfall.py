"""缺口成因判据 · 可逆性/稳健性检验 (ERCOT + 西班牙, 统一设定)
问题: "决定缺口→电价符号的是缺口成因(外生供给损失 vs 内生供给过剩), 而非电源类型" —— 可逆? 稳健?

对 {市场}×{技术}×{成因} 每个格子, 在同一设定下给 4 个估计:
  目标函数: ln(price) 与 price(水平)
  控制:     gap 单独 与 gap + 该技术出力水平
报告 %/GW (log) 与 价格单位/GW (水平)、SE、n、corr(gap, 水平)。

格子: ERCOT 光伏 外生(晴空缺口)/内生(潜力−实际); ERCOT 风电 外生(低风异常)/内生(潜力−实际);
      西班牙 光伏 外生(gap_cs)/内生(gap_w)。
输入: data/ercot/{ercot_hourly_panel_{2025,2026},wind_power_hourly_2025_2026,ercot_pv_potential_2025_2026}.csv,
      data/nsrdb/pv_clearsky_hourly_2025_2026.csv, data/spain/spain_regime_hourly_{2024,2025}.csv
输出: data/ercot/reversibility_matrix.csv + stdout
用法: python scripts/analysis/reversibility_test_shortfall.py
"""
import os

import numpy as np
import pandas as pd

D_E = r"c:\work\meteo\data\ercot"
D_N = r"c:\work\meteo\data\nsrdb"
D_S = r"c:\work\meteo\data\spain"
OUT = os.path.join(D_E, "reversibility_matrix.csv")
PG = 100000.0


def regress(y, df, num_cols, fe_specs):
    mats = [np.column_stack([np.ones(len(y))] + [df[c].values for c in num_cols])]
    for values, _ in fe_specs:
        s = pd.Series(np.asarray(values))
        cats = sorted(s.unique())
        m = [(s == c).astype(float).values for c in cats[1:]]
        if m:
            mats.append(np.column_stack(m))
    X = np.column_stack(mats)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - (resid @ resid) / ((y - y.mean()) ** 2).sum()
    return (["const"] + num_cols), beta, se, r2


ROWS = []


def estimate(market, tech, cause, gap, year, sub, price, level, others, unit):
    fe = [(sub.index.hour, "h"), (sub.index.month, "m")]
    out = {}
    base = [gap] + others
    for tag, cols in (("only", base), ("lvl", [gap, level] + others)):
        yl = np.log(sub[price].clip(lower=1.0)).values
        n, b, s, _ = regress(yl, sub, cols, fe)
        out[f"b_log_{tag}"] = b[n.index(gap)] * PG
        out[f"se_log_{tag}"] = s[n.index(gap)] * PG
        yv = sub[price].values
        n, b, s, _ = regress(yv, sub, cols, fe)
        out[f"b_raw_{tag}"] = b[n.index(gap)] * 1000.0
        out[f"se_raw_{tag}"] = s[n.index(gap)] * 1000.0
    out.update({"market": market, "tech": tech, "cause": cause, "gap": gap,
                "year": year, "n": len(sub), "unit": unit,
                "corr_gap_level": sub[gap].corr(sub[level])})
    ROWS.append(out)
    print(f"  {year} {tech} {cause}: log 单独 {out['b_log_only']:+.2f}"
          f"(SE {out['se_log_only']:.2f}) -> +水平 {out['b_log_lvl']:+.2f}"
          f"(SE {out['se_log_lvl']:.2f}) | 水平 单独 {out['b_raw_only']:+.1f}"
          f" -> +水平 {out['b_raw_lvl']:+.1f} {unit}/GW | corr={out['corr_gap_level']:+.2f} n={len(sub)}")


def ercot():
    pan = pd.concat([pd.read_csv(os.path.join(D_E, f"ercot_hourly_panel_{y}.csv"),
                                 index_col=0, parse_dates=True) for y in (2025, 2026)])
    pan = pan[~pan.index.duplicated(keep="first")].sort_index()
    w = pd.read_csv(os.path.join(D_E, "wind_power_hourly_2025_2026.csv"),
                    index_col=0, parse_dates=True)
    pvpot = pd.read_csv(os.path.join(D_E, "ercot_pv_potential_2025_2026.csv"),
                        index_col=0, parse_dates=True)
    cs = pd.read_csv(os.path.join(D_N, "pv_clearsky_hourly_2025_2026.csv"),
                     index_col=0, parse_dates=True)
    cs.index = pd.to_datetime(cs.index, utc=True).tz_localize(None)
    cs = cs[~cs.index.duplicated(keep="first")]

    df = pd.DataFrame({"solar": pan["solar"], "wind": pan["wind"],
                       "demand": pan["demand"], "rtm": pan["rtm"]})
    df = df.join(w[["w_short", "w_drought"]], how="left")
    df = df.join(pvpot[["pv_pot", "pv_gap_w"]], how="left").join(cs[["clearsky_mw"]], how="left")
    raw = df["clearsky_mw"] - df["solar"]
    off = raw.groupby(df.index.hour).quantile(0.05)
    df["pv_gap_cs"] = (raw - off.reindex(df.index.hour).values).clip(lower=0)

    print("=" * 100)
    print("ERCOT (hour/month FE; log 列=%/GW, 水平列=$/MWh per GW)")
    for year in (2025, 2026):
        pv = df[(df.index.year == year) & (df["solar"] > 50)].dropna(
            subset=["pv_gap_cs", "pv_gap_w", "solar", "wind", "demand", "rtm"])
        estimate("ERCOT", "PV", "外生", "pv_gap_cs", year, pv, "rtm", "solar", ["wind", "demand"], "$")
        estimate("ERCOT", "PV", "内生", "pv_gap_w", year, pv, "rtm", "solar", ["wind", "demand"], "$")
        wd = df[df.index.year == year].dropna(
            subset=["w_short", "w_drought", "wind", "solar", "demand", "rtm"])
        estimate("ERCOT", "Wind", "外生", "w_drought", year, wd, "rtm", "wind", ["solar", "demand"], "$")
        estimate("ERCOT", "Wind", "内生", "w_short", year, wd, "rtm", "wind", ["solar", "demand"], "$")


def spain():
    print("=" * 100)
    print("西班牙 (hour/month FE; log 列=%/GW, 水平列=€/MWh per GW)")
    for year in (2024, 2025):
        p = os.path.join(D_S, f"spain_regime_hourly_{year}.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, index_col=0, parse_dates=True)
        d = d[d["act"] > 50].dropna(
            subset=["gap_cs", "gap_w", "act", "wind", "load", "price"]).copy()
        estimate("西班牙", "PV", "外生", "gap_cs", year, d, "price", "act", ["wind", "load"], "€")
        estimate("西班牙", "PV", "内生", "gap_w", year, d, "price", "act", ["wind", "load"], "€")


if __name__ == "__main__":
    ercot()
    spain()
    t = pd.DataFrame(ROWS)
    cols = ["market", "tech", "cause", "gap", "year", "unit", "n", "corr_gap_level",
            "b_log_only", "se_log_only", "b_log_lvl", "se_log_lvl",
            "b_raw_only", "se_raw_only", "b_raw_lvl", "se_raw_lvl"]
    t[cols].to_csv(OUT, index=False)
    print(f"\n→ {OUT}")
