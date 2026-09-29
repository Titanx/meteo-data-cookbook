# -*- coding: utf-8 -*-
"""补齐 ES 侧 NWP: D-1/D-3 西班牙负价日预警能不能建起来? —— PS-044

背景与动机:
  · PS-042/043 把"法国通道"在预报语境下证否(气候学与真实 NWP 均≈0 增益)。
  · 但 PS-042/043 的 **ES 侧特征全部是滞后/滚动量**(`noon_ratio_roll7` / `load_GWh_roll7`),
    即用**过去 7 天平均**代表**明天**的西班牙资源与负荷 —— 这本身是弱预报。
  · PS-043 §7-2 因此留下唯一尚未检验的路径: **补齐西班牙光伏区的 NWP 预报**,
    把 `noon_ratio` / `load_GWh` 也换成**预报量**, 建成"完全可运营"的 D-1/D-3 预警。

本流程回答三件事:
  ① 西班牙侧自身是否可预报? (NWP → 正午份额 / 负荷 / 正午负价小时)
  ② 把滞后/滚动量换成 D-1 预报量, 预警能否超过持续性骨架?
  ③ 关键判据 —— **"同期上界"**: 若把明天的 `noon_ratio`/`load_GWh` 换成**真实值**也不比
     持续性骨架好, 则任何"资源/负荷预报"通道都不可能有空间(与 PS-043 同一逻辑)。

设计要点:
  · 训练 = 2024-07~2025-12 (previous-runs 归档起点≈2024-07-01), 测试 = **2026 全年(从未参与训练)**;
    另做第二个样本外年: 训练 2024-07~2024-12 → 测试 **2025**。
  · 训练/测试输入类型一致(PS-042 §8-3); lead 同质性先行筛查(PF-015), 主分析只用 D1~D3。
  · 概率输出必须过**经验可靠性校准**(PS-042: 泊松 `1−exp(−λ)` 在零膨胀下高估约 2.5 倍)。
  · AUC 用秩基 Mann–Whitney(与 PS-041/042/043 同口径)。

输入:  data/spain/spain_nwp_panel.csv
输出:  data/spain/spain_nwp_{stage1,warning,oos2025,reliability,warn2026}.csv
用法:  python scripts/analysis/model_spain_nwp_warning.py
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")

SP = Path(r"c:\work\meteo\data\spain")
TRAIN_YEARS = (2024, 2025)       # 2024 仅含 07-12
TEST_YEAR = 2026
LEADS_MAIN = [1, 2, 3]
ES_PERSIST = ["is_weekend", "negh_lag1", "negh_roll7", "noon_ratio_roll7", "load_GWh_roll7"]
ES_CONTEMP = ["noon_ratio", "load_GWh"]


# ------------------------------------------------------------------ 工具
def design(df, cols, month_fe=False):
    X = df[cols].astype(float).copy()
    if month_fe:
        mm = df["month"].astype(int).values
        for k in range(2, 13):
            X["m_%d" % k] = (mm == k).astype(float)
    return sm.add_constant(X)


def fit_glm(df, cols, target, month_fe=False):
    return sm.GLM(df[target].astype(float).values, design(df, cols, month_fe),
                  family=sm.families.Poisson()).fit()


def pred(res, df, cols, month_fe=False):
    return np.asarray(res.predict(design(df, cols, month_fe)), dtype=float)


def fit_ols(a, cols, target):
    return sm.OLS(a[target].astype(float).values, design(a, cols)).fit()


def auc(y, score):
    yy, s = np.asarray(y, int), np.asarray(score, float)
    m = ~np.isnan(s)
    yy, s = yy[m], s[m]
    n1, n0 = int((yy == 1).sum()), int((yy == 0).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = pd.Series(s).rank().values
    return float((r[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def add_lags(df):
    for c in ["negh", "noon_ratio", "load_GWh", "fr_negh_noon", "share_day"]:
        if c not in df.columns:
            continue
        df[c + "_lag1"] = df[c].shift(1)
        for k in (3, 7):
            df["%s_roll%d" % (c, k)] = df[c].shift(1).rolling(k).mean()
    return df


def reliability(lam_tr, y_tr, lam_te, nb=8):
    """经验可靠性曲线: 训练集上按 λ 分位分箱 → 箱内实际 P(负价日) → 测试集线性插值"""
    d = pd.DataFrame({"lam": np.asarray(lam_tr, float), "y": np.asarray(y_tr, float)}).dropna()
    d["b"] = pd.qcut(d["lam"], nb, labels=False, duplicates="drop")
    g = d.groupby("b").agg(lam=("lam", "mean"), p=("y", "mean"), n=("y", "size"))
    x, y = g["lam"].values, g["p"].values
    o = np.argsort(x)
    x, y = x[o], y[o]
    p_te = np.interp(np.asarray(lam_te, float), x, y, left=y[0], right=y[-1])
    return g.reset_index(drop=True), p_te


# ------------------------------------------------------------------ 主流程
def main():
    raw = pd.read_csv(SP / "spain_nwp_panel.csv", parse_dates=["date"]).set_index("date").sort_index()
    raw["month"] = raw.index.month
    df = add_lags(raw.replace([np.inf, -np.inf], np.nan).copy())

    # ---- lead 同质性筛查(PF-015) ----
    m = df.dropna(subset=["es_ghi_obs"]).copy()
    m["period"] = np.where(m.index < "2025-05-01", "① 2024-07~2025-04", "② 2025-05~2026-09")
    lc = []
    for L in range(1, 8):
        c = "es_ghi_d%d" % L
        r = {"lead": "D%d" % L}
        for p, sub in m.groupby("period"):
            d = sub.dropna(subset=[c])
            r[p] = round(float((d[c] - d["es_ghi_obs"]).mean()), 1)
        d = m.dropna(subset=[c])
        r["MAE"] = round(float((d[c] - d["es_ghi_obs"]).abs().mean()), 1)
        r["corr"] = round(float(d[c].corr(d["es_ghi_obs"])), 4)
        lc.append(r)
    print("[① lead 同质性筛查: 西班牙正午 GHI 指数 vs ERA5, 分段偏差 (W/m²)]")
    lcq = pd.DataFrame(lc)
    lcq.to_csv(SP / "spain_nwp_leadcheck.csv", index=False)
    print(lcq.to_string(index=False))
    print("⇒ 主分析取 %s\n" % LEADS_MAIN)

    tr = df[df.index.year.isin(TRAIN_YEARS) & df["es_ghi_d1"].notna()].copy()
    te = df[df.index.year == TEST_YEAR].copy()
    print("主分析窗口: 训练 %d 日 (%s ~ %s) | 测试 %d 日 (%s ~ %s)\n"
          % (len(tr), tr.index.min().date(), tr.index.max().date(),
             len(te), te.index.min().date(), te.index.max().date()))

    # ============ A. 西班牙侧可预报性: NWP → 正午份额 / 负荷 / 正午负价h ============
    s1 = []
    for L in LEADS_MAIN:
        # A1 正午份额(noon_ratio): 天气 + 滚动水位 + 周末
        cols = ["es_ghi_d%d" % L, "es_t2m_d%d" % L, "noon_ratio_roll7", "is_weekend"]
        need = cols + ["noon_ratio"]
        a, b = tr.dropna(subset=need), te.dropna(subset=need)
        ra = fit_ols(a, cols, "noon_ratio")
        pa, pb = np.asarray(ra.predict(design(a, cols))), np.asarray(ra.predict(design(b, cols)))
        # 朴素基准: 直接用滚动水位当预报
        base_b = b["noon_ratio_roll7"].values
        s1.append({"目标": "正午份额 noon_ratio", "设定": "NWP D%d" % L, "n 训练/测试": "%d/%d" % (len(a), len(b)),
                   "训练 R²": round(float(ra.rsquared), 3),
                   "2026 MAE": round(float(np.abs(pb - b["noon_ratio"]).mean()), 4),
                   "2026 corr": round(float(pd.Series(pb).corr(pd.Series(b["noon_ratio"].values))), 3),
                   "滚动基准 2026 MAE": round(float(np.abs(base_b - b["noon_ratio"]).mean()), 4)})
        # A2 负荷(load_GWh): 温度 + 非线性 + 滚动水位 + 周末
        t2 = "es_t2m_d%d" % L
        for f in (tr, te):
            f["%s_sq" % t2] = (f[t2] - 15.0) ** 2
        cols2 = [t2, "%s_sq" % t2, "load_GWh_roll7", "is_weekend"]
        a2 = tr.dropna(subset=cols2 + ["load_GWh"])
        b2 = te.dropna(subset=cols2 + ["load_GWh"])
        ra2 = fit_ols(a2, cols2, "load_GWh")
        pa2, pb2 = np.asarray(ra2.predict(design(a2, cols2))), np.asarray(ra2.predict(design(b2, cols2)))
        s1.append({"目标": "负荷 load_GWh", "设定": "NWP D%d" % L, "n 训练/测试": "%d/%d" % (len(a2), len(b2)),
                   "训练 R²": round(float(ra2.rsquared), 3),
                   "2026 MAE": round(float(np.abs(pb2 - b2["load_GWh"]).mean()), 2),
                   "2026 corr": round(float(pd.Series(pb2).corr(pd.Series(b2["load_GWh"].values))), 3),
                   "滚动基准 2026 MAE": round(float(np.abs(b2["load_GWh_roll7"].values - b2["load_GWh"].values).mean()), 2)})
        # A3 正午负价小时(直接 Poisson)
        cols3 = ["es_ghi_d%d" % L, "es_t2m_d%d" % L, "negh_roll7", "is_weekend"]
        need3 = cols3 + ["negh_noon"]
        a3, b3 = tr.dropna(subset=need3), te.dropna(subset=need3)
        r3 = fit_glm(a3, cols3, "negh_noon")
        s1.append({"目标": "正午负价h negh_noon", "设定": "NWP D%d (Poisson)" % L,
                   "n 训练/测试": "%d/%d" % (len(a3), len(b3)),
                   "训练 R²": "-",
                   "2026 MAE": round(float(np.abs(pred(r3, b3, cols3) - b3["negh_noon"]).mean()), 3),
                   "2026 corr": round(float(pd.Series(pred(r3, b3, cols3)).corr(
                       pd.Series(b3["negh_noon"].values), method="spearman")), 3),
                   "滚动基准 2026 MAE": "-"})
    # 正午负价h 的 AUC(单独列)
    st1 = pd.DataFrame(s1)
    st1.to_csv(SP / "spain_nwp_stage1.csv", index=False)
    print("[② 西班牙侧可预报性: NWP 预报 → 正午份额 / 负荷 / 正午负价 h]")
    print(st1.to_string(index=False))

    neg_auc = []
    for L in LEADS_MAIN:
        cols3 = ["es_ghi_d%d" % L, "es_t2m_d%d" % L, "negh_roll7", "is_weekend"]
        a3, b3 = tr.dropna(subset=cols3 + ["negh_noon"]), te.dropna(subset=cols3 + ["negh_noon"])
        r3 = fit_glm(a3, cols3, "negh_noon")
        neg_auc.append({"设定": "西班牙 正午负价日 ~ NWP D%d + 滞后" % L,
                        "2026 AUC": round(auc(b3["negh_noon"] > 0, pred(r3, b3, cols3)), 3),
                        "参照: 仅滞后(A1 同族)": round(auc(
                            b3["negh_noon"] > 0, b3["negh_roll7"].values), 3)})
    print("\n[②b 西班牙正午负价日: NWP 的排序能力]")
    print(pd.DataFrame(neg_auc).to_string(index=False))

    # ============ B. D-1 预警: 把滚动基准换成预报量 ============
    # B1 生成"次日份额/负荷"的 D-N 预报量(拟合值), 训练/测试同法
    for L in LEADS_MAIN:
        cols = ["es_ghi_d%d" % L, "es_t2m_d%d" % L, "noon_ratio_roll7", "is_weekend"]
        a, b = tr.dropna(subset=cols + ["noon_ratio"]), te.dropna(subset=cols + ["noon_ratio"])
        r = fit_ols(a, cols, "noon_ratio")
        tr.loc[a.index, "fc_ratio_d%d" % L] = np.asarray(r.predict(design(a, cols)))
        te.loc[b.index, "fc_ratio_d%d" % L] = np.asarray(r.predict(design(b, cols)))

        t2 = "es_t2m_d%d" % L
        for f in (tr, te):
            f["%s_sq" % t2] = (f[t2] - 15.0) ** 2
        cols2 = [t2, "%s_sq" % t2, "load_GWh_roll7", "is_weekend"]
        a2 = tr.dropna(subset=cols2 + ["load_GWh", "fc_ratio_d%d" % L])
        b2 = te.dropna(subset=cols2 + ["load_GWh", "fc_ratio_d%d" % L])
        r2 = fit_ols(a2, cols2, "load_GWh")
        tr.loc[a2.index, "fc_load_d%d" % L] = np.asarray(r2.predict(design(a2, cols2)))
        te.loc[b2.index, "fc_load_d%d" % L] = np.asarray(r2.predict(design(b2, cols2)))

    # B2 预警设定
    stage = [
        ("W0 仅日历(月份FE+周末)", ES_PERSIST[:1], True),
        ("W1 持续性骨架 (ES 滞后/滚动) = PS-043 A1", ES_PERSIST, False),
        ("W2 W1 + ES 份额/负荷 D1 预报", ES_PERSIST + ["fc_ratio_d1", "fc_load_d1"], False),
        ("W2r W1 + **仅**份额 D1 预报", ES_PERSIST + ["fc_ratio_d1"], False),
        ("W2l W1 + **仅**负荷 D1 预报", ES_PERSIST + ["fc_load_d1"], False),
        ("W3 W1 + ES 份额/负荷 D3 预报", ES_PERSIST + ["fc_ratio_d3", "fc_load_d3"], False),
        ("W4 W1 + 原始 NWP(D1 光照+气温)", ES_PERSIST + ["es_ghi_d1", "es_t2m_d1"], False),
        ("W5 W1 + **同期实际**份额/负荷 (ES 侧上界)", ES_PERSIST + ES_CONTEMP, False),
        ("W6 W1 + **完美气象** ERA5 观测 (气象上界)", ES_PERSIST + ["es_ghi_obs", "es_t2m_obs"], False),
        ("W7 仅同期国内基本面 (= PS-043 B1)", ES_CONTEMP, False),
        ("W8 W1 + FR 同期负价h (参照 PS-041)", ES_PERSIST + ["fr_negh_noon"], False),
    ]
    rows = []
    for name, cols, mfe in stage:
        a = tr.dropna(subset=cols + ["negh", "negday"])
        b = te.dropna(subset=cols + ["negh", "negday"])
        if len(a) < 60 or len(b) < 60:
            print("  [跳过] %s (训练 %d / 测试 %d)" % (name, len(a), len(b)))
            continue
        res = fit_glm(a, cols, "negh", month_fe=mfe)
        la, lb = pred(res, a, cols, mfe), pred(res, b, cols, mfe)
        rows.append({"设定": name, "n 训练/测试": "%d/%d" % (len(a), len(b)),
                     "训练 AUC": round(auc(a["negday"], la), 3),
                     "**2026 AUC**": round(auc(b["negday"], lb), 3),
                     "2026 MAE_h": round(float(np.abs(lb - b["negh"]).mean()), 3),
                     "2026 偏差": round(float((lb - b["negh"]).mean()), 3)})
    warn = pd.DataFrame(rows)
    warn.to_csv(SP / "spain_nwp_warning.csv", index=False)
    print("\n[③ D-1/D-3 预警: 持续性骨架 vs 预报量 vs 上界 — 训练 → 2026]")
    print(warn.to_string(index=False))
    print("   判读: ①若 W5(同期实际)≈W1, 则任何'份额/负荷预报'通道都无空间;")
    print("         ②W2/W3 vs W1 给出 D-1 预报量相对滚动基准的真实增量;")
    print("         ③W6 是气象预报的完美版, 给出该通道的理论天花板。")

    # ============ C. 第二个样本外年: 训练 2024-07~2024-12 → 测试 2025 ============
    tr24 = df[(df.index >= "2024-07-01") & (df.index.year == 2024) & df["es_ghi_d1"].notna()].copy()
    te25 = df[df.index.year == 2025].copy()
    for L in LEADS_MAIN:
        cols = ["es_ghi_d%d" % L, "es_t2m_d%d" % L, "noon_ratio_roll7", "is_weekend"]
        a, b = tr24.dropna(subset=cols + ["noon_ratio"]), te25.dropna(subset=cols + ["noon_ratio"])
        r = fit_ols(a, cols, "noon_ratio")
        tr24.loc[a.index, "fc_ratio_d%d" % L] = np.asarray(r.predict(design(a, cols)))
        te25.loc[b.index, "fc_ratio_d%d" % L] = np.asarray(r.predict(design(b, cols)))
        t2 = "es_t2m_d%d" % L
        for f in (tr24, te25):
            f["%s_sq" % t2] = (f[t2] - 15.0) ** 2
        cols2 = [t2, "%s_sq" % t2, "load_GWh_roll7", "is_weekend"]
        a2 = tr24.dropna(subset=cols2 + ["load_GWh"])
        b2 = te25.dropna(subset=cols2 + ["load_GWh"])
        r2 = fit_ols(a2, cols2, "load_GWh")
        tr24.loc[a2.index, "fc_load_d%d" % L] = np.asarray(r2.predict(design(a2, cols2)))
        te25.loc[b2.index, "fc_load_d%d" % L] = np.asarray(r2.predict(design(b2, cols2)))
    rows2 = []
    for name, cols in [("W1 持续性骨架", ES_PERSIST),
                       ("W2 W1 + ES D1 预报", ES_PERSIST + ["fc_ratio_d1", "fc_load_d1"]),
                       ("W2r W1 + 仅份额 D1", ES_PERSIST + ["fc_ratio_d1"]),
                       ("W2l W1 + 仅负荷 D1", ES_PERSIST + ["fc_load_d1"]),
                       ("W3 W1 + ES D3 预报", ES_PERSIST + ["fc_ratio_d3", "fc_load_d3"]),
                       ("W5 W1 + 同期实际 (上界)", ES_PERSIST + ES_CONTEMP),
                       ("W6 W1 + 完美气象 (上界)", ES_PERSIST + ["es_ghi_obs", "es_t2m_obs"]),
                       ("W8 W1 + FR 同期负价h", ES_PERSIST + ["fr_negh_noon"])]:
        a = tr24.dropna(subset=cols + ["negh", "negday"])
        b = te25.dropna(subset=cols + ["negh", "negday"])
        if len(a) < 60:
            continue
        res = fit_glm(a, cols, "negh")
        la, lb = pred(res, a, cols), pred(res, b, cols)
        rows2.append({"设定(训练 2024-07~2024-12)": name, "训练日": len(a),
                      "训练 AUC": round(auc(a["negday"], la), 3),
                      "**2025 AUC**": round(auc(b["negday"], lb), 3),
                      "2025 MAE_h": round(float(np.abs(lb - b["negh"]).mean()), 3)})
    r2 = pd.DataFrame(rows2)
    r2.to_csv(SP / "spain_nwp_oos2025.csv", index=False)
    print("\n[④ 第二个样本外年: 训练 2024-07~2024-12 → 测试 2025]")
    print(r2.to_string(index=False))

    # ============ D. 概率校准 + 2026 预警日历(以 W1 持续性骨架为运营模型) ============
    a = tr.dropna(subset=ES_PERSIST + ["negh", "negday"])
    b = te.dropna(subset=ES_PERSIST + ["negh", "negday"])
    res = fit_glm(a, ES_PERSIST, "negh")
    la, lb = pred(res, a, ES_PERSIST), pred(res, b, ES_PERSIST)
    g, p_te = reliability(la, a["negday"].values, lb)
    b = b.assign(lam=lb, p_cal=p_te)
    naive = 1.0 - np.exp(-lb)
    br_cal = float(np.mean((p_te - b["negday"].values) ** 2))
    br_poi = float(np.mean((naive - b["negday"].values) ** 2))
    g.to_csv(SP / "spain_nwp_reliability.csv", index=False)
    print("\n[⑤ 概率校准(运营模型 W1 持续性骨架, 训练 2024-07~2025-12 → 2026)]")
    print("  泊松 1−exp(−λ) 均值 %.3f vs 校准后 %.3f vs 实际 %.3f"
          % (naive.mean(), p_te.mean(), b["negday"].mean()))
    print("  Brier: 泊松 %.4f vs 校准 %.4f  ⇒ %s"
          % (br_poi, br_cal, "校准更优" if br_cal < br_poi else "泊松更优"))
    print(g.round(3).to_string(index=False))

    cal = b[["lam", "p_cal", "negday", "negh", "noon_ratio", "load_GWh", "es_ghi_d1", "es_t2m_d1"]].copy()
    cal.index.name = "date"
    cal.sort_values("p_cal", ascending=False).to_csv(SP / "spain_nwp_warn2026.csv")
    top = cal.sort_values("p_cal", ascending=False).head(30)
    print("\n[⑥ 2026 预警日历: 校准概率最高的 30 日]")
    print("  命中率(前30日): %.1f%% (实际负价日 %d 日) vs 全期基准 %.1f%%"
          % (100 * top["negday"].mean(), int(top["negday"].sum()), 100 * b["negday"].mean()))
    print(top[["lam", "p_cal", "negday", "negh"]].round(3).to_string())
    print("\n→ 输出: %s" % SP)


if __name__ == "__main__":
    main()
