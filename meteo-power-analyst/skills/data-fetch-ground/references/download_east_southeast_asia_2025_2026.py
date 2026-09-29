"""
东亚东南亚其他国家机场气象数据下载（2025-2026）

覆盖国家/地区:
- 东亚: 日本、韩国、朝鲜、蒙古
- 东南亚: 越南、泰国、缅甸、老挝、柬埔寨、马来西亚、新加坡、印尼、菲律宾、文莱、东帝汶

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

# 东亚东南亚主要机场 (ICAO, 名称, 国家, 纬度, 经度, 海拔m)
EAST_SOUTHEAST_ASIA_AIRPORTS = [
    # ===== 日本 (8) =====
    ("RJTT", "东京羽田",     "日本",   35.5494, 139.7798, 6),
    ("RJAA", "东京成田",     "日本",   35.7720, 140.3929, 43),
    ("RJBB", "大阪关西",     "日本",   34.4347, 135.2440, 8),
    ("RJOO", "大阪伊丹",     "日本",   34.7855, 135.4382, 12),
    ("RJCC", "札幌新千岁",    "日本",   42.7752, 141.6923, 25),
    ("RJFF", "福冈",         "日本",   33.5859, 130.4509, 10),
    ("RJNN", "名古屋中部",    "日本",   34.8584, 136.8054, 5),
    ("ROAH", "那霸",         "日本",   26.1958, 127.6458, 11),
    # ===== 韩国 (5) =====
    ("RKSI", "首尔仁川",     "韩国",   37.4602, 126.4407, 7),
    ("RKSS", "首尔金浦",     "韩国",   37.5583, 126.7906, 18),
    ("RKPC", "济州",         "韩国",   33.5113, 126.4930, 36),
    ("RKPK", "釜山金海",     "韩国",   35.1795, 128.9376, 2),
    ("RKNY", "襄阳",         "韩国",   38.0612, 128.6646, 23),
    # ===== 朝鲜 (2) =====
    ("ZKPY", "平壤顺安",     "朝鲜",   39.2241, 125.6700, 38),
    ("ZKHM", "咸兴",         "朝鲜",   39.8617, 127.6375, 28),
    # ===== 蒙古 (3) =====
    ("ZMUB", "乌兰巴托成吉思汗", "蒙古", 47.6433, 106.8203, 1305),
    ("ZMMN", "木伦",         "蒙古",   49.7786, 106.0881, 1196),
    ("ZMKD", "乔巴山",       "蒙古",   48.1308, 114.6728, 725),
    # ===== 越南 (5) =====
    ("VVTS", "胡志明新山一",   "越南",   10.8189, 106.6519, 10),
    ("VVNB", "河内内排",      "越南",   21.2212, 105.8072, 12),
    ("VVDN", "岘港",         "越南",   16.0439, 108.1994, 10),
    ("VVCT", "芹苴",         "越南",   10.0850, 105.7117, 5),
    ("VVPH", "富国岛",        "越南",   10.1700, 103.9933, 8),
    # ===== 泰国 (6) =====
    ("VTBS", "曼谷素万那普",   "泰国",   13.6900, 100.7501, 2),
    ("VTBD", "曼谷廊曼",      "泰国",   13.9126, 100.6068, 3),
    ("VTSP", "普吉",         "泰国",    7.8826,  98.3926, 8),
    ("VTSM", "清迈",         "泰国",   18.7669,  98.9650, 3),
    ("VTSB", "乌汶",         "泰国",   15.2448, 104.8699, 124),
    ("VTSH", "合艾",         "泰国",    6.9333, 100.3926, 10),
    # ===== 缅甸 (3) =====
    ("VYYY", "仰光",         "缅甸",   16.9073,  96.1332, 11),
    ("VYMD", "曼德勒",       "缅甸",   21.7022,  95.9779, 91),
    ("VYNT", "内比都",       "缅甸",   19.6261,  96.2017, 100),
    # ===== 老挝 (2) =====
    ("VLVT", "万象瓦岱",      "老挝",   17.9883, 102.5630, 171),
    ("VLLL", "琅勃拉邦",      "老挝",   19.8975, 102.1611, 290),
    # ===== 柬埔寨 (2) =====
    ("VDPP", "金边",         "柬埔寨",  11.5466, 104.8443, 12),
    ("VDSV", "暹粒",         "柬埔寨",  13.4106, 103.8131, 18),
    # ===== 马来西亚 (5) =====
    ("WMKK", "吉隆坡国际",    "马来西亚", 2.7456, 101.7099, 21),
    ("WMKJ", "新山",         "马来西亚", 1.6411, 103.6699, 44),
    ("WMKP", "槟城",         "马来西亚", 5.2971, 100.2767, 11),
    ("WMKB", "哥打巴鲁",      "马来西亚", 6.1667, 102.2933, 6),
    ("WBKK", "亚庇",         "马来西亚", 5.9372, 116.0511, 8),
    # ===== 新加坡 (1) =====
    ("WSSS", "新加坡樟宜",    "新加坡",  1.3644, 103.9915, 7),
    # ===== 印度尼西亚 (6) =====
    ("WIII", "雅加达苏加诺-哈达", "印尼", -6.1256, 106.6559, 10),
    ("WADD", "登巴萨巴厘",    "印尼",   -8.7482, 115.1672, 4),
    ("WARR", "泗水朱安达",    "印尼",   -7.3798, 112.7869, 3),
    ("WIOO", "望加锡",       "印尼",   -5.0617, 119.5542, 14),
    ("WIMM", "棉兰瓜拉纳穆",   "印尼",    3.6422,  98.8853, 31),
    ("WAPP", "查亚普拉",      "印尼",   -2.5761, 140.5175, 10),
    # ===== 菲律宾 (4) =====
    ("RPLL", "马尼拉尼诺伊·阿基诺", "菲律宾", 14.5086, 121.0194, 23),
    ("RPVM", "宿务马克坦",    "菲律宾",  10.3075, 123.9789, 24),
    ("RPVO", "达沃",         "菲律宾",   7.1255, 125.6457, 15),
    ("RPMK", "卡利博",       "菲律宾",  11.6794, 122.3762, 8),
    # ===== 文莱 (1) =====
    ("WBSB", "斯里巴加湾市",   "文莱",    4.9442, 114.9283, 19),
    # ===== 东帝汶 (1) =====
    ("WPDL", "帝力",         "东帝汶",  -8.5466, 125.5275, 15),
]

# 时间范围
PERIODS = [
    ("2025", datetime(2025, 1, 1), datetime(2025, 12, 31, 23, 59)),
    ("2026", datetime(2026, 1, 1), datetime(2026, 7, 19, 23, 59)),
]

OUTPUT_BASE = Path("c:/work/meteo/data/meteostat/east_southeast_asia")


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
    
    # 日数据
    daily_path = out_dir / f"daily_{icao}.csv"
    try:
        df = Daily(station_id, start, end).fetch()
        if len(df) > 0:
            df.to_csv(daily_path, encoding='utf-8-sig')
    except Exception as e:
        log(f"  {period_name} 日数据失败: {e}")
        return 0, 0
    daily_cnt = len(df) if len(df) > 0 else 0
    
    time.sleep(0.3)
    
    # 小时数据
    hourly_path = out_dir / f"hourly_{icao}.csv"
    try:
        df_h = Hourly(station_id, start, end).fetch()
        if len(df_h) > 0:
            df_h.to_csv(hourly_path, encoding='utf-8-sig')
    except Exception as e:
        log(f"  {period_name} 小时数据失败: {e}")
        return daily_cnt, 0
    hourly_cnt = len(df_h) if len(df_h) > 0 else 0
    
    return daily_cnt, hourly_cnt


def main():
    log("=" * 80)
    log("东亚东南亚其他国家机场气象数据下载 (2025-2026)")
    log("=" * 80)
    log(f"机场总数: {len(EAST_SOUTHEAST_ASIA_AIRPORTS)}")

    # 按国家统计
    countries = {}
    for _, _, country, _, _, _ in EAST_SOUTHEAST_ASIA_AIRPORTS:
        countries[country] = countries.get(country, 0) + 1
    log("国家/地区分布:")
    for c, cnt in sorted(countries.items(), key=lambda x: -x[1]):
        log(f"  {c}: {cnt} 个机场")
    log("")

    # 第一阶段: 查询所有机场的站点ID
    log("=" * 80)
    log("阶段1: 查询所有机场的站点映射")
    log("=" * 80)

    station_map = {}  # icao -> (station_id, station_name, name, country)
    current_country = None

    for i, (icao, name, country, lat, lon, alt) in enumerate(EAST_SOUTHEAST_ASIA_AIRPORTS, 1):
        if country != current_country:
            log(f"\n【{country}】")
            current_country = country

        log(f"  [{i}/{len(EAST_SOUTHEAST_ASIA_AIRPORTS)}] {icao} {name} ({lat:.4f}, {lon:.4f})")

        sid, station_row = find_station_robust(lat, lon)
        if sid is None:
            log(f"    ❌ 未找到站点")
            station_map[icao] = (None, None, name, country)
        else:
            sname = station_row.get('name', 'unknown')
            dist = station_row.get('distance', None)
            dist_str = f", 距离={dist:.1f}km" if dist else ""
            log(f"    ✅ 站点={sid} ({sname}){dist_str}")
            station_map[icao] = (sid, sname, name, country)
        time.sleep(0.3)

    # 保存站点元数据
    station_records = []
    for icao, (sid, sname, name, country) in station_map.items():
        station_records.append({
            'icao': icao, 'airport_name': name, 'country': country,
            'station_id': sid, 'station_name': sname
        })
    stations_df = pd.DataFrame(station_records)
    stations_path = OUTPUT_BASE / "stations_metadata.csv"
    stations_path.parent.mkdir(parents=True, exist_ok=True)
    stations_df.to_csv(stations_path, index=False, encoding='utf-8-sig')
    log(f"\n站点元数据: {stations_path}")

    found = sum(1 for v in station_map.values() if v[0] is not None)
    log(f"站点映射: {found}/{len(station_map)} 成功")

    # 第二阶段: 下载两个时期的数据
    log("\n" + "=" * 80)
    log("阶段2: 下载2025和2026年数据")
    log("=" * 80)

    all_summary = []

    for period_name, start, end in PERIODS:
        log(f"\n{'─' * 60}")
        log(f"时期: {period_name} ({start:%Y-%m-%d} ~ {end:%Y-%m-%d})")
        log(f"{'─' * 60}")

        out_dir = OUTPUT_BASE / period_name
        out_dir.mkdir(parents=True, exist_ok=True)

        for icao, (sid, sname, name, country) in station_map.items():
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
                    preview = f" 均温={tavg:.1f}°C, 极值={tmin:.1f}~{tmax:.1f}°C, 降水={prcp:.0f}mm"
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
        log(f"{'ICAO':<7}{'机场':<18}{'国家':<8}{'站点ID':<10}{'日数据':>8}{'小时数据':>10}{'状态':<8}")
        log("-" * 75)
        
        period_data = [r for r in all_summary if r['period'] == period_name]
        current_country = None
        for r in period_data:
            if r['country'] != current_country:
                if current_country is not None:
                    c_items = [x for x in period_data if x['country'] == current_country]
                    cd = sum(x['daily_count'] for x in c_items)
                    ch = sum(x['hourly_count'] for x in c_items)
                    log(f"{'':7}{'小计':<18}{current_country:<8}{'':10}{cd:>8}{ch:>10}")
                    log("")
                current_country = r['country']
            log(f"{r['icao']:<7}{r['name']:<18}{r['country']:<8}{str(r['station_id']):<10}"
                f"{r['daily_count']:>8}{r['hourly_count']:>10}{r['status']:<8}")
        
        c_items = [x for x in period_data if x['country'] == current_country]
        cd = sum(x['daily_count'] for x in c_items)
        ch = sum(x['hourly_count'] for x in c_items)
        log(f"{'':7}{'小计':<18}{current_country:<8}{'':10}{cd:>8}{ch:>10}")
        
        total_d = sum(r['daily_count'] for r in period_data)
        total_h = sum(r['hourly_count'] for r in period_data)
        success = sum(1 for r in period_data if r['status'] == 'ok')
        log(f"\n{period_name}年总计: 日{total_d}条, 时{total_h}条, 成功{success}/{len(period_data)}")

    log(f"\n输出目录: {OUTPUT_BASE}")
    log(f"汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
