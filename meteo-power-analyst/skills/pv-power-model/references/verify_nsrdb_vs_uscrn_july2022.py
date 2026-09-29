"""NSRDB 卫星辐照 vs USCRN 地面实测 交叉验证 (2022-07, 德州 8 站)
核心问题: 热浪期 (07-13~18) 模型低估是 NSRDB 反演偏低, 还是 PV 侧 (温度/弃电)?
方法: 同像素同窗 GHI 逐日对比, 热浪日 vs 非热浪日 的 NSRDB/USCRN 比值漂移
"""
import os

import numpy as np
import pandas as pd

USCRN_DIR = r"c:\work\meteo\data\uscrn"
NSRDB = r"c:\work\meteo\data\nsrdb\uscrn_nsrdb_ghi_2022-07.npz"
HEATWAVE = pd.date_range("2022-07-13", "2022-07-18")


def load_uscrn(station):
    d = pd.read_csv(os.path.join(USCRN_DIR, f"{station}.csv"),
                    index_col=0, parse_dates=True)
    d.index = d.index.tz_localize(None)
    d = d[d["flag"] == 0]
    return d[["solarad", "tair"]].resample("5min").mean()


def daily_stats(j, daylight="solarad"):
    """逐日: 白天辐照积分 (KWh/m2) + 正午窗 (17-22 UTC) 均值"""
    dl = j[j[daylight] > 20]
    daily_ins = dl[daylight].resample("1D").sum() / 1000.0  # Wh->kWh
    noon = j.between_time("17:00", "22:00")[daylight].resample("1D").mean()
    return daily_ins, noon


def main():
    z = np.load(NSRDB, allow_pickle=True)
    times = pd.DatetimeIndex(z["times"]).tz_localize(None)
    ghi = z["ghi"]
    stations = list(z["stations"])

    rows = []
    per_station_daily = {}
    for k, st in enumerate(stations):
        ns = pd.Series(ghi[:, k].astype(float), index=times)
        us = load_uscrn(st).reindex(times)["solarad"]
        ta = load_uscrn(st).reindex(times)["tair"]
        j = pd.DataFrame({"nsrdb": ns, "uscrn": us, "tair": ta}).dropna(
            subset=["nsrdb", "uscrn"])

        # 小时均值再比 (吸收 5min 时标/云移相位差)
        h = j[["nsrdb", "uscrn"]].resample("1h").mean()
        hb = h[h["uscrn"] > 20]
        r = hb["nsrdb"].corr(hb["uscrn"])
        ratio_all = (hb["nsrdb"] / hb["uscrn"].clip(lower=20)).median()

        ins_n, noon_n = daily_stats(j, "nsrdb")
        ins_u, noon_u = daily_stats(j, "uscrn")
        dd = pd.DataFrame({"ins_n": ins_n, "ins_u": ins_u,
                           "noon_n": noon_n, "noon_u": noon_u}).dropna()
        dd["ratio"] = dd["ins_n"] / dd["ins_u"]
        per_station_daily[st] = dd

        hw = dd.index.normalize().isin(HEATWAVE)
        nhw = ~hw
        tmax = ta.resample("1D").max().reindex(dd.index)
        rows.append({
            "station": st, "hours": len(hb), "hourly_r": r,
            "ratio_all": ratio_all,
            "ratio_heatwave": dd.loc[hw, "ratio"].median(),
            "ratio_normal": dd.loc[nhw, "ratio"].median(),
            "tmax_hw_mean": tmax[hw].mean(),
            "tmax_normal_mean": tmax[nhw].mean(),
        })

    t = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(t.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # 全站汇总逐日比值 (装机区域权重外, 简单中位)
    all_daily = pd.concat([d[["ratio"]] for d in per_station_daily.values()])
    daily_med = all_daily.groupby(level=0).median()
    daily_med = daily_med.loc["2022-07-01":"2022-07-31"]
    print("\n逐日全站中位 NSRDB/USCRN 比值 (日辐照积分):")
    for day, r in daily_med.iterrows():
        tag = "  <-- 热浪" if day in HEATWAVE else ""
        print(f"  {day.date()}  {r['ratio']:.4f}{tag}")

    hw = daily_med.loc[daily_med.index.isin(HEATWAVE), "ratio"]
    nhw = daily_med.loc[~daily_med.index.isin(HEATWAVE), "ratio"]
    print(f"\n热浪期比值中位 {hw.median():.4f} vs 非热浪 {nhw.median():.4f}, "
          f"漂移 {hw.median()/nhw.median()-1:+.2%}")

    out = os.path.join(USCRN_DIR, "nsrdb_uscrn_daily.csv")
    pd.concat({k: v for k, v in per_station_daily.items()}).to_csv(out)
    print(f"逐站逐日明细: {out}")


if __name__ == "__main__":
    main()
