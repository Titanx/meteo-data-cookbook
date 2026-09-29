# -*- coding: utf-8 -*-
"""法国 NWP 预报 → 正午(当地 10-16h)日尺度面板 —— PS-043

把 20 个 GEM 法国光伏代表点位的 NWP 预报(ECMWF IFS, D1~D7)按**容量加权**聚合成全国指数,
再压到当地日/正午窗口, 与 PS-042 的 `france_noon_panel.csv` 对齐。

口径:
  · 窗口 = 当地 10–16h (Europe/Paris) —— 与 PS-040/041/042 一致
  · 全国指数 = Σ_h share_h × 变量_h  (容量加权平均; GHI 单位 W/m², 温度 °C)
  · 日尺度取窗口内**均值**(辐射)与**均值**(温度); 另存窗口内均值即可(日照强度而非能量)
  · `ghi_obs` / `t2m_obs` 来自 ERA5 archive, 作为训练用"真值气象"与预报误差核验基准

输入:  data/openmeteo_nwp_france/fr_nwp_prevruns_*.npz, fr_ghi_archive.npz,
       data/gem/france_solar_hubs_2024.csv, data/spain/france_noon_panel.csv
输出:  data/spain/france_nwp_panel.csv
用法:  python scripts/analysis/build_france_nwp_panel.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

NWP = Path(r"c:\work\meteo\data\openmeteo_nwp_france")
SP = Path(r"c:\work\meteo\data\spain")
HUBS = Path(r"c:\work\meteo\data\gem\france_solar_hubs_2024.csv")
TZ = "Europe/Paris"
NOON = (10, 16)
LEADS = list(range(1, 8))


def load_chunks():
    out = []
    for f in sorted(NWP.glob("fr_nwp_prevruns_*.npz")):
        z = np.load(f)
        t = pd.DatetimeIndex(z["time"]).tz_localize("UTC")
        out.append((z, t))
    return out


def stack(zs):
    """把 (lead, hub, time) 按时间轴拼起来"""
    ghi = np.concatenate([z["ghi"] for z, _ in zs], axis=2)
    t2m = np.concatenate([z["t2m"] for z, _ in zs], axis=2)
    tt = pd.DatetimeIndex(np.concatenate([t.values for _, t in zs])).tz_localize("UTC")
    return ghi, t2m, tt


def noon_daily(idx_utc, mat, name, leads=None):
    """mat: [n, time] → 当地日 × n 的正午均值 (列名 name_d{k})"""
    leads = leads if leads is not None else LEADS
    df = pd.DataFrame(mat.T, index=idx_utc)
    df.index = df.index.tz_convert(TZ)
    w = df[(df.index.hour >= NOON[0]) & (df.index.hour < NOON[1])]
    g = w.groupby(w.index.date).mean()
    g.index = pd.DatetimeIndex(g.index, name="date")
    g.columns = ["%s_d%d" % (name, L) for L in leads]
    return g


def main():
    hubs = pd.read_csv(HUBS)
    share = hubs["share"].values.reshape(1, -1, 1)

    zs = load_chunks()
    ghi, t2m, tt = stack(zs)
    print("NWP: %d chunk, %d hub, %d 小时 (%s ~ %s)"
          % (len(zs), ghi.shape[1], ghi.shape[2], tt.min(), tt.max()))

    # 容量加权全国指数
    ghi_idx = (ghi * share).sum(axis=1)          # [lead, time]
    t2m_idx = (t2m * share).sum(axis=1)
    print("预报 GHI 指数(容量加权): D1 均值 %.1f, D7 均值 %.1f W/m²"
          % (np.nanmean(ghi_idx[0]), np.nanmean(ghi_idx[6])))

    fc = pd.concat([noon_daily(tt, ghi_idx, "ghi"), noon_daily(tt, t2m_idx, "t2m")], axis=1)

    # 实测(ERA5)
    za = np.load(NWP / "fr_ghi_archive.npz")
    ta = pd.DatetimeIndex(za["time"]).tz_localize("UTC")
    g_o = (za["ghi"] * hubs["share"].values.reshape(-1, 1)).sum(axis=0)
    t_o = (za["t2m"] * hubs["share"].values.reshape(-1, 1)).sum(axis=0)
    obs = pd.concat([noon_daily(ta, g_o.reshape(1, -1), "ghi", leads=[1]).rename(columns={"ghi_d1": "ghi_obs"}),
                     noon_daily(ta, t_o.reshape(1, -1), "t2m", leads=[1]).rename(columns={"t2m_d1": "t2m_obs"})],
                    axis=1)

    base = pd.read_csv(SP / "france_noon_panel.csv", parse_dates=["date"]).set_index("date").sort_index()
    out = base.join(fc, how="left").join(obs, how="left")
    out.index.name = "date"
    out.to_csv(SP / "france_nwp_panel.csv")

    print("\n面板: %d 日 × %d 列 → %s" % (len(out), out.shape[1], SP / "france_nwp_panel.csv"))
    print("NWP 覆盖: %d 日 (%s ~ %s); ERA5 覆盖: %d 日"
          % (int(out["ghi_d1"].notna().sum()), out["ghi_d1"].first_valid_index().date(),
             out["ghi_d1"].last_valid_index().date(), int(out["ghi_obs"].notna().sum())))

    # 预报误差核验(与 ERA5 对照, 仅重叠期) —— 并分段检查 lead 的一致性
    m = out.dropna(subset=["ghi_obs"]).copy()
    m["period"] = np.where(m.index < "2025-05-01", "① 2024-07~2025-04", "② 2025-05~2026-09")
    print("\n[预报误差: 正午 GHI 指数 vs ERA5]")
    rows = []
    for L in LEADS:
        d = m.dropna(subset=["ghi_d%d" % L])
        err = d["ghi_d%d" % L] - d["ghi_obs"]
        rows.append({"lead": "D%d" % L, "n": len(d), "MAE (W/m²)": round(float(err.abs().mean()), 2),
                     "偏差": round(float(err.mean()), 2),
                     "corr": round(float(d["ghi_d%d" % L].corr(d["ghi_obs"])), 4)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n[分段一致性: 偏差 (W/m²) — 用于判别归档是否同质]")
    seg = []
    for p, sub in m.groupby("period"):
        r = {"时段": p, "n": len(sub)}
        for L in LEADS:
            d = sub.dropna(subset=["ghi_d%d" % L])
            r["D%d" % L] = round(float((d["ghi_d%d" % L] - d["ghi_obs"]).mean()), 1)
        seg.append(r)
    print(pd.DataFrame(seg).to_string(index=False))
    print("🔴 若某 lead 在两段的偏差量级不同(如 D7 在①段 +60、②段 ≈0), 说明该 lead 在早段归档不可信,")
    print("   必须限制训练窗口或弃用该 lead —— 否则训练/推理分布不一致, 会低估该 lead 的真实技能。")

    print("\n逐年(正午均):")
    y = out.groupby(out.index.year).agg(
        n=("ghi_obs", "size"),
        ghi_obs=("ghi_obs", "mean"), ghi_d1=("ghi_d1", "mean"), ghi_d7=("ghi_d7", "mean"),
        t2m_obs=("t2m_obs", "mean"), fr_negh_noon=("fr_negh_noon", "mean"),
        es_negday=("negday", "mean"))
    print(y.round(2).to_string())


if __name__ == "__main__":
    main()
