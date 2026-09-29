"""西班牙链路 · ENTSO-E 官方口径复核 + 2026 样本外检验 (PS-037)
动机: PS-036 拿到 ENTSO-E 官方 TSO 数据后, 回答两个问题:
      ① PS-030~035 用的 Energy-Charts 序列是否等于官方口径 (是否需要"换源重算")
      ② PS-035 的负价概率模型 (S 指数, 跨年 AUC 0.72) 在**从未见过的 2026** 上是否成立
链路: ENTSO-E 15min → 小时 → 逐日; S = clear_clim(doy) × τ / load_clim(月,周末), τ = act/pot_cs
      pot_cs 2023-2025 用 PS-031 实测值; 2026 用 2025 的 (doy,hour) 形状模板,
      尺度按 PS-031 同法(年能量比)标定 —— pot_cs ∝ 装机 × ILR, 跨年需重新定标否则 τ 会饱和到 1
输出: data/spain/spain_official_daily.csv, spain_official_quintile.csv, spain_official_yearly.csv
用法: python scripts/analysis/verify_spain_entsoe_official.py
"""
import os

import numpy as np
import pandas as pd

D_S = r"c:\work\meteo\data\spain"
OUT_DAILY = os.path.join(D_S, "spain_official_daily.csv")
OUT_Q = os.path.join(D_S, "spain_official_quintile.csv")
OUT_Y = os.path.join(D_S, "spain_official_yearly.csv")
YEARS = [2023, 2024, 2025, 2026]
ROWS_Y, ROWS_Q = [], []


