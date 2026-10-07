"""匹配节点的 ERA5 逐时辐照下载 (Open-Meteo archive, 方向3 本地云归因)

NASA POWER hourly 在 2026-06-25 之后返回填充值 (-999), 无法覆盖 9 月事件窗口;
改用 Open-Meteo archive (ERA5, ~0.25°, 滞后 ~5 天, 无鉴权) 拉取同口径 GHI。
晴空包络 (P95 by hour-of-day x doy±15d) 与 local_rel 均基于同一来源计算。

输入: data/ercot/pv_node_match.csv (46 个有坐标的匹配节点, NPZ+GEM)
输出: data/nasa_power/ercot_pv_node_om.npz
      (times, node, plant, lat, lon, capacity_mw, shortwave_radiation)
用法: python skills/data-fetch-nwp/references/download_openmeteo_pv_nodes.py
"""
import time

import numpy as np
import pandas as pd
import requests

MT = r"c:\work\meteo\data\ercot\pv_node_match.csv"
OUT = r"c:\work\meteo\data\nasa_power\ercot_pv_node_om.npz"
API = "https://archive-api.open-meteo.com/v1/archive"
START, END = "2025-01-01", "2026-09-30"


def om_point(lat, lon, retries=4):
    for k in range(retries):
        try:
            r = requests.get(API, params={
                "latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}",
                "start_date": START, "end_date": END,
                "hourly": "shortwave_radiation", "timezone": "UTC",
            }, timeout=300)
            if r.status_code == 200:
                return r.json()["hourly"]
            print(f"    HTTP {r.status_code}: {r.text[:120]}", flush=True)
        except Exception as e:
            print(f"    ERR {type(e).__name__}: {e}", flush=True)
        time.sleep(5 * (k + 1))
    return None


def main():
    mt = pd.read_csv(MT)
    mt = mt[mt["lat"].notna() & mt["match_source"].isin(["NPZ", "GEM"])].copy()
    mt = mt.drop_duplicates(subset=["node"])
    print(f"待拉取匹配节点: {len(mt)} 个", flush=True)

    times_ref = None
    ghi_blocks, nodes, plants, lats, lons, caps = [], [], [], [], [], []
    for _, r in mt.iterrows():
        h = om_point(float(r["lat"]), float(r["lon"]))
        if h is None:
            raise RuntimeError(f"OM 点失败: {r['node']}")
        t = h["time"]
        if times_ref is None:
            times_ref = t
        elif len(t) != len(times_ref):
            raise RuntimeError(f"时间轴长度不一致: {r['node']}")
        ghi_blocks.append(h["shortwave_radiation"])
        nodes.append(r["node"])
        plants.append(r["plant"])
        lats.append(float(r["lat"]))
        lons.append(float(r["lon"]))
        caps.append(float(r["cap_mw"]) if pd.notna(r["cap_mw"]) else np.nan)
        print(f"  {r['node']:14s} {str(r['plant'])[:30]:30s} "
              f"{len(t)}h 末时 {t[-1]}", flush=True)
        time.sleep(1.0)

    ghi = np.array(ghi_blocks, dtype=np.float32).T
    times = np.array([t.replace("-", "").replace("T", "")[:10]
                      for t in times_ref])
    np.savez_compressed(
        OUT, times=times, node=np.array(nodes, dtype=str),
        plant=np.array(plants, dtype=str), lat=np.array(lats),
        lon=np.array(lons), capacity_mw=np.array(caps, dtype=np.float32),
        shortwave_radiation=ghi)
    ok = np.isfinite(ghi[times >= "2026090700"]).mean()
    print(f"时间轴 {len(times)} h {times[0]} ~ {times[-1]}; "
          f"9月事件窗口非NaN占比 {ok:.3f} -> {OUT}")


if __name__ == "__main__":
    main()
