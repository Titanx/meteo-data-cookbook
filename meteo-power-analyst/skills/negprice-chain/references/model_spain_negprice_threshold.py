# -*- coding: utf-8 -*-
"""西班牙负价"爆发阈值"模型 (PS-039)

动机(接 PS-038): 用 3 年线性趋势外推到秋季会给出 62% 的过冲, 且情景 A/B/C 相差 5 倍。
本流程改用 12 年(2015-2026)逐月面板, 以**光伏占需求的份额**(solar_share)为驱动, 检验"阈值/爆发"设定:
  ① 阈值从哪来: 2015-2023 负价小时恒为 0, 而光伏份额从 5% 单调升到 16.8% ⇒ 份额存在临界值
  ② 设定对比: 线性趋势(PS-038) vs 折线阈值(hockey-stick, θ 网格搜索) vs 障碍(hurdle) vs 含季节FE
  ③ 样本外: train ≤2023 / ≤2024 / ≤2025 → 预测后续年份的逐月负价小时, 比 MAE
输出: data/spain/spain_negprice_threshold.csv (面板+拟合), spain_negprice_threshold_fit.csv (设定对比)
用法: python scripts/analysis/model_spain_negprice_threshold.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
PANEL = os.path.join(D, "spain_long_panel.csv")
OUT_P = os.path.join(D, "spain_negprice_threshold.csv")
OUT_F = os.path.join(D, "spain_negprice_threshold_fit.csv")


def auc(score, label):
    s, y = np.asarray(score, float), np.asarray(label, float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def fit_threshold(df, ycol, share_col="solar_share", tmin=0.0):
    """折线阈值: y = a + b * max(0, share - θ); θ 网格搜索最小化 SSE, 要求超阈值点 >= 8"""
    best = None
    X0 = df[share_col].values
    Y = df[ycol].values
    grid = np.arange(max(tmin, 0.02), 0.42, 0.005)
    for th in grid:
        k = np.maximum(0.0, X0 - th)
        if (k > 0).sum() < 8:
            continue
        A = np.column_stack([np.ones(len(k)), k])
        b, *_ = np.linalg.lstsq(A, Y, rcond=None)
        res = Y - A @ b
        sse = float(res @ res)
        if best is None or sse < best[0]:
            best = (sse, th, b)
    if best is None:
        return None
    sse, th, b = best
    ss = float(((Y - Y.mean()) ** 2).sum())
    return {"theta": th, "a": b[0], "b": b[1], "r2": 1 - sse / ss if ss else np.nan}


def predict_threshold(df, fit, share_col="solar_share"):
    k = np.maximum(0.0, df[share_col].values - fit["theta"])
    return fit["a"] + fit["b"] * k


def month_fe(df):
    """固定 12 个月的哑变量(去掉 1 月), 保证 train/test 列一致"""
    d = pd.get_dummies(df["month"], prefix="m")
    for m in range(1, 13):
        if "m_%d" % m not in d.columns:
            d["m_%d" % m] = 0.0
    return d[["m_%d" % m for m in range(2, 13)]].values.astype(float)


def fit_linear_trend(df, ycol):
    X = df["trend"].values
    A = np.column_stack([np.ones(len(X)), X])
    b, *_ = np.linalg.lstsq(A, df[ycol].values, rcond=None)
    res = df[ycol].values - A @ b
    ss = float(((df[ycol].values - df[ycol].values.mean()) ** 2).sum())
    return {"a": b[0], "b": b[1], "r2": 1 - float(res @ res) / ss if ss else np.nan}


def main():
    p = pd.read_csv(PANEL)
    p = p[p["neg_h"].notna() & p["load_TWh"].notna() & p["solar_TWh"].notna()].copy()
    p["year"] = p["ym"].str[:4].astype(int)
    p["month"] = p["ym"].str[5:7].astype(int)
    p["trend"] = (p["year"] - 2015) + (p["month"] - 1) / 12.0
    p["solar_share"] = p["solar_TWh"] / p["load_TWh"]
    p["negday_rate"] = np.nan
    print("面板 %d 月 (%s ~ %s), 缺负荷月已剔除" % (len(p), p["ym"].min(), p["ym"].max()))

    print()
    print("=" * 96)
    print("① 逐月面板: 光伏占需求份额 vs 负价小时")
    print("=" * 96)
    piv_s = p.pivot_table(index="month", columns="year", values="solar_share") * 100
    piv_n = p.pivot_table(index="month", columns="year", values="neg_h")
    print("\n光伏占需求份额 (%):")
    print(piv_s.round(1).to_string())
    print("\n负价小时:")
    print(piv_n.to_string())
    print("\n[自检] 逐月光伏 TWh (2015 / 2020 / 2025):")
    print(p.pivot_table(index="month", columns="year", values="solar_TWh")[[2015, 2020, 2025]].round(2).to_string())

    print()
    print("=" * 96)
    print("② 设定对比 (全样本拟合, 目标 = 逐月负价小时)")
    print("=" * 96)
    fits = {}
    th = fit_threshold(p, "neg_h")
    lin = fit_linear_trend(p, "neg_h")
    fits["阈值(份额)"] = th
    fits["线性趋势"] = lin
    pr = predict_threshold(p, th)
    p["pred_threshold"] = pr
    p["pred_trend"] = lin["a"] + lin["b"] * p["trend"]
    mae_th = float(np.abs(p["neg_h"] - p["pred_threshold"]).mean())
    mae_li = float(np.abs(p["neg_h"] - p["pred_trend"]).mean())
    print("  阈值(hockey-stick): θ = %.3f (光伏份额 %.1f%%) | a=%.1f b=%.1f | R²=%.3f | 全样本 MAE=%.1f h/月"
          % (th["theta"], th["theta"] * 100, th["a"], th["b"], th["r2"], mae_th))
    print("  线性趋势          : a=%.1f b=%.1f  | R²=%.3f | 全样本 MAE=%.1f h/月"
          % (lin["a"], lin["b"], lin["r2"], mae_li))

    # 含月份 FE 的阈值模型
    A = np.column_stack([np.maximum(0, p["solar_share"] - th["theta"]), month_fe(p)])
    b2, *_ = np.linalg.lstsq(A, p["neg_h"].values, rcond=None)
    res = p["neg_h"].values - A @ b2
    ss = float(((p["neg_h"].values - p["neg_h"].values.mean()) ** 2).sum())
    r2_fe = 1 - float(res @ res) / ss
    p["pred_thr_mfe"] = A @ b2
    print("  阈值+月份FE       : 斜率=%.1f | R²=%.3f | MAE=%.1f h/月"
          % (b2[0], r2_fe, float(np.abs(res).mean())))

    print()
    print("=" * 96)
    print("③ 样本外: 逐年扩展窗口 → 预测后续年份逐月负价小时 (MAE, h/月)")
    print("=" * 96)
    print("  %-14s %-14s %-14s %-14s" % ("训练至", "阈值模型", "线性趋势", "阈值+月份FE"))
    rows_f = []
    for ty in (2023, 2024, 2025):
        tr, te = p[p["year"] <= ty], p[p["year"] > ty]
        if len(te) == 0 or len(tr) < 24:
            continue
        f1 = fit_threshold(tr, "neg_h")
        f2 = fit_linear_trend(tr, "neg_h")
        A2 = np.column_stack([np.maximum(0, tr["solar_share"] - f1["theta"]), month_fe(tr)])
        b3, *_ = np.linalg.lstsq(A2, tr["neg_h"].values, rcond=None)
        A2t = np.column_stack([np.maximum(0, te["solar_share"] - f1["theta"]), month_fe(te)])
        m1 = float(np.abs(te["neg_h"] - predict_threshold(te, f1)).mean())
        m2 = float(np.abs(te["neg_h"] - (f2["a"] + f2["b"] * te["trend"])).mean())
        m3 = float(np.abs(te["neg_h"] - A2t @ b3).mean())
        # 均值偏差(水位)
        d1 = float(predict_threshold(te, f1).mean() - te["neg_h"].mean())
        d2 = float((f2["a"] + f2["b"] * te["trend"]).mean() - te["neg_h"].mean())
        print("  ≤%d (%2d月)   MAE %5.1f (偏差%+6.1f)  MAE %5.1f (偏差%+6.1f)  MAE %5.1f"
              % (ty, len(te), m1, d1, m2, d2, m3))
        rows_f.append({"train_to": ty, "n_test": len(te), "theta_train": f1["theta"],
                       "mae_threshold": m1, "bias_threshold": d1,
                       "mae_trend": m2, "bias_trend": d2, "mae_thr_mfe": m3})

    print()
    print("=" * 96)
    print("④ 关键量: 各年 4-5 月(春季高发)与 10-11 月(秋季)的光伏份额与负价小时")
    print("=" * 96)
    for lab, mm in (("春季 4-5月", [4, 5]), ("秋季 10-11月", [10, 11])):
        s = p[p["month"].isin(mm)].groupby("year").agg(
            份额=("solar_share", "mean"), 负价h=("neg_h", "mean"),
            月数=("neg_h", "size")) 
        s["份额%"] = (s["份额"] * 100).round(1)
        print("\n%s:" % lab)
        print(s[["月数", "份额%", "负价h"]].round(1).to_string())

    p.to_csv(OUT_P, index=False)
    pd.DataFrame(rows_f).to_csv(OUT_F, index=False)

    print()
    print("=" * 96)
    print("⑤ 秋季 2026 外推: 份额 → 预期负价小时 → 负价日率")
    print("=" * 96)
    AUT = [10, 11]
    s25 = p[(p.year == 2025) & p.month.isin(AUT)]
    j25 = p[(p.year == 2025) & (p.month <= 9)]
    j26 = p[(p.year == 2026) & (p.month <= 9)]
    sol_g = j26["solar_TWh"].sum() / j25["solar_TWh"].sum()
    lo_g = j26["load_TWh"].sum() / j25["load_TWh"].sum()
    share25 = s25["solar_TWh"].sum() / s25["load_TWh"].sum()
    share26 = share25 * sol_g / lo_g
    print("  基准 2025 年 10-11 月: 光伏 %.1f TWh / 负荷 %.1f TWh ⇒ 份额 %.1f%% (实测负价 %.0f h/月)"
          % (s25["solar_TWh"].sum(), s25["load_TWh"].sum(), share25 * 100, s25["neg_h"].mean()))
    print("  2026 相对 2025 的 1-9 月: 光伏 ×%.3f, 负荷 ×%.3f (光伏增长快于负荷)"
          % (sol_g, lo_g))
    print("  ⇒ **2026 年 10-11 月份额外推 = %.1f%%**" % (share26 * 100))

    # 秋季专用阈值拟合(仅 10-11 月样本) + 全局阈值 + 月份FE
    aut = p[p.month.isin(AUT)]
    f_aut = fit_threshold(aut, "neg_h", tmin=0.0)
    print("\n  秋季(10-11月)专用阈值拟合: θ=%.3f | a=%.1f b=%.1f | R²=%.3f | n=%d"
          % (f_aut["theta"], f_aut["a"], f_aut["b"], f_aut["r2"], len(aut)))
    # 预测(用全局阈值与秋季阈值两种)
    row = pd.DataFrame([{"solar_share": share26}])
    pre_g = float(predict_threshold(row, th)[0])
    pre_a = float(predict_threshold(row, f_aut)[0])
    # 月份FE 模型(用全样本斜率, 取 10-11 月的月份截距均值)
    A = np.column_stack([np.maximum(0, p["solar_share"] - th["theta"]), month_fe(p)])
    b2, *_ = np.linalg.lstsq(A, p["neg_h"].values, rcond=None)
    base_aut = float(np.mean([b2[9], b2[10]]))     # 10月/11月 的月份效应(1月为基准, 索引0=2月)
    pre_fe = base_aut + b2[0] * max(0.0, share26 - th["theta"])
    print("  预期负价小时 (10-11 月平均, h/月): 全局阈值 %.1f | 秋季阈值 %.1f | 阈值+月份FE %.2f"
          % (pre_g, pre_a, pre_fe))
    print("  对照实测: 2024 = %.1f (份额 %.1f%%) | 2025 = %.1f (份额 %.1f%%)"
          % (p[(p.year == 2024) & p.month.isin(AUT)]["neg_h"].mean(),
             p[(p.year == 2024) & p.month.isin(AUT)]["solar_share"].mean() * 100,
             p[(p.year == 2025) & p.month.isin(AUT)]["neg_h"].mean(),
             p[(p.year == 2025) & p.month.isin(AUT)]["solar_share"].mean() * 100))
    # 换算负价日率: 用 2025 秋季实测的 天/h 比
    dly = pd.read_csv(os.path.join(D, "spain_official_daily.csv"), index_col=0, parse_dates=True)
    a25 = dly[(dly.index.year == 2025) & dly.index.month.isin(AUT)]
    a24 = dly[(dly.index.year == 2024) & dly.index.month.isin(AUT)]
    dph25 = a25["negday"].sum() / max(a25["negh"].sum(), 1e-9)
    dph24 = a24["negday"].sum() / max(a24["negh"].sum(), 1e-9)
    print("\n  实测换算系数 (负价日/负价小时): 2024 = %.3f, 2025 = %.3f" % (dph24, dph25))
    for lab, pre in (("全局阈值", pre_g), ("秋季阈值", pre_a), ("阈值+月份FE", pre_fe)):
        nd = pre * 2 * dph25          # 2 个月 ≈ 61 天
        print("    %-12s ⇒ 61 天预期负价日 %.1f 天 ⇒ **负价日率 %.1f%%**"
              % (lab, nd, nd / 61 * 100))

    print("\n  参照: PS-035 8.2% | PS-037 6.8% | PS-038 A趋势 62.0% / B秋季残差 21.4% / C同年比例 11.3%")
    print("\n→ %s\n→ %s" % (OUT_P, OUT_F))


if __name__ == "__main__":
    main()
