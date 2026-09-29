"""西班牙最小链路数据获取 (全部免注册)
1) NASA POWER 逐小时 GHI/DNI/DHI/2m气温 @ 容量前 N 个光伏采样点, 2023
   (hourly solar 单位 kW-hr/m2/hr, ×1000 → W/m2; 填充值 -999)
2) PVGIS-SARAH3 逐小时 POA(G(i))/气温 @ 容量前 12 点, 2023 (辐照源交叉校验)
3) Energy-Charts (Fraunhofer ISE) 西班牙实际发电分技术 + 日前电价, 2023
输出: data/nasa_power/spain_pv_hubs_2023.npz
      data/pvgis/spain_sarah3_top12_2023.json
      data/energy_charts/es_2023.csv, es_price_2023.csv
用法: python scripts/data_download/download_spain_data.py [nhub]
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

HUB = r"c:\work\meteo\data\gem\spain_solar_hubs_2023.csv"
D_NASA = r"c:\work\meteo\data\nasa_power"
D_PVG = r"c:\work\meteo\data\pvgis"
D_ECH = r"c:\work\meteo\data\energy_charts"
for d in (D_NASA, D_PVG, D_ECH):
    os.makedirs(d, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}
NASA = "https://power.larc.nasa.gov/api/temporal/hourly/point"
VARS = ["ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_SW_DNI", "ALLSKY_SFC_SW_DIFF", "T2M"]
START, END = "20230101", "20231231"


def nasa_point(lat, lon, retries=3):
    for k in range(retries):
        try:
            r = requests.get(NASA, params={
                "parameters": ",".join(VARS), "community": "RE",
                "longitude": f"{lon:.4f}", "latitude": f"{lat:.4f}",
                "start": START, "end": END, "format": "JSON"}, headers=H, timeout=180)
            if r.status_code == 200:
                return r.json()["properties"]["parameter"]
            print(f"    HTTP {r.status_code}", flush=True)
        except Exception as e:
            print(f"    ERR {type(e).__name__}", flush=True)
        time.sleep(4 * (k + 1))
    return None


def get_nasa(nhub):
    hubs = pd.read_csv(HUB).head(nhub)
    n = len(hubs)
    print(f"[1] NASA POWER: {n} 点 (占清单容量 "
          f"{hubs['capacity_mw'].sum()/pd.read_csv(HUB)['capacity_mw'].sum()*100:.1f}%) "
          f"× {START}~{END}", flush=True)
    blocks = {v: [] for v in VARS}
    keys_ref = None
    for i, (_, h) in enumerate(hubs.iterrows()):
        pr = nasa_point(float(h["lat"]), float(h["lon"]))
        if pr is None:
            raise RuntimeError(f"NASA POWER 点 {i} ({h['name']}) 失败")
        ks = sorted(pr[VARS[0]].keys())
        if keys_ref is None:
            keys_ref = ks
        elif ks != keys_ref:
            raise RuntimeError("时间轴不一致")
        for v in VARS:
            blocks[v].append([pr[v][k] for k in ks])
        if (i + 1) % 20 == 0 or i == n - 1:
            print(f"  {i+1}/{n}", flush=True)
        time.sleep(0.7)
    fill = lambda a: a * 1000.0 if a.max() < 20 else a
    ghi = np.array(blocks["ALLSKY_SFC_SW_DWN"], dtype=np.float32).T
    dni = np.array(blocks["ALLSKY_SFC_SW_DNI"], dtype=np.float32).T
    dhi = np.array(blocks["ALLSKY_SFC_SW_DIFF"], dtype=np.float32).T
    t2m = np.array(blocks["T2M"], dtype=np.float32).T
    for a in (ghi, dni, dhi):
        a[a <= -900] = np.nan
    t2m[t2m <= -900] = np.nan
    if np.nanmax(ghi) < 20:      # kW/m2 → W/m2
        ghi, dni, dhi = ghi * 1000, dni * 1000, dhi * 1000
        print("  单位换算 ×1000 (kW/m2 → W/m2)")
    print(f"  GHI 均值 {np.nanmean(ghi):.1f} / 峰值 {np.nanmax(ghi):.0f} W/m2, "
          f"DNI 峰值 {np.nanmax(dni):.0f}, 形状 {ghi.shape}")
    p = os.path.join(D_NASA, "spain_pv_hubs_2023.npz")
    np.savez_compressed(p, times=np.array(keys_ref), lat=hubs["lat"].values,
                        lon=hubs["lon"].values, name=hubs["name"].values.astype(str),
                        capacity_mw=hubs["capacity_mw"].values.astype(np.float32),
                        shortwave_radiation=ghi, direct_normal_irradiance=dni,
                        diffuse_radiation=dhi, temperature_2m=t2m)
    print(f"  → {p}")


def get_pvgis():
    hubs = pd.read_csv(HUB).head(12)
    recs = {}
    print(f"\n[2] PVGIS-SARAH3: 前 {len(hubs)} 个大站点", flush=True)
    for _, h in hubs.iterrows():
        u = ("https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?"
             f"lat={h['lat']:.4f}&lon={h['lon']:.4f}&startyear=2023&endyear=2023"
             "&raddatabase=PVGIS-SARAH3&pvcalculation=1&peakpower=1&loss=14"
             "&angle=35&aspect=0&outputformat=json&browser=0")
        try:
            r = requests.get(u, headers=H, timeout=180)
            if r.status_code != 200:
                print(f"  {h['name'][:24]} -> {r.status_code}", flush=True)
                continue
            j = r.json()
            g = np.array([x["G(i)"] for x in j["outputs"]["hourly"]])
            recs[h["name"]] = {"lat": float(h["lat"]), "lon": float(h["lon"]),
                               "capacity_mw": float(h["capacity_mw"]),
                               "hourly": j["outputs"]["hourly"],
                               "meteo": j["inputs"]["meteo_data"]}
            print(f"  {h['name'][:26]:26s} n={len(g)} POA均值 {g.mean():6.1f} W/m2",
                  flush=True)
        except Exception as e:
            print(f"  {h['name'][:24]} ERR {type(e).__name__}", flush=True)
        time.sleep(1.5)
    p = os.path.join(D_PVG, "spain_sarah3_top12_2023.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False)
    print(f"  → {p}")


def get_ech():
    print("\n[3] Energy-Charts 西班牙实际发电 + 日前电价", flush=True)
    r = requests.get("https://api.energy-charts.info/public_power",
                     params={"country": "es", "start": "2023-01-01", "end": "2023-12-31"},
                     headers=H, timeout=300)
    j = r.json()
    df = pd.DataFrame({"time_utc": pd.to_datetime(j["unix_seconds"], unit="s", utc=True)})
    for t in j["production_types"]:
        df[t["name"]] = pd.Series(t["data"], dtype="float64")
    p1 = os.path.join(D_ECH, "es_2023.csv")
    df.to_csv(p1, index=False)
    print(f"  public_power n={len(df)} ({len(df)/365:.0f}/日) "
          f"Solar 峰值 {df['Solar'].max():.0f} MW → {p1}")

    r2 = requests.get("https://api.energy-charts.info/price",
                      params={"bzn": "ES", "start": "2023-01-01", "end": "2023-12-31"},
                      headers=H, timeout=300)
    j2 = r2.json()
    df2 = pd.DataFrame({"time_utc": pd.to_datetime(j2["unix_seconds"], unit="s", utc=True),
                        "price_eur_mwh": j2["price"]})
    p2 = os.path.join(D_ECH, "es_price_2023.csv")
    df2.to_csv(p2, index=False)
    print(f"  price n={len(df2)} 均价 {df2['price_eur_mwh'].mean():.2f} €/MWh, "
          f"负价 {int((df2['price_eur_mwh']<0).sum())} 段 → {p2}")


if __name__ == "__main__":
    nhub = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    get_nasa(nhub)
    get_pvgis()
    get_ech()