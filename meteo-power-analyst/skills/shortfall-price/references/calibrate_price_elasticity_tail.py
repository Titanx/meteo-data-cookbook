"""RTM 尾部尖峰弹性标定 v2 (分位数回归 + 凸性检验, 极端场景外推)

动机 (PS-022 遗留):
  既有弹性用【小时均值 ln(RTM) 的 OLS】-> 只给条件均值响应 (+5.08 %/GW);
  但 (a) 小时平均把尖峰抹平 (15min 最高 $3777 vs 小时均值最高 $1561);
      (b) 均值响应无法回答"极端场景" (高价格分位/尖峰概率)。

本脚本四个改进:
  A 口径: 用 15min RTM 保留尖峰, 量化"小时内平均"造成的尾部损失
  B 分位数: Q_tau(ln RTM) ~ X, tau=.5~.995 -> beta(tau) 尾部弹性曲线
  C 凸性: 检验 ln RTM 对缺口是否超线性 (平方项 / 分箱斜率) -> 线性外推是否低估极端
  D 尾部: P(尖峰) 概率模型 + 高需求交互项

单位: 回归量用 GW -> beta 直接是 ln/GW, x100 = %/GW
输出: stdout + data/ercot/price_elasticity_tail.csv
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


def _series(pattern):
    """按 glob 解析唯一的序列文件 (合并后每个 market+location 只有一个文件)。"""
    import glob

    hits = sorted(glob.glob(os.path.join(D, pattern)))
    if len(hits) != 1:
        raise FileNotFoundError(f"预期 1 个文件, 实得 {len(hits)}: {hits}")
    return hits[0]


RTM_PATH = _series("ercot_rtm_HB_HOUSTON_*.csv")
OUT_CSV = os.path.join(D, "price_elasticity_tail.csv")
QS = [0.50, 0.75, 0.90, 0.95, 0.99, 0.995]
F_BASE = "lnp ~ sf + wind + dem + C(hour) + C(month)"
F_QUAD = "lnp ~ sf + I(sf**2) + wind + dem + C(hour) + C(month)"
F_INTER = "lnp ~ sf + sfhot + wind + dem + C(hour) + C(month)"
ROWS = []


def rec(year, model, param, est, se, n):
    ROWS.append({"year": year, "model": model, "param": param,
                 "estimate": est, "se": se, "n": n})


def load_eia_year(year):
    # 月份范围由磁盘上实际存在的月度文件决定。
    # 旧实现把 2026 硬编码为 1–8 月, 新增月份会被静默漏读。
    fuels, demand = [], []
    for m in range(1, 13):
        f = os.path.join(D, f"ercot_fuel_type_data_{year}-{m:02d}.csv")
        r = os.path.join(D, f"ercot_region_data_{year}-{m:02d}.csv")
        if not os.path.exists(f) or not os.path.exists(r):
            continue
        fuels.append(pd.read_csv(f))
        rr = pd.read_csv(r)
        demand.append(rr[rr["type_code"] == "D"])
    fuel = pd.concat(fuels)
    piv = fuel.pivot_table(index="time", columns="fuel_code", values="value",
                           aggfunc="mean")
    piv.index = pd.to_datetime(piv.index).tz_localize("UTC").tz_localize(None) \
        - pd.Timedelta(hours=1)
    piv = piv[~piv.index.duplicated(keep="first")]
    d = pd.concat(demand).set_index("time")["value"].astype(float)
    d.index = pd.to_datetime(d.index).tz_localize("UTC").tz_localize(None) \
        - pd.Timedelta(hours=1)
    d = d[~d.index.duplicated(keep="first")]
    return piv, d


def clearsky_envelope(solar, halfwin=15):
    doy = solar.index.dayofyear.values
    hour = solar.index.hour.values
    mat = np.full((367, 24), np.nan)
    vals = solar.values
    for h in range(24):
        mh = hour == h
        for dd in range(1, 366):
            w = mh & (np.abs(doy - dd) <= halfwin)
            if w.sum() >= 5:
                mat[dd, h] = np.nanpercentile(vals[w], 95)
    env = np.array([mat[doy[i], hour[i]] for i in range(len(solar))])
    return pd.Series(np.nan_to_num(env, nan=0.0), index=solar.index).clip(lower=0)


def load_rtm15():
    df = pd.read_csv(RTM_PATH)
    t = pd.to_datetime(df["interval_start_utc"]).dt.tz_convert("UTC") \
        .dt.tz_localize(None)
    s = pd.Series(df["spp"].astype(float).values, index=t).sort_index()
    s.index.name = "t"
    return s


def build(year, rtm15):
    piv, dem = load_eia_year(year)
    hp = pd.DataFrame({"solar": piv.get("SUN"), "wind": piv.get("WND"),
                       "demand": dem}).dropna()
    hp["env"] = clearsky_envelope(hp["solar"])
    hp["shortfall"] = (hp["env"] - hp["solar"]).clip(lower=0)
    hp = hp[hp["solar"] > 50]                       # 白天小时 (与 PS-022 同口径)
    hp = hp[(hp.index >= rtm15.index.min()) & (hp.index <= rtm15.index.max())]
    hp.index.name = "hkey"

    h = hp.reset_index()
    r = rtm15.to_frame("rtm").reset_index()
    r["hkey"] = r["t"].dt.floor("1h")
    m = r.merge(h, on="hkey", how="inner")
    for c, s in (("sf", "shortfall"), ("wind", "wind"), ("dem", "demand")):
        m[c] = m[s] / 1000.0                        # GW
    m["hour"] = m["hkey"].dt.hour
    m["month"] = m["hkey"].dt.month
    m["lnp"] = np.log(m["rtm"].clip(lower=1))
    m["sfhot"] = m["sf"] * (m["dem"] >= 72.0)

    g = m.groupby("hkey")
    mh = g.agg(rtm_mean=("rtm", "mean"), rtm_max=("rtm", "max"),
               sf=("sf", "first"), wind=("wind", "first"),
               dem=("dem", "first")).reset_index()
    mh["hour"] = mh["hkey"].dt.hour
    mh["month"] = mh["hkey"].dt.month
    mh["lnp_mean"] = np.log(mh["rtm_mean"].clip(lower=1))
    mh["lnp_max"] = np.log(mh["rtm_max"].clip(lower=1))
    mh["lnp"] = mh["lnp_mean"]                   # 基准复现用 (PS-022 口径)
    mh["sfhot"] = mh["sf"] * (mh["dem"] >= 72.0)
    return m, mh


def main():
    rtm15 = load_rtm15()
    print(f"15min RTM {len(rtm15)} 条 {rtm15.index.min().date()} ~ "
          f"{rtm15.index.max().date()}")
    print(f"全样本尖峰: 15min max ${rtm15.max():.0f} | 小时均值 max "
          f"${rtm15.resample('1h').mean().max():.0f} "
          f"(衰减 {rtm15.max()/rtm15.resample('1h').mean().max():.1f}x)")
    q = rtm15.quantile([0.9, 0.99, 0.995, 0.999])
    print(f"  15min 分位: q90 ${q[0.9]:.0f} q99 ${q[0.99]:.0f} "
          f"q99.5 ${q[0.995]:.0f} q99.9 ${q[0.999]:.0f}")

    for year in (2025, 2026):
        m, mh = build(year, rtm15)
        u99 = float(rtm15.quantile(0.99))
        print(f"\n{'='*76}\n{year}: 15min n={len(m)} (小时 n={len(mh)}), "
              f"缺口 sf 中位 {m['sf'].median():.2f} GW / P95 {m['sf'].quantile(0.95):.2f} GW")

        # A 口径损失
        print(f"\n[A 口径] 白天样本内 15min max ${m['rtm'].max():.0f} | "
              f"小时均值 max ${mh['rtm_mean'].max():.0f} | 小时内极值 max "
              f"${mh['rtm_max'].max():.0f}")

        # 基准复现 (OLS 小时均值, 应复现 PS-022 +5.08)
        r = smf.ols(F_BASE, mh).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
        b = r.params["sf"] * 100
        rec(year, "OLS_hourmean_HAC", "sf", b, r.bse["sf"] * 100, len(mh))
        print(f"\n[基准复现] 小时均值 OLS: sf {b:+.2f} %/GW "
              f"(SE {r.bse['sf']*100:.2f})  <- PS-022 口径")
        print(f"   wind {r.params['wind']*100:+.2f} %/GW | "
              f"dem {r.params['dem']*100:+.2f} %/GW")

        # B 分位数曲线 (15min, 伪重复导致 SE 偏小, 视为下界)
        print(f"\n[B 分位数 ln 尺度] Q_tau(ln RTM) 15min, 回归量 GW")
        print(f"  {'tau':>6s}{'beta %/GW':>11s}{'SE*':>7s}{'wind':>8s}{'dem':>8s}")
        for tq in QS:
            res = smf.quantreg(F_BASE, m).fit(q=tq, max_iter=2000, p_tol=1e-5)
            rec(year, "qreg15", f"sf_q{tq}", res.params["sf"] * 100,
                res.bse["sf"] * 100, len(m))
            print(f"  {tq:>6.3f}{res.params['sf']*100:>11.2f}"
                  f"{res.bse['sf']*100:>7.2f}{res.params['wind']*100:>8.2f}"
                  f"{res.params['dem']*100:>8.2f}")
        print("   * 15min 与小时供需对齐, 1h 内 4 条伪重复 -> SE 为下界")

        # B2 原始价格尺度 (小时内极值, 无伪重复) -> $/GW 尾部放大
        print(f"\n[B2 原始尺度] Q_tau(小时极值 RTM $/MWh) ~ sf  (n={len(mh)})")
        print(f"  {'tau':>6s}{'$GW':>10s}{'SE':>8s}{'价格分位$':>11s}")
        for tq in QS:
            res = smf.quantreg("rtm_max ~ sf + wind + dem + C(hour) + C(month)",
                               mh).fit(q=tq, max_iter=2000, p_tol=1e-5)
            rec(year, "qreg_hourmax_usd", f"sf_usd_q{tq}", res.params["sf"],
                res.bse["sf"], len(mh))
            print(f"  {tq:>6.3f}{res.params['sf']:>10.1f}{res.bse['sf']:>8.1f}"
                  f"{mh['rtm_max'].quantile(tq):>11.0f}")
        print("   * 同 1 GW 缺口对高价格分位的绝对冲击远大于中位分位")

        # C 凸性
        print(f"\n[C 凸性] ln RTM 对缺口是否超线性")
        rq = smf.ols(F_QUAD, mh).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
        sq = rq.params["I(sf ** 2)"] * 100
        rec(year, "quad_hourmean_HAC", "sf2", sq, rq.bse["I(sf ** 2)"] * 100, len(mh))
        print(f"  全样本 平方项 {sq:+.3f} per GW^2 (SE {rq.bse['I(sf ** 2)']*100:.3f}, "
              f"t={sq/(rq.bse['I(sf ** 2)']*100):+.1f})")
        ev = mh[mh["sf"] <= 6]        # 事件尺度子样本 (2022-07 事件 1.5~4.4 GW)
        rq2 = smf.ols(F_QUAD, ev).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
        sq2 = rq2.params["I(sf ** 2)"] * 100
        rec(year, "quad_event_range_HAC", "sf2", sq2,
            rq2.bse["I(sf ** 2)"] * 100, len(ev))
        print(f"  事件尺度 (sf<=6GW, n={len(ev)}) 平方项 {sq2:+.3f} (SE "
              f"{rq2.bse['I(sf ** 2)']*100:.3f}, "
              f"t={sq2/(rq2.bse['I(sf ** 2)']*100):+.1f})")
        q99 = smf.quantreg(F_QUAD, m).fit(q=0.99, max_iter=2000, p_tol=1e-5)
        sq99 = q99.params["I(sf ** 2)"] * 100
        rec(year, "quad_q99_15min", "sf2", sq99, q99.bse["I(sf ** 2)"] * 100, len(m))
        print(f"  Q99(15min) 平方项 {sq99:+.3f} (SE {q99.bse['I(sf ** 2)']*100:.3f})")

        # D 尾部概率 (小时粒度, 避免伪重复)
        thr = float(mh["rtm_max"].quantile(0.99))
        mh2 = mh.assign(tail=(mh["rtm_max"] > thr).astype(int))
        gl = smf.glm("tail ~ sf + wind + dem + C(hour) + C(month)",
                     data=mh2, family=sm.families.Binomial()).fit()
        orr = np.exp(gl.params["sf"])
        rec(year, "glm_tail_hour", "lnOR", gl.params["sf"], gl.bse["sf"], len(mh2))
        print(f"\n[D 尾部概率] 小时尖峰 (>{thr:.0f} $/MWh) 概率 ~ 缺口 "
              f"(n={len(mh2)}, 基础率 {mh2['tail'].mean()*100:.1f}%)")
        print(f"   +1 GW 缺口 -> lnOR {gl.params['sf']:+.3f} (SE {gl.bse['sf']:.3f})"
              f" -> OR {orr:.3f} ({(orr-1)*100:+.1f}%)")
        mh2["p"] = gl.predict(mh2)
        print(f"  {'缺口档GW':>10s}{'n':>7s}{'实际尖峰率':>11s}{'模型预测':>10s}")
        for lo, hi in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 99)]:
            g = mh2[(mh2["sf"] >= lo) & (mh2["sf"] < hi)]
            if len(g) < 30:
                continue
            print(f"  {f'{lo}~{hi}':>10s}{len(g):>7d}{g['tail'].mean()*100:>10.1f}%"
                  f"{g['p'].mean()*100:>9.1f}%")
        rec(year, "glm_base_rate", "p", mh2["tail"].mean(), np.nan, len(mh2))

        # E 稳健性: 小时粒度 (无伪重复) 对照 15min
        print(f"\n[E 稳健性] 小时粒度 (无伪重复) 分位弹性 vs 均值")
        for lab, col in (("小时极值 rtm_max", "lnp_max"), ("小时均值 rtm_mean", "lnp_mean")):
            fo = f"{col} ~ sf + wind + dem + C(hour) + C(month)"
            ols = smf.ols(fo, mh).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
            line = f"  {lab:<20s} OLS {ols.params['sf']*100:+.2f} %/GW | "
            rec(year, f"hourly_{col}_ols", "sf", ols.params["sf"] * 100,
                ols.bse["sf"] * 100, len(mh))
            for tq in (0.5, 0.9, 0.99):
                res = smf.quantreg(fo, mh).fit(q=tq, max_iter=3000, p_tol=1e-6)
                line += f"Q{int(tq*100)} {res.params['sf']*100:+.2f}  "
                rec(year, f"hourly_{col}", f"sf_q{tq}", res.params["sf"] * 100,
                    res.bse["sf"] * 100, len(mh))
            print(line)

        # 高需求交互
        ri = smf.ols(F_INTER, mh).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
        bi = ri.params["sfhot"] * 100
        rec(year, "inter_hourmean_HAC", "sf_x_hot", bi,
            ri.bse["sfhot"] * 100, len(mh))
        print(f"\n[高需求交互] 基础弹性 {ri.params['sf']*100:+.2f} %/GW, "
              f"需求>=72GW 增量 {bi:+.2f} %/GW (SE {ri.bse['sfhot']*100:.2f}) "
              f"-> 合计 {(ri.params['sf']+ri.params['sfhot'])*100:+.2f}")

    t = pd.DataFrame(ROWS)
    t.to_csv(OUT_CSV, index=False)
    print(f"\n已保存: {OUT_CSV}  ({len(t)} 行)")


if __name__ == "__main__":
    main()
