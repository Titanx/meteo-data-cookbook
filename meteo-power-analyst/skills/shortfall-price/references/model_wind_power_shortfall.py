"""ERCOT 风功率物理链路 + 风电缺口 × 电价弹性 (2025/2026, 对标 PS-021~027 光伏链)

动机 (PS-022 推广方向): 光伏链已建成"物理反事实 → 缺口 → 电价"并证缺口正相关电价。
风电同法推演: 用 HRRR 80m 风速 + 风功率曲线重建 fleet 资源潜力, 与 EIA-930 实际风电对比。

⚠ 概念要点 (与光伏的关键差异):
  光伏"晴空反事实"是**确定上界**(太阳位置精确已知), 缺口 = 云致供给收缩 → 推高价格。
  风电的"资源潜力"同样可由风速算出, 但风速本身就定义了资源 ⇒ 潜力−实际 ≈ 
  **弃风 + 场损/可用率**, 而非"低风缺口"。ERCOT 弃风集中在高风+低需求(夜间)时段,
  因此预计风电缺口与电价**负相关** —— 与光伏符号相反。本脚本同时给出:
    (a) 资源潜力缺口 w_short = 潜力 − 实际 (≈ 弃风+损失)  -> 预期负号
    (b) 低风异常 w_drought = 容量因子气候偏离 (天气型低风) -> 预期正号
  以证"缺口→电价"机制在风光上不对称, 不能简单套用。

校准: 与 PS-022/024 同法 —— 逐小时偏移 = 该小时 (潜力 − 实际) 的 5% 分位
      (资源最好 5% 小时视为无弃风无损失), 自动吸收 HRRR 风速系统偏差与场损率选择。
输入: data/nsrdb/hrrr_wind80m_2025_2026.npz, data/gem/ercot_wind_plants_2025.csv,
      data/ercot/ercot_hourly_panel_{2025,2026}.csv
输出: data/ercot/wind_shortfall_2025_2026.csv, wind_power_hourly_2025_2026.csv
用法: python skills/shortfall-price/references/model_wind_power_shortfall.py
"""
import os

import numpy as np
import pandas as pd

NPZ = r"c:\work\meteo\data\nsrdb\hrrr_wind80m_2025_2026.npz"
HUB = r"c:\work\meteo\data\gem\ercot_wind_plants_2025.csv"
PANEL = {2025: r"c:\work\meteo\data\ercot\ercot_hourly_panel_2025.csv",
         2026: r"c:\work\meteo\data\ercot\ercot_hourly_panel_2026.csv"}
OUT_H = r"c:\work\meteo\data\ercot\wind_power_hourly_2025_2026.csv"
OUT_SF = r"c:\work\meteo\data\ercot\wind_shortfall_2025_2026.csv"
OUT_EL = r"c:\work\meteo\data\ercot\wind_elasticity_2025.csv"

ETA_FARM = 0.90            # 场内尾流+电气+可用率 (标定前设定, 残差由偏移吸收)
PC_V = np.array([0.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0,
                 12.6, 25.0, 25.1, 60.0])
PC_P = np.array([0.0, 0.0, 0.055, 0.127, 0.235, 0.366, 0.510, 0.660, 0.808,
                 0.935, 1.0, 1.0, 1.0, 0.0, 0.0])
ROWS = []


def power_curve(v):
    return np.interp(v, PC_V, PC_P)


def load_fleet_potential():
    d = np.load(NPZ, allow_pickle=True)
    ws = d["ws80"]                                  # (nt, nhub) m/s
    cap = d["capacity_mw"].astype(float)            # (nhub,) MW
    times = pd.to_datetime(d["times"])
    pc = power_curve(np.clip(ws, 0, 60))            # (nt, nhub)
    # 机位加权 fleet 归一化出力 (容量加权平均 PC) × 总容量 × 场损
    w = cap / cap.sum()
    fleet_pc = pc @ w                               # (nt,) 0~1
    pot = fleet_pc * cap.sum() * ETA_FARM
    s = pd.Series(pot, index=times, name="wind_pot")
    s = s[~s.index.duplicated(keep="first")].sort_index()
    return s, cap.sum(), ws, cap, times


