"""ERCOT 光伏电站 NASA POWER 逐小时辐照/气温下载 (2025-01 ~ 2026-09)
目的: 为 ERCOT 光伏构造**全天候潜力** (all-sky potential), 以得到"潜力−实际"内生缺口,
      补齐可逆性检验矩阵中缺失的一格 (ERCOT 光伏 内生缺口)。
源:   NASA POWER hourly point (MERRA-2, 免注册, 无硬限流)
输入: data/nsrdb/ercot_solar_plants_pixels_2025.csv (name, lat, lon, capacity_mw)
输出: data/nasa_power/ercot_pv_plants.npz
用法: python skills/data-fetch-nwp/references/download_nasa_power_ercot_pv.py
"""
import os
import time

import numpy as np
import pandas as pd
import requests

PLANTS = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels_2025.csv"
D_NASA = r"c:\work\meteo\data\nasa_power"
os.makedirs(D_NASA, exist_ok=True)
OUT = os.path.join(D_NASA, "ercot_pv_plants.npz")
H = {"User-Agent": "Mozilla/5.0"}
NASA = "https://power.larc.nasa.gov/api/temporal/hourly/point"
VARS = ["ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_SW_DNI", "ALLSKY_SFC_SW_DIFF", "T2M"]
START, END = "20250101", "20260906"


def nasa_point(lat, lon, retries=4):
    for k in range(retries):
        try:
            r = requests.get(NASA, params={
                "parameters": ",".join(VARS), "community": "RE",
                "longitude": f"{lon:.4f}", "latitude": f"{lat:.4f}",
                "start": START, "end": END, "format": "JSON",
                "time-standard": "UTC"}, headers=H, timeout=300)
            if r.status_code == 200:
                return r.json()["properties"]["parameter"]
            print(f"    HTTP {r.status_code}", flush=True)
        except Exception as e:
            print(f"    ERR {type(e).__name__}", flush=True)
        time.sleep(5 * (k + 1))
    return None


def main():
    df = pd.read_csv(PLANTS)
    df["key"] = df["lat"].round(4).astype(str) + "_" + df["lon"].round(4).astype(str)
    # 按唯一坐标去重 (同一像素多座电站 → 容量相加)
    agg = df.groupby("key").agg(lat=("lat", "first"), lon=("lon", "first"),
                                capacity_mw=("capacity_mw", "sum"),
                                name=("name", "first")).reset_index()
    n = len(agg)
    print(f"电站 {len(df)} 行 → 唯一坐标 {n} 个, 总容量 {agg['capacity_mw'].sum()/1000:.2f} GW",
          flush=True)

    blocks = {v: [] for v in VARS}
    keys_ref = None
    for i, row in agg.iterrows():
        pr = nasa_point(float(row["lat"]), float(row["lon"]))
        if pr is None:
            raise RuntimeError(f"NASA 点 {i} ({row['name']}) 失败")
        ks = sorted(pr[VARS[0]].keys())
        if keys_ref is None:
            keys_ref = ks
        elif len(ks) != len(keys_ref):
            raise RuntimeError(f"时间轴长度不一致: {len(ks)} vs {len(keys_ref)}")
        for v in VARS:
            blocks[v].append([pr[v][k] for k in ks])
        if (i + 1) % 20 == 0 or i == n - 1:
            print(f"  {i+1}/{n}  最新时间 {ks[-1]}", flush=True)
        time.sleep(0.6)

    arr = {v: np.array(blocks[v], dtype=np.float32).T for v in VARS}
    for v in ("ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_SW_DNI", "ALLSKY_SFC_SW_DIFF"):
        a = arr[v]
        a[a <= -900] = np.nan
        if np.nanmax(a) < 20:          # 单位可能是 kW-hr/m2 -> W/m2
            arr[v] = a * 1000.0
    arr["T2M"][arr["T2M"] <= -900] = np.nan

    np.savez_compressed(
        OUT, times=np.array(keys_ref),
        lat=agg["lat"].values, lon=agg["lon"].values,
        name=agg["name"].values.astype(str),
        capacity_mw=agg["capacity_mw"].values.astype(np.float32),
        shortwave_radiation=arr["ALLSKY_SFC_SW_DWN"],
        direct_normal_irradiance=arr["ALLSKY_SFC_SW_DNI"],
        diffuse_radiation=arr["ALLSKY_SFC_SW_DIFF"],
        temperature_2m=arr["T2M"])
    t0, t1 = keys_ref[0], keys_ref[-1]
    print(f"时间轴 {len(keys_ref)} 小时 {t0} ~ {t1}", flush=True)
    gmean = np.nanmean(arr["ALLSKY_SFC_SW_DWN"], axis=1)
    hh = pd.to_datetime(pd.Series(keys_ref), format="%Y%m%d%H").dt.hour
    print(f"GHI 峰值标签小时(UTC, 应≈18-19): "
          f"{pd.Series(gmean).groupby(hh.values).mean().idxmax()}", flush=True)
    print(f"GHI 峰值 {np.nanmax(arr['ALLSKY_SFC_SW_DWN']):.0f} W/m2, "
          f"NaN 比例 {np.isnan(arr['ALLSKY_SFC_SW_DWN']).mean()*100:.2f}%", flush=True)
    print(f"→ {OUT}", flush=True)


if __name__ == "__main__":
    main()
