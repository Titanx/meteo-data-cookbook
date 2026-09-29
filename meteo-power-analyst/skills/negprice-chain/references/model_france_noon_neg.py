# -*- coding: utf-8 -*-
"""法国正午负价的可预报化 + 两阶段"区域过剩 → 西班牙负价"条件模型 —— PS-042

背景: PS-041 证明"法国同窗口负价小时数"是西班牙负价的**支配性预测量**
      (r=+0.620; 控国内份额后残差 +0.540; 泊松强度 AUC 0.808→0.903),
      但该变量当时是**同期观测**, 因此 PS-041 刻意没有给出新的秋季数字。
本流程: ①给 FR 侧建"正午负价小时"模型; ②把它换成**事前可算**的输入(留一年气候学),
      量化"可预报化"的技能损失; ③用两阶段模型产出 P(西班牙负价日 | 区域过剩);
      ④给出秋季 2026 的条件展望(两情景)。

方法要点:
  · 目标 = 当日正午窗口(当地 10-16h)的负价小时数 ∈ [0,6] ⇒ Poisson 对数链接
  · **AUC 用拟合/预测强度作分数**评估"是否为负价日"的排序能力
  · **留一年气候学 (leave-one-year-out)**: 当年某日的 FR 光伏/核电份额代理 = **其他年份**
    同 (月份, 是否周末) 均值 ⇒ 无同年度信息泄漏, 可作"事前"输入
  · 两阶段: FR 模型给 E[FR 负价h] → 作为 ES 模型的一个特征

输入:  data/spain/france_noon_panel.csv
输出:  data/spain/france_neg_{model,coef,forecast,frskill,twostage,oos,season}.csv
用法:  python scripts/analysis/model_france_noon_neg.py
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")

SP = Path(r"c:\work\meteo\data\spain")
CLIM_KEYS = ["month", "is_weekend"]
FR_FEATS = ["fr_noon_ratio", "fr_nuclear_ratio", "is_weekend"]


# ---------------------------------------------------------------- 工具
def design(df, cols, month_fe=False):
    X = df[cols].astype(float).copy()
    if month_fe:
        # 固定 11 个哑变量 (m_2..m_12, 基准=1 月) —— 不能依赖当帧出现的月份,
        # 否则"训练全 12 月 / 测试只有 1-9 月"时列数不一致 (PS-042 §8 陷阱)
        mm = df["month"].astype(int).values
        for k in range(2, 13):
            X["m_%d" % k] = (mm == k).astype(float)
    return sm.add_constant(X)


def fit_glm(df, cols, target, family="poisson", month_fe=False):
    fam = sm.families.Poisson() if family == "poisson" else sm.families.NegativeBinomial(alpha=1.0)
    return sm.GLM(df[target].astype(float).values, design(df, cols, month_fe), family=fam).fit()


def pred(res, df, cols, month_fe=False):
    return np.asarray(res.predict(design(df, cols, month_fe)), dtype=float)


def auc(y, score):
    """秩基 AUC (Mann–Whitney U), 与 PS-041 的口径一致(不依赖 sklearn)"""
    yy, s = np.asarray(y, int), np.asarray(score, float)
    m = ~np.isnan(s)
    yy, s = yy[m], s[m]
    n1, n0 = int((yy == 1).sum()), int((yy == 0).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = pd.Series(s).rank().values
    return float((r[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def disp(res):
    return float((res.resid_pearson ** 2).mean())


def clim_of(df, keys, cols):
    return df.groupby(keys)[cols].mean()


def map_clim(ref, idx_df, cols):
    """把 (月, 周末) 气候学表映射到目标日"""
    key = list(zip(idx_df["month"].astype(int), idx_df["is_weekend"].astype(int)))
    return pd.DataFrame({c: [ref[c].get(k, np.nan) for k in key] for c in cols}, index=idx_df.index)


def loo_clim_series(df, col):
    """留一年气候学(用于同面板内的"事前"代理)"""
    out = pd.Series(index=df.index, dtype=float)
    for y in sorted(df.index.year.unique()):
        ref = clim_of(df[df.index.year != y], CLIM_KEYS, [col])
        cur = df[df.index.year == y]
        out.loc[cur.index] = map_clim(ref, cur, [col])[col].values
    return out


# ---------------------------------------------------------------- 主流程
def main():
    df = pd.read_csv(SP / "france_noon_panel.csv", parse_dates=["date"]).set_index("date").sort_index()
    df["month"] = df.index.month
    df = df.replace([np.inf, -np.inf], np.nan)
    print("面板: %d 日 (%s ~ %s)" % (len(df), df.index.min().date(), df.index.max().date()))

    # 秋季情景的 ES 侧输入(PS-040 口径): 正午份额与负荷量级
    ES_AUTUMN_RATIO = 0.617          # 2025 年 10-11 月 52.7% × (2026/2025 正午光伏 1.198 ÷ 正午负荷 1.024)
    ES_AUTUMN_LOAD = 600.0           # GWh/日 (2025 年 10-11 月量级)

    # ============ A. FR 侧设定比较(同期特征 = "oracle" 上界) ============
    SPECS = {
        "F1 光伏份额": (["fr_noon_ratio"], False),
        "F2 +核电份额": (["fr_noon_ratio", "fr_nuclear_ratio"], False),
        "F3 +周末": (FR_FEATS, False),
        "F4 +月份FE": (FR_FEATS, True),
        "F5 总供给覆盖(核+光+风)/负荷": (["fr_vre_ratio", "is_weekend"], False),
        "F6 +剩余负荷占比": (["fr_noon_ratio", "fr_nuclear_ratio", "fr_resload_ratio", "is_weekend"], False),
    }
    rows, coef_rows = [], []
    for name, (cols, mfe) in SPECS.items():
        d = df.dropna(subset=cols + ["fr_negh_noon"]).copy()
        res = fit_glm(d, cols, "fr_negh_noon", month_fe=mfe)
        lam = pred(res, d, cols, mfe)
        rows.append({"设定": name, "k": int(res.df_model + 1), "n": len(d),
                     "AIC": round(res.aic, 1), "离散度": round(disp(res), 2),
                     "MAE_h": round(float(np.abs(lam - d["fr_negh_noon"]).mean()), 3),
                     "AUC_负价日": round(auc(d["fr_negh_noon"] > 0, lam), 3)})
        Xd = design(d, cols, mfe)
        for nm, b, t in zip(Xd.columns, res.params, res.tvalues):
            coef_rows.append({"设定": name, "term": nm, "coef": round(float(b), 4), "t": round(float(t), 2)})
    mod = pd.DataFrame(rows)
    mod.to_csv(SP / "france_neg_model.csv", index=False)
    pd.DataFrame(coef_rows).to_csv(SP / "france_neg_coef.csv", index=False)
    print("\n[FR 正午负价小时 · Poisson 设定比较 (同期特征)]")
    print(mod.to_string(index=False))

    # ============ B. FR 侧技能: 同期特征 vs 事前(留一年气候学) ============
    df["fr_noon_ratio_clim"] = loo_clim_series(df, "fr_noon_ratio")
    df["fr_nuclear_ratio_clim"] = loo_clim_series(df, "fr_nuclear_ratio")

    d = df.dropna(subset=FR_FEATS + ["fr_negh_noon"]).copy()
    res_fr = fit_glm(d, FR_FEATS, "fr_negh_noon")
    lam_oracle = pred(res_fr, d, FR_FEATS)

    dc = d.dropna(subset=["fr_noon_ratio_clim", "fr_nuclear_ratio_clim"]).copy()
    dc["fr_noon_ratio"] = dc["fr_noon_ratio_clim"]
    dc["fr_nuclear_ratio"] = dc["fr_nuclear_ratio_clim"]
    lam_clim = pred(res_fr, dc, FR_FEATS)

    skill = pd.DataFrame([
        {"FR 输入": "同期特征(上界)", "n": len(d), "MAE_h": round(float(np.abs(lam_oracle - d["fr_negh_noon"]).mean()), 3),
         "Spearman(强度)": round(float(pd.Series(lam_oracle).corr(pd.Series(d["fr_negh_noon"].values), method="spearman")), 3),
         "AUC_负价日": round(auc(d["fr_negh_noon"] > 0, lam_oracle), 3)},
        {"FR 输入": "留一年气候学(事前)", "n": len(dc), "MAE_h": round(float(np.abs(lam_clim - dc["fr_negh_noon"]).mean()), 3),
         "Spearman(强度)": round(float(pd.Series(lam_clim).corr(pd.Series(dc["fr_negh_noon"].values), method="spearman")), 3),
         "AUC_负价日": round(auc(dc["fr_negh_noon"] > 0, lam_clim), 3)},
    ])
    skill.to_csv(SP / "france_neg_frskill.csv", index=False)
    print("\n[FR 侧技能: 可预报化的代价]")
    print(skill.to_string(index=False))

    df["lam_fr_clim"] = np.nan
    df.loc[dc.index, "lam_fr_clim"] = lam_clim
    fc = df[["fr_negh_noon", "lam_fr_clim", "fr_noon_ratio", "fr_noon_ratio_clim",
             "fr_nuclear_ratio", "noon_ratio", "load_GWh", "negh", "negday"]].copy()
    fc.index.name = "date"
    fc.to_csv(SP / "france_neg_forecast.csv")

    # ============ C. 两阶段: ES 负价 ← 国内 + FR 通道 ============
    ES_BASE = ["noon_ratio", "load_GWh"]
    stage = [
        ("S2 仅国内(PS-041 基线)", ES_BASE, None),
        ("T1 +FR **观测**负价h(上界, 需同期观测)", ES_BASE, "fr_negh_noon"),
        ("T2 +FR **事前**强度 λ", ES_BASE, "lam_fr_clim"),
        ("T3 T2+FR 事前光伏份额", ES_BASE + ["fr_noon_ratio_clim"], "lam_fr_clim"),
    ]
    ts = []
    for name, cols, extra in stage:
        use = list(cols) + ([] if extra is None else [extra])
        dd = df.dropna(subset=use + ["negh", "negday"]).copy()
        res = fit_glm(dd, use, "negh")
        lam = pred(res, dd, use)
        ts.append({"设定": name, "变量数": len(use), "n": len(dd),
                   "AIC": round(res.aic, 1),
                   "AUC(ES 负价日)": round(auc(dd["negday"], lam), 3),
                   "MAE(ES 负价h)": round(float(np.abs(lam - dd["negh"]).mean()), 3),
                   "偏差": round(float((lam - dd["negh"]).mean()), 3)})
    two = pd.DataFrame(ts)
    two.to_csv(SP / "france_neg_twostage.csv", index=False)
    print("\n[两阶段: ES 负价日 ← 国内 + FR 通道 (全样本)]")
    print(two.to_string(index=False))

    # ============ D. 样本外(训练 ≤Y-1 → 测试 Y) ============
    # 关键: 训练集与测试集的 FR 通道输入必须**同为事前量** ——
    #   训练年内用留一年气候学, 测试年用**仅训练年**的气候学(无任何测试年信息)
    oos = []
    for Y in (2025, 2026):
        tr = df[df.index.year < Y].copy()
        te = df[df.index.year == Y].copy()
        tr["fr_noon_ratio_cl"] = loo_clim_series(tr, "fr_noon_ratio")
        tr["fr_nuclear_ratio_cl"] = loo_clim_series(tr, "fr_nuclear_ratio")
        ref = clim_of(tr, CLIM_KEYS, ["fr_noon_ratio", "fr_nuclear_ratio"])
        cm = map_clim(ref, te, ["fr_noon_ratio", "fr_nuclear_ratio"])
        te["fr_noon_ratio_cl"] = cm["fr_noon_ratio"].values
        te["fr_nuclear_ratio_cl"] = cm["fr_nuclear_ratio"].values

        # FR 模型只用"事前特征"拟合(与部署时一致)
        trc = tr.dropna(subset=FR_FEATS + ["fr_noon_ratio_cl", "fr_nuclear_ratio_cl", "fr_negh_noon"]).copy()
        for c in ["fr_noon_ratio", "fr_nuclear_ratio"]:
            trc[c] = trc[c + "_cl"]
        res_fr_tr = fit_glm(trc, FR_FEATS, "fr_negh_noon")

        def lam_of(frame):
            f = frame.copy()
            for c in ["fr_noon_ratio", "fr_nuclear_ratio"]:
                f[c] = f[c + "_cl"]
            return pred(res_fr_tr, f, FR_FEATS)

        tr["lam_fr"] = lam_of(tr)
        te["lam_fr"] = lam_of(te)

        for name, use_extra in [("S2 仅国内", None), ("T2 +FR 事前强度 λ", "lam_fr"),
                                ("T1 +FR 观测负价h(上界)", "fr_negh_noon")]:
            use = list(ES_BASE) + ([] if use_extra is None else [use_extra])
            a = tr.dropna(subset=use + ["negh"]).copy()
            b = te.dropna(subset=use + ["negh", "negday"]).copy()
            res = fit_glm(a, use, "negh")
            lam = pred(res, b, use)
            oos.append({"训练至": "<%d" % Y, "设定": name, "测试日": len(b),
                        "AUC": round(auc(b["negday"], lam), 3),
                        "MAE_h": round(float(np.abs(lam - b["negh"]).mean()), 3),
                        "偏差": round(float((lam - b["negh"]).mean()), 3)})
    oosdf = pd.DataFrame(oos)
    oosdf.to_csv(SP / "france_neg_oos.csv", index=False)
    print("\n[样本外]")
    print(oosdf.to_string(index=False))

    # ============ C. 事前可得变量库(滞后/滚动) —— 唯一能真正"事前"拿到的信息 ============
    # 关键词: 同期份额/负荷/价格在 D-1 都拿不到; 能拿到的只有**滞后与滚动**统计
    LAG_SRC = ["fr_negh_noon", "fr_noon_ratio", "fr_nuclear_ratio", "negh", "noon_ratio", "load_GWh"]
    for c in LAG_SRC:
        df[c + "_lag1"] = df[c].shift(1)
        for k in (3, 7):
            df["%s_roll%d" % (c, k)] = df[c].shift(1).rolling(k).mean()

    PRE = {
        "P0 仅日历(月份FE+周末)": (["is_weekend"], True),
        "P1 +ES 滞后负价h": (["is_weekend", "negh_lag1", "negh_roll7"], True),
        "P2 +ES 滞后份额/负荷": (["is_weekend", "negh_lag1", "negh_roll7",
                                 "noon_ratio_roll7", "load_GWh_roll7"], True),
        "P3 +FR 滞后负价h": (["is_weekend", "negh_lag1", "negh_roll7", "noon_ratio_roll7",
                              "load_GWh_roll7", "fr_negh_noon_lag1", "fr_negh_noon_roll7"], True),
        "P4 +FR 基本面滚动(光伏/核电份额)": (["is_weekend", "negh_lag1", "negh_roll7", "noon_ratio_roll7",
                                             "load_GWh_roll7", "fr_negh_noon_lag1", "fr_negh_noon_roll7",
                                             "fr_noon_ratio_roll7", "fr_nuclear_ratio_roll7"], True),
    }
    pre_rows = []
    for name, (cols, mfe) in PRE.items():
        dd = df.dropna(subset=cols + ["negh", "negday"]).copy()
        res = fit_glm(dd, cols, "negh", month_fe=mfe)
        lam = pred(res, dd, cols, mfe)
        # 2026 样本外(训练 <2026)
        a = dd[dd.index.year < 2026]
        b = dd[dd.index.year == 2026]
        res_o = fit_glm(a, cols, "negh", month_fe=mfe)
        lam_o = pred(res_o, b, cols, mfe)
        pre_rows.append({"设定(全部为事前可得)": name, "变量数": len(cols) + (12 if mfe else 0),
                         "全样本 AUC": round(auc(dd["negday"], lam), 3),
                         "全样本 MAE_h": round(float(np.abs(lam - dd["negh"]).mean()), 3),
                         "2026 OOS AUC": round(auc(b["negday"], lam_o), 3),
                         "2026 OOS MAE_h": round(float(np.abs(lam_o - b["negh"]).mean()), 3)})
    pre = pd.DataFrame(pre_rows)
    pre.to_csv(SP / "france_neg_preexante.csv", index=False)
    print("\n[仅用**事前可得**变量的模型 (滞后/滚动; 同期量一律不入场)]")
    print(pre.to_string(index=False))
    print("    对照(非事前, 需同期观测): S2 仅国内 AUC 0.808 | T1 +FR 观测负价h AUC 0.891 | 2026 OOS 0.761 / 0.817")

    # ============ D. 概率转换的校准修正(泊松 1−exp(−λ) 严重高估) ============
    dd = df.dropna(subset=ES_BASE + ["fr_negh_noon", "negh", "negday"]).copy()
    res_cond = fit_glm(dd, ES_BASE + ["fr_negh_noon"], "negh")
    lam_cond = pred(res_cond, dd, ES_BASE + ["fr_negh_noon"])
    poi = 1 - np.exp(-lam_cond)
    dcal = pd.DataFrame({"lam": lam_cond, "y": dd["negday"].values})
    dcal["bin"] = pd.qcut(dcal["lam"], 8, duplicates="drop")
    rel = dcal.groupby("bin").agg(n=("y", "size"), lam=("lam", "mean"), obs=("y", "mean")).reset_index(drop=True)
    rel.to_csv(SP / "france_neg_reliability.csv", index=False)
    print("\n[概率转换校准: 泊松 1−exp(−λ) vs 经验可靠性曲线]")
    print("    样本均值: 泊松 %.3f vs 实际 %.3f  ⇒ 泊松口径**严重高估**(计数过散布+零膨胀)"
          % (poi.mean(), dd["negday"].mean()))
    print(rel.round(3).to_string(index=False))
    xk, yk = rel["lam"].values, rel["obs"].values
    P_CAL = lambda lam: float(np.clip(np.interp(lam, xk, yk), yk.min(), yk.max()))

    # ============ E. 条件结构表: P(ES 负价日 | ES 正午份额, FR 正午负价h) ============
    # (ES_AUTUMN_RATIO / ES_AUTUMN_LOAD 已在 main 开头定义)
    tab = []
    for frh in (0, 2, 4, 6):
        row = {"FR 正午负价h": frh}
        for sr in (0.45, 0.55, 0.65, 0.75):
            X = pd.DataFrame({"const": [1.0], "noon_ratio": [sr], "load_GWh": [ES_AUTUMN_LOAD],
                              "fr_negh_noon": [float(frh)]})[res_cond.model.exog_names]
            lam = float(res_cond.predict(X)[0])
            row["份额%.0f%%" % (100 * sr)] = round(P_CAL(lam), 3)
        tab.append(row)
    tabdf = pd.DataFrame(tab)
    tabdf.to_csv(SP / "france_neg_condtable.csv", index=False)
    print("\n[条件结构表 — 校准后 P(西班牙负价日 | 正午份额, FR 负价h)]  (负荷 600 GWh/日)")
    print(tabdf.to_string(index=False))

    # ============ F. 秋季 2026: 为什么**不**改用 FR 通道 ============
    hist = df[df["month"].isin([10, 11]) & (df.index.year < 2026)]
    base_r = float(hist["fr_noon_ratio"].mean())
    base_n = float(hist["fr_nuclear_ratio"].mean())
    r26 = float(df[(df.index.year == 2026) & (df["month"] <= 9)]["fr_noon_ratio"].mean())
    r25 = float(df[(df.index.year == 2025) & (df["month"] <= 9)]["fr_noon_ratio"].mean())
    trend = r26 / r25

    sea = []
    for nm, (rr, nn) in [("① FR 原始气候学(2023-25 秋季)", (base_r, base_n)),
                         ("② FR 按 2026 已实现份额趋势外推 (×%.3f)" % trend, (base_r * trend, base_n))]:
        Xf = pd.DataFrame({"const": [1.0], "fr_noon_ratio": [rr], "fr_nuclear_ratio": [nn],
                           "is_weekend": [0.0]})[res_fr.model.exog_names]
        lam_fr = float(res_fr.predict(Xf)[0])
        Xe = pd.DataFrame({"const": [1.0], "noon_ratio": [ES_AUTUMN_RATIO], "load_GWh": [ES_AUTUMN_LOAD],
                           "fr_negh_noon": [lam_fr]})[res_cond.model.exog_names]
        lam_es = float(res_cond.predict(Xe)[0])
        sea.append({"情景": nm, "FR 正午份额": round(rr, 4), "E[FR 负价h/日]": round(lam_fr, 2),
                    "E[ES 负价h/日]": round(lam_es, 2),
                    "泊松 P(负价日)": round(1 - np.exp(-lam_es), 3),
                    "校准后 P(负价日)": round(P_CAL(lam_es), 3)})
    # ③ 对照: 完全不带 FR 通道(等价于"只靠国内份额 + 负荷")
    X0 = pd.DataFrame({"const": [1.0], "noon_ratio": [ES_AUTUMN_RATIO], "load_GWh": [ES_AUTUMN_LOAD],
                       "fr_negh_noon": [0.0]})[res_cond.model.exog_names]
    lam0 = float(res_cond.predict(X0)[0])
    sea.append({"情景": "③ 对照: 不带 FR 通道(FR 负价h=0)", "FR 正午份额": np.nan, "E[FR 负价h/日]": 0.0,
                "E[ES 负价h/日]": round(lam0, 2),
                "泊松 P(负价日)": round(1 - np.exp(-lam0), 3),
                "校准后 P(负价日)": round(P_CAL(lam0), 3)})
    seas = pd.DataFrame(sea)
    seas.to_csv(SP / "france_neg_season.csv", index=False)
    print("\n[秋季 2026 — 走 FR 通道的情景(ES 正午份额固定 %.1f%%)]" % (100 * ES_AUTUMN_RATIO))
    print(seas.to_string(index=False))
    print("    ⚠ 该情景的 FR 输入是**气候学**(§C 已证其不带来增量技能) ⇒ 只作敏感性参照, 不作展望值")

    print("\n对照 — 秋季(10-11 月)实测基准:")
    for y in (2023, 2024, 2025):
        w = df[(df["month"].isin([10, 11])) & (df.index.year == y)]
        print("  %d: ES 负价日率 %5.1f%% | ES 正午份额 %4.1f%% | FR 正午负价h/日 %.2f | FR 正午份额 %4.1f%%"
              % (y, 100 * w["negday"].mean(), 100 * w["noon_ratio"].mean(),
                 w["fr_negh_noon"].mean(), 100 * w["fr_noon_ratio"].mean()))
    print("\n→ 输出目录: %s" % SP)


if __name__ == "__main__":
    main()
