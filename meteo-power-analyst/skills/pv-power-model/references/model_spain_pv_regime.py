"""西班牙光伏链路 · 多年份/市场区间对比 (2023 vs 2024 vs 2025)
目的: 2023 西班牙尚无负电价, 2024 起负价常态化、弃电升至 3.2% —— 检验 PS-024「光伏缺口→电价」
      与 PS-028「缺口=内生弃电(负价标记)」在成熟高可再生市场的表现
链路: 与 PS-021/030 同法 (NASA POWER 辐照 → pvlib 单轴跟踪 → PVWatts), ILR 逐年标定
输出: data/spain/spain_regime_summary.csv, spain_regime_hourly_{year}.csv, spain_regime_elasticity.csv
用法: python skills/pv-power-model/references/model_spain_pv_regime.py
"""
import os

import numpy as np
import pandas as pd
import pvlib

HUB = r"c:\work\meteo\data\gem\spain_solar_hubs_multi.csv"
NASA = r"c:\work\meteo\data\nasa_power\spain_pv_hubs_multi_{year}.npz"
ECH = r"c:\work\meteo\data\energy_charts\es_{year}.csv"
PRICE = r"c:\work\meteo\data\energy_charts\es_price_{year}.csv"
OUTDIR = r"c:\work\meteo\data\spain"
os.makedirs(OUTDIR, exist_ok=True)
YEARS = [2023, 2024, 2025]
GAMMA, LOSS, ETA = -0.0037, 0.86, 0.96
ROW_S, ROW_E = [], []


def poa_of(times, ghi, dni, dhi, lat, lon):
    sp = pvlib.solarposition.get_solarposition(times, lat, lon)
    zen, azi = sp["apparent_zenith"].values, sp["azimuth"].values
    tr = pvlib.tracking.singleaxis(zen, azi, axis_tilt=0, axis_azimuth=180,
                                   max_angle=60, backtrack=True, gcr=0.35)
    t = np.where(np.isnan(tr["surface_tilt"]), 0.0, tr["surface_tilt"])
    a = np.where(np.isnan(tr["surface_azimuth"]), 180.0, tr["surface_azimuth"])
    p = pvlib.irradiance.get_total_irradiance(t, a, zen, azi, dni=dni, ghi=ghi, dhi=dhi)
    return np.nan_to_num(np.asarray(p["poa_global"], dtype=float))


def poa_clearsky(times, lat, lon):
    sp = pvlib.solarposition.get_solarposition(times, lat, lon)
    zen, azi = sp["apparent_zenith"].values, sp["azimuth"].values
    cs = pvlib.clearsky.simplified_solis(sp["apparent_elevation"].values,
                                         aod700=0.1, precipitable_water=1.5)
    g, n, d = (np.asarray(cs[k], dtype=float) for k in ("ghi", "dni", "dhi"))
    tr = pvlib.tracking.singleaxis(zen, azi, axis_tilt=0, axis_azimuth=180,
                                   max_angle=60, backtrack=True, gcr=0.35)
    t = np.where(np.isnan(tr["surface_tilt"]), 0.0, tr["surface_tilt"])
    a = np.where(np.isnan(tr["surface_azimuth"]), 180.0, tr["surface_azimuth"])
    p = pvlib.irradiance.get_total_irradiance(t, a, zen, azi, dni=n, ghi=g, dhi=d)
    return np.nan_to_num(np.asarray(p["poa_global"], dtype=float))


def ac(poa, tamb, cap, ilr):
    tcell = tamb + poa / 800.0 * 25.0
    pdc = np.clip(cap[None, :] * 1000.0 * ilr * poa / 1000.0 *
                  (1 + GAMMA * (tcell - 25)) * LOSS, 0, None)
    pac = np.minimum(pdc * ETA, cap[None, :] * 1000.0)
    pac[poa <= 0] = 0.0
    return pac


