"""NSRDB v3.2.2 meta 流式下载与 ERCOT 像素定位
关键结论:
  - v3.2.2 "CONUS" 实际是 GOES-East+West 全视域网格: lat 14.6~47.9 (含墨西哥南部),
    lon -160~-60 (夏威夷~波多黎各), 像素按 gid_full 升序连续存储
  - h5coro 不支持 compound meta; h5py+fsspec 可读但大块请求跨境超时
  - 最优路径: h5py 拿 meta 磁盘偏移 (连续存储, offset=2636192, 346.8MB) ->
    requests Range 流式下载字节段 -> numpy frombuffer 本地解析
用法: python skills/pv-power-model/references/test_nsrdb_meta.py
依赖: h5py, fsspec, aiohttp, requests
"""
import os

import aiohttp
import fsspec
import h5py
import numpy as np
import requests

URL = ("https://nrel-pds-nsrdb.s3.amazonaws.com/"
       "GOES/conus/v3.2.2/nsrdb_conus_irradiance_2022.h5")
OUT_DIR = r"c:\work\meteo\data\nsrdb"
ERCOT_LAT = (25.8, 36.5)
ERCOT_LON = (-106.7, -93.4)

META_DTYPE = np.dtype([
    ("latitude", "<f4"), ("longitude", "<f4"), ("elevation", "<i2"),
    ("timezone", "<f4"), ("country", "S36"), ("state", "S30"),
    ("county", "S38"), ("gid_full", "<i4"),
])


def get_meta_offset():
    kw = {"client_kwargs": {"timeout": aiohttp.ClientTimeout(total=120)}}
    f = fsspec.open(URL, "rb", block_size=1024 * 1024, **kw).open()
    with h5py.File(f, "r") as h5:
        meta = h5["meta"]
        assert meta.chunks is None, "非连续存储, 需改用 chunk 逐块下载"
        return meta.id.get_offset(), meta.shape[0]


def stream_download(off, size, dst, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            headers = {"Range": f"bytes={off}-{off + size - 1}"}
            with requests.get(URL, headers=headers, stream=True,
                              timeout=(30, 120)) as r:
                r.raise_for_status()
                got = 0
                with open(dst, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        got += len(chunk)
                        if got % (16 << 20) < (1 << 20):
                            print(f"  {got/1e6:.0f}/{size/1e6:.0f} MB", flush=True)
            if got == size:
                return dst
            print(f"  不完整 ({got}/{size}), 重试")
        except Exception as e:
            print(f"  异常: {e}, 重试")
    raise RuntimeError("下载失败")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    raw = os.path.join(OUT_DIR, "nsrdb_v322_meta_raw.bin")

    off, n = get_meta_offset()
    size = n * META_DTYPE.itemsize
    print(f"meta: {n} 像素, offset={off}, {size/1e6:.1f} MB")

    if not (os.path.exists(raw) and os.path.getsize(raw) == size):
        print("流式下载 meta 字节段...")
        stream_download(off, size, raw)
    print(f"已缓存: {raw} ({os.path.getsize(raw)/1e6:.1f} MB)")

    meta = np.fromfile(raw, dtype=META_DTYPE, count=n)
    assert meta[0]["gid_full"] == 75456, "首像素 gid 校验失败"
    print(f"覆盖: lat {meta['latitude'].min():.1f}~{meta['latitude'].max():.1f}, "
          f"lon {meta['longitude'].min():.1f}~{meta['longitude'].max():.1f}")

    m = (meta["latitude"] >= ERCOT_LAT[0]) & (meta["latitude"] <= ERCOT_LAT[1]) & \
        (meta["longitude"] >= ERCOT_LON[0]) & (meta["longitude"] <= ERCOT_LON[1])
    idx = np.where(m)[0]
    print(f"ERCOT 像素: {idx.size} 个")
    print(f"  索引范围: {idx.min()} ~ {idx.max()}, gid 范围: "
          f"{meta['gid_full'][idx].min()} ~ {meta['gid_full'][idx].max()}")
    print(f"  州分布:德州 {int((meta['state'][idx] == b'Texas').sum())} 个")

    out = os.path.join(OUT_DIR, "nsrdb_v322_ercot_pixels.npz")
    np.savez_compressed(
        out,
        index=idx.astype(np.int64),
        latitude=meta["latitude"][idx],
        longitude=meta["longitude"][idx],
        elevation=meta["elevation"][idx],
        timezone=meta["timezone"][idx],
        gid_full=meta["gid_full"][idx],
    )
    print(f"已保存: {out} ({os.path.getsize(out)/1e6:.1f} MB)")

    all_meta = os.path.join(OUT_DIR, "nsrdb_v322_meta_all.npz")
    np.savez_compressed(
        all_meta,
        latitude=meta["latitude"], longitude=meta["longitude"],
        elevation=meta["elevation"], timezone=meta["timezone"],
        gid_full=meta["gid_full"],
    )
    print(f"全域 meta 缓存: {all_meta} ({os.path.getsize(all_meta)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
