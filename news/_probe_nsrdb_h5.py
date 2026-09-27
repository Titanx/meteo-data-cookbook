"""NSRDB 日循环诊断: 像素0 的1月1日/7月1日全天 GHI"""
import numpy as np
from h5coro import h5coro
from h5coro.webdriver import HTTPDriver

URL = ("https://nrel-pds-nsrdb.s3.amazonaws.com/"
       "GOES/conus/v3.2.2/nsrdb_conus_irradiance_2022.h5")
h5o = h5coro.H5Coro(URL, HTTPDriver, credentials=None, cacheLineSize=131072,
                    verbose=False, errorChecking=False)

for label, r0 in [("1月1日", 0), ("7月1日", 181 * 288)]:
    arr = h5o.readDatasets([{"dataset": "/ghi", "hyperslice": [[r0, r0 + 288], [0, 1]]}])["/ghi"]
    a = np.asarray(arr).ravel()
    imax = int(np.argmax(a))
    print(f"{label}: max={a[imax]} @ {imax*5//60:02d}:{imax*5%60:02d} UTC | "
          f"min={a.min()} | 06-18UTC均值={a[int(6*12):int(18*12)].mean():.0f} | "
          f"夜(00-06)均值={a[:72].mean():.0f}")
    # 每3小时采样
    print("   每3h:", [int(a[i*36]) for i in range(8)])
