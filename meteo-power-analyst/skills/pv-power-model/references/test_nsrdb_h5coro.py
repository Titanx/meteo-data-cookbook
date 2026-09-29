"""NSRDB v3.2.2 CONUS S3 懒读取测试 (h5coro, 不下载 TB 级文件)
关键结论:
  - developer.nrel.gov / *.nrel.gov 在当前网络 DNS 不通, API/HSDS 路径不可用
  - nrel-pds-nsrdb.s3.amazonaws.com 匿名可列可读 (registry.opendata.aws/nrel-pds-nsrdb)
  - 全域 h5 单文件 1.5~2.4 TB, 只能部分读取; h5coro + HTTPDriver + 128KB 缓存行实测可用
  - h5coro 不支持复合 meta 与属性, 像素->坐标映射待解 (见报告)
用法: python scripts/data_download/test_nsrdb_h5coro.py
依赖: pip install h5coro
"""
import numpy as np
from h5coro import h5coro
from h5coro.webdriver import HTTPDriver

URL = ("https://nrel-pds-nsrdb.s3.amazonaws.com/"
       "GOES/conus/v3.2.2/nsrdb_conus_irradiance_2022.h5")


def main():
    # cacheLineSize=131072: 默认 4MB 缓存行在跨境网络会读超时
    # credentials 必须为 None: 传 "" 会被 HTTPDriver 加空 Bearer 头导致 S3 400
    h5o = h5coro.H5Coro(URL, HTTPDriver, credentials=None,
                        cacheLineSize=131072, verbose=False, errorChecking=False)

    print("=== 结构 ===")
    print(h5o.inspectPath("/"))
    print(h5o.inspectPath("/ghi"))  # uint16 [105120, 2842719] = 5min x 2km像素

    print()
    print("=== /ghi [0:4, 0:6] 直读 (HTTP Range) ===")
    arr = h5o.readDatasets(
        [{"dataset": "/ghi", "hyperslice": [[0, 4], [0, 6]]}])["/ghi"]
    print(arr)

    print()
    print("=== 像素0 日循环 (定位与量纲验证) ===")
    for label, r0 in [("1月1日", 0), ("7月1日", 181 * 288)]:
        a = np.asarray(h5o.readDatasets(
            [{"dataset": "/ghi", "hyperslice": [[r0, r0 + 288], [0, 1]]}])["/ghi"]).ravel()
        imax = int(a.argmax())
        print(f"{label}: max={a[imax]} W/m2 @ {imax*5//60:02d}:{imax*5%60:02d} UTC "
              f"(正午时刻指示像素经度, 峰值量级验证 scale_factor=1)")


if __name__ == "__main__":
    main()
