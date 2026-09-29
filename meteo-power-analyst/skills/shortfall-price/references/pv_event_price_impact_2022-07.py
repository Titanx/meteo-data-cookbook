"""2022-07 光伏缺口事件的电价冲击推演 (晴空反事实 + 2025 弹性 + 2022 价格锚)
方法:
  1) pvlib simplified_solis 晴空分量 -> 同一物理链路 (单轴跟踪/HRRR温度/
     ILR 1.30/损耗 14%) -> 56 站晴空反事实出力 (小时)
  2) 缺口 = 晴空反事实 - EIA 实际 (校准: 最晴 5% 小时缺口归零的常数偏移)
  3) 事件 = 15-23 UTC 缺口 >=1.5 GW 的小时, 连续小时合并
  4) 冲击: %上浮 = exp(β*缺口GW)-1, β 取 2025 缺口弹性 +5.1%/GW
     (高需求区 +5.8%/GW 做情景), $ 上浮按 2022-07 ERCOT North 月均 $182/MWh
     (EIA TODAY IN ENERGY #55139) 情景化
输出: stdout + data/nsrdb/pv_event_price_impact_2022-07.csv
"""
import numpy as np
import pandas as pd
import pvlib
import xarray as xr

NC = r"c:\work\meteo\data\nsrdb\ercot_solar_irradiance_2022-07.nc"
T2M = r"c:\work\meteo\data\nsrdb\hrrr_t2m_2022-07.npz"
EIA = r"c:\work\meteo\data\ercot\ercot_fuel_type_data_2022-07.csv"
OUT = r"c:\work\meteo\data\nsrdb\pv_event_price_impact_2022-07.csv"
BETA = 0.0508          # 2025 缺口弹性 ln/GW
BETA_HOT = 0.0584      # 2025 高需求区 (>=72GW)
BASE_PRICE = 182.0     # 2022-07 ERCOT North 月均 $/MWh (EIA)
HEATWAVE = pd.date_range("2022-07-13", "2022-07-18")
ETA_INV, LOSS, GAMMA = 0.96, 0.86, -0.0037


