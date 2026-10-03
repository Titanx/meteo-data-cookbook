"""光伏缺口的持续时间维度建模 (2025/2026 ERCOT, 物理晴空反事实口径)

动机 (PS-022/023/024 遗留):
  既有弹性按【小时】标定 (+5.3 %/GW), 2022-07 事件推演把 44 个事件小时
  当作独立样本逐小时叠加。尚未回答:
    (a) 缺口在连续小时内的时长分布 (单发 vs 长云系);
    (b) 连续多小时的缺口是否产生【持续时间溢价】—— 即扣掉瞬时缺口量级后,
        一个已持续 4h 的缺口比刚发生 1h 的同量级缺口是否传导更高电价
        (系统储备耗竭 / 持续爬坡 / 惯性收紧)。

本脚本四步:
  A 事件切分: 按物理缺口 >= 阈值切连续小时事件, 统计时长/峰值/累积能量分布
  B 持续时间溢价: ln(RTM) ~ sf + 事件累积能量 + 事件内小时序号 + wind + dem + 时段
     (小时粒度 OLS, HAC 标准误)
  C 分位稳健性: 溢价在价格 Q90/Q99 是否增强 (尾部累积, 15min 对齐做伪重复下界)
  D 日际持久性: 逐日能量缺口, 识别多日连阴云系的持续天数特征

输出: stdout + data/ercot/shortfall_duration_2025_2026.csv
"""
import os
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.tools.sm_exceptions import IterationLimitWarning

warnings.simplefilter("ignore", IterationLimitWarning)

D = r"c:\work\meteo\data\ercot"
SF_CSV = os.path.join(D, "shortfall_physical_2025_2026.csv")


def _series(pattern):
    """按 glob 解析唯一的序列文件 (合并后每个 market+location 只有一个文件)。"""
    import glob

    hits = sorted(glob.glob(os.path.join(D, pattern)))
    if len(hits) != 1:
        raise FileNotFoundError(f"预期 1 个文件, 实得 {len(hits)}: {hits}")
    return hits[0]


RTM15 = _series("ercot_rtm_HB_HOUSTON_*.csv")
OUT_CSV = os.path.join(D, "shortfall_duration_2025_2026.csv")

F_BASE = "lnp ~ sf + wind + dem + C(hour) + C(month)"
F_CUM = "lnp ~ sf + cum_gwh + wind + dem + C(hour) + C(month)"
F_DUR = "lnp ~ sf + hours_into + wind + dem + C(hour) + C(month)"
F_BOTH = "lnp ~ sf + cum_gwh + hours_into + wind + dem + C(hour) + C(month)"
ROWS = []


def rec(year, model, param, est, se, n):
    ROWS.append({"year": year, "model": model, "param": param,
                 "estimate": est, "se": se, "n": n})


