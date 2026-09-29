"""提取 NSRDB GHI 在 USCRN 德州 8 站像素上的 2022-07 序列 (交叉验证用)
机制复用 download_nsrdb_ercot_july2022.py: fsspec+h5py 分块读, 断点续传
输出: data/nsrdb/uscrn_nsrdb_ghi_2022-07.npz
"""
import os
import time

import aiohttp
import fsspec
import h5py
import numpy as np
import pandas as pd

URL = ("https://nrel-pds-nsrdb.s3.amazonaws.com/"
       "GOES/conus/v3.2.2/nsrdb_conus_irradiance_2022.h5")
PIXELS = r"c:\work\meteo\data\nsrdb\nsrdb_v322_ercot_pixels.npz"
STATIONS = r"c:\work\meteo\data\uscrn\stations.csv"
OUT = r"c:\work\meteo\data\nsrdb\uscrn_nsrdb_ghi_2022-07.npz"

ROWS_PER_DAY = 288
JULY_R0 = 181 * ROWS_PER_DAY   # 52128
JULY_R1 = JULY_R0 + 31 * ROWS_PER_DAY
CHUNK_T, CHUNK_C = 2000, 500


def nearest_pixels():
    z = np.load(PIXELS)
    lat, lon, idx = z["latitude"], z["longitude"], z["index"]
    st = pd.read_csv(STATIONS)
    picks = []
    for _, r in st.iterrows():
        d = (lat - r["lat"]) ** 2 + \
            (np.cos(np.radians(r["lat"])) * (lon - r["lon"])) ** 2
        k = int(np.argmin(d))
        picks.append({"station": r["station"], "lat": r["lat"], "lon": r["lon"],
                      "nsrdb_index": int(idx[k]), "pixel_lat": float(lat[k]),
                      "pixel_lon": float(lon[k])})
    return pd.DataFrame(picks)


def main():
    picks = nearest_pixels()
    print("站点 -> NSRDB 像素:")
    for _, r in picks.iterrows():
        d_lat = (r["lat"] - r["pixel_lat"]) * 111
        d_lon = (r["lon"] - r["pixel_lon"]) * 111 * np.cos(np.radians(r["lat"]))
        print(f"  {r['station']:<24s} idx={r['nsrdb_index']:>8d} "
              f"距离 {np.hypot(d_lat, d_lon):.2f} km", flush=True)

    cols = picks["nsrdb_index"].values
    col_blocks = np.unique(cols // CHUNK_C)
    time_blocks = sorted(set(
        range(JULY_R0 // CHUNK_T, (JULY_R1 - 1) // CHUNK_T + 1)))
    tasks = [(tb, int(cb)) for tb in time_blocks for cb in col_blocks]
    print(f"{len(tasks)} chunks 待读", flush=True)

    kw = {"client_kwargs": {"timeout": aiohttp.ClientTimeout(total=300)}}
    f = h5 = None

    def reopen():
        for k in range(4):
            try:
                if h5 is not None:
                    try:
                        h5.close()
                    except Exception:
                        pass
                if f is not None:
                    try:
                        f.close()
                    except Exception:
                        pass
                nf = fsspec.open(URL, "rb", block_size=1024 * 1024, **kw).open()
                return nf, h5py.File(nf, "r")
            except Exception as e:
                print(f"reopen 第 {k+1} 次失败: {type(e).__name__}", flush=True)
                time.sleep(5 * (k + 1))
        raise RuntimeError("reopen 4 次失败")

    f, h5 = reopen()
    n_time = JULY_R1 - JULY_R0
    ghi = np.zeros((n_time, len(picks)), dtype=np.float32)
    t0 = time.time()
    for n, (tb, cb) in enumerate(tasks, 1):
        r0 = max(tb * CHUNK_T, JULY_R0)
        r1 = min((tb + 1) * CHUNK_T, JULY_R1)
        for attempt in range(4):
            try:
                arr = np.asarray(
                    h5["ghi"][r0:r1, cb * CHUNK_C:(cb + 1) * CHUNK_C],
                    dtype=np.uint16)
                break
            except Exception:
                print(f"chunk {tb}_{cb} 失败, 重开", flush=True)
                f, h5 = reopen()
        for j, pi in enumerate(cols):
            if pi // CHUNK_C != cb:
                continue
            off = pi - cb * CHUNK_C
            ghi[r0 - JULY_R0:r1 - JULY_R0, j] = arr[:, off]
        if n % 10 == 0:
            print(f"  {n}/{len(tasks)} {time.time()-t0:.0f}s", flush=True)

    times = pd.date_range("2022-07-01", periods=n_time, freq="5min")
    np.savez_compressed(
        OUT, ghi=ghi, times=times.values.astype("datetime64[s]"),
        stations=picks["station"].values.astype(str),
        nsrdb_index=picks["nsrdb_index"].values,
        lat=picks["lat"].values, lon=picks["lon"].values)
    print(f"已保存: {OUT} ({os.path.getsize(OUT)/1e6:.2f} MB)", flush=True)


if __name__ == "__main__":
    main()
