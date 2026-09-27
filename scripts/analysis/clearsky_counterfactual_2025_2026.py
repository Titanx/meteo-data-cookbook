"""ERCOT 光伏晴空反事实出力 (2025-01-01 ~ 2026-09-06, pvlib Solis 链路)

用途: 统一缺口气径 —— 用与 PS-022(2022-07) 完全相同的物理链路, 为 2025/2026
      弹性标定提供"晴空可发"基准, 替代 P95 数据驱动包络(其在低太阳高度角虚高)。
链路: simplified_solis 晴空 GHI/DNI/DHI -> 单轴跟踪 POA(backtrack gcr=0.35) ->
      HRRR 2m 实测气温(Faiman 简化电池温度) -> PVWatts DC/AC (ILR 1.30, 损耗 14%)
步长: 5min (与 2022 一致), 逐站计算后全网聚合, 再取小时均值
用法: python scripts/analysis/clearsky_counterfactual_2025_2026.py
输出: data/nsrdb/pv_clearsky_hourly_2025_2026.csv  (小时, MW)
"""
import numpy as np
import pandas as pd
import pvlib

PLANTS = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels_2025.csv"
T2M = r"c:\work\meteo\data\nsrdb\hrrr_t2m_2025_2026.npz"
OUT = r"c:\work\meteo\data\nsrdb\pv_clearsky_hourly_2025_2026.csv"

ETA_INV, LOSS, GAMMA, ILR = 0.96, 0.86, -0.0037, 1.30


def main():
    plants = pd.read_csv(PLANTS)
    z = np.load(T2M, allow_pickle=True)
    t2m, names = z["t2m"], list(z["names"])
    assert list(plants["name"].values) == names, "温度站序与电站清单不一致"
    nt_h = t2m.shape[0]
    print(f"{len(plants)} 座电站, {plants['capacity_mw'].sum()/1000:.2f} GW, "
          f"{nt_h} 小时 ({nt_h/24:.0f} 天)")

    # 5min 时间轴 (与温度同时段)
    t5 = pd.date_range("2025-01-01", periods=nt_h * 12, freq="5min", tz="UTC")
    assert t5[-1] == pd.Timestamp("2026-09-06 23:55", tz="UTC"), t5[-1]
    frac = np.arange(len(t5)) * 5 / 60.0

    total = np.zeros(len(t5), dtype=np.float64)
    caps = plants["capacity_mw"].values
    for j in range(len(plants)):
        lat, lon = float(plants["lat"].iloc[j]), float(plants["lon"].iloc[j])
        tamb = np.interp(frac, np.arange(nt_h), t2m[:, j]).astype(np.float32)
        sp = pvlib.solarposition.get_solarposition(t5, lat, lon)
        zen = sp["apparent_zenith"].values
        azi = sp["azimuth"].values
        elev = 90.0 - zen
        cs = pvlib.clearsky.simplified_solis(elev)
        tr = pvlib.tracking.singleaxis(zen, azi, axis_tilt=0, axis_azimuth=180,
                                       max_angle=60, backtrack=True, gcr=0.35)
        tilt = np.where(np.isnan(tr["surface_tilt"]), 0.0, tr["surface_tilt"])
        az = np.where(np.isnan(tr["surface_azimuth"]), 180.0, tr["surface_azimuth"])
        poa = pvlib.irradiance.get_total_irradiance(
            tilt, az, zen, azi, dni=np.asarray(cs["dni"]),
            ghi=np.asarray(cs["ghi"]), dhi=np.asarray(cs["dhi"]))
        poa_g = np.nan_to_num(np.asarray(poa["poa_global"], dtype=float))
        cap_kw = caps[j] * 1000.0
        tcell = tamb + poa_g / 800.0 * 25.0
        pdc = cap_kw * ILR * poa_g / 1000.0 * (1 + GAMMA * (tcell - 25)) * LOSS
        pac = np.minimum(pdc * ETA_INV, cap_kw)
        pac[poa_g <= 0] = 0.0
        total += pac
        if (j + 1) % 20 == 0:
            print(f"  {j+1}/{len(plants)} 完成", flush=True)

    s = pd.Series(total / 1000.0, index=t5)
    h = s.resample("1h").mean()
    h.index.name = "time_utc"
    h.to_csv(OUT, header=["clearsky_mw"])
    print(f"\n晴空反事实: 峰值 {h.max():.0f} MW, 中位(白天) "
          f"{h[h>500].median():.0f} MW, 年发电 {h.sum()/1000:.0f} GWh")
    print(f"已保存: {OUT}")


if __name__ == "__main__":
    main()