def auc(score, label):
    s, y = np.asarray(score, float), np.asarray(label, float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    r = pd.Series(np.concatenate([pos, neg])).rank().values
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    print("=" * 80)
    print("[1] ENTSO-E 官方小时面板 + 2023-2025 实测 pot_cs")
    E = pd.read_csv(os.path.join(D_S, "spain_entsoe_hourly.csv"), index_col=0, parse_dates=True)
    print("    面板 %s, %s ~ %s" % (E.shape, E.index.min(), E.index.max()))

    pcs = []
    for y in (2023, 2024, 2025):
        x = pd.read_csv(os.path.join(D_S, f"spain_regime_hourly_{y}.csv"),
                        index_col=0, parse_dates=True)
        s = x["pot_cs"].copy()
        s.index = pd.to_datetime(s.index)
        pcs.append(s)
    PCS = pd.concat(pcs)
    print("    实测 pot_cs: %d 行 (%s ~ %s)" % (len(PCS), PCS.index.min(), PCS.index.max()))

    # ---- 逐日面板 ----
    d = pd.DataFrame(index=E.index)
    d["solar"], d["load"], d["price"] = E["e_solar"], E["e_load"], E["e_price"]
    d["negh"] = (E["e_price"] < 0).astype(float)
    d["pot_cs"] = PCS.reindex(E.index)

    # 2026 的 pot_cs: 用 2025 的 (doy,hour) 形状模板 + 年能量比定标
    tpl_src = PCS[PCS.index.year == 2025]
    tpl = tpl_src.groupby([tpl_src.index.dayofyear, tpl_src.index.hour]).median()
    m26 = d.index.year == 2026
    key26 = pd.MultiIndex.from_arrays([d.index[m26].dayofyear, d.index[m26].hour])
    tpl26 = tpl.reindex(key26).values
    hist_ratio = np.mean([PCS[PCS.index.year == y].sum() /
                          d[d.index.year == y]["solar"].sum() for y in (2023, 2024, 2025)])
    act26 = d.loc[m26, "solar"].sum()
    scale = hist_ratio * act26 / np.nansum(tpl26)
    d.loc[m26, "pot_cs"] = tpl26 * scale
    print("    2026 pot_cs: 形状模板=2025(doy,hour)中位 | 标定尺度 s=%.3f "
          "(使 pot_cs/act 年比 = 历史均值 %.4f)" % (scale, hist_ratio))

    # 近似自检: 模板形状 vs 2025 实测
    k25 = pd.MultiIndex.from_arrays([tpl_src.index.dayofyear, tpl_src.index.hour])
    a25 = tpl.reindex(k25).values
    v = tpl_src.notna().values & ~np.isnan(a25)
    print("    [自检] 模板 vs 2025 实测 pot_cs: r=%.4f, 能量比=%.4f"
          % (np.corrcoef(tpl_src.values[v], a25[v])[0, 1],
             tpl_src.values[v].sum() / a25[v].sum()))

    g = d.resample("D").agg({"solar": "sum", "pot_cs": "sum", "load": "mean",
                             "price": "mean", "negh": "sum"})
    g = g[g["solar"] > 1e3].copy()
    g["year"] = g.index.year
    g["negday"] = (g["negh"] > 0).astype(float)
    g["doy"] = g.index.dayofyear
    print("\n[2] 逐日面板: %d 天 (%s ~ %s)" % (len(g), g.index.min().date(), g.index.max().date()))
    print(g.groupby("year").agg(天=("solar", "size"), 负价日=("negday", "sum"),
                                负价日率=("negday", "mean"), 负价h=("negh", "sum"),
                                均价=("price", "mean")).round(3).to_string())

    # ---- S 指数 ----
    print("\n[3] S = clear_clim(doy) × τ / load_clim(月, 周末)   (气候量仅用 2023-2025)")
    h = g[g["year"] <= 2025]
    clear_clim = h.groupby("doy")["pot_cs"].median()
    load_clim = h.groupby([h.index.month, h.index.weekday >= 5])["load"].median()
    g["clear_clim"] = clear_clim.reindex(g["doy"]).values
    g["load_clim"] = load_clim.reindex(list(zip(g.index.month, g.index.weekday >= 5))).values
    g["tau"] = (g["solar"] / g["pot_cs"]).clip(0, 1)
    g["S"] = g["clear_clim"] * g["tau"] / g["load_clim"]
    g = g[g["S"].notna()]
    print("    τ 中位/年能量比: " + ", ".join(
        "%d %.3f/%.3f" % (y, g[g["year"] == y]["tau"].median(),
                          g[g["year"] == y]["pot_cs"].sum() / g[g["year"] == y]["solar"].sum())
        for y in YEARS))
    print("    S 中位: " + ", ".join("%d %.3f" % (y, g[g["year"] == y]["S"].median()) for y in YEARS))
    print("    τ 被截断(=1)的天数: " + ", ".join(
        "%d %d" % (y, int((g[g["year"] == y]["tau"] >= 0.999).sum())) for y in YEARS))

    # ---- 标定 (2024-25, 与 PS-035 同窗口) ----
    c = g[(g["year"] >= 2024) & (g["year"] <= 2025)]
    X = np.column_stack([np.ones(len(c)), c["S"].values])
    b, *_ = np.linalg.lstsq(X, c["negday"].values, rcond=None)
    fit = (b[0], b[1])
    print("\n[4] 标定 2024-25: P(负价日) = %+.4f %+.4f × S  (n=%d)   [PS-035 原值 −0.072 +0.054]"
          % (b[0], b[1], len(c)))

    # ---- 样本外 ----
    print("\n[5] 样本外检验 (S 对负价日的排序能力)")
    for lab, te in (("→2024", 2024), ("→2025", 2025), ("→2026 全新样本", 2026)):
        t = g[g["year"] == te]
        if len(t) < 50:
            continue
        lo = t["S"].quantile(0.8)
        pred = np.clip(fit[0] + fit[1] * t["S"], 0, 1)
        ROWS_Y.append({"train": "2024-25", "test": te, "n": len(t), "auc": auc(t["S"], t["negday"]),
                       "actual_negday": t["negday"].mean(), "pred_negday": pred.mean(),
                       "top20_actual": t[t["S"] >= lo]["negday"].mean()})
        print("    %-14s n=%3d | AUC %.3f | 预测均 %.3f vs 实际 %.3f | S最高20%%子集实际 %.3f (全年 %.3f)"
              % (lab, len(t), auc(t["S"], t["negday"]), pred.mean(), t["negday"].mean(),
                 t[t["S"] >= lo]["negday"].mean(), t["negday"].mean()))

    # ---- 五分位 ----
    print("\n[6] S 五分位 → 实际负价日率")
    for y in YEARS:
        t = g[g["year"] == y].copy()
        if len(t) < 60:
            continue
        t["q"] = pd.qcut(t["S"].rank(method="first"), 5, labels=False)
        line = []
        for kk, sub in t.groupby("q"):
            line.append("Q%d %.0f%%" % (int(kk) + 1, sub["negday"].mean() * 100))
            ROWS_Q.append({"year": y, "q": int(kk) + 1, "S_med": sub["S"].median(), "n": len(sub),
                           "negday": sub["negday"].mean(), "neg_h": sub["negh"].mean(),
                           "price": sub["price"].mean()})
        print("    %d: %s  (全年 %.0f%%)" % (y, " | ".join(line), t["negday"].mean() * 100))

    # ---- 季节结构 ----
    print("\n[7] 逐月 实际/预测 P(负价日) —— 检验 PS-035 的季节偏差")
    for y in YEARS:
        t = g[g["year"] == y].copy()
        t["pred"] = np.clip(fit[0] + fit[1] * t["S"], 0, 1)
        mm = t.groupby(t.index.month).agg(a=("negday", "mean"), p=("pred", "mean"))
        print("    %d: %s" % (y, " ".join("%d月%.0f/%.0f" % (m, r.a * 100, r.p * 100)
                                         for m, r in mm.iterrows())))

    # ---- 机制: 高光伏 × 低负荷 ----
    print("\n[8] 高光伏×低负荷象限负价频率 (PS-033 机制, 官方口径 + 补 2026)")
    for y in YEARS:
        t = g[g["year"] == y].copy()
        if len(t) < 60:
            continue
        qa, ql = t["solar"].quantile(0.75), t["load"].quantile(0.25)
        q = t[(t["solar"] >= qa) & (t["load"] <= ql)]
        print("    %d: 全样本 %.1f%% → 象限 %.1f%% (n=%d)" %
              (y, t["negday"].mean() * 100, q["negday"].mean() * 100, len(q)))

    pd.DataFrame(ROWS_Y).to_csv(OUT_Y, index=False)
    pd.DataFrame(ROWS_Q).to_csv(OUT_Q, index=False)
    g.to_csv(OUT_DAILY)
    print("\n→ %s\n→ %s\n→ %s" % (OUT_DAILY, OUT_Q, OUT_Y))


if __name__ == "__main__":
    main()
