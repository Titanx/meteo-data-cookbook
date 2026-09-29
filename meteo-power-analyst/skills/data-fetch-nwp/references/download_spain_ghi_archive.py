# -*- coding: utf-8 -*-
"""西班牙光伏代表点位的**实测**辐照下载(Open-Meteo Archive, ERA5) —— PS-044

用途: 给西班牙侧 NWP 预报做 ①训练用的"真值气象"与 ②预报误差/同质性核验基准。
      口径与 NWP 点位完全一致(同一批 GEM 容量加权点)。

输出: data/openmeteo_nwp_spain/es_ghi_archive.npz (ghi/t2m [N hub, T hour], time)
用法: python skills/data-fetch-nwp/references/download_spain_ghi_archive.py
"""
import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(r"c:\work\meteo\data\openmeteo_nwp_spain")
OUT.mkdir(parents=True, exist_ok=True)
HUBS = Path(r"c:\work\meteo\data\gem\spain_solar_hubs_nwp.csv")
START, END = "2023-01-01", "2026-09-29"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(url, tries=5):
    delay = 6
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "meteo-research/1.0"})
            with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and k < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def main():
    hubs = pd.read_csv(HUBS)
    f = OUT / "es_ghi_archive.npz"
    if f.exists():
        z = np.load(f)
        print("缓存: %s %d hub × %d 小时" % (str(f), z["ghi"].shape[0], z["ghi"].shape[1]))
        return
    G, Tall, tt = [], [], None
    for i, h in hubs.iterrows():
        q = dict(latitude=h["lat"], longitude=h["lon"], start_date=START, end_date=END,
                 timezone="UTC", hourly="shortwave_radiation,temperature_2m")
        j = get("https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(q))
        hh = j["hourly"]
        if tt is None:
            tt = np.array(pd.to_datetime(hh["time"]).astype("datetime64[ns]"))
        G.append(np.array([np.nan if v is None else float(v) for v in hh["shortwave_radiation"]],
                          dtype=np.float32))
        Tall.append(np.array([np.nan if v is None else float(v) for v in hh["temperature_2m"]],
                             dtype=np.float32))
        print("  hub %2d/%d %-40s ghi 均值 %6.1f W/m²" % (i + 1, len(hubs), str(h["name"])[:40],
                                                          np.nanmean(G[-1])))
        time.sleep(1.2)
    ghi = np.stack(G, axis=0)
    t2m = np.stack(Tall, axis=0)
    np.savez_compressed(f, ghi=ghi, t2m=t2m, time=tt)
    print("\n→ %s  ghi %s  t2m %s  时间 %s ~ %s"
          % (f, ghi.shape, t2m.shape, pd.Timestamp(tt[0]), pd.Timestamp(tt[-1])))


if __name__ == "__main__":
    main()
