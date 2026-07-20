"""验证 Meteostat 美洲数据实时性（修复 station_id）"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import warnings
warnings.filterwarnings('ignore')

from datetime import datetime, timedelta
from meteostat import Daily, Hourly
import time

now = datetime.utcnow()
print(f"当前 UTC 时间: {now:%Y-%m-%d %H:%M:%S}")
print(f"当前北京时间: {now + timedelta(hours=8):%Y-%m-%d %H:%M:%S}")
print()

# 美洲站点 - 使用 stations_metadata.csv 中的正确 station_id
americas_stations = [
    ("72295", "KLAX", "洛杉矶", "美国"),
    ("72530", "KORD", "芝加哥", "美国"),
    ("74486", "KJFK", "纽约肯尼迪", "美国"),
    ("72202", "KMIA", "迈阿密", "美国"),
    ("71624", "CYYZ", "多伦多", "加拿大"),
    ("87576", "SAEZ", "布宜诺斯艾利斯", "阿根廷"),
    ("85574", "SCEL", "圣地亚哥", "智利"),
    ("83778", "SBGR", "圣保罗", "巴西"),
    ("80222", "SKBO", "波哥大", "哥伦比亚"),
    ("84628", "SPJC", "利马", "秘鲁"),
]

start_check = now - timedelta(days=7)
start_check_d = now - timedelta(days=30)

print("=" * 95)
print("美洲机场实时性测试")
print("=" * 95)
print(f"{'站点':<8}{'机场':<10}{'国家':<10}{'最新小时':<20}{'延迟(h)':<10}{'最新日期':<14}{'延迟(d)':<8}")
print("-" * 95)

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

        print(f"{sid:<8}{icao:<10}{country:<10}{latest_h:<20}{delay_h:<10}{latest_d:<14}{delay_d:<8}")
    except Exception as e:
        print(f"{sid:<8}{icao:<10}{country:<10}错误: {str(e)[:40]}")
    time.sleep(0.3)

print()
print(f"测试完成时间: {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC")

