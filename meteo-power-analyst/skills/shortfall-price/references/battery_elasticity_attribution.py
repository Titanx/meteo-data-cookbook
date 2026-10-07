"""弹性跨年漂移的储能归因 (ERCOT, 2025-01 ~ 2026-09)

问题: 缺口->RTM 弹性 2025 +5.08 vs 2026 +5.30~5.43 %/GW 的漂移,
      是否由储能快速扩张驱动? 方向是放大还是削弱?

数据口径 (与 calibrate_price_elasticity_2025.py 完全一致):
  面板: EIA-930 小时 SUN/WND/需求 + BAT/UES + GridStatus RTM/DAM HB_HOUSTON
  晴空包络: 同 hour-of-day ±15 天窗口光伏 P95 (逐年计算)
  白天: solar > 50 MW; 回归 ln(RTM.clip(1)) ~ shortfall + wind + demand + h/m FE

储能报告口径切换 (EIA-930 storage 口径):
  < 2025-12-15 07:00 UTC: BAT=纯放电(>=0), UES=纯充电负载(<=0), 分列
  >= 2025-12-15 07:00:    BAT=净额(放电-充电), UES 停报
  统一序列: net = BAT+UES; dis = 切换前 BAT / 切换后 max(BAT,0);
             chg = 切换前 -UES / 切换后 max(-BAT,0)

分析四件套:
  P1 弹性路径: 逐年头条复算 + 季度窗口弹性 + 2025Q3 vs 2026Q3 同季对照
  P2 漂移检验: 池化 year x shortfall 交互; 容量交互 (cap=滚动90天放电P99)
  P3 事件机制: 缺口>=1.5GW 15-23UTC 事件小时, rtm/储能相对同小时±30天
      非事件基线的偏离; 检验"储能响应大->价格冲击小"与 2025 vs 2026 对比

输出: data/ercot/battery_attribution_{panel,quarterly,events,summary}.csv
用法: python skills/shortfall-price/references/battery_elasticity_attribution.py
"""
import glob
import os

import numpy as np
import pandas as pd

D_ERCOT = r"c:\work\meteo\data\ercot"
PG = 100000.0  # ln/MW -> %/GW
SWITCH = pd.Timestamp("2025-12-15 07:00:00")  # UES 并入 BAT 净额的切换点


def _series(pattern):
    hits = sorted(glob.glob(os.path.join(D_ERCOT, pattern)))
    if len(hits) != 1:
        raise FileNotFoundError(f"预期 1 个文件, 实得 {len(hits)}: {hits}")
    return hits[0]


def load_eia():
    fuels, demand = [], []
    for year in (2025, 2026):
        for m in range(1, 13):
            f = os.path.join(D_ERCOT, f"ercot_fuel_type_data_{year}-{m:02d}.csv")
            r = os.path.join(D_ERCOT, f"ercot_region_data_{year}-{m:02d}.csv")
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
    piv = piv[~piv.index.duplicated(keep="first")].sort_index()
    d = pd.concat(demand).set_index("time")["value"].astype(float)
    d.index = pd.to_datetime(d.index).tz_localize("UTC").tz_localize(None) \
        - pd.Timedelta(hours=1)
    d = d[~d.index.duplicated(keep="first")].sort_index()
    return piv, d


def build_storage(piv):
    bat = piv.get("BAT", pd.Series(0.0, index=piv.index))
    if "UES" in piv.columns:
        ues = piv["UES"].copy()
        ues[ues.index >= SWITCH] = 0.0  # UES 停报后按 0, 防 NaN 传染
    else:
        ues = pd.Series(0.0, index=piv.index)
    pre = piv.index < SWITCH
    net = bat + ues
    dis = bat.where(pre, bat.clip(lower=0))
    chg = (-ues).where(pre, (-bat).clip(lower=0))
    return net, dis, chg


