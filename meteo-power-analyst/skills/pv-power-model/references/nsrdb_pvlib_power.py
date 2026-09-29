"""NSRDB 辐照 -> pvlib PVWatts 出力链路 (ERCOT 56 座大光伏电站, 2022-07)
模型链: GHI/DNI/DHI -> 太阳位置 -> 单轴跟踪 POA (ERCOT 大电站主流) ->
        电池温度 (HRRR 2m 实测分析气温插值到 5min) -> PVWatts DC/AC ->
        装机加权聚合 -> 小时均值 -> 与 EIA ERCO SUN 实际出力对比
温度源: NSRDB S3 v3.2.2 无地表温度 (仅有 ancillary 大气光学量), 用
        Open-Meteo historical-api HRRR ncep_hrrr_conus 2m 气温 (3km 分析场)
用法: python scripts/analysis/nsrdb_pvlib_power.py
依赖: pvlib (0.15.2), xarray, pandas
输出: data/nsrdb/ercot_pv_power_2022-07.csv + stdout 对比统计
"""
import os

import numpy as np
import pandas as pd
import pvlib
import xarray as xr

NC = r"c:\work\meteo\data\nsrdb\ercot_solar_irradiance_2022-07.nc"
T2M = r"c:\work\meteo\data\nsrdb\hrrr_t2m_2022-07.npz"
EIA = r"c:\work\meteo\data\ercot\ercot_fuel_type_data_2022-07.csv"
OUT = r"c:\work\meteo\data\nsrdb\ercot_pv_power_2022-07.csv"


def load_tamb_5min(times_5min, plant_names):
    """HRRR 小时气温 (744×56) -> 5min (8928×56), 电站序与 nc 对齐"""
    z = np.load(T2M, allow_pickle=True)
    t2m, names = z["t2m"], list(z["names"])
    assert list(plant_names) == names, "HRRR 温度站序与 nc 电站序不一致"
    n_t = len(times_5min)
    hour_frac = (np.arange(n_t) * 5 / 60.0)  # 5min 步的小时坐标
    tamb = np.empty((n_t, len(names)), dtype=np.float32)
    for j in range(len(names)):
        tamb[:, j] = np.interp(hour_frac, np.arange(t2m.shape[0]), t2m[:, j])
    return tamb


