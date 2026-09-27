"""NSRDB chunk 化散点提取效率小样
目的: 实测 h5coro 读取 (chunk 2000x500) 内单列/多列的耗时与流量, 决定批量策略
用法: python scripts/data_download/test_nsrdb_extract_speed.py
"""
import time

import numpy as np
import pandas as pd

from h5coro import h5coro
from h5coro.webdriver import HTTPDriver

URL = ("https://nrel-pds-nsrdb.s3.amazonaws.com/"
       "GOES/conus/v3.2.2/nsrdb_conus_irradiance_2022.h5")
PLANTS = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels.csv"


def bench(label, h5o, ds, rows, cols):
    t0 = time.time()
    arr = h5o.readDatasets(
        [{"dataset": ds, "hyperslice": [rows, cols]}])[ds]
    dt = time.time() - t0
    a = np.asarray(arr)
    print(f"{label}: shape={a.shape} elapsed={dt:.2f}s "
          f"valid={a.size} min={a.min()} max={a.max()}")
    return dt


def main():
    df = pd.read_csv(PLANTS)
    ok = df[df["nsrdb_index"] >= 0].sort_values("nsrdb_index")
    idx = ok["nsrdb_index"].values
    print(f"{len(idx)} 站, 索引 {idx.min()}~{idx.max()}")

    h5o = h5coro.H5Coro(URL, HTTPDriver, credentials=None,
                        cacheLineSize=131072, verbose=False, errorChecking=False)

    p0 = int(idx[0])
    # 1) 单站: 1 个时间块 (2000 行) 单列
    bench("单站 1 chunk (2000行x1列)", h5o, "/ghi", [0, 2000], [p0, p0 + 1])

    # 2) 单站: 1 天 (288 行) 单列
    bench("单站 1 天 (288行x1列)", h5o, "/ghi", [0, 288], [p0, p0 + 1])

    # 3) 单站: 5 个时间块 (整月 8640 行, 但月中跨块) 单列
    bench("单站 1 月 (8640行x1列)", h5o, "/ghi", [0, 8640], [p0, p0 + 1])

    # 4) 多站单 chunk: 该 chunk 内所有站列 (用首个站所在列块内的站)
    block = p0 // 500
    same = idx[(idx // 500) == block]
    print(f"\n站 {p0} 所在列块 {block} 内共 {len(same)} 站: {same}")
    if len(same) >= 2:
        bench(f"{len(same)} 站 1 chunk", h5o, "/ghi",
              [0, 2000], [int(same.min()), int(same.max()) + 1])

    # 5) 5 站 (不同列块) 1 天, 逐站循环
    t0 = time.time()
    for p in idx[:5]:
        h5o.readDatasets(
            [{"dataset": "/ghi", "hyperslice": [[0, 288], [int(p), int(p) + 1]]}])
    print(f"5 站 1 天 (逐站循环): {time.time()-t0:.2f}s "
          f"-> 100 站 1 月 3 分量估算 {100*30*3/5*(time.time()-t0):.0f}s")


if __name__ == "__main__":
    main()
