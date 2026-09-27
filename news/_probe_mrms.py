"""MRMS 样例读取验证 + ERCOT 区域裁剪 + S3 产品归档现状核查"""
import os
import re
import requests
import numpy as np

out = r"c:\work\meteo\data\mrms\sample_MRMS_MultiSensor_QPE_01H_Pass2_00.00_20230710-090000.grib2"
print("=== 1. cfgrib 读取样例 ===")
import xarray as xr
ds = xr.open_dataset(out, engine="cfgrib")
print("  dims:", dict(ds.sizes))
print("  变量:", list(ds.data_vars))
v = list(ds.data_vars)[0]
lat = ds.latitude.values
lon = ds.longitude.values
print(f"  网格: lat {lat.min():.3f}~{lat.max():.3f} ({len(lat)} 行, dlat={abs(lat[1]-lat[0]):.4f})")
print(f"        lon {lon.min():.3f}~{lon.max():.3f} ({len(lon)} 列, dlon={abs(lon[1]-lon[0]):.4f})")
print(f"  {v} 范围: {float(ds[v].min()):.2f} ~ {float(ds[v].max()):.2f} mm")
print(f"  有效格点: {int((~np.isnan(ds[v].values)).sum())} / {ds[v].size}")

print()
print("=== 2. ERCOT 区域裁剪 (经度 0-360 约定: 253.3~266.6) ===")
mask = (lat >= 25.8) & (lat <= 36.5)
lonm = (lon >= 253.3) & (lon <= 266.6)
sub = ds[v].values[np.ix_(mask, lonm)]
print(f"  ERCOT 子网格: {mask.sum()} x {lonm.sum()} = {mask.sum()*lonm.sum()} 格点 (原 {ds[v].size})")
print(f"  ERCOT 最大 1h 降水: {np.nanmax(sub):.2f} mm, 均值: {np.nanmean(sub):.3f} mm")

dst = r"c:\work\meteo\data\mrms\ercot_sample_20230710_09Z.nc"
sub_ds = ds[v].isel(latitude=np.where(mask)[0], longitude=np.where(lonm)[0])
sub_ds.to_netcdf(dst)
print(f"  已保存 ERCOT 样例: {dst} ({os.path.getsize(dst)/1e6:.2f} MB)")

print()
print("=== 3. noaa-mrms-pds 顶层与 Pass1 归档现状 ===")
r = requests.get("https://noaa-mrms-pds.s3.amazonaws.com/?list-type=2&delimiter=/&max-keys=20", timeout=30)
tops = [d for d in re.findall(r"<Prefix>(.*?)</Prefix>", r.text)]
print("  顶层:", tops)

def latest_date(prod):
    url = f"https://noaa-mrms-pds.s3.amazonaws.com/?list-type=2&prefix={prod}&delimiter=/&max-keys=5"
    rr = requests.get(url, timeout=30)
    tk = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", rr.text)
    # 用 binary search: 先取 max-keys=2 从尾部? S3 不支持尾部; 用 marker 逐步逼近
    dates = [d for d in re.findall(r"<Prefix>(.*?)</Prefix>", rr.text) if re.search(r"/(\d{8})/$", d)]
    n_trunc = bool(tk and re.search(r"<IsTruncated>true</IsTruncated>", rr.text))
    return dates, n_trunc

for prod in ["CONUS/MultiSensor_QPE_01H_Pass1_00.00/",
             "CONUS/RadarOnly_QPE_01H/"]:
    try:
        dates, trunc = latest_date(prod)
        print(f"  {prod}: 前{len(dates)}个日期 {dates[0].split('/')[-2] if dates else '-'}~{dates[-1].split('/')[-2] if dates else '-'}, 截断={trunc}")
    except Exception as e:
        print(f"  {prod}: ERR {str(e)[:100]}")
