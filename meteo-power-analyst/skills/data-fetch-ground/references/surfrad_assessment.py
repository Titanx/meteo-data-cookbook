"""SURFRAD 数据量评估 + 实时性测试

1. 评估 2025-2026 全部 7 站点下载量
2. 测试实时性（realtime 目录最新文件时间）
3. 测试历史数据最早可获取时间
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import urllib.request
import re
import os
from datetime import datetime, timedelta

BASE_URL = "https://gml.noaa.gov/aftp/data/radiation/surfrad/"
STATIONS = ['bon','dra','fpk','gwn','psu','sxf','tbl']

def list_dir(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        items = re.findall(r'href="([^"]+)"', html)
        return [i for i in items if not i.startswith('?') and i not in ('..', '.') and not i.startswith('http') and not i.startswith('#')]
    except Exception as e:
        return [f"ERROR: {e}"]

def get_file_size(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=15) as resp:
            return int(resp.headers.get('Content-Length', 0))
    except:
        return 0

print("=" * 70)
print("SURFRAD 数据量评估 + 实时性测试")
print("=" * 70)
print(f"当前 UTC: {datetime.utcnow():%Y-%m-%d %H:%M:%S}")

# === 1. 检查各站点年份目录 ===
print("\n--- 1. 各站点可用年份 ---")
for sid in STATIONS:
    items = list_dir(f"{BASE_URL}{sid}/")
    years = sorted([i.rstrip('/') for i in items if i.rstrip('/').isdigit()])
    print(f"  {sid}: {years}")

# === 2. 2025 + 2026 文件数统计（每站）===
print("\n--- 2. 2025-2026 文件数统计 ---")
total_files = 0
total_size_bytes = 0
for sid in STATIONS:
    for year in ['2025', '2026']:
        items = list_dir(f"{BASE_URL}{sid}/{year}/")
        dat_files = [f for f in items if f.endswith('.dat')]
        if dat_files:
            # 采样第一个文件大小估算
            sample_size = get_file_size(f"{BASE_URL}{sid}/{year}/{dat_files[0]}")
            est_size = sample_size * len(dat_files)
            total_files += len(dat_files)
            total_size_bytes += est_size
            print(f"  {sid}/{year}/: {len(dat_files)} 文件, 单文件~{sample_size/1024:.0f}KB, 估算 {est_size/1024/1024:.1f}MB")

print(f"\n  合计: {total_files} 文件, 估算 {total_size_bytes/1024/1024:.1f} MB ({total_size_bytes/1024/1024/1024:.2f} GB)")

# === 3. 实时性测试：realtime 目录最新文件 ===
print("\n--- 3. 实时性测试 ---")
now = datetime.utcnow()
print(f"  当前 UTC: {now:%Y-%m-%d %H:%M:%S}")
for sid in STATIONS:
    items = list_dir(f"{BASE_URL}realtime/{sid}/")
    dat_files = sorted([f for f in items if f.endswith('.dat')])
    if dat_files:
        latest = dat_files[-1]
        # 文件名格式 {sid}{YY}{DOY}.dat，解析日期
        try:
            yy = int(latest[3:5])
            doy = int(latest[5:8])
            year = 2000 + yy
            file_date = datetime(year, 1, 1) + timedelta(days=doy - 1)
            # 文件修改时间
            size = get_file_size(f"{BASE_URL}realtime/{sid}/{latest}")
            delay_hours = (now - file_date).total_seconds() / 3600
            print(f"  {sid}: 最新 {latest} (日期 {file_date:%Y-%m-%d}), 大小 {size/1024:.0f}KB, 延迟 ~{delay_hours:.1f}h")
        except Exception as e:
            print(f"  {sid}: 解析失败 {latest} - {e}")
    else:
        print(f"  {sid}: realtime 无文件")

# === 4. 历史目录最新文件（对比 realtime）===
print("\n--- 4. 历史目录最新文件 ---")
for sid in STATIONS:
    for year in ['2026', '2025']:
        items = list_dir(f"{BASE_URL}{sid}/{year}/")
        dat_files = sorted([f for f in items if f.endswith('.dat')])
        if dat_files:
            latest = dat_files[-1]
            yy = int(latest[3:5])
            doy = int(latest[5:8])
            year_actual = 2000 + yy
            file_date = datetime(year_actual, 1, 1) + timedelta(days=doy - 1)
            delay_days = (now.date() - file_date.date()).days
            print(f"  {sid}/{year}/: 最新 {latest} = {file_date:%Y-%m-%d}, 延迟 {delay_days} 天")
            break

# === 5. 历史数据起始时间（每站最早年份的最早文件）===
print("\n--- 5. 历史数据起始时间 ---")
for sid in STATIONS:
    items = list_dir(f"{BASE_URL}{sid}/")
    years = sorted([i.rstrip('/') for i in items if i.rstrip('/').isdigit()])
    if years:
        earliest_year = years[0]
        files = list_dir(f"{BASE_URL}{sid}/{earliest_year}/")
        dat_files = sorted([f for f in files if f.endswith('.dat')])
        if dat_files:
            first = dat_files[0]
            try:
                yy = int(first[3:5])
                doy = int(first[5:8])
                year_actual = 2000 + yy if yy < 50 else 1900 + yy
                file_date = datetime(year_actual, 1, 1) + timedelta(days=doy - 1)
                print(f"  {sid}: 起始 {first} = {file_date:%Y-%m-%d} (年份目录: {earliest_year})")
            except:
                print(f"  {sid}: 起始 {first}")

print("\n完成!")

