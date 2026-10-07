"""Storm Events (NCEI 对流天气) × ERCOT 电价 联动分析

研究问题:
  NCEI Storm Events 强对流事件记录 (龙卷/雷暴大风/冰雹/山洪) 与同期 ERCOT
  实时电价波动之间, 是否存在可论证的统计关系?

口径 (关键):
  - NCEI 时间为 **当地标准时 (LST)**, 由 CZ_TIMEZONE 给出 (德州 CST-6 全年, 不随夏令时调整)
    → UTC = 本地时间 - offset(负值) = 本地时间 + |offset|
  - ERCOT hourly_panel 索引为 UTC, 转 America/Chicago (含夏令时) 得到本地小时/日
  - 事件计数单位为 details 表行数 (= 县级事件记录数), 另给 EPISODE_ID 去重计数

分析 (6 组):
  A1 日级: 事件日 vs 非事件日 的价格水平/尖峰频率
  A2 条件阶梯: 日在事件强度分箱下 P(日最高 RTM ≥ $100/200/500)
  A3 小时级: 事件小时 vs 非事件小时, 含滞后结构 (t, t+1, t+2, t+3)
  A4 分事件类型 (龙卷/雷暴大风/冰雹/山洪)
  A5 分区: 事件空间落区(LZ) vs 该区 Hub 电价 (本地效应 vs 跨区效应)
  A6 混杂控制: OLS 日级 ln(rtm) ~ 事件数 + ln(需求) + 月FE (cluster by day)

输出:
  data/ercot/storm_events_texas_convective_2025_2026.csv  事件明细
  data/ercot/storm_events_price_daily.csv                 日级面板
  data/ercot/storm_events_price_results.csv               结果汇总
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import re
import gzip
import glob
import numpy as np
import pandas as pd

SE_DIR = r"c:\work\meteo\data\storm_events\details"
ERCOT_DIR = r"c:\work\meteo\data\ercot"
OUT_EVENTS = os.path.join(ERCOT_DIR, "storm_events_texas_convective_2025_2026.csv")
OUT_DAILY = os.path.join(ERCOT_DIR, "storm_events_price_daily.csv")
OUT_RES = os.path.join(ERCOT_DIR, "storm_events_price_results.csv")

CONVECTIVE = ["Tornado", "Thunderstorm Wind", "Hail", "Flash Flood", "Funnel Cloud"]
CONVECTIVE_EXT = CONVECTIVE + ["Marine Thunderstorm Wind"]
THRESHOLDS = [100.0, 200.0, 500.0]
_RESULTS = []


def rec(tag, desc, value, extra=""):
    _RESULTS.append({"tag": tag, "desc": desc, "value": value, "extra": extra})
    v = f"{value:.4f}" if isinstance(value, float) and np.isfinite(value) else str(value)
    print(f"  [{tag}] {desc}: {v}  {extra}")


def tz_offset(s):
    """'CST-6' → -6 ; 'MST-7' → -7"""
    if not isinstance(s, str):
        return None
    m = re.search(r"([+-]\d+)", s)
    return int(m.group(1)) if m else None


# ────────────────────────────────────────────────────────────
# 0. 载入 Storm Events (德州对流) 2025 + 2026
# ────────────────────────────────────────────────────────────
def load_storm_events():
    frames = []
    for yr in (2025, 2026):
        cands = glob.glob(os.path.join(SE_DIR, f"StormEvents_details-ftp_v1.0_d{yr}_c*.csv.gz"))
        if not cands:
            continue
        cols = ["BEGIN_YEARMONTH", "BEGIN_DAY", "BEGIN_TIME", "EPISODE_ID", "EVENT_ID",
                "STATE", "CZ_TIMEZONE", "EVENT_TYPE", "CZ_NAME", "CZ_FIPS",
                "BEGIN_LAT", "BEGIN_LON", "TOR_F_SCALE", "MAGNITUDE", "DAMAGE_PROPERTY"]
        with gzip.open(cands[0], "rt", encoding="utf-8", errors="replace") as f:
            d = pd.read_csv(f, usecols=lambda c: c in cols)
        d = d[d["STATE"] == "TEXAS"].copy()
        d = d[d["EVENT_TYPE"].isin(CONVECTIVE_EXT)].copy()
        frames.append(d)
    e = pd.concat(frames, ignore_index=True)

    e["year"] = (e["BEGIN_YEARMONTH"] // 100).astype(int)
    e["month"] = (e["BEGIN_YEARMONTH"] % 100).astype(int)
    e["day"] = e["BEGIN_DAY"].astype(int)
    e["hhmm"] = e["BEGIN_TIME"].astype(int)
    e["hour_lst"] = e["hhmm"] // 100
    e["minute"] = e["hhmm"] % 100
    e["off"] = e["CZ_TIMEZONE"].map(tz_offset)
    e = e[e["off"].notna()].copy()

    # 本地标准时 → UTC (本地 = UTC + off ; off 为负 → UTC = 本地 - off)
    base = pd.to_datetime(dict(year=e["year"], month=e["month"], day=e["day"]), errors="coerce")
    local = base + pd.to_timedelta(e["hour_lst"], unit="h") + pd.to_timedelta(e["minute"], unit="m")
    e["ts_lst"] = local
    e["ts_utc"] = (local - pd.to_timedelta(e["off"], unit="h")).dt.tz_localize("UTC")
    e = e[e["ts_utc"].notna()].copy()
    # 本地墙钟 (含夏令时) 用于小时剖面校验
    e["ts_chi"] = e["ts_utc"].dt.tz_convert("America/Chicago")
    e["local_day"] = e["ts_chi"].dt.normalize().dt.tz_localize(None)
    e["hour_chi"] = e["ts_chi"].dt.hour

    # ERCOT 负荷区 (按坐标, 沿用 gem_ercot_lz_analysis 口径)
    def assign_lz(lat, lon):
        if pd.isna(lat) or pd.isna(lon):
            return "UNKNOWN"
        if lon <= -100:
            return "LZ_WEST"
        if lat >= 32:
            return "LZ_NORTH"
        if lon >= -97.5 and lat <= 31:
            return "LZ_HOUSTON"
        if lat < 32:
            return "LZ_SOUTH"
        return "LZ_NORTH"
    e["lz"] = [assign_lz(a, b) for a, b in zip(e["BEGIN_LAT"], e["BEGIN_LON"])]
    e["is_marine"] = (e["EVENT_TYPE"] == "Marine Thunderstorm Wind").astype(int)
    return e


# ────────────────────────────────────────────────────────────
# 1. ERCOT hourly panel (UTC → Chicago)
# ────────────────────────────────────────────────────────────
def load_panel():
    frames = []
    for yr in (2025, 2026):
        h = pd.read_csv(os.path.join(ERCOT_DIR, f"ercot_hourly_panel_{yr}.csv"),
                        index_col=0, parse_dates=True)
        frames.append(h[["solar", "wind", "demand", "rtm", "dam"]])
    h = pd.concat(frames)
    h = h[~h.index.duplicated(keep="last")].sort_index()
    h.index = pd.to_datetime(h.index, utc=True)
    h = h.tz_convert("America/Chicago")
    h["local_day"] = h.index.normalize().tz_localize(None)
    h["hour_chi"] = h.index.hour
    return h


def ols_cluster(y, X, groups):
    XtXi = np.linalg.pinv(X.T @ X)
    b = XtXi @ (X.T @ y)
    e = y - X @ b
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(groups):
        m = groups == g
        s = X[m].T @ e[m]
        meat += np.outer(s, s)
    n, k = X.shape
    G = len(np.unique(groups))
    adj = (G / (G - 1)) * ((n - 1) / (n - k))
    V = XtXi @ meat @ XtXi * adj
    return b, np.sqrt(np.diag(V))


def main():
    print("=" * 68)
    print("Storm Events × ERCOT 电价联动分析")
    print("=" * 68)

    ev = load_storm_events()
    ev.to_csv(OUT_EVENTS, index=False)
    print(f"\n[0] 德州对流事件 (2025-2026): {len(ev)} 条县级记录, "
          f"{ev['EPISODE_ID'].nunique()} 个 episode")
    print(f"    时间跨度: {ev['ts_utc'].min()} → {ev['ts_utc'].max()}")
    print(f"    事件类型:\n{ev['EVENT_TYPE'].value_counts().to_string()}")
    print(f"    落区: {ev['lz'].value_counts().to_dict()}")
    rec("SAMPLE", "德州对流县级记录数", float(len(ev)),
        f"episodes={ev['EPISODE_ID'].nunique()}, 2025-2026")
    rec("SAMPLE", "落区分布(记录数)", np.nan, str(ev["lz"].value_counts().to_dict()))

    panel = load_panel()
    print(f"\n[1] hourly_panel: {len(panel)} 小时, "
          f"{panel.index.min()} → {panel.index.max()} (Chicago)")

    # 小时事件计数 (UTC 对齐 panel)
    ev_utc_hour = ev.copy()
    ev_utc_hour["ts_h"] = ev_utc_hour["ts_utc"].dt.floor("h").dt.tz_convert("America/Chicago")
    hc = {"n_ev": ev_utc_hour.groupby("ts_h").size()}
    for lz in ["LZ_WEST", "LZ_NORTH", "LZ_SOUTH", "LZ_HOUSTON"]:
        hc[f"n_{lz}"] = ev_utc_hour[ev_utc_hour["lz"] == lz].groupby("ts_h").size()
    hourly_cnt = pd.DataFrame(hc).fillna(0)
    hourly_cnt.index.name = None
    p = panel.join(hourly_cnt, how="left").fillna({"n_ev": 0})
    for c in [c for c in p.columns if c.startswith("n_LZ")]:
        p[c] = p[c].fillna(0)

    p["is_event"] = (p["n_ev"] > 0).astype(int)
    p["month"] = p.index.month
    p["summer"] = p["month"].isin([6, 7, 8, 9]).astype(int)

    # ── 日级面板 ──
    daily = p.groupby("local_day").agg(
        n_ev=("n_ev", "sum"),
        rtm_mean=("rtm", "mean"),
        rtm_max=("rtm", "max"),
        dam_mean=("dam", "mean"),
        demand_mean=("demand", "mean"),
        demand_max=("demand", "max"),
        solar_mean=("solar", "mean"),
        wind_mean=("wind", "mean"),
        hours=("rtm", "size"),
    )
    for c in ["LZ_WEST", "LZ_NORTH", "LZ_SOUTH", "LZ_HOUSTON"]:
        daily[f"n_{c}"] = p.groupby("local_day")[f"n_{c}"].sum()
    daily["month"] = daily.index.month
    daily["summer"] = daily["month"].isin([6, 7, 8, 9]).astype(int)
    daily["is_event"] = (daily["n_ev"] > 0).astype(int)
    for t in THRESHOLDS:
        daily[f"spike_{int(t)}"] = (daily["rtm_max"] >= t).astype(int)
    daily.to_csv(OUT_DAILY)
    print(f"\n[2] 日级面板: {len(daily)} 天, 事件日 {int(daily['is_event'].sum())} "
          f"({daily['is_event'].mean()*100:.1f}%)")

    # ══════════════ A1: 日级 事件 vs 非事件 ══════════════
    print("\n" + "─" * 68)
    print("A1  日级: 事件日 vs 非事件日")
    print("─" * 68)
    for scope, sub in [("全年", daily), ("夏季(6-9月)", daily[daily["summer"] == 1])]:
        g1 = sub[sub["is_event"] == 1]
        g0 = sub[sub["is_event"] == 0]
        print(f"  [{scope}] 事件日 n={len(g1)} / 非事件日 n={len(g0)}")
        for col in ["rtm_mean", "rtm_max", "demand_mean"]:
            m1, m0 = g1[col].mean(), g0[col].mean()
            print(f"    {col:12s}: 事件日 {m1:8.2f} | 非事件日 {m0:8.2f} | "
                  f"差 {m1-m0:+8.2f} ({'+' if m1>=m0 else ''}{100*(m1-m0)/m0:.1f}%)")
        for t in THRESHOLDS:
            p1 = g1[f"spike_{int(t)}"].mean() * 100
            p0 = g0[f"spike_{int(t)}"].mean() * 100
            print(f"    P(日最高≥${int(t)}) : 事件日 {p1:5.1f}% | 非事件日 {p0:5.1f}%")
        rec("A1", f"{scope} 事件日 rtm_mean 差", float(g1['rtm_mean'].mean()-g0['rtm_mean'].mean()),
            f"事件日 {g1['rtm_mean'].mean():.2f} vs 非事件日 {g0['rtm_mean'].mean():.2f}, n={len(g1)}/{len(g0)}")
        rec("A1", f"{scope} 事件日 P(rtm_max≥200)", float(g1['spike_200'].mean()-g0['spike_200'].mean()),
            f"{g1['spike_200'].mean()*100:.1f}% vs {g0['spike_200'].mean()*100:.1f}%")

    # ══════════════ A2: 条件阶梯 ══════════════
    print("\n" + "─" * 68)
    print("A2  条件阶梯: 日事件强度分箱 → 价格")
    print("─" * 68)
    ev_days = daily[daily["n_ev"] > 0].copy()
    bins = [0, 5, 15, 40, 10**9]
    labels = ["1-5", "6-15", "16-40", ">40"]
    ev_days["bin"] = pd.cut(ev_days["n_ev"], bins=bins, labels=labels, right=True)
    print(f"  (仅事件日 n={len(ev_days)}, 分箱=当日县级对流记录数)")
    print(f"  {'箱':>8s} {'n':>5s} {'rtm_mean':>9s} {'rtm_max中位':>11s} "
          f"{'P≥100':>7s} {'P≥200':>7s} {'P≥500':>7s}")
    for lb in labels:
        s = ev_days[ev_days["bin"] == lb]
        if len(s) == 0:
            continue
        print(f"  {lb:>8s} {len(s):5d} {s['rtm_mean'].mean():9.2f} "
              f"{s['rtm_max'].median():11.2f} {s['spike_100'].mean()*100:6.1f}% "
              f"{s['spike_200'].mean()*100:6.1f}% {s['spike_500'].mean()*100:6.1f}%")
        rec("A2", f"日事件 {lb} 箱 P(rtm_max≥200)", float(s["spike_200"].mean()*100),
            f"n={len(s)}, mean_rtm={s['rtm_mean'].mean():.2f}")
    s0 = daily[daily["n_ev"] == 0]
    print(f"  {'0事件':>8s} {len(s0):5d} {s0['rtm_mean'].mean():9.2f} "
          f"{s0['rtm_max'].median():11.2f} {s0['spike_100'].mean()*100:6.1f}% "
          f"{s0['spike_200'].mean()*100:6.1f}% {s0['spike_500'].mean()*100:6.1f}%")
    rec("A2", "0事件日 P(rtm_max≥200)", float(s0["spike_200"].mean()*100), f"n={len(s0)}")

    # 夏季限定阶梯
    se_days = ev_days[ev_days["summer"] == 1]
    print("  -- 夏季(6-9)限定 --")
    for lb in labels:
        s = se_days[se_days["bin"] == lb]
        if len(s) == 0:
            continue
        print(f"  {lb:>8s} {len(s):5d} {s['rtm_mean'].mean():9.2f} "
              f"{s['rtm_max'].median():11.2f} {s['spike_100'].mean()*100:6.1f}% "
              f"{s['spike_200'].mean()*100:6.1f}% {s['spike_500'].mean()*100:6.1f}%")
    s0s = daily[(daily["n_ev"] == 0) & (daily["summer"] == 1)]
    print(f"  {'0事件':>8s} {len(s0s):5d} {s0s['rtm_mean'].mean():9.2f} "
          f"{s0s['rtm_max'].median():11.2f} {s0s['spike_100'].mean()*100:6.1f}% "
          f"{s0s['spike_200'].mean()*100:6.1f}% {s0s['spike_500'].mean()*100:6.1f}%")

    # ══════════════ A3: 小时级 + 滞后 ══════════════
    print("\n" + "─" * 68)
    print("A3  小时级: 事件小时 vs 非事件小时 (+滞后)")
    print("─" * 68)
    ph = p.copy()
    for lag in (1, 2, 3):
        ph[f"rtm_t{lag}"] = ph["rtm"].shift(-lag)
    for scope, m in [("全年", np.ones(len(ph), bool)),
                     ("夏季(6-9)", ph["month"].isin([6, 7, 8, 9]).values)]:
        sub = ph[m]
        ge = sub[sub["is_event"] == 1]
        gn = sub[sub["is_event"] == 0]
        print(f"  [{scope}] 事件小时 n={len(ge)} / 非事件小时 n={len(gn)}")
        for col, nm in [("rtm", "t"), ("rtm_t1", "t+1"), ("rtm_t2", "t+2"), ("rtm_t3", "t+3")]:
            a, b = ge[col].mean(), gn[col].mean()
            print(f"    RTM({nm}): 事件 {a:8.2f} | 非事件 {b:8.2f} | 差 {a-b:+8.2f}")
        print(f"    P(RTM≥200): 事件 {(ge['rtm']>=200).mean()*100:.2f}% | "
              f"非事件 {(gn['rtm']>=200).mean()*100:.2f}%")
        rec("A3", f"{scope} 事件小时 RTM 差 (t)", float(ge["rtm"].mean()-gn["rtm"].mean()),
            f"事件 {ge['rtm'].mean():.2f} vs 非事件 {gn['rtm'].mean():.2f}, n={len(ge)}/{len(gn)}")
        rec("A3", f"{scope} P(RTM≥200) 事件小时", float((ge['rtm']>=200).mean()*100),
            f"非事件 {(gn['rtm']>=200).mean()*100:.2f}%")

    # 事件小时的分时剖面 (夏季)
    print("  -- 事件小时按本地小时的价格剖面 (夏季) --")
    ss = ph[(ph["month"].isin([6, 7, 8, 9]))]
    print(f"  {'hour':>5s} {'事件n':>6s} {'事件RTM':>9s} {'非事件RTM':>10s} {'差':>9s}")
    for h in range(0, 24):
        a = ss[(ss["hour_chi"] == h) & (ss["is_event"] == 1)]["rtm"]
        b = ss[(ss["hour_chi"] == h) & (ss["is_event"] == 0)]["rtm"]
        if len(a) < 20:
            continue
        print(f"  {h:5d} {len(a):6d} {a.mean():9.2f} {b.mean():10.2f} {a.mean()-b.mean():+9.2f}")
        rec("A3h", f"夏季 hour {h:02d} 事件-非事件 RTM差", float(a.mean()-b.mean()),
            f"事件n={len(a)}, 事件 {a.mean():.2f} vs 非事件 {b.mean():.2f}")

    # ══════════════ A4: 分事件类型 ══════════════
    print("\n" + "─" * 68)
    print("A4  分事件类型 (小时级)")
    print("─" * 68)
    for et in CONVECTIVE:
        sub = ev_utc_hour[ev_utc_hour["EVENT_TYPE"] == et]
        hrs = set(sub["ts_h"])
        mask_e = p.index.isin(hrs)
        ge = p[mask_e]
        gn = p[~mask_e]
        if len(ge) < 20:
            continue
        print(f"  {et:18s} 事件小时 n={len(ge):5d} | RTM 事件 {ge['rtm'].mean():7.2f} "
              f"vs 其他 {gn['rtm'].mean():7.2f} (差 {ge['rtm'].mean()-gn['rtm'].mean():+7.2f}) | "
              f"P(≥200) {((ge['rtm']>=200).mean()*100):5.2f}% vs {((gn['rtm']>=200).mean()*100):.2f}%")
        rec("A4", f"{et} 事件小时 RTM差", float(ge["rtm"].mean()-gn["rtm"].mean()),
            f"P(≥200) {((ge['rtm']>=200).mean()*100):.2f}% vs {((gn['rtm']>=200).mean()*100):.2f}%, n={len(ge)}")

    # ══════════════ A5: 分区效应 ══════════════
    print("\n" + "─" * 68)
    print("A5  分区: 事件落区(LZ) vs 该区 Hub 电价 (15min→小时)")
    print("─" * 68)
    hub = {}
    for lz in ["LZ_WEST", "LZ_NORTH", "LZ_SOUTH", "LZ_HOUSTON"]:
        f = glob.glob(os.path.join(ERCOT_DIR, f"ercot_rtm_HB_{lz.replace('LZ_','')}_*.csv"))
        if not f:
            continue
        d = pd.read_csv(f[0])
        d["ts"] = pd.to_datetime(d["interval_start_utc"], utc=True)
        d = d[~d["ts"].duplicated(keep="last")].set_index("ts").sort_index()
        s = d["spp"].resample("h").mean()
        s.index = s.index.tz_convert("America/Chicago")
        hub[lz] = s
    for lz, s in hub.items():
        own = p[f"n_{lz}"] > 0
        other = (p["n_ev"] - p[f"n_{lz}"]) > 0
        base = (~own) & (~other)
        r = s.reindex(p.index)
        a = r[own.values].mean()
        b = r[other.values].mean()
        c = r[base.values].mean()
        print(f"  {lz:11s} 本区事件小时 {a:8.2f} (n={int(own.sum()):4d}) | "
              f"仅他区事件 {b:8.2f} (n={int(other.sum()):4d}) | 无事件 {c:8.2f} (n={int(base.sum()):4d})")
        rec("A5", f"{lz} 本区事件 vs 无事件 Hub价差", float(a - c),
            f"本区 {a:.2f} / 他区 {b:.2f} / 无 {c:.2f}")
        rec("A5", f"{lz} 全系统 HB 本区事件 vs 无事件 (对照 system rtm)", float(
            p["rtm"][own.values].mean() - p["rtm"][base.values].mean()),
            f"本区事件 {p['rtm'][own.values].mean():.2f} / 无 {p['rtm'][base.values].mean():.2f}")

    # ══════════════ A6: 混杂控制回归 ══════════════
    print("\n" + "─" * 68)
    print("A6  混杂控制: 日级回归")
    print("─" * 68)
    dd = daily.dropna(subset=["rtm_mean", "demand_mean"]).copy()
    y = np.log(dd["rtm_mean"].clip(lower=1.0).values)
    feats = [np.ones(len(dd)),
             dd["n_ev"].values / 10.0,
             np.log(dd["demand_mean"].values)]
    X = np.column_stack(feats)
    groups = dd["month"].values * 100 + (dd.index.day.values)
    b, se = ols_cluster(y, X, groups)
    print(f"  ln(rtm_mean) ~ n_ev/10 + ln(demand)   n={len(dd)}")
    for nm, bi, si in zip(["const", "n_ev/10", "ln(demand)"], b, se):
        print(f"    {nm:12s} {bi:+8.4f}  (SE {si:.4f}, t={bi/si:+.2f})")
    rec("A6", "日级 ln(rtm)~事件数/10 (控需求)", float(b[1]), f"SE {se[1]:.4f}, n={len(dd)}")

    # 加月FE
    md = pd.get_dummies(dd["month"].astype(int).astype(str), drop_first=True).values.astype(float)
    X2 = np.column_stack([np.ones(len(dd)), dd["n_ev"].values / 10.0,
                          np.log(dd["demand_mean"].values), md])
    b2, se2 = ols_cluster(y, X2, groups)
    print(f"  + 月固定效应   n={len(dd)}")
    print(f"    n_ev/10 {b2[1]:+8.4f} (SE {se2[1]:.4f}, t={b2[1]/se2[1]:+.2f})"
          f" | ln(demand) {b2[2]:+8.4f} (SE {se2[2]:.4f})")
    rec("A6", "日级 ln(rtm)~事件数/10 (+月FE)", float(b2[1]), f"SE {se2[1]:.4f}, n={len(dd)}")

    # 尖峰概率 logit-ish (线性概率)
    yl = dd["spike_200"].values.astype(float)
    b3, se3 = ols_cluster(yl, X, groups)
    print(f"  LP: P(rtm_max≥200) ~ n_ev/10 + ln(demand)   n={len(dd)}")
    for nm, bi, si in zip(["const", "n_ev/10", "ln(demand)"], b3, se3):
        print(f"    {nm:12s} {bi:+8.4f}  (SE {si:.4f}, t={bi/si:+.2f})")
    rec("A6", "日级 P(rtm_max≥200)~事件数/10", float(b3[1]), f"SE {se3[1]:.4f}, n={len(dd)}")
    b4, se4 = ols_cluster(yl, X2, groups)
    print(f"  LP + 月FE: n_ev/10 {b4[1]:+.4f} (SE {se4[1]:.4f}, t={b4[1]/se4[1]:+.2f})")
    rec("A6", "日级 P(rtm_max≥200)~事件数/10 (+月FE)", float(b4[1]),
        f"SE {se4[1]:.4f}, n={len(dd)}")

    # ══════════════ A7: 小时级控制回归 (小时FE+月FE+需求, 含前后期) ══════════════
    print("\n" + "─" * 68)
    print("A7  小时级控制回归: ln(rtm) ~ 事件(t-1,t,t+1) + ln(需求) + 小时FE + 月FE")
    print("─" * 68)
    q = p.dropna(subset=["rtm", "demand"]).copy()
    q["lag1"] = q["is_event"].shift(1)
    q["lead1"] = q["is_event"].shift(-1)
    q["n_ev_l"] = q["n_ev"].shift(1)
    q = q.dropna(subset=["lag1", "lead1", "n_ev_l"])
    yh = np.log(q["rtm"].clip(lower=1.0).values)
    hd = pd.get_dummies(q["hour_chi"].astype(int).astype(str), drop_first=True).values.astype(float)
    md2 = pd.get_dummies(q["month"].astype(int).astype(str), drop_first=True).values.astype(float)
    Xh = np.column_stack([
        np.ones(len(q)),
        q["is_event"].values,
        q["lag1"].values,
        q["lead1"].values,
        np.log(q["demand"].values),
        hd, md2,
    ])
    names = ["const", "event(t)", "event(t-1)", "event(t+1)", "ln(demand)"] + \
            [f"h{h}" for h in range(1, 24)] + [f"m{m}" for m in range(2, 13)]
    gh = q["local_day"].values
    bh, seh = ols_cluster(yh, Xh, gh)
    print(f"  n={len(q)}, cluster={len(np.unique(gh))} 天")
    for nm, bi, si in list(zip(names, bh, seh))[:5]:
        print(f"    {nm:12s} {bi:+8.4f}  (SE {si:.4f}, t={bi/si:+.2f})")
    for i, nm in enumerate(["event(t)", "event(t-1)", "event(t+1)"]):
        rec("A7", f"小时 ln(rtm)~{nm}", float(bh[1 + i]), f"SE {seh[1+i]:.4f}, n={len(q)}")

    # 夏季限定
    qs = q[q["month"].isin([6, 7, 8, 9])].copy()
    if len(qs) > 200:
        ys = np.log(qs["rtm"].clip(lower=1.0).values)
        hds = pd.get_dummies(qs["hour_chi"].astype(int).astype(str), drop_first=True).values.astype(float)
        Xs = np.column_stack([np.ones(len(qs)), qs["is_event"].values, qs["lag1"].values,
                              qs["lead1"].values, np.log(qs["demand"].values), hds])
        gs = qs["local_day"].values
        bs, ss_ = ols_cluster(ys, Xs, gs)
        print(f"  [夏季] n={len(qs)}")
        for nm, bi, si in zip(["const", "event(t)", "event(t-1)", "event(t+1)", "ln(demand)"], bs, ss_):
            print(f"    {nm:12s} {bi:+8.4f}  (SE {si:.4f}, t={bi/si:+.2f})")
        for i, nm in enumerate(["event(t)", "event(t-1)", "event(t+1)"]):
            rec("A7s", f"夏季 小时 ln(rtm)~{nm}", float(bs[1 + i]), f"SE {ss_[1+i]:.4f}, n={len(qs)}")

    # 尾概率 LPM (小时, 控制小时FE)
    yt = (q["rtm"] >= 200).astype(float).values
    Xt = np.column_stack([np.ones(len(q)), q["is_event"].values, np.log(q["demand"].values), hd, md2])
    bt, set_ = ols_cluster(yt, Xt, gh)
    print(f"  LPM P(rtm≥200) ~ event(t): {bt[1]:+.4f} (SE {set_[1]:.4f}, t={bt[1]/set_[1]:+.2f})")
    rec("A7", "小时 P(rtm≥200)~event(t)", float(bt[1]), f"SE {set_[1]:.4f}, n={len(q)}")

    pd.DataFrame(_RESULTS).to_csv(OUT_RES, index=False)
    print(f"\n结果 → {OUT_RES}")
    print(f"事件明细 → {OUT_EVENTS}")
    print(f"日级面板 → {OUT_DAILY}")


if __name__ == "__main__":
    main()
