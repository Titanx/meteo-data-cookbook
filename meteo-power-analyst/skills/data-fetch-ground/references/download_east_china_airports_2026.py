"""
华东地区机场气象数据下载脚本（2026年至今）

数据源: Meteostat (聚合 NOAA ISD + 各国气象服务)
覆盖机场: 上海浦东/虹桥、杭州、南京、青岛、厦门、合肥、济南、无锡、温州、福州、宁波
时间范围: 2026-01-01 ~ 2026-07-19 (今天)

输出:
- 每个机场的日数据 CSV (温度/降水/风/气压)
- 每个机场的小时数据 CSV (温度/露点/湿度/风/气压/天气码)
- 站点元数据 CSV
- 汇总报告
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime
from pathlib import Path
import time
import pandas as pd

try:
    from meteostat import Stations, Daily, Hourly, Point
except ImportError:
    print("请先安装: pip install meteostat")
    raise

# 华东地区主要机场 (ICAO代码、名称、纬度、经度、海拔m)
EAST_CHINA_AIRPORTS = [
    ("ZSPD", "上海浦东",   31.1443, 121.8083, 4),
    ("ZSSS", "上海虹桥",   31.1979, 121.3361, 3),
    ("ZSHC", "杭州萧山",   30.2294, 120.4344, 7),
    ("ZSNJ", "南京禄口",   31.7420, 118.8622, 14),
    ("ZSQD", "青岛流亭",   36.2622, 120.3744, 10),
    ("ZSAM", "厦门高崎",   24.5440, 118.1270, 18),
    ("ZSOF", "合肥新桥",   31.7494, 117.3094, 31),
    ("ZSJN", "济南遥墙",   36.3611, 117.2131, 23),
    ("ZSWX", "无锡硕放",   31.4939, 120.4297, 5),
    ("ZSWZ", "温州龙湾",   27.9122, 120.8528, 9),
    ("ZSFZ", "福州长乐",   25.9451, 119.6623, 14),
    ("ZSNB", "宁波栎社",   29.8267, 121.4589, 4),
]

# 时间范围: 2026-01-01 至今
START = datetime(2026, 1, 1)
END   = datetime(2026, 7, 19, 23, 59)

# 输出目录
OUTPUT_DIR = Path("c:/work/meteo/data/meteostat/east_china_2026")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(msg, flush=True)


def find_nearest_station(lat, lon, airport_name):
    """查询机场坐标附近最近的气象站"""
    try:
        stations = Stations()
        stations = stations.nearby(lat, lon, radius=30000)  # 30km
        df = stations.fetch()
        if len(df) == 0:
            # 扩大半径到 50km
            stations = Stations()
            stations = stations.nearby(lat, lon, radius=50000)
            df = stations.fetch()
        if len(df) > 0:
            # 取最近的一个
            df = df.head(1)
            sid = df.index[0]
            row = df.iloc[0]
            return sid, row
        return None, None
    except Exception as e:
        log(f"  查询站点失败: {e}")
        return None, None


def download_daily(station_id, airport_code, airport_name):
    """下载日数据"""
    try:
        data = Daily(station_id, START, END)
        df = data.fetch()
        if len(df) > 0:
            out_path = OUTPUT_DIR / f"daily_{airport_code}_{station_id}.csv"
            df.to_csv(out_path, encoding='utf-8-sig')
            log(f"  日数据: {len(df)} 条 → {out_path.name}")
            return df
        else:
            log(f"  日数据: 无数据")
            return pd.DataFrame()
    except Exception as e:
        log(f"  日数据失败: {e}")
        return pd.DataFrame()


def download_hourly(station_id, airport_code, airport_name):
    """下载小时数据"""
    try:
        data = Hourly(station_id, START, END)
        df = data.fetch()
        if len(df) > 0:
            out_path = OUTPUT_DIR / f"hourly_{airport_code}_{station_id}.csv"
            df.to_csv(out_path, encoding='utf-8-sig')
            log(f"  小时数据: {len(df)} 条 → {out_path.name}")
            return df
        else:
            log(f"  小时数据: 无数据")
            return pd.DataFrame()
    except Exception as e:
        log(f"  小时数据失败: {e}")
        return pd.DataFrame()


def main():
    log("=" * 70)
    log("华东地区机场气象数据下载 (2026-01-01 ~ 2026-07-19)")
    log("=" * 70)
    log(f"机场数: {len(EAST_CHINA_AIRPORTS)}")
    log(f"时间范围: {START:%Y-%m-%d} ~ {END:%Y-%m-%d}")
    log(f"输出目录: {OUTPUT_DIR}")
    log("")

    station_records = []
    summary_records = []

    for i, (icao, name, lat, lon, alt) in enumerate(EAST_CHINA_AIRPORTS, 1):
        log(f"\n[{i}/{len(EAST_CHINA_AIRPORTS)}] {icao} {name} ({lat:.4f}°N, {lon:.4f}°E)")

        # 查找最近站点
        sid, station_row = find_nearest_station(lat, lon, name)
        if sid is None:
            log(f"  未找到附近站点，跳过")
            summary_records.append({
                'icao': icao, 'name': name, 'lat': lat, 'lon': lon,
                'station_id': None, 'station_name': None,
                'daily_count': 0, 'hourly_count': 0, 'status': 'no_station'
            })
            continue

        sname = station_row.get('name', 'unknown')
        slat  = station_row.get('latitude', None)
        slon  = station_row.get('longitude', None)
        salt  = station_row.get('elevation', None)
        dist  = station_row.get('distance', None)
        log(f"  站点: ID={sid}, 名称={sname}, 距离={dist:.1f}km" if dist else f"  站点: ID={sid}, 名称={sname}")
        log(f"  坐标: {slat}°N, {slon}°E, 海拔={salt}m")

        station_records.append({
            'airport_icao': icao, 'airport_name': name,
            'airport_lat': lat, 'airport_lon': lon, 'airport_alt': alt,
            'station_id': sid, 'station_name': sname,
            'station_lat': slat, 'station_lon': slon, 'station_alt': salt,
            'distance_km': dist
        })

        # 下载日数据
        daily_df = download_daily(sid, icao, name)
        time.sleep(0.5)

        # 下载小时数据
        hourly_df = download_hourly(sid, icao, name)
        time.sleep(0.5)

        # 数据预览
        if len(daily_df) > 0:
            log(f"  日数据预览:")
            log(f"    日期范围: {daily_df.index[0]} ~ {daily_df.index[-1]}")
            log(f"    温度: tavg={daily_df['tavg'].mean():.1f}°C (均值), "
                f"tmax={daily_df['tmax'].max():.1f}°C (最高), "
                f"tmin={daily_df['tmin'].min():.1f}°C (最低)")
            if 'prcp' in daily_df.columns:
                log(f"    降水: 总量={daily_df['prcp'].sum():.1f}mm, "
                    f"降水日数={int((daily_df['prcp'] > 0).sum())}天")

        if len(hourly_df) > 0:
            log(f"  小时数据预览:")
            log(f"    时间范围: {hourly_df.index[0]} ~ {hourly_df.index[-1]}")
            valid_temp = hourly_df['temp'].dropna()
            if len(valid_temp) > 0:
                log(f"    温度: {valid_temp.min():.1f}~{valid_temp.max():.1f}°C, 均值={valid_temp.mean():.1f}°C")
            valid_rhum = hourly_df['rhum'].dropna() if 'rhum' in hourly_df.columns else pd.Series()
            if len(valid_rhum) > 0:
                log(f"    湿度: {valid_rhum.min():.0f}%~{valid_rhum.max():.0f}%, 均值={valid_rhum.mean():.0f}%")

        summary_records.append({
            'icao': icao, 'name': name, 'lat': lat, 'lon': lon,
            'station_id': sid, 'station_name': sname,
            'daily_count': len(daily_df), 'hourly_count': len(hourly_df),
            'status': 'ok' if len(daily_df) > 0 or len(hourly_df) > 0 else 'no_data'
        })

    # 保存站点元数据
    if station_records:
        stations_df = pd.DataFrame(station_records)
        stations_path = OUTPUT_DIR / "stations_metadata.csv"
        stations_df.to_csv(stations_path, index=False, encoding='utf-8-sig')
        log(f"\n站点元数据保存: {stations_path}")

    # 保存汇总
    summary_df = pd.DataFrame(summary_records)
    summary_path = OUTPUT_DIR / "download_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')

    # 打印汇总
    log("\n" + "=" * 70)
    log("下载汇总")
    log("=" * 70)
    log(f"{'ICAO':<6} {'机场':<10} {'站点ID':<10} {'日数据':>8} {'小时数据':>10} {'状态':<10}")
    log("-" * 70)
    for r in summary_records:
        log(f"{r['icao']:<6} {r['name']:<10} {str(r['station_id']):<10} "
            f"{r['daily_count']:>8} {r['hourly_count']:>10} {r['status']:<10}")

    total_daily = sum(r['daily_count'] for r in summary_records)
    total_hourly = sum(r['hourly_count'] for r in summary_records)
    log("-" * 70)
    log(f"{'合计':<28} {total_daily:>8} {total_hourly:>10}")
    log(f"\n输出目录: {OUTPUT_DIR}")
    log(f"汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