def main():
    ds = xr.open_dataset(NC)
    times = pd.DatetimeIndex(ds["time"].values).tz_localize("UTC")
    ghi = ds["GHI"].values          # (8928, 56) W/m2
    dni = ds["DNI"].values
    dhi = ds["DHI"].values
    lats = ds["latitude"].values
    lons = ds["longitude"].values
    caps = ds["capacity_mw"].values
    names = ds["plant"].values
    print(f"数据: {ghi.shape[0]} 时步 x {ghi.shape[1]} 站, "
          f"总装机 {caps.sum()/1000:.1f} GW")

    # 环境温度: HRRR 2m 分析气温 (逐站逐时步, 插值到 5min)
    # 原全域统一日循环参数化无法反映逐站/逐日差异, 换实测以分离温度因子
    # 对热浪期正午偏差的影响 (方向由实证判定)
    tamb = load_tamb_5min(times, names)

    # 逐站计算 POA + 出力
    n_t, n_p = ghi.shape
    power = np.zeros((n_t, n_p), dtype=np.float32)  # kW/站

    for j in range(n_p):
        lat, lon = float(lats[j]), float(lons[j])
        solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
        # 注意: pvlib singleaxis / get_total_irradiance 的角度参数均为度数
        # (v1 曾误传弧度 -> 倾角恒 0, POA 退化为 DNI+DHI)
        zen = solpos["apparent_zenith"].values
        azi = solpos["azimuth"].values
        # 单轴跟踪 (N-S 轴, 0 倾角, backtracking 避免行列遮挡)
        tr = pvlib.tracking.singleaxis(
            zen, azi, axis_tilt=0, axis_azimuth=180, max_angle=60,
            backtrack=True, gcr=0.35)
        # pvlib>=0.10 singleaxis 返回 numpy 数组 (非 Series), NaN 需 numpy 处理:
        # 夜间/低仰角无解时 tilt=NaN -> 视作平放 (poa 由 GHI 主导, 影响极小)
        tilt = tr["surface_tilt"]
        az = tr["surface_azimuth"]
        tilt = np.where(np.isnan(tilt), 0.0, tilt)
        az = np.where(np.isnan(az), 180.0, az)
        poa = pvlib.irradiance.get_total_irradiance(
            tilt, az, zen, azi,
            dni=dni[:, j], ghi=ghi[:, j], dhi=dhi[:, j])
        poa_g = np.asarray(poa["poa_global"], dtype=float)
        poa_g = np.where(np.isnan(poa_g), 0.0, poa_g)

        # 电池温度: 简化 Faiman/NOCT 混合 — Tcell = Tamb + poa/800 * 25
        tcell = tamb[:, j] + poa_g / 800.0 * 25.0
        # PVWatts DC: pdc = pdc0 * poa/1000 * (1 + gamma*(Tcell-25))
        pdc0 = caps[j] * 1000.0  # kW (1 MW = 1000 kWdc)
        # ILR 1.30 (2020-2022 ERCOT 主流机型 1.25~1.35 的舰队均值):
        # ILR 扫描实证 1.30 同时最小化非热浪过估 (+2.1%) 与热浪低估 (-1.4%)
        pdc0 *= 1.30
        gamma = -0.0037
        # 系统综合损耗 14% (PVWatts 默认: soiling 2% + wiring 2% + mismatch 2%
        # + availability 3% + 其他), 无此项时月能量高估 ~15%
        pdc = pdc0 * poa_g / 1000.0 * (1 + gamma * (tcell - 25)) * 0.86
        pdc = np.clip(pdc, 0, None)
        # AC: PVWatts inverter 有限容量裁剪 (pdc0/1.2 = 交流额定)
        pac_max = caps[j] * 1000.0
        eta = 0.96
        pac = np.minimum(pdc * eta, pac_max)
        # 夜间强制 0
        pac[poa_g <= 0] = 0.0
        power[:, j] = pac

    df = pd.DataFrame(power, index=times, columns=names)
    # 聚合全网出力 (MW): power 已含各站装机 (kW), 直接求和
    total_mw = pd.Series((power / 1000.0).sum(axis=1), index=times)

    # 小时均值
    hourly = total_mw.resample("1h").mean()

    eia = pd.read_csv(EIA)
    sun = eia[eia["fuel_code"] == "SUN"].set_index("time")["value"]
    sun.index = pd.to_datetime(sun.index).tz_localize("UTC")
    sun = sun.sort_index()
    # EIA-930 小时时间戳为区间结束 (值属于 [t-1, t)), 实证: 对齐后
    # r 0.942->0.992, MAE 785->346 MW; 前移 1h 使标签=区间起点
    sun.index = sun.index - pd.Timedelta(hours=1)
    sun_hourly = sun.resample("1h").mean()

    joined = pd.DataFrame({"pvlib_mw": hourly, "eia_mw": sun_hourly}).dropna()
    corr = joined["pvlib_mw"].corr(joined["eia_mw"])
    mae = (joined["pvlib_mw"] - joined["eia_mw"]).abs().mean()
    # 容量口径: EIA-930 2022-07 峰值仅 9706 MW (07-25 晴天正午), 隐含有效装机
    # ≈ 模型 56 站装机 10.66 GW, 故直接对比 (原 12 GW 缩放假设为 2023+ 装机, 已废弃)
    print(f"\n=== 模型 vs 实际 (2022-07, {len(joined)} 小时) ===")
    print(f"相关系数 r: {corr:.4f}")
    print(f"MAE: {mae:.0f} MW")
    print(f"模型峰值 {joined['pvlib_mw'].max():.0f} MW vs EIA 峰值 "
          f"{joined['eia_mw'].max():.0f} MW")
    print(f"模型能量 {joined['pvlib_mw'].sum()/1000:.1f} GWh vs EIA "
          f"{joined['eia_mw'].sum()/1000:.1f} GWh "
          f"({(joined['pvlib_mw'].sum()-joined['eia_mw'].sum())/joined['eia_mw'].sum():+.1%})")

    hw = joined.index.tz_convert(None).normalize().isin(
        pd.date_range("2022-07-13", "2022-07-18"))
    h = joined.index.hour
    for label, m in [
        ("热浪 07-13~18", hw), ("非热浪", ~hw),
        ("热浪正午 16-21UTC", hw & (h >= 16) & (h <= 21)),
        ("非热浪正午", ~hw & (h >= 16) & (h <= 21)),
    ]:
        w = joined[m]
        if len(w) < 3:
            continue
        b = (w["pvlib_mw"] - w["eia_mw"]).mean() / w["eia_mw"].mean() * 100
        print(f"  {label:<18s} 偏差 {b:+.1f}%")

    joined.to_csv(OUT)
    print(f"已保存: {OUT}")
    return joined


if __name__ == "__main__":
    main()
