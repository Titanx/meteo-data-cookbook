"""验证 Meteostat 数据的实时性

测试策略：
1. 查询几个不同区域的机场最新数据时间戳
2. 对比当前 UTC 时间，计算延迟
3. 检查日数据和小时数据的实时性差异
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import warnings
warnings.filterwarnings('ignore')

from datetime import datetime, timedelta
from meteostat import Stations, Daily, Hourly
import time

# Meteostat 期望 tz-naive UTC datetime
now = datetime.utcnow()
print(f"当前 UTC 时间: {now:%Y-%m-%d %H:%M:%S}")
print(f"当前北京时间: {now + timedelta(hours=8):%Y-%m-%d %H:%M:%S}")
print()

# 测试机场 - 使用之前已下载的站点ID
test_station_ids = [
    ("54511",  "ZBAA", "北京", "中国"),
    ("58367",  "ZSSS", "上海虹桥", "中国"),
    ("58457",  "ZSHC", "杭州", "中国"),
    ("59287",  "ZGGG", "广州", "中国"),
    ("47671",  "RJTT", "东京羽田", "日本"),
    ("47113",  "RKSI", "首尔仁川", "韩国"),
    ("48900",  "VVTS", "胡志明", "越南"),
    ("48429",  "VTBS", "曼谷", "泰国"),
]

print("=" * 80)
print("测试1: 小时数据实时性（查询最近7天）")
print("=" * 80)
print(f"{'站点':<8}{'机场':<12}{'国家':<8}{'最新时间':<22}{'延迟(小时)':<12}{'记录数':<8}")
print("-" * 80)

start_check = now - timedelta(days=7)

for sid, icao, name, country in test_station_ids:
    try:
        df = Hourly(sid, start_check, now).fetch()
        if len(df) > 0:
            latest = df.index.max()
            # df.index 可能是 tz-naive 或 tz-aware，统一处理
            if latest.tzinfo is not None:
                latest = latest.tz_localize(None)
            delay_hours = (now - latest).total_seconds() / 3600
            print(f"{sid:<8}{icao:<12}{country:<8}{latest.strftime('%Y-%m-%d %H:%M'):<22}{delay_hours:<12.1f}{len(df):<8}")
        else:
            print(f"{sid:<8}{icao:<12}{country:<8}{'无数据':<22}{'-':<12}{0:<8}")
    except Exception as e:
        print(f"{sid:<8}{icao:<12}{country:<8}{'错误: ' + str(e)[:30]:<22}")
    time.sleep(0.3)

print()
print("=" * 80)
print("测试2: 日数据实时性（查询最近30天）")
print("=" * 80)
print(f"{'站点':<8}{'机场':<12}{'国家':<8}{'最新日期':<15}{'延迟(天)':<10}{'记录数':<8}")
print("-" * 80)

start_check_d = now - timedelta(days=30)

for sid, icao, name, country in test_station_ids:
    try:
        df = Daily(sid, start_check_d, now).fetch()
        if len(df) > 0:
            latest = df.index.max()
            if latest.tzinfo is not None:
                latest = latest.tz_localize(None)
            delay_days = (now.date() - latest.date()).days
            print(f"{sid:<8}{icao:<12}{country:<8}{latest.strftime('%Y-%m-%d'):<15}{delay_days:<10}{len(df):<8}")
        else:
            print(f"{sid:<8}{icao:<12}{country:<8}{'无数据':<15}{'-':<10}{0:<8}")
    except Exception as e:
        print(f"{sid:<8}{icao:<12}{country:<8}{'错误: ' + str(e)[:30]:<15}")
    time.sleep(0.3)

print()
print("=" * 80)
print("测试3: 美洲机场实时性")
print("=" * 80)

# 美洲站点 - 使用之前下载时映射的 station_id
americas_stations = [
    ("722950", "KLAX", "洛杉矶", "美国"),
    ("725300", "KORD", "芝加哥", "美国"),
    ("744860", "KJFK", "纽约肯尼迪", "美国"),
    ("722930", "KMIA", "迈阿密", "美国"),
    ("716240", "CYYZ", "多伦多", "加拿大"),
    ("875820", "SAEZ", "布宜诺斯艾利斯", "阿根廷"),
    ("855740", "SCEL", "圣地亚哥", "智利"),
]

print(f"{'站点':<10}{'机场':<10}{'国家':<8}{'最新小时':<22}{'延迟(h)':<10}{'最新日期':<12}{'延迟(d)':<8}")
print("-" * 90)

for sid, icao, name, country in americas_stations:
    try:
        # 小时数据
        df_h = Hourly(sid, start_check, now).fetch()
        latest_h = "无数据"
        delay_h = "-"
        if len(df_h) > 0:
            latest = df_h.index.max()
            if latest.tzinfo is not None:
                latest = latest.tz_localize(None)
            latest_h = latest.strftime('%Y-%m-%d %H:%M')
            delay_h = f"{(now - latest).total_seconds() / 3600:.1f}"

        # 日数据
        df_d = Daily(sid, start_check_d, now).fetch()
        latest_d = "无数据"
        delay_d = "-"
        if len(df_d) > 0:
            latest = df_d.index.max()
            if latest.tzinfo is not None:
                latest = latest.tz_localize(None)
            latest_d = latest.strftime('%Y-%m-%d')
            delay_d = f"{(now.date() - latest.date()).days}"

        print(f"{sid:<10}{icao:<10}{country:<8}{latest_h:<22}{delay_h:<10}{latest_d:<12}{delay_d:<8}")
    except Exception as e:
        print(f"{sid:<10}{icao:<10}{country:<8}错误: {str(e)[:40]}")
    time.sleep(0.3)

print()
print(f"测试完成时间: {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC")

