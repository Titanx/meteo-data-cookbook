"""光伏缺口的日际/跨日持续时间维度 (PS-026, 2025/2026 ERCOT, 物理晴空反事实)

PS-025 只检验了【白天内小时级】持续: 恶劣缺口多小时持续是常态, 但白天内
持续时间溢价跨年不稳健。本脚本推进到【日级/周级】持续 —— 连阴低日照云系
(PS-025 已发现最长 25~26 天) 是否在多日累积下收紧市场?

三部分:
  A 阈值敏感性: 白天内事件时长结构(+时长分布)在 8/10/15GW 阈值下是否稳健
  B 跨日持续时间溢价: 日级 ln(RTM) ~ 日内缺口能量 + 负荷 + 时段 + 连阴序号,
     检验「连阴第 N 天 vs 孤立高缺日」在扣掉当日缺口与负荷后是否仍有加价
  C 危险云系鉴别: 高缺日 × 高需求 四分格, 量化「低日照+高需求」高风险云系
     的占比与价格(热盖/连阴), 对应 PS-023/024 的"罕见高风险组合"

输出: stdout + data/ercot/shortfall_duration_crossday_2025_2026.csv
"""
import os
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.tools.sm_exceptions import IterationLimitWarning

warnings.simplefilter("ignore", IterationLimitWarning)

D = r"c:\work\meteo\data\ercot"
SF = os.path.join(D, "shortfall_physical_2025_2026.csv")
OUT = os.path.join(D, "shortfall_duration_crossday_2025_2026.csv")
ROWS = []


def rec(year, model, param, est, se, n):
    ROWS.append({"year": year, "model": model, "param": param,
                 "estimate": float(est), "se": float(se), "n": int(n)})


