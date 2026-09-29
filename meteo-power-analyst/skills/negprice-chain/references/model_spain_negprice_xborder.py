# -*- coding: utf-8 -*-
"""西班牙负价 · 跨境结构能否改善强度模型 (PS-041)

目标(日尺度): 当日负价小时数 negh (计数) / 当日是否有负价 negday (二值)
驱动: 正午份额 noon_ratio(当地10-16h 光伏/负荷)、负荷 load_GWh、
      **ES−FR 日前价差 spread_noon(正午窗口均值)**、**FR 中午价 fr_price_noon**、
      **净出口 netexp_noon(正午窗口均值, 正=出口; 泛边界合计, 由符号自检统一)**

设定(嵌套, 全部 Poisson 对数链接; 另有 NB 处理过度离散):
  S1 noon | S2 noon+load | S3 S2+价差 | S4 S2+净出口 | S5 S2+价差+净出口 | S6 S5+月份FE | S7 S2+FR价
评估: AIC / Pearson 离散度 / 逐日 MAE / 用 μ 作分数的 negday AUC
      样本外: 训练 ≤2024 → 2025; 训练 ≤2025 → 2026
机制: 高正午份额子样本内, 负价日率 按 价差/净出口 分位;
      negh ~ noon_ratio 的**残差** 对 价差/净出口 的回归(是否补充信息)

用法: python skills/negprice-chain/references/model_spain_negprice_xborder.py
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

D = r"c:\work\meteo\data\spain\spain_xborder_daily.csv"
OD = r"c:\work\meteo\data\spain"
OUT = OD + r"\spain_xborder_model.csv"
OUT_OOS = OD + r"\spain_xborder_oos.csv"
OUT_MECH = OD + r"\spain_xborder_mechanism.csv"
OUT_COEF = OD + r"\spain_xborder_coef.csv"


def auc(score, y):
    s, yy = np.asarray(score, float), np.asarray(y, int)
    m = ~np.isnan(s)
    s, yy = s[m], yy[m]
    n1, n0 = int((yy == 1).sum()), int((yy == 0).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    r = pd.Series(s).rank().values
    return (r[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def fe(df):
    d = pd.get_dummies(df["month"], prefix="m")
    for m in range(1, 13):
        if "m_%d" % m not in d.columns:
            d["m_%d" % m] = 0.0
    return d[["m_%d" % m for m in range(2, 13)]].values.astype(float)


SPECS = {
    "S1 noon": ["noon_ratio"],
    "S2 +负荷": ["noon_ratio", "load_GWh"],
    "S3 +价差": ["noon_ratio", "load_GWh", "spread_noon"],
    "S4 +净出口": ["noon_ratio", "load_GWh", "netexp_noon"],
    "S5 +价差+净出口": ["noon_ratio", "load_GWh", "spread_noon", "netexp_noon"],
    "S7 +FR中午价": ["noon_ratio", "load_GWh", "fr_price_noon"],
    "S7a +FR负价h": ["noon_ratio", "load_GWh", "fr_negh_noon"],
    "S8a +FR负价h+价差": ["noon_ratio", "load_GWh", "fr_negh_noon", "spread_noon"],
    "S8b +FR负价h+净出口": ["noon_ratio", "load_GWh", "fr_negh_noon", "netexp_noon"],
}


def design(df, cols, month_fe=False):
    X = df[cols].values.astype(float)
    X = np.column_stack([np.ones(len(X)), X])
    if month_fe:
        X = np.column_stack([X, fe(df)])
    return X


def fit_poisson(df, cols, month_fe=False):
    X = design(df, cols, month_fe)
    return sm.GLM(df["negh"].values, X, family=sm.families.Poisson()).fit()


def main():
    df = pd.read_csv(D, parse_dates=["date"]).set_index("date")
    need = ["negh", "noon_ratio", "load_GWh", "spread_noon", "netexp_noon",
            "fr_price_noon", "fr_negh_noon", "month"]
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=need).copy()
    print("日样本 %d 日 (%s ~ %s) | 负价日 %d | 负价h %d"
          % (len(df), df.index.min().date(), df.index.max().date(),
             int(df["negday"].sum()), int(df["negh"].sum())))

    # ---------- ① 简单相关 ----------
    print("\n" + "=" * 92)
    print("① 与当日负价小时的相关系数")
    for c in ["noon_ratio", "load_GWh", "spread_noon", "fr_price_noon",
              "fr_negh_noon", "netexp_noon"]:
        print("   %-14s r=%+.3f" % (c, df[c].corr(df["negh"])))

    # 负价日 vs 非负价日的均值对比
    print("\n   工作日均值对比:")
    t = df.groupby("negday").agg(日数=("negh", "size"), 午比=("noon_ratio", "mean"),
                                 负荷=("load_GWh", "mean"), 价差=("spread_noon", "mean"),
                                 FR价=("fr_price_noon", "mean"), FR负价h=("fr_negh_noon", "mean"),
                                 净出口=("netexp_noon", "mean"))
    t["午比"] = (t["午比"] * 100).round(1)
    print(t.round(2).to_string())

    # ---------- ② 嵌套设定(全样本) ----------
    print("\n" + "=" * 92)
    print("② 嵌套设定（全样本, Poisson 对数链接, 目标 = 当日负价小时）")
    print("   %-16s %6s %4s %8s %8s %8s" % ("设定", "AIC", "k", "离散度", "MAE", "AUC(negday)"))
    rows = []
    for lab, cols in SPECS.items():
        m = fit_poisson(df, cols)
        mu = m.predict()
        disp = float(((df["negh"] - mu) ** 2 / np.maximum(mu, 1e-9)).sum() / (len(df) - len(m.params)))
        rows.append({"spec": lab, "aic": m.aic, "k": len(m.params),
                     "disp": disp, "mae": float(np.abs(df["negh"] - mu).mean()),
                     "auc": auc(mu, df["negday"])})
        print("   %-16s %6.0f %4d %8.2f %8.2f %8.3f"
              % (lab, m.aic, len(m.params), disp, rows[-1]["mae"], rows[-1]["auc"]))
    m6 = fit_poisson(df, SPECS["S5 +价差+净出口"], month_fe=True)
    mu6 = m6.predict()
    d6 = float(((df["negh"] - mu6) ** 2 / np.maximum(mu6, 1e-9)).sum() / (len(df) - len(m6.params)))
    rows.append({"spec": "S6 S5+月份FE", "aic": m6.aic, "k": len(m6.params), "disp": d6,
                 "mae": float(np.abs(df["negh"] - mu6).mean()), "auc": auc(mu6, df["negday"])})
    print("   %-16s %6.0f %4d %8.2f %8.2f %8.3f"
          % ("S6 +月份FE", m6.aic, len(m6.params), d6, rows[-1]["mae"], rows[-1]["auc"]))

    # NB 对照(处理过度离散)
    try:
        mnb = sm.GLM(df["negh"].values, design(df, SPECS["S2 +负荷"]),
                     family=sm.families.NegativeBinomial(alpha=1.0)).fit()
        print("   %-16s %6.0f %4d %8s %8.2f %8.3f"
              % ("S2b NB(α=1)", mnb.aic, len(mnb.params), "—",
                 float(np.abs(df["negh"] - mnb.predict()).mean()), auc(mnb.predict(), df["negday"])))
    except Exception as e:
        print("   NB 拟合失败: %s" % str(e)[:90])

    # 系数(主设定)
    m5 = fit_poisson(df, SPECS["S5 +价差+净出口"])
    coefs = []
    print("\n   S5 系数(值/标准误/t):")
    for nm, b, se, tv in zip(["const"] + SPECS["S5 +价差+净出口"], m5.params, m5.bse, m5.tvalues):
        print("     %-14s %+10.4f  se %7.4f  t %+6.2f" % (nm, b, se, tv))
        coefs.append({"term": nm, "coef": b, "se": se, "t": tv})
    pd.DataFrame(coefs).to_csv(OUT_COEF, index=False)
    pd.DataFrame(rows).to_csv(OUT, index=False)

    # ---------- ③ 样本外 ----------
    print("\n" + "=" * 92)
    print("③ 样本外：训练 ≤2024 → 2025；训练 ≤2025 → 2026")
    print("   %-14s %-16s %6s %8s %8s %8s" % ("训练", "设定", "测试日", "AUC", "MAE", "偏差"))
    oos = []
    for cut, te_year in ((2024, 2025), (2025, 2026)):
        tr = df[df["year"] <= cut]
        te = df[df["year"] == te_year]
        for lab in ["S2 +负荷", "S5 +价差+净出口", "S7 +FR中午价", "S7a +FR负价h",
                    "S8a +FR负价h+价差", "S8b +FR负价h+净出口"]:
            m = sm.GLM(tr["negh"].values, design(tr, SPECS[lab]),
                       family=sm.families.Poisson()).fit()
            mu = m.predict(design(te, SPECS[lab]))
            a = auc(mu, te["negday"])
            mae = float(np.abs(te["negh"].values - mu).mean())
            bias = float((mu - te["negh"].values).mean())
            oos.append({"train_to": cut, "spec": lab, "n_test": len(te), "auc": a,
                        "mae": mae, "bias": bias})
            print("   ≤%-13d %-16s %6d %8.3f %8.2f %+8.2f" % (cut, lab, len(te), a, mae, bias))
    pd.DataFrame(oos).to_csv(OUT_OOS, index=False)

    # ---------- ④ 机制: 高午比日内的价差/净出口分位 ----------
    print("\n" + "=" * 92)
    print("④ 机制：高正午份额日（上半）内，负价日率按价差 / 净出口 分位")
    hi = df[df["noon_ratio"] >= df["noon_ratio"].median()].copy()
    print("   子样本 %d 日 (午比中位 %.1f%%)" % (len(hi), hi["noon_ratio"].median() * 100))
    mech = []
    for c, lab in [("spread_noon", "ES−FR 价差 (€/MWh)"), ("netexp_noon", "净出口 (GW)"),
                   ("fr_negh_noon", "FR 窗口负价小时 (h)")]:
        hi["q"] = pd.qcut(hi[c], 5, labels=False, duplicates="drop")
        g = hi.groupby("q").agg(区间=("q", "size"), 下界=(c, "min"), 上界=(c, "max"),
                                负价日率=("negday", "mean"), 负价h均=("negh", "mean"))
        g["负价日率"] = (g["负价日率"] * 100).round(1)
        print("\n   %s:" % lab)
        print(g.round(2).to_string())
        for q, r in g.iterrows():
            mech.append({"var": c, "label": lab, "q": int(q), "n": int(r.区间),
                         "lo": r.下界, "hi": r.上界, "negday_rate": r.负价日率, "negh": r.负价h均})
    pd.DataFrame(mech).to_csv(OUT_MECH, index=False)

    # 负价日 vs 非负价日 均值对比(也落盘)
    t.reset_index().to_csv(OD + r"\spain_xborder_negday_means.csv", index=False)

    # 相关系数表
    cor = pd.DataFrame([{"var": c, "r": df[c].corr(df["negh"]),
                         "r_resid": float(np.corrcoef(
                             df["negh"].values - sm.GLM(
                                 df["negh"].values, sm.add_constant(df[["noon_ratio"]].values),
                                 family=sm.families.Poisson()).fit().predict(),
                             df[c].values)[0, 1])}
                        for c in ["noon_ratio", "load_GWh", "spread_noon",
                                  "fr_price_noon", "netexp_noon"]])
    cor.to_csv(OD + r"\spain_xborder_corr.csv", index=False)

    # ---------- ⑤ 增量信息: 残差回归 ----------
    print("\n" + "=" * 92)
    print("⑤ 增量信息：negh ~ noon_ratio 的残差 对 价差/净出口")
    X = sm.add_constant(df[["noon_ratio"]].values)
    base = sm.GLM(df["negh"].values, X, family=sm.families.Poisson()).fit()
    resid = df["negh"].values - base.predict()
    for c in ["spread_noon", "fr_price_noon", "fr_negh_noon", "netexp_noon", "load_GWh"]:
        r = np.corrcoef(resid, df[c].values)[0, 1]
        print("   corr(残差, %-14s) = %+.3f" % (c, r))

    print("\n→ %s\n→ %s\n→ %s\n→ %s" % (OUT, OUT_OOS, OUT_MECH, OUT_COEF))


if __name__ == "__main__":
    main()
