"""下载 HRRR 2m 气温 (Open-Meteo 历史预报 API, ERCOT 56 光伏电站, 2022-07)
用途: 替换 nsrdb_pvlib_power.py 的温度参数化, 消除热浪期正午低估
API: historical-forecast-api.open-meteo.com, models=ncep_hrrr_conus, 匿名免key
输出: data/nsrdb/hrrr_t2m_2022-07.npz (744×56, °C) + CSV
"""
import time

import numpy as np
import pandas as pd
import requests

PLANTS = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels.csv"
OUT_NPZ = r"c:\work\meteo\data\nsrdb\hrrr_t2m_2022-07.npz"
OUT_CSV = r"c:\work\meteo\data\nsrdb\hrrr_t2m_2022-07.csv"
API = "https://historical-forecast-api.open-meteo.com/v1/forecast"


def load_plants():
    df = pd.read_csv(PLANTS)
    return df[(df["nsrdb_index"] >= 0) & (df["capacity_mw"] >= 100)] \
        .sort_values("nsrdb_index").reset_index(drop=True)


def fetch_one(lat, lon, retries=3):
    for k in range(retries):
        try:
            r = requests.get(API, params={
                "latitude": lat, "longitude": lon,
                "start_date": "2022-07-01", "end_date": "2022-08-01",
                "hourly": "temperature_2m,wind_speed_10m",
                "models": "ncep_hrrr_conus", "timezone": "UTC",
            }, timeout=60)
            d = r.json()
            if "hourly" in d:
                return d["hourly"]["time"], d["hourly"]["temperature_2m"], \
                    d["hourly"]["wind_speed_10m"]
            print(f"  响应异常: {str(d)[:120]}", flush=True)
        except Exception as e:
            print(f"  请求失败 {type(e).__name__}, 重试", flush=True)
            time.sleep(5 * (k + 1))
    return None, None, None


def main():
    plants = load_plants()
    print(f"{len(plants)} 座电站", flush=True)

    times_ref = None
    t2m = np.zeros((744, len(plants)), dtype=np.float32)
    ws10 = np.zeros((744, len(plants)), dtype=np.float32)

    for i, row in plants.iterrows():
        ts, temp, ws = fetch_one(row["lat"], row["lon"])
        if ts is None:
            raise RuntimeError(f"电站 {row['name']} 获取失败")
        if times_ref is None:
            times_ref = ts
        elif ts != times_ref:
            raise RuntimeError(f"电站 {row['name']} 时间轴不一致")
        t2m[:, i] = temp[:744]
        ws10[:, i] = ws[:744]
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(plants)} 完成", flush=True)
        time.sleep(0.5)

    np.savez_compressed(OUT_NPZ, t2m=t2m, ws10=ws10,
                        names=plants["name"].values.astype(str),
                        times=np.array(times_ref[:744]))
    df = pd.DataFrame(t2m, index=pd.to_datetime(times_ref[:744]),
                      columns=plants["name"].values)
    df.to_csv(OUT_CSV)
    print(f"已保存: {OUT_NPZ}")
    print(f"温度范围: {t2m.min():.1f} ~ {t2m.max():.1f} °C, "
          f"均值 {t2m.mean():.1f}", flush=True)


if __name__ == "__main__":
    main()