def regress(y, num_df, num_cols, fe_specs):
    mats = [np.column_stack([np.ones(len(y))] +
                            [num_df[c].values for c in num_cols])]
    for values, prefix, ref in fe_specs:
        s = pd.Series(np.asarray(values))
        cats = sorted(s.unique())
        if ref is None:
            ref = cats[0]
        m = [ (s == c).astype(float).values for c in cats if c != ref ]
        if m:
            mats.append(np.column_stack(m))
    X = np.column_stack(mats)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    names = ["const"] + num_cols
    return names, beta, se


def rec(year, model, param, est, se, n):
    ROWS.append({"year": year, "model": model, "param": param,
                 "estimate_pct_per_gw": est * 100000.0 if est is not None else np.nan,
                 "se_pct_per_gw": se * 100000.0 if se is not None else np.nan, "n": n})


def main():
    pot, tot_mw, ws, cap, wt = load_fleet_potential()
    print(f"风电场 {len(cap)} 点位, 总容量 {tot_mw/1000:.2f} GW, "
          f"风速序列 {ws.shape[0]} 小时 {wt.min().date()}~{wt.max().date()}")
    print(f"资源潜力(标定前): 均值 {pot.mean():.0f} MW, 峰值 {pot.max():.0f} MW, "
          f"等效容量因子 {pot.mean()/tot_mw:.3f}")

    frames = []
    for year, path in PANEL.items():
        p = pd.read_csv(path, index_col=0, parse_dates=True)
        frames.append(p)
    pan = pd.concat(frames)
    pan = pan[~pan.index.duplicated(keep="first")].sort_index()

    # --- 时滞诊断 (确认时间对齐) ---
    print("\n== 时滞诊断 (潜力 vs 实际风电 相关) ==")
    for lag in (-2, -1, 0, 1, 2):
        a = pot.reindex(pan.index + pd.Timedelta(hours=lag))
        m = pd.DataFrame({"p": a.values, "w": pan["wind"].values}).dropna()
        print(f"  lag {lag:+d}h: r = {m['p'].corr(m['w']):.4f}")

    df = pd.DataFrame({"pot": pot.reindex(pan.index), "act": pan["wind"],
                       "demand": pan["demand"], "rtm": pan["rtm"],
                       "dam": pan["dam"]}).dropna()
    df["year"] = df.index.year
    print(f"\n建模样本 {len(df)} 小时 ({df.index.min()} ~ {df.index.max()})")
    print(f"实际风电 均值 {df['act'].mean():.0f} MW, 容量因子 {df['act'].mean()/tot_mw:.3f}")
    print(f"潜力/实际 能量比 {df['pot'].sum()/df['act'].sum():.3f}")

    for year in (2025, 2026):
        d = df[df["year"] == year]
        print(f"  {year}: n={len(d)} r={d['pot'].corr(d['act']):.4f} "
              f"能量比 {d['pot'].sum()/d['act'].sum():.3f} "
              f"潜力CF {d['pot'].mean()/tot_mw:.3f} 实际CF {d['act'].mean()/tot_mw:.3f}")

    # --- 逐小时偏移校准 (与 PS-022/024 同法) ---
    raw = df["pot"] - df["act"]
    off_h = raw.groupby(df.index.hour).quantile(0.05)
    df["w_short"] = (raw - off_h.reindex(df.index.hour).values).clip(lower=0)
    print(f"\n== 风电缺口 w_short = 潜力 − 实际 − 偏移 (≈弃风+场损) ==")
    print(f"  偏移(逐小时q05) 范围 {off_h.min():.0f} ~ {off_h.max():.0f} MW")
    print(f"  缺口: 中位 {df['w_short'].median():.0f}, 均值 {df['w_short'].mean():.0f}, "
          f"P95 {df['w_short'].quantile(.95):.0f} MW")
    print(f"  弃风/损失占比 (缺口能量/潜力能量) {df['w_short'].sum()/df['pot'].sum()*100:.1f}%")

    # 低风异常 (容量因子气候偏离): 按 (hour, 月) 的 P50 为气候基准
    cf = df["act"] / tot_mw
    clim = cf.groupby([df.index.hour, df.index.month]).transform("median")
    df["w_drought"] = (clim - cf).clip(lower=0) * tot_mw     # MW 不足
    print(f"  低风异常 w_drought: 中位 {df['w_drought'].median():.0f}, "
          f"P95 {df['w_drought'].quantile(.95):.0f} MW")

    # --- 缺口的时段/工况结构 ---
    print("\n== 缺口工况结构 (判断是弃风还是低风) ==")
    hh = df.groupby(df.index.hour).agg(ws=("w_short", "mean"),
                                       wind=("act", "mean"),
                                       dem=("demand", "mean"),
                                       pot=("pot", "mean"))
    for h in (0, 3, 6, 9, 12, 15, 18, 21):
        r = hh.loc[h]
        print(f"  {h:02d}UTC: 缺口 {r['ws']:5.0f} MW | 实际风 {r['wind']:6.0f} | "
              f"潜力 {r['pot']:6.0f} | 需求 {r['dem']:6.0f}")
    hi = df[df["act"] > df["act"].quantile(0.9)]
    lo = df[df["act"] < df["act"].quantile(0.1)]
    print(f"  高风小时(>P90): 缺口均值 {hi['w_short'].mean():.0f} MW, 需求均值 {hi['demand'].mean():.0f}")
    print(f"  低风小时(<P10): 缺口均值 {lo['w_short'].mean():.0f} MW, 需求均值 {lo['demand'].mean():.0f}")

    # --- 电价弹性 ---
    print("\n== 电价弹性 (%/GW, 全小时, hour+month FE) ==")
    out = {}
    for year in (2025, 2026):
        d = df[df["year"] == year].copy()
        lnp = np.log(d["rtm"].clip(lower=1)).values
        fe = [(d.index.hour, "h", None), (d.index.month, "m", None)]
        # (a) 风电缺口
        n, b, s = regress(lnp, d, ["w_short", "demand"], fe)
        out[(year, "w_short")] = (b[n.index("w_short")], s[n.index("w_short")])
        rec(year, "wind_short", "w_short", *out[(year, "w_short")], len(d))
        # (b) 低风异常
        n2, b2, s2 = regress(lnp, d, ["w_drought", "demand"], fe)
        out[(year, "w_drought")] = (b2[n2.index("w_drought")], s2[n2.index("w_drought")])
        rec(year, "drought", "w_drought", *out[(year, "w_drought")], len(d))
        # (c) 实际风电水平 (对照光伏水平项)
        n3, b3, s3 = regress(lnp, d, ["act", "demand"], fe)
        out[(year, "act")] = (b3[n3.index("act")], s3[n3.index("act")])
        rec(year, "level", "act", *out[(year, "act")], len(d))
        PG = 100000.0
        print(f"  {year}: 风电缺口 {out[(year,'w_short')][0]*PG:+.3f} "
              f"(SE {out[(year,'w_short')][1]*PG:.3f})%/GW | "
              f"低风异常 {out[(year,'w_drought')][0]*PG:+.3f} "
              f"(SE {out[(year,'w_drought')][1]*PG:.3f})%/GW | "
              f"风电水平 {out[(year,'act')][0]*PG:+.3f} %/GW")

    # --- 光伏/风电联合 (白天小时, 与 PS-024 口径对照) ---
    print("\n== 风光联合弹性 (白天小时, 对照 PS-024 光伏) ==")
    cs = pd.read_csv(r"c:\work\meteo\data\nsrdb\pv_clearsky_hourly_2025_2026.csv",
                     index_col=0, parse_dates=True)
    cs.index = pd.to_datetime(cs.index, utc=True).tz_localize(None)
    cs = cs[~cs.index.duplicated(keep="first")]
    for year in (2025, 2026):
        pp = pd.read_csv(PANEL[year], index_col=0, parse_dates=True)
        d = df[df["year"] == year].join(
            pp[["solar"]].rename(columns={"solar": "solar"}), how="inner")
        d = d.join(cs, how="inner").dropna(subset=["clearsky_mw", "solar"])
        dd = d[d.index.hour.isin(range(14, 24))].copy()
        rp = dd["clearsky_mw"] - dd["solar"]
        off = rp.groupby(dd.index.hour).quantile(0.05)
        dd["pv_short"] = (rp - off.reindex(dd.index.hour).values).clip(lower=0)
        lnp = np.log(dd["rtm"].clip(lower=1)).values
        fe = [(dd.index.hour, "h", None), (dd.index.month, "m", None)]
        n, b, s = regress(lnp, dd, ["pv_short", "w_short", "demand"], fe)
        PG = 100000.0
        print(f"  {year}: 光伏缺口 {b[n.index('pv_short')]*PG:+.3f}%/GW | "
              f"风电缺口 {b[n.index('w_short')]*PG:+.3f}%/GW | n={len(dd)}")
        rec(year, "joint_day", "pv_short", b[n.index("pv_short")], s[n.index("pv_short")], len(dd))
        rec(year, "joint_day", "w_short", b[n.index("w_short")], s[n.index("w_short")], len(dd))

    # --- 机制检验: 缺口是"外生供给冲击"还是"内生弃风" ---
    print("\n== 机制检验 A: 加入实际风电后缺口系数是否稳健 ==")
    for year in (2025, 2026):
        d = df[df["year"] == year]
        lnp = np.log(d["rtm"].clip(lower=1)).values
        fe = [(d.index.hour, "h", None), (d.index.month, "m", None)]
        n, b, s = regress(lnp, d, ["w_short", "act", "demand"], fe)
        PG = 100000.0
        print(f"  {year}: w_short {b[n.index('w_short')]*PG:+.3f} "
              f"(SE {s[n.index('w_short')]*PG:.3f}) | act {b[n.index('act')]*PG:+.3f} | "
              f"n={len(d)}")
        rec(year, "mech_control_act", "w_short", b[n.index("w_short")],
            s[n.index("w_short")], len(d))

    print("\n== 机制检验 B: 高缺口小时的负/低价频率 (弃风特征) ==")
    for year in (2025, 2026):
        d = df[df["year"] == year]
        q = d["w_short"].quantile(0.9)
        hi = d[d["w_short"] >= q]
        lo = d[d["w_short"] <= d["w_short"].quantile(0.5)]
        print(f"  {year}: 高缺口(>P90={q:.0f}MW) n={len(hi)}: RTM中位 {hi['rtm'].median():.1f}, "
              f"负价(<$5)占比 {(hi['rtm']<5).mean()*100:.1f}%, 需求中位 {hi['demand'].median():.0f} | "
              f"低缺口 n={len(lo)}: RTM中位 {lo['rtm'].median():.1f}, "
              f"负价占比 {(lo['rtm']<5).mean()*100:.1f}%")

    print("\n== 机制检验 C: 时间对齐敏感性 (滞后 +1h 重算弹性) ==")
    pot1 = pot.shift(1)
    r1 = pot1.reindex(pan.index) - pan["wind"]
    off1 = r1.groupby(pan.index.hour).quantile(0.05)
    ws1 = (r1 - off1.reindex(pan.index.hour).values).clip(lower=0)
    d1 = pd.DataFrame({"w_short": ws1, "demand": pan["demand"],
                       "rtm": pan["rtm"]}).dropna()
    d1["year"] = d1.index.year
    for year in (2025, 2026):
        d = d1[d1["year"] == year]
        lnp = np.log(d["rtm"].clip(lower=1)).values
        fe = [(d.index.hour, "h", None), (d.index.month, "m", None)]
        n, b, s = regress(lnp, d, ["w_short", "demand"], fe)
        PG = 100000.0
        print(f"  {year}: 缺口(滞后1h) {b[n.index('w_short')]*PG:+.3f} %/GW "
              f"(SE {s[n.index('w_short')]*PG:.3f})")
        rec(year, "lag1", "w_short", b[n.index("w_short")], s[n.index("w_short")], len(d))

    print("\n== 机制检验 D: 高需求区弹性 (对照光伏热浪场景) ==")
    for year in (2025, 2026):
        d = df[(df["year"] == year) & (df["demand"] >= df["demand"].quantile(0.9))]
        lnp = np.log(d["rtm"].clip(lower=1)).values
        fe = [(d.index.hour, "h", None), (d.index.month, "m", None)]
        n, b, s = regress(lnp, d, ["w_short", "demand"], fe)
        PG = 100000.0
        print(f"  {year}: 高需求 (n={len(d)}) 缺口 {b[n.index('w_short')]*PG:+.3f} %/GW "
              f"(SE {s[n.index('w_short')]*PG:.3f}), RTM中位 {d['rtm'].median():.1f}")
        rec(year, "shortfall_hot", "w_short", b[n.index("w_short")],
            s[n.index("w_short")], len(d))

    print("\n== 机制检验 E: 光伏对称检验 (缺口是否也只是'光伏水平'的重编码) ==")
    for year in (2025, 2026):
        pp = pd.read_csv(PANEL[year], index_col=0, parse_dates=True)
        d = df[df["year"] == year].join(pp[["solar"]], how="inner")
        d = d.join(cs, how="inner").dropna(subset=["clearsky_mw", "solar"])
        d = d[d.index.hour.isin(range(14, 24))].copy()
        rp = d["clearsky_mw"] - d["solar"]
        off = rp.groupby(d.index.hour).quantile(0.05)
        d["pv_short"] = (rp - off.reindex(d.index.hour).values).clip(lower=0)
        lnp = np.log(d["rtm"].clip(lower=1)).values
        fe = [(d.index.hour, "h", None), (d.index.month, "m", None)]
        PG = 100000.0
        n1, b1, s1 = regress(lnp, d, ["pv_short", "demand"], fe)
        n2, b2, s2 = regress(lnp, d, ["pv_short", "solar", "demand"], fe)
        print(f"  {year}: 光伏缺口(仅) {b1[n1.index('pv_short')]*PG:+.3f} "
              f"(SE {s1[n1.index('pv_short')]*PG:.3f}) → "
              f"控光伏水平后 {b2[n2.index('pv_short')]*PG:+.3f} "
              f"(SE {s2[n2.index('pv_short')]*PG:.3f}); 光伏水平项 "
              f"{b2[n2.index('solar')]*PG:+.3f} %/GW")
        rec(year, "pv_control_level", "pv_short", b2[n2.index("pv_short")],
            s2[n2.index("pv_short")], len(d))

    print("\n== 机制检验 F: 共线性诊断 (缺口 vs 水平 能否分开识别) ==")
    for year in (2025, 2026):
        d = df[df["year"] == year]
        print(f"  {year}: corr(act, w_short) = {d['act'].corr(d['w_short']):+.3f}, "
              f"corr(pot, act) = {d['pot'].corr(d['act']):+.3f}")
        # 资源潜力本身的价格弹性
        lnp = np.log(d["rtm"].clip(lower=1)).values
        fe = [(d.index.hour, "h", None), (d.index.month, "m", None)]
        n, b, s = regress(lnp, d, ["pot", "demand"], fe)
        print(f"      资源潜力 pot 弹性 {b[n.index('pot')]*100000:.3f} %/GW "
              f"(SE {s[n.index('pot')]*100000:.3f})")
        rec(year, "level_pot", "pot", b[n.index("pot")], s[n.index("pot")], len(d))

    df.to_csv(OUT_H)
    print(f"\n→ {OUT_H}")

    daily = df.resample("D").agg(w_short_gwh=("w_short", lambda x: x.sum()/1e3),
                                 w_drought_gwh=("w_drought", lambda x: x.sum()/1e3),
                                 act_gwh=("act", lambda x: x.sum()/1e3),
                                 pot_gwh=("pot", lambda x: x.sum()/1e3),
                                 dem_peak=("demand", "max"),
                                 rtm_mean=("rtm", "mean"))
    daily.to_csv(OUT_SF)
    print(f"→ {OUT_SF}")
    pd.DataFrame(ROWS).to_csv(OUT_EL, index=False)
    print(f"→ {OUT_EL}")


if __name__ == "__main__":
    main()