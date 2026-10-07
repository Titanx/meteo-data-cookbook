"""生成 Storm Events × ERCOT 电价 报告的图表数据 (charts_data.js)"""
import sys, os, glob, gzip, re, json
sys.stdout.reconfigure(line_buffering=True)
import numpy as np
import pandas as pd

ERCOT_DIR = r"c:\work\meteo\data\ercot"
OUT_DIR = r"c:\work\meteo\output\storm_events_price"
os.makedirs(os.path.join(OUT_DIR, "assets"), exist_ok=True)

ev = pd.read_csv(os.path.join(ERCOT_DIR, "storm_events_texas_convective_2025_2026.csv"),
                 parse_dates=["ts_utc", "ts_chi", "local_day"])
daily = pd.read_csv(os.path.join(ERCOT_DIR, "storm_events_price_daily.csv"),
                    index_col=0, parse_dates=True)

# ── 重建小时面板 ──
frames = []
for yr in (2025, 2026):
    h = pd.read_csv(os.path.join(ERCOT_DIR, f"ercot_hourly_panel_{yr}.csv"),
                    index_col=0, parse_dates=True)
    frames.append(h[["solar", "wind", "demand", "rtm", "dam"]])
h = pd.concat(frames)
h = h[~h.index.duplicated(keep="last")].sort_index()
h.index = pd.to_datetime(h.index, utc=True).tz_convert("America/Chicago")
p = h.copy()
p["month"] = p.index.month
p["hour_chi"] = p.index.hour
p["local_day"] = p.index.normalize()

ev["ts_h"] = pd.to_datetime(ev["ts_utc"], utc=True).dt.floor("h").dt.tz_convert("America/Chicago")
cnt = ev.groupby("ts_h").size()
p["n_ev"] = p.index.map(cnt).fillna(0)
for lz in ["LZ_WEST", "LZ_NORTH", "LZ_SOUTH", "LZ_HOUSTON"]:
    c = ev[ev["lz"] == lz].groupby("ts_h").size()
    p[f"n_{lz}"] = p.index.map(c).fillna(0)
p["is_event"] = (p["n_ev"] > 0).astype(int)

data = {}

# 1. 月度时间线
g = p.groupby(p.index.to_period("M"))
mon = pd.DataFrame({
    "events": g["n_ev"].sum(),
    "rtm": g["rtm"].mean(),
    "demand": g["demand"].mean(),
})
mon.index = mon.index.astype(str)
mon = mon[mon.index >= "2025-01"]
data["monthly"] = {
    "labels": list(mon.index),
    "events": [round(float(x), 0) for x in mon["events"]],
    "rtm": [round(float(x), 2) for x in mon["rtm"]],
}

# 2. 条件阶梯 (日级, 全年 + 夏季)
def ladder(sub):
    out = {"labels": ["0", "1-5", "6-15", "16-40", ">40"], "p100": [], "p200": [], "p500": [], "rtm": []}
    bins = [(-1, 0), (1, 5), (6, 15), (16, 40), (41, 10**9)]
    for lo, hi in bins:
        s = sub[(sub["n_ev"] >= lo) & (sub["n_ev"] <= hi)]
        if len(s) == 0:
            for k in ["p100", "p200", "p500", "rtm"]:
                out[k].append(None)
            continue
        out["p100"].append(round(float((s["rtm_max"] >= 100).mean() * 100), 2))
        out["p200"].append(round(float((s["rtm_max"] >= 200).mean() * 100), 2))
        out["p500"].append(round(float((s["rtm_max"] >= 500).mean() * 100), 2))
        out["rtm"].append(round(float(s["rtm_mean"].mean()), 2))
    return out
data["ladder_all"] = ladder(daily)
data["ladder_summer"] = ladder(daily[daily["summer"] == 1])

# 3. 小时剖面 (夏季, 事件 vs 非事件)
hr_all = []
for hh in range(24):
    a = p[(p["hour_chi"] == hh) & (p["is_event"] == 1)]["rtm"]
    b = p[(p["hour_chi"] == hh) & (p["is_event"] == 0)]["rtm"]
    hr_all.append({"h": hh, "ev": round(float(a.mean()), 2) if len(a) >= 15 else None,
                   "ne": round(float(b.mean()), 2), "n": int(len(a))})
ps = p[p["month"].isin([6, 7, 8, 9])]
hr_sum = []
for hh in range(24):
    a = ps[(ps["hour_chi"] == hh) & (ps["is_event"] == 1)]["rtm"]
    b = ps[(ps["hour_chi"] == hh) & (ps["is_event"] == 0)]["rtm"]
    hr_sum.append({"h": hh, "ev": round(float(a.mean()), 2) if len(a) >= 15 else None,
                   "ne": round(float(b.mean()), 2), "n": int(len(a))})
data["hourly_all"] = hr_all
data["hourly_summer"] = hr_sum

# 4. 滞后结构 (原始溢价 + 受控系数)
ph = p.copy()
for lag in (-1, 1, 2, 3):
    ph[f"rtm_l{lag}"] = ph["rtm"].shift(-lag)
labels = ["t-1", "t", "t+1", "t+2", "t+3"]
raw = []
for lab in labels:
    col = "rtm" if lab == "t" else f"rtm_l{int(lab[1:])}" if lab.startswith("t+") else f"rtm_l-1"
    ge = ph[ph["is_event"] == 1][col]
    gn = ph[ph["is_event"] == 0][col]
    raw.append(round(float(ge.mean() - gn.mean()), 2))
