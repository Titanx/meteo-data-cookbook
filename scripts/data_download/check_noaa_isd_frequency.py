"""验证 NOAA ISD 原始数据的实际观测频率"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import urllib.request
import gzip
from datetime import datetime

# NOAA ISD 原始数据访问
# 格式: https://www.ncei.noaa.gov/data/global-hourly/access/{YYYY}/{USAF}{WBAN}.csv
# 例如: 722950-23174 是洛杉矶 LAX (USAF=722950, WBAN=23174)

# 先尝试下载洛杉矶 LAX 机场最近的数据
# LAX: USAF=722950, WBAN=23174
# 芝加哥 O'Hare: USAF=725300, WBAN=14819
# 纽约肯尼迪: USAF=744860, WBAN=94789

test_stations = [
    ("722950", "23174", "KLAX", "洛杉矶"),
    ("725300", "14819", "KORD", "芝加哥"),
    ("744860", "94789", "KJFK", "纽约肯尼迪"),
    # 北京首都 PEK: USAF=545110, WBAN=99999
    ("545110", "99999", "ZBAA", "北京首都"),
]

for year in [2025, 2026]:
    print(f"\n{'='*60}")
    print(f"年份: {year}")
    print(f"{'='*60}")
    
    for usaf, wban, icao, name in test_stations:
        url = f"https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{usaf}{wban}.csv"
        print(f"\n{icao} {name}: {url}")
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=30)
            data = resp.read().decode('utf-8')
            lines = data.strip().split('\n')
            
            if len(lines) < 2:
                print(f"  无数据")
                continue
            
            header = lines[0]
            print(f"  列数: {len(header.split(','))}")
            print(f"  总行数: {len(lines)-1}")
            
            # 查看前5行的时间戳
            print(f"  前5行时间戳:")
            for line in lines[1:6]:
                cols = line.split(',')
                print(f"    {cols[1]}")  # DATE 列
            
            # 查看最后5行
            print(f"  最后5行时间戳:")
            for line in lines[-5:]:
                cols = line.split(',')
                print(f"    {cols[1]}")
            
            # 统计时间间隔
            timestamps = []
            for line in lines[1:]:
                cols = line.split(',')
                if len(cols) > 1:
                    try:
                        ts = datetime.strptime(cols[1], '%Y-%m-%dT%H:%M:%S')
                        timestamps.append(ts)
                    except:
                        pass
            
            if len(timestamps) > 1:
                # 计算时间间隔
                from collections import Counter
                intervals = []
                for i in range(1, min(len(timestamps), 1000)):
                    delta = (timestamps[i] - timestamps[i-1]).total_seconds() / 60  # 分钟
                    intervals.append(int(delta))
                
                interval_counts = Counter(intervals)
                print(f"  时间间隔分布(前1000条): {dict(sorted(interval_counts.items())[:10])}")
                print(f"  最小间隔: {min(intervals)} 分钟")
                print(f"  最常见间隔: {interval_counts.most_common(3)}")
        
        except Exception as e:
            print(f"  错误: {e}")

