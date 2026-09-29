# -*- coding: utf-8 -*-
"""用真实 NWP 预报填法国侧: 短期(D-1~D-7)能否恢复区域通道的技能? —— PS-043

背景: PS-042 证明"用气候学把 FR 通道事前化"不带来增量技能(全样本 0.808→0.891→0.805;
2026 样本外 0.761→0.817→0.764)。本流程用**真实 NWP 预报**(ECMWF IFS previous-runs)
替换气候学, 在同一时间窗、同一口径下重做对比。

设计要点(避免四类常见偏误):
  1. **时间切分干净**: previous-runs 归档起点≈2024-07-01 ⇒ 主分析训练 = 2024-07~2025-12,
     测试 = **2026 全年(从未参与训练)**。
  2. **训练与测试的输入类型必须一致**(PS-042 §8-3): 气候学变体两侧都气候学; NWP 变体两侧都 NWP。
  3. **lead 同质性筛查先行**: previous-runs 的 D6/D7 在归档早段(2024-07~2025-04)偏差高达
     +37 / +143 W/m², 而 2025-05 起恢复正常 ⇒ 主分析只用 **D1~D3**;
     D5/D7 另在**同质窗**(训练 2025-05~2025-12)内评估。
  4. **年内标准化**: 法国负价频次的年度水位主要由装机增长决定、单靠天气不可预报,
     而 AUC 是**年内排序**指标 ⇒ FR 强度 λ 先做**年内 z-score** 再入 ES 模型(训练/测试同法);
     原始尺度结果一并给出作稳健性。

输入:  data/spain/france_nwp_panel.csv
输出:  data/spain/france_nwp_{leadcheck,frskill,twostage,homog}.csv
用法:  python skills/negprice-chain/references/model_france_nwp_forecast.py
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")

SP = Path(r"c:\work\meteo\data\spain")
CLIM_KEYS = ["month", "is_weekend"]
TRAIN_YEARS = (2024, 2025)      # 2024 仅含 07-12
TEST_YEAR = 2026
LEADS_MAIN = [1, 2, 3]          # 两段同质, 用于主分析
LEADS_HOM = [1, 3, 5, 7]        # 供同质窗(2025-05 起)评估
ES_EXANTE = ["is_weekend", "negh_lag1", "negh_roll7", "noon_ratio_roll7", "load_GWh_roll7"]
ES_CONTEMP = ["noon_ratio", "load_GWh"]
FR_NUC = "fr_nuclear_ratio_roll7"
HOM_START = "2025-05-01"


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


def auc(y, score):
    yy, s = np.asarray(y, int), np.asarray(score, float)
    m = ~np.isnan(s)
    yy, s = yy[m], s[m]
    n1, n0 = int((yy == 1).sum()), int((yy == 0).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = pd.Series(s).rank().values
    return float((r[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def zscore_by_year(s):
    out = pd.Series(index=s.index, dtype=float)
    for y in np.unique(s.index.year):
        m = s.index.year == y
        v = s[m]
        out[m] = (v - v.mean()) / v.std() if v.std() > 0 else 0.0
    return out


def add_lags(df):
    for c in ["negh", "noon_ratio", "load_GWh", "fr_negh_noon", "fr_noon_ratio", "fr_nuclear_ratio"]:
        if c not in df.columns:
            continue
        df[c + "_lag1"] = df[c].shift(1)
        for k in (3, 7):
            df["%s_roll%d" % (c, k)] = df[c].shift(1).rolling(k).mean()
    return df


def lead_quality(df):
    """逐 lead × 时期的正午 GHI 偏差, 用于判定归档同质性"""
    out = df.dropna(subset=["ghi_obs"]).copy()
    out["period"] = np.where(out.index < HOM_START, "① 2024-07~2025-04", "② 2025-05~2026-09")
    rows = []
    for L in range(1, 8):
        c = "ghi_d%d" % L
        if c not in out.columns:
            continue
        r = {"lead": "D%d" % L}
        for p, sub in out.groupby("period"):
            d = sub.dropna(subset=[c])
            r[p] = round(float((d[c] - d["ghi_obs"]).mean()), 1)
        d = out.dropna(subset=[c])
        r["MAE"] = round(float((d[c] - d["ghi_obs"]).abs().mean()), 1)
        r["corr"] = round(float(d[c].corr(d["ghi_obs"])), 4)
        rows.append(r)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 主流程
def main():
    raw = pd.read_csv(SP / "france_nwp_panel.csv", parse_dates=["date"]).set_index("date").sort_index()
    raw["month"] = raw.index.month
    df = add_lags(raw.replace([np.inf, -np.inf], np.nan).copy())

    lq = lead_quality(df)
    lq.to_csv(SP / "france_nwp_leadcheck.csv", index=False)
    print("[① lead 同质性筛查: 正午 GHI 指数 vs ERA5, 分段偏差 (W/m²)]")
    print(lq.to_string(index=False))
    print("⇒ 主分析取 %s (两段同质); D6/D7 仅在同质窗评估\n" % LEADS_MAIN)

    tr = df[df.index.year.isin(TRAIN_YEARS) & df["ghi_d1"].notna()].copy()
    te = df[df.index.year == TEST_YEAR].copy()
    print("主分析窗口: 训练 %d 日 (%s ~ %s) | 测试 %d 日 (%s ~ %s)\n"
          % (len(tr), tr.index.min().date(), tr.index.max().date(),
             len(te), te.index.min().date(), te.index.max().date()))

    # ================= A. 法国侧: 事前特征 → 法国正午负价 =================
    def fr_lams(tr_, te_, leads):
        """返回 {名字: (训练λ, 测试λ)} —— 均已在各自年份内 z-score"""
        out, rows = {}, []
        for name, cols, mfe in [("仅核+日历(无天气)", [FR_NUC, "is_weekend"], False)] + \
                [("NWP D%d 天气" % L, ["ghi_d%d" % L, "t2m_d%d" % L, FR_NUC, "is_weekend"], False)
                 for L in leads] + \
                [("NWP D1 +月份FE", ["ghi_d1", "t2m_d1", FR_NUC, "is_weekend"], True)]:
            need = cols + ["fr_negh_noon"]
            a, b = tr_.dropna(subset=need), te_.dropna(subset=need)
            res = fit_glm(a, cols, "fr_negh_noon", month_fe=mfe)
            la, lb = pred(res, a, cols, mfe), pred(res, b, cols, mfe)
            out["fr_" + name.replace(" ", "")] = (zscore_by_year(pd.Series(la, index=a.index)),
                                                  zscore_by_year(pd.Series(lb, index=b.index)))
            rows.append({"法国侧事前特征": name, "变量数": len(cols) + (11 if mfe else 0),
                         "训练 AUC": round(auc(a["fr_negh_noon"] > 0, la), 3),
                         "训练 MAE_h": round(float(np.abs(la - a["fr_negh_noon"]).mean()), 3),
                         "**2026 AUC**": round(auc(b["fr_negh_noon"] > 0, lb), 3),
                         "2026 MAE_h": round(float(np.abs(lb - b["fr_negh_noon"]).mean()), 3),
                         "2026 相关(Spearman)": round(float(pd.Series(lb).corr(
                             pd.Series(b["fr_negh_noon"].values), method="spearman")), 3)})
        return out, pd.DataFrame(rows)

    lam, fr = fr_lams(tr, te, LEADS_MAIN)

    # 气候学 λ(PS-042 口径): 训练年 (月份,周末) 均值份额 → 观测份额结构的 FR 模型
    clim = tr.groupby(CLIM_KEYS)[["fr_noon_ratio", "fr_nuclear_ratio"]].mean()
    a_obs = tr.dropna(subset=["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend", "fr_negh_noon"])
    res_obs = fit_glm(a_obs, ["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend"], "fr_negh_noon")

    def clim_lam(frame, ref):
        key = list(zip(frame["month"].astype(int), frame["is_weekend"].astype(int)))
        f = pd.DataFrame({"fr_noon_ratio": [ref["fr_noon_ratio"].get(k, np.nan) for k in key],
                          "fr_nuclear_ratio": [ref["fr_nuclear_ratio"].get(k, np.nan) for k in key],
                          "is_weekend": frame["is_weekend"].astype(float)}, index=frame.index).dropna()
        return pd.Series(pred(res_obs, f, ["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend"]), index=f.index)

    lam["fr_气候学"] = (zscore_by_year(clim_lam(tr, clim)), zscore_by_year(clim_lam(te, clim)))

    fr.to_csv(SP / "france_nwp_frskill.csv", index=False)
    print("[② 法国侧: 用 NWP 预报预测法国正午负价 (训练 → 2026)]")
    print(fr.to_string(index=False))

    for k, (va, vb) in lam.items():
        tr["lam_" + k] = va
        te["lam_" + k] = vb

    # ================= B. 两阶段: ES 负价 =================
    stage = [("A0 仅日历(月份FE+周末)", [], True),
             ("A1 +ES 滞后/滚动 (=PS-042 P2 特征, 无月份FE)", ES_EXANTE, False),
             ("A1m A1 +月份FE (与 PS-042 P2 完全同式)", ES_EXANTE, True),
             ("A2 A1 + FR λ(气候学, PS-042 口径)", ES_EXANTE + ["lam_fr_气候学"], False)]
    for L in LEADS_MAIN:
        stage.append(("A%d A1 + FR λ(NWP D%d)" % (2 + L, L), ES_EXANTE + ["lam_fr_NWPD%d天气" % L], False))
    stage.append(("A6 A1 + FR 观测负价h(同期, 上界)", ES_EXANTE + ["fr_negh_noon"], False))
    stage += [("B1 ES 同期(仅国内 = PS-041 S2)", ES_CONTEMP, False),
              ("B2 B1 + FR λ(气候学)", ES_CONTEMP + ["lam_fr_气候学"], False),
              ("B3 B1 + FR λ(NWP D1)", ES_CONTEMP + ["lam_fr_NWPD1天气"], False),
              ("B4 B1 + FR 观测负价h(上界)", ES_CONTEMP + ["fr_negh_noon"], False)]

    rows = []
    for name, cols, mfe in stage:
        use = [c for c in cols if c]
        a = tr.dropna(subset=use + ["negh", "negday"])
        b = te.dropna(subset=use + ["negh", "negday"])
        if len(a) < 60 or len(b) < 60:
            print("  [跳过] %s (训练 %d / 测试 %d)" % (name, len(a), len(b)))
            continue
        res = fit_glm(a, use, "negh", month_fe=mfe)
        la, lb = pred(res, a, use, mfe), pred(res, b, use, mfe)
        rows.append({"设定": name, "n 训练/测试": "%d/%d" % (len(a), len(b)),
                     "训练 AUC": round(auc(a["negday"], la), 3),
                     "**2026 AUC**": round(auc(b["negday"], lb), 3),
                     "2026 MAE_h": round(float(np.abs(lb - b["negh"]).mean()), 3),
                     "2026 偏差": round(float((lb - b["negh"]).mean()), 3)})
    # 与 PS-042 的同源可比性诊断: PS-042 的 P2(=ES_EXANTE+月份FE) 在训练 2023-2025 时 2026 AUC = 0.751。
    # 这里在同一特征式上换训练窗口, 用以判定"0.751 → 0.84x"的差异来自**训练窗口**而非特征。
    diag = []
    for tag, yrs in [("训练 2023-2025 (PS-042 窗口)", (2023, 2024, 2025)),
                     ("训练 2024-2025 (本流程窗口)", (2024, 2025))]:
        tw = df[df.index.year.isin(yrs)].copy()
        use = list(ES_EXANTE)
        a = tw.dropna(subset=use + ["negh", "negday"])
        b = te.dropna(subset=use + ["negh", "negday"])
        res = fit_glm(a, use, "negh", month_fe=True)
        la, lb = pred(res, a, use, True), pred(res, b, use, True)
        diag.append({"诊断(同一特征式: ES 滞后/滚动 + 月份FE)": tag,
                     "n 训练": len(a),
                     "训练 AUC": round(auc(a["negday"], la), 3),
                     "**2026 AUC**": round(auc(b["negday"], lb), 3),
                     "2026 MAE_h": round(float(np.abs(lb - b["negh"]).mean()), 3)})
    pd.DataFrame(diag).to_csv(SP / "france_nwp_trainwin.csv", index=False)
    two = pd.DataFrame(rows)
    two.to_csv(SP / "france_nwp_twostage.csv", index=False)
    print("\n[③ 两阶段: ES 负价 (A*=全事前可得; B*=ES 侧同期, 仅对照) — 训练 → 2026]")
    print(two.to_string(index=False))

    print("\n[③b 可比性诊断: 同一特征式(ES 滞后/滚动 + 月份FE), 只换训练窗口]")
    print(pd.DataFrame(diag).to_string(index=False))
    print("    ⇒ 换训练窗口只值 0.010 (0.751→0.761)。但把**月份FE**去掉(A1, 其余同式)后跳到 0.838 ——")
    print("      即 PS-042 的 P 系列基线(0.751/0.753)被 **11 个月份哑变量在短窗上的过拟合**压低了约 0.08 AUC;")
    print("      这与 PS-038「自由季节项在样本外过拟合」是同一现象, 只是发生在**日尺度**。")
    print("      后续都以**无月份FE**的 A1 = 0.838 作为「全事前可得」的正确基线。")

    # ================= C. 稳健性: λ 不做年内标准化 =================
    rows2 = []
    for L in LEADS_MAIN:
        cols = ["ghi_d%d" % L, "t2m_d%d" % L, FR_NUC, "is_weekend"]
        a, b = tr.dropna(subset=cols + ["fr_negh_noon"]), te.dropna(subset=cols + ["fr_negh_noon"])
        rfr = fit_glm(a, cols, "fr_negh_noon")
        ca = "lamraw_d%d" % L
        tr[ca] = np.nan
        te[ca] = np.nan
        tr.loc[a.index, ca] = pred(rfr, a, cols)
        te.loc[b.index, ca] = pred(rfr, b, cols)
        use = ES_EXANTE + [ca]
        aa, bb = tr.dropna(subset=use + ["negh", "negday"]), te.dropna(subset=use + ["negh", "negday"])
        res = fit_glm(aa, use, "negh")
        lb = pred(res, bb, use)
        rows2.append({"设定": "A%d′ A1 + FR λ(NWP D%d) 原始尺度(不标准化)" % (2 + L, L),
                      "**2026 AUC**": round(auc(bb["negday"], lb), 3),
                      "2026 MAE_h": round(float(np.abs(lb - bb["negh"]).mean()), 3)})
    r2 = pd.DataFrame(rows2)
    print("\n[④ 稳健性: λ 不做年内标准化(原始尺度)]")
    print(r2.to_string(index=False))

    # ================= D. 同质窗(2025-05 起)内评估到 D7 =================
    htr = df[(df.index >= HOM_START) & (df.index.year == 2025) & df["ghi_d1"].notna()].copy()
    lamh, frh = fr_lams(htr, te, LEADS_HOM)
    clith = htr.groupby(CLIM_KEYS)[["fr_noon_ratio", "fr_nuclear_ratio"]].mean()
    a_obsh = htr.dropna(subset=["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend", "fr_negh_noon"])
    res_obsh = fit_glm(a_obsh, ["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend"], "fr_negh_noon")

    def clim_lam2(frame, ref, resm):
        key = list(zip(frame["month"].astype(int), frame["is_weekend"].astype(int)))
        f = pd.DataFrame({"fr_noon_ratio": [ref["fr_noon_ratio"].get(k, np.nan) for k in key],
                          "fr_nuclear_ratio": [ref["fr_nuclear_ratio"].get(k, np.nan) for k in key],
                          "is_weekend": frame["is_weekend"].astype(float)}, index=frame.index).dropna()
        return pd.Series(pred(resm, f, ["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend"]), index=f.index)

    lamh["fr_气候学"] = (zscore_by_year(clim_lam2(htr, clith, res_obsh)),
                        zscore_by_year(clim_lam2(te, clith, res_obsh)))
    for k, (va, vb) in lamh.items():
        htr["lam_" + k] = va
        te["lam_" + k] = vb

    rows3 = []
    for name, cols, mfe in [("A1 +ES 滞后/滚动", ES_EXANTE, False),
                            ("A2 A1 + FR λ(气候学)", ES_EXANTE + ["lam_fr_气候学"], False)] + \
                           [("A%d A1 + FR λ(NWP D%d)" % (3 + L, L), ES_EXANTE + ["lam_fr_NWPD%d天气" % L], False)
                            for L in LEADS_HOM] + \
                           [("A9 A1 + FR 观测负价h(上界)", ES_EXANTE + ["fr_negh_noon"], False)]:
        a = htr.dropna(subset=cols + ["negh", "negday"])
        b = te.dropna(subset=cols + ["negh", "negday"])
        if len(a) < 60:
            continue
        res = fit_glm(a, cols, "negh", month_fe=mfe)
        la, lb = pred(res, a, cols, mfe), pred(res, b, cols, mfe)
        rows3.append({"设定(训练窗口 %s~2025-12)" % HOM_START: name, "训练日": len(a),
                      "训练 AUC": round(auc(a["negday"], la), 3),
                      "**2026 AUC**": round(auc(b["negday"], lb), 3),
                      "2026 MAE_h": round(float(np.abs(lb - b["negh"]).mean()), 3)})
    r3 = pd.DataFrame(rows3)
    r3.to_csv(SP / "france_nwp_homog.csv", index=False)
    print("\n[⑤ 同质窗(训练 %s ~ 2025-12)内评估到 D7 — 用短训练窗换取 lead 同质性]" % HOM_START)
    print(r3.to_string(index=False))

    # ================= E. 第二个样本外年: 训练 2024-07~2024-12 → 测试 2025 =================
    tr24 = df[(df.index >= "2024-07-01") & (df.index.year == 2024) & df["ghi_d1"].notna()].copy()
    te25 = df[df.index.year == 2025].copy()
    lam24, _ = fr_lams(tr24, te25, LEADS_MAIN)
    cl24 = tr24.groupby(CLIM_KEYS)[["fr_noon_ratio", "fr_nuclear_ratio"]].mean()
    a24 = tr24.dropna(subset=["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend", "fr_negh_noon"])
    r24 = fit_glm(a24, ["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend"], "fr_negh_noon")
    lam24["fr_气候学"] = (zscore_by_year(clim_lam2(tr24, cl24, r24)),
                         zscore_by_year(clim_lam2(te25, cl24, r24)))
    for k, (va, vb) in lam24.items():
        tr24["lam_" + k] = va
        te25["lam_" + k] = vb
    rows4 = []
    for name, cols in [("A1 +ES 滞后/滚动", ES_EXANTE),
                       ("A2 A1 + FR λ(气候学)", ES_EXANTE + ["lam_fr_气候学"]),
                       ("A3 A1 + FR λ(NWP D1)", ES_EXANTE + ["lam_fr_NWPD1天气"]),
                       ("A4 A1 + FR λ(NWP D2)", ES_EXANTE + ["lam_fr_NWPD2天气"]),
                       ("A5 A1 + FR λ(NWP D3)", ES_EXANTE + ["lam_fr_NWPD3天气"]),
                       ("A6 A1 + FR 观测负价h(上界)", ES_EXANTE + ["fr_negh_noon"])]:
        a = tr24.dropna(subset=cols + ["negh", "negday"])
        b = te25.dropna(subset=cols + ["negh", "negday"])
        if len(a) < 60:
            continue
        res = fit_glm(a, cols, "negh")
        la, lb = pred(res, a, cols), pred(res, b, cols)
        rows4.append({"设定(训练 2024-07~2024-12)": name, "训练日": len(a),
                      "训练 AUC": round(auc(a["negday"], la), 3),
                      "**2025 AUC**": round(auc(b["negday"], lb), 3),
                      "2025 MAE_h": round(float(np.abs(lb - b["negh"]).mean()), 3)})
    r4 = pd.DataFrame(rows4)
    r4.to_csv(SP / "france_nwp_oos2025.csv", index=False)
    print("\n[⑥ 第二个样本外年: 训练 2024-07~2024-12 → 测试 2025]")
    print(r4.to_string(index=False))
    print("\n→ 输出: %s" % SP)


if __name__ == "__main__":
    main()