data["lag"] = {"labels": labels, "raw": raw}

# 5. 分事件类型
types = ["Tornado", "Thunderstorm Wind", "Hail", "Flash Flood"]
bt = []
for et in types:
    hrs = set(ev[ev["EVENT_TYPE"] == et]["ts_h"])
    m = p.index.isin(hrs)
    ge, gn = p[m], p[~m]
    bt.append({"type": et, "prem": round(float(ge["rtm"].mean() - gn["rtm"].mean()), 2),
               "p200": round(float((ge["rtm"] >= 200).mean() * 100), 2),
               "p200_other": round(float((gn["rtm"] >= 200).mean() * 100), 2),
               "n": int(m.sum())})
data["bytype"] = bt

# 6. 分区
sp = []
for lz in ["LZ_WEST", "LZ_NORTH", "LZ_SOUTH", "LZ_HOUSTON"]:
    f = glob.glob(os.path.join(ERCOT_DIR, f"ercot_rtm_HB_{lz.replace('LZ_','')}_*.csv"))[0]
    d = pd.read_csv(f)
    d["ts"] = pd.to_datetime(d["interval_start_utc"], utc=True)
    d = d[~d["ts"].duplicated(keep="last")].set_index("ts").sort_index()
    s = d["spp"].resample("h").mean()
    s.index = s.index.tz_convert("America/Chicago")
    r = s.reindex(p.index).values
    own = (p[f"n_{lz}"] > 0).values
    other = ((p["n_ev"] - p[f"n_{lz}"]) > 0).values
    base = (~own) & (~other)
    sp.append({"lz": lz, "own": round(float(np.nanmean(r[own])), 2),
               "other": round(float(np.nanmean(r[other])), 2),
               "none": round(float(np.nanmean(r[base])), 2),
               "n_own": int(own.sum())})
data["spatial"] = sp

# 7. 受控系数 (从结果 CSV 取)
res = pd.read_csv(os.path.join(ERCOT_DIR, "storm_events_price_results.csv"))

def val(tag, prefix):
    r = res[(res["tag"] == tag) & (res["desc"].str.contains(prefix, regex=False))]
    if len(r) == 0:
        return None, None
    v = float(r.iloc[0]["value"])
    se = np.nan
    m = re.search(r"SE ([\d.]+)", str(r.iloc[0]["extra"]))
    if m:
        se = float(m.group(1))
    return v, se

coef = {"labels": [], "beta": [], "lo": [], "hi": []}
for tag, key, lab in [
    ("A6", "ln(rtm)~事件数/10 (+月FE)", "日级 ln(rtm)~事件数/10"),
    ("A7", "ln(rtm)~event(t)", "小时 event(t)"),
    ("A7", "ln(rtm)~event(t-1)", "小时 event(t-1)"),
    ("A7", "ln(rtm)~event(t+1)", "小时 event(t+1)"),
    ("A6", "P(rtm_max≥200)~事件数/10 (+月FE)", "日级 ΔP(≥200)"),
    ("A7", "P(rtm≥200)~event(t)", "小时 ΔP(≥200)"),
]:
    v, se = val(tag, key)
    if v is None:
        continue
    # 统一到"百分比点"或"%" 尺度: 对 ln 系数转 %
    scale = 100 if "ln(" in key else 100
    coef["labels"].append(lab)
    coef["beta"].append(round(v * scale, 3))
    coef["lo"].append(round((v - 1.96 * se) * scale, 3) if se == se else 0)
    coef["hi"].append(round((v + 1.96 * se) * scale, 3) if se == se else 0)
data["coef"] = coef

# 供 A1 表用
g1 = daily[daily["n_ev"] > 0]; g0 = daily[daily["n_ev"] == 0]
s1 = daily[(daily["n_ev"] > 0) & (daily["summer"] == 1)]; s0 = daily[(daily["n_ev"] == 0) & (daily["summer"] == 1)]
data["kpi"] = {
    "n_events": int(len(ev)),
    "n_episodes": int(ev["EPISODE_ID"].nunique()),
    "n_days": int(len(daily)),
    "n_event_days": int(daily["is_event"].sum()),
    "span": [str(ev["ts_chi"].min())[:16], str(ev["ts_chi"].max())[:16]],
    "all": {"ev_rtm": round(float(g1["rtm_mean"].mean()), 2), "ne_rtm": round(float(g0["rtm_mean"].mean()), 2),
            "ev_p200": round(float(g1["spike_200"].mean() * 100), 2), "ne_p200": round(float(g0["spike_200"].mean() * 100), 2)},
    "summer": {"ev_rtm": round(float(s1["rtm_mean"].mean()), 2), "ne_rtm": round(float(s0["rtm_mean"].mean()), 2),
               "ev_p200": round(float(s1["spike_200"].mean() * 100), 2), "ne_p200": round(float(s0["spike_200"].mean() * 100), 2)},
    "type_counts": {k: int(v) for k, v in ev["EVENT_TYPE"].value_counts().items()},
    "lz_counts": {k: int(v) for k, v in ev["lz"].value_counts().items()},
}

with open(os.path.join(OUT_DIR, "assets", "charts_data.js"), "w", encoding="utf-8") as f:
    f.write("window.SE_DATA = ")
    json.dump(data, f, ensure_ascii=False, indent=1)
    f.write(";\n")
print("charts_data.js 已生成")
print(json.dumps(data["kpi"], ensure_ascii=False, indent=1))
print("coef:", json.dumps(data["coef"], ensure_ascii=False))
