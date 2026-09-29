"""ERCOT 光伏"全天候潜力"重建 (NASA POWER 辐照 + pvlib 单轴跟踪 + PVWatts)
目的: pot = 全天候(含云)物理出力潜力, 进而 gap_w = pot − 实际 = 内生缺口(弃光+模型残差)。
链路与 PS-021/030/031 同法: solarposition -> singleaxis(±60,backtrack,gcr0.35)
      -> get_total_irradiance -> Tcell -> PVWatts DC/AC -> fleet 求和(MW)。
注: NASA POWER hourly 辐照有约 4 个月延迟 (本次覆盖到 ~2026-06), 后段自动剔除。
输入: data/nasa_power/ercot_pv_plants.npz, data/ercot/ercot_hourly_panel_{2025,2026}.csv
输出: data/ercot/ercot_pv_potential_2025_2026.csv
用法: python skills/pv-power-model/references/build_ercot_pv_potential.py
"""
import os

import numpy as np
import pandas as pd
import pvlib

NPZ = r"c:\work\meteo\data\nasa_power\ercot_pv_plants.npz"
PANEL = {2025: r"c:\work\meteo\data\ercot\ercot_hourly_panel_2025.csv",
         2026: r"c:\work\meteo\data\ercot\ercot_hourly_panel_2026.csv"}
OUT = r"c:\work\meteo\data\ercot\ercot_pv_potential_2025_2026.csv"
GAMMA, LOSS, ETA = -0.0037, 0.86, 0.96


def poa_of(times, ghi, dni, dhi, lat, lon):
    sp = pvlib.solarposition.get_solarposition(times, lat, lon)
    zen = sp["apparent_zenith"].values
    azi = sp["azimuth"].values
    tr = pvlib.tracking.singleaxis(zen, azi, axis_tilt=0, axis_azimuth=180,
                                   max_angle=60, backtrack=True, gcr=0.35)
    tilt = np.where(np.isnan(tr["surface_tilt"]), 0.0, tr["surface_tilt"])
    az = np.where(np.isnan(tr["surface_azimuth"]), 180.0, tr["surface_azimuth"])
    poa = pvlib.irradiance.get_total_irradiance(tilt, az, zen, azi,
                                                dni=dni, ghi=ghi, dhi=dhi)
    return np.nan_to_num(np.asarray(poa["poa_global"], dtype=float))


def ac(poa, tamb, cap, ilr):
    tcell = tamb + poa / 800.0 * 25.0
    pdc = np.clip(cap[None, :] * 1000.0 * ilr * poa / 1000.0 *
                  (1 + GAMMA * (tcell - 25)) * LOSS, 0, None)
    pac = np.minimum(pdc * ETA, cap[None, :] * 1000.0)
    pac[poa <= 0] = 0.0
    return pac


def main():
    z = np.load(NPZ, allow_pickle=True)
    times = pd.to_datetime(pd.Series(z["times"]), format="%Y%m%d%H")
    ghi, dni, dhi = (z["shortwave_radiation"], z["direct_normal_irradiance"],
                     z["diffuse_radiation"])
    tamb = z["temperature_2m"]
    cap = z["capacity_mw"].astype(float)
    nk = len(cap)
    valid = ~np.isnan(ghi).all(axis=1)
    print(f"点位 {nk}, 容量 {cap.sum()/1000:.2f} GW, 有效时刻 {valid.sum()}/{len(times)} "
          f"({times[valid].iloc[0]} ~ {times[valid].iloc[-1]})")
    times_v = times[valid].reset_index(drop=True)
    ghi, dni, dhi, tamb = ghi[valid], dni[valid], dhi[valid], tamb[valid]

    poa = np.zeros_like(ghi)
    for j in range(nk):
        poa[:, j] = poa_of(times_v, ghi[:, j], dni[:, j], dhi[:, j],
                           float(z["lat"][j]), float(z["lon"][j]))
    print(f"POA 峰值 {np.nanmax(poa):.0f} W/m2")

    acts = {}
    for y, p in PANEL.items():
        d = pd.read_csv(p, index_col=0, parse_dates=True)
        acts[y] = d["solar"]
    act_all = pd.concat(acts.values())
    act_all = act_all[~act_all.index.duplicated(keep="first")].sort_index()

    ilr_by_year, pot_by_year = {}, {}
    for y in (2025, 2026):
        m = (times_v.dt.year == y).values
        if m.sum() < 48:
            continue
        a_energy = act_all[(act_all.index.year == y) &
                           (act_all.index.isin(times_v[m]))].sum()
        best, best_ilr = None, None
        for ilr in np.arange(0.80, 1.85, 0.05):
            pp = ac(poa[m], tamb[m], cap, ilr).sum(axis=1) / 1000.0
            ratio = pp.sum() / a_energy
            if best is None or abs(ratio - 1) < abs(best - 1):
                best, best_ilr = ratio, ilr
        ilr_by_year[y] = best_ilr
        pot_by_year[y] = pd.Series(
            ac(poa[m], tamb[m], cap, best_ilr).sum(axis=1) / 1000.0,
            index=times_v[m].values)
        print(f"  {y}: 样本 {m.sum()}h 标定 ILR {best_ilr:.2f} 年能量比 {best:.3f}")

    pot = pd.concat(pot_by_year.values()).sort_index()
    df = pd.DataFrame({"pv_pot": pot}).join(act_all.rename("pv_act"), how="inner").dropna()
    for y in sorted(set(df.index.year)):
        d = df[df.index.year == y]
        print(f"  {y}: n={len(d)} r(潜力,实际)={d['pv_pot'].corr(d['pv_act']):.4f} "
              f"能量比 {d['pv_pot'].sum()/d['pv_act'].sum():.3f} "
              f"CF 潜力 {d['pv_pot'].mean()/cap.sum():.3f} vs 实际 {d['pv_act'].mean()/cap.sum():.3f}")

    raw = df["pv_pot"] - df["pv_act"]
    off_h = raw.groupby(df.index.hour).quantile(0.05)
    df["pv_gap_w"] = (raw - off_h.reindex(df.index.hour).values).clip(lower=0)
    print(f"  偏移(逐小时q05) {off_h.min():.0f}~{off_h.max():.0f} MW; "
          f"内生缺口 中位 {df['pv_gap_w'].median():.0f} 均值 {df['pv_gap_w'].mean():.0f} "
          f"P95 {df['pv_gap_w'].quantile(.95):.0f} MW; "
          f"占潜力能量 {df['pv_gap_w'].sum()/df['pv_pot'].sum()*100:.1f}%")
    df["ilr"] = df.index.year.map(ilr_by_year)
    df.to_csv(OUT)
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