def load():
    df = pd.read_csv(SF, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    for c, s in (("sf", "shortfall_phys"), ("wind", "wind"), ("dem", "demand")):
        df[c] = df[s] / 1000.0                     # GW
    df["hour"] = df.index.hour
    df["month"] = df.index.month
    df["lnp"] = np.log(df["rtm"].clip(lower=1))
    return df


# ---------- A 白天内事件时长对阈值的敏感性 ----------
def sensitivity_A(df):
    print("=" * 78)
    print("[A 白天内事件时长结构 对事件阈值的敏感性] (物理口径, 事件=连续缺口小时)")
    print(f"  {'阈GW':>5s}{'事件':>5s}{'1h占':>7s}{'≥3h能量':>9s}{'≥4h能量':>9s}"
          f"{'最大h':>6s}")
    for thr in (8.0, 10.0, 12.0, 15.0):
        thrs = thr * 1000.0
        hits = df["shortfall_phys"] >= thrs
        n_ev = 0
        durs = []
        eng = {"g3": 0.0, "g4": 0.0, "tot": 0.0, "e1": 0.0, "e2": 0.0}
        for _, sub in df.groupby(df.index.date):
            arr = hits.reindex(sub.index).fillna(False).values
            starts = np.where(arr & ~np.r_[False, arr[:-1]])[0]
            for st in starts:
                k = st + 1
                while k < len(arr) and arr[k]:
                    k += 1
                idx = sub.index[st:k]
                seg = df.loc[idx, "shortfall_phys"].sum() / 1e3   # GWh
                dur = len(idx)
                n_ev += 1
                durs.append(dur)
                eng["tot"] += seg
                if dur == 1:
                    eng["e1"] += seg
                elif dur == 2:
                    eng["e2"] += seg
                if dur >= 3:
                    eng["g3"] += seg
                if dur >= 4:
                    eng["g4"] += seg
        n1 = sum(1 for d in durs if d == 1) / max(n_ev, 1)
        mx = max(durs) if durs else 0
        print(f"  {thr:>5.0f}{n_ev:>5d}{n1*100:>6.1f}%{eng['g3']/eng['tot']*100:>8.0f}%"
              f"{eng['g4']/eng['tot']*100:>8.0f}%{mx:>6d}h")
        rec(0, "sens_dur", f"thr{int(thr)}_worst_events", n_ev, np.nan,
            n_ev)
        rec(0, "sens_dur", f"thr{int(thr)}_en_ge3", eng["g3"] / eng["tot"],
            np.nan, n_ev)


# ---------- B 日级口径 + 跨日持续时间溢价 ----------
def build_daily(df):
    g = df.groupby(df.index.date).agg(
        sf_en=("sf", lambda x: x.clip(lower=0).sum()),
        wind=("wind", "mean"), dem_peak=("demand", "max"),
        dem_mean=("demand", "mean"),
        rtm_mean=("rtm", "mean"), rtm_max=("rtm", "max"),
        n_hr=("rtm", "count"), solar=("solar", "sum"),
        clearsky=("clearsky_mw", "sum"))
    g.index = pd.to_datetime(np.array(g.index, dtype="datetime64[ns]"))
    g["year"] = g.index.year
    g["month"] = g.index.month
    g["lnrtm_mean"] = np.log(g["rtm_mean"].clip(lower=1))
    g["lnrtm_max"] = np.log(g["rtm_max"].clip(lower=1))
    return g


def streak_labels(daily, thr_gwh):
    dhi = daily["sf_en"] >= thr_gwh
    runs = np.cumsum((dhi.values != np.roll(dhi.values, 1)) & dhi.values) * dhi.values
    # streak 位置与全局累积
    idx_in = []
    cum_s = []
    for r in np.unique(runs[runs > 0]):
        pos = np.where(runs == r)[0]
        for j, p in enumerate(pos):
            idx_in.append((daily.index[p], j + 1))
        c = daily["sf_en"].values[pos]
        for j, p in enumerate(pos):
            cum_s.append((daily.index[p], c[: j + 1].sum()))
    mp = pd.Series(dict(idx_in), name="streak_idx")
    mpc = pd.Series(dict(cum_s), name="streak_cum")
    return daily.assign(streak_idx=mp, streak_cum=mpc) \
        .fillna({"streak_idx": 0, "streak_cum": 0}), dhi


def crossday_B(daily, dhi):
    print("\n" + "=" * 78)
    print("[B 跨日持续时间溢价] 日级粒度, 连阴第N天相对孤立高缺日的额外加价")
    med = float(daily["sf_en"].median())
    print(f"  高缺日阈 = 日缺口能量中位 {med:.1f} GWh ({dhi.mean()*100:.0f}% 的天)")
    for year in (2025, 2026):
        dd = daily[daily["year"] == year]
        dd = dd[dd["sf_en"] > 5]
        print(f"\n{year}: n={len(dd)} 有日照的天")
        # 基线: 只有当日缺口+负荷+月份
        b = smf.ols("lnrtm_mean ~ sf_en + wind + dem_peak + C(month)",
                    dd).fit(cov_type="HC1")
        bsf = b.params["sf_en"] * 100
        print(f"  基线日级: sf_en {bsf:+.3f} %/GWh (SE {b.bse['sf_en']*100:.3f})")
        rec(year, "day_base", "sf_en", bsf, b.bse["sf_en"] * 100, len(dd))
        # 加连阴序号
        b2 = smf.ols("lnrtm_mean ~ sf_en + wind + dem_peak + C(month) + streak_idx",
                     dd).fit(cov_type="HC1")
        bsf2 = b2.params["sf_en"] * 100
        bi = b2.params["streak_idx"] * 100
        bis = b2.bse["streak_idx"] * 100
        print(f"  +streak_idx: sf_en {bsf2:+.3f} | streak_idx {bi:+.3f} %/天 "
              f"(SE {bis:.3f}, t={bi/bis:+.1f})")
        rec(year, "day_xd", "sf_en", bsf2, b2.bse["sf_en"] * 100, len(dd))
        rec(year, "day_xd", "streak_idx", bi, bis, len(dd))
        # 加连阴累积能量
        b3 = smf.ols("lnrtm_mean ~ sf_en + wind + dem_peak + C(month) + streak_cum",
                     dd).fit(cov_type="HC1")
        bc = b3.params["streak_cum"] * 100
        print(f"  +streak_cum: sf_en {b3.params['sf_en']*100:+.3f} | "
              f"streak_cum {bc:+.3f} %/GWh (SE {b3.bse['streak_cum']*100:.3f}, "
              f"t={bc/(b3.bse['streak_cum']*100):+.1f})")
        rec(year, "day_xd_cum", "streak_cum", bc,
            b3.bse["streak_cum"] * 100, len(dd))
        # 非参数: 按连阴内位置分箱残差
        r0 = smf.ols("lnrtm_mean ~ sf_en + wind + dem_peak + C(month)",
                     dd).fit(cov_type="HC1")
        dd = dd.assign(resid=dd["lnrtm_mean"] - r0.predict(dd)).copy()
        print("  连阴内位置残差 (基线日级模型, 仅高缺日):")
        for lab, f in (("第1天", dd["streak_idx"] == 1),
                       ("第2天", dd["streak_idx"] == 2),
                       ("第3天", dd["streak_idx"] == 3),
                       ("第4~6天", dd["streak_idx"].between(4, 6)),
                       ("第7天+", dd["streak_idx"] >= 7)):
            g = dd[f]
            if (g["streak_idx"] > 0).sum() and len(g) >= 20:
                z = g[g["streak_idx"] > 0]["resid"]
                print(f"    {lab:<8s} n={len(z):>4d} resid均 {z.mean():+.3f}")
                rec(year, "day_pos", f"pos{lab}", z.mean(), np.nan, len(z))
    return daily, dhi


# ---------- C 危险云系鉴别 ----------
def hazard_C(daily, dhi):
    print("\n" + "=" * 78)
    print("[C 危险云系鉴别] 高缺日 × 高需求 四分格 (月内相对需求)")
    # 高需求 = 当日负荷峰 > 该月负荷峰中位
    dd = daily[daily["sf_en"] > 5].copy()
    dd["hih_dem"] = dd["dem_peak"] >= dd.groupby("month")["dem_peak"] \
        .transform("median")
    dd["hih_gap"] = dhi.reindex(dd.index).fillna(False)
    tab = dd.groupby(["hih_gap", "hih_dem"])["rtm_mean"].agg(["count", "mean"])
    print(f"  {'':<22s}{'n':>5s}{'日RTM均>$':>9s}")
    for (g, h), r in tab.iterrows():
        lbl = {("False", "False"): "量子1 低缺×低需",
               ("False", "True"): "量子2 低缺×高需(晴热)",
               ("True", "False"): "量子3 高缺×低需(阴凉,良性)",
               ("True", "True"): "量子4 高缺×高需(危险云系)"} \
            .get((str(bool(g)), str(bool(h))), (str(bool(g)), str(bool(h))))
        print(f"  {lbl:<22s}{int(r['count']):>5d}{r['mean']:>9.0f}")
    # 危险象限价格 vs 良性
    dgrp = dd[dd["hih_gap"] & dd["hih_dem"]]
    dgn = dd[dd["hih_gap"] & ~dd["hih_dem"]]
    print(f"\n  危险云系(高缺×高需): n={len(dgrp)}, 日RTM均 ${dgrp['rtm_mean'].mean():.0f}")
    print(f"  良性云系(高缺×低需): n={len(dgn)}, 日RTM均 ${dgn['rtm_mean'].mean():.0f}")
    print(f"  危险/良性 之比: {dgrp['rtm_mean'].mean()/max(dgn['rtm_mean'].mean(),1e-9):.2f}x, "
          f"危险象限占所有高缺日 {100*len(dgrp)/(len(dgrp)+len(dgn)):.0f}%")
    rec(0, "hazard", "danger_n", len(dgrp), np.nan, len(dd))
    rec(0, "hazard", "danger_share_hi", len(dgrp) / (len(dgrp) + len(dgn)),
        np.nan, len(dd))
    rec(0, "hazard", "ratio_danger_benign",
        dgrp["rtm_mean"].mean() / max(dgn["rtm_mean"].mean(), 1e-9), np.nan,
        len(dd))


def main():
    df = load()
    sensitivity_A(df)
    daily = build_daily(df)
    daily, dhi = streak_labels(daily, float(daily["sf_en"].median()))
    daily, dhi = crossday_B(daily, dhi)
    hazard_C(daily, dhi)

    t = pd.DataFrame(ROWS)
    t.to_csv(OUT, index=False)
    print(f"\n已保存: {OUT} ({len(t)} 行)")


if __name__ == "__main__":
    main()