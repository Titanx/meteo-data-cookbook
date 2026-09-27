"""2022-07 ERCOT 光伏骤降事件识别 + 归因 (实际 EIA vs 模型反事实)
事件定义: 小时出力较前一小时下降 >=1500 MW, 且事件前 >=3000 MW,
          时段 15-23 UTC (10:00-18:00 CDT 下午, 避开自然傍晚下坡)
归因: 模型同期降幅 (NSRDB 真实辐照) 可解释 >=60% -> 云/辐照主导;
      残差 >=600 MW -> 非辐照因素 (弃电/机组降额) 疑似
输出: stdout 事件表 + data/nsrdb/pv_drop_events_2022-07.csv
"""
import numpy as np
import pandas as pd

MODEL = r"c:\work\meteo\data\nsrdb\ercot_pv_power_2022-07.csv"
OUT = r"c:\work\meteo\data\nsrdb\pv_drop_events_2022-07.csv"
DROP_MW = 1500.0
PRE_MIN_MW = 3000.0
EXPLAIN_RATIO = 0.6
RESID_MW = 600.0


def main():
    j = pd.read_csv(MODEL, index_col=0, parse_dates=True)
    if j.index.tz is None:
        j.index = j.index.tz_localize("UTC")
    j = j[["pvlib_mw", "eia_mw"]].dropna()

    d_eia = j["eia_mw"].diff()
    d_mod = j["pvlib_mw"].diff()

    raw = (d_eia <= -DROP_MW) & (j["eia_mw"].shift(1) >= PRE_MIN_MW) \
        & (j.index.hour >= 15) & (j.index.hour <= 23)

    # 合并连续事件小时为单个事件
    events = []
    idx = j.index
    flags = np.where(raw.values)[0]
    groups = []
    for k in flags:
        if groups and k == groups[-1][-1] + 1:
            groups[-1].append(k)
        else:
            groups.append([k])

    print(f"{'事件起点(UTC)':<18s} {'持续h':>5s} {'EIA降幅':>9s} {'模型降幅':>9s} "
          f"{'解释比':>7s} {'残差':>7s} {'归因':<14s}")
    rows = []
    for g in groups:
        i0, i1 = g[0], g[-1]
        pre = i0 - 1
        # 峰值取事件前 2h 内最大值, 谷值取事件内最小值
        pre_val = max(j["eia_mw"].iloc[pre - 1:i0].max(), j["eia_mw"].iloc[pre])
        trough_i = j["eia_mw"].iloc[i0:i1 + 1].idxmin()
        trough = j["eia_mw"].loc[trough_i]
        d_eia_ev = trough - pre_val
        m_pre = j["pvlib_mw"].loc[:j.index[pre]].iloc[-1]
        # 模型在相同窗 (事件前峰值时刻 -> 实际谷值时刻) 的降幅
        pre_t = j["eia_mw"].loc[:j.index[pre]].idxmax()
        m_trough = j["pvlib_mw"].loc[trough_i]
        m_pre_t = j["pvlib_mw"].loc[pre_t]
        d_mod_ev = m_trough - m_pre_t
        ratio = d_mod_ev / d_eia_ev if d_eia_ev < 0 else np.nan
        resid = d_eia_ev - d_mod_ev
        if ratio >= EXPLAIN_RATIO:
            cause = "云/辐照主导"
        elif resid >= RESID_MW:
            cause = "非辐照残差(疑弃电/降额)"
        else:
            cause = "混合"
        print(f"{j.index[i0].strftime('%m-%d %H:%M'):<18s} {len(g):>5d} "
              f"{d_eia_ev:>9.0f} {d_mod_ev:>9.0f} {ratio:>7.0%} {resid:>7.0f} {cause}")
        rows.append({
            "start_utc": j.index[i0], "hours": len(g),
            "pre_mw": pre_val, "trough_mw": trough, "trough_time_utc": trough_i,
            "d_eia_mw": d_eia_ev, "d_model_mw": d_mod_ev,
            "explain_ratio": ratio, "resid_mw": resid, "cause": cause,
        })

    ev = pd.DataFrame(rows)
    ev.to_csv(OUT, index=False)
    print(f"\n共 {len(ev)} 个事件, 已保存 {OUT}")
    if len(ev):
        print(f"总 EIA 降深 {ev['d_eia_mw'].sum():.0f} MW, "
              f"其中模型解释 {ev['d_model_mw'].sum():.0f} MW "
              f"({ev['d_model_mw'].sum()/ev['d_eia_mw'].sum():.0%}), "
              f"残差 {ev['resid_mw'].sum():.0f} MW")
        print("\n事件日分布:")
        by = ev.copy()
        by["date"] = pd.to_datetime(ev["start_utc"]).dt.date
        print(by.groupby("date")["d_eia_mw"].agg(["count", "min"])
              .to_string())


if __name__ == "__main__":
    main()
