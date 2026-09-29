"""西班牙 负价概率 季节预报链路 (PS-035)
动机: PS-034 判定"ERCOT 预报桥不成立"，但西班牙负价可预报性另有结构——
      日尺度上可预报的 pot/负荷 指数对负价中等相关(+0.45/+0.60)，且负价有强季节性。
链路: Open-Meteo Seasonal 50成员逐日短波 → 逐站晴空(haurwitz) → fleet 传输率 τ
      → 可预报指数 S = clear_clim(doy) × τ / load_clim(月,工作日)
      → 历史标定 P(负价日) 与 负价小时/日 → 套到未来45天(逐成员传播)
验证: 跨年(2024↔2025) AUC，避免自我验证。
输出: data/spain/spain_negprice_calibration.csv, spain_negprice_outlook.csv
用法: python scripts/analysis/model_spain_negprice_forecast.py
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import pvlib

D_F = r"c:\work\meteo\data\openmeteo_seasonal_spain"
D_S = r"c:\work\meteo\data\spain"
HUB = r"c:\work\meteo\data\gem\spain_solar_hubs_multi.csv"
OUT_CAL = os.path.join(D_S, "spain_negprice_calibration.csv")
OUT_OUT = os.path.join(D_S, "spain_negprice_outlook.csv")
ROWS = []


def load_forecast():
    sites = {}
    for f in glob.glob(os.path.join(D_F, "*_seasonal_45d.json")):
        name = os.path.basename(f).replace("_seasonal_45d.json", "")
        d = json.load(open(f, encoding="utf-8"))
        day = d["daily"]
        sw = np.column_stack([day[f"shortwave_radiation_sum_member{k:02d}"] for k in range(1, 51)])
        sites[name] = {"dates": pd.to_datetime(day["time"]), "sw": np.asarray(sw, float),
                       "lat": d["latitude"], "lon": d["longitude"]}
    return sites


def clear_daily(site, dates):
    out = []
    for dt in dates:
        t = pd.date_range(dt, dt + pd.Timedelta(days=1) - pd.Timedelta(minutes=5),
                          freq="1h", tz="UTC")
        zen = pvlib.solarposition.get_solarposition(t, site["lat"], site["lon"])["apparent_zenith"]
        out.append(np.nansum(pvlib.clearsky.haurwitz(zen)) * 3600 / 1e6)
    return np.array(out)


def site_weights(sites):
    pl = pd.read_csv(HUB)
    names = list(sites.keys())
    coords = np.array([[sites[n]["lat"], sites[n]["lon"]] for n in names])
    w = {n: 0.0 for n in names}
    for _, r in pl.iterrows():
        dx = coords[:, 0] - r["lat"]
        dy = np.cos(np.radians(r["lat"])) * (coords[:, 1] - r["lon"])
        w[names[int(np.argmin(dx * dx + dy * dy))]] += r["cap_2025"]
    tot = sum(w.values())
    return {k: v / tot for k, v in w.items()}, tot


def hist_daily():
    """历史逐日: pot_cs/act(MWh) 与 负荷(MW)"""
    fr = []
    for y in (2023, 2024, 2025):
        x = pd.read_csv(os.path.join(D_S, f"spain_regime_hourly_{y}.csv"),
                        index_col=0, parse_dates=True)
        g = pd.DataFrame({"pot_cs": x["pot_cs"].resample("D").sum(),
                          "act": x["act"].resample("D").sum(),
                          "load": x["load"].resample("D").mean(),
                          "price": x["price"].resample("D").mean(),
                          "neg_h": (x["price"] < 0).resample("D").sum()})
        g = g[g["act"] > 1e3]
        g["year"] = y
        fr.append(g)
    return pd.concat(fr)


def auc(score, label):
    s, y = np.asarray(score, float), np.asarray(label, float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    sites = load_forecast()
    dates = list(sites.values())[0]["dates"]
    doy_fc = dates.dayofyear.values
    w, tot = site_weights(sites)
    print(f"fleet {tot/1000:.1f} GW 按最近站权重: "
          + ", ".join(f"{k}={v*100:.0f}%" for k, v in sorted(w.items(), key=lambda x: -x[1])))

    fleet_tau = np.zeros((len(dates), 50))
    for n, s in sites.items():
        cl = clear_daily(s, dates)
        fleet_tau += w[n] * np.clip(s["sw"] / cl[:, None], 0, 1)
    fleet_tau = np.clip(fleet_tau, 0, 1)
    print(f"预报 fleet τ: 中位 {np.median(fleet_tau):.3f}, "
          f"P10 {np.percentile(fleet_tau,10):.3f}, P90 {np.percentile(fleet_tau,90):.3f}")

    h = hist_daily()
    clear_clim = h.groupby(h.index.dayofyear)["pot_cs"].median()
    load_clim = h.groupby([h.index.month, h.index.weekday >= 5])["load"].median()

    # --- τ 标定: 预报(haurwitz水平面) 与 历史(POA链路) 的尺度差异用重叠 doy 窗口校正 ---
    h["tau_hist"] = h["act"] / h["pot_cs"]
    tau_clim = h.groupby(h.index.dayofyear)["tau_hist"].median()
    win = np.unique(doy_fc)
    t_hist_win = tau_clim.reindex(win).dropna()
    k = t_hist_win.median() / np.median(fleet_tau)
    print(f"τ 尺度校正 k={k:.3f} (历史窗口 τ 中位 {t_hist_win.median():.3f} / "
          f"预报 τ 中位 {np.median(fleet_tau):.3f})")
    tau_adj = np.clip(fleet_tau * k, 0, 1)

    # --- 历史指数 S 与结果 ---
    h["clear_clim"] = clear_clim.reindex(h.index.dayofyear).values
    h["load_clim"] = load_clim.reindex(list(zip(h.index.month, h.index.weekday >= 5))).values
    h["S"] = h["clear_clim"] * h["tau_hist"] / h["load_clim"]
    h["negday"] = (h["neg_h"] > 0).astype(float)
    print(f"\n历史指数 S: corr(S, neg_h)={h['S'].corr(h['neg_h']):+.3f}, "
          f"corr(S, negday)={h['S'].corr(h['negday']):+.3f}")

    # --- 跨年验证 ---
    print("\n== 跨年验证 (AUC) ==")
    for tr, te in ((2024, 2025), (2025, 2024)):
        a = h[h["year"] == tr]
        b = h[h["year"] == te]
        bm = b[b["year"] == te]
        lo = bm["S"].quantile(0.2)
        print(f"  train {tr} → test {te}: 全样本 AUC {auc(bm['S'], bm['negday']):.3f} | "
              f"测试年 S 最高20% 阈 {lo:.3f} → 该子集负价日占 {bm[bm['S']>=lo]['negday'].mean()*100:.0f}% "
              f"(全年 {bm['negday'].mean()*100:.0f}%)")

    # --- 标定曲线 (合并 2024-25, 五分位) ---
    c = h[(h["year"] >= 2024) & (h["S"].notna())].copy()
    q = pd.qcut(c["S"].rank(method="first"), 5, labels=False)
    for kk, sub in c.groupby(q):
        ROWS.append({"curve": "quintile", "bin": int(kk) + 1, "S_med": sub["S"].median(),
                     "n": len(sub), "p_negday": sub["negday"].mean(),
                     "neg_h": sub["neg_h"].mean(), "price": sub["price"].mean()})
        print(f"  Q{int(kk)+1}: S {sub['S'].median():.3f} | P(负价日) {sub['negday'].mean()*100:.0f}% "
              f"| 负价 {sub['neg_h'].mean():.1f}h | 均价 {sub['price'].mean():.1f}€")
    X = np.column_stack([np.ones(len(c)), c["S"].values])
    b, *_ = np.linalg.lstsq(X, c["negday"].values, rcond=None)
    fit = (b[0], b[1])
    print(f"  线性概率 P(负价日) = {b[0]:.3f} + {b[1]:.3f}×S  (n={len(c)})")
    ROWS.append({"curve": "fit", "bin": 0, "S_med": np.nan, "n": len(c),
                 "p_negday": b[0], "neg_h": b[1], "price": np.nan})

    # --- 季节校准检验: 历史同窗口(秋) 的实际 vs 模型 ---
    cw = c[c.index.dayofyear.isin(set(doy_fc))]
    pred = np.clip(fit[0] + fit[1] * cw["S"], 0, 1)
    print(f"  季节校准(历史同窗口 doy): n={len(cw)} 实际 P(负价日) {cw['negday'].mean():.3f} "
          f"vs 模型均值 {pred.mean():.3f}  (偏差 {pred.mean()-cw['negday'].mean():+.3f})")
    ROWS.append({"curve": "season_check", "bin": 0, "S_med": np.nan, "n": len(cw),
                 "p_negday": cw["negday"].mean(), "neg_h": pred.mean(), "price": np.nan})
    bias = pred.mean() - cw["negday"].mean()
    fit_corr = (fit[0] - bias, fit[1])
    print(f"  ⇒ 季节偏差校正: 截距 {fit[0]:+.3f} → {fit_corr[0]:+.3f} (校正 −{bias:.3f})")

    # --- 未来45天展望 (逐成员) ---
    S_fc = np.zeros_like(tau_adj)
    for i, d in enumerate(doy_fc):
        cl = clear_clim.get(d, np.nanmedian(clear_clim.values))
        lc = load_clim.get((dates[i].month, dates[i].weekday() >= 5), np.nanmedian(load_clim.values))
        S_fc[i] = cl * tau_adj[i] / lc
    p_raw = np.clip(fit[0] + fit[1] * S_fc, 0, 1)
    p_neg = np.clip(fit_corr[0] + fit_corr[1] * S_fc, 0, 1)
    out = pd.DataFrame({
        "date": dates,
        "tau_p50": np.percentile(tau_adj, 50, axis=1),
        "S_p50": np.percentile(S_fc, 50, axis=1),
        "S_p10": np.percentile(S_fc, 10, axis=1),
        "S_p90": np.percentile(S_fc, 90, axis=1),
        "Pneg_raw_mean": p_raw.mean(axis=1),
        "Pnegday_mean": p_neg.mean(axis=1),
        "Pnegday_p50": np.percentile(p_neg, 50, axis=1),
        "Pnegday_p90": np.percentile(p_neg, 90, axis=1),
    })
    out["wk"] = np.arange(len(out)) // 7 + 1
    out.to_csv(OUT_OUT, index=False)
    wk = out.groupby("wk").agg(周起=("date", "first"), tau=("tau_p50", "median"),
                               S=("S_p50", "median"), P=("Pnegday_mean", "mean"),
                               P_raw=("Pneg_raw_mean", "mean"),
                               P90=("Pnegday_p90", "median"))
    print("\n== 西班牙 未来45天 负价日概率 (P=季节校正后, P_raw=未校正) ==")
    print(wk.round(3).to_string())
    print(f"  全窗 P(负价日) 中位 {out['Pnegday_p50'].median():.2f} "
          f"(成员均值 {out['Pnegday_mean'].mean():.2f}; 未校正 {out['Pneg_raw_mean'].mean():.2f})")
    pd.DataFrame(ROWS).to_csv(OUT_CAL, index=False)
    print(f"\n→ {OUT_CAL}\n→ {OUT_OUT}")


if __name__ == "__main__":
    main()
