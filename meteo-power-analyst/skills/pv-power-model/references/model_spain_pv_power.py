"""西班牙光伏最小链路: 辐照 → pvlib → fleet 潜力 → 与 Energy-Charts 实际对比
                                        → ILR 标定 → 缺口 → 日前电价弹性 (对标 PS-021/024/028)

链路 (与 PS-021 同法, 仅换数据源与参数标定):
  NASA POWER 逐小时 GHI/DNI/DHI + 2m 气温 (免注册) → pvlib 单轴跟踪 POA
  → NOCT 电池温度 → PVWatts (γ=-0.0037, 系统损耗 14%, 逆变 0.96, ILR 标定)
  → 120 个采样点容量加权 → fleet 潜力 (MW)
实际/价格/负荷: Energy-Charts (ENTSO-E/OMIE 口径, 免注册)
缺口: ①天气辐照潜力 − 实际 (≈损失+弃电/清单偏差)  ②pvlib 晴空潜力 − 实际 (≈云致缺口)
输出: data/spain/spain_pv_hourly_2023.csv, spain_pv_gap_2023.csv, spain_elasticity_2023.csv
用法: python skills/pv-power-model/references/model_spain_pv_power.py
"""
import json
import os

import numpy as np
import pandas as pd
import pvlib

ERA = r"c:\work\meteo\data\nasa_power\spain_pv_hubs_2023.npz"
ECH = r"c:\work\meteo\data\energy_charts\es_2023.csv"
PRICE = r"c:\work\meteo\data\energy_charts\es_price_2023.csv"
PVGIS = r"c:\work\meteo\data\pvgis\spain_sarah3_top12_2023.json"
OUTDIR = r"c:\work\meteo\data\spain"
os.makedirs(OUTDIR, exist_ok=True)
OUT_H = os.path.join(OUTDIR, "spain_pv_hourly_2023.csv")
OUT_G = os.path.join(OUTDIR, "spain_pv_gap_2023.csv")
OUT_EL = os.path.join(OUTDIR, "spain_elasticity_2023.csv")

GAMMA = -0.0037
LOSS = 0.86
ETA = 0.96
ROWS = []


def poa_series(times, ghi, dni, dhi, lat, lon):
    """单点: 单轴跟踪 POA (度参数, 与 PS-021 同法)"""
    sp = pvlib.solarposition.get_solarposition(times, lat, lon)
    zen, azi = sp["apparent_zenith"].values, sp["azimuth"].values
    tr = pvlib.tracking.singleaxis(zen, azi, axis_tilt=0, axis_azimuth=180,
                                   max_angle=60, backtrack=True, gcr=0.35)
    tilt = np.where(np.isnan(tr["surface_tilt"]), 0.0, tr["surface_tilt"])
    az = np.where(np.isnan(tr["surface_azimuth"]), 180.0, tr["surface_azimuth"])
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, az, zen, azi, dni=dni, ghi=ghi, dhi=dhi)
    return np.nan_to_num(np.asarray(poa["poa_global"], dtype=float))


def clearsky_poa(times, lat, lon):
    sp = pvlib.solarposition.get_solarposition(times, lat, lon)
    zen, azi = sp["apparent_zenith"].values, sp["azimuth"].values
    elev = sp["apparent_elevation"].values
    cs = pvlib.clearsky.simplified_solis(elev, aod700=0.1, precipitable_water=1.5)
    g, n, d = (np.asarray(cs[k], dtype=float) for k in ("ghi", "dni", "dhi"))
    tr = pvlib.tracking.singleaxis(zen, azi, axis_tilt=0, axis_azimuth=180,
                                   max_angle=60, backtrack=True, gcr=0.35)
    tilt = np.where(np.isnan(tr["surface_tilt"]), 0.0, tr["surface_tilt"])
    az = np.where(np.isnan(tr["surface_azimuth"]), 180.0, tr["surface_azimuth"])
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, az, zen, azi, dni=n, ghi=g, dhi=d)
    return np.nan_to_num(np.asarray(poa["poa_global"], dtype=float))


def ac_output(poa, tamb, cap_mw, ilr):
    """POA(W/m2) + 气温 → 交流出力 kW (向量化, 每列一个站点)"""
    tcell = tamb + poa / 800.0 * 25.0
    pdc0 = cap_mw[None, :] * 1000.0 * ilr
    pdc = np.clip(pdc0 * poa / 1000.0 * (1 + GAMMA * (tcell - 25)) * LOSS, 0, None)
    pac = np.minimum(pdc * ETA, cap_mw[None, :] * 1000.0)
    pac[poa <= 0] = 0.0
    return pac


