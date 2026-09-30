"""MRMS QPE 下载与 ERCOT 裁剪测试
数据源: AWS S3 noaa-mrms-pds (匿名, 归档 2020-10-14 ~ 至今, 实测 2,178 天)
        https://mrms.ncep.noaa.gov/2D/ (匿名, 滚动最新 ~10天)
用法: python skills/data-fetch-radar/references/test_mrms_download.py
依赖: requests, xarray, cfgrib (GRIB2 读取)

2026-09-30 修: list_archive_dates() 此前用字符串拼接 URL, 未对 continuation-token
做 URL 编码 -> 第 2 页返回 HTTP 400(InvalidArgument), 而函数不检查状态码, 把"没有
下一页 token"当成"取完了", 于是静默截断在 1000 天(2020-10-14~2023-07-10), 并被误
读成"归档已终止、每产品恰好 1000 天"。现改用 params= 交给 requests 编码 + 校验状态码。
"""
import gzip
import os
import re
import requests

import numpy as np
import xarray as xr

S3 = "https://noaa-mrms-pds.s3.amazonaws.com"
DATA_DIR = r"c:\work\meteo\data\mrms"
PROD = "CONUS/MultiSensor_QPE_01H_Pass2_00.00/"  # 多传感器融合1h QPE, 最优产品
ERCOT_LAT = (25.8, 36.5)
ERCOT_LON = (253.3, 266.6)  # 0-360 约定; -106.7~-93.4


def list_archive_dates():
    """S3 归档日期全量分页。

    实测 2178 天 (2020-10-14 ~ 至今, 仍在写入), 分 3 页 [1000, 1000, 178]。
    注意: continuation-token 含 '/' 等字符, 必须 URL 编码 —— 用 params= 交给 requests,
    不要手工拼接; 并且必须校验 status_code, 否则 400 错误体会被当成"已取完"。
    """
    dates, token, pages = [], None, 0
    while True:
        q = {"list-type": "2", "prefix": PROD, "delimiter": "/", "max-keys": "1000"}
        if token:
            q["continuation-token"] = token
        r = requests.get(f"{S3}/", params=q, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"S3 列举失败 HTTP {r.status_code}: {r.text[:200]}")
        dates += [d for d in re.findall(r"<Prefix>(.*?)</Prefix>", r.text)
                  if re.search(r"/(\d{8})/$", d)]
        pages += 1
        tk = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", r.text)
        trunc = re.search(r"<IsTruncated>(.*?)</IsTruncated>", r.text)
        if trunc is None:
            raise RuntimeError("响应里没有 IsTruncated, 无法确认是否取完")
        if trunc.group(1) != "true" or tk is None:
            break
        token = tk.group(1)
    print(f"[S3] {pages} 页, 共 {len(dates)} 个日期: "
          f"{min(dates)[-9:-1]} ~ {max(dates)[-9:-1]}")
    return dates


def list_web_latest(n=5):
    """NCEP 官网滚动最新文件 (匿名, 滞后约1天)"""
    r = requests.get("https://mrms.ncep.noaa.gov/2D/MultiSensor_QPE_01H_Pass2/", timeout=30)
    files = re.findall(r'href="(MRMS_MultiSensor[^"]+\.gz)"', r.text)
    return files[-n:]


def download(key, dst):
    url = f"{S3}/{key}"
    with requests.get(url, timeout=300, stream=True) as rr:
        rr.raise_for_status()
        with open(dst, "wb") as f:
            for chunk in rr.iter_content(65536):
                f.write(chunk)
    return dst


def read_grib_crop_ercot(grib_path, nc_path):
    """读 GRIB2, 裁剪 ERCOT, 存 NetCDF"""
    with xr.open_dataset(grib_path, engine="cfgrib") as ds:
        v = list(ds.data_vars)[0]  # MRMS QPE 参数名在 cfgrib 中显示为 unknown
        lat, lon = ds.latitude.values, ds.longitude.values
        mask = (lat >= ERCOT_LAT[0]) & (lat <= ERCOT_LAT[1])
        lonm = (lon >= ERCOT_LON[0]) & (lon <= ERCOT_LON[1])
        sub = ds[v].isel(latitude=np.where(mask)[0], longitude=np.where(lonm)[0])
        sub.to_netcdf(nc_path)
        return float(sub.max()), float(sub.mean()), sub.shape


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)

    dates = list_archive_dates()
    print(f"[1] S3 归档: {len(dates)} 天, {dates[0].split('/')[-2]} ~ {dates[-1].split('/')[-2]}")
    print(f"[2] NCEP 官网最新: {list_web_latest(3)}")

    date = dates[-1]  # 归档最新一天
    r = requests.get(f"{S3}/?list-type=2&prefix={date}&max-keys=10", timeout=30)
    keys = re.findall(r"<Key>(.*?)</Key>", r.text)
    print(f"[3] {date} 文件数: {len(keys)}, 取 {keys[-1]}")
    dst = download(keys[-1], os.path.join(DATA_DIR, "sample_" + keys[-1].split("/")[-1]))
    print(f"[4] 下载完成: {dst} ({os.path.getsize(dst)/1e3:.0f} KB)")

    grib = dst[:-3]
    with gzip.open(dst, "rb") as fin, open(grib, "wb") as fout:
        fout.write(fin.read())
    nc_path = grib.replace("sample_", "ercot_sample_").replace(".grib2", ".nc")
    mx, mean, shape = read_grib_crop_ercot(grib, nc_path)
    print(f"[5] ERCOT 裁剪 {shape}, 最大 {mx:.2f} mm, 均值 {mean:.3f} mm")
    print(f"[6] 已保存: {nc_path}")
