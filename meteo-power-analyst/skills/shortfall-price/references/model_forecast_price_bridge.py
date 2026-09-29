"""缺口 → 电价 的日尺度转移函数 + 季节预报展望 (PS-034)
动机: PS-027 给出未来45天"缺日/重缺日"概率, PS-032/033 给出"缺口→电价"的符号与工况。
      本流程把两者接起来: 先标定**日尺度转移函数**, 再把它套到 PS-027 的季节预报上。
发现(先导诊断): 
  ERCOT —— 日尺度云致缺口对电价的传递**很弱且是"稀缺"方向**(白天相对逐时气候溢价随缺口上升),
            且**不标记负价**; 原因是缺口与需求负相关(云来天凉, 日尺度上被抵消)。
  西班牙 —— 日尺度内生缺口 gap_w 与负价小时**强相关**(corr≈+0.80), 可建成可用的负价转移曲线。
产出: data/ercot/forecast_bridge_calibration.csv (两市场校准)
      data/ercot/forecast_price_outlook.csv (ERCOT 未来45天白天溢价展望)
用法: python skills/shortfall-price/references/model_forecast_price_bridge.py
"""
import os

import numpy as np
import pandas as pd

D_E = r"c:\work\meteo\data\ercot"
D_S = r"c:\work\meteo\data\spain"
SEASONAL = r"c:\work\meteo\data\openmeteo_seasonal\seasonal_shortfall_risk.csv"
OUT_CAL = os.path.join(D_E, "forecast_bridge_calibration.csv")
OUT_OUT = os.path.join(D_E, "forecast_price_outlook.csv")
DAY_HOURS = range(13, 24)
ROWS = []


def ols(x, y):
    X = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    se = np.sqrt(np.diag((r @ r / max(len(y) - 2, 1)) * np.linalg.pinv(X.T @ X)))
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - (r @ r) / ss_tot if ss_tot > 0 else np.nan
    return b, se, r2


def ercot_calibration():
    s = pd.read_csv(os.path.join(D_E, "shortfall_physical_2025_2026.csv"),
                    parse_dates=["time_utc"]).set_index("time_utc")
    daily = pd.DataFrame({"cle": s["clearsky_mw"].resample("D").sum(),
                          "sf": s["shortfall_phys"].resample("D").sum()})
    daily = daily[daily["cle"] > 1e3]
    daily["deficit"] = daily["sf"] / daily["cle"]

    pan = pd.concat([pd.read_csv(os.path.join(D_E, f"ercot_hourly_panel_{y}.csv"),
                                 index_col=0, parse_dates=True) for y in (2025, 2026)])
    pan = pan[~pan.index.duplicated(keep="first")].sort_index()
    pan["h"] = pan.index.hour
    # 白天溢价 = 该小时电价 − 该小时(全样本)中位价 → 去掉日循环与季节
    clim = pan.groupby("h")["rtm"].transform("median")
    pan["prem"] = pan["rtm"] - clim
    day = pan[pan["h"].isin(DAY_HOURS)]
    dp = pd.DataFrame({"p_day": day["rtm"].resample("D").mean(),
                       "prem_day": day["prem"].resample("D").mean(),
                       "neg_day": (day["rtm"] < 0).resample("D").sum(),
                       "low5_day": (day["rtm"] < 5).resample("D").sum(),
                       "dem_day": day["demand"].resample("D").mean(),
                       "pv_day": day["solar"].resample("D").mean()})
    d = daily.join(dp, how="inner").dropna()
    b, se, r2 = ols(d["deficit"].values, d["prem_day"].values)
    print(f"[ERCOT] 白天溢价 = {b[0]:+.2f} + {b[1]:+.2f}×deficit  "
          f"(SE b {se[1]:.2f}, R² {r2:.3f}, n={len(d)})")
    print(f"  即缺口分数 0→1 对应白天溢价 {b[0]:+.2f}→{b[0]+b[1]:+.2f} $/MWh")
    print(f"  corr(deficit, prem_day)={d['deficit'].corr(d['prem_day']):+.3f}, "
          f"corr(deficit, neg_day)={d['deficit'].corr(d['neg_day']):+.3f}, "
          f"corr(deficit, dem_day)={d['deficit'].corr(d['dem_day']):+.3f}")
    ROWS.append({"market": "ERCOT", "curve": "fit", "bin": 0, "driver": np.nan,
                 "fit_a": b[0], "fit_b": b[1], "fit_se": se[1], "fit_r2": r2, "n": len(d)})
    q = pd.qcut(d["deficit"].rank(method="first"), 5, labels=False)
    for k, sub in d.groupby(q):
        ROWS.append({"market": "ERCOT", "curve": "day_premium", "bin": int(k) + 1,
                     "driver": d.loc[sub.index, "deficit"].mean(),
                     "prem_mean": sub["prem_day"].mean(), "neg_h_day": sub["neg_day"].mean(),
                     "low5_h_day": sub["low5_day"].mean(), "dem_mean": sub["dem_day"].mean(),
                     "p_mean": sub["p_day"].mean()})
        print(f"  Q{int(k)+1}: deficit {d.loc[sub.index,'deficit'].mean():.2f} "
              f"溢价 {sub['prem_day'].mean():+.2f} | 白天负价 {sub['neg_day'].mean():.2f}h "
              f"| 需求 {sub['dem_day'].mean()/1000:.1f}GW")
    return b, se, r2


