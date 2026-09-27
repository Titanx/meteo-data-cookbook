import time

import aiohttp
import fsspec
import h5py

URL = ("https://nrel-pds-nsrdb.s3.amazonaws.com/"
       "GOES/conus/v3.2.2/nsrdb_conus_irradiance_2022.h5")

kw = {"client_kwargs": {"timeout": aiohttp.ClientTimeout(total=120)}}
f = fsspec.open(URL, "rb", block_size=1024 * 1024, **kw).open()
with h5py.File(f, "r") as h5:
    ghi = h5["ghi"]
    print("chunks:", ghi.chunks)
    t0 = time.time()
    for coord in [(26 * 2000, 848035 // 500 * 500),
                  (27 * 2000, 1000000 // 500 * 500),
                  (30 * 2000, 1708116 // 500 * 500)]:
        ci = ghi.id.get_chunk_info_by_coord(coord)
        print(f"coord {coord}: offset={ci.byte_offset} size={ci.size}")
    print(f"3 次定位耗时: {time.time()-t0:.2f}s")
    t0 = time.time()
    for tb in range(26, 31):
        for cb in [848035 // 500, 1000000 // 500, 1708116 // 500]:
            ghi.id.get_chunk_info_by_coord((tb * 2000, cb * 500))
    print(f"再 15 次定位: {time.time()-t0:.2f}s")
