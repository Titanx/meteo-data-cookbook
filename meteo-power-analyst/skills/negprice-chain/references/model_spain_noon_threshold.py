# -*- coding: utf-8 -*-
"""西班牙负价: "正午份额" vs "月度份额" 阈值模型对比 (PS-040)

问题: PS-039 用**月度**光伏份额得到 θ=16% 的爆发阈值。但负价几乎只发生在正午,
      月度聚合把正午的过剩稀释掉了。本流程把驱动量换成**当地时间正午窗口
      (10-16h) 的光伏/负荷比**("正午份额"), 检验是否更贴合机制、并给出秋季 2026 外推。

设定(与 PS-039 保持同形, 只有驱动量不同, 保证可比):
  · 线性趋势      neg_h ~ a + b·t
  · 阈值/爆发     neg_h ~ a + b·max(0, share − θ)      θ 网格搜索(要求超阈值点 ≥ 8)
  · 阈值 + 月份FE 吸收季节形状
  · 季节专用阈值  仅用 4-5 月 / 10-11 月子样本拟合
评估: 全样本 MAE / R²; 逐年扩展窗口样本外 MAE(训练 ≤2023 / ≤2024 / ≤2025)

用法: python scripts/analysis/model_spain_noon_threshold.py
"""
import numpy as np
import pandas as pd

NOON = r"c:\work\meteo\data\spain\spain_noon_panel.csv"
OUT_P = r"c:\work\meteo\data\spain\spain_noon_threshold.csv"
OUT_F = r"c:\work\meteo\data\spain\spain_noon_threshold_fit.csv"

GRID = {
    "solar_share": (0.02, 0.42, 0.005),
    "noon_share_9_17": (0.05, 0.90, 0.01),
    "noon_share_10_16": (0.05, 0.90, 0.01),
    "noon_share_11_15": (0.05, 0.90, 0.01),
}
LABEL = {"solar_share": "月度份额(PS-039)",
         "noon_share_9_17": "正午份额 9-17h",
         "noon_share_10_16": "正午份额 10-16h",
         "noon_share_11_15": "正午份额 11-15h"}


def month_fe(df):
    """固定 12 个月虚拟变量(丢 1 月) —— 训练/测试列一致"""
    d = pd.get_dummies(df["month"], prefix="m")
    for m in range(1, 13):
        if "m_%d" % m not in d.columns:
            d["m_%d" % m] = 0.0
    return d[["m_%d" % m for m in range(2, 13)]].values.astype(float)


def lstsq(X, y):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return b