def load_prices():
    rtm = pd.read_csv(_series("ercot_rtm_HB_HOUSTON_*.csv"))
    rtm_h = (rtm.assign(t=pd.to_datetime(rtm["interval_start_utc"])
                        .dt.tz_convert("UTC").dt.tz_localize(None))
             .set_index("t")["spp"].resample("1h").mean())
    dam = pd.read_csv(_series("ercot_dam_HB_HOUSTON_*.csv"))
    dam_h = (dam.assign(t=pd.to_datetime(dam["interval_start_utc"])
                        .dt.tz_convert("UTC").dt.tz_localize(None))
             .set_index("t")["spp"].resample("1h").mean())
    return rtm_h, dam_h


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


def fit_ols(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
    return beta, np.sqrt(np.clip(np.diag(cov), 0, None))


def hour_month_dummies(idx):
    h = idx.hour.values
    m = idx.month.values
    hd = np.column_stack([(h == k).astype(float) for k in range(1, 24)])
    md = np.column_stack([(m == k).astype(float) for k in range(2, 13)])
    return hd, md


def elasticity(day, extra_cols=()):
    """头条口径: ln(RTM) ~ shortfall + [交互项] + wind + demand + h/m FE。
    extra_cols 为 df 中已构造好的数值列 (含主效应), 交互项自身系数即输出对象。"""
    lnp = np.log(day["rtm"].clip(lower=1))
    cols = ["shortfall", "wind", "demand"] + list(extra_cols)
    hd, md = hour_month_dummies(day.index)
    X = np.column_stack([np.ones(len(day))] + [day[c].values for c in cols]
                        + [hd, md])
    beta, se = fit_ols(X, lnp.values)
    names = ["const"] + cols
    return {n: (b, s) for n, b, s in zip(names, beta, se)}


def same_hour_baseline(day, col, ev_mask, event_idx, halfwin=30):
    """事件小时相对基线: 同 hour-of-day, doy 环形距离<=halfwin, 非事件小时中位"""
    s = day[col]
    hours = day.index.hour.values
    doy = day.index.dayofyear.values
    v = s.values
    dd = np.abs(doy[:, None] - doy[None, :])
    dd = np.minimum(dd, 365 - dd)  # 环形
    pos = {t: i for i, t in enumerate(day.index)}
    out = {}
    for t in event_idx:
        i = pos[t]
        w = (hours == hours[i]) & (dd[i] <= halfwin) & (~ev_mask)
        x = v[w]
        x = x[~np.isnan(x)]
        out[t] = np.median(x) if len(x) else np.nan
    return out


def main():
    piv, dem = load_eia()
    rtm_h, dam_h = load_prices()
    net, dis, chg = build_storage(piv)
    cap = dis.rolling("90D", min_periods=24 * 14).quantile(0.99)

    env_parts = []
    for year in (2025, 2026):
        s = piv.get("SUN")
        env_parts.append(clearsky_envelope(s[s.index.year == year]))
    env = pd.concat(env_parts).sort_index()

    panel = pd.DataFrame({
        "solar": piv.get("SUN"), "wind": piv.get("WND"), "demand": dem,
        "rtm": rtm_h, "dam": dam_h,
        "bat_net": net, "bat_dis": dis, "bat_chg": chg, "cap_mw": cap,
        "env": env,
    })
    panel["shortfall"] = (panel["env"] - panel["solar"]).clip(lower=0)
    panel = panel.dropna(subset=["solar", "wind", "demand", "rtm", "cap_mw"])
    panel["year"] = panel.index.year
    panel["quarter"] = panel.index.to_period("Q").astype(str)
    panel.to_csv(os.path.join(D_ERCOT, "battery_attribution_panel.csv"))

    day = panel[panel["solar"] > 50].copy()
    day["cap_gw"] = day["cap_mw"] / 1000.0
    print(f"面板: {panel.index.min()} ~ {panel.index.max()}, "
          f"{len(panel)} 小时 (白天 {len(day)})")
    print(f"容量代理 (滚动90d放电P99): 首段中位 {day['cap_mw'].iloc[:24*30].median():.0f}"
          f" -> 末段中位 {day['cap_mw'].iloc[-24*30:].median():.0f} MW")

    results = {}

    # ---- P1a: 头条复算 (逐年) ----
    print(f"\n{'='*72}\nP1a 头条弹性复算 (逐年)")
    for year, g in day.groupby("year"):
        r = elasticity(g)
        b, s = r["shortfall"]
        results[f"headline_{year}"] = (b, s)
        print(f"  {year}: 缺口弹性 {b*PG:+.3f} %/GW (SE {s*PG:.3f}), n={len(g)}")

    # ---- P1b: 季度弹性路径 ----
    print(f"\n{'='*72}\nP1b 季度弹性路径")
    qrows = []
    for q, g in day.groupby("quarter"):
        if len(g) < 800:
            continue
        r = elasticity(g)
        b, s = r["shortfall"]
        qrows.append({"quarter": q, "n": len(g),
                      "beta_pct_per_gw": b * PG, "se_pct_per_gw": s * PG,
                      "cap_med_mw": g["cap_mw"].median(),
                      "rtm_med": g["rtm"].median(),
                      "shortfall_p95_mw": g["shortfall"].quantile(0.95)})
        print(f"  {q}: {b*PG:+6.2f} (SE {s*PG:.2f}) %/GW | 容量中位 "
              f"{g['cap_mw'].median():5.0f} MW | RTM中位 {g['rtm'].median():6.1f}"
              f" | 缺口P95 {g['shortfall'].quantile(0.95):4.0f} MW | n={len(g)}")
    pd.DataFrame(qrows).to_csv(
        os.path.join(D_ERCOT, "battery_attribution_quarterly.csv"), index=False)

    # ---- P1c: 同季对照 ----
    print(f"\n{'='*72}\nP1c 同季对照 (Jul-Sep)")
    q3 = {}
    for year in (2025, 2026):
        g = day[(day["year"] == year) & (day.index.month.isin([7, 8, 9]))]
        r = elasticity(g)
        q3[year] = r["shortfall"]
        results[f"q3_{year}"] = r["shortfall"]
        print(f"  {year} Jul-Sep: {q3[year][0]*PG:+.2f} "
              f"(SE {q3[year][1]*PG:.2f}) %/GW, n={len(g)}")
    print(f"  同季漂移 2026Q3-2025Q3: {(q3[2026][0]-q3[2025][0])*PG:+.3f} %/GW")

    # ---- P1d: 季节匹配池化漂移 + RTM/DAM 价差弹性 ----
    # 池化漂移(+0.38)仍混季; 只取两年共有的 Q1-Q3, quarter x shortfall FE 化,
    # 年交互 = 干净的同季漂移; ln(RTM/DAM) 弹性剔除天气-价格同动成分
    print(f"\n{'='*72}\nP1d 季节匹配池化漂移 + 价差弹性")
    matched = day[day["quarter"].isin(["2025Q1", "2025Q2", "2025Q3",
                                       "2026Q1", "2026Q2", "2026Q3"])].copy()
    matched["q"] = matched["quarter"].str[5:]
    for qk in ("Q2", "Q3"):
        matched[f"sf_x_{qk}"] = matched["shortfall"] * (matched["q"] == qk)
    matched["sf_x_y26"] = matched["shortfall"] * (matched["year"] == 2026)
    matched["i_y26"] = (matched["year"] == 2026).astype(float)
    r = elasticity(matched, extra_cols=["sf_x_y26", "i_y26",
                                        "sf_x_Q2", "sf_x_Q3"])
    b, s = r["sf_x_y26"]
    results["drift_season_matched"] = (b, s)
    print(f"  季节匹配漂移 (Q1-Q3, quarter FE x shortfall): {b*PG:+.3f} "
          f"(SE {s*PG:.3f}) %/GW => "
          f"{'显著' if abs(b) > 1.96 * s else '不显著'}")
    matched["ln_spread"] = (np.log(matched["rtm"].clip(lower=1))
                            - np.log(matched["dam"].clip(lower=1)))
    for year, g in matched.groupby("year"):
        cols = ["shortfall", "wind", "demand"]
        hd, md = hour_month_dummies(g.index)
        X = np.column_stack([np.ones(len(g))] + [g[c].values for c in cols]
                            + [hd, md])
        beta, se = fit_ols(X, g["ln_spread"].values)
        b, s = beta[1], se[1]
        results[f"spread_{year}"] = (b, s)
        print(f"  {year} 价差弹性 ln(RTM/DAM): {b*PG:+.2f} (SE {s*PG:.2f}) "
              f"%/GW (剔除 DAM 可见部分后的纯实时成分)")

    # ---- P2a: 池化 year x shortfall ----
    print(f"\n{'='*72}\nP2a 池化漂移检验: shortfall x I(2026)")
    d2 = day.copy()
    d2["sf_x_y26"] = d2["shortfall"] * (d2["year"] == 2026)
    d2["i_y26"] = (d2["year"] == 2026).astype(float)
    r = elasticity(d2, extra_cols=["sf_x_y26", "i_y26"])
    b, s = r["sf_x_y26"]
    results["drift_2026_vs_2025"] = (b, s)
    print(f"  漂移项: {b*PG:+.3f} %/GW (SE {s*PG:.3f}) "
          f"=> {'显著' if abs(b) > 1.96 * s else '不显著'}")

    # ---- P2b: 容量交互 ----
    print(f"\n{'='*72}\nP2b 容量交互: shortfall x cap_gw (滚动90d放电P99)")
    d2["sf_x_cap"] = d2["shortfall"] * d2["cap_gw"]
    r = elasticity(d2, extra_cols=["sf_x_cap", "cap_gw"])
    b, s = r["sf_x_cap"]
    results["cap_interaction"] = (b, s)
    sd_cap = d2["cap_gw"].std()
    print(f"  shortfall x cap: {b*1e5:+.4f} %/GW per 1GW容量 (SE {s*1e5:.4f}), "
          f"cap SD={sd_cap:.2f} GW")
    print(f"  => 容量 +1 SD ({sd_cap:.1f} GW) 弹性变化 {b*1e5*sd_cap:+.2f} %/GW "
          f"=> {'储能削弱传导' if b < 0 else '储能放大传导'} "
          f"({('显著' if abs(b) > 1.96 * s else '不显著')})")
    for name, g in [("低容量 cap<6GW", d2[d2["cap_gw"] < 6]),
                    ("高容量 cap>=6GW", d2[d2["cap_gw"] >= 6])]:
        r = elasticity(g)
        b, s = r["shortfall"]
        results[f"{'low' if '<' in name else 'high'}_cap"] = (b, s)
        print(f"  {name}: {b*PG:+.2f} (SE {s*PG:.2f}) %/GW, n={len(g)}")

    # ---- P2c: DAM 安慰剂 (云事件对日前价格应弱于对实时价格) ----
    print(f"\n{'='*72}\nP2c DAM 安慰剂: 云致缺口在日前市场不可见, 系数应显著小于 RTM")
    for year, g in d2.groupby("year"):
        lnp_d = np.log(g["dam"].clip(lower=1))
        cols = ["shortfall", "wind", "demand"]
        hd, md = hour_month_dummies(g.index)
        X = np.column_stack([np.ones(len(g))] + [g[c].values for c in cols]
                            + [hd, md])
        beta, se = fit_ols(X, lnp_d.values)
        b, s = beta[1], se[1]
        results[f"dam_placebo_{year}"] = (b, s)
        print(f"  {year}: DAM 缺口弹性 {b*PG:+.2f} (SE {s*PG:.2f}) %/GW "
              f"vs RTM {results[f'headline_{year}'][0]*PG:+.2f}")

    # ---- P3: 事件机制 ----
    print(f"\n{'='*72}\nP3 事件机制: 缺口>=1.5GW, 15-23UTC, solar>=1.5GW")
    ev_mask = (day["shortfall"] >= 1500)
    ev = day[ev_mask & day.index.hour.isin(range(15, 24))
             & (day["solar"] >= 1500)].copy()
    print(f"  事件小时: {len(ev)} ({ev.groupby('year').size().to_dict()})")
    if len(ev) == 0:
        print("  无事件, 跳过 P3")
        return save_summary(results)

    base_rtm = same_hour_baseline(day, "rtm", ev_mask, ev.index)
    base_net = same_hour_baseline(day, "bat_net", ev_mask, ev.index)
    base_dis = same_hour_baseline(day, "bat_dis", ev_mask, ev.index)
    ev["rtm_base"] = pd.Series(base_rtm)
    ev["net_base"] = pd.Series(base_net)
    ev["dis_base"] = pd.Series(base_dis)
    ev["ln_premium"] = (np.log(ev["rtm"].clip(lower=1))
                        - np.log(ev["rtm_base"].clip(lower=1)))
    ev["net_response"] = ev["bat_net"] - ev["net_base"]
    ev["dis_response"] = ev["bat_dis"] - ev["dis_base"]
    ev["sf_gw"] = ev["shortfall"] / 1000.0
    ev["resp_gw"] = ev["net_response"] / 1000.0
    ev = ev.dropna(subset=["ln_premium", "net_response", "rtm_base"])
    ev.to_csv(os.path.join(D_ERCOT, "battery_attribution_events.csv"))

    for year, g in ev.groupby("year"):
        print(f"  {year}: n={len(g)}, 缺口中位 {g['shortfall'].median():.0f} MW, "
              f"ln溢价中位 {g['ln_premium'].median()*100:+.1f}%, "
              f"储能净响应中位 {g['net_response'].median():+.0f} MW "
              f"(P90 {g['net_response'].quantile(0.9):+.0f})")
    corr = ev["ln_premium"].corr(ev["net_response"])
    print(f"  溢价 x 储能净响应相关: r={corr:+.3f} "
          f"(负=储能响应大的事件溢价低)")
    print(f"  事件小时风电中位: " + "  ".join(
        f"{y}: {g['wind'].median():.0f} MW (风/缺口比 "
        f"{g['wind'].median()/g['shortfall'].median():.2f})"
        for y, g in ev.groupby("year")))
    print(f"  事件小时 RTM 中位: " + "  ".join(
        f"{y}: {g['rtm'].median():.1f}" for y, g in ev.groupby("year")))
    rw = ev["net_response"].corr(ev["wind"])
    print(f"  储能净响应 x 事件风电相关: r={rw:+.3f} "
          f"(负=风大的事件储能少放电/多充电)")

    if len(ev) > 60:
        X = np.column_stack([
            np.ones(len(ev)), ev["sf_gw"], ev["resp_gw"],
            ev["sf_gw"] * ev["resp_gw"],
            np.column_stack([(ev.index.hour.values == k).astype(float)
                             for k in range(16, 23)]),
        ])
        beta, se = fit_ols(X, (ev["ln_premium"] * 100).values)
        for n, b, s in zip(["const", "sf_gw(缺口GW)", "resp_gw(净响应GW)",
                            "sf x resp 交互"], beta, se):
            print(f"    {n:16s}: {b:+8.2f} (SE {s:.2f})")
        results["event_sf"] = (beta[1], se[1])
        results["event_resp"] = (beta[2], se[2])
        results["event_inter"] = (beta[3], se[3])

    print(f"\n  缺口分箱 x 年份 (ln溢价% 中位 | 储能净响应中位 MW):")
    for lo, hi in [(1.5, 2.5), (2.5, 3.5), (3.5, 99)]:
        seg = ev[(ev["sf_gw"] >= lo) & (ev["sf_gw"] < hi)]
        if len(seg) < 5:
            continue
        line = f"    [{lo:.1f},{hi:.1f}) GW:"
        for year in (2025, 2026):
            g = seg[seg["year"] == year]
            if len(g) == 0:
                continue
            line += (f"  {year}: n={len(g)}, "
                     f"{g['ln_premium'].median()*100:+5.0f}% | "
                     f"{g['net_response'].median():+5.0f}MW")
        print(line)

    return save_summary(results)


def save_summary(results):
    rows = []
    for k, (b, s) in results.items():
        rows.append({"metric": k, "beta": b, "se": s})
    pd.DataFrame(rows).to_csv(
        os.path.join(D_ERCOT, "battery_attribution_summary.csv"), index=False)
    print(f"\n已保存: battery_attribution_{{panel,quarterly,events,summary}}.csv")


if __name__ == "__main__":
    main()
