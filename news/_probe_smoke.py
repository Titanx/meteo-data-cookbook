import time

import aiohttp
import fsspec
import h5py

URL = ("https://nrel-pds-nsrdb.s3.amazonaws.com/"
       "GOES/conus/v3.2.2/nsrdb_conus_irradiance_2022.h5")

kw = {"client_kwargs": {"timeout": aiohttp.ClientTimeout(total=180)}}
f = fsspec.open(URL, "rb", block_size=1024 * 1024, **kw).open()
t0 = time.time()
with h5py.File(f, "r") as h5:
    arr = h5["ghi"][52128:53128, 848000:848500]
    print(f"切片耗时: {time.time()-t0:.2f}s, shape={arr.shape}, dtype={arr.dtype}")
    print("max:", arr.max(), "列 848035 行样本:", arr[0, 35], arr[144, 35], arr[287, 35])
    t0 = time.time()
    arr2 = h5["ghi"][53128:55128, 848000:848500]
    print(f"第二切片 (同列块相邻时间块): {time.time()-t0:.2f}s")
f.close()
