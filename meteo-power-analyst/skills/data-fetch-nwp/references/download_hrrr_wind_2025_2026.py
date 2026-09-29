"""下载 HRRR 80m 风速 + 2m 气温 (Open-Meteo 历史预报 API, ERCOT 风电场 2025-01-01~2026-09-06)
用途: 风功率物理链路的资源输入 (80m 为 ERCOT 风机典型轮毂高度)
API: historical-forecast-api.open-meteo.com, models=ncep_hrrr_conus, 匿名免key
输出: data/nsrdb/hrrr_wind80m_2025_2026.npz (14736×165, m/s) + t2m + time + names
用法: python scripts/data_download/download_hrrr_wind_2025_2026.py
"""
import time

import numpy as np
import pandas as pd
import requests

API = "https://historical-forecast-api.open-meteo.com/v1/forecast"
OUT = r"c:\work\meteo\data\nsrdb\hrrr_wind80m_2025_2026.npz"
HUB = r"c:\work\meteo\data\gem\ercot_wind_plants_2025.csv"
START, END = "2025-01-01", "2026-09-06"
BATCH = 20
KMH = 1 / 3.6


def fetch(lats, lons, retries=4):
    for k in range(retries):
        try:
            r = requests.get(API, params={
                "latitude": lats, "longitude": lons,
                "start_date": START, "end_date": END,
                "hourly": "wind_speed_80m,temperature_2m",
                "models": "ncep_hrrr_conus", "timezone": "UTC"}, timeout=240)
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
    h = pd.read_csv(HUB)
    n = len(h)
    print(f"{n} 个风电点位, {START} ~ {END}", flush=True)
    times_ref, spd_blocks, tm_blocks = None, [], []
    for s in range(0, n, BATCH):
        chunk = h.iloc[s:s + BATCH]
        lats = ",".join(f"{x:.4f}" for x in chunk["lat"])
        lons = ",".join(f"{x:.4f}" for x in chunk["lon"])
        d = fetch(lats, lons)
        if d is None or len(d) != len(chunk):
            raise RuntimeError(f"批次 {s} 失败 (返回 {None if d is None else len(d)})")
        if times_ref is None:
            times_ref = d[0]["hourly"]["time"]
        for item in d:
            if item["hourly"]["time"] != times_ref:
                raise RuntimeError("时间轴不一致")
            spd_blocks.append(item["hourly"]["wind_speed_80m"])
            tm_blocks.append(item["hourly"]["temperature_2m"])
        print(f"  {min(s+BATCH, n)}/{n} 完成", flush=True)
        time.sleep(0.6)

    ws = np.array(spd_blocks, dtype=np.float32).T * KMH      # km/h → m/s
    tm = np.array(tm_blocks, dtype=np.float32).T
    print(f"风速形状 {ws.shape}, 缺失 {int(np.isnan(ws).sum())}")
    print(f"风速 {np.nanmin(ws):.1f} ~ {np.nanmax(ws):.1f} m/s, 均值 {np.nanmean(ws):.1f} m/s")
    print(f"点位均值范围 {np.nanmean(ws,axis=0).min():.1f} ~ {np.nanmean(ws,axis=0).max():.1f} m/s")
    np.savez_compressed(OUT, ws80=ws, t2m=tm,
                        names=h["name"].values.astype(str),
                        capacity_mw=h["capacity_mw"].values.astype(np.float32),
                        times=np.array(times_ref))
    print(f"已保存: {OUT}")


if __name__ == "__main__":
    main()