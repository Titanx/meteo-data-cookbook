"""光伏节点级冲击验证: Hub vs 节点 (PS-046, 2026-09-07 ~ 2026-09-30)

问题: PS-022/PS-045 在 HB_HOUSTON 标定的缺口->电价弹性 (+5~9 %/GW), 是否低估了
      电站节点 (Resource Node) 结算点上的冲击? 云冲击在节点层面是否更尖锐、更分散、
      并由本地云驱动?

数据: 89 个 SLR 节点 + 12 个大电站节点 (ROSELAND/PROSPERO/JUNO/LHORN/SAMSON...),
      RTM 15min (GridStatus); 事件集 = battery_attribution_events.csv
      (缺口>=1.5GW, 15-23 UTC); 节点->电站匹配 46 个 (11.5 GW),
      本地 GHI = ERA5 逐时 (Open-Meteo, ercot_pv_node_om.npz;
      NASA POWER 2026-06-25 后缺数, 不可用)。

分析:
  A. 事件小时溢价 (DAM 锚定): ln(RTM_node/DAM_hub) = hub溢价 + 节点价差
  A2. 事件小时溢价 (同 hour-of-day 非事件中位锚, PS-045 事件口径): 节点 vs Hub,
      逐节点斜率 -> 容量加权, 含/不含小时FE 两版
  B. 横截面离散: 事件 vs 非事件小时的节点-Hub ln 价差 IQR/P90-P10, 离散度~缺口强度
  C. 15min 尖峰: 节点 vs Hub 的 P95/P99、>=100/500/1000 美元占比、触顶次数
  D. 本地云归因 (匹配节点): ln_prem ~ fleet缺口 + 本地GHI缺口 + 小时FE, 按小时聚类
  E. 窗口稳健性: 4 个 56 天节点 (08-06 起) 的事件溢价 vs 9 月窗口

输出: data/ercot/pv_node_shock_results.csv (A/B/C/D/E 全部指标)
      data/ercot/pv_node_hourly_premium.csv (图表用 tidy 溢价)
      data/ercot/pv_node_dispersion.csv (逐小时离散度)
      data/ercot/pv_node_local_panel.csv (D 回归面板)
用法: python skills/shortfall-price/references/pv_node_shock_analysis.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\ercot"
D_NPZ = r"c:\work\meteo\data\nasa_power"
W0, W1 = "2026-09-07", "2026-10-01"
PG = 100.0  # ln/MW -> %/GW 换算只用于 fleet 缺口; local_rel 无量纲

RESULTS = []


def rec(section, name, value, note=""):
    RESULTS.append({"section": section, "metric": name, "value": value, "note": note})
    if isinstance(value, float):
        v = f"{value:.4f}"
    else:
        v = str(value)
    print(f"[{section}] {name:42s} {v:>14s}  {note}")


def ols_cluster(X, y, cluster):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((k, k))
    df = pd.DataFrame({"c": cluster})
    for c, idx in df.groupby("c").groups.items():
        ii = np.asarray(list(idx), dtype=int)
        u = X[ii].T @ resid[ii]
        meat += np.outer(u, u)
    cov = XtX_inv @ meat @ XtX_inv
    g = len(set(cluster))
    cov *= g / (g - 1) * (n - 1) / max(n - k, 1)
    return beta, np.sqrt(np.clip(np.diag(cov), 0, None))


def load_ghi_node_map():
    """匹配节点 -> 逐时 GHI DataFrame (index=UTC hour, columns=node), ERA5/OM 单源"""
    d = np.load(os.path.join(D_NPZ, "ercot_pv_node_om.npz"), allow_pickle=True)
    t = pd.to_datetime([str(x) for x in d["times"]], format="%Y%m%d%H")
    ghi = pd.DataFrame(d["shortwave_radiation"], index=t,
                       columns=[str(x) for x in d["node"]])
    ghi = ghi[~ghi.index.duplicated()].sort_index()
    win = ghi.loc["2026-09-07":"2026-09-30 23:00"]
    print(f"GHI 面板 (ERA5/OM): {ghi.shape[1]} 节点, "
          f"{ghi.index.min()} ~ {ghi.index.max()}, "
          f"事件窗口非NaN {np.isfinite(win.values).mean():.3f}")
    return ghi


def clearsky_env(ghi, halfwin=15):
    """hour-of-day x doy 的 P95 晴空包络 (沿用 PS-024/PS-045 口径)"""
    doy = ghi.index.dayofyear.values
    hour = ghi.index.hour.values
    env = pd.DataFrame(index=ghi.index, columns=ghi.columns, dtype=float)
    for col in ghi.columns:
        vals = ghi[col].values
        mat = np.full((367, 24), np.nan)
        for h in range(24):
            mh = hour == h
            for dd in range(1, 366):
                w = mh & (np.abs(doy - dd) <= halfwin)
                if w.sum() >= 5:
                    mat[dd, h] = np.nanpercentile(vals[w], 95)
        env[col] = [mat[doy[i], hour[i]] for i in range(len(ghi))]
    return env


def main():
    # ---- 数据加载 ----
    hourly = pd.read_csv(os.path.join(D, "pv_node_hourly.csv"),
                         index_col=0, parse_dates=True)
    nodes = [c for c in hourly.columns if c != "HB_HOUSTON"]
    hub = hourly["HB_HOUSTON"]
    panel = pd.read_csv(os.path.join(D, "battery_attribution_panel.csv"),
                        index_col=0, parse_dates=True)
    ev = pd.read_csv(os.path.join(D, "battery_attribution_events.csv"),
                     index_col=0, parse_dates=True)

    w = hourly.loc[(hourly.index >= W0) & (hourly.index < W1)]
    evw = ev.loc[(ev.index >= W0) & (ev.index < W1)]
    ev_mask = w.index.isin(evw.index)
    daytime = (w.index.hour >= 15) & (w.index.hour <= 23)
    rec("0", "窗口", f"{W0}~{W1}",
        f"{len(w)}h, 事件 {ev_mask.sum()}, 白天 {daytime.sum()}")
    # fleet 缺口: 全小时口径 (来自 battery panel), 事件小时与 events 文件一致
    sf_all = (panel["shortfall"].reindex(w.index) / 1000.0)
    sf_all[panel["env"].reindex(w.index) <= 0] = np.nan
    sf_ev = evw["sf_gw"].reindex(w.index)
    assert np.allclose(sf_all[ev_mask].dropna(), sf_ev[ev_mask].dropna()), "口径校验失败"
    sf = sf_all

    # 覆盖率过滤: 节点窗口覆盖率 >= 90%
    cov = w[nodes].notna().mean()
    nodes_ok = cov[cov >= 0.9].index.tolist()
    rec("0", "有效节点 (覆盖>=90%)", len(nodes_ok),
        f"{len(nodes)} 中剔除 {len(nodes)-len(nodes_ok)}")

    # ---- 核心口径: 实时溢价 = ln(RTM_node / DAM_hub) = hub溢价 + 节点价差 ----
    dam = panel["dam"].reindex(w.index)
    lndam = np.log(dam.clip(lower=1.0))
    hub_surp = np.log(hub.reindex(w.index).clip(lower=1.0)) - lndam
    node_surp = np.log(w[nodes_ok].clip(lower=1.0)).sub(lndam, axis=0)

    # ---- A. 事件小时: Hub 溢价 vs 节点溢价分布 (DAM 锚定) ----
    ev_h = hub_surp[ev_mask]
    ev_n = node_surp[ev_mask]
    cap = pd.read_csv(os.path.join(D, "pv_node_match.csv")).set_index("node")["cap_mw"]
    cap_ok = cap.reindex(nodes_ok).dropna()
    evn_med = ev_n.median(axis=1)
    evn_p90 = ev_n.quantile(0.9, axis=1)
    capw = (ev_n[cap_ok.index] * cap_ok.values).sum(axis=1) / cap_ok.values.sum()
    matched_ok = [n for n in ev_n.columns if n in cap_ok.index]
    unmatch = [n for n in ev_n.columns if n not in cap_ok.index]
    rec("A", "Hub 实时溢价 中位 (事件, ln)", ev_h.median(), "ln(RTM_hub/DAM_hub)")
    rec("A", "节点实时溢价 中位 (事件, ln)", ev_n.stack().median(), "全部节点小时")
    rec("A", "逐时节点中位溢价 中位 (ln)", evn_med.median(), "")
    rec("A", "逐时节点P90溢价 中位 (ln)", evn_p90.median(), "尖尾")
    rec("A", "容量加权节点溢价 中位 (ln)", capw.median(),
        f"{len(cap_ok)} 匹配节点 {cap_ok.sum()/1000:.1f}GW")
    rec("A", "匹配节点溢价中位 (ln)", ev_n[matched_ok].stack().median(),
        f"vs 未匹配 {ev_n[unmatch].stack().median():.3f}")
    rec("A", "节点溢价>Hub的小时占比", (evn_med > ev_h).mean(), "逐小时")
    rec("A", "节点P90>Hub的占比", (evn_p90 > ev_h).mean(), "")
    # 非事件白天 (安慰剂)
    ne_h = hub_surp[~ev_mask & daytime]
    ne_n = node_surp[~ev_mask & daytime]
    rec("A", "Hub 溢价 中位 (非事件白天)", ne_h.median(), "安慰剂")
    rec("A", "节点溢价 中位 (非事件白天)", ne_n.stack().median(), "安慰剂")

    # 事件小时弹性: pooled 节点 vs Hub (斜率=弹性, %/GW)
    ee = pd.DataFrame({"sf": sf[ev_mask], "hub": hub_surp[ev_mask]})
    ee = ee.dropna()
    X = np.column_stack([np.ones(len(ee)), ee["sf"].values])
    bh, sh = ols_cluster(X, ee["hub"].values, ee.index.date)
    rec("A", "Hub 弹性 (事件小时, ln/GW)", bh[1], f"SE {sh[1]:.3f} 聚类=日")
    # pooled 节点弹性: 逐节点斜率后容量加权
    slopes = []
    for n in nodes_ok:
        s = pd.DataFrame({"sf": sf[ev_mask], "y": node_surp[ev_mask][n]}).dropna()
        if len(s) >= 50:
            b, _ = ols_cluster(np.column_stack([np.ones(len(s)), s["sf"].values]),
                               s["y"].values, s.index.date)
            slopes.append((n, b[1]))
    sl = pd.DataFrame(slopes, columns=["node", "slope"]).set_index("node")
    sl["cap"] = cap.reindex(sl.index).fillna(0)
    pooled = (sl["slope"] * sl["cap"]).sum() / sl["cap"].sum() if sl["cap"].sum() > 0 else np.nan
    rec("A", "节点中位弹性 (逐节点斜率中位, ln/GW)", sl["slope"].median(),
        f"n={len(sl)}")
    rec("A", "容量加权节点弹性 (ln/GW)", pooled,
        f"vs Hub {bh[1]:.3f}; 低估比 {bh[1]/pooled if pooled else float('nan'):.2f}x" if pooled else "")
    sl.to_csv(os.path.join(D, "pv_node_elasticity.csv"))

    # ---- A2. 事件小时溢价 (同 hour-of-day 非事件中位锚, PS-045 事件口径) ----
    # 与 DAM 锚不同: 基线是"该小时通常什么价", 溢价度量冲击时刻相对典型水平的偏离,
    # 与 PS-022/045 头条弹性 (+5~9 %/GW) 同一量纲, 可直接对比 Hub vs 结算点。
    ne_day = (~ev_mask) & daytime
    lnrtm = np.log(w[nodes_ok].clip(lower=1.0))
    lnhub = np.log(hub.reindex(w.index).clip(lower=1.0))
    bas_n, bas_h = {}, {}
    for h in range(15, 24):
        m = ne_day & (w.index.hour == h)
        if m.sum() >= 2:
            bas_n[h] = lnrtm[m].median()
            bas_h[h] = lnhub[m].median()
    rec("A2", "非事件白天小时数", int(ne_day.sum()),
        f"基线 hour-of-day 覆盖 {len(bas_n)}/9")
    ev_idx = w.index[ev_mask]
    ev_hr = ev_idx.hour
    ok_h = np.isin(ev_hr, list(bas_h.keys()))
    pb_hub = lnhub.loc[ev_idx].values - pd.Series(bas_h).reindex(ev_hr).values
    pb_nodes = {}
    for n in nodes_ok:
        b = pd.Series({h: bas_n[h][n] for h in bas_n})
        pb_nodes[n] = lnrtm[n].loc[ev_idx].values - b.reindex(ev_hr).values
    pb_n = pd.DataFrame(pb_nodes, index=ev_idx)
    sf_ev = sf[ev_mask].values
    date_ev = ev_idx.date
    rec("A2", "Hub 冲击溢价 中位 (事件, ln)",
        np.nanmedian(pb_hub[ok_h]), "ln(RTM_hub/同小时非事件中位)")
    rec("A2", "节点冲击溢价 中位 (事件, ln)", np.nanmedian(pb_n.values[ok_h]),
        "全部节点小时")
    # Hub 斜率: 无FE / 含小时FE
    m_h = ok_h & np.isfinite(pb_hub) & np.isfinite(sf_ev)
    bh2, sh2 = ols_cluster(np.column_stack([np.ones(m_h.sum()), sf_ev[m_h]]),
                           pb_hub[m_h], np.asarray(date_ev)[m_h])
    rec("A2", "Hub 弹性 (事件, ln/GW)", bh2[1], f"SE {sh2[1]:.3f} 聚类=日")
    hrs_ev = np.asarray(ev_hr)
    H2 = np.column_stack([(hrs_ev[m_h] == h).astype(float)
                          for h in sorted(bas_h)[:-1]])
    bh2f, sh2f = ols_cluster(np.column_stack([np.ones(m_h.sum()), sf_ev[m_h], H2]),
                             pb_hub[m_h], np.asarray(date_ev)[m_h])
    rec("A2", "Hub 弹性 (事件, 含小时FE)", bh2f[1], f"SE {sh2f[1]:.3f}")
    # 逐节点斜率 -> 容量加权 (无FE / 含FE)
    sl2, sl2f = [], []
    for n in nodes_ok:
        y = pb_n[n].values
        m = ok_h & np.isfinite(y) & np.isfinite(sf_ev)
        if m.sum() < 50:
            continue
        b_, _ = ols_cluster(np.column_stack([np.ones(m.sum()), sf_ev[m]]),
                            y[m], np.asarray(date_ev)[m])
        sl2.append((n, b_[1]))
        Hn = np.column_stack([(hrs_ev[m] == h).astype(float)
                              for h in sorted(bas_h)[:-1]])
        bf_, _ = ols_cluster(np.column_stack([np.ones(m.sum()), sf_ev[m], Hn]),
                             y[m], np.asarray(date_ev)[m])
        sl2f.append((n, bf_[1]))
    s2 = pd.DataFrame(sl2, columns=["node", "slope"]).set_index("node")
    s2f = pd.DataFrame(sl2f, columns=["node", "slope"]).set_index("node")
    for tag, df_ in [("无FE", s2), ("含小时FE", s2f)]:
        df_["cap"] = cap.reindex(df_.index).fillna(0)
        pw = (df_["slope"] * df_["cap"]).sum() / df_["cap"].sum()
        rec("A2", f"容量加权节点弹性 ({tag}, ln/GW)", pw,
            f"n={len(df_)}; vs Hub {bh2[1]:.3f}"
            + (f"; Hub/节点 {bh2[1]/pw:.2f}x" if pw else ""))
        rec("A2", f"节点弹性中位 ({tag}, ln/GW)", df_["slope"].median(), "")
    s2f.to_csv(os.path.join(D, "pv_node_elasticity_baseline.csv"))

    # ---- B. 横截面离散: 节点-Hub ln 价差 ----
    lr = np.log(w[nodes_ok].clip(lower=1.0)).sub(
        np.log(hub.reindex(w.index).clip(lower=1.0)), axis=0)
    lvl = w[nodes_ok].sub(hub.reindex(w.index), axis=0)
    disp = pd.DataFrame(index=w.index)
    for m, tag in [(ev_mask & daytime, "事件"), (~ev_mask & daytime, "非事件")]:
        q75, q25 = lr[m].quantile(0.75, axis=1), lr[m].quantile(0.25, axis=1)
        q90, q10 = lr[m].quantile(0.9, axis=1), lr[m].quantile(0.1, axis=1)
        late = w.index.hour >= 18
        ml = m & late
        q90l, q10l = lr[ml].quantile(0.9, axis=1), lr[ml].quantile(0.1, axis=1)
        rec("B", f"{tag} IQR (全白天)", (q75 - q25).median(), "")
        rec("B", f"{tag} P90-P10 (全白天)", (q90 - q10).median(), "")
        rec("B", f"{tag} P90-P10 (18-23UTC)", (q90l - q10l).median(),
            "排除清晨 surplus 小时")
        rec("B", f"{tag} 价差P90 ($/MWh)", lvl[m].quantile(0.9, axis=1).median(), "")
    dd = pd.DataFrame({"p9010": lr[daytime].quantile(0.9, axis=1)
                       - lr[daytime].quantile(0.1, axis=1),
                       "sf": sf[daytime]}, index=w.index[daytime]).dropna()
    X = np.column_stack([np.ones(len(dd)), dd["sf"].values])
    b, s = ols_cluster(X, dd["p9010"].values, dd.index.date)
    rec("B", "离散(P90-P10)~缺口 斜率 (ln/GW)", b[1], f"SE {s[1]:.3f} 聚类=日")
    disp["p9010"] = dd["p9010"].reindex(w.index)
    disp["sf_gw"] = sf
    disp["is_event"] = ev_mask
    disp["is_daytime"] = daytime
    disp.to_csv(os.path.join(D, "pv_node_dispersion.csv"))

    # ---- C. 15min 尖峰强度 ----
    p15 = pd.read_csv(os.path.join(D, "pv_node_panel_15min.csv"), parse_dates=["ts"])
    p15 = p15[(p15["ts"] >= W0) & (p15["ts"] < W1)]
    ev_h_set = set(w.index[ev_mask])
    p15["is_ev"] = p15["ts"].dt.floor("h").isin(ev_h_set)
    node15 = p15[p15["node"].isin(nodes_ok)]
    hub15 = p15[p15["node"] == "HB_HOUSTON"]
    for tag, sub_n, sub_h in [("事件", node15[node15["is_ev"]], hub15[hub15["is_ev"]]),
                              ("非事件", node15[~node15["is_ev"]], hub15[~hub15["is_ev"]])]:
        rec("C", f"{tag} Hub P99 ($/MWh)", sub_h["spp"].quantile(0.99), "15min")
        rec("C", f"{tag} 节点 P99 ($/MWh)", sub_n["spp"].quantile(0.99), "逐节点逐interval池化")
        rec("C", f"{tag} 节点>=1000 占比%", (sub_n["spp"] >= 1000).mean()*100, "")
        rec("C", f"{tag} Hub>=1000 占比%", (sub_h["spp"] >= 1000).mean()*100, "")
        rec("C", f"{tag} 节点>=500 占比%", (sub_n["spp"] >= 500).mean()*100, "")
        rec("C", f"{tag} Hub>=500 占比%", (sub_h["spp"] >= 500).mean()*100, "")
    ev_nodes_hi = node15[node15["is_ev"]].groupby("node")["spp"].max()
    rec("C", "事件中曾>=1000的节点数", (ev_nodes_hi >= 1000).sum(),
        f"/ {ev_nodes_hi.size}; Hub 事件段最大 ${hub15[hub15['is_ev']]['spp'].max():.0f}")
    rec("C", "事件段节点最大价 ($/MWh)", ev_nodes_hi.max(), "")
    spikes = pd.DataFrame({
        "node": ev_nodes_hi.index, "max_ev": ev_nodes_hi.values})
    spikes.to_csv(os.path.join(D, "pv_node_spikes.csv"), index=False)

    # ---- D. 本地云归因 (匹配节点) ----
    ghi = load_ghi_node_map()
    matched = [n for n in ghi.columns if n in nodes_ok]
    rec("D", "本地归因节点数", len(matched), f"GHI∩价格覆盖")
    env = clearsky_env(ghi[matched])
    loc_rel = (1.0 - ghi[matched] / env.clip(lower=1.0))
    loc_valid = env >= 100.0  # 白天有效

    # tidy 回归面板: MultiIndex (ts, node) 对齐 join (层级命名后 join)
    dfd = node_surp[matched].stack().to_frame("y")
    dfd.index = dfd.index.set_names(["ts", "node"])
    ls = loc_rel.stack().to_frame("local_rel")
    ls.index = ls.index.set_names(["ts", "node"])
    vs_ = loc_valid.stack().to_frame("day_ok")
    vs_.index = vs_.index.set_names(["ts", "node"])
    dfd = dfd.join(ls, how="left").join(vs_, how="left")
    ts_lvl = dfd.index.get_level_values(0)
    dfd["sf_gw"] = sf.reindex(ts_lvl).values
    dfd["hour"] = ts_lvl.hour
    dfd["is_event"] = ts_lvl.isin(ev_h_set)
    dfd = dfd[dfd["day_ok"].fillna(False) & dfd["y"].notna()
              & dfd["local_rel"].notna() & dfd["sf_gw"].notna()]
    rec("D", "回归样本 (白天全时, 节点x小时)", len(dfd),
        f"事件 {int(dfd['is_event'].sum())}, 小时 {dfd.index.get_level_values(0).nunique()}")
    # 效度: 事件小时 fleet 缺口 vs 节点平均本地 GHI 缺口
    lr_mean = loc_rel.mean(axis=1).reindex(w.index)
    m_ev2 = ev_mask & lr_mean.notna() & sf.notna()
    rec("D", "corr(fleet缺口, 节点平均本地缺口) 事件小时",
        float(np.corrcoef(sf[m_ev2], lr_mean[m_ev2])[0, 1]),
        f"n={int(m_ev2.sum())}; ERA5 本地云度量效度")

    H = np.column_stack([(dfd["hour"] == h).astype(float) for h in range(16, 24)])
    X = np.column_stack([np.ones(len(dfd)), dfd["sf_gw"].values,
                         dfd["local_rel"].values, H])
    ts_arr = dfd.index.get_level_values(0)
    b, s = ols_cluster(X, dfd["y"].values, ts_arr)
    rec("D", "fleet缺口弹性 (全样本, ln/GW)", b[1], f"SE {s[1]:.3f} 聚类=小时")
    rec("D", "本地GHI缺口系数 (全样本, ln/100%)", b[2]*100, f"SE {s[2]*100:.2f}")
    m_ev = dfd["is_event"].values.astype(bool)
    be, se_ = ols_cluster(X[m_ev], dfd["y"].values[m_ev], ts_arr[m_ev])
    rec("D", "fleet缺口弹性 (事件小时)", be[1], f"SE {se_[1]:.3f}")
    rec("D", "本地GHI缺口系数 (事件小时)", be[2]*100, f"SE {se_[2]*100:.2f}")
    me = (~m_ev)
    bn, sn_ = ols_cluster(X[me], dfd["y"].values[me], ts_arr[me])
    rec("D", "本地GHI缺口系数 (非事件白天, 安慰剂)", bn[2]*100, f"SE {sn_[2]*100:.2f}")
    inter = dfd["sf_gw"].fillna(0).values * dfd["local_rel"].values
    Xi = np.column_stack([X, inter])
    bi, si = ols_cluster(Xi, dfd["y"].values, ts_arr)
    rec("D", "fleet×本地交互 (ln/GW)", bi[3], f"SE {si[3]:.3f}")
    # 本地命中事件: local_rel>=0.5 且 hub 自身溢价低 (排除 fleet 共振)
    hit = (dfd["local_rel"] >= 0.5) & (dfd["is_event"] == False)
    rec("D", "本地命中且非fleet事件: 样本数", int(hit.sum()),
        f"其中 y 中位 {dfd['y'][hit].median() if hit.any() else float('nan'):.3f}")
    # ---- D2. 剂量反应: 事件小时按 local_rel 分箱的 y 中位 (解读离群敏感的回归系数) ----
    dfe = dfd[dfd["is_event"]]
    for lo in (0.0, 0.2, 0.4, 0.6):
        m = (dfe["local_rel"] >= lo) & (dfe["local_rel"] < lo + 0.2)
        if m.sum() >= 30:
            rec("D2", f"事件 y中位 | local_rel [{lo:.1f},{lo+0.2:.1f})",
                float(dfe["y"][m].median()), f"n={int(m.sum())}")
    m_hi = dfe["local_rel"] >= 0.8
    if m_hi.sum() >= 10:
        rec("D2", "事件 y中位 | local_rel [0.8,1]",
            float(dfe["y"][m_hi].median()), f"n={int(m_hi.sum())}")
    m_lo = dfe["local_rel"] < 0.2
    rec("D2", "事件 y中位 | local_rel <0.2 (无本地云)",
        float(dfe["y"][m_lo].median()), f"n={int(m_lo.sum())}")
    m50 = dfe["local_rel"] >= 0.5
    rec("D2", "事件 y中位 | local_rel >=0.5 (深本地云)",
        float(dfe["y"][m50].median()), f"n={int(m50.sum())}")
    # ---- D3. 截尾稳健性: y 截到 P99 后重跑事件回归 ----
    p99 = float(dfe["y"].quantile(0.99))
    yw = dfe["y"].clip(upper=p99).values
    bw, sw_ = ols_cluster(X[m_ev], yw, ts_arr[m_ev])
    rec("D3", f"事件本地系数 (y截尾P99={p99:.2f}, ln/100%)", bw[2]*100,
        f"SE {sw_[2]*100:.2f}; fleet {bw[1]:.4f} (SE {sw_[1]:.4f})")
    dfd.reset_index(names=["ts", "node"]).to_csv(
        os.path.join(D, "pv_node_local_panel.csv"), index=False)

    # ---- E. 窗口稳健性: 长窗口节点 08-06 起 (DAM 锚定口径) ----
    LONG = ["FIVEWSLR_ALL", "FRYE_SLR_ALL", "HRNT_SLR_RN", "SAMSON_ALL"]
    wl = hourly.loc["2026-08-06":"2026-09-30 23:00"]
    pl_dam = np.log(panel["dam"].clip(lower=1.0)).reindex(wl.index)
    evl = ev.loc["2026-08-06":"2026-09-30 23:00"]
    evl_mask = wl.index.isin(evl.index)
    dl = (wl.index.hour >= 15) & (wl.index.hour <= 23)
    sfl = (panel["shortfall"].reindex(wl.index) / 1000.0)
    sfl[panel["env"].reindex(wl.index) <= 0] = np.nan
    for n in LONG:
        if n not in wl.columns or wl[n].notna().sum() < 500:
            continue
        surp = np.log(wl[n].clip(lower=1.0)) - pl_dam
        m = evl_mask & dl
        aug = surp[m & (wl.index < W0)].dropna()
        sep = surp[m & (wl.index >= W0)].dropna()
        rec("E", f"{n} 事件溢价 全窗 (ln)", surp[m].dropna().median(),
            f"8月部分 {aug.median() if len(aug) else float('nan'):.3f}; "
            f"9月部分 {sep.median() if len(sep) else float('nan'):.3f}")
        s2 = pd.DataFrame({"sf": sfl[m], "y": surp[m]}).dropna()
        if len(s2) >= 30:
            b2, s2e = ols_cluster(np.column_stack([np.ones(len(s2)), s2["sf"].values]),
                                  s2["y"].values, s2.index.date)
            rec("E", f"{n} 弹性 (全窗, ln/GW)", b2[1], f"SE {s2e[1]:.3f}")

    # ---- 落盘 ----
    tidy = node_surp.copy()
    tidy["HB_HOUSTON"] = hub_surp
    tidy["event"] = ev_mask
    tidy["sf_gw"] = sf
    tidy.index.name = "ts_utc"
    tidy.to_csv(os.path.join(D, "pv_node_hourly_premium.csv"))
    out = pd.DataFrame(RESULTS)
    out.to_csv(os.path.join(D, "pv_node_shock_results.csv"), index=False)
    print(f"\n已保存 {len(RESULTS)} 条指标 -> pv_node_shock_results.csv")


if __name__ == "__main__":
    main()
