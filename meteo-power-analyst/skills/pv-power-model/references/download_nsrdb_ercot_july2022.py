"""NSRDB v3.2.2 ERCOT 光伏电站 2022年7月辐照批量提取 (v2, 多进程)
v1 教训: 每 chunk 新开 h5py 句柄 -> 每次 ~20s B-tree 定位, 2 分钟 0 chunk
v2: 每分量 1 个独立进程, 进程内共享 1 个 h5py 句柄 (B-tree 缓存命中后 1.7s/chunk),
    3 进程并行无 h5py 线程安全问题
用法: python scripts/data_download/download_nsrdb_ercot_july2022.py            # 全部 3 分量
      python scripts/data_download/download_nsrdb_ercot_july2022.py ghi       # 单分量
"""
import json
import os
import subprocess
import sys
import time

import aiohttp
import fsspec
import h5py
import numpy as np
import pandas as pd
import xarray as xr

URL = ("https://nrel-pds-nsrdb.s3.amazonaws.com/"
       "GOES/conus/v3.2.2/nsrdb_conus_irradiance_2022.h5")
PLANTS = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels.csv"
OUT_DIR = r"c:\work\meteo\data\nsrdb"
OUT_NC = os.path.join(OUT_DIR, "ercot_solar_irradiance_2022-07.nc")
PROGRESS = os.path.join(OUT_DIR, "_july2022_progress.json")
TMP_DIR = os.path.join(OUT_DIR, "_chunks_tmp")

ROWS_PER_DAY = 288
JULY_R0 = 181 * ROWS_PER_DAY           # 2022-07-01 00:00 UTC = 52128
JULY_R1 = JULY_R0 + 31 * ROWS_PER_DAY  # 60960
CHUNK_T, CHUNK_C = 2000, 500
TIME_BLOCKS = sorted(set(range(JULY_R0 // CHUNK_T, (JULY_R1 - 1) // CHUNK_T + 1)))
DSETS = ["ghi", "dni", "dhi"]


def load_plants():
    df = pd.read_csv(PLANTS)
    ok = df[(df["nsrdb_index"] >= 0) & (df["capacity_mw"] >= 100)].copy()
    return ok.sort_values("nsrdb_index").reset_index(drop=True)


def run_one_ds(ds):
    plants = load_plants()
    col_blocks = np.unique(plants["nsrdb_index"] // CHUNK_C)
    tasks = [(int(tb), int(cb)) for tb in TIME_BLOCKS for cb in col_blocks]
    os.makedirs(TMP_DIR, exist_ok=True)

    # 断点状态以 npz 文件为准 (v2 教训: 3 进程共写 progress json 互相覆盖)
    todo = [(tb, cb) for tb, cb in tasks
            if not os.path.exists(os.path.join(TMP_DIR, f"{ds}_{tb}_{cb}.npz"))]
    print(f"[{ds}] {len(todo)}/{len(tasks)} 待处理", flush=True)

    kw = {"client_kwargs": {"timeout": aiohttp.ClientTimeout(total=300)}}
    f = None
    h5 = None

    def reopen():
        # reopen 自身也可能超时, 必须独立重试 (在 except 块中抛出的异常
        # 不会被同一轮 for-try 捕获)
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
                nh5 = h5py.File(nf, "r")
                return nf, nh5
            except Exception as e:
                print(f"[{ds}] reopen 第 {k+1} 次失败: {type(e).__name__}",
                      flush=True)
                time.sleep(5 * (k + 1))
        raise RuntimeError(f"[{ds}] reopen 4 次失败")

    t0 = time.time()
    cnt = 0
    f, h5 = reopen()
    for tb, cb in todo:
        pkl = os.path.join(TMP_DIR, f"{ds}_{tb}_{cb}.npz")
        r0 = max(tb * CHUNK_T, JULY_R0)
        r1 = min((tb + 1) * CHUNK_T, JULY_R1)
        for attempt in range(4):
            try:
                arr = np.asarray(h5[ds][r0:r1, cb * CHUNK_C:(cb + 1) * CHUNK_C],
                                 dtype=np.uint16)
                np.savez_compressed(pkl, arr=arr)
                break
            except Exception as e:
                print(f"[{ds}] chunk {tb}_{cb} 第 {attempt+1} 次失败: "
                      f"{type(e).__name__}, 重开句柄", flush=True)
                f, h5 = reopen()
        else:
            raise RuntimeError(f"[{ds}] chunk {tb}_{cb} 4 次重试均失败")
        cnt += 1
        if cnt % 10 == 0:
            el = time.time() - t0
            eta = el / cnt * (len(todo) - cnt)
            print(f"[{ds}] {cnt}/{len(todo)} {el:.0f}s "
                  f"({cnt/el:.2f}/s) ETA {eta/60:.1f}min", flush=True)
    print(f"[{ds}] 完成: {cnt} chunks, {time.time()-t0:.0f}s", flush=True)


def assemble():
    plants = load_plants()
    col_blocks = np.unique(plants["nsrdb_index"] // CHUNK_C)
    n_time = JULY_R1 - JULY_R0
    out = {}
    for ds in DSETS:
        full = np.zeros((n_time, len(plants)), dtype=np.float32)
        for tb in TIME_BLOCKS:
            r0 = max(tb * CHUNK_T, JULY_R0) - JULY_R0
            r1 = min((tb + 1) * CHUNK_T, JULY_R1) - JULY_R0
            block_arrs = {}
            for cb in col_blocks:
                pkl = os.path.join(TMP_DIR, f"{ds}_{tb}_{cb}.npz")
                if not os.path.exists(pkl):
                    raise RuntimeError(f"缺 chunk: {ds} tb={tb} cb={cb}")
                block_arrs[cb] = np.load(pkl)["arr"]
            for j, pi in enumerate(plants["nsrdb_index"]):
                cb = pi // CHUNK_C
                off = pi - cb * CHUNK_C
                full[r0:r1, j] = block_arrs[cb][:, off]
        out[ds] = full
        print(f"{ds}: max={full.max():.0f} W/m2", flush=True)

    times = pd.date_range("2022-07-01", periods=n_time, freq="5min")
    ds_out = xr.Dataset(
        {k.upper(): (("time", "plant"), v) for k, v in out.items()},
        coords={"time": times, "plant": plants["name"].values,
                "latitude": ("plant", plants["lat"].values),
                "longitude": ("plant", plants["lon"].values),
                "capacity_mw": ("plant", plants["capacity_mw"].values),
                "nsrdb_index": ("plant", plants["nsrdb_index"].values)},
        attrs={"source": URL, "units": "W/m2", "temporal": "5min means UTC",
               "created": time.strftime("%Y-%m-%d %H:%M:%S")})
    ds_out.to_netcdf(OUT_NC)
    print(f"已保存: {OUT_NC} ({os.path.getsize(OUT_NC)/1e6:.1f} MB)", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_one_ds(sys.argv[1])
    else:
        script = os.path.abspath(__file__)
        procs = [subprocess.Popen(
            [sys.executable, "-X", "utf8", script, ds])
            for ds in DSETS]
        for p in procs:
            p.wait()
        print("3 分量全部完成, 开始组装", flush=True)
        assemble()
