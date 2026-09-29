"""ILR 扫描 + 热浪偏差归因 v2 (tz 修复 + 容量假设诊断)
背景: USCRN 交叉验证已排除 "NSRDB 热浪期反演偏低" (漂移仅 -1.5%);
     容量归一化暴露原 "月能量 -2.1%" 是 10.66 GW vs 12 GW 的口径差,
     EIA 分母 12.0 GW 需要用 2022-07 实际装机与 EIA 小时分布重新锚定
方法: pdc 基准 (ILR=1) 只算一次, pac(ILR)=min(pdc*ILR*eta, caps) 解析扫描;
     scale = EIA装机/模型装机 作为场景参数
"""
import numpy as np
import pandas as pd
import pvlib
import xarray as xr

NC = r"c:\work\meteo\data\nsrdb\ercot_solar_irradiance_2022-07.nc"
T2M = r"c:\work\meteo\data\nsrdb\hrrr_t2m_2022-07.npz"
EIA = r"c:\work\meteo\data\ercot\ercot_fuel_type_data_2022-07.csv"
HEATWAVE = pd.date_range("2022-07-13", "2022-07-18")  # naive
ETA_INV = 0.96
LOSS = 0.86
GAMMA = -0.0037


def main():
    ds = xr.open_dataset(NC)
    times = pd.DatetimeIndex(ds["time"].values).tz_localize("UTC")
    t_naive = times.tz_convert(None)
    ghi, dni, dhi = ds["GHI"].values, ds["DNI"].values, ds["DHI"].values
    lats, lons = ds["latitude"].values, ds["longitude"].values
    caps, names = ds["capacity_mw"].values, ds["plant"].values

    z = np.load(T2M, allow_pickle=True)
    t2m = z["t2m"]
    assert list(names) == list(z["names"]), "站序不一致"
    n_t = len(times)
    hour_frac = np.arange(n_t) * 5 / 60.0
    tamb = np.empty((n_t, len(names)), dtype=np.float32)
    for j in range(len(names)):
        tamb[:, j] = np.interp(hour_frac, np.arange(t2m.shape[0]), t2m[:, j])

    n_p = len(names)
    pdc_base = np.zeros((n_t, n_p))
    plant_poa = np.zeros((n_t, n_p))
    for j in range(n_p):
        solpos = pvlib.solarposition.get_solarposition(times, lats[j], lons[j])
        zen = solpos["apparent_zenith"].values
        azi = solpos["azimuth"].values
        tr = pvlib.tracking.singleaxis(zen, azi, axis_tilt=0, axis_azimuth=180,
                                      max_angle=60, backtrack=True, gcr=0.35)
        tilt = np.where(np.isnan(tr["surface_tilt"]), 0.0, tr["surface_tilt"])
        az = np.where(np.isnan(tr["surface_azimuth"]), 180.0, tr["surface_azimuth"])
        poa = pvlib.irradiance.get_total_irradiance(
            tilt, az, zen, azi, dni=dni[:, j], ghi=ghi[:, j], dhi=dhi[:, j])
        poa_g = np.nan_to_num(np.asarray(poa["poa_global"], dtype=float))
        tcell = tamb[:, j] + poa_g / 800.0 * 25.0
        pdc_base[:, j] = (caps[j] * 1000.0 * poa_g / 1000.0
                          * (1 + GAMMA * (tcell - 25)) * LOSS)
        plant_poa[:, j] = poa_g

    eia = pd.read_csv(EIA)
    sun = eia[eia["fuel_code"] == "SUN"].set_index("time")["value"]
    sun.index = pd.to_datetime(sun.index).tz_localize("UTC")
    sun.index = sun.index - pd.Timedelta(hours=1)
    eia_hourly = sun.resample("1h").mean()

    # ---- 诊断 1: EIA 小时分布 (锚定真实装机) ----
    print("=== EIA-930 ERCOT SUN 2022-07 分布 ===")
    print(f"max {eia_hourly.max():.0f} MW @ {eia_hourly.idxmax()}")
    print(f"P99.9 {eia_hourly.quantile(0.999):.0f}, P99 {eia_hourly.quantile(0.99):.0f}, "
          f"P95 {eia_hourly.quantile(0.95):.0f} MW")
    top10 = eia_hourly.nlargest(10)
    for t, v in top10.items():
        print(f"  {t}  {v:.0f} MW")
    print(f"模型装机 {caps.sum():.0f} MW (56 座 >=100MW)")

    # ---- 模型各 ILR 小时曲线 ----
    hourly_models = {}
    noon_mask = (t_naive.hour >= 16) & (t_naive.hour <= 21)
    for ilr in [1.20, 1.25, 1.30, 1.35]:
        pac = np.minimum(pdc_base * ilr * ETA_INV, caps * 1000.0)
        pac[plant_poa <= 0] = 0.0
        total = pd.Series(pac.sum(axis=1) / 1000.0, index=t_naive)
        hourly_models[ilr] = total.resample("1h").mean()
        util = pac[noon_mask].sum(axis=1).mean() / caps.sum() / 1000 * 1000
        print(f"ILR {ilr:.2f}: 模型正午均值出力 {pac[noon_mask].sum(axis=1).mean()/1000:.0f} MW "
              f"({pac[noon_mask].sum(axis=1).mean()/caps.sum()*100:.1f}% 装机)")

    eia_naive = eia_hourly.copy()
    eia_naive.index = eia_naive.index.tz_convert(None)

    def get(idx, name):
        hw = idx.normalize().isin(HEATWAVE)
        h = idx.hour
        if name == "全月":
            return idx
        if name == "热浪":
            return idx[hw]
        if name == "非热浪":
            return idx[~hw]
        if name == "热浪正午":
            return idx[hw & (h >= 16) & (h <= 21)]
        if name == "非热浪正午":
            return idx[~hw & (h >= 16) & (h <= 21)]
        raise ValueError(name)

    # ---- 诊断 2: 辐照分量热浪日漂移 ----
    hw5 = t_naive.normalize().isin(HEATWAVE)
    print("\n=== 辐照分量 (56 站均值, 16-21 UTC) 热浪 vs 非热浪 ===")
    for var, arr in [("GHI", ghi), ("DNI", dni), ("DHI", dhi), ("POA", plant_poa)]:
        v_n, v_h = arr[noon_mask & ~hw5].mean(), arr[noon_mask & hw5].mean()
        print(f"{var}: 非热浪 {v_n:.1f} vs 热浪 {v_h:.1f} W/m2 ({v_h/v_n-1:+.1%})")

    # ---- 主表: scale 场景 × ILR × 窗口 ----
    print("\n=== 归一化指标: bias% (能量差%) | MAE MW ===")
    scales = [("scale=1.0", 1.0), ("scale=12GW", 12000.0 / caps.sum())]
    for sname, scale in scales:
        print(f"\n--- {sname} ---")
        print(f"{'窗口':<10s}{'ILR':>5s} {'r':>7s} {'MAE':>6s} {'bias%':>7s} {'E差%':>7s}")
        for label in ["全月", "热浪", "非热浪", "热浪正午", "非热浪正午"]:
            w = get(eia_naive.index, label)
            ev = eia_naive.reindex(w)
            for ilr in hourly_models:
                mv = hourly_models[ilr].reindex(w) * scale
                j = pd.DataFrame({"m": mv, "e": ev}).dropna()
                if len(j) < 3:
                    continue
                r = j["m"].corr(j["e"])
                mae = (j["m"] - j["e"]).abs().mean()
                biasp = (j["m"] - j["e"]).mean() / j["e"].mean() * 100
                ediff = (j["m"].sum() - j["e"].sum()) / j["e"].sum() * 100
                print(f"{label:<10s}{ilr:>5.2f} {r:>7.4f} {mae:>6.0f} "
                      f"{biasp:>+6.1f}% {ediff:>+6.1f}%")

    # ---- 逐日: 正午 POA vs EIA (定位异常日) ----
    daily_poa = pd.Series((plant_poa * caps[None, :]).sum(axis=1) / caps.sum(),
                          index=t_naive)
    daily_noon = daily_poa[noon_mask].resample("1D").mean()
    daily_eia = eia_naive.resample("1D").mean()
    hw_days = daily_noon.index.isin(HEATWAVE)
    print("\n=== 逐日正午 POA vs EIA 日均 (07-10 ~ 07-22) ===")
    for d in pd.date_range("2022-07-10", "2022-07-22"):
        tag = "热浪" if d in HEATWAVE else ""
        print(f"  {d.date()} | POA {daily_noon.get(d, np.nan):6.1f} | "
              f"EIA {daily_eia.get(d, np.nan):6.0f} MW | {tag}")


if __name__ == "__main__":
    main()
