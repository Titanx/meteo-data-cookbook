"""下载 HRRR 2m 气温 (Open-Meteo 历史预报 API, ERCOT 光伏电站 2025-01-01~2026-09-06)
用途: 物理晴空反事实的温度输入, 与 PS-021/022 的 2022 口径完全一致
API: historical-forecast-api.open-meteo.com, models=ncep_hrrr_conus, 匿名免key
     支持逗号分隔多坐标批量请求 (顺序与输入一致)
输出: data/nsrdb/hrrr_t2m_2025_2026.npz (14736×N, °C) + 时间轴 + 站名
用法: python scripts/data_download/download_hrrr_temp_2025_2026.py [year]
"""
import sys
import time

import numpy as np
import pandas as pd
import requests

API = "https://historical-forecast-api.open-meteo.com/v1/forecast"
OUT_NPZ = r"c:\work\meteo\data\nsrdb\hrrr_t2m_2025_2026{sfx}.npz"
PLANTS_TMPL = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels_{year}.csv"
START, END = "2025-01-01", "2026-09-06"
BATCH = 20


def fetch(lats, lons, retries=3):
    for k in range(retries):
        try:
            r = requests.get(API, params={
                "latitude": lats, "longitude": lons,
                "start_date": START, "end_date": END,
                "hourly": "temperature_2m", "models": "ncep_hrrr_conus",
                "timezone": "UTC"}, timeout=180)
            d = r.json()
            if isinstance(d, list):
                return d
            if isinstance(d, dict) and "hourly" in d:
                return [d]
            print(f"  响应异常: {str(d)[:150]}", flush=True)
        except Exception as e:
            print(f"  请求失败 {type(e).__name__}: {e}", flush=True)
        time.sleep(6 * (k + 1))
    return None


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    sfx = "" if year == 2025 else f"_{year}"
    plants = pd.read_csv(PLANTS_TMPL.format(year=year))
    n = len(plants)
    print(f"{year}: {n} 座电站, {START} ~ {END}", flush=True)

    times_ref, blocks = None, []
    for s in range(0, n, BATCH):
        chunk = plants.iloc[s:s + BATCH]
        lats = ",".join(f"{x:.4f}" for x in chunk["lat"])
        lons = ",".join(f"{x:.4f}" for x in chunk["lon"])
        d = fetch(lats, lons)
        if d is None:
            raise RuntimeError(f"批次 {s} 失败")
        if len(d) != len(chunk):
            raise RuntimeError(f"批次 {s} 返回 {len(d)} != {len(chunk)}")
        if times_ref is None:
            times_ref = d[0]["hourly"]["time"]
        for item in d:
            t = item["hourly"]["time"]
            if t != times_ref:
                raise RuntimeError("时间轴不一致")
            blocks.append(item["hourly"]["temperature_2m"])
        print(f"  {min(s+BATCH, n)}/{n} 完成", flush=True)
        time.sleep(0.6)

    nt = len(times_ref)
    t2m = np.array(blocks, dtype=np.float32).T          # (nt, n)
    print(f"形状 {t2m.shape}, 缺失 {int(np.isnan(t2m).sum())}")
    print(f"温度范围 {np.nanmin(t2m):.1f} ~ {np.nanmax(t2m):.1f} °C, "
          f"均值 {np.nanmean(t2m):.1f}")
    out = OUT_NPZ.format(sfx=sfx)
    np.savez_compressed(out, t2m=t2m, names=plants["name"].values.astype(str),
                        times=np.array(times_ref))
    print(f"已保存: {out}")


if __name__ == "__main__":
    main()
