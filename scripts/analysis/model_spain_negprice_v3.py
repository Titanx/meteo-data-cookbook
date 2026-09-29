"""西班牙 负价 概率/强度模型 v3 · 趋势 + logit + 季节结构 (PS-038)

背景(PS-037 的三个遗留问题):
  ① 概率模型系统性低估 2026 水位(预测 0.15~0.22 vs 实际 0.42) —— 负价"常态化"趋势未被建模;
  ② 线性概率两端被 clip ⇒ 季节校正后 P10 全为 0, 且无法做概率校准评估(Brier/reliability);
  ③ 季节偏差靠"事后截距平移"修补, 只用了 2 个秋季(n=122), 样本薄。

本流程:
  ① 目标从二元"负价日"扩到"负价小时强度"(E[负价 h/日]) —— 泊松对数链接, 信息量更大且无 clip;
  ② 概率模型改 logit;
  ③ 加入 (a) 时间趋势项 (b) 年内季节谐波(2 对), 让季节形状由数据学出(并与不学形状的版本对照);
  ④ 统一样本外评估: train 2024-25 / train 2023-25 → test 2026;
     指标 = AUC(排序) + Brier + 校准(预测均值 vs 实际) + 2026 可靠性分箱;
  ⑤ 展望改用**链接空间**的季节偏移(解 d 使历史 10-11 月平均概率等于实测), 而非 PS-037 的概率域 clip。

输出: data/spain/spain_negprice_v3_skill.csv
      data/spain/spain_negprice_v3_skill_train23.csv
      data/spain/spain_negprice_v3_reliability.csv
      data/spain/spain_negprice_v3_outlook.csv
用法: python scripts/analysis/model_spain_negprice_v3.py
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import pvlib
import statsmodels.api as sm

D_S = r"c:\work\meteo\data\spain"
D_T = r"c:\work\meteo\data\openmeteo_temperature_spain\daily_temp.json"
D_F = r"c:\work\meteo\data\openmeteo_seasonal_spain"
HUB = r"c:\work\meteo\data\gem\spain_solar_hubs_multi.csv"
OUT_SK = os.path.join(D_S, "spain_negprice_v3_skill.csv")
OUT_SK23 = os.path.join(D_S, "spain_negprice_v3_skill_train23.csv")
OUT_REL = os.path.join(D_S, "spain_negprice_v3_reliability.csv")
OUT_OUT = os.path.join(D_S, "spain_negprice_v3_outlook.csv")
TAU0 = pd.Timestamp("2023-01-01")
HARM = 2          # 年内季节谐波对数
AUTUMN = (10, 11)  # 季节偏移的参照窗口

# 设定: (名称, 目标, 特征, 模型类型)
SPECS = [
    ("P · 线性 S+负荷 (PS-037 基线)", "negday", ["S", "load_gw"], "linear"),
    ("P · 线性 S+负荷+趋势",          "negday", ["S", "load_gw", "trend"], "linear"),
    ("P · logit S+负荷",             "negday", ["S", "load_gw"], "logit"),
    ("P · logit S+负荷+趋势",        "negday", ["S", "load_gw", "trend"], "logit"),
    ("P · logit S+预报负荷+趋势",     "negday", ["S", "loadoo_gw", "trend"], "logit"),
    ("P · logit S+负荷+趋势+季节",    "negday", ["S", "load_gw", "trend", "harm"], "logit"),
    ("H · 泊松 S+负荷",              "negh", ["S", "load_gw"], "poisson"),
    ("H · 泊松 S+负荷+趋势",         "negh", ["S", "load_gw", "trend"], "poisson"),
    ("H · 泊松 S+预报负荷+趋势",      "negh", ["S", "loadoo_gw", "trend"], "poisson"),
    ("H · 泊松 S+负荷+趋势+季节",     "negh", ["S", "load_gw", "trend", "harm"], "poisson"),
]


def auc(score, label):
    s, y = np.asarray(score, float), np.asarray(label, float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def brier(p, y):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


# ---------------- 温度 / 负荷 ----------------
def load_temp_series():
    d = json.load(open(D_T, encoding="utf-8"))
    names = list(d)
    tmax = np.column_stack([pd.to_numeric(pd.Series(d[n]["tmax"]), errors="coerce") for n in names])
    tmin = np.column_stack([pd.to_numeric(pd.Series(d[n]["tmin"]), errors="coerce") for n in names])
    idx = pd.to_datetime(d[names[0]]["time"])
    T = pd.Series(np.nanmean((tmax + tmin) / 2.0, axis=1), index=idx, name="tmean")
    return T[~T.index.duplicated()]


def load_design(T, idx, nyear_harm=HARM):
    """负荷回归设计阵(MW): const, CDD, HDD, 周末, 趋势, 星期哑变量(6) [, 年内谐波]"""
    t = T.reindex(idx).values
    cdd = np.clip(t - 22.0, 0, None)
    hdd = np.clip(15.0 - t, 0, None)
    we = (idx.weekday >= 5).astype(float)
    trend = np.asarray((idx - TAU0).days, float) / 365.25
    dow = pd.get_dummies(idx.dayofweek, prefix="d").values[:, 1:].astype(float)
    cols = [np.ones(len(idx)), cdd, hdd, we, trend, dow]
    if nyear_harm:
        doy = idx.dayofyear.values
        for k in range(1, nyear_harm + 1):
            cols.append(np.sin(2 * np.pi * k * doy / 365.25))
            cols.append(np.cos(2 * np.pi * k * doy / 365.25))
    return np.column_stack(cols)


def lstsq(X, y):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    ss = ((y - y.mean()) ** 2).sum()
    return b, (1 - (r @ r) / ss if ss > 0 else np.nan)


# ---------------- 负价模型 ----------------
def p_design(df, cols):
    parts = [np.ones(len(df))]
    for c in cols:
        if c == "harm":
            doy = df.index.dayofyear.values
            for k in range(1, HARM + 1):
                parts.append(np.sin(2 * np.pi * k * doy / 365.25))
                parts.append(np.cos(2 * np.pi * k * doy / 365.25))
        else:
            parts.append(df[c].values.astype(float))
    return np.column_stack(parts)


def fit_spec(tr, target, cols, kind):
    X, y = p_design(tr, cols), tr[target].values.astype(float)
    if kind == "linear":         # 用 lstsq 拟合线性概率
        b, _ = lstsq(X, y)
        return ("lin", b), (lambda Xn, b=b: np.clip(Xn @ b, 0, 1)), (lambda Xn, b=b: Xn @ b)
    if kind == "logit":
        m = sm.Logit(y, X).fit(disp=0)
        return ("logit", m), (lambda Xn, m=m: m.predict(Xn)), (lambda Xn, m=m: Xn @ m.params)
    m = sm.GLM(y, X, family=sm.families.Poisson()).fit()
    return ("poisson", m), (lambda Xn, m=m: m.predict(Xn)), (lambda Xn, m=m: Xn @ m.params)


def main():
    print("=" * 84)
    print("[1] 官方向日面板 + 温度")
    g = pd.read_csv(os.path.join(D_S, "spain_official_daily.csv"), index_col=0, parse_dates=True)
    g = g[g["S"].notna()].copy()
    T = load_temp_series()
    g = g.loc[g.index.intersection(T.dropna().index)]
    g["load_gw"] = g["load"] / 1000.0
    g["trend"] = (g.index - TAU0).days.values / 365.25
    print("    逐日 %d 天 (%s ~ %s)" % (len(g), g.index.min().date(), g.index.max().date()))
    print("    逐年 负价日率: %s" % " ".join(
        "%d=%.1f%%" % (y, g[g.year == y]["negday"].mean() * 100) for y in sorted(g.year.unique())))
    print("    逐年 负价 h/日: %s" % " ".join(
        "%d=%.2f" % (y, g[g.year == y]["negh"].mean()) for y in sorted(g.year.unique())))

    # ---------------- 负荷模型 ----------------
    print("\n[2] 负荷回归: 年内谐波项的贡献 (训练 2023-25)")
    for nh in (0, 2):
        tr = g[g.year.isin((2023, 2024, 2025))]
        b, r2 = lstsq(load_design(T, tr.index, nh), tr["load"].values)
        oos = []
        for y in (2023, 2024, 2025, 2026):
            t = g[g.year == y]
            p = load_design(T, t.index, nh) @ b
            oos.append("%d R2=%.3f bias%+.0f" % (
                y, 1 - ((t["load"].values - p) ** 2).sum() /
                ((t["load"].values - t["load"].mean()) ** 2).sum(), (p - t["load"].values).mean()))
        print("    谐波 %d 对 (拟合 R2=%.4f): %s" % (nh, r2, " | ".join(oos)))
    bop, r2op = lstsq(load_design(T, g.index, HARM), g["load"].values)
    g["loadoo"] = load_design(T, g.index, HARM) @ bop
    g["loadoo_gw"] = g["loadoo"] / 1000.0
    print("    全样本(2023-2026.09) 拟合 R2=%.4f, 取谐波 %d 对" % (r2op, HARM))

    # ---------------- 样本外评估 ----------------
    for train_lab, yrs, out_path in (("2024-25", (2024, 2025), OUT_SK),
                                     ("2023-25", (2023, 2024, 2025), OUT_SK23)):
        print("\n[3] 样本外评估: train %s → test 各年" % train_lab)
        tr = g[g.year.isin(yrs)]
        rows, fitted = [], {}
        for lab, target, cols, kind in SPECS:
            meta, pred, eta = fit_spec(tr, target, cols, kind)
            fitted[lab] = (meta, pred, eta, cols, kind)
            rec = {"spec": lab, "target": target, "cols": ",".join(cols), "kind": kind,
                   "k_params": int(p_design(tr, cols).shape[1])}
            for te in (2024, 2025, 2026):
                t = g[g.year == te]
                p = pred(p_design(t, cols))
                rec["auc_%d" % te] = auc(p, t[target].values)
                rec["predmean_%d" % te] = p.mean()
                rec["actual_%d" % te] = t[target].mean()
                if te == 2026:
                    rec["brier_2026"] = brier(p, t[target].values) if target == "negday" else np.nan
            rows.append(rec)
            print("    %-30s k=%2d | AUC 24 %.3f 25 %.3f **26 %.3f** | 26 预测均 %.3f vs 实际 %.3f | Brier %.4f"
                  % (lab, rec["k_params"], rec["auc_2024"], rec["auc_2025"], rec["auc_2026"],
                     rec["predmean_2026"], rec["actual_2026"], rec["brier_2026"]))
        pd.DataFrame(rows).to_csv(out_path, index=False)

    # ---------------- 2026 可靠性 ----------------
    print("\n[4] 2026 可靠性分箱 (train 2023-25; 按预测概率等样本五分位)")
    rel_rows = []
    for lab in ("P · logit S+负荷+趋势", "P · logit S+负荷+趋势+季节"):
        _, pred, _, cols, _ = fitted[lab]
        t26 = g[g.year == 2026].copy()
        t26["p"] = pred(p_design(t26, cols))
        t26["bin"] = pd.qcut(t26["p"].rank(method="first"), 5, labels=False)
        rel = t26.groupby("bin").agg(n=("negday", "size"), p_mean=("p", "mean"),
                                     actual=("negday", "mean"), neg_h=("negh", "mean"))
        rel["gap"] = rel["p_mean"] - rel["actual"]
        rel["spec"] = lab
        print("  -- %s" % lab)
        print(rel.round(3).to_string())
        rel_rows.append(rel.reset_index())
        # Brier 分解: 可靠性 / 分辨率
        print("     整体 预测均 %.3f vs 实际 %.3f | Brier %.4f"
              % (t26["p"].mean(), t26["negday"].mean(), brier(t26["p"], t26["negday"])))
    pd.concat(rel_rows).to_csv(OUT_REL, index=False)

    # ---------------- 运营期标定 + 45 天展望 ----------------
    print("\n[5] 运营期标定 (2023-2026.09) + 未来 45 天展望")
    OP = [("P · logit S+负荷+趋势", "negday", ["S", "load_gw", "trend"], "logit"),
          ("P · logit S+负荷+趋势+季节", "negday", ["S", "load_gw", "trend", "harm"], "logit"),
          ("H · 泊松 S+负荷+趋势", "negh", ["S", "load_gw", "trend"], "poisson")]
    op = {}
    for lab, target, cols, kind in OP:
        meta, pred, eta = fit_spec(g, target, cols, kind)
        X = p_design(g, cols)
        # 季节偏移参照窗口: 只取 2024-2025 的 10-11 月(与 PS-037 同口径; 2023 全年零负价无信息)
        on = (g.index.month.isin(AUTUMN)) & (g.year >= 2024) & (g.year <= 2025)
        e_on = eta(X)
        tgt = g[target].values[on].mean()
        if kind == "logit":
            d = solve_offset_logit(e_on[on], tgt)
            print("    %s: 拟合均 %.4f vs 实际 %.4f | 10-11月(24-25, n=%d) 偏移 d=%+.4f (目标 %.4f)"
                  % (lab, pred(X).mean(), g[target].mean(), int(on.sum()), d, tgt))
        else:
            d = np.log(np.mean(np.exp(e_on[on])) / tgt)
            print("    %s: 拟合均 %.3f vs 实际 %.3f | 10-11月(24-25, n=%d) 偏移 d=%+.4f (目标 %.3f)"
                  % (lab, pred(X).mean(), g[target].mean(), int(on.sum()), d, tgt))
        op[lab] = (meta, pred, eta, cols, kind, d)

    # 情景 C: 同年比例口径 —— 秋季(10-11月)与全年负价日率的比例在 2024/2025 稳定
    ann = g.groupby("year")["negday"].mean()
    ratios = [g[(g.index.year == y) & g.index.month.isin(AUTUMN)]["negday"].mean() / ann[y]
              for y in (2024, 2025)]
    ann26 = g[g.year == 2026]["negday"].mean()   # 2026 = 1-9 月, 作全年代理
    scenC = float(np.mean(ratios)) * ann26
    print("    情景C(同年比例): 10-11月/全年 比例 2024=%.3f 2025=%.3f (均 %.3f) × 2026(1-9月) %.3f = **%.4f**"
          % (ratios[0], ratios[1], np.mean(ratios), ann26, scenC))

    sites, dates = {}, None
    for f in glob.glob(os.path.join(D_F, "*_seasonal_45d.json")):
        n = os.path.basename(f).replace("_seasonal_45d.json", "")
        d = json.load(open(f, encoding="utf-8"))["daily"]
        dates = pd.to_datetime(d["time"])
        sites[n] = {"sw": np.column_stack([d[f"shortwave_radiation_sum_member{k:02d}"] for k in range(1, 51)]),
                    "tx": np.column_stack([d[f"temperature_2m_max_member{k:02d}"] for k in range(1, 51)]),
                    "tn": np.column_stack([d[f"temperature_2m_min_member{k:02d}"] for k in range(1, 51)]),
                    "lat": json.load(open(f, encoding="utf-8"))["latitude"],
                    "lon": json.load(open(f, encoding="utf-8"))["longitude"]}
    names = list(sites)
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

    def clear_daily(lat, lon, ds):
        out = []
        for dt in ds:
            tt = pd.date_range(dt, dt + pd.Timedelta(days=1) - pd.Timedelta(minutes=5), freq="1h", tz="UTC")
            zen = pvlib.solarposition.get_solarposition(tt, lat, lon)["apparent_zenith"]
            out.append(np.nansum(pvlib.clearsky.haurwitz(zen)) * 3600 / 1e6)
        return np.array(out)

    tau = np.zeros((len(dates), 50))
    tm = np.zeros((len(dates), 50))
    for n, s in sites.items():
        c = clear_daily(s["lat"], s["lon"], dates)
        tau += w[n] * np.clip(s["sw"] / c[:, None], 0, 1)
        tm += w[n] * (s["tx"] + s["tn"]) / 2.0
    tau = np.clip(tau, 0, 1)
    h = g[g.year <= 2025].copy()
    k = (h.assign(tau_h=h["solar"] / h["pot_cs"]).groupby(h.index.dayofyear)["tau_h"].median()
         .reindex(np.unique(dates.dayofyear)).dropna().median() / np.median(tau))
    tau = np.clip(tau * k, 0, 1)
    print("    τ 尺度校正 k=%.3f" % k)

    n_m = tau.shape[1]
    cdd = np.clip(tm - 22.0, 0, None)
    hdd = np.clip(15.0 - tm, 0, None)
    we = (dates.weekday >= 5).astype(float)[:, None]
    tr_f = (np.asarray((dates - TAU0).days, float) / 365.25)[:, None]
    dow = pd.get_dummies(pd.Series(dates.dayofweek), prefix="d").values[:, 1:].astype(float)
    load_mw = (bop[0] + bop[1] * cdd + bop[2] * hdd + bop[3] * we + bop[4] * tr_f
               + (dow @ bop[5:11])[:, None])
    doy_f = dates.dayofyear.values
    harm_cols = []
    for i in range(HARM):
        harm_cols.append(np.sin(2 * np.pi * (i + 1) * doy_f / 365.25)[:, None])
        harm_cols.append(np.cos(2 * np.pi * (i + 1) * doy_f / 365.25)[:, None])
    harm_f = np.hstack(harm_cols)
    load_mw = load_mw + harm_f @ bop[11:].reshape(-1, 1)
    load_m = load_mw / 1000.0

    S_m = np.zeros_like(tau)
    for i, d0 in enumerate(doy_f):
        cc = g.groupby("doy")["pot_cs"].median().get(d0, np.nan)
        lc = (h.groupby([h.index.month, h.index.weekday >= 5])["load"]
              .median()).get((dates[i].month, dates[i].weekday() >= 5), np.nan)
        S_m[i] = cc * tau[i] / lc

    out = pd.DataFrame({"date": np.asarray(dates),
                        "tau_p50": np.percentile(tau, 50, axis=1),
                        "S_p50": np.percentile(S_m, 50, axis=1),
                        "load_p50": np.percentile(load_m, 50, axis=1)})
    for lab, (meta, pred, eta, cols, kind, d) in op.items():
        X = np.ones((len(dates) * n_m, 1))
        for c in cols:
            if c == "S":
                X = np.hstack([X, S_m.ravel()[:, None]])
            elif c == "load_gw":
                X = np.hstack([X, load_m.ravel()[:, None]])
            elif c == "trend":
                X = np.hstack([X, np.repeat(tr_f, n_m)[:, None]])
            elif c == "harm":
                X = np.hstack([X, np.repeat(harm_f, n_m, axis=0)])
        e = eta(X).reshape(len(dates), n_m)
        if kind == "logit":
            pr = sigmoid(e)
            pc = sigmoid(e - d)
            tag = "P" if "趋势+季节" not in lab else "Pseas"
            out[tag + "_mean"] = pr.mean(axis=1)
            out[tag + "_corr"] = pc.mean(axis=1)
            for q in (10, 50, 90):
                out["%s_c%d" % (tag, q)] = np.percentile(pc, q, axis=1)
        else:
            mu, muc = np.exp(e), np.exp(e - d)
            out["H_mean"] = mu.mean(axis=1)
            out["H_corr"] = muc.mean(axis=1)
            for q in (10, 50, 90):
                out["H_c%d" % q] = np.percentile(muc, q, axis=1)
    out["wk"] = np.arange(len(out)) // 7 + 1
    out.to_csv(OUT_OUT, index=False)
    wk = out.groupby("wk").agg(周起=("date", "first"), tau=("tau_p50", "median"), S=("S_p50", "median"),
                               load_GW=("load_p50", "median"),
                               P_raw=("P_mean", "mean"), P_corr=("P_corr", "mean"),
                               P10=("P_c10", "median"), P50=("P_c50", "median"), P90=("P_c90", "median"),
                               Pseas=("Pseas_mean", "mean"),
                               H_raw=("H_mean", "mean"), H_corr=("H_corr", "mean"))
    print("\n" + wk.round(3).to_string())
    print("    全窗: P(校正后) %.4f | P10 中位 %.4f | P90 中位 %.4f | P(含季节项, 未校正) %.4f"
          % (out["P_corr"].mean(), out["P_c10"].median(), out["P_c90"].median(), out["Pseas_mean"].mean()))
    print("    负价 h/日: 原始 %.3f → 偏移校正后 %.3f" % (out["H_mean"].mean(), out["H_corr"].mean()))
    print("    ★ 三情景对照(45 天窗口均值): A 趋势口径 %.3f | B 秋季残差口径 %.3f | C 同年比例口径 %.3f"
          % (out["P_mean"].mean(), out["P_corr"].mean(), scenC))
    print("      参照: PS-037 季节校正 0.068 | PS-035 0.082 | PS-037 原始 0.259")
    with open(os.path.join(D_S, "spain_negprice_v3_scenarios.csv"), "w", encoding="utf-8") as f:
        f.write("scenario,window_mean,note\n")
        f.write("A_trend,%.6f,模型原始输出(含趋势项)\n" % out["P_mean"].mean())
        f.write("B_autumn_resid,%.6f,按 2024-25 10-11 月残差平移\n" % out["P_corr"].mean())
        f.write("C_same_ratio,%.6f,10-11月/全年比例 × 2026(1-9月)年率\n" % scenC)
        f.write("PS-037_corrected,0.068000,PS-037 线性+概率域clip\n")
        f.write("PS-035,0.082000,PS-035 原式\n")
    print("\n→ %s\n→ %s\n→ %s\n→ %s" % (OUT_SK, OUT_SK23, OUT_REL, OUT_OUT))


def solve_offset_logit(eta, target):
    """解 d 使 mean(sigmoid(eta - d)) = target"""
    lo, hi = -30.0, 30.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if sigmoid(eta - mid).mean() > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


if __name__ == "__main__":
    main()