def spain_curve():
    for year in (2023, 2024, 2025):
        x = pd.read_csv(os.path.join(D_S, f"spain_regime_hourly_{year}.csv"),
                        index_col=0, parse_dates=True)
        g = pd.DataFrame({"gap_w": x["gap_w"].resample("D").sum(),
                          "gap_cs": x["gap_cs"].resample("D").sum(),
                          "p_mean": x["price"].resample("D").mean(),
                          "neg_h": (x["price"] < 0).resample("D").sum(),
                          "low5_h": (x["price"] < 5).resample("D").sum(),
                          "load": x["load"].resample("D").mean(),
                          "act": x["act"].resample("D").sum()})
        g = g[g["act"] > 1e3].dropna()
        negday = (g["neg_h"] > 0).astype(float)
        b, se, r2 = ols(g["gap_w"].values / 1000.0, negday.values)   # gap 以 GW·h 计
        print(f"[西班牙 {year}] P(负价日) = {b[0]:.3f} + {b[1]:.4f}×gap_w  "
              f"(SE {se[1]:.4f}, R² {r2:.3f}, n={len(g)}) | 负价日占 {negday.mean()*100:.0f}%")
        ROWS.append({"market": "西班牙", "curve": "fit", "year": year, "bin": year, "driver": np.nan,
                     "fit_a": b[0], "fit_b": b[1], "fit_se": se[1], "fit_r2": r2, "n": len(g)})
        q = pd.qcut(g["gap_w"].rank(method="first"), 5, labels=False)
        for k, sub in g.groupby(q):
            ROWS.append({"market": "西班牙", "curve": "neg_price", "year": year, "bin": int(k) + 1,
                         "driver": g.loc[sub.index, "gap_w"].mean() / 1000.0,
                         "prem_mean": np.nan, "neg_h_day": sub["neg_h"].mean(),
                         "low5_h_day": sub["low5_h"].mean(), "dem_mean": sub["load"].mean(),
                         "p_mean": sub["p_mean"].mean(),
                         "p_negday": (sub["neg_h"] > 0).mean()})
            print(f"  {year} Q{int(k)+1}: gap_w {g.loc[sub.index,'gap_w'].mean()/1000:.1f}GW·h "
                  f"| P(负价日) {(sub['neg_h']>0).mean()*100:.0f}% | 负价 {sub['neg_h'].mean():.1f}h "
                  f"| 均价 {sub['p_mean'].mean():.1f}€")


def outlook(b):
    """把 ERCOT 校准套到 PS-027 季节预报的日缺口分布上 (用 P10/P50/P90 三分位近似成员分布)"""
    f = pd.read_csv(SEASONAL)
    f["date"] = pd.to_datetime(f["date"])
    # 缺口分数 = 1 − τ; τ_p90 → deficit_p10, τ_p10 → deficit_p90
    f["def_p10"] = 1 - f["tau_p90"]
    f["def_p50"] = 1 - f["tau_p50"]
    f["def_p90"] = 1 - f["tau_p10"]
    for c in ("def_p10", "def_p50", "def_p90"):
        f["prem_" + c.split("_")[1]] = b[0] + b[1] * f[c]
    f["wk"] = np.arange(len(f)) // 7 + 1
    keep = ["date", "def_p10", "def_p50", "def_p90", "prem_p10", "prem_p50", "prem_p90",
            "P_轻缺日", "P_重缺日", "P_热日", "tmax_p50"]
    f[keep].to_csv(OUT_OUT, index=False)
    wk = f.groupby("wk").agg(周起=("date", "first"), deficit_p50=("def_p50", "median"),
                             prem_p50=("prem_p50", "median"), prem_p10=("prem_p10", "median"),
                             prem_p90=("prem_p90", "median"),
                             P_热=("P_热日", "mean"), tmax=("tmax_p50", "median"))
    print("\n== ERCOT 未来45天 白天溢价展望 ($/MWh, 相对逐时气候) ==")
    print(wk.round(2).to_string())
    print(f"  全窗: deficit 中位 {f['def_p50'].median():.2f}, "
          f"溢价中位 {f['prem_p50'].median():+.2f} (P10 {f['prem_p10'].median():+.2f} "
          f"~ P90 {f['prem_p90'].median():+.2f})")
    print(f"\n→ {OUT_OUT}")


if __name__ == "__main__":
    b, se, r2 = ercot_calibration()
    spain_curve()
    pd.DataFrame(ROWS).to_csv(OUT_CAL, index=False)
    print(f"\n→ {OUT_CAL}")
    outlook(b)
