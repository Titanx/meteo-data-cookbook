"""下载 USCRN (美国气候基准网) 德州 8 站 2022-07 5 分钟观测 (NCEI 匿名 HTTPS)
用途: 用地面 pyranometer 实测 GHI 交叉验证热浪期 NSRDB 卫星反演辐照
产品: subhourly01 (CRNS0101), 5min SOLARAD (W/m2, 区间均值) + AIR_TEMPERATURE
输出: data/uscrn/{station}.csv (time_utc, solarad, air_temp, lat, lon)
"""
import io
import os
import time

import numpy as np
import pandas as pd
import requests

BASE = ("https://www.ncei.noaa.gov/pub/data/uscrn/products/"
        "subhourly01/2022/CRNS0101-05-2022-{name}.txt")
OUT_DIR = r"c:\work\meteo\data\uscrn"
STATIONS = [
    "TX_Austin_33_NW", "TX_Bronte_11_NNE", "TX_Edinburg_17_NNE",
    "TX_Monahans_6_ENE", "TX_Muleshoe_19_S", "TX_Palestine_6_WNW",
    "TX_Panther_Junction_2_N", "TX_Port_Aransas_32_NNE",
]
MISS = -9999.0


def fetch(name, retries=3):
    url = BASE.format(name=name)
    for k in range(retries):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200:
                return r.text
            print(f"  HTTP {r.status_code}, 重试", flush=True)
        except Exception as e:
            print(f"  {type(e).__name__}, 重试", flush=True)
            time.sleep(5 * (k + 1))
    raise RuntimeError(f"{name} 下载失败")


def parse(text):
    """CRNS0101-05: 无表头, 空格分隔 23 列; 时间戳=5min 区间结束
    列: 0 WBANNO 1 UTC_DATE 2 UTC_TIME 3 LST_DATE 4 LST_TIME 5 CRX_VN
        6 LONGITUDE 7 LATITUDE 8 AIR_TEMPERATURE 9 PRECIPITATION
        10 SOLAR_RADIATION 11 SR_FLAG (0=好, 1=溢出, 3=错误)"""
    rows = [ln.split() for ln in text.splitlines() if ln.strip()]
    a = np.array(rows, dtype=object)
    d = pd.DataFrame({
        "utc_date": a[:, 1],
        "utc_time": a[:, 2].astype(int),
        "lon": a[:, 6].astype(float),
        "lat": a[:, 7].astype(float),
        "tair": a[:, 8].astype(float),
        "solarad": a[:, 10].astype(float),
        "flag": a[:, 11].astype(int),
    })
    miss = d["tair"] <= -9990
    d.loc[miss, "tair"] = np.nan
    miss = d["solarad"] <= -9990
    d.loc[miss, "solarad"] = np.nan
    hh = (d["utc_time"] // 100).astype(str).str.zfill(2)
    mm = (d["utc_time"] % 100).astype(str).str.zfill(2)
    # 标签平移到区间起点 (与 NSRDB 5min 标签一致): end-5min
    d["time_utc"] = pd.to_datetime(d["utc_date"], format="%Y%m%d") + \
        pd.to_timedelta(hh + ":" + mm + ":00") - pd.Timedelta(minutes=5)
    return d.drop_duplicates("time_utc").set_index("time_utc")[
        ["lon", "lat", "tair", "solarad", "flag"]].sort_index()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    meta = []
    for name in STATIONS:
        d = parse(fetch(name))
        out = os.path.join(OUT_DIR, f"{name}.csv")
        d.to_csv(out)
        bad = (d["flag"] != 0).mean() * 100
        jul = d.loc["2022-07"]
        print(f"{name}: {len(jul)} 行 (07月), 范围 {jul.index[0]} ~ {jul.index[-1]}, "
              f"SOLARAD 最大 {jul['solarad'].max():.0f} W/m2, 非好标记 {bad:.1f}%",
              flush=True)
        meta.append({"station": name, "lat": d["lat"].iloc[0],
                     "lon": d["lon"].iloc[0], "rows_july": len(jul)})
        time.sleep(1)
    pd.DataFrame(meta).to_csv(os.path.join(OUT_DIR, "stations.csv"), index=False)
    print(f"已保存 {len(STATIONS)} 站至 {OUT_DIR}")


if __name__ == "__main__":
    main()
