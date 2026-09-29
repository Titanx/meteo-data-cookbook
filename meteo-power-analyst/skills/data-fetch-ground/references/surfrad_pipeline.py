"""SURFRAD 完整下载 + 解析 + 可视化

下载 7 个站点的最近 7 天数据，解析为 DataFrame，生成辐照日变化图
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import urllib.request
import os
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, HourLocator

# 站点信息
STATIONS = {
    'bon': {'name': 'Bondville, IL', 'lat': 40.05, 'lon': -88.37, 'tz': 'CST/CDT'},
    'dra': {'name': 'Desert Rock, NV', 'lat': 36.63, 'lon': -116.02, 'tz': 'PST/PDT'},
    'fpk': {'name': 'Fort Peck, MT', 'lat': 48.31, 'lon': -105.10, 'tz': 'MST/MDT'},
    'gwn': {'name': 'Goodwin Creek, MS', 'lat': 34.25, 'lon': -89.87, 'tz': 'CST/CDT'},
    'psu': {'name': 'Penn State, PA', 'lat': 40.72, 'lon': -77.93, 'tz': 'EST/EDT'},
    'sxf': {'name': 'Sioux Falls, SD', 'lat': 43.73, 'lon': -96.62, 'tz': 'CST/CDT'},
    'tbl': {'name': 'Table Mountain, CO', 'lat': 40.13, 'lon': -105.24, 'tz': 'MST/MDT'},
}

BASE_URL = "https://gml.noaa.gov/aftp/data/radiation/surfrad/"
OUT_DIR = r"c:\work\meteo\data\surfrad"
os.makedirs(OUT_DIR, exist_ok=True)

# 列名定义（48 列）
COLUMNS = ['year','jday','month','day','hour','minute','dec_hour','sza',
           'ghi','ghi_qc','up_solar','up_solar_qc','dni','dni_qc','dhi','dhi_qc',
           'dw_ir','dw_ir_qc','dw_ir_case','dw_ir_case_qc','dw_ir_dome','dw_ir_dome_qc',
           'uw_ir','uw_ir_qc','uw_ir_case','uw_ir_case_qc','uw_ir_dome','uw_ir_dome_qc',
           'uvb','uvb_qc','par','par_qc','net_solar','net_solar_qc',
           'net_ir','net_ir_qc','net_total','net_total_qc',
           'temp','temp_qc','rh','rh_qc','windspd','windspd_qc',
           'winddir','winddir_qc','pressure','pressure_qc']

def doy_to_date(year, doy):
    return datetime(year, 1, 1) + timedelta(days=doy - 1)

def download_file(station, year, doy):
    """下载单个 DOY 文件，先从历史目录，404 则试 realtime"""
    fname = f"{station}{str(year)[-2:]}{doy:03d}.dat"
    # 先试历史目录
    url = f"{BASE_URL}{station}/{year}/{fname}"
    dst = os.path.join(OUT_DIR, fname)
    if os.path.exists(dst):
        return dst, 'cached'
    try:
        urllib.request.urlretrieve(url, dst)
        return dst, 'historical'
    except:
        pass
    # 试 realtime
    url = f"{BASE_URL}realtime/{station}/{fname}"
    try:
        urllib.request.urlretrieve(url, dst)
        return dst, 'realtime'
    except:
        return None, 'failed'

def parse_file(filepath):
    """解析 SURFRAD .dat 文件为 DataFrame"""
    with open(filepath, 'r', errors='ignore') as f:
        lines = f.readlines()
    # 跳过前 2 行头部
    data_lines = lines[2:]
    records = []
    skipped = 0
    for line in data_lines:
        tokens = line.split()
        if len(tokens) == 48:
            try:
                vals = [float(t) for t in tokens]
                records.append(vals)
            except:
                skipped += 1
        else:
            skipped += 1
    if skipped > 0:
        # 检查异常行的列数
        sample_bad = [l for l in data_lines if len(l.split()) != 48][:1]
        if sample_bad:
            print(f"    [警告] {os.path.basename(filepath)}: 跳过 {skipped} 行, 样本列数={len(sample_bad[0].split())}")
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records, columns=COLUMNS)
    # 构造 datetime（用字符串拼接，最兼容）
    dt_str = (df['year'].astype(int).astype(str) + '-' + 
              df['month'].astype(int).astype(str).str.zfill(2) + '-' +
              df['day'].astype(int).astype(str).str.zfill(2) + ' ' +
              df['hour'].astype(int).astype(str).str.zfill(2) + ':' +
              df['minute'].astype(int).astype(str).str.zfill(2))
    df['datetime'] = pd.to_datetime(dt_str, format='%Y-%m-%d %H:%M', errors='coerce')
    return df

# === 主流程 ===
print("=" * 70)
print("SURFRAD 下载 + 解析 + 可视化")
print("=" * 70)

today = datetime.utcnow()
# 下载最近 7 天（DOY）
target_doys = []
for i in range(7):
    d = today - timedelta(days=i)
    target_doys.append(d.timetuple().tm_yday)

print(f"\n当前 UTC: {today:%Y-%m-%d %H:%M}")
print(f"目标 DOY: {target_doys} (最近 7 天)")
print(f"目标年份: {today.year}")

all_data = {}
print(f"\n--- 下载 7 站点 × 7 天 ---")
for sid, info in STATIONS.items():
    station_data = []
    for doy in target_doys:
        filepath, status = download_file(sid, today.year, doy)
        if filepath:
            df = parse_file(filepath)
            if len(df) > 0:
                df['station'] = sid
                df['station_name'] = info['name']
                station_data.append(df)
    if station_data:
        all_data[sid] = pd.concat(station_data, ignore_index=True)
        print(f"  {sid} ({info['name']:<25}): {len(all_data[sid])} 条记录")
    else:
        print(f"  {sid} ({info['name']:<25}): 失败或无数据")

# === 数据质量检查 ===
print(f"\n--- 数据质量检查 ---")
for sid, df in all_data.items():
    # 检查 GHI 范围
    ghi = df['ghi']
    # 缺失值 -9999.9 设为 NaN 用于统计
    ghi_clean = ghi.where(ghi > -1000)
    print(f"  {sid}: GHI min={ghi_clean.min():.1f} max={ghi_clean.max():.1f} mean={ghi_clean.mean():.1f} W/m², "
          f"DNI max={df['dni'].where(df['dni']>-1000).max():.1f}, DHI max={df['dhi'].where(df['dhi']>-1000).max():.1f}")

# 缺失值处理：-9999.9 → NaN
for df in all_data.values():
    for col in ['ghi','dni','dhi','up_solar','dw_ir','uw_ir','temp','rh','windspd','pressure']:
        df[col] = df[col].where(df[col] > -1000)

# === 可视化：7 站点 GHI 日变化 ===
print(f"\n--- 生成图表 ---")
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

fig, axes = plt.subplots(2, 1, figsize=(14, 10))

# 图 1: 7 站点昨天 GHI 日变化（昨天数据完整）
ax1 = axes[0]
yesterday_doy = target_doys[1]  # DOY 200 = 昨天
yesterday_date = doy_to_date(today.year, yesterday_doy)
colors = plt.cm.tab10(np.linspace(0, 1, 7))
for (sid, df), color in zip(all_data.items(), colors):
    day_df = df[df['jday'] == yesterday_doy].copy()
    if len(day_df) > 0:
        local_hour = day_df['datetime'] + pd.Timedelta(hours=-6)  # 转 CST 近似
        ax1.plot(local_hour, day_df['ghi'].values, label=f"{sid} ({STATIONS[sid]['name']})", 
                 color=color, linewidth=0.8, alpha=0.8)
ax1.set_xlabel('时间 (CST 近似, UTC-6)')
ax1.set_ylabel('GHI (W/m2)')
ax1.set_title(f'SURFRAD 7 站点 GHI 日变化 - {yesterday_date:%Y-%m-%d}')
ax1.legend(loc='upper left', fontsize=8)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(DateFormatter('%H:%M'))

# 图 2: Bondville 7 天 GHI 日变化（按小时对齐）
ax2 = axes[1]
if 'bon' in all_data:
    df = all_data['bon']
    cmap = plt.cm.viridis(np.linspace(0, 1, len(target_doys)))
    for i, doy in enumerate(target_doys):
        day_df = df[df['jday'] == doy].copy()
        if len(day_df) > 0:
            date = doy_to_date(today.year, doy)
            # 用本地小时作为 x 轴
            day_df = day_df.copy()
            day_df['local_hour'] = day_df['dec_hour'] - 6  # UTC→CST
            day_df = day_df.sort_values('local_hour')
            ax2.plot(day_df['local_hour'], day_df['ghi'], 
                    label=f"{date:%m-%d} DOY{doy}", color=cmap[i], alpha=0.8, linewidth=0.9)
    ax2.set_xlabel('本地时间 (CST, UTC-6)')
    ax2.set_ylabel('GHI (W/m2)')
    ax2.set_title('Bondville 站最近 7 天 GHI 日变化')
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(-2, 24)

plt.tight_layout()
chart_path = os.path.join(OUT_DIR, 'surfrad_ghi_analysis.png')
plt.savefig(chart_path, dpi=120, bbox_inches='tight')
print(f"  图表保存: {chart_path}")

# === 保存解析后的 CSV 样本 ===
if 'bon' in all_data:
    sample = all_data['bon'][['datetime','sza','ghi','dni','dhi','dw_ir','temp','rh','windspd','pressure']].copy()
    sample_csv = os.path.join(OUT_DIR, 'bon_parsed_sample.csv')
    sample.to_csv(sample_csv, index=False)
    print(f"  解析样本: {sample_csv} ({len(sample)} 行)")
    print(f"\n--- Bondville 昨天 GHI 统计 ---")
    yest_bon = all_data['bon'][all_data['bon']['jday'] == yesterday_doy]
    if len(yest_bon) > 0:
        print(f"  日期: {yesterday_date:%Y-%m-%d} (DOY {yesterday_doy})")
        print(f"  记录数: {len(yest_bon)}")
        print(f"  GHI: min={yest_bon['ghi'].min():.1f} max={yest_bon['ghi'].max():.1f} mean={yest_bon['ghi'].mean():.1f} W/m2")
        print(f"  DNI: max={yest_bon['dni'].max():.1f} W/m2")
        print(f"  DHI: max={yest_bon['dhi'].max():.1f} W/m2")
        print(f"  气温: {yest_bon['temp'].min():.1f}~{yest_bon['temp'].max():.1f} C")
        print(f"  气压: {yest_bon['pressure'].mean():.1f} hPa")

print(f"\n完成! 数据目录: {OUT_DIR}")

