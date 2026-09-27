"""探测 NSRDB v3.2.2 ancillary_a/b 2022 文件
确认: 数据集清单 / 温度变量名 / dtype / chunk / 时间分辨率 (shape[0]/365) / 样例值"""
import time

import aiohttp
import fsspec
import h5py

BASE = ("https://nrel-pds-nsrdb.s3.amazonaws.com/GOES/conus/v3.2.2/"
        "nsrdb_conus_ancillary_{tag}_2022.h5")
kw = {"client_kwargs": {"timeout": aiohttp.ClientTimeout(total=60)}}


def open_h5(url, attempt=5):
    for k in range(attempt):
        try:
            f = fsspec.open(url, "rb", block_size=1024 * 1024, **kw).open()
            return f, h5py.File(f, "r")
        except Exception as e:
            print(f"open 第 {k+1} 次失败: {type(e).__name__}", flush=True)
            time.sleep(3 * (k + 1))
    raise RuntimeError("open 5 次失败")


for tag in ["a", "b"]:
    url = BASE.format(tag=tag)
    f, h5 = open_h5(url)
    print(f"\n===== ancillary_{tag} =====", flush=True)
    print("根键:", sorted(h5.keys()), flush=True)
    for name in sorted(h5.keys()):
        if name in ("meta", "time_index"):
            d = h5[name]
            print(f"  {name}: shape={d.shape} dtype={d.dtype}", flush=True)
            continue
        d = h5[name]
        n_per_day = d.shape[0] / 365 if d.shape[0] > 4000 else None
        print(f"  {name}: dtype={d.dtype} shape={d.shape} "
              f"chunks={d.chunks} rows/day={n_per_day}", flush=True)
        print(f"    attrs: {{k: (v.tolist() if hasattr(v,'tolist') else v) "
              f"for k,v in d.attrs.items()}}", flush=True)
        print("    attrs:", {k: (v.tolist() if hasattr(v, "tolist") else v)
                              for k, v in d.attrs.items()}, flush=True)
        if n_per_day is not None:
            # 07-01 15:00 UTC 附近: 5min->行 52296 / 60min->行 4344+... 视分辨率
            row = int(181 * d.shape[0] / 365) + int(15 / (24 / (d.shape[0] / 365)))
            try:
                print(f"    sample [{row},1530437] = {d[row, 1530437]}",
                      flush=True)
            except Exception as e:
                print(f"    sample 失败: {type(e).__name__}", flush=True)
    h5.close()
    f.close()
print("done", flush=True)
