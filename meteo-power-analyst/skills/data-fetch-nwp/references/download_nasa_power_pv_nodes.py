"""GEM 匹配节点的 NASA POWER 逐小时辐照下载 (方向3 补充)

NPZ (ercot_pv_plants.npz) 只覆盖 136 个大电站; 节点匹配表 (pv_node_match.csv)
中 match_source=GEM 的节点电站不在 NPZ 内, 需单独拉取同口径 GHI,
才能做"节点本地云冲击 -> 节点电价"归因。

输入: data/ercot/pv_node_match.csv (GEM 行: node, plant, lat, lon, cap_mw)
输出: data/nasa_power/ercot_pv_node_extra.npz
      (times, node, plant, lat, lon, capacity_mw, shortwave_radiation, temperature_2m)
用法: python skills/data-fetch-nwp/references/download_nasa_power_pv_nodes.py
"""
import time

import numpy as np
import pandas as pd
import requests

MT = r"c:\work\meteo\data\ercot\pv_node_match.csv"
OUT = r"c:\work\meteo\data\nasa_power\ercot_pv_node_extra.npz"
NASA = "https://power.larc.nasa.gov/api/temporal/hourly/point"
VARS = ["ALLSKY_SFC_SW_DWN", "T2M"]
START, END = "20250101", "20260930"
H = {"User-Agent": "Mozilla/5.0"}


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
    mt = pd.read_csv(MT)
    mt = mt[(mt["match_source"] == "GEM") & mt["lat"].notna()].copy()
    mt = mt.drop_duplicates(subset=["plant"])
    print(f"待拉取 GEM 匹配节点: {len(mt)} 个", flush=True)

    ghi_blocks, t2m_blocks, keys_ref = [], [], None
    for i, r in mt.iterrows():
        pr = nasa_point(float(r["lat"]), float(r["lon"]))
        if pr is None:
            raise RuntimeError(f"NASA 点失败: {r['node']} {r['plant']}")
        ks = sorted(pr[VARS[0]].keys())
        if keys_ref is None:
            keys_ref = ks
        elif len(ks) != len(keys_ref):
            raise RuntimeError(f"时间轴长度不一致: {r['node']}")
        ghi_blocks.append([pr[VARS[0]][k] for k in ks])
        t2m_blocks.append([pr[VARS[1]][k] for k in ks])
        print(f"  {r['node']:14s} {r['plant']}  末时 {ks[-1]}", flush=True)
        time.sleep(0.6)

    ghi = np.array(ghi_blocks, dtype=np.float32).T
    ghi[ghi <= -900] = np.nan
    if np.nanmax(ghi) < 20:
        ghi = ghi * 1000.0
    t2m = np.array(t2m_blocks, dtype=np.float32).T
    t2m[t2m <= -900] = np.nan

    np.savez_compressed(
        OUT, times=np.array(keys_ref),
        node=mt["node"].values.astype(str), plant=mt["plant"].values.astype(str),
        lat=mt["lat"].values, lon=mt["lon"].values,
        capacity_mw=mt["cap_mw"].values.astype(np.float32),
        shortwave_radiation=ghi, temperature_2m=t2m)
    print(f"时间轴 {len(keys_ref)} h {keys_ref[0]} ~ {keys_ref[-1]}  -> {OUT}")


if __name__ == "__main__":
    main()