def main():
    ds = xr.open_dataset(NC)
    times = pd.DatetimeIndex(ds["time"].values).tz_localize("UTC")
    t_naive = times.tz_convert(None)
    lats, lons = ds["latitude"].values, ds["longitude"].values
    caps, names = ds["capacity_mw"].values, ds["plant"].values

    z = np.load(T2M, allow_pickle=True)
    t2m = z["t2m"]
    n_t = len(times)
    hour_frac = np.arange(n_t) * 5 / 60.0
    tamb = np.empty((n_t, len(names)), dtype=np.float32)
    for j in range(len(names)):
        tamb[:, j] = np.interp(hour_frac, np.arange(t2m.shape[0]), t2m[:, j])

    power_cs = np.zeros((n_t, len(names)))
    for j in range(len(names)):
        solpos = pvlib.solarposition.get_solarposition(times, lats[j], lons[j])
        zen = solpos["apparent_zenith"].values
        azi = solpos["azimuth"].values
        elev = 90.0 - zen
        cs = pvlib.clearsky.simplified_solis(elev)
        tr = pvlib.tracking.singleaxis(zen, azi, axis_tilt=0, axis_azimuth=180,
                                      max_angle=60, backtrack=True, gcr=0.35)
        tilt = np.where(np.isnan(tr["surface_tilt"]), 0.0, tr["surface_tilt"])
        az = np.where(np.isnan(tr["surface_azimuth"]), 180.0, tr["surface_azimuth"])
        poa = pvlib.irradiance.get_total_irradiance(
            tilt, az, zen, azi,
            dni=np.asarray(cs["dni"]), ghi=np.asarray(cs["ghi"]),
            dhi=np.asarray(cs["dhi"]))
        poa_g = np.nan_to_num(np.asarray(poa["poa_global"], dtype=float))
        tcell = tamb[:, j] + poa_g / 800.0 * 25.0
        pdc = (caps[j] * 1000.0 * 1.30 * poa_g / 1000.0
               * (1 + GAMMA * (tcell - 25)) * LOSS)
        pac = np.minimum(pdc * ETA_INV, caps[j] * 1000.0)
        pac[poa_g <= 0] = 0.0
        power_cs[:, j] = pac

    cs_total = pd.Series(power_cs.sum(axis=1) / 1000.0, index=t_naive)
    cs_hourly = cs_total.resample("1h").mean()

    eia = pd.read_csv(EIA)
    sun = eia[eia["fuel_code"] == "SUN"].set_index("time")["value"]
    sun.index = pd.to_datetime(sun.index).tz_localize("UTC").tz_localize(None) \
        - pd.Timedelta(hours=1)
    eia_hourly = sun.resample("1h").mean()

    # 需求代理 = 全燃料出力之和 (2022-07 无 region 数据)
    total = eia.pivot_table(index="time", columns="fuel_code", values="value",
                            aggfunc="mean").sum(axis=1)
    total.index = pd.to_datetime(total.index).tz_localize("UTC").tz_localize(None) \
        - pd.Timedelta(hours=1)
    demand = total.resample("1h").mean()

    df = pd.DataFrame({"cs": cs_hourly, "eia": eia_hourly,
                       "demand": demand}).dropna(subset=["cs", "eia"])
    day = df[df["eia"] > 500]
    raw_short = day["cs"] - day["eia"]
    off = raw_short.quantile(0.05)
    # 逐小时偏移 (与 2025 弹性标定的逐小时晴空包络口径一致);
    # 单一全局偏移会把傍晚 (低仰角跟踪 POA 偏高) 的系统性偏差计入缺口
    off_h = raw_short.groupby(raw_short.index.hour).quantile(0.05)
    hh = df.index.hour
    df["shortfall"] = (df["cs"] - df["eia"]
                       - off_h.reindex(hh).values).clip(lower=0)
    df.loc[df["eia"] <= 200, "shortfall"] = np.nan

    print(f"晴空反事实峰值 {df['cs'].max():.0f} MW vs EIA 峰值 {df['eia'].max():.0f} MW")
    print(f"缺口校准偏移 (最晴5%小时): 全局 {off:.0f} MW, 逐小时 "
          f"{off_h.min():.0f}~{off_h.max():.0f} MW")
    print("逐小时偏移 (UTC): " + ", ".join(
        f"{h:02d}:{v:.0f}" for h, v in off_h.items()))
    chk = df.loc["2022-07-25 15:00":"2022-07-25 21:00"]
    print(f"晴日核查 07-25 正午缺口中位: {chk['shortfall'].median():.0f} MW")

    ev_h = df[(df["shortfall"] >= 1500) & (df.index.hour >= 15)
              & (df.index.hour <= 23)]
    print(f"\n事件小时 (缺口>=1.5GW, 15-23UTC): {len(ev_h)} 个")

    def uplift(sw_gw, beta):
        return (np.exp(beta * sw_gw) - 1) * 100.0

    rows = []
    for t, r in ev_h.iterrows():
        sw_gw = r["shortfall"] / 1000.0
        rows.append({
            "time_utc": t, "eia_mw": r["eia"], "clearsky_mw": r["cs"],
            "shortfall_mw": r["shortfall"], "demand_mw": r["demand"],
            "uplift_pct_base": uplift(sw_gw, BETA),
            "uplift_pct_hot": uplift(sw_gw, BETA_HOT),
            "price_uplift_usd_at_182": BASE_PRICE * uplift(sw_gw, BETA) / 100,
        })
    ev = pd.DataFrame(rows).set_index("time_utc")
    hw = ev.index.normalize().isin(HEATWAVE)

    print(f"\n{'时刻(UTC)':<17s}{'实际MW':>8s}{'晴空MW':>8s}{'缺口MW':>8s}"
          f"{'需求GW':>7s}{'上浮%':>7s}{'$@182':>8s}")
    for t, r in ev.iterrows():
        tag = " 热浪" if t.normalize() in HEATWAVE else ""
        print(f"{t.strftime('%m-%d %H:%M'):<17s}{r['eia_mw']:>8.0f}"
              f"{r['clearsky_mw']:>8.0f}{r['shortfall_mw']:>8.0f}"
              f"{r['demand_mw']/1000:>7.1f}{r['uplift_pct_base']:>7.1f}"
              f"{r['price_uplift_usd_at_182']:>8.1f}{tag}")

    print(f"\n=== 汇总 ===")
    print(f"事件小时 {len(ev)} 个, 其中热浪期 {hw.sum()} 个")
    print(f"缺口: 中位 {ev['shortfall_mw'].median():.0f}, 最大 {ev['shortfall_mw'].max():.0f} MW")
    print(f"事件缺电总量 {ev['shortfall_mw'].sum()/1000:.1f} GWh")
    print(f"隐含 RTM 上浮: 中位 +{ev['uplift_pct_base'].median():.1f}% "
          f"(高需求弹性情景 +{ev['uplift_pct_hot'].median():.1f}%)")
    print(f"按 2022-07 North 月均 $182/MWh: 中位 +"
          f"{ev['price_uplift_usd_at_182'].median():.0f} $/MWh, "
          f"最大 +{ev['price_uplift_usd_at_182'].max():.0f} $/MWh")

    ev.to_csv(OUT)
    print(f"已保存: {OUT}")
    FULL = OUT.replace("pv_event_price_impact", "pv_counterfactual_hourly")
    df.to_csv(FULL)
    print(f"已保存: {FULL}")

    # 07-14 沙尘日逐时剖面
    d14 = df.loc["2022-07-14"].between_time("15:00", "23:00")
    print("\n07-14 撒哈拉沙尘日逐时 (UTC):")
    for t, r in d14.iterrows():
        sw = r["shortfall"] if not np.isnan(r["shortfall"]) else 0
        print(f"  {t.strftime('%H:%M')}  实际 {r['eia']:6.0f}  晴空 {r['cs']:6.0f} "
              f" 缺口 {sw:6.0f} MW")


if __name__ == "__main__":
    main()