def fit_threshold(df, xcol, ycol="neg_h", grid=None, min_above=8):
    """网格搜索 θ, 拟合 neg_h ~ a + b·max(0, share−θ); 返回(θ, a, b, 拟合值)"""
    d = df[[xcol, ycol]].dropna()
    x, y = d[xcol].values, d[ycol].values
    lo, hi, st = grid or GRID[xcol]
    best = None
    for th in np.arange(lo, hi, st):
        z = np.maximum(0.0, x - th)
        if (z > 0).sum() < min_above:
            continue
        X = np.column_stack([np.ones_like(z), z])
        b = lstsq(X, y)
        sse = float(((y - X @ b) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, th, b)
    _, th, b = best
    d = d.assign(fit=b[0] + b[1] * np.maximum(0.0, d[xcol] - th))
    return th, float(b[0]), float(b[1]), d


def fit_fe(df, xcol, ycol="neg_h", min_above=8, grid=None):
    """阈值 + 月份固定效应（θ 同样网格搜索）"""
    d = df[[xcol, ycol, "month"]].dropna()
    lo, hi, st = grid or GRID[xcol]
    best = None
    for th in np.arange(lo, hi, st):
        z = np.maximum(0.0, d[xcol].values - th)
        if (z > 0).sum() < min_above:
            continue
        X = np.column_stack([np.ones_like(z), z, month_fe(d)])
        b = lstsq(X, d[ycol].values)
        sse = float(((d[ycol].values - X @ b) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, th, b)
    return best[1], best[2]


def fit_trend(df, ycol="neg_h"):
    d = df[[ycol, "t"]].dropna()
    X = np.column_stack([np.ones(len(d)), d["t"].values])
    b = lstsq(X, d[ycol].values)
    d = d.assign(fit=X @ b)
    return float(b[0]), float(b[1]), d


def r2mae(d, ycol="neg_h"):
    y, f = d[ycol].values, d["fit"].values
    r2 = 1 - ((y - f) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return r2, float(np.abs(y - f).mean())


def main():
    p = pd.read_csv(NOON).set_index("ym")
    p["month"] = [int(k[5:7]) for k in p.index]
    p["year"] = [int(k[:4]) for k in p.index]
    p["t"] = p.index.map(lambda k: (int(k[:4]) - 2015) * 12 + int(k[5:7]) - 1)
    p = p.sort_index().reset_index()
    print("面板 %d 月 (%s ~ %s)" % (len(p), p.ym.iloc[0], p.ym.iloc[-1]))

    # ---------------- ① 设定比较 ----------------
    print("\n" + "=" * 96)
    print("① 设定比较（全样本, 目标 = 逐月负价小时）")
    print("=" * 96)
    res = []
    a0, b0, dt = fit_trend(p)
    r2, mae = r2mae(dt)
    res.append(("线性趋势", 2, np.nan, r2, mae, 0.0))
    print("  %-18s a=%7.2f b=%6.3f                      R²=%.3f MAE=%5.1f h/月"
          % ("线性趋势", a0, b0, r2, mae))

    for c in ["solar_share", "noon_share_9_17", "noon_share_10_16", "noon_share_11_15"]:
        th, a, b, d = fit_threshold(p, c)
        r2, mae = r2mae(d)
        th2, b2 = fit_fe(p, c)
        dfx = p[["neg_h", c, "month"]].dropna().copy()
        z = np.maximum(0.0, dfx[c].values - th2)
        X = np.column_stack([np.ones_like(z), z, month_fe(dfx)])
        dfx["fit"] = X @ b2
        r2f, maef = r2mae(dfx)
        res.append((LABEL[c], 3, th, r2, mae, 0.0))
        print("  %-18s θ=%6.1f%% a=%7.2f b=%7.1f  R²=%.3f MAE=%5.1f h/月"
              % (LABEL[c], th * 100, a, b, r2, mae))
        print("  %-18s θ=%6.1f%%(月FE)                 R²=%.3f MAE=%5.1f h/月"
              % ("  + 月份FE", th2 * 100, r2f, maef))

    # ---------------- ② 样本外 ----------------
    print("\n" + "=" * 96)
    print("② 样本外: 逐年扩展窗口 → 预测后续年份逐月负价小时 (MAE, h/月)")
    print("=" * 96)
    print("  %-14s %-26s %-26s %-26s %s" % ("训练至", "月度份额(PS-039)", "正午份额 10-16h",
                                             "正午份额 11-15h", "线性趋势"))
    rows = []
    for cut in (2023, 2024, 2025):
        tr = p[p.year <= cut]
        te = p[p.year > cut]
        cells, rec = [], {"train_to": cut, "n_test": int(len(te))}
        for c in ["solar_share", "noon_share_10_16", "noon_share_11_15"]:
            th, a, b = fit_threshold(tr, c)[:3]
            pr = a + b * np.maximum(0.0, te[c].values - th)
            m = (te["neg_h"].notna() & te[c].notna()).values
            mae = float(np.abs(te["neg_h"].values[m] - pr[m]).mean())
            bias = float((pr[m] - te["neg_h"].values[m]).mean())
            cells.append("MAE %5.1f (偏差 %+5.1f)" % (mae, bias))
            rec["mae_" + c] = mae
            rec["bias_" + c] = bias
            rec["theta_" + c] = th
        a0, b0, _ = fit_trend(tr)
        pr = a0 + b0 * te["t"].values
        mae = float(np.abs(te["neg_h"].values - pr).mean())
        bias = float((pr - te["neg_h"].values).mean())
        cells.append("MAE %5.1f (偏差 %+5.1f)" % (mae, bias))
        rec["mae_trend"], rec["bias_trend"] = mae, bias
        rows.append(rec)
        print("  ≤%-13d %-26s %-26s %-26s %s" % (cut, cells[0], cells[1], cells[2], cells[3]))
    pd.DataFrame(rows).to_csv(OUT_F, index=False)

    # ---------------- ③ 季节性阈值 ----------------
    print("\n" + "=" * 96)
    print("③ 季节专用阈值（正午份额 10-16h）")
    print("=" * 96)
    win = {"春季 4-5月": [4, 5], "秋季 10-11月": [10, 11]}
    seas = {}
    for lab, mm in win.items():
        sub = p[p.month.isin(mm)]
        th, a, b, d = fit_threshold(sub, "noon_share_10_16")
        r2, mae = r2mae(d)
        seas[lab] = (th, a, b, r2)
        print("  %-12s 正午θ=%6.1f%% a=%7.2f b=%7.1f  R²=%.3f MAE=%5.1f h/月 (n=%d)"
              % (lab, th * 100, a, b, r2, mae, len(d)))
    sub = p[p.month.isin([10, 11])]
    thm, am, bm, dm = fit_threshold(sub, "solar_share")
    print("  %-12s 月度θ=%6.1f%% (PS-039 口径)      R²=%.3f (n=%d)"
          % ("秋季 10-11月", thm * 100, r2mae(dm)[0], len(dm)))

    # 逐月正午份额表
    print("\n  4-5月 与 10-11月 的正午份额(10-16h, %):")
    for lab, mm in win.items():
        g = p[p.month.isin(mm)].groupby("year").agg(份额=("noon_share_10_16", lambda x: x.mean() * 100),
                                                    负价h=("neg_h", "sum"))
        print("   " + lab + ": " + " | ".join("%d %.1f/%.0f" % (y, r.份额, r.负价h)
                                              for y, r in g.iterrows() if y >= 2020))

    # ---------------- ④ 秋季 2026 外推 ----------------
    print("\n" + "=" * 96)
    print("④ 秋季 2026 外推（正午份额口径）")
    print("=" * 96)
    f25 = p[(p.year == 2025) & p.month.isin([10, 11])]
    j25 = p[(p.year == 2025) & (p.month <= 9)]
    j26 = p[(p.year == 2026) & (p.month <= 9)]
    for c, nm in [("noon_solar_TWh_10_16", "正午光伏"), ("noon_load_TWh_10_16", "正午负荷")]:
        r = j26[c].sum() / j25[c].sum()
        print("  2026/2025 的 1-9 月 %s: ×%.3f" % (nm, r))
    sg = j26["noon_solar_TWh_10_16"].sum() / j25["noon_solar_TWh_10_16"].sum()
    lg = j26["noon_load_TWh_10_16"].sum() / j25["noon_load_TWh_10_16"].sum()
    base = f25["noon_solar_TWh_10_16"].sum() / f25["noon_load_TWh_10_16"].sum()
    share26 = base * sg / lg
    print("  基准 2025 年 10-11 月正午份额 = %.1f%% (实测负价 %.1f h/月)"
          % (base * 100, f25["neg_h"].mean()))
    print("  ⇒ **2026 年 10-11 月正午份额外推 = %.1f%%**" % (share26 * 100))
    print("  参照: 2026 年 9 月实测正午份额 = %.1f%% | 2026 年 1-9 月均值 = %.1f%%"
          % (p.loc[p.ym == "2026-09", "noon_share_10_16"].values[0] * 100,
             j26["noon_share_10_16"].mean() * 100))

    glob_th, ga, gb = fit_threshold(p, "noon_share_10_16")[:3]
    ath, aa, ab = seas["秋季 10-11月"][0], seas["秋季 10-11月"][1], seas["秋季 10-11月"][2]
    # 负价日/负价小时 换算系数(用 2025 秋季实测)
    k25 = 0.19
    print("\n  全局正午θ=%.1f%%: 预期负价 %.1f h/月" % (glob_th * 100, ga + gb * max(0.0, share26 - glob_th)))
    print("  秋季正午θ=%.1f%%: 预期负价 %.1f h/月" % (ath * 100, aa + ab * max(0.0, share26 - ath)))
    for lab, th, a, b in [("全局正午阈值", glob_th, ga, gb), ("秋季正午阈值", ath, aa, ab)]:
        h = a + b * max(0.0, share26 - th)
        days = h * k25 * 2        # 61 天 / 2 个月 → 月均 h × 2 × (负价日/负价h)
        print("    %-12s ⇒ 61 天预期负价日 %.1f 天 ⇒ **负价日率 %.1f%%**" % (lab, days, days / 61 * 100))

    # ---------------- ⑤ 有界(饱和)设定 ----------------
    print("\n" + "=" * 96)
    print("⑤ 有界设定: 正午窗口(10-16h)负价小时**占比** ∈ [0,1] 的 logistic 拟合")
    print("=" * 96)
    import statsmodels.api as sm

    d = p[["noon_share_10_16", "neg_noon_h", "n_noon_h", "noon_neg_frac"]].dropna().copy()
    tot = float(p["neg_h"].sum())
    print("  样本 %d 月 | 窗口内负价小时 %d h / 全部负价小时 %d h = **%.0f%%**"
          % (len(d), d.neg_noon_h.sum(), tot, 100 * d.neg_noon_h.sum() / tot))
    yy = p[p["neg_h"].notna() & p["neg_noon_h"].notna()].copy()
    yy["year"] = [int(k[:4]) for k in yy["ym"]]
    g = yy.groupby("year").agg(负价h=("neg_h", "sum"), 窗口内h=("neg_noon_h", "sum"))
    g["窗口占比%"] = (g.窗口内h / g.负价h.replace(0, np.nan) * 100).round(0)
    print(g.tail(5).to_string())

    X = sm.add_constant(d["noon_share_10_16"].values)
    m = sm.GLM(d["noon_neg_frac"].values, X, family=sm.families.Binomial()).fit()
    print("\n  ① logistic:  logit(窗口负价占比) = %+.3f %+.3f · 正午份额   (伪R²=%.3f)"
          % (m.params[0], m.params[1], 1 - m.deviance / m.null_deviance))
    fit = m.predict(X) * d["n_noon_h"].values
    print("     窗口内负价小时 MAE = %.1f h/月 (实测均值 %.1f)"
          % (np.abs(fit - d["neg_noon_h"].values).mean(), d["neg_noon_h"].mean()))

    # 阈值-logistic: logit(frac) = a + b·max(0, share−θ)
    best = None
    for th in np.arange(0.05, 0.90, 0.01):
        z = np.maximum(0.0, d["noon_share_10_16"].values - th)
        if (z > 0).sum() < 8:
            continue
        mth = sm.GLM(d["noon_neg_frac"].values, np.column_stack([np.ones_like(z), z]),
                     family=sm.families.Binomial()).fit()
        if best is None or mth.deviance < best[0]:
            best = (mth.deviance, th, mth)
    _, thL, mL = best
    print("  ② 阈值-logistic: θ=%.1f%%  logit(frac) = %+.3f %+.3f·max(0,share−θ)  (伪R²=%.3f)"
          % (thL * 100, mL.params[0], mL.params[1], 1 - mL.deviance / mL.null_deviance))

    NW_H = 61 * 6                                     # 秋季 61 天 × 6 小时窗口
    print("\n  秋季 2026 外推（正午份额 %.1f%%）:" % (share26 * 100))
    for lab, f26 in [("① logistic", float(m.predict([[1.0, share26]])[0])),
                     ("② 阈值-logistic", float(mL.predict([[1.0, max(0.0, share26 - thL)]])[0]))]:
        wh = f26 * NW_H
        days = wh * k25
        print("    %-14s 窗口负价占比 %.1f%% ⇒ 窗口内负价 %.0f h ⇒ 负价日 %.1f 天 ⇒ **负价日率 %.1f%%**"
              % (lab, f26 * 100, wh, days, days / 61 * 100))

    # ---------------- 输出 ----------------
    out = p.copy()
    for c in ["solar_share", "noon_share_9_17", "noon_share_10_16", "noon_share_11_15"]:
        th, a, b, _ = fit_threshold(p, c)
        out["fit_" + c] = a + b * np.maximum(0.0, out[c] - th)
    out.to_csv(OUT_P, index=False)
    print("\n→ %s\n→ %s" % (OUT_P, OUT_F))


if __name__ == "__main__":
    main()
