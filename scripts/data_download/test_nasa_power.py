"""NASA POWER API 实测 + 与 SURFRAD 实测对比

1. 测试 API 访问（免 key）
2. 下载 Bondville 站点的 GHI/温度/风速数据
3. 与 SURFRAD 实测数据对比验证精度
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import requests
import pandas as pd
import numpy as np
from datetime import datetime, date
from io import StringIO
import os
import urllib.request as ur

print("=" * 70)
print("NASA POWER API 实测验证")
print("=" * 70)

# Bondville, IL 站点（与 SURFRAD 对比）
LAT, LON = 40.05, -88.37
# POWER 辐射延迟 3-4 个月，用 2025 年 7 月数据确保辐射可用
START = "20250701"
END = "20250710"

# === 1. 测试 hourly API ===
print("\n--- 1. Hourly API 测试（Bondville 2025-07-01~10）---")
params = "T2M,ALLSKY_SFC_SW_DWN,WS10M,RH2M,PS,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF"
url = (f"https://power.larc.nasa.gov/api/temporal/hourly/point?"
       f"parameters={params}&community=RE&longitude={LON}&latitude={LAT}"
       f"&start={START}&end={END}&format=CSV&header=true&time-standard=UTC")

print(f"  URL: {url[:100]}...")
resp = requests.get(url, timeout=60)
print(f"  HTTP {resp.status_code}, 内容长度 {len(resp.text)} 字符")

df_power = pd.DataFrame()
if resp.status_code == 200:
    lines = resp.text.split('\n')
    data_start = 0
    for i, line in enumerate(lines):
        if '-END HEADER-' in line:
            data_start = i + 1
            break
    print(f"  Header 行数: {data_start}")
    csv_data = '\n'.join(lines[data_start:])
    df_power = pd.read_csv(StringIO(csv_data))
    print(f"  数据行数: {len(df_power)}")
    print(f"  列名: {list(df_power.columns)}")
    ghi = df_power['ALLSKY_SFC_SW_DWN']
    print(f"  GHI 范围: {ghi.min():.2f} ~ {ghi.max():.2f} Wh/m²")

# === 2. 下载 SURFRAD 数据用于对比 ===
print("\n--- 2. 下载 SURFRAD 数据（2025-07-01~10）---")
surfrad_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'surfrad')
os.makedirs(surfrad_dir, exist_ok=True)

for doy in range(182, 192):
    fname = f"bon25{doy:03d}.dat"
    dst = os.path.join(surfrad_dir, fname)
    if not os.path.exists(dst):
        for path_type in ['bon/2025', 'bon/2026', 'realtime/bon']:
            url_s = f"https://gml.noaa.gov/aftp/data/radiation/surfrad/{path_type}/{fname}"
            try:
                ur.urlretrieve(url_s, dst)
                print(f"  下载 {fname} OK")
                break
            except:
                pass

# === 3. 解析 SURFRAD 并对比 ===
print("\n--- 3. GHI 对比（POWER vs SURFRAD 实测）---")
COLUMNS = ['year','jday','month','day','hour','minute','dec_hour','sza',
           'ghi','ghi_qc','up_solar','up_solar_qc','dni','dni_qc','dhi','dhi_qc',
           'dw_ir','dw_ir_qc','dw_ir_case','dw_ir_case_qc','dw_ir_dome','dw_ir_dome_qc',
           'uw_ir','uw_ir_qc','uw_ir_case','uw_ir_case_qc','uw_ir_dome','uw_ir_dome_qc',
           'uvb','uvb_qc','par','par_qc','net_solar','net_solar_qc',
           'net_ir','net_ir_qc','net_total','net_total_qc',
           'temp','temp_qc','rh','rh_qc','windspd','windspd_qc',
           'winddir','winddir_qc','pressure','pressure_qc']

surfrad_files = sorted([f for f in os.listdir(surfrad_dir) if f.startswith('bon25') and f.endswith('.dat')])
records = []
for fname in surfrad_files:
    with open(os.path.join(surfrad_dir, fname), 'r', errors='ignore') as f:
        for line in f.readlines()[2:]:
            tokens = line.split()
            if len(tokens) == 48:
                try:
                    records.append([float(t) for t in tokens])
                except:
                    pass

df_surf = pd.DataFrame(records, columns=COLUMNS)
dt_str = (df_surf['year'].astype(int).astype(str) + '-' +
          df_surf['month'].astype(int).astype(str).str.zfill(2) + '-' +
          df_surf['day'].astype(int).astype(str).str.zfill(2) + ' ' +
          df_surf['hour'].astype(int).astype(str).str.zfill(2) + ':' +
          df_surf['minute'].astype(int).astype(str).str.zfill(2))
df_surf['datetime'] = pd.to_datetime(dt_str, format='%Y-%m-%d %H:%M')
for col in ['ghi','dni','dhi','temp','windspd','pressure']:
    df_surf[col] = df_surf[col].where(df_surf[col] > -1000)

# 按小时聚合
df_surf['datetime_floor'] = df_surf['datetime'].dt.floor('h')
hourly_surf = df_surf.groupby('datetime_floor').agg({
    'ghi':'mean','dni':'mean','dhi':'mean','temp':'mean','windspd':'mean','pressure':'mean'
}).reset_index().rename(columns={'datetime_floor':'datetime'})

if len(df_power) > 0:
    df_power['datetime'] = pd.to_datetime(
        df_power['YEAR'].astype(str) + '-' +
        df_power['MO'].astype(str).str.zfill(2) + '-' +
        df_power['DY'].astype(str).str.zfill(2) + ' ' +
        df_power['HR'].astype(str).str.zfill(2) + ':00')
    for col in ['ALLSKY_SFC_SW_DWN','T2M','WS10M']:
        df_power[col] = df_power[col].where(df_power[col] > -900)

    df_power_sel = df_power[['datetime','ALLSKY_SFC_SW_DWN','T2M','WS10M']].copy()
    df_power_sel.columns = ['datetime','power_ghi','power_temp','power_wind']
    df_power_sel['power_ghi_wm2'] = df_power_sel['power_ghi']  # Wh/m² per hour = W/m²

    merged = pd.merge(hourly_surf, df_power_sel, on='datetime', how='inner')
    print(f"  匹配小时数: {len(merged)}")
    if len(merged) > 0:
        merged['ghi_error'] = merged['power_ghi_wm2'] - merged['ghi']
        mae = merged['ghi_error'].abs().mean()
        rmse = np.sqrt((merged['ghi_error']**2).mean())
        bias = merged['ghi_error'].mean()
        print(f"  GHI SURFRAD: mean={merged['ghi'].mean():.1f} max={merged['ghi'].max():.1f} W/m²")
        print(f"  GHI POWER:   mean={merged['power_ghi_wm2'].mean():.1f} max={merged['power_ghi_wm2'].max():.1f} W/m²")
        print(f"  MAE={mae:.1f} RMSE={rmse:.1f} BIAS={bias:.1f} W/m²")
        temp_valid = merged.dropna(subset=['temp','power_temp'])
        if len(temp_valid) > 0:
            temp_error = temp_valid['power_temp'] - temp_valid['temp']
            print(f"  温度 MAE={temp_error.abs().mean():.1f}°C")

# === 4. Daily API ===
print("\n--- 4. Daily API 测试 ---")
url_daily = (f"https://power.larc.nasa.gov/api/temporal/daily/point?"
             f"parameters=T2M,T2M_MAX,T2M_MIN,ALLSKY_SFC_SW_DWN,PRECTOTCORR,WS10M&"
             f"community=RE&longitude={LON}&latitude={LAT}"
             f"&start={START}&end={END}&format=CSV&header=false")
resp_d = requests.get(url_daily, timeout=30)
if resp_d.status_code == 200:
    df_daily = pd.read_csv(StringIO(resp_d.text))
    print(f"  日数据: {len(df_daily)} 行")
    print(df_daily.to_string())

print("\n完成!")