def regress(y, num_df, num_cols, fe_specs):
    mats = [np.column_stack([np.ones(len(y))] + [num_df[c].values for c in num_cols])]
    for values in fe_specs:
        s = pd.Series(np.asarray(values))
        cats = sorted(s.unique())
        m = [(s == c).astype(float).values for c in cats[1:]]
        if m:
            mats.append(np.column_stack(m))
    X = np.column_stack(mats)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
    return ["const"] + num_cols, beta, np.sqrt(np.diag(cov))


def main():
    d = np.load(ERA, allow_pickle=True)
    times = pd.to_datetime(pd.Series(d["times"]).astype(str), format="%Y%m%d%H")
    ghi = d["shortwave_radiation"]
    dni = d["direct_normal_irradiance"]
    dhi = d["diffuse_radiation"]
    t2m = d["temperature_2m"]
    cap, lat, lon = d["capacity_mw"].astype(float), d["lat"], d["lon"]
    n_t, n_p = ghi.shape
    tot_gw = cap.sum() / 1000
    print(f"NASA POWER: {n_p} 点 × {n_t} h, 总容量 {tot_gw:.2f} GW")

    ok = (~np.isnan(ghi).any(0) & ~np.isnan(dni).any(0) & ~np.isnan(t2m).any(0))
    if (~ok).sum():
        print(f"  剔除含 NaN 点 {(~ok).sum()} ({cap[~ok].sum()/1000:.2f} GW)")
    ghi, dni, dhi, t2m = ghi[:, ok], dni[:, ok], dhi[:, ok], t2m[:, ok]
    cap, lat, lon = cap[ok], lat[ok], lon[ok]
    n_p = ok.sum()

    # --- 一次算好 POA (与 ILR 无关) ---
    poa = np.zeros((n_t, n_p), dtype=np.float32)
    poa_cs = np.zeros((n_t, n_p), dtype=np.float32)
    for j in range(n_p):
        poa[:, j] = poa_series(times, ghi[:, j], dni[:, j], dhi[:, j],
                               float(lat[j]), float(lon[j]))
        poa_cs[:, j] = clearsky_poa(times, float(lat[j]), float(lon[j]))
        if (j + 1) % 40 == 0:
            print(f"  POA {j+1}/{n_p}", flush=True)

    # --- 实际 / 价格 / 负荷 (Energy-Charts) ---
    e = pd.read_csv(ECH, parse_dates=["time_utc"])
    e["time_utc"] = e["time_utc"].dt.tz_convert("UTC").dt.tz_localize(None)
    e = e.set_index("time_utc")
    act = e["Solar"].resample("1h").mean().rename("solar_actual_mw")
    wind = e["Wind onshore"].resample("1h").mean().rename("wind_mw")
    load = e["Load"].resample("1h").mean().rename("load_mw")
    pr = pd.read_csv(PRICE, parse_dates=["time_utc"])
    pr["time_utc"] = pr["time_utc"].dt.tz_convert("UTC").dt.tz_localize(None)
    pr = pr.set_index("time_utc")
    price = pr["price_eur_mwh"].resample("1h").mean().rename("price")
    act_h = act.reindex(times)

    # --- ILR 标定 (使年能量最接近实际) ---
    print("\n== ILR 标定 (西班牙) ==")
    best = None
    for ilr in (0.80, 0.85, 0.90, 1.00, 1.10, 1.20, 1.30):
        p = pd.Series(ac_output(poa, t2m, cap, ilr).sum(axis=1) / 1000.0, index=times)
        ratio = p.sum() / act_h.sum()
        print(f"  ILR {ilr:.2f}: 年潜力/实际 = {ratio:.3f}")
        if best is None or abs(ratio - 1) < abs(best[1] - 1):
            best = (ilr, ratio)
    ilr = best[0]
    print(f"  → 标定 ILR = {ilr:.2f} (比值 {best[1]:.3f}); ERCOT 曾用 1.30")

    pot = pd.Series(ac_output(poa, t2m, cap, ilr).sum(axis=1) / 1000.0,
                    index=times, name="pv_pot_mw")
    pot_cs = pd.Series(ac_output(poa_cs, t2m, cap, ilr).sum(axis=1) / 1000.0,
                       index=times, name="pv_clearsky_mw")
    df = pd.concat([pot, pot_cs, act_h, wind, load, price], axis=1).dropna()
    print(f"\n对齐 {len(df)} h; 潜力均值 {df['pv_pot_mw'].mean():.0f} MW "
          f"(CF {df['pv_pot_mw'].mean()/cap.sum():.3f}) | "
          f"实际均值 {df['solar_actual_mw'].mean():.0f} MW "
          f"(CF {df['solar_actual_mw'].mean()/cap.sum():.3f})")
    print(f"能量比 潜力/实际 {df['pv_pot_mw'].sum()/df['solar_actual_mw'].sum():.3f} | "
          f"晴空/实际 {df['pv_clearsky_mw'].sum()/df['solar_actual_mw'].sum():.3f}")

    print("\n== 时滞诊断 ==")
    for lag in (-1, 0, 1):
        print(f"  lag {lag:+d}h: r = "
              f"{df['pv_pot_mw'].shift(lag).corr(df['solar_actual_mw']):.4f}")
    print("\n== 逐月能量 (GWh) ==")
    m = df.resample("MS").agg(pot=("pv_pot_mw", "sum"), cs=("pv_clearsky_mw", "sum"),
                              act=("solar_actual_mw", "sum"), price=("price", "mean"))
    for c in ("pot", "cs", "act"):
        m[c] /= 1e3
    for idx, r in m.iterrows():
        print(f"  {idx.strftime('%Y-%m')}: 潜力 {r['pot']:6.0f} | 晴空 {r['cs']:6.0f} | "
              f"实际 {r['act']:6.0f} | 比 {r['pot']/r['act']:.3f} | 均价 {r['price']:6.2f}")

    df["gap_weather"] = (df["pv_pot_mw"] - df["solar_actual_mw"]).clip(lower=0)
    df["gap_cs"] = (df["pv_clearsky_mw"] - df["solar_actual_mw"]).clip(lower=0)

    print("\n== 电价弹性 (白天, %/GW, ln(price)~X+风电+负荷+小时/月FE) ==")
    PG = 100000.0
    day = df[df["solar_actual_mw"] > 50].copy()
    for col, lab in (("gap_cs", "晴空缺口(云)"), ("gap_weather", "天气缺口(损失/弃电)"),
                     ("solar_actual_mw", "实际光伏水平")):
        lnp = np.log(day["price"].clip(lower=0.1)).values
        n, b, s = regress(lnp, day, [col, "wind_mw", "load_mw"],
                          [day.index.hour, day.index.month])
        est, se = b[n.index(col)] * PG, s[n.index(col)] * PG
        ROWS.append({"model": col, "estimate_pct_per_gw": est,
                     "se_pct_per_gw": se, "n": len(day)})
        print(f"  {lab:16s} {est:+9.3f} %/GW (SE {se:.3f})")
    print(f"  原始相关: gap_cs×price {day['gap_cs'].corr(day['price']):+.3f} | "
          f"actual×price {day['solar_actual_mw'].corr(day['price']):+.3f} | "
          f"gap_weather×price {day['gap_weather'].corr(day['price']):+.3f}")

    if os.path.exists(PVGIS):
        with open(PVGIS, encoding="utf-8") as f:
            pv = json.load(f)
        print("\n== PVGIS-SARAH3 交叉校验 (固定35° POA 年总量 kWh/m2) ==")
        for name, rec in list(pv.items())[:6]:
            g = np.array([x["G(i)"] for x in rec["hourly"]])
            sp = pvlib.solarposition.get_solarposition(times, rec["lat"], rec["lon"])
            j = int(np.argmin((lat - rec["lat"]) ** 2 +
                              (np.cos(np.radians(rec["lat"])) * (lon - rec["lon"])) ** 2))
            po = pvlib.irradiance.get_total_irradiance(
                35.0, 180.0, sp["apparent_zenith"].values, sp["azimuth"].values,
                dni=dni[:, j], ghi=ghi[:, j], dhi=dhi[:, j])
            pg = np.nan_to_num(np.asarray(po["poa_global"], dtype=float))
            print(f"  {name[:26]:26s} SARAH3 {g.sum()/1e3:7.1f} | NASA {pg.sum()/1e3:7.1f}"
                  f" | 比值 {pg.sum()/g.sum():.3f}")

    df.to_csv(OUT_H)
    df.resample("D").agg(gap_cs_gwh=("gap_cs", lambda x: x.sum()/1e3),
                         gap_weather_gwh=("gap_weather", lambda x: x.sum()/1e3),
                         pot_gwh=("pv_pot_mw", lambda x: x.sum()/1e3),
                         act_gwh=("solar_actual_mw", lambda x: x.sum()/1e3),
                         load_peak=("load_mw", "max"),
                         price_mean=("price", "mean")).to_csv(OUT_G)
    pd.DataFrame(ROWS).to_csv(OUT_EL, index=False)
    print(f"\n→ {OUT_H}\n→ {OUT_G}\n→ {OUT_EL}")


if __name__ == "__main__":
    main()