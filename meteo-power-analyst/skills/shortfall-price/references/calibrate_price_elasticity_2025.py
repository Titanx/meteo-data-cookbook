"""ΔPV -> Δ电价 弹性标定 (2025 + 2026 对照, ERCOT)
v2 关键修正: 事件 = 相对晴空包络的光伏缺口 (shortfall), 而非绝对 1h 降幅
  (绝对降幅把市场可预期的自然日落下坡也计入, 无价格冲击信号;
   2025 实证: |Δsolar|>1500MW 的 1300 个小时 RTM-DAM 价差与正常小时基本相同)
面板: EIA-930 小时光伏/风电/需求 + GridStatus RTM(15min->h)/DAM HB_HOUSTON
晴空包络: 同 hour-of-day ±15 天窗口内光伏出力 P95 (数据驱动, 无需建模)
回归 (numpy lstsq + hour/month FE):
  水平:  ln(RTM) ~ solar + wind + demand + FE          -> βs (%/GW)
  缺口:  ln(RTM) ~ shortfall + wind + demand + FE      -> β_short (%/GW) 头条弹性
  爬坡:  Δln(RTM) ~ Δsolar + Δwind + Δdemand + hourFE  -> 事件内 1h 弹性
注意: EIA-930 小时时间戳为区间结束 -> -1h; RTM/DAM 区间起点; 负价格 clip $1
输出: stdout + data/ercot/price_elasticity_2025.csv + ercot_hourly_panel_{year}.csv
"""
import os

import numpy as np
import pandas as pd

D_ERCOT = r"c:\work\meteo\data\ercot"
RTM = os.path.join(D_ERCOT, "ercot_rtm_HB_HOUSTON_2025-01-01_2026-09-07.csv")
DAM = os.path.join(D_ERCOT, "ercot_dam_HB_HOUSTON_2025-01-01_2026-09-07.csv")
OUT_COEF = os.path.join(D_ERCOT, "price_elasticity_2025.csv")

rtm_h, dam_h = None, None


def load_prices():
    global rtm_h, dam_h
    if rtm_h is not None:
        return rtm_h, dam_h
    rtm = pd.read_csv(RTM)
    rtm["t"] = pd.to_datetime(rtm["interval_start_utc"]).dt.tz_convert("UTC")
    rtm_h = rtm.set_index(rtm["t"].dt.tz_localize(None))["spp"] \
        .resample("1h").mean()
    dam = pd.read_csv(DAM)
    dam["t"] = pd.to_datetime(dam["interval_start_utc"]).dt.tz_convert("UTC")
    dam_h = dam.set_index(dam["t"].dt.tz_localize(None))["spp"] \
        .resample("1h").mean()
    return rtm_h, dam_h


def load_eia_year(year):
    months = list(range(1, 13)) if year == 2025 else list(range(1, 9))
    fuels, demand = [], []
    for m in months:
        f = os.path.join(D_ERCOT, f"ercot_fuel_type_data_{year}-{m:02d}.csv")
        r = os.path.join(D_ERCOT, f"ercot_region_data_{year}-{m:02d}.csv")
        if not os.path.exists(f):
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
    """数据驱动晴空包络: 每个 (hour, doy) 取 ±halfwin 天同小时光伏出力 P95"""
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
    env = pd.Series(np.nan_to_num(env, nan=0.0), index=solar.index)
    # 包络不应低于实际值太多: 校正为 max(env, 0)
    return env.clip(lower=0)


