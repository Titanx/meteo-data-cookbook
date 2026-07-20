"""
全中国机场气象数据下载脚本（2026年至今）

覆盖8大区域的主要机场:
- 华北: 北京首都/大兴、天津、石家庄、太原、呼和浩特
- 东北: 沈阳、大连、长春、哈尔滨
- 华东: 上海浦东/虹桥、杭州、南京、青岛、厦门、合肥、济南、无锡、温州、福州、宁波
- 华中: 武汉、长沙、郑州、南昌
- 华南: 广州、深圳、珠海、海口、三亚、南宁、桂林
- 西南: 成都、重庆、昆明、贵阳、拉萨
- 西北: 西安、兰州、西宁、银川、乌鲁木齐
- 港澳台: 香港、澳门、台北

数据源: Meteostat (NOAA ISD + 各国气象服务聚合)
时间范围: 2026-01-01 ~ 2026-07-19
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
    from meteostat import Stations, Daily, Hourly
except ImportError:
    print("请先安装: pip install meteostat")
    raise

# 全中国主要机场 (ICAO, 名称, 区域, 纬度, 经度, 海拔m)
CHINA_AIRPORTS = [
    # 华北 (6)
    ("ZBAA", "北京首都", "华北", 40.0801, 116.5846, 35),
    ("ZBAD", "北京大兴", "华北", 39.5098, 116.4105, 25),
    ("ZBTJ", "天津滨海", "华北", 39.1244, 117.3464, 2),
    ("ZBSJ", "石家庄正定", "华北", 38.2810, 114.6960, 71),
    ("ZBYN", "太原武宿", "华北", 37.7449, 112.6286, 785),
    ("ZBHH", "呼和浩特白塔", "华北", 40.8515, 111.8233, 1083),
    # 东北 (4)
    ("ZYTX", "沈阳桃仙", "东北", 41.6398, 123.4836, 60),
    ("ZYTL", "大连周水子", "东北", 38.9657, 121.5386, 32),
    ("ZYCC", "长春龙嘉", "东北", 44.0046, 125.6848, 215),
    ("ZYHB", "哈尔滨太平", "东北", 45.6234, 126.2503, 139),
    # 华东 (12)
    ("ZSPD", "上海浦东", "华东", 31.1443, 121.8083, 4),
    ("ZSSS", "上海虹桥", "华东", 31.1979, 121.3361, 3),
    ("ZSHC", "杭州萧山", "华东", 30.2294, 120.4344, 7),
    ("ZSNJ", "南京禄口", "华东", 31.7420, 118.8622, 14),
    ("ZSQD", "青岛流亭", "华东", 36.2622, 120.3744, 10),
    ("ZSAM", "厦门高崎", "华东", 24.5440, 118.1270, 18),
    ("ZSOF", "合肥新桥", "华东", 31.7494, 117.3094, 31),
    ("ZSJN", "济南遥墙", "华东", 36.3611, 117.2131, 23),
    ("ZSWX", "无锡硕放", "华东", 31.4939, 120.4297, 5),
    ("ZSWZ", "温州龙湾", "华东", 27.9122, 120.8528, 9),
    ("ZSFZ", "福州长乐", "华东", 25.9451, 119.6623, 14),
    ("ZSNB", "宁波栎社", "华东", 29.8267, 121.4589, 4),
    # 华中 (4)
    ("ZHHH", "武汉天河", "华中", 30.7838, 114.2081, 34),
    ("ZGHA", "长沙黄花", "华中", 28.1892, 113.2196, 66),
    ("ZHCC", "郑州新郑", "华中", 34.5197, 113.8408, 151),
    ("ZSCN", "南昌昌北", "华中", 28.8650, 115.9020, 44),
    # 华南 (7)
    ("ZGGG", "广州白云", "华南", 23.3924, 113.2988, 11),
    ("ZGSZ", "深圳宝安", "华南", 22.6393, 113.8108, 4),
    ("ZGSD", "珠海金湾", "华南", 22.0086, 113.3763, 5),
    ("ZJHK", "海口美兰", "华南", 19.9349, 110.4589, 23),
    ("ZJSY", "三亚凤凰", "华南", 18.3029, 109.4124, 28),
    ("ZGNN", "南宁吴圩", "华南", 22.6083, 108.1722, 65),
    ("ZGKL", "桂林两江", "华南", 25.2181, 110.0394, 174),
    # 西南 (5)
    ("ZUUU", "成都双流", "西南", 30.5785, 103.9471, 495),
    ("ZUCK", "重庆江北", "西南", 29.7192, 106.6418, 416),
    ("ZPPP", "昆明长水", "西南", 25.1019, 102.9292, 2102),
    ("ZUGY", "贵阳龙洞堡", "西南", 26.5385, 106.8009, 1139),
    ("ZULS", "拉萨贡嘎", "西南", 29.2978, 90.9119, 3570),
    # 西北 (5)
    ("ZLXY", "西安咸阳", "西北", 34.4471, 108.7517, 479),
    ("ZLLL", "兰州中川", "西北", 36.5152, 103.6202, 1947),
    ("ZLXN", "西宁曹家堡", "西北", 36.5333, 102.0381, 2184),
    ("ZLIC", "银川河东", "西北", 38.3242, 106.3931, 1147),
    ("ZWAT", "乌鲁木齐地窝堡", "西北", 43.9072, 87.4742, 648),
    # 港澳台 (3)
    ("VHHH", "香港赤鱲角", "港澳台", 22.3089, 113.9185, 9),
    ("VMMC", "澳门国际", "港澳台", 22.1496, 113.5926, 6),
    ("RCTP", "台北桃园", "港澳台", 25.0797, 121.2342, 33),
]

# 时间范围: 2026-01-01 至今
START = datetime(2026, 1, 1)
END   = datetime(2026, 7, 19, 23, 59)

# 输出目录
OUTPUT_DIR = Path("c:/work/meteo/data/meteostat/china_2026")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(msg, flush=True)


def find_nearest_station(lat, lon):
    """查询机场坐标附近最近的气象站"""
    try:
        # 先找 30km 内
        stations = Stations().nearby(lat, lon, radius=30000)
        df = stations.fetch()
        if len(df) > 0:
            sid = df.index[0]
            return sid, df.iloc[0]
        # 扩大到 50km
        stations = Stations().nearby(lat, lon, radius=50000)
        df = stations.fetch()
        if len(df) > 0:
            sid = df.index[0]
            return sid, df.iloc[0]
        return None, None
    except Exception as e:
        return None, None


def download_daily(station_id, icao):
    try:
        data = Daily(station_id, START, END)
        df = data.fetch()
        if len(df) > 0:
            out_path = OUTPUT_DIR / f"daily_{icao}_{station_id}.csv"
            df.to_csv(out_path, encoding='utf-8-sig')
        return df
    except Exception as e:
        log(f"  日数据失败: {e}")
        return pd.DataFrame()


def download_hourly(station_id, icao):
    try:
        data = Hourly(station_id, START, END)
        df = data.fetch()
        if len(df) > 0:
            out_path = OUTPUT_DIR / f"hourly_{icao}_{station_id}.csv"
            df.to_csv(out_path, encoding='utf-8-sig')
        return df
    except Exception as e:
        log(f"  小时数据失败: {e}")
        return pd.DataFrame()


def main():
    log("=" * 80)
    log("全中国机场气象数据下载 (2026-01-01 ~ 2026-07-19)")
    log("=" * 80)
    log(f"机场总数: {len(CHINA_AIRPORTS)}")

    # 按区域统计
    regions = {}
    for _, _, region, _, _, _ in CHINA_AIRPORTS:
        regions[region] = regions.get(region, 0) + 1
    log("区域分布:")
    for r, c in regions.items():
        log(f"  {r}: {c} 个")

    log(f"时间范围: {START:%Y-%m-%d} ~ {END:%Y-%m-%d}")
    log(f"输出目录: {OUTPUT_DIR}")
    log("")

    station_records = []
    summary_records = []
    current_region = None

    for i, (icao, name, region, lat, lon, alt) in enumerate(CHINA_AIRPORTS, 1):
        if region != current_region:
            log(f"\n{'─' * 60}")
            log(f"【{region}】")
            log(f"{'─' * 60}")
            current_region = region

        log(f"\n[{i}/{len(CHINA_AIRPORTS)}] {icao} {name} ({lat:.4f}°N, {lon:.4f}°E, {alt}m)")

        sid, station_row = find_nearest_station(lat, lon)
        if sid is None:
            log(f"  ❌ 未找到附近站点")
            summary_records.append({
                'icao': icao, 'name': name, 'region': region,
                'lat': lat, 'lon': lon, 'alt': alt,
                'station_id': None, 'station_name': None,
                'daily_count': 0, 'hourly_count': 0, 'status': 'no_station'
            })
            continue

        sname = station_row.get('name', 'unknown')
        slat  = station_row.get('latitude', None)
        slon  = station_row.get('longitude', None)
        salt  = station_row.get('elevation', None)
        dist  = station_row.get('distance', None)
        dist_str = f", 距离={dist:.1f}km" if dist is not None else ""
        log(f"  站点: ID={sid}, 名称={sname}{dist_str}")

        station_records.append({
            'airport_icao': icao, 'airport_name': name, 'region': region,
            'airport_lat': lat, 'airport_lon': lon, 'airport_alt': alt,
            'station_id': sid, 'station_name': sname,
            'station_lat': slat, 'station_lon': slon, 'station_alt': salt,
            'distance_km': dist
        })

        # 下载日数据
        daily_df = download_daily(sid, icao)
        time.sleep(0.3)

        # 下载小时数据
        hourly_df = download_hourly(sid, icao)
        time.sleep(0.3)

        # 预览
        daily_cnt = len(daily_df)
        hourly_cnt = len(hourly_df)
        log(f"  日数据: {daily_cnt} 条, 小时数据: {hourly_cnt} 条")

        if daily_cnt > 0:
            tavg = daily_df['tavg'].mean()
            tmax = daily_df['tmax'].max()
            tmin = daily_df['tmin'].min()
            prcp_total = daily_df['prcp'].sum() if 'prcp' in daily_df.columns else 0
            log(f"    温度: 均值={tavg:.1f}°C, 极值={tmin:.1f}~{tmax:.1f}°C, 降水={prcp_total:.0f}mm")

        summary_records.append({
            'icao': icao, 'name': name, 'region': region,
            'lat': lat, 'lon': lon, 'alt': alt,
            'station_id': sid, 'station_name': sname,
            'daily_count': daily_cnt, 'hourly_count': hourly_cnt,
            'status': 'ok' if daily_cnt > 0 or hourly_cnt > 0 else 'no_data'
        })

    # 保存元数据
    if station_records:
        stations_df = pd.DataFrame(station_records)
        stations_path = OUTPUT_DIR / "stations_metadata.csv"
        stations_df.to_csv(stations_path, index=False, encoding='utf-8-sig')
        log(f"\n站点元数据: {stations_path}")

    # 保存汇总
    summary_df = pd.DataFrame(summary_records)
    summary_path = OUTPUT_DIR / "download_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')

    # 汇总报告
    log("\n" + "=" * 80)
    log("下载汇总")
    log("=" * 80)
    log(f"\n{'ICAO':<7}{'机场':<14}{'区域':<8}{'站点ID':<10}{'日数据':>8}{'小时数据':>10}{'状态':<10}")
    log("-" * 80)

    current_region = None
    for r in summary_records:
        if r['region'] != current_region:
            if current_region is not None:
                # 区域小计
                region_items = [x for x in summary_records if x['region'] == current_region]
                r_daily = sum(x['daily_count'] for x in region_items)
                r_hourly = sum(x['hourly_count'] for x in region_items)
                log(f"{'':7}{'小计':<14}{current_region:<8}{'':10}{r_daily:>8}{r_hourly:>10}")
                log("")
            current_region = r['region']
        log(f"{r['icao']:<7}{r['name']:<14}{r['region']:<8}{str(r['station_id']):<10}"
            f"{r['daily_count']:>8}{r['hourly_count']:>10}{r['status']:<10}")

    # 最后一个区域小计
    region_items = [x for x in summary_records if x['region'] == current_region]
    r_daily = sum(x['daily_count'] for x in region_items)
    r_hourly = sum(x['hourly_count'] for x in region_items)
    log(f"{'':7}{'小计':<14}{current_region:<8}{'':10}{r_daily:>8}{r_hourly:>10}")

    # 总计
    total_daily = sum(r['daily_count'] for r in summary_records)
    total_hourly = sum(r['hourly_count'] for r in summary_records)
    success = sum(1 for r in summary_records if r['status'] == 'ok')
    failed = sum(1 for r in summary_records if r['status'] != 'ok')
    log("-" * 80)
    log(f"{'总计':<39}{total_daily:>8}{total_hourly:>10}")
    log(f"\n成功: {success} 个机场, 失败: {failed} 个机场")
    log(f"总记录数: 日数据 {total_daily} 条, 小时数据 {total_hourly} 条")
    log(f"\n输出目录: {OUTPUT_DIR}")
    log(f"汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