def load_data():
    df = pd.read_csv(SF_CSV, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def segment_events(df, thr):
    """逐天逐段切分连续缺口小时事件. 返回 df 附事件标注 + 事件汇总表"""
    df = df.copy()
    ev_rows = []
    # 按 (日期, 连续run) 切分: 白天过滤后同一日内不足阈值小时即断段
    hits = (df["shortfall_phys"] >= thr)
    for day, sub in df.groupby(df.index.date):
        arr = hits.reindex(sub.index).fillna(False).values
        # 连续 run 切分: 每个命中 start 开新 run
        starts = np.where(arr & ~np.r_[False, arr[:-1]])[0]
        for st in starts:
            idxs = [st]
            k = st + 1
            while k < len(arr) and arr[k]:
                idxs.append(k)
                k += 1
            idx = sub.index[idxs]
            seg = df.loc[idx]
            ev_rows.append({
                "year": int(day.year), "date": pd.Timestamp(day),
                "start_utc": idx[0], "end_utc": idx[-1],
                "duration_h": len(idx),
                "peak_mw": float(seg["shortfall_phys"].max()),
                "mean_mw": float(seg["shortfall_phys"].mean()),
                "cum_gwh": float(seg["shortfall_phys"].sum()) / 1e3,
                "load_peak_dem": float(seg["demand"].max()),
                "price_peak": float(seg["rtm"].max()),
                "price_mean": float(seg["rtm"].mean()),
            })
            df.loc[idx, "ev_id"] = len(ev_rows) - 1
            df.loc[idx, "hours_into"] = np.arange(len(idx))
    ev = pd.DataFrame(ev_rows)
    df["ev_id"] = df.get("ev_id", np.nan)
    df["hours_into"] = df.get("hours_into", np.nan)
    return df, ev


def compute_cum(df):
    """事件内累积能量 (到当前小时为止, GWh). 非事件小时置 0"""
    df = df.copy()
    df["cum_gwh"] = 0.0
    for eid, g in df.groupby("ev_id", dropna=False):
        if pd.isna(eid):
            continue
        pos = g.index
        c = g["shortfall_phys"].cumsum().values / 1e3
        df.loc[pos, "cum_gwh"] = c
    df["hours_into"] = df["hours_into"].fillna(0)
    df["ev_id"] = df["ev_id"].fillna(-1)
    return df


def main():
    df = load_data()
    print(f"物理缺口样本 {len(df)} 白天小时, 缺口中位 "
          f"{df['shortfall_phys'].median():.0f} MW / P95 "
          f"{df['shortfall_phys'].quantile(0.95):.0f} MW")

    # 事件阈值类比 PS-022(2022, 10.66GW 舰队, 缺口>=1.5GW/峰值4.4GW) 按舰队规模放大:
    # 30.89GW 舰队 -> 阈值约 12GW (≈39% 容量离线). 另报 8GW(敏感下界) 衰减.
    thr = 12000.0
    dfm, ev = segment_events(df, thr)
    dfm = compute_cum(dfm)
    ev.to_csv(os.path.join(D, "shortfall_duration_events_2025_2026.csv"),
              index=False)
    print(f"\n[A 事件切分] 物理缺口>={int(thr)}MW (≈{thr/1000:.0f}GW, "
          f"{thr/30884*100:.0f}% 舰队) 连续小时事件 (n={len(ev)})")

    hc = ev["duration_h"].value_counts().sort_index()
    print("\n时长分布 (小时数): ")
    for h, c in hc.items():
        tot_e = ev.loc[ev["duration_h"] >= h, "cum_gwh"].sum()
        print(f"  {h:>2d}h: {c:>4d} 事件 ({c/len(ev)*100:>4.1f}%), "
              f"累积能量(>=此时长) {tot_e:>7.1f} GWh")
    en_tot = ev["cum_gwh"].sum()
    print(f"\n全事件累积缺口能量汇总 {en_tot:.1f} GWh")
    for h0 in (2, 3, 4):
        sub_e = ev[ev["duration_h"] >= h0]
        print(f"  >= {h0} 小时事件: {len(sub_e)} 个, "
              f"能量 {sub_e['cum_gwh'].sum():.1f} GWh "
              f"({sub_e['cum_gwh'].sum()/en_tot*100:.0f}% 事件能量)")

    # 峰值-时长联合
    med_pk = ev["peak_mw"].median()
    print(f"\n时长>=4h 事件 (n={ (ev['duration_h']>=4).sum() }):")
    for _, r in ev[ev["duration_h"] >= 4].sort_values("cum_gwh", ascending=False) \
            .head(8).iterrows():
        print(f"  {r['start_utc']} ~ {r['end_utc']} {int(r['duration_h'])}h "
              f"峰值{r['peak_mw']:.0f}MW cum {r['cum_gwh']:.1f}GWh "
              f"dem峰{r['load_peak_dem']/1000:.0f}GW rtm峰${r['price_peak']:.0f}")

    # ---- B 持续时间溢价 ----
    mh = dfm.copy()
    mh["ev_flag"] = (mh["ev_id"] >= 0)
    for c, s in (("sf", "shortfall_phys"), ("wind", "wind"), ("dem", "demand")):
        mh[c] = mh[s] / 1000.0
    mh["hour"] = mh.index.hour
    mh["month"] = mh.index.month
    mh["lnp"] = np.log(mh["rtm"].clip(lower=1))

    print("\n" + "=" * 78)
    print("[B 持续时间溢价] 小时粒度 ln(RTM) OLS (HAC, 全白天样本)")
    for year in (2025, 2026):
        m = mh[mh["year"] == year]
        print(f"\n{year}: n={len(m)}")
        r0 = smf.ols(F_BASE, m).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
        b = r0.params["sf"] * 100
        rec(year, "base_dur", "sf", b, r0.bse["sf"] * 100, len(m))
        print(f"  基线 sf {b:+.2f} %/GW (SE {r0.bse['sf']*100:.2f})")
        for lab, fo in (("+cum_gwh", F_CUM), ("+hours_into", F_DUR),
                        ("+cum+hours", F_BOTH)):
            r = smf.ols(fo, m).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
            bsf = r.params["sf"] * 100
            res = []
            for p in ("cum_gwh", "hours_into"):
                if p in r.params:
                    res.append(f"{p} {r.params[p]*100:+.3f} "
                               f"(SE {r.bse[p]*100:.3f})")
            rec(year, "dur_" + lab, "sf", bsf, r.bse["sf"] * 100, len(m))
            rec(year, "dur_" + lab, "add", r.params.get("cum_gwh", np.nan) * 100,
                r.bse.get("cum_gwh", np.nan) * 100, len(m))
            print(f"  {lab:<12s} sf {bsf:+.2f} %/GW | "
                  + " | ".join(res))

        # 饱和效应: 事件内小时序号 0..4+ 的响应差异 (基线模型残差)
        print("\n  同量级缺口下, 事件内续小时的残差 (基线模型, 仅事件内小时):")
        me = m[m["ev_flag"]]
        r0r = smf.ols(F_BASE, me).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
        me["resid"] = me["lnp"] - r0r.predict(me)
        for h in (0, 1, 2, 3, 4):
            g = me[me["hours_into"] == h]
            if len(g) >= 50:
                print(f"    事件第{h+1}h: n={len(g)} resid均 "
                      f"{g['resid'].mean():+.3f}")
                rec(year, "dur_pos", f"pos{h}", g["resid"].mean(), np.nan,
                    len(g))

    # ---- C 分位/尾部 (15min 对齐, 伪重复 SE 为下界) ----
    print("\n" + "=" * 78)
    print("[C 尾部稳健性] 15min 对齐, Q90/Q99 下 cum 溢价 (伪重复 SE 下界)")
    r15 = pd.read_csv(RTM15)
    tt = pd.to_datetime(r15["interval_start_utc"]).dt.tz_convert("UTC") \
        .dt.tz_localize(None)
    r15s = pd.Series(r15["spp"].astype(float).values, index=tt).sort_index()
    hh = dfm.reset_index()                  # 列含原始时间索引 (time_utc)
    hh["hkey"] = hh[hh.columns[0]]
    hh = hh.drop(columns=["rtm", "dam"], errors="ignore")   # 用 15min rtm, 避免列冲突
    rr = r15s.to_frame("rtm").reset_index()
    rr["hkey"] = rr[rr.columns[0]].dt.floor("1h")
    mm = rr.merge(hh, on="hkey", how="inner")
    mm["sf"] = mm["shortfall_phys"] / 1000.0
    for c in ("wind", "dem"):
        mm[c] = mm["wind"] / 1000.0 if c == "wind" else mm["demand"] / 1000.0
    mm["hour"] = mm["hkey"].dt.hour
    mm["month"] = mm["hkey"].dt.month
    mm["lnp"] = np.log(mm["rtm"].clip(lower=1))
    for year in (2025, 2026):
        m = mm[mm["year"] == year]
        print(f"\n{year}: 15min n={len(m)}")
        for tq in (0.5, 0.9, 0.99):
            r0 = smf.quantreg(F_BASE, m).fit(q=tq, max_iter=3000, p_tol=1e-6)
            rc = smf.quantreg(F_CUM, m).fit(q=tq, max_iter=3000, p_tol=1e-6)
            print(f"  Q{tq:>3}: 基线 sf {r0.params['sf']*100:+.2f} | "
                  f"cum模型 sf {rc.params['sf']*100:+.2f}, "
                  f"cum {rc.params['cum_gwh']*100:+.3f} %/GWh "
                  f"(SE {rc.bse['cum_gwh']*100:.3f})")
            rec(year, "qreg15_cumdur", f"sf_q{tq}", rc.params["sf"] * 100,
                rc.bse["sf"] * 100, len(m))
            rec(year, "qreg15_cumdur", f"cum_q{tq}",
                rc.params["cum_gwh"] * 100, rc.bse["cum_gwh"] * 100, len(m))

    # ---- D 日际持久性 ----
    print("\n" + "=" * 78)
    print("[D 日际持久性] 逐日能量缺口 (GWh/日)")
    dsub = dfm[dfm["shortfall_phys"] > 50]
    daily = dsub.groupby(dsub.index.date) \
        .agg(cum_en=("shortfall_phys", lambda x: x.sum() / 1e3),
             load_peak=("demand", "max"),
             mid_en=("shortfall_phys", "median")).round(2)
    dm = (daily["cum_en"] >= daily["cum_en"].quantile(0.5))
    # 连续"高缺口日"run
    runs = (dm != np.roll(dm, 1)) & dm
    rnum = np.cumsum(runs) * dm
    grp = pd.DataFrame({"d": dm.values, "r": rnum.values}, index=daily.index)
    glen = grp[grp["d"]].groupby("r").size()
    print(f"  高缺日阈值: >= {daily['cum_en'].quantile(0.5):.1f} GWh/日 "
          f"({dm.mean()*100:.0f}% 的天)")
    print(f"  连阴天数分布: " + ", ".join(
        f"{l}天×{c}次" for l, c in glen.value_counts().sort_index().items()))
    rec(0, "daily_persistence", "max_streak", int(glen.max()), np.nan, len(daily))
    rec(0, "daily_persistence", "multi_day_days", int(glen[glen >= 2].sum()),
        np.nan, len(daily))

    t = pd.DataFrame(ROWS)
    t.to_csv(OUT_CSV, index=False)
    print(f"\n已保存: {OUT_CSV} ({len(t)} 行)")


if __name__ == "__main__":
    main()