# -*- coding: utf-8 -*-
"""西班牙 9 个光伏区 日最高/最低气温 下载 (Open-Meteo Archive, 免注册)
用途: PS-037 的"温度→负荷"预报链。站点与 download_spain_seasonal.py 的季节预报**完全一致**,
      以保证历史拟合与未来预报的气温口径相同。
输出: data/openmeteo_temperature_spain/daily_temp.json
用法: python download_spain_temperature.py
"""
import json
import os
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(r"c:\work\meteo\data\openmeteo_temperature_spain")
SITES = {
    "Andalucia_Sevilla": (37.40, -5.60), "Andalucia_Cordoba": (37.90, -4.60),
    "Extremadura_Badajoz": (38.85, -6.40), "Extremadura_Caceres": (39.50, -6.30),
    "CastillaLaMancha_CReal": (38.95, -3.90), "CastillaLaMancha_Toledo": (39.90, -3.05),
    "Murcia": (37.90, -1.40), "Aragon_Zaragoza": (41.55, -1.00),
    "CastillaLeon_Valladolid": (41.50, -4.90),
}
START, END = "2022-12-01", "2026-09-28"   # 起点前移一个月, 便于跨年对齐
BASE = "https://archive-api.open-meteo.com/v1/archive"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = list(SITES)
    lats = ",".join("%.2f" % SITES[n][0] for n in names)
    lons = ",".join("%.2f" % SITES[n][1] for n in names)
    params = {
        "latitude": lats, "longitude": lons,
        "start_date": START, "end_date": END,
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean",
        "timezone": "Europe/Madrid",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "meteo-research/1.0"})
    with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
        data = json.loads(r.read().decode("utf-8"))

    locs = data if isinstance(data, list) else [data]
    print("返回站点数 = %d (请求 %d)" % (len(locs), len(names)))
    payload = {}
    for n, loc in zip(names, locs):
        d = loc["daily"]
        payload[n] = {"lat": loc["latitude"], "lon": loc["longitude"],
                      "time": d["time"],
                      "tmax": d["temperature_2m_max"],
                      "tmin": d["temperature_2m_min"],
                      "tmean": d["temperature_2m_mean"]}
        ok = sum(v is not None for v in d["temperature_2m_max"])
        print("  %-26s %d 天 (有效 %d), 覆盖 %s ~ %s"
              % (n, len(d["time"]), ok, d["time"][0], d["time"][-1]))
    with open(OUT / "daily_temp.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print("\n→ %s" % (OUT / "daily_temp.json"))


if __name__ == "__main__":
    main()
