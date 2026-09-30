"""西班牙多年份数据获取 (2023/2024/2025, 全部免注册)
1) NASA POWER 逐小时 GHI/DNI/DHI/2m气温 @ 120 个采样点 × 3 年
2) Energy-Charts 西班牙实际发电分技术 + 日前电价 (2024, 2025; 2023 已有)
输出: data/nasa_power/spain_pv_hubs_{year}.npz
      data/energy_charts/es_{year}.csv, es_price_{year}.csv
用法: python skills/data-fetch-power/references/download_spain_data_multi.py [years 2023,2024,2025]
"""
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

HUB = r"c:\work\meteo\data\gem\spain_solar_hubs_multi.csv"
D_NASA = r"c:\work\meteo\data\nasa_power"
D_ECH = r"c:\work\meteo\data\energy_charts"
for d in (D_NASA, D_ECH):
    os.makedirs(d, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}
NASA = "https://power.larc.nasa.gov/api/temporal/hourly/point"
VARS = ["ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_SW_DNI", "ALLSKY_SFC_SW_DIFF", "T2M"]


def nasa_year_point(lat, lon, year, retries=4):
    for k in range(retries):
        try:
            r = requests.get(NASA, params={
                "parameters": ",".join(VARS), "community": "RE",
                "longitude": f"{lon:.4f}", "latitude": f"{lat:.4f}",
                "start": f"{year}0101", "end": f"{year}1231",
                "format": "JSON",
                # 2026-09-30 修正: 此处原缺省不传 -> NASA POWER 默认 LST(当地太阳时)。
                # 西班牙大陆 hub 的 LST 与 UTC 标签重合(实测差 0h), 但加那利 hub 差 1h,
                # 且该默认值不可依赖。见 kb/pitfalls/PIT-20260930-004。
                # 注意: data/nasa_power/spain_pv_hubs_multi_{年}.npz 是修正前生成的(LST 标签),
                # 对大陆 hub 等价, 加那利 2 点相差 1h。
                "time-standard": "UTC"}, headers=H, timeout=180)
            if r.status_code == 200:
                return r.json()["properties"]["parameter"]
            print(f"    HTTP {r.status_code}", flush=True)
        except Exception as e:
            print(f"    ERR {type(e).__name__}", flush=True)
        time.sleep(5 * (k + 1))
    return None


def get_nasa(years):
    hubs = pd.read_csv(HUB)
    n = len(hubs)
    for year in years:
        out = os.path.join(D_NASA, f"spain_pv_hubs_multi_{year}.npz")
        if os.path.exists(out):
            print(f"[NASA] {year} 已存在, 跳过 → {out}", flush=True)
            continue
        print(f"[NASA] {year}: {n} 点", flush=True)
        blocks = {v: [] for v in VARS}
        keys_ref = None
        for i, (_, h) in enumerate(hubs.iterrows()):
            pr = nasa_year_point(float(h["lat"]), float(h["lon"]), year)
            if pr is None:
                raise RuntimeError(f"NASA {year} 点 {i} 失败")
            ks = sorted(pr[VARS[0]].keys())
            if keys_ref is None:
                keys_ref = ks
            elif ks != keys_ref:
                raise RuntimeError("时间轴不一致")
            for v in VARS:
                blocks[v].append([pr[v][k] for k in ks])
            if (i + 1) % 30 == 0 or i == n - 1:
                print(f"  {i+1}/{n}", flush=True)
            time.sleep(0.6)
        arr = {v: np.array(blocks[v], dtype=np.float32).T for v in VARS}
        for v in ("ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_SW_DNI", "ALLSKY_SFC_SW_DIFF"):
            a = arr[v]
            a[a <= -900] = np.nan
            if np.nanmax(a) < 20:
                arr[v] = a * 1000.0
        arr["T2M"][arr["T2M"] <= -900] = np.nan
        np.savez_compressed(
            out, times=np.array(keys_ref), lat=hubs["lat"].values,
            lon=hubs["lon"].values, name=hubs["name"].values.astype(str),
            capacity_mw=hubs[f"cap_{year}"].values.astype(np.float32),
            shortwave_radiation=arr["ALLSKY_SFC_SW_DWN"],
            direct_normal_irradiance=arr["ALLSKY_SFC_SW_DNI"],
            diffuse_radiation=arr["ALLSKY_SFC_SW_DIFF"],
            temperature_2m=arr["T2M"])
        print(f"  GHI 峰值 {np.nanmax(arr['ALLSKY_SFC_SW_DWN']):.0f} W/m2, "
              f"容量 {hubs[f'cap_{year}'].sum()/1000:.2f} GW → {out}", flush=True)


def get_ech(years):
    for year in years:
        p1 = os.path.join(D_ECH, f"es_{year}.csv")
        if not os.path.exists(p1):
            r = requests.get("https://api.energy-charts.info/public_power",
                             params={"country": "es", "start": f"{year}-01-01",
                                     "end": f"{year}-12-31"}, headers=H, timeout=300)
            j = r.json()
            df = pd.DataFrame({"time_utc": pd.to_datetime(j["unix_seconds"], unit="s", utc=True)})
            for t in j["production_types"]:
                df[t["name"]] = pd.Series(t["data"], dtype="float64")
            df.to_csv(p1, index=False)
            print(f"[ECH] {year} public_power n={len(df)} Solar峰值 {df['Solar'].max():.0f} MW → {p1}",
                  flush=True)
        p2 = os.path.join(D_ECH, f"es_price_{year}.csv")
        if not os.path.exists(p2):
            r2 = requests.get("https://api.energy-charts.info/price",
                              params={"bzn": "ES", "start": f"{year}-01-01",
                                      "end": f"{year}-12-31"}, headers=H, timeout=300)
            j2 = r2.json()
            df2 = pd.DataFrame({"time_utc": pd.to_datetime(j2["unix_seconds"], unit="s", utc=True),
                                "price_eur_mwh": j2["price"]})
            df2.to_csv(p2, index=False)
            print(f"[ECH] {year} price n={len(df2)} 均价 {df2['price_eur_mwh'].mean():.2f} "
                  f"负价 {int((df2['price_eur_mwh']<0).sum())} → {p2}", flush=True)


if __name__ == "__main__":
    years = ([int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1
             else [2024, 2025])
    get_nasa(years)
    get_ech(years)