"""
南北美洲主要机场气象数据下载（2025-2026）

覆盖国家:
- 北美: 美国、加拿大、墨西哥
- 中美洲: 危地马拉、巴拿马、哥斯达黎加、古巴、多米尼加、洪都拉斯、萨尔瓦多
- 南美: 巴西、阿根廷、智利、哥伦比亚、秘鲁、委内瑞拉、厄瓜多尔、玻利维亚、巴拉圭、乌拉圭

数据源: Meteostat (聚合 NOAA ISD + 各国气象服务)
时间范围: 2025-01-01 ~ 2025-12-31, 2026-01-01 ~ 2026-07-19
策略: 站点ID复用 + 逐级扩大半径 + 按ICAO号独立保存
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import warnings
warnings.filterwarnings('ignore')

from datetime import datetime
from pathlib import Path
import time
import pandas as pd

from meteostat import Stations, Daily, Hourly

# 南北美洲主要机场 (ICAO, 名称, 国家, 纬度, 经度, 海拔m)
AMERICAS_AIRPORTS = [
    # ===== 美国 (20) =====
    ("KATL", "亚特兰大",       "美国",   33.6407,  -84.4277, 308),
    ("KLAX", "洛杉矶",         "美国",   33.9425, -118.4081, 38),
    ("KORD", "芝加哥奥黑尔",    "美国",   41.9742,  -87.9073, 201),
    ("KDFW", "达拉斯沃斯堡",    "美国",   32.8998,  -97.0403, 185),
    ("KDEN", "丹佛",           "美国",   39.8561, -104.6737, 1655),
    ("KJFK", "纽约肯尼迪",      "美国",   40.6413,  -73.7781, 4),
    ("KSFO", "旧金山",          "美国",   37.6213, -122.3790, 4),
    ("KSEA", "西雅图塔科马",    "美国",   47.4502, -122.3088, 132),
    ("KLAS", "拉斯维加斯",      "美国",   36.0840, -115.1537, 636),
    ("KMCO", "奥兰多",          "美国",   28.4312,  -81.3081, 30),
    ("KMIA", "迈阿密",          "美国",   25.7959,  -80.2870, 9),
    ("KPHX", "凤凰城",          "美国",   33.4343, -112.0116, 336),
    ("KIAH", "休斯顿布什",      "美国",   29.9844,  -95.3414, 30),
    ("KBOS", "波士顿",          "美国",   42.3656,  -71.0096, 6),
    ("KMSP", "明尼阿波利斯",    "美国",   44.8820,  -93.2218, 256),
    ("KFLL", "劳德代尔堡",      "美国",   26.0742,  -80.1506, 10),
    ("KDTW", "底特律",          "美国",   42.2162,  -83.3554, 196),
    ("KPHL", "费城",            "美国",   39.8744,  -75.2424, 7),
    ("KLGA", "纽约拉瓜迪亚",    "美国",   40.7769,  -73.8740, 7),
    ("KBWI", "巴尔的摩",        "美国",   39.1754,  -76.6683, 44),
    # ===== 加拿大 (10) =====
    ("CYYZ", "多伦多皮尔逊",    "加拿大", 43.6777,  -79.6246, 173),
    ("CYVR", "温哥华",          "加拿大", 49.1939, -123.1844, 4),
    ("CYUL", "蒙特利尔特鲁多",  "加拿大", 45.4706,  -73.7408, 36),
    ("CYEG", "埃德蒙顿",        "加拿大", 53.3097, -113.5801, 723),
    ("CYOW", "渥太华",          "加拿大", 45.3225,  -75.6692, 114),
    ("CYWG", "温尼伯",          "加拿大", 49.9100,  -97.2399, 239),
    ("CYHZ", "哈利法克斯",      "加拿大", 44.8808,  -63.5086, 145),
    ("CYYC", "卡尔加里",        "加拿大", 51.1215, -114.0076, 1084),
    ("CYQB", "魁北克",          "加拿大", 46.7911,  -71.3933, 74),
    ("CYXY", "白马市",          "加拿大", 60.7095, -135.0674, 707),
    # ===== 墨西哥 (6) =====
    ("MMMX", "墨西哥城",        "墨西哥", 19.4363,  -99.0721, 2230),
    ("MMUN", "坎昆",            "墨西哥", 21.0365,  -86.8770, 7),
    ("MMGL", "瓜达拉哈拉",      "墨西哥", 20.5218, -103.3111, 1529),
    ("MMMY", "蒙特雷",          "墨西哥", 25.7785, -100.1067, 390),
    ("MMTJ", "蒂华纳",          "墨西哥", 32.5411, -116.9700, 151),
    ("MMPR", "巴亚尔塔港",      "墨西哥", 20.6801, -105.2540, 6),
    # ===== 中美洲 (7) =====
    ("MGGT", "危地马拉城",      "危地马拉", 14.5833,  -90.5275, 1495),
    ("MPTO", "巴拿马城",        "巴拿马",   9.0714,  -79.3835,  41),
    ("MROC", "圣何塞",          "哥斯达黎加", 9.9939, -84.2088, 921),
    ("MUHA", "哈瓦那",          "古巴",   22.9892,  -82.4091,  64),
    ("MDSD", "圣多明各",        "多米尼加", 18.4297,  -69.6689,  18),
    ("MHLM", "圣佩德罗苏拉",    "洪都拉斯", 15.4525,  -87.9234,  31),
    ("MSLP", "圣萨尔瓦多",      "萨尔瓦多", 13.4409,  -89.0557,  616),
    # ===== 巴西 (10) =====
    ("SBGR", "圣保罗瓜鲁柳斯",  "巴西",  -23.4356,  -46.4731,  760),
    ("SBGL", "里约热内卢",      "巴西",  -22.8089,  -43.2436,   6),
    ("SBSP", "圣保罗 Congonhas","巴西",  -23.6261,  -46.6564,  803),
    ("SBBR", "巴西利亚",        "巴西",  -15.8711,  -47.9186, 1060),
    ("SBRF", "累西腓",          "巴西",   -8.1264,  -34.9236,   8),
    ("SBPA", "阿雷格里港",      "巴西",  -29.9939,  -51.1714,   3),
    ("SBCF", "贝洛奥里藏特",    "巴西",  -19.6244,  -43.9719,  828),
    ("SBFL", "弗洛里亚诺波利斯","巴西",  -27.6703,  -48.5477,   5),
    ("SBSV", "萨尔瓦多",        "巴西",  -12.9086,  -38.3225,  20),
    ("SBMA", "马瑙斯",          "巴西",   -3.0386,  -60.0497,  80),
    # ===== 阿根廷 (5) =====
    ("SAEZ", "布宜诺斯艾利斯",  "阿根廷", -34.8222,  -58.5358,  21),
    ("SAAC", "科尔多瓦",        "阿根廷", -31.3236,  -64.2080,  474),
    ("SAVC", "乌斯怀亚",        "阿根廷", -54.8433,  -68.2956,  22),
    ("SARE", "雷西斯坦西亚",    "阿根廷", -29.3833,  -66.9500,  488),
    ("SAZM", "门多萨",          "阿根廷", -32.8317,  -68.7929,  704),
    # ===== 智利 (5) =====
    ("SCEL", "圣地亚哥",        "智利",  -33.3930,  -70.7858,  474),
    ("SCFA", "安托法加斯塔",    "智利",  -23.4445,  -70.4451,  120),
    ("SCCF", "蓬塔阿雷纳斯",    "智利",  -53.0028,  -70.8536,  35),
    ("SCVD", "瓦尔迪维亚",      "智利",  -39.6275,  -73.0939,  18),
    ("SCIE", "康塞普西翁",      "智利",  -36.7727,  -73.0631,  14),
    # ===== 哥伦比亚 (5) =====
    ("SKBO", "波哥大",          "哥伦比亚",  4.7016,  -74.1469, 2548),
    ("SKCL", "卡利",            "哥伦比亚",  3.5432,  -76.3815,  964),
    ("SKMD", "麦德林",          "哥伦比亚",  6.1645,  -75.4231, 2114),
    ("SKBQ", "巴兰基亚",        "哥伦比亚", 10.8896,  -74.7808,  30),
    ("SKCG", "卡塔赫纳",        "哥伦比亚", 10.4424,  -75.5130,   5),
    # ===== 秘鲁 (4) =====
    ("SPJC", "利马",            "秘鲁",  -12.0219,  -77.1143,   13),
    ("SPZO", "库斯科",          "秘鲁",  -13.5357,  -71.9388, 3249),
    ("SPQU", "阿雷基帕",        "秘鲁",  -16.3411,  -71.5830, 2520),
    ("SPRU", "伊基托斯",        "秘鲁",   -3.7847,  -73.3088,  106),
    # ===== 委内瑞拉 (3) =====
    ("SVMI", "加拉加斯",        "委内瑞拉", 10.6013,  -66.9911,   48),
    ("SVVA", "瓦伦西亚",        "委内瑞拉", 10.1497,  -67.9284,  434),
    ("SVTM", "马拉开波",        "委内瑞拉", 10.5581,  -71.7279,   65),
    # ===== 厄瓜多尔 (3) =====
    ("SEQM", "基多",            "厄瓜多尔", -0.1292,  -78.3576, 2408),
    ("SEGU", "瓜亚基尔",        "厄瓜多尔", -2.1574,  -79.8836,   7),
    ("SEST", "曼塔",            "厄瓜多尔", -0.9542,  -80.6847,   9),
    # ===== 玻利维亚 (3) =====
    ("SLLP", "拉巴斯",          "玻利维亚",-16.5133,  -68.1925, 4048),
    ("SLVR", "圣克鲁斯",        "玻利维亚",-17.8147,  -63.1354,  373),
    ("SLCO", "科恰班巴",        "玻利维亚",-17.4211,  -66.1771, 2535),
    # ===== 巴拉圭 (2) =====
    ("SGAS", "亚松森",          "巴拉圭",-25.2399,  -57.5193,   93),
    ("SGES", "东方城",          "巴拉圭",-25.5047,  -54.8453,  185),
    # ===== 乌拉圭 (2) =====
    ("SUMU", "蒙得维的亚",      "乌拉圭",-34.8384,  -56.0308,   32),
    ("SUAA", "埃斯特角城",      "乌拉圭",-34.8551,  -55.0944,   21),
]

# 时间范围
PERIODS = [
    ("2025", datetime(2025, 1, 1), datetime(2025, 12, 31, 23, 59)),
    ("2026", datetime(2026, 1, 1), datetime(2026, 7, 19, 23, 59)),
]

OUTPUT_BASE = Path("c:/work/meteo/data/meteostat/americas")


def log(msg):
    print(msg, flush=True)


def find_station_robust(lat, lon):
    """逐级扩大半径搜索站点"""
    for radius_km in [30, 50, 100, 200, 500]:
        try:
            df = Stations().nearby(lat, lon, radius=radius_km * 1000).fetch()
            if len(df) > 0:
                sid = df.index[0]
                row = df.iloc[0]
                return sid, row
        except Exception:
            pass
        time.sleep(0.3)
    return None, None


def download_and_save(station_id, icao, period_name, start, end):
    """下载日/小时数据，按ICAO号保存"""
    out_dir = OUTPUT_BASE / period_name
    out_dir.mkdir(parents=True, exist_ok=True)

    daily_cnt = 0
    try:
        df = Daily(station_id, start, end).fetch()
        if len(df) > 0:
            df.to_csv(out_dir / f"daily_{icao}.csv", encoding='utf-8-sig')
            daily_cnt = len(df)
    except Exception as e:
        log(f"  {period_name} 日数据失败: {e}")

    time.sleep(0.3)

    hourly_cnt = 0
    try:
        df_h = Hourly(station_id, start, end).fetch()
        if len(df_h) > 0:
            df_h.to_csv(out_dir / f"hourly_{icao}.csv", encoding='utf-8-sig')
            hourly_cnt = len(df_h)
    except Exception as e:
        log(f"  {period_name} 小时数据失败: {e}")

    return daily_cnt, hourly_cnt


def main():
    log("=" * 80)
    log("南北美洲机场气象数据下载 (2025-2026)")
    log("=" * 80)
    log(f"机场总数: {len(AMERICAS_AIRPORTS)}")

    # 检查重复ICAO
    icaos = [a[0] for a in AMERICAS_AIRPORTS]
    dups = [x for x in set(icaos) if icaos.count(x) > 1]
    if dups:
        log(f"警告: 重复ICAO: {dups}")

    # 按国家统计
    countries = {}
    for _, _, country, _, _, _ in AMERICAS_AIRPORTS:
        countries[country] = countries.get(country, 0) + 1
    log("国家分布:")
    for c, cnt in sorted(countries.items(), key=lambda x: -x[1]):
        log(f"  {c}: {cnt} 个机场")
    log("")

    # 阶段1: 查询站点ID
    log("=" * 80)
    log("阶段1: 查询所有机场的站点映射")
    log("=" * 80)

    station_map = {}
    current_country = None

    for i, (icao, name, country, lat, lon, alt) in enumerate(AMERICAS_AIRPORTS, 1):
        if country != current_country:
            log(f"\n【{country}】")
            current_country = country

        log(f"  [{i}/{len(AMERICAS_AIRPORTS)}] {icao} {name} ({lat:.4f}, {lon:.4f})")

        sid, station_row = find_station_robust(lat, lon)
        if sid is None:
            log(f"    X 未找到站点")
            station_map[icao] = (None, None, None, None, None, None, name, country, lat, lon, alt)
        else:
            sname = station_row.get('name', 'unknown')
            slat = station_row.get('latitude', None)
            slon = station_row.get('longitude', None)
            salt = station_row.get('elevation', None)
            dist = station_row.get('distance', None)
            dist_str = f", 距离={dist/1000:.1f}km" if dist else ""
            log(f"    OK 站点={sid} ({sname}){dist_str}")
            station_map[icao] = (sid, sname, slat, slon, salt, dist, name, country, lat, lon, alt)
        time.sleep(0.3)

    # 保存站点元数据
    station_records = []
    for icao, (sid, sname, slat, slon, salt, dist_m, name, country, alat, alon, aalt) in station_map.items():
        station_records.append({
            'icao': icao, 'airport_name': name, 'country': country,
            'station_id': sid, 'station_name': sname,
            'station_lat': slat, 'station_lon': slon, 'station_alt': salt,
            'distance_km': (dist_m / 1000) if dist_m else None,
        })
    stations_df = pd.DataFrame(station_records)
    stations_path = OUTPUT_BASE / "stations_metadata.csv"
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    stations_df.to_csv(stations_path, index=False, encoding='utf-8-sig')
    log(f"\n站点元数据: {stations_path}")

    # 保存坐标
    coords_path = Path("c:/work/meteo/data/meteostat/all_stations_coordinates.csv")
    coords_new_records = []
    for icao, (sid, sname, slat, slon, salt, dist_m, name, country, alat, alon, aalt) in station_map.items():
        dist_km = (dist_m / 1000) if dist_m else None
        coords_new_records.append({
            'icao': icao, 'name': name, 'country': country,
            'airport_lat': alat, 'airport_lon': alon, 'airport_alt': aalt,
            'station_id': sid, 'station_name': sname,
            'station_lat': slat, 'station_lon': slon, 'station_alt': salt,
            'distance_km': dist_km,
            'delta_lat': (abs(alat - slat)) if (slat is not None and not pd.isna(slat)) else None,
            'delta_lon': (abs(alon - slon)) if (slon is not None and not pd.isna(slon)) else None,
        })
    coords_new_df = pd.DataFrame(coords_new_records)
    if coords_path.exists():
        existing_coords = pd.read_csv(coords_path, encoding='utf-8-sig')
        existing_icaos = set(existing_coords['icao'].astype(str))
        new_coords_rows = coords_new_df[~coords_new_df['icao'].isin(existing_icaos)]
        combined_coords = pd.concat([existing_coords, new_coords_rows], ignore_index=True)
        combined_coords.to_csv(coords_path, index=False, encoding='utf-8-sig')
        log(f"坐标文件已追加: {coords_path} (新增 {len(new_coords_rows)} 条, 总计 {len(combined_coords)} 条)")
    else:
        coords_new_df.to_csv(coords_path, index=False, encoding='utf-8-sig')
        log(f"坐标文件已创建: {coords_path} ({len(coords_new_df)} 条)")

    found = sum(1 for v in station_map.values() if v[0] is not None)
    log(f"\n站点映射: {found}/{len(station_map)} 成功")

    # 阶段2: 下载数据
    log("\n" + "=" * 80)
    log("阶段2: 下载2025和2026年数据")
    log("=" * 80)

    all_summary = []

    for period_name, start, end in PERIODS:
        log(f"\n{'-' * 60}")
        log(f"时期: {period_name} ({start:%Y-%m-%d} ~ {end:%Y-%m-%d})")
        log(f"{'-' * 60}")

        out_dir = OUTPUT_BASE / period_name
        out_dir.mkdir(parents=True, exist_ok=True)

        for icao, (sid, sname, slat, slon, salt, dist_m, name, country, alat, alon, aalt) in station_map.items():
            if sid is None:
                all_summary.append({
                    'icao': icao, 'name': name, 'country': country,
                    'period': period_name, 'station_id': None,
                    'daily_count': 0, 'hourly_count': 0, 'status': 'no_station'
                })
                continue

            daily_cnt, hourly_cnt = download_and_save(sid, icao, period_name, start, end)

            preview = ""
            if daily_cnt > 0:
                try:
                    df = pd.read_csv(out_dir / f"daily_{icao}.csv", index_col='time', parse_dates=['time'])
                    tavg = df['tavg'].mean()
                    tmax = df['tmax'].max()
                    tmin = df['tmin'].min()
                    prcp = df['prcp'].sum() if 'prcp' in df.columns else 0
                    preview = f" 均温={tavg:.1f}C, 极值={tmin:.1f}~{tmax:.1f}C, 降水={prcp:.0f}mm"
                except Exception:
                    pass

            log(f"  {icao} {name}: 日{daily_cnt}条, 时{hourly_cnt}条{preview}")

            all_summary.append({
                'icao': icao, 'name': name, 'country': country,
                'period': period_name, 'station_id': sid,
                'daily_count': daily_cnt, 'hourly_count': hourly_cnt,
                'status': 'ok' if daily_cnt > 0 or hourly_cnt > 0 else 'no_data'
            })
            time.sleep(0.3)

    # 保存汇总
    summary_df = pd.DataFrame(all_summary)
    summary_path = OUTPUT_BASE / "download_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')

    # 汇总报告
    log("\n" + "=" * 80)
    log("下载汇总")
    log("=" * 80)

    for period_name, _, _ in PERIODS:
        log(f"\n【{period_name}年】")
        log(f"{'ICAO':<7}{'机场':<20}{'国家':<10}{'站点ID':<10}{'日数据':>8}{'小时数据':>10}{'状态':<8}")
        log("-" * 80)

        period_data = [r for r in all_summary if r['period'] == period_name]
        current_country = None
        for r in period_data:
            if r['country'] != current_country:
                if current_country is not None:
                    c_items = [x for x in period_data if x['country'] == current_country]
                    cd = sum(x['daily_count'] for x in c_items)
                    ch = sum(x['hourly_count'] for x in c_items)
                    log(f"{'':7}{'小计':<20}{current_country:<10}{'':10}{cd:>8}{ch:>10}")
                    log("")
                current_country = r['country']
            log(f"{r['icao']:<7}{r['name']:<20}{r['country']:<10}{str(r['station_id']):<10}"
                f"{r['daily_count']:>8}{r['hourly_count']:>10}{r['status']:<8}")

        c_items = [x for x in period_data if x['country'] == current_country]
        cd = sum(x['daily_count'] for x in c_items)
        ch = sum(x['hourly_count'] for x in c_items)
        log(f"{'':7}{'小计':<20}{current_country:<10}{'':10}{cd:>8}{ch:>10}")

        total_d = sum(r['daily_count'] for r in period_data)
        total_h = sum(r['hourly_count'] for r in period_data)
        success = sum(1 for r in period_data if r['status'] == 'ok')
        log(f"\n{period_name}年总计: 日{total_d}条, 时{total_h}条, 成功{success}/{len(period_data)}")

    log(f"\n输出目录: {OUTPUT_BASE}")
    log(f"汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
