"""
东亚东南亚机场气象数据补充下载（2025-2026）

补充 64 个机场，覆盖：
- 印尼(8) 韩国(7) 菲律宾(6) 缅甸(6) 越南(6) 马来西亚(6)
- 日本(8) 泰国(5) 蒙古(4) 老挝(3) 朝鲜(2) 柬埔寨(1)

数据源: Meteostat (聚合 NOAA ISD + 各国气象服务)
时间范围: 2025-01-01 ~ 2025-12-31, 2026-01-01 ~ 2026-07-19
策略: 站点ID复用 + 逐级扩大半径 + 按ICAO号独立保存 + 追加元数据
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

# 补充机场清单 (ICAO, 名称, 国家, 纬度, 经度, 海拔m)
SUPPLEMENT_AIRPORTS = [
    # ===== 印尼 (8) - 群岛国家补充重点 =====
    ("WIPP", "巨港",         "印尼",   -2.8983,  104.7006, 10),
    ("WICC", "万隆",         "印尼",   -6.9006,  107.5756, 740),
    ("WIIJ", "日惹",         "印尼",   -7.7892,  110.4292, 113),
    ("WIBB", "北干巴鲁",      "印尼",    0.4609,  101.4458, 31),
    ("WIEE", "巴东",         "印尼",   -0.8886,  100.3489, 3),
    ("WION", "坤甸",         "印尼",   -0.1519,  109.4039, 10),
    ("WALL", "巴厘巴板",      "印尼",   -1.2683,  116.8944, 4),
    ("WAMM", "万鸦老",       "印尼",    1.5492,  124.9264, 17),
    # ===== 韩国 (7) =====
    ("RKTN", "大邱",         "韩国",   35.8941,  128.6588, 116),
    ("RKTU", "清州",         "韩国",   36.7164,  127.4989, 58),
    ("RKNN", "群山",         "韩国",   35.9034,  126.6156, 8),
    ("RKJY", "丽水",         "韩国",   34.8422,  127.6161, 16),
    ("RKJM", "木浦",         "韩国",   34.7856,  126.4472, 10),
    ("RKJJ", "光州",         "韩国",   35.1264,  126.8103, 12),
    ("RKNW", "原州",         "韩国",   37.4381,  127.9497, 87),
    # ===== 菲律宾 (6) =====
    ("RPVI", "伊洛伊洛",      "菲律宾",  10.8333,  122.4933, 8),
    ("RPML", "卡加延德奥罗",   "菲律宾",   8.4089,  124.6133, 6),
    ("RPMG", "巴科洛德",      "菲律宾",  10.5194,  123.0128, 7),
    ("RPLP", "拉瓦格",        "菲律宾",  18.1828,  120.5289, 5),
    ("RPZM", "桑博安加",      "菲律宾",   6.9375,  122.0592, 6),
    ("RPVB", "黎牙实比",      "菲律宾",  13.1336,  123.7364, 17),
    # ===== 缅甸 (6) =====
    ("VYMN", "密支那",        "缅甸",   25.3425,   97.3528, 147),
    ("VYDW", "土瓦",         "缅甸",   14.0892,   98.2011, 16),
    ("VYSW", "丹老",         "缅甸",   12.4356,   98.6156, 15),
    ("VYMG", "马圭",         "缅甸",   20.1517,   94.9497, 50),
    ("VYSK", "实兑",         "缅甸",   20.1325,   92.8969, 8),
    ("VYTL", "毛淡棉",        "缅甸",   16.0442,   97.6464, 16),
    # ===== 越南 (6) =====
    ("VVCR", "芽庄金兰",      "越南",   11.9983,  109.2192, 8),
    ("VVHB", "海防",         "越南",   20.8192,  106.7250, 4),
    ("VVPK", "波来古",        "越南",   13.9597,  108.0139, 481),
    ("VVBM", "邦美蜀",        "越南",   12.7008,  108.1167, 529),
    ("VVDL", "大叻",         "越南",   11.7497,  108.2517, 967),
    ("VVVI", "荣市",         "越南",   18.7356,  105.1964, 5),
    # ===== 马来西亚 (6) - 东马+东海岸补充 =====
    ("WBGG", "古晋",         "马来西亚",  1.4847,  110.3478, 22),
    ("WBGM", "美里",         "马来西亚",  4.3375,  113.9908, 17),
    ("WBKS", "山打根",        "马来西亚",  5.8989,  118.0589, 10),
    ("WBKW", "斗湖",         "马来西亚",  4.2628,  118.1214, 16),
    ("WMKC", "关丹",         "马来西亚",  3.7783,  103.2042, 15),
    ("WMKL", "兰卡威",        "马来西亚",  6.3297,   99.7286, 7),
    # ===== 日本 (8) - 地方机场补充 =====
    ("RJFU", "长崎",         "日本",   32.9167,  129.9167, 2),
    ("RJOY", "冈山",         "日本",   34.6578,  133.8550, 242),
    ("RJOS", "德岛",         "日本",   34.1328,  134.2419, 9),
    ("RJOT", "高松",         "日本",   34.2142,  134.0156, 184),
    ("RJDC", "山口宇部",      "日本",   33.9297,  131.2786, 4),
    ("RJCW", "稚内",         "日本",   45.0500,  141.8000, 8),
    ("RJEB", "纹别",         "日本",   44.2906,  143.2139, 23),
    ("RORS", "下地岛",        "日本",   24.8131,  125.1475, 45),
    # ===== 泰国 (5) =====
    ("VTSG", "甲米",         "泰国",    8.0992,   98.9864, 4),
    ("VTUD", "乌隆",         "泰国",   17.3864,  102.7881, 246),
    ("VTKK", "孔敬",         "泰国",   16.4664,  102.7975, 200),
    ("VTST", "春蓬",         "泰国",   10.7117,   99.3739, 5),
    ("VTSM", "苏梅岛",        "泰国",    9.5467,  100.0622, 8),
    # ===== 蒙古 (4) =====
    ("ZMHB", "科布多",        "蒙古",   48.0167,   91.6333, 1560),
    ("ZMUL", "乌兰固木",      "蒙古",   49.8167,   92.0667, 1670),
    ("ZMSB", "赛音山达",      "蒙古",   44.8667,  110.1167, 962),
    ("ZMCK", "达尔汗",        "蒙古",   49.4833,  105.9167, 790),
    # ===== 老挝 (3) =====
    ("VLPS", "巴色",         "老挝",   15.1397,  105.7894, 113),
    ("VLSK", "沙湾拿吉",      "老挝",   16.5167,  104.7667, 153),
    ("VLXK", "川圹",         "老挝",   19.4500,  103.0333, 1150),
    # ===== 朝鲜 (2) - 数据可能稀少 =====
    ("ZKKP", "元山",         "朝鲜",   39.1500,  127.4833, 10),
    ("ZKKC", "清津",         "朝鲜",   41.6833,  129.6500, 5),
    # ===== 柬埔寨 (1) =====
    ("VDSR", "西哈努克市",    "柬埔寨",  10.6094,  103.6331, 5),
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
    """逐级扩大半径搜索站点，返回 (station_id, station_row)"""
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
    daily_cnt = 0
    try:
        df = Daily(station_id, start, end).fetch()
        if len(df) > 0:
            df.to_csv(daily_path, encoding='utf-8-sig')
            daily_cnt = len(df)
    except Exception as e:
        log(f"  {period_name} 日数据失败: {e}")

    time.sleep(0.3)

    # 小时数据
    hourly_path = out_dir / f"hourly_{icao}.csv"
    hourly_cnt = 0
    try:
        df_h = Hourly(station_id, start, end).fetch()
        if len(df_h) > 0:
            df_h.to_csv(hourly_path, encoding='utf-8-sig')
            hourly_cnt = len(df_h)
    except Exception as e:
        log(f"  {period_name} 小时数据失败: {e}")

    return daily_cnt, hourly_cnt


def main():
    log("=" * 80)
    log("东亚东南亚机场气象数据补充下载 (2025-2026)")
    log("=" * 80)
    log(f"补充机场总数: {len(SUPPLEMENT_AIRPORTS)}")

    # 按国家统计
    countries = {}
    for _, _, country, _, _, _ in SUPPLEMENT_AIRPORTS:
        countries[country] = countries.get(country, 0) + 1
    log("国家/地区分布:")
    for c, cnt in sorted(countries.items(), key=lambda x: -x[1]):
        log(f"  {c}: {cnt} 个机场")
    log("")

    # ============ 阶段1: 查询所有机场的站点ID ============
    log("=" * 80)
    log("阶段1: 查询所有补充机场的站点映射")
    log("=" * 80)

    station_map = {}  # icao -> (station_id, station_name, station_lat, station_lon, station_alt, distance_m, name, country, airport_lat, airport_lon, airport_alt)
    current_country = None

    for i, (icao, name, country, lat, lon, alt) in enumerate(SUPPLEMENT_AIRPORTS, 1):
        if country != current_country:
            log(f"\n【{country}】")
            current_country = country

        log(f"  [{i}/{len(SUPPLEMENT_AIRPORTS)}] {icao} {name} ({lat:.4f}, {lon:.4f})")

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

    # 追加到站点元数据
    station_records = []
    for icao, (sid, sname, slat, slon, salt, dist_m, name, country, alat, alon, aalt) in station_map.items():
        station_records.append({
            'icao': icao, 'airport_name': name, 'country': country,
            'station_id': sid, 'station_name': sname,
            'station_lat': slat, 'station_lon': slon, 'station_alt': salt,
            'distance_km': (dist_m / 1000) if dist_m else None,
        })
    stations_new_df = pd.DataFrame(station_records)

    # 追加到现有 stations_metadata.csv
    stations_path = OUTPUT_BASE / "stations_metadata.csv"
    if stations_path.exists():
        existing = pd.read_csv(stations_path, encoding='utf-8-sig')
        # 去重: 如果ICAO已存在则跳过
        existing_icaos = set(existing['icao'].astype(str))
        new_rows = stations_new_df[~stations_new_df['icao'].isin(existing_icaos)]
        combined = pd.concat([existing, new_rows], ignore_index=True)
        combined.to_csv(stations_path, index=False, encoding='utf-8-sig')
        log(f"\n站点元数据已追加: {stations_path} (新增 {len(new_rows)} 条, 总计 {len(combined)} 条)")
    else:
        stations_new_df.to_csv(stations_path, index=False, encoding='utf-8-sig')
        log(f"\n站点元数据已创建: {stations_path} ({len(stations_new_df)} 条)")

    # 追加到 all_stations_coordinates.csv
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

    # ============ 阶段2: 下载两个时期的数据 ============
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

    # 追加到 download_summary.csv
    summary_new_df = pd.DataFrame(all_summary)
    summary_path = OUTPUT_BASE / "download_summary.csv"
    if summary_path.exists():
        existing_sum = pd.read_csv(summary_path, encoding='utf-8-sig')
        existing_keys = set(zip(existing_sum['icao'].astype(str), existing_sum['period'].astype(str)))
        new_rows = summary_new_df[~summary_new_df.apply(lambda r: (str(r['icao']), str(r['period'])) in existing_keys, axis=1)]
        combined_sum = pd.concat([existing_sum, new_rows], ignore_index=True)
        combined_sum.to_csv(summary_path, index=False, encoding='utf-8-sig')
        log(f"\n汇总文件已追加: {summary_path} (新增 {len(new_rows)} 条, 总计 {len(combined_sum)} 条)")
    else:
        summary_new_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
        log(f"\n汇总文件已创建: {summary_path} ({len(summary_new_df)} 条)")

    # ============ 汇总报告 ============
    log("\n" + "=" * 80)
    log("补充下载汇总")
    log("=" * 80)

    for period_name, _, _ in PERIODS:
        log(f"\n【{period_name}年】")
        log(f"{'ICAO':<7}{'机场':<20}{'国家':<8}{'站点ID':<10}{'日数据':>8}{'小时数据':>10}{'状态':<8}")
        log("-" * 75)

        period_data = [r for r in all_summary if r['period'] == period_name]
        current_country = None
        for r in period_data:
            if r['country'] != current_country:
                if current_country is not None:
                    c_items = [x for x in period_data if x['country'] == current_country]
                    cd = sum(x['daily_count'] for x in c_items)
                    ch = sum(x['hourly_count'] for x in c_items)
                    log(f"{'':7}{'小计':<20}{current_country:<8}{'':10}{cd:>8}{ch:>10}")
                    log("")
                current_country = r['country']
            log(f"{r['icao']:<7}{r['name']:<20}{r['country']:<8}{str(r['station_id']):<10}"
                f"{r['daily_count']:>8}{r['hourly_count']:>10}{r['status']:<8}")

        c_items = [x for x in period_data if x['country'] == current_country]
        cd = sum(x['daily_count'] for x in c_items)
        ch = sum(x['hourly_count'] for x in c_items)
        log(f"{'':7}{'小计':<20}{current_country:<8}{'':10}{cd:>8}{ch:>10}")

        total_d = sum(r['daily_count'] for r in period_data)
        total_h = sum(r['hourly_count'] for r in period_data)
        success = sum(1 for r in period_data if r['status'] == 'ok')
        log(f"\n{period_name}年补充总计: 日{total_d}条, 时{total_h}条, 成功{success}/{len(period_data)}")

    log(f"\n输出目录: {OUTPUT_BASE}")
    log(f"汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