def fit_ols(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
    return beta, np.sqrt(np.diag(cov))


def add_fe(values, prefix, ref=None):
    s = pd.Series(np.asarray(values))
    cats = sorted(s.unique())
    if ref is None:
        ref = cats[0]
    mats = [(s == c).astype(float).values for c in cats if c != ref]
    names = [f"{prefix}{c}" for c in cats if c != ref]
    if not mats:
        return np.zeros((len(s), 0)), names
    return np.column_stack(mats), names


def regress(y, num_df, num_cols, fe_specs):
    mats = [np.column_stack([np.ones(len(y))] + [
        num_df[c].values for c in num_cols])]
    for values, prefix, ref in fe_specs:
        m, _ = add_fe(values, prefix, ref)
        mats.append(m)
    X = np.column_stack(mats)
    beta, se = fit_ols(X, y)
    names = ["const"] + num_cols
    return names, beta, se


def fit_year(year):
    piv, dem = load_eia_year(year)
    rtm, dam = load_prices()
    panel = pd.DataFrame({
        "solar": piv.get("SUN"), "wind": piv.get("WND"),
        "demand": dem, "rtm": rtm, "dam": dam,
    }).dropna()
    full_solar = panel["solar"].copy()
    env = clearsky_envelope(full_solar)
    panel["env"] = env
    panel["shortfall"] = (panel["env"] - panel["solar"]).clip(lower=0)

    day = panel[panel["solar"] > 50].copy()
    print(f"\n{'='*70}\n{year}: {len(day)} 白天小时, "
          f"光伏中位 {day['solar'].median():.0f} MW, 最大 {day['solar'].max():.0f} MW")

    lnp = np.log(day["rtm"].clip(lower=1))
    out = {}

    # 水平回归
    names, beta, se = regress(
        lnp.values, day, ["solar", "wind", "demand"],
        [(day.index.hour, "h", None), (day.index.month, "m", None)])
    bs = beta[names.index("solar")]
    out["level_solar"] = (bs, se[names.index("solar")])
    # 系数以 MW 计 (ln/MW): %/GW = beta * 1000(MW/GW) * 100(%)
    PG = 100000.0
    print(f"  水平: 光伏 +1 GW -> RTM {bs*PG:+.2f}% "
          f"(SE {se[names.index('solar')]*PG:.2f}%)"
          f" | 风电 {beta[names.index('wind')]*PG:+.2f}%/GW | "
          f"需求 {beta[names.index('demand')]*PG:+.2f}%/GW")

    # 缺口回归 (头条弹性)
    names, beta, se = regress(
        lnp.values, day, ["shortfall", "wind", "demand"],
        [(day.index.hour, "h", None), (day.index.month, "m", None)])
    bsh = beta[names.index("shortfall")]
    out["shortfall"] = (bsh, se[names.index("shortfall")])
    print(f"  缺口: 光伏缺口 -1 GW -> RTM {bsh*PG:+.2f}% "
          f"(SE {se[names.index('shortfall')]*PG:.2f}%)"
          f" | 风电 {beta[names.index('wind')]*PG:+.2f}%/GW")

    # 爬坡回归
    reg = pd.DataFrame({
        "dlnp": lnp.diff(), "d_solar": day["solar"].diff(),
        "d_wind": day["wind"].diff(), "d_demand": day["demand"].diff(),
        "hour": day.index.hour,
    }).dropna()
    names2, beta2, se2 = regress(
        reg["dlnp"].values, reg, ["d_solar", "d_wind", "d_demand"],
        [(reg["hour"], "h", None)])
    br = beta2[names2.index("d_solar")]
    out["ramp"] = (br, se2[names2.index("d_solar")])
    print(f"  爬坡: 1h 内光伏 -1 GW -> RTM {br*PG:+.2f}% "
          f"(SE {se2[names2.index('d_solar')]*PG:.2f}%)")

    # 高需求区 (热浪场景) 弹性: 2022-07 事件多发生在 72~80 GW 需求区间
    hot = day[day["demand"] >= 72000]
    if len(hot) > 500:
        lnp_h = np.log(hot["rtm"].clip(lower=1))
        names, beta, se = regress(
            lnp_h.values, hot, ["shortfall", "wind", "demand"],
            [(hot.index.hour, "h", None), (hot.index.month, "m", None)])
        bh = beta[names.index("shortfall")]
        out["shortfall_hot"] = (bh, se[names.index("shortfall")])
        print(f"  高需求区 (>=72GW, n={len(hot)}): 缺口 -1 GW -> RTM "
              f"{bh*PG:+.2f}% (SE {se[names.index('shortfall')]*PG:.2f}%), "
              f"RTM 中位 {hot['rtm'].median():.1f} $/MWh")

    # 冲击事件统计
    ev = day[(day["shortfall"] >= 1500) & (day.index.hour.isin(range(15, 24)))
             & (day["solar"] >= 1500)]
    same_h = day[day.index.hour.isin(ev.index.hour.unique())]
    print(f"  冲击事件 (缺口>=1.5GW, 15-23UTC): {len(ev)} 小时")
    if len(ev):
        print(f"    事件 RTM 中位 {ev['rtm'].median():.1f} vs 同小时正常 "
              f"{same_h.loc[~same_h.index.isin(ev.index), 'rtm'].median():.1f} $/MWh")
        sp = (ev["rtm"] - ev["dam"]).median()
        spn = (same_h["rtm"] - same_h["dam"]).median()
        print(f"    事件 RTM-DAM 价差中位 {sp:+.1f} vs 正常 {spn:+.1f} $/MWh")
        print(f"    缺口中位 {ev['shortfall'].median():.0f} MW, 最大 {ev['shortfall'].max():.0f} MW")

    panel.to_csv(os.path.join(D_ERCOT, f"ercot_hourly_panel_{year}.csv"))
    return out


def main():
    allout = {}
    for year in [2025, 2026]:
        allout[year] = fit_year(year)

    print(f"\n{'='*70}\n弹性汇总 (%/GW):")
    rows = []
    PG = 100000.0
    for year, o in allout.items():
        for model, (b, s) in o.items():
            rows.append({"year": year, "model": model,
                         "beta_per_gw_pct": b * PG, "se_per_gw_pct": s * PG})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    t.to_csv(OUT_COEF, index=False)
    print(f"已保存: {OUT_COEF}")


if __name__ == "__main__":
    main()