def regress(y, df, cols, fes):
    mats = [np.column_stack([np.ones(len(y))] + [df[c].values for c in cols])]
    for f in fes:
        s = pd.Series(np.asarray(f))
        cats = sorted(s.unique())
        mats.append(np.column_stack([(s == c).astype(float).values for c in cats[1:]]))
    X = np.column_stack(mats)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    cov = (r @ r / max(len(y) - X.shape[1], 1)) * np.linalg.pinv(X.T @ X)
    return ["const"] + cols, b, np.sqrt(np.diag(cov))


def run_year(year):
    d = np.load(NASA.format(year=year), allow_pickle=True)
    times = pd.to_datetime(pd.Series(d["times"]).astype(str), format="%Y%m%d%H")
    ghi, dni, dhi, t2m = (d["shortwave_radiation"], d["direct_normal_irradiance"],
                          d["diffuse_radiation"], d["temperature_2m"])
    cap, lat, lon = d["capacity_mw"].astype(float), d["lat"], d["lon"]
    ok = ~np.isnan(ghi).any(0) & ~np.isnan(dni).any(0) & ~np.isnan(t2m).any(0)
    ghi, dni, dhi, t2m = ghi[:, ok], dni[:, ok], dhi[:, ok], t2m[:, ok]
    cap, lat, lon = cap[ok], lat[ok], lon[ok]
    n_p = ok.sum()
    tot = cap.sum()
    print(f"\n{'='*72}\n[{year}] {n_p} 点, {tot/1000:.2f} GW", flush=True)

    poa = np.zeros_like(ghi, dtype=np.float32)
    pcs = np.zeros_like(ghi, dtype=np.float32)
    for j in range(n_p):
        poa[:, j] = poa_of(times, ghi[:, j], dni[:, j], dhi[:, j], float(lat[j]), float(lon[j]))
        pcs[:, j] = poa_clearsky(times, float(lat[j]), float(lon[j]))
    print(f"  POA 完成", flush=True)

    e = pd.read_csv(ECH.format(year=year), parse_dates=["time_utc"])
    e["time_utc"] = e["time_utc"].dt.tz_convert("UTC").dt.tz_localize(None)
    e = e.set_index("time_utc")
    act = e["Solar"].resample("1h").mean()
    wind = e["Wind onshore"].resample("1h").mean()
    load = e["Load"].resample("1h").mean()
    pr = pd.read_csv(PRICE.format(year=year), parse_dates=["time_utc"])
    pr["time_utc"] = pr["time_utc"].dt.tz_convert("UTC").dt.tz_localize(None)
    price = pr.set_index("time_utc")["price_eur_mwh"].resample("1h").mean()
    act_h = act.reindex(times)

    best, curve = None, []
    for ilr in np.arange(0.60, 1.36, 0.05):
        p = ac(poa, t2m, cap, ilr).sum(axis=1) / 1000.0      # kW → MW
        rr = p.sum() / np.nansum(act_h.values)
        curve.append((round(float(ilr), 2), float(rr)))
        if best is None or abs(rr - 1) < abs(best[1] - 1):
            best = (round(float(ilr), 2), float(rr))
    ilr = best[0]
    pot = pd.Series(ac(poa, t2m, cap, ilr).sum(axis=1) / 1000.0, index=times, name="pot")
    pot_cs = pd.Series(ac(pcs, t2m, cap, ilr).sum(axis=1) / 1000.0, index=times, name="pot_cs")
    df = pd.concat([pot, pot_cs, act_h.rename("act"), wind.rename("wind"),
                    load.rename("load"), price.rename("price")], axis=1).dropna()
    r = df["pot"].corr(df["act"])
    ratio = df["pot"].sum() / df["act"].sum()
    neg_h = int((df["price"] < 0).sum())
    print(f"  标定 ILR={ilr} (比值 {best[1]:.3f}) | 相关 r={r:.4f} | 能量比 {ratio:.3f} | "
          f"CF 潜力 {df['pot'].mean()/tot:.3f} vs 实际 {df['act'].mean()/tot:.3f}")
    print(f"  电价: 均 {df['price'].mean():.2f}, 最低 {df['price'].min():.2f}, "
          f"负价小时 {neg_h} ({neg_h/len(df)*100:.1f}%), "
          f"≤0 小时 {int((df['price']<=0).sum())}")

    df["gap_w"] = (df["pot"] - df["act"]).clip(lower=0)
    df["gap_cs"] = (df["pot_cs"] - df["act"]).clip(lower=0)
    day = df[df["act"] > 50].copy()
    q = day["gap_w"].quantile(0.9)
    hi, lo = day[day["gap_w"] >= q], day[day["gap_w"] <= day["gap_w"].median()]
    print(f"  高天气缺口(>P90={q:.0f}MW) n={len(hi)}: 负价频率 {(hi['price']<0).mean()*100:.1f}% | "
          f"低缺口 n={len(lo)}: {(lo['price']<0).mean()*100:.1f}%")
    print(f"  高缺口小时 负荷中位 {hi['load'].median():.0f} vs 低缺口 {lo['load'].median():.0f} MW")
    # 时段分布
    hh = day.groupby(day.index.hour).agg(g=("gap_w", "mean"), p=("price", "mean"))
    print("  逐小时(UTC) 缺口/电价: " +
          ", ".join(f"{h:02d}h {hh.loc[h,'g']:.0f}MW/${hh.loc[h,'p']:.0f}"
                    for h in (6, 9, 11, 13, 15, 18, 21) if h in hh.index))
    # 高光伏×低负荷 象限
    qs_act = day["act"].quantile(0.75)
    qs_load = day["load"].quantile(0.25)
    quad = day[(day["act"] >= qs_act) & (day["load"] <= qs_load)]
    print(f"  高光伏×低负荷象限 n={len(quad)}: 负价频率 {(quad['price']<0).mean()*100:.1f}% "
          f"(全天基准 {(day['price']<0).mean()*100:.1f}%)")

    for col, lab in (("act", "光伏出力水平"), ("gap_w", "天气缺口"),
                     ("gap_cs", "晴空缺口")):
        for tgt, tlab in (("ln", "log"), ("lv", "level")):
            y = (np.log(day["price"].clip(lower=1)).values if tgt == "ln"
                 else day["price"].values)
            pg = 1e5 if tgt == "ln" else 1e3     # log: %/GW ; level: €/MWh per GW
            n, b, s = regress(y, day, [col, "wind", "load"], [day.index.hour, day.index.month])
            i = n.index(col)
            ROW_E.append({"year": year, "target": tlab, "var": col,
                          "beta": b[i] * pg, "se": s[i] * pg, "n": len(day)})

    ROW_S.append({"year": year, "n_hub": n_p, "GW": tot / 1000, "ilr": ilr,
                  "r": r, "energy_ratio": ratio,
                  "cf_pot": df["pot"].mean() / tot, "cf_act": df["act"].mean() / tot,
                  "price_mean": df["price"].mean(), "price_min": df["price"].min(),
                  "neg_h": neg_h, "neg_pct": neg_h / len(df) * 100,
                  "gap_w_median": df["gap_w"].median(),
                  "negfreq_highgap": (hi["price"] < 0).mean() * 100,
                  "negfreq_lowgap": (lo["price"] < 0).mean() * 100,
                  "quad_negfreq": (quad["price"] < 0).mean() * 100})
    df.to_csv(os.path.join(OUTDIR, f"spain_regime_hourly_{year}.csv"))
    return curve


def main():
    curves = {}
    for y in YEARS:
        curves[y] = run_year(y)
    s = pd.DataFrame(ROW_S)
    s.to_csv(os.path.join(OUTDIR, "spain_regime_summary.csv"), index=False)
    e = pd.DataFrame(ROW_E)
    e.to_csv(os.path.join(OUTDIR, "spain_regime_elasticity.csv"), index=False)
    print("\n" + "=" * 72)
    print(s.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\n== 弹性 (log: %/GW ; level: €/MWh per GW) ==")
    print(e.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\n→ {OUTDIR}\\spain_regime_*.csv")


if __name__ == "__main__":
    main()