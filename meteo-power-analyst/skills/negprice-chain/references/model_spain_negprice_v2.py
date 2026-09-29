"""西班牙 负价日概率 v2 · 两因子 + 温度驱动负荷预报 (PS-037)
背景: PS-035 的 S 指数(云量资源/月度负荷气候)在 2024/25 跨年 AUC 0.73, 但在**全新 2026** 塌到 0.495。
      诊断: 负价日 = 云量修正后的光伏资源 **AND** 负荷水平; S 只用月度负荷气候代理负荷,
      而 2026 起负荷通道成为主导(逐年 corr(负荷,negday) −0.41/−0.51/−0.59, 光伏通道 +0.18→−0.11)。
链路: ①温度(9 光伏区, Open-Meteo) → 负荷回归(CDD/HDD+周末+星期)
      ②负价日 logit/线性概率 = f(S, 负荷)
      ③季节预报 50 成员(短波 τ + Tmax) → 逐成员 S 与负荷 → 逐成员 P(负价日)
输出: data/spain/spain_negprice_v2_skill.csv, spain_negprice_v2_outlook.csv
用法: python skills/negprice-chain/references/model_spain_negprice_v2.py
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import pvlib

D_S = r"c:\work\meteo\data\spain"
D_T = r"c:\work\meteo\data\openmeteo_temperature_spain\daily_temp.json"
D_F = r"c:\work\meteo\data\openmeteo_seasonal_spain"
HUB = r"c:\work\meteo\data\gem\spain_solar_hubs_multi.csv"
OUT_SK = os.path.join(D_S, "spain_negprice_v2_skill.csv")
OUT_OUT = os.path.join(D_S, "spain_negprice_v2_outlook.csv")
ROWS_SK = []


def auc(score, label):
    s, y = np.asarray(score, float), np.asarray(label, float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def lstsq(X, y):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    ss = ((y - y.mean()) ** 2).sum()
    return b, (1 - (r @ r) / ss if ss > 0 else np.nan)


# ---------------- 温度 → 负荷 ----------------
def fit_load_model():
    d = json.load(open(D_T, encoding="utf-8"))
    names = list(d)
    tmax = np.column_stack([pd.to_numeric(pd.Series(d[n]["tmax"]), errors="coerce") for n in names])
    tmin = np.column_stack([pd.to_numeric(pd.Series(d[n]["tmin"]), errors="coerce") for n in names])
    dates = pd.to_datetime(d[names[0]]["time"])
    T = pd.Series(np.nanmean((tmax + tmin) / 2.0, axis=1), index=dates, name="tmean")
    T = T[~T.index.duplicated()]
    return T


def design(T, idx):
    t = T.reindex(idx).values
    cdd = np.clip(t - 22.0, 0, None)
    hdd = np.clip(15.0 - t, 0, None)
    we = (idx.weekday >= 5).astype(float)
    trend = np.asarray((idx - pd.Timestamp("2023-01-01")).days, float) / 365.25
    dow = pd.get_dummies(idx.dayofweek, prefix="d").values[:, 1:].astype(float)
    return (np.column_stack([np.ones(len(idx)), cdd, hdd, we, trend, dow]),
            ["const", "CDD22", "HDD15", "weekend", "trend"])


def main():
    print("=" * 80)
    print("[1] 官方向日面板 + 温度")
    g = pd.read_csv(os.path.join(D_S, "spain_official_daily.csv"), index_col=0, parse_dates=True)
    g = g[g["S"].notna()].copy()
    T = fit_load_model()
    common = g.index.intersection(T.dropna().index)      # 只保留有温度的日期
    g = g.loc[common]
    print("    逐日 %d 天; 温度 %d 天 (%s ~ %s); 交集 %d 天"
          % (len(g), len(T), T.index.min().date(), T.index.max().date(), len(common)))

    # ---------------- 负荷模型 ----------------
    print("\n[2] 负荷回归: load ~ CDD(>22℃) + HDD(<15℃) + 周末 + 星期")
    tr = g[(g["year"] >= 2023) & (g["year"] <= 2025)]
    Xtr, nm = design(T, tr.index)
    btr, r2 = lstsq(Xtr, tr["load"].values)
    print("    2023-25 拟合 R² = %.4f | CDD %+.0f MW/℃ | HDD %+.0f MW/℃ | 周末 %+.0f MW | 趋势 %+.0f MW/年"
          % (r2, btr[1], btr[2], btr[3], btr[4]))
    for y in (2023, 2024, 2025, 2026):
        t = g[g["year"] == y]
        X, _ = design(T, t.index)
        p = X @ btr
        print("    %d: 样本外/内 R²=%.3f, MAE=%.0f MW, 偏差 %+.0f MW"
              % (y, 1 - ((t["load"].values - p) ** 2).sum() /
                 ((t["load"].values - t["load"].mean()) ** 2).sum(),
                 np.abs(t["load"].values - p).mean(), (p - t["load"].values).mean()))
    # 含 2026 的运营期拟合
    op = g[g["year"] >= 2024]
    Xop, _ = design(T, op.index)
    bop, r2op = lstsq(Xop, op["load"].values)
    print("    运营期(2024-2026.09) 拟合 R² = %.4f" % r2op)

    # 逐日负荷预报(OOS: 2023-25 参数) —— 用于评估"真实可预报技能"
    dall = g.copy()
    Xall, _ = design(T, dall.index)
    dall["load_pred_oo"] = Xall @ btr          # 用 2023-25 参数
    dall["load_pred_op"] = Xall @ bop          # 用运营期参数

    # ---------------- 负价日模型 ----------------
    print("\n[3] 负价日模型对比 (训练 2024-25, 测试 2026 全新样本)")
    dall["load_gw"] = dall["load"] / 1000.0
    dall["loadoo_gw"] = dall["load_pred_oo"] / 1000.0
    SPECS = [
        ("S 单因子 (PS-035)", ["S"]),
        ("S + 实际负荷", ["S", "load_gw"]),
        ("S + 预报负荷(温度驱动)", ["S", "loadoo_gw"]),
        ("τ + 预报负荷", ["tau", "loadoo_gw"]),
    ]
    for lab, cols in SPECS:
        c = dall[(dall["year"] >= 2024) & (dall["year"] <= 2025)].dropna(subset=cols)
        X = np.column_stack([np.ones(len(c))] + [c[k].values for k in cols])
        b, _ = lstsq(X, c["negday"].values)
        line = []
        for te in (2024, 2025, 2026):
            t = dall[dall["year"] == te].dropna(subset=cols)
            Xt = np.column_stack([np.ones(len(t))] + [t[k].values for k in cols])
            p = np.clip(Xt @ b, 0, 1)
            line.append((auc(p, t["negday"].values), p.mean(), t["negday"].mean()))
        ROWS_SK.append({"spec": lab, "cols": ",".join(cols),
                        "auc_2024": line[0][0], "auc_2025": line[1][0], "auc_2026": line[2][0],
                        "pred_2026": line[2][1], "actual_2026": line[2][2]})
        print("    %-24s →2024 %.3f | →2025 %.3f | →2026 %.3f  (2026 预测 %.3f vs 实际 %.3f)"
              % (lab, line[0][0], line[1][0], line[2][0], line[2][1], line[2][2]))

    # ---------------- 运营期标定 + 45 天展望 ----------------
    print("\n[4] 运营期标定 (2024-2026.09) + 未来45天展望")
    COLS = ["S", "load_gw"]
    c = dall[dall["year"] >= 2024].dropna(subset=COLS)
    X = np.column_stack([np.ones(len(c))] + [c[k].values for k in COLS])
    B, _ = lstsq(X, c["negday"].values)
    print("    P(负价日) = %+.4f %+.4f×S %+.4f×load[GW]  (n=%d)" % (B[0], B[1], B[2], len(c)))
    cl = c.copy()
    cl["q"] = pd.qcut(cl["S"] + 0.0, 5, labels=False, duplicates="drop")
    pred = np.clip(np.column_stack([np.ones(len(cl))] + [cl[k].values for k in COLS]) @ B, 0, 1)
    print("    运营期 拟合期 AUC = %.3f, 预测均 %.3f vs 实际 %.3f"
          % (auc(pred, cl["negday"].values), pred.mean(), cl["negday"].mean()))

    # ---- 季节预报 → 逐成员 S 与负荷 ----
    sites, dates = {}, None
    for f in glob.glob(os.path.join(D_F, "*_seasonal_45d.json")):
        n = os.path.basename(f).replace("_seasonal_45d.json", "")
        d = json.load(open(f, encoding="utf-8"))["daily"]
        dates = pd.to_datetime(d["time"])
        sites[n] = {
            "sw": np.column_stack([d[f"shortwave_radiation_sum_member{k:02d}"] for k in range(1, 51)]),
            "tx": np.column_stack([d[f"temperature_2m_max_member{k:02d}"] for k in range(1, 51)]),
            "tn": np.column_stack([d[f"temperature_2m_min_member{k:02d}"] for k in range(1, 51)]),
            "lat": json.load(open(f, encoding="utf-8"))["latitude"],
            "lon": json.load(open(f, encoding="utf-8"))["longitude"],
        }
    names = list(sites)
    # 容量权重(与 PS-035 同法)
    pl = pd.read_csv(HUB)
    coords = np.array([[sites[n]["lat"], sites[n]["lon"]] for n in names])
    w = {n: 0.0 for n in names}
    for _, r in pl.iterrows():
        dx = coords[:, 0] - r["lat"]
        dy = np.cos(np.radians(r["lat"])) * (coords[:, 1] - r["lon"])
        w[names[int(np.argmin(dx * dx + dy * dy))]] += r["cap_2025"]
    tot = sum(w.values())
    w = {k: v / tot for k, v in w.items()}
    print("    fleet %.1f GW; 预报窗口 %s ~ %s (%d 天)"
          % (tot / 1000, dates[0].date(), dates[-1].date(), len(dates)))

    doy = dates.dayofyear.values


    def clear_daily(lat, lon, ds):
        out = []
        for dt in ds:
            t = pd.date_range(dt, dt + pd.Timedelta(days=1) - pd.Timedelta(minutes=5), freq="1h", tz="UTC")
            zen = pvlib.solarposition.get_solarposition(t, lat, lon)["apparent_zenith"]
            out.append(np.nansum(pvlib.clearsky.haurwitz(zen)) * 3600 / 1e6)
        return np.array(out)


    tau = np.zeros((len(dates), 50))
    tm = np.zeros((len(dates), 50))
    for n, s in sites.items():
        c = clear_daily(s["lat"], s["lon"], dates)
        tau += w[n] * np.clip(s["sw"] / c[:, None], 0, 1)
        tm += w[n] * (s["tx"] + s["tn"]) / 2.0
    tau = np.clip(tau, 0, 1)
    v = np.asarray(dates)
    # τ 尺度校正 (与 PS-035 同法)
    h = dall[dall["year"] <= 2025].copy()
    h["tau_h"] = h["solar"] / h["pot_cs"]
    tau_clim = h.groupby(h.index.dayofyear)["tau_h"].median()
    k = tau_clim.reindex(np.unique(doy)).dropna().median() / np.median(tau)
    tau_adj = np.clip(tau * k, 0, 1)
    print("    τ 尺度校正 k=%.3f" % k)

    cdd = np.clip(tm - 22.0, 0, None)
    hdd = np.clip(15.0 - tm, 0, None)
    we = (dates.weekday >= 5).astype(float)[:, None]
    trend_f = (np.asarray((dates - pd.Timestamp("2023-01-01")).days, float) / 365.25)[:, None]
    dow = pd.get_dummies(pd.Series(dates.dayofweek), prefix="d").values[:, 1:].astype(float)
    load_m = (bop[0] + bop[1] * cdd + bop[2] * hdd + bop[3] * we +
              bop[4] * trend_f + (dow @ bop[5:])[:, None]) / 1000.0

    S_m = np.zeros_like(tau_adj)
    for i, d0 in enumerate(doy):
        cc = (g.groupby("doy")["pot_cs"].median()).get(d0, np.nan)
        lc = (g[g["year"] <= 2025].groupby([g[g["year"] <= 2025].index.month,
                                            g[g["year"] <= 2025].index.weekday >= 5])["load"]
              .median()).get((dates[i].month, dates[i].weekday() >= 5), np.nan)
        S_m[i] = cc * tau_adj[i] / lc
    P = np.clip(B[0] + B[1] * S_m + B[2] * load_m, 0, 1)

    # ---- 季节偏差校正: 用历史同窗口(10-11月)的 预测−实际 平均偏差 ----
    opc = cl.copy()
    opc["pred"] = np.clip(np.column_stack([np.ones(len(opc))] + [opc[k].values for k in COLS]) @ B, 0, 1)
    on = opc[opc.index.month.isin([10, 11]) & (opc["year"] <= 2025)]
    bias_on = (on["pred"] - on["negday"]).mean()
    print("\n    季节偏差(10-11月, 2024-25, n=%d): 预测 %.3f vs 实际 %.3f ⇒ 偏差 %+.3f"
          % (len(on), on["pred"].mean(), on["negday"].mean(), bias_on))
    mon = opc.groupby(opc.index.month).apply(
        lambda x: pd.Series({"实际": x["negday"].mean(), "预测": x["pred"].mean()}))
    print("    逐月 实际/预测: " + " ".join("%d月%.0f/%.0f" % (m, r["实际"] * 100, r["预测"] * 100)
                                          for m, r in mon.iterrows()))
    Pc = np.clip(P - bias_on, 0, 1)

    out = pd.DataFrame({
        "date": v, "tau_p50": np.percentile(tau_adj, 50, axis=1),
        "S_p50": np.percentile(S_m, 50, axis=1),
        "load_p50": np.percentile(load_m, 50, axis=1),
        "Pnegday_mean": P.mean(axis=1),
        "Pnegday_p50": np.percentile(P, 50, axis=1),
        "Pnegday_p90": np.percentile(P, 90, axis=1),
        "Pnegday_p10": np.percentile(P, 10, axis=1),
        "Pcorr_mean": Pc.mean(axis=1),
        "Pcorr_p50": np.percentile(Pc, 50, axis=1),
        "Pcorr_p90": np.percentile(Pc, 90, axis=1),
        "Pcorr_p10": np.percentile(Pc, 10, axis=1),
    })
    out["wk"] = np.arange(len(out)) // 7 + 1
    out.to_csv(OUT_OUT, index=False)
    wk = out.groupby("wk").agg(周起=("date", "first"), tau=("tau_p50", "median"),
                               S=("S_p50", "median"), load_GW=("load_p50", "median"),
                               P=("Pnegday_mean", "mean"), P_corr=("Pcorr_mean", "mean"),
                               P10=("Pcorr_p10", "median"), P90=("Pcorr_p90", "median"))
    print("\n    未来 45 天 (v2 两因子): P=原始, P_corr=季节校正后")
    print(wk.round(3).to_string())
    print("    全窗均值: 原始 %.3f | 季节校正后 %.3f   [PS-035 旧模型: 0.082]"
          % (out["Pnegday_mean"].mean(), out["Pcorr_mean"].mean()))
    pd.DataFrame(ROWS_SK).to_csv(OUT_SK, index=False)
    print("\n→ %s\n→ %s" % (OUT_SK, OUT_OUT))


if __name__ == "__main__":
    main()
