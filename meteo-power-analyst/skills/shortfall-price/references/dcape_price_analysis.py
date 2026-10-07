# -*- coding: utf-8 -*-
"""方向4: 探空 DCAPE × ERCOT 电价联动分析 (PS-046)

问题: 早探空 (12Z, 当地 07:00 发布) 的 DCAPE (下沉对流有效位能) 能否
事前指示当天下午-傍晚 (当地 13-22h) 的 RTM 尖峰/波动? 机制上是雷暴
下击暴流 → (a) 阵风冲击风电爬坡 (b) 雷暴云遮蔽光伏缺口 (c) 降温降需求。

样本: 2025-06-15~09-15 + 2026-06-15~09-30 当地日, 6 站探空
(72249 FWD / 72251 CRP / 72261 DRT / 72265 MAF / 72340 LIT / 72357 OUN)。

纪律 (继承 PS-043/044): ①区分"事前" (12Z 早探空) 与"同期" (00Z 晚探空/
已实现缺口) 信息; ②先算同期上界再谈预报价值; ③跨年分报。

输入:
  data/sounding/{station}/sounding_{st}_{YYYYMMDD}{00,12}Z.csv  (DCAPE 列)
  data/ercot/shortfall_physical_2025_2026.csv     (逐时 UTC: solar/wind/demand/rtm/dam/shortfall_phys)
  data/ercot/ercot_rtm_HB_{HOUSTON,NORTH,SOUTH,WEST}_2025-01-01_2026-10-01.csv (15min)
  data/ercot/pv_node_hourly_premium.csv / pv_node_dispersion.csv  (2026-09 窗口, 方向3)
输出:
  data/ercot/dcape_daily_panel.csv    (逐日面板)
  data/ercot/dcape_price_results.csv   ([X] 指标行)
用法: python skills/shortfall-price/references/dcape_price_analysis.py
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)

SD = r"c:\work\meteo\data\sounding"
D = r"c:\work\meteo\data\ercot"
OUT_PANEL = os.path.join(D, "dcape_daily_panel.csv")
OUT_RES = os.path.join(D, "dcape_price_results.csv")

STATIONS = {
    "72249": ("FWD", "Fort Worth"),
    "72251": ("CRP", "Corpus Christi"),
    "72261": ("DRT", "Del Rio"),
    "72265": ("MAF", "Midland"),
    "72340": ("LIT", "Little Rock"),
    "72357": ("OUN", "Norman"),
}
YEARS = {2025: ("2025-06-15", "2025-09-15"), 2026: ("2026-06-15", "2026-09-30")}
EVE_HOURS = range(13, 23)          # 当地 13:00-22:59
DAY_HOURS = range(7, 21)            # 光照窗口
HUBS = ["HOUSTON", "NORTH", "SOUTH", "WEST"]

rows = []


def rec(tag, name, val, note=""):
    rows.append({"tag": tag, "metric": name, "value": val, "note": note})
    try:
        v = f"{val:.4f}"
    except (TypeError, ValueError):
        v = str(val)
    print(f"[{tag}] {name:44s} {v:>12s}  {note}", flush=True)


def ols(y, X):
    """HC1 稳健标准误 OLS; X 不含常数则报错"""
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ (X.T @ y)
    e = y - X @ b
    s2 = X.T @ ((e ** 2)[:, None] * X) * (n / (n - k))
    cov = XtX_inv @ s2 @ XtX_inv
    return b, np.sqrt(np.diag(cov))


def ols_cluster(X, y, groups, n_cl=None):
    """按 groups 聚类的 cluster-robust SE OLS"""
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ (X.T @ y)
    e = y - X @ b
    if n_cl is None:
        n_cl = len(np.unique(groups))
    meat = np.zeros((k, k))
    for g in np.unique(groups):
        m = groups == g
        Xg = X[m] * e[m, None]
        meat += Xg.T @ Xg
    cov = XtX_inv @ meat @ XtX_inv * ((n - 1) / (n - k)) * (n_cl / (n_cl - 1))
    return b, np.sqrt(np.diag(cov))


def spear(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return np.nan, int(m.sum())
    return float(pd.Series(a[m]).corr(pd.Series(b[m]), method="spearman")), int(m.sum())


# ── 1. 探空 → 站点级 DCAPE 表 ─────────────────────────────
def load_soundings():
    """返回 DataFrame(date_utc, hour_z, station, dcape)"""
    out = []
    for st, (code, name) in STATIONS.items():
        for f in glob.glob(os.path.join(SD, st, "*.csv")):
            m = re.search(r"_(\d{8})(\d{2})Z\.csv$", os.path.basename(f))
            if not m:
                continue
            d, h = m.group(1), int(m.group(2))
            if h not in (0, 12):
                continue
            try:
                head = pd.read_csv(f, nrows=1)
            except Exception:
                continue
            if "DCAPE" not in head.columns:
                continue
            dc = pd.read_csv(f, usecols=["DCAPE"]).iloc[0, 0]
            try:
                dc = float(dc)
            except (TypeError, ValueError):
                continue
            out.append({"date_utc": pd.Timestamp(d), "hour_z": h,
                        "station": code, "dcape": dc})
    df = pd.DataFrame(out)
    df["local_ts"] = df["date_utc"].dt.tz_localize("UTC").dt.tz_convert("America/Chicago")
    # 12Z -> 当地同日早晨; 00Z -> 前一当地日晚 19:00
    df["local_day"] = df["local_ts"].dt.normalize()
    df.loc[df["hour_z"] == 0, "local_day"] -= pd.Timedelta(days=1)
    return df


# ── 2. 价格/出力小时面板 (UTC → 当地) ────────────────────
def load_hourly():
    """hourly_panel (完整) + NSRDB 晴空 → PV 物理缺口 (PS-024 口径)"""
    frames = []
    for yr in (2025, 2026):
        h = pd.read_csv(os.path.join(D, f"ercot_hourly_panel_{yr}.csv"),
                        index_col=0, parse_dates=True)
        frames.append(h[["solar", "wind", "demand", "rtm", "dam"]])
    h = pd.concat(frames)
    h = h[~h.index.duplicated(keep="last")].sort_index()

    cs = pd.read_csv(r"c:\work\meteo\data\nsrdb\pv_clearsky_hourly_2025_2026.csv",
                     index_col=0, parse_dates=True)
    cs.index = pd.to_datetime(cs.index, utc=True).tz_localize(None)
    cs = cs[~cs.index.duplicated()]
    h = h.join(cs, how="inner")
    raw_gap = h["clearsky_mw"] - h["solar"]
    off5 = raw_gap.groupby(h.index.hour).quantile(0.05)
    h["shortfall_phys"] = (raw_gap - off5.reindex(h.index.hour).values).clip(lower=0)

    h.index.name = "ts_utc"
    h = h.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT").tz_convert("America/Chicago")
    h = h[~h.index.isna()]
    h["local_day"] = h.index.normalize()
    h["hour"] = h.index.hour
    return h


def load_rtm15():
    """4 hub 15min spp → 当地 (index=local_ts, columns=hubs)"""
    cols = {}
    for hb in HUBS:
        f = os.path.join(D, f"ercot_rtm_HB_{hb}_2025-01-01_2026-10-01.csv")
        r = pd.read_csv(f, usecols=["interval_start_utc", "spp"])
        r["ts"] = pd.to_datetime(r["interval_start_utc"], utc=True)
        s = r.set_index("ts")["spp"].sort_index()
        s = s[~s.index.duplicated()]
        cols[hb] = s
    w = pd.DataFrame(cols).dropna()
    w = w.tz_convert("America/Chicago")
    w["local_day"] = w.index.normalize()
    return w


# ── 3. 逐日面板 ───────────────────────────────────────────
def build_daily(snd, hr, r15):
    days = []
    for yr, (d0, d1) in YEARS.items():
        d0, d1 = pd.Timestamp(d0, tz="America/Chicago"), pd.Timestamp(d1, tz="America/Chicago")
        d = d0
        while d <= d1:
            days.append(d)
            d += pd.Timedelta(days=1)
    idx = pd.DatetimeIndex(days)

    # 探空聚合
    m12 = snd[snd["hour_z"] == 12]
    m00 = snd[snd["hour_z"] == 0]
    g12max = m12.groupby("local_day")["dcape"].max()
    g12mean = m12.groupby("local_day")["dcape"].mean()
    g12n = m12.groupby("local_day")["dcape"].count()
    g00max = m00.groupby("local_day")["dcape"].max()
    per_st = {}
    for code, _ in STATIONS.values():
        per_st[code] = m12[m12["station"] == code].groupby("local_day")["dcape"].max()

    # 傍晚窗口 (当地 13-22)
    eve = hr[(hr["hour"] >= 13) & (hr["hour"] <= 22)]
    eveh = eve.groupby("local_day")
    r15e = r15[(r15.index.hour >= 13) & (r15.index.hour <= 22)]
    r15h = r15e.groupby("local_day")

    recs = []
    for d in idx:
        day = hr[hr["local_day"] == d]
        if len(day) < 20:
            continue
        ev = eve[eve["local_day"] == d]
        rw = r15e[r15e["local_day"] == d]
        n_eve_h = len(ev)
        n_eve_i = len(rw)
        if n_eve_h < 9 or n_eve_i < 30:
            continue
        r = {"local_day": d.date().isoformat(), "year": d.year,
             "dcape_m": g12max.get(d, np.nan), "dcape_m_mean": g12mean.get(d, np.nan),
             "n_st12": g12n.get(d, 0), "dcape_e": g00max.get(d, np.nan)}
        for code, _ in STATIONS.values():
            r[f"dcape_{code}"] = per_st[code].get(d, np.nan)

        r["rtm_eve_max"] = float(rw["HOUSTON"].max())
        for hb in HUBS:
            r[f"rtm_eve_max_{hb}"] = float(rw[hb].max())
        r["n200"] = int((rw["HOUSTON"] >= 200).sum())
        r["n500"] = int((rw["HOUSTON"] >= 500).sum())
        r["spike200"] = int(r["rtm_eve_max"] >= 200)
        r["spike500"] = int(r["rtm_eve_max"] >= 500)
        r["rtm_eve_med"] = float(ev["rtm"].median())
        r["rtm_eve_mean"] = float(ev["rtm"].mean())
        r["dam_eve_mean"] = float(ev["dam"].mean())
        prem = np.log(ev["rtm"].clip(lower=1) / ev["dam"].clip(lower=1))
        r["prem_eve"] = float(prem.mean())
        r["vol_eve"] = float(prem.quantile(0.9) - prem.quantile(0.1))

        dayday = day[(day["hour"] >= 7) & (day["hour"] <= 20)]
        r["pv_short_max"] = float(dayday["shortfall_phys"].max()) / 1000.0
        evd = day[(day["hour"] >= 13) & (day["hour"] <= 20)]
        r["pv_short_eve"] = float(evd["shortfall_phys"].max()) / 1000.0
        w_ = day["wind"].astype(float)
        dw = w_.diff().dropna() / 1000.0
        r["wind_ramp_up"] = float(dw.max())
        r["wind_ramp_dn"] = float(dw.min())
        r["wind_mean"] = float(day["wind"].mean()) / 1000.0
        r["dem_peak"] = float(day["demand"].max()) / 1000.0
        recs.append(r)

    df = pd.DataFrame(recs).set_index("local_day")
    df.index = pd.to_datetime(df.index)
    df["rtm_eve_max_lag1"] = df.groupby("year")["rtm_eve_max"].shift(1)
    df["dcape_e_lag1"] = df.groupby("year")["dcape_e"].shift(1)
    df["dow"] = df.index.dayofweek
    return df


# ── 4. 分析 ───────────────────────────────────────────────
def main():
    snd = load_soundings()
    hr = load_hourly()
    r15 = load_rtm15()
    df = build_daily(snd, hr, r15)
    df.to_csv(OUT_PANEL)

    # [0] 覆盖
    for yr in (2025, 2026):
        d = df[df["year"] == yr]
        rec("0", f"{yr} 天数 (傍晚窗口+全日出力)", len(d), f"DCAPE覆盖 {(d['dcape_m'].notna()).sum()}")
        rec("0", f"{yr} dcape_m 中位/最大 (J/kg)",
             f"{d['dcape_m'].median():.0f}/{d['dcape_m'].max():.0f}",
             f"12Z站数中位 {d['n_st12'].median():.0f}; 傍晚max中位 ${d['rtm_eve_max'].median():.0f}")
    pooled = df[df["dcape_m"].notna()].copy()

    # [A] 事前: 12Z DCAPE -> 当晚
    for yr in (2025, 2026, 0):
        d = pooled if yr == 0 else pooled[pooled["year"] == yr]
        if len(d) < 30:
            continue
        y = np.log(d["rtm_eve_max"].clip(lower=1)).values
        x = d["dcape_m"].values / 1000.0
        tag = f"A{yr}" if yr else "A"
        r, n = spear(x, y)
        rec(tag, f"ρ(dcape_m, ln rtm_eve_max) Spearman", r, f"n={n}{'; pooled' if yr == 0 else ''}")
        X = np.column_stack([np.ones(len(d)), x])
        b, s = ols(y, X)
        rec(tag, f"OLS ln(rtm_eve_max) ~ dcape_m (ln /kJ)", b[1], f"SE {s[1]:.4f}")
        if yr == 0:  # pooled + 年FE
            yr_d = (d["year"] == 2026).astype(float)
            X = np.column_stack([np.ones(len(d)), x, yr_d])
            b, s = ols(y, X)
            rec(tag, "OLS 含年FE ln /kJ", b[1], f"SE {s[1]:.4f}")

    # [A2] 事前 vs 同期 (00Z 晚探空) 与滞后
    d = pooled
    y = np.log(d["rtm_eve_max"].clip(lower=1)).values
    for v, lab in [("dcape_e", "同期00Z晚探空 dcape_e"),
                   ("dcape_e_lag1", "昨傍晚 dcape_e_lag1"),
                   ("dcape_m_mean", "dcape_m 均值口径")]:
        x = d[v].values / 1000.0
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 50:
            continue
        b, s = ols(y[m], np.column_stack([np.ones(m.sum()), x[m]]))
        rec("A2", f"{lab} ln /kJ", b[1], f"SE {s[1]:.4f}; n={int(m.sum())}")
    r, n = spear(d["dcape_m"].values, d["dcape_e"].values)
    rec("A2", "ρ(dcape_m, dcape_e) 同日早晚", r, f"n={n}; 晨探空持续性")

    # [A3] 持续性骨架 + 增量
    dl = pooled.dropna(subset=["rtm_eve_max_lag1"])
    y = np.log(dl["rtm_eve_max"].clip(lower=1)).values
    xl = np.log(dl["rtm_eve_max_lag1"].clip(lower=1)).values
    xm = dl["dcape_m"].values / 1000.0
    b1, s1 = ols(y, np.column_stack([np.ones(len(dl)), xl]))
    rec("A3", "骨架: ln(eve_max) ~ ln(lag1) 斜率", b1[1], f"SE {s1[1]:.3f}; R2基础")
    b2, s2_ = ols(y, np.column_stack([np.ones(len(dl)), xl, xm]))
    e1 = y - np.column_stack([np.ones(len(dl)), xl]) @ b1
    e2 = y - np.column_stack([np.ones(len(dl)), xl, xm]) @ b2
    r2_1 = 1 - e1.var() / y.var()
    r2_2 = 1 - e2.var() / y.var()
    rec("A3", "骨架 R²", r2_1, "")
    rec("A3", "骨架 + dcape_m R²", r2_2, f"增量 {r2_2 - r2_1:+.4f}; dcape系数 {b2[2]:+.4f} (SE {s2_[2]:.4f})")

    # [A4] 尖峰条件表 (年内三分位)
    for thr in (200, 500):
        for yr in (2025, 2026):
            d = pooled[pooled["year"] == yr].dropna(subset=["dcape_m"])
            if len(d) < 40:
                continue
            q = d["dcape_m"].quantile([1 / 3, 2 / 3]).values
            bins = np.digitize(d["dcape_m"], q)
            for i in range(3):
                dd = d[bins == i]
                if len(dd) == 0:
                    continue
                rec(f"A4-{yr}", f"P(≥{thr} | DCAPE{'低中高'[i]})", float(dd[f"spike{thr}"].mean()),
                    f"n={len(dd)}; DCAPE中位 {dd['dcape_m'].median():.0f}")
        d = pooled.dropna(subset=["dcape_m"])
        q = d["dcape_m"].quantile([1 / 3, 2 / 3]).values
        bins = np.digitize(d["dcape_m"], q)
        for i in range(3):
            dd = d[bins == i]
            rec("A4-P", f"P(≥{thr} | DCAPE{'低中高'[i]}) pooled", float(dd[f"spike{thr}"].mean()),
                f"n={len(dd)}; DCAPE中位 {dd['dcape_m'].median():.0f}")

    # [A5] 小时级傍晚回归 (10h × N日, 小时FE, 日聚类SE)
    eve_hrs = hr[(hr["hour"] >= 13) & (hr["hour"] <= 22)][["rtm", "local_day", "hour"]].copy()
    eve_hrs["day"] = eve_hrs["local_day"].dt.tz_localize(None)
    for yr, lab in [(2025, "2025"), (2026, "2026"), (0, "pooled")]:
        dsel = pooled if yr == 0 else pooled[pooled["year"] == yr]
        dsel = dsel.dropna(subset=["dcape_m"])
        if len(dsel) < 40:
            continue
        idx_d = {d: i for i, d in enumerate(dsel.index)}
        sub = eve_hrs[eve_hrs["day"].isin(idx_d)]
        if len(sub) < 300:
            continue
        yv = np.log(sub["rtm"].clip(lower=1.0).values)
        xv = sub["day"].map(dsel["dcape_m"]).values / 1000.0
        harr = sub["hour"].values
        cols = [np.ones(len(yv)), xv] + [(harr == h).astype(float) for h in range(14, 23)]
        if yr == 0:
            cols.append((sub["day"].dt.year.values == 2026).astype(float))
        X = np.column_stack(cols)
        cl = sub["day"].map(idx_d).values
        b, s = ols_cluster(X, yv, cl)
        rec("A5", f"{lab}: 小时ln(rtm) ~ dcape_m (ln /kJ)", b[1],
            f"SE {s[1]:.4f}; n={len(yv)} 聚类=日{' + 年FE' if yr == 0 else ''}")

    # [A5h] 分小时系数 (每时单独日级回归, 供小时×弹性剖面图)
    for h in range(13, 23):
        sub_h = eve_hrs[eve_hrs["hour"] == h]
        m2 = sub_h["day"].isin({d for d in pooled.index if np.isfinite(pooled.loc[d, "dcape_m"])})
        sh = sub_h[m2]
        if len(sh) < 40:
            continue
        yh = np.log(sh["rtm"].clip(lower=1.0).values)
        xh = sh["day"].map(pooled["dcape_m"]).values / 1000.0
        ok = np.isfinite(xh) & np.isfinite(yh)
        if ok.sum() < 40:
            continue
        bh, sh_se = ols(yh[ok], np.column_stack([np.ones(ok.sum()), xh[ok]]))
        rec("A5h", f"hour {h:02d} ln(rtm) ~ dcape_m (ln /kJ)", bh[1],
            f"SE {sh_se[1]:.4f}; n={int(ok.sum())}")

    # [A6] DAM 吸收检验: 12Z 探空 (07:00 CDT 可得) 早于 DAM 出清 (~10:00 CDT),
    #      若市场定价雷暴风险, ln(DAM_eve) 应随 dcape_m 上升; RTM-DAM 为残余冲击
    for yr, lab in [(2025, "2025"), (2026, "2026"), (0, "pooled")]:
        dsel = pooled if yr == 0 else pooled[pooled["year"] == yr]
        if len(dsel) < 40:
            continue
        yd = np.log(dsel["dam_eve_mean"].clip(lower=1)).values
        xd = dsel["dcape_m"].values / 1000.0
        cols = [np.ones(len(dsel)), xd]
        if yr == 0:
            cols.append((dsel["year"] == 2026).astype(float).values)
        b, s = ols(yd, np.column_stack(cols))
        rec("A6", f"{lab}: ln(DAM_eve) ~ dcape_m (ln /kJ)", b[1], f"SE {s[1]:.4f}; n={len(dsel)}")
        spread = np.log(dsel["rtm_eve_mean"].clip(lower=1)).values - yd
        b2_, s2_ = ols(spread, np.column_stack(cols))
        rec("A6", f"{lab}: ln(RTM/DAM_eve) ~ dcape_m (ln /kJ)", b2_[1],
            f"SE {s2_[1]:.4f}; 已实现溢价通道")

    # [B] 机制
    d = pooled
    for v, lab in [("pv_short_max", "当日PV物理缺口max (GW)"),
                   ("pv_short_eve", "傍晚PV缺口max (GW)"),
                   ("wind_ramp_up", "风电1h最大上爬坡 (GW)"),
                   ("wind_mean", "风电日均出力 (GW)"),
                   ("dem_peak", "需求峰 (GW)")]:
        r_, n = spear(d["dcape_m"].values, d[v].values)
        rec("B1", f"ρ(dcape_m, {lab})", r_, f"n={n}")
    # 中介: 缺口通道 vs 爬坡通道
    dd = d.dropna(subset=["pv_short_max", "wind_ramp_up", "dem_peak"])
    y = np.log(dd["rtm_eve_max"].clip(lower=1)).values
    xm = dd["dcape_m"].values / 1000.0
    m0 = np.isfinite(xm) & np.isfinite(y)
    if m0.sum() < 40:
        rec("B2", "样本不足", int(m0.sum()), "跳过 B2/B3")
    b0, _ = ols(y[m0], np.column_stack([np.ones(m0.sum()), xm[m0]]))
    rec("B2", "B2-0 纯DCAPE系数 (ln /kJ)", b0[1], f"n={m0.sum()}")
    for extra, lab in [ (["pv_short_max"], "+PV缺口"),
                        (["wind_ramp_up"], "+风电爬坡"),
                        (["pv_short_max", "wind_ramp_up"], "+双通道"),
                        (["pv_short_max", "wind_ramp_up", "dem_peak"], "+双通道+需求")]:
        X = np.column_stack([np.ones(m0.sum()), xm[m0]] +
                            [dd[c].values[m0] for c in extra])
        b, s = ols(y[m0], X)
        rec("B2", f"B2 {lab}: DCAPE系数", b[1],
            f"SE {s[1]:.4f}; 其他 " + "; ".join(f"{c}={b[i + 2]:+.3f}" for i, c in enumerate(extra)))
    # 同期上界
    X = np.column_stack([np.ones(m0.sum())] + [dd[c].values[m0] for c in
                        ["pv_short_max", "wind_ramp_up", "dem_peak"]])
    b, s = ols(y[m0], X)
    e = y[m0] - X @ b
    ctrl = ["pv_short_max", "wind_ramp_up", "dem_peak"]
    rec("B3", "同期上界: 已实现缺口/爬坡/需求 R²",
        1 - e.var() / y[m0].var(),
        "; ".join(f"{c}={b[i + 1]:+.3f}(SE {s[i + 1]:.3f})" for i, c in enumerate(ctrl)))
    Xd = np.column_stack([np.ones(m0.sum()), xm[m0]])
    ed = y[m0] - Xd @ ols(y[m0], Xd)[0]
    rec("B3", "纯DCAPE R²", 1 - ed.var() / y[m0].var(), "与同期上界对比")

    # [B4] 方向3 事件日联动 (2026-09 窗口)
    try:
        pnp = pd.read_csv(os.path.join(D, "pv_node_hourly_premium.csv"),
                          usecols=["ts_utc", "event", "sf_gw"])
        pnp["ts"] = pd.to_datetime(pnp["ts_utc"], utc=True).dt.tz_convert("America/Chicago")
        pnp["local_day"] = pnp["ts"].dt.normalize().dt.tz_localize(None)
        d26 = df[(df["year"] == 2026) & (df.index >= "2026-09-07")]

        ev_sum = pnp.groupby("local_day")["event"].sum()
        ev_days = set(ev_sum[ev_sum > 0].index)
        isev = d26.index.isin(ev_days)
        evm = d26[isev]["dcape_m"]
        nem = d26[~isev]["dcape_m"]
        if evm.notna().sum() >= 3:
            rec("B4", "9月 PV事件日 dcape_m 中位", float(evm.median()),
                f"n={evm.notna().sum()} vs 非事件 {nem.median():.0f} (n={nem.notna().sum()})")
        sf_day = pnp.groupby("local_day")["sf_gw"].max()
        dd9 = d26.dropna(subset=["dcape_m"]).copy()
        dd9["sf"] = sf_day.reindex(dd9.index).astype(float)
        r_, n = spear(dd9["dcape_m"].values, dd9["sf"].values)
        rec("B4", "ρ(dcape_m, 当日sf_gw max) 9月", r_, f"n={n}")

        # 节点 $1000+ 日 (15min 长表)
        pnl = pd.read_csv(os.path.join(D, "pv_node_panel_15min.csv"),
                          usecols=["ts", "node", "spp"])
        pnl["day"] = pd.to_datetime(pnl["ts"]).dt.tz_localize(
            "UTC").dt.tz_convert("America/Chicago").dt.normalize().dt.tz_localize(None)
        hi = pnl[pnl["spp"] >= 1000]
        hi_days = set(hi["day"].unique())
        ishi = d26.index.isin(hi_days)
        if ishi.sum() > 0:
            dh = d26[ishi]["dcape_m"]
            dn = d26[~ishi]["dcape_m"]
            rec("B4", "节点$1000+日 dcape_m 中位", float(dh.median()),
                f"n={ishi.sum()}; 其余日 {dn.median():.0f}")
        # 日内离散度 (p9010) ~ dcape
        dsp = pd.read_csv(os.path.join(D, "pv_node_dispersion.csv"))
        dsp["day"] = pd.to_datetime(dsp["ts_utc"]).dt.tz_localize(
            "UTC").dt.tz_convert("America/Chicago").dt.normalize().dt.tz_localize(None)
        if "is_daytime" in dsp.columns:
            dsp = dsp[dsp["is_daytime"].astype(bool)]
        p9010_day = dsp.groupby("day")["p9010"].mean()
        dd9["disp"] = p9010_day.reindex(dd9.index).astype(float)
        r_, n = spear(dd9["dcape_m"].values, dd9["disp"].values)
        rec("B4", "ρ(dcape_m, 节点离散度p9010日均) 9月", r_, f"n={n}")
    except Exception as ex:
        rec("B4", "pv_node 联动失败", str(ex)[:70], "")

    # [C] 站点异质性
    for code, nm in STATIONS.values():
        v = f"dcape_{code}"
        dd = pooled.dropna(subset=[v])
        if len(dd) < 40:
            continue
        y = np.log(dd["rtm_eve_max"].clip(lower=1)).values
        x = dd[v].values / 1000.0
        b, s = ols(y, np.column_stack([np.ones(len(dd)), x]))
        rec("C1", f"{code} {nm}: DCAPE系数 (ln /kJ)", b[1], f"SE {s[1]:.4f}; n={len(dd)}")
    # 空间相干: 站点 × hub
    for code, nm in STATIONS.values():
        v = f"dcape_{code}"
        dd = pooled.dropna(subset=[v])
        if len(dd) < 40:
            continue
        betas = []
        for hb in HUBS:
            y = np.log(dd[f"rtm_eve_max_{hb}"].clip(lower=1)).values
            x = dd[v].values / 1000.0
            b, s = ols(y, np.column_stack([np.ones(len(dd)), x]))
            betas.append(f"{hb}:{b[1]:+.3f}({s[1]:.3f})")
        rec("C2", f"{code} 分hub系数", " ".join(betas), f"n={len(dd)}")

    # [D] 概率产品: 阈值表
    d = pooled.dropna(subset=["dcape_m"])
    for thr_d in (800, 1200, 1600):
        hit = d[d["dcape_m"] >= thr_d]
        base = d["spike200"].mean()
        if len(hit) >= 5:
            rec("D", f"P(≥200 | dcape_m≥{thr_d})", float(hit["spike200"].mean()),
                f"n={len(hit)}; 无条件 {base:.3f}; PPV {hit['spike200'].mean() / max(base, 1e-9):.2f}x")
    # 命中率 (9月事件口径)
    pd.DataFrame(rows).to_csv(OUT_RES, index=False)
    print(f"\n保存 {OUT_RES}; 面板 {OUT_PANEL} ({len(df)} 日)")


if __name__ == "__main__":
    main()
