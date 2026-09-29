"""
补充下载日本机场气象数据（2025-2026）
之前只有8个主要机场，现在补充22个地方机场，合计30个覆盖日本全国
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

# 补充的日本机场 (ICAO, 名称, 地区, 纬度, 经度, 海拔m)
# 已有的8个: RJTT RJAA RJBB RJOO RJCC RJFF RJNN ROAH
# 补充22个覆盖全国
JAPAN_ADDITIONAL = [
    # 北海道 (5)
    ("RJCH", "函馆",     "北海道", 41.7708, 140.8219, 34),
    ("RJEC", "旭川",     "北海道", 43.6706, 142.4475, 117),
    ("RJCK", "钏路",     "北海道", 43.0419, 144.1947, 96),
    ("RJCM", "女满别",    "北海道", 43.8750, 144.1608, 33),
    ("RJCB", "带广",     "北海道", 42.7333, 143.2167, 91),
    # 东北 (5)
    ("RJSS", "仙台",     "东北",   38.1386, 140.9172, 2),
    ("RJSN", "新潟",     "东北",   37.9544, 139.2364, 5),
    ("RJSK", "秋田",     "东北",   39.6156, 140.2189, 87),
    ("RJSC", "山形",     "东北",   38.8083, 140.3719, 117),
    ("RJSR", "三泽",     "东北",   40.6972, 141.3683, 36),
    # 关东/中部 (4)
    ("RJNS", "静冈",     "中部",   34.7956, 138.8056, 132),
    ("RJSK", "小松",     "中部",   36.3947, 136.4072, 9),  # 注: ICAO重复，实际为RJNK
    # 修正
    # 关西/中国 (3)
    ("RJOA", "广岛",     "中国",   34.4361, 132.9194, 331),
    ("RJOK", "高知",     "四国",   33.5469, 133.6725, 9),
    ("RJOM", "松山",     "四国",   33.8275, 132.7694, 26),
    # 九州/冲绳 (5)
    ("RJFT", "熊本",     "九州",   32.8372, 130.8556, 194),
    ("RJFK", "鹿儿岛",    "九州",   31.8033, 130.7178, 90),
    ("RJFM", "宫崎",     "九州",   31.8758, 131.4483, 14),
    ("RJFO", "大分",     "九州",   33.4792, 131.7372, 7),
    ("RJFS", "佐贺",     "九州",   33.1497, 130.4561, 6),
    ("RJFK", "种子岛",    "九州",   30.6167, 130.9500, 20),
    # 冲绳
    ("RODN", "嘉手纳",    "冲绳",   26.3589, 127.7683, 45),
    ("RORE", "宫古",     "冲绳",   24.7833, 125.3000, 40),
    ("ROIG", "石垣",     "冲绳",   24.3417, 124.1833, 18),
]

# 修正ICAO重复（RJSK既是秋田也是小松，RJFK既是鹿儿岛也是种子岛）
# 实际: 小松=RJNK, 鹿儿岛=RJFK, 种子岛=RJFG
JAPAN_ADDITIONAL_FIXED = [
    # 北海道 (5)
    ("RJCH", "函馆",     "北海道", 41.7708, 140.8219, 34),
    ("RJEC", "旭川",     "北海道", 43.6706, 142.4475, 117),
    ("RJCK", "钏路",     "北海道", 43.0419, 144.1947, 96),
    ("RJCM", "女满别",    "北海道", 43.8750, 144.1608, 33),
    ("RJCB", "带广",     "北海道", 42.7333, 143.2167, 91),
    # 东北 (5)
    ("RJSS", "仙台",     "东北",   38.1386, 140.9172, 2),
    ("RJSN", "新潟",     "东北",   37.9544, 139.2364, 5),
    ("RJSK", "秋田",     "东北",   39.6156, 140.2189, 87),
    ("RJSC", "山形",     "东北",   38.8083, 140.3719, 117),
    ("RJSR", "三泽",     "东北",   40.6972, 141.3683, 36),
    # 中部 (2)
    ("RJNS", "静冈",     "中部",   34.7956, 138.8056, 132),
    ("RJNK", "小松",     "中部",   36.3947, 136.4072, 9),
    # 中国/四国 (3)
    ("RJOA", "广岛",     "中国",   34.4361, 132.9194, 331),
    ("RJOK", "高知",     "四国",   33.5469, 133.6725, 9),
    ("RJOM", "松山",     "四国",   33.8275, 132.7694, 26),
    # 九州 (5)
    ("RJFT", "熊本",     "九州",   32.8372, 130.8556, 194),
    ("RJFK", "鹿儿岛",    "九州",   31.8033, 130.7178, 90),
    ("RJFM", "宫崎",     "九州",   31.8758, 131.4483, 14),
    ("RJFO", "大分",     "九州",   33.4792, 131.7372, 7),
    ("RJFS", "佐贺",     "九州",   33.1497, 130.4561, 6),
    # 冲绳 (3)
    ("RODN", "嘉手纳",    "冲绳",   26.3589, 127.7683, 45),
    ("RORE", "宫古",     "冲绳",   24.7833, 125.3000, 40),
    ("ROIG", "石垣",     "冲绳",   24.3417, 124.1833, 18),
]

PERIODS = [
    ("2025", datetime(2025, 1, 1), datetime(2025, 12, 31, 23, 59)),
    ("2026", datetime(2026, 1, 1), datetime(2026, 7, 19, 23, 59)),
]

OUTPUT_BASE = Path("c:/work/meteo/data/meteostat/east_southeast_asia")


def log(msg):
    print(msg, flush=True)


def find_station_robust(lat, lon):
    for radius_km in [30, 50, 100, 200]:
        try:
            df = Stations().nearby(lat, lon, radius=radius_km * 1000).fetch()
            if len(df) > 0:
                return df.index[0], df.iloc[0]
        except Exception:
            pass
        time.sleep(0.3)
    return None, None


def main():
    log("=" * 80)
    log("补充下载日本机场数据 (22个新增, 之前已有8个, 合计30个)")
    log("=" * 80)
    log(f"新增机场数: {len(JAPAN_ADDITIONAL_FIXED)}")

    # 按地区统计
    regions = {}
    for _, name, region, _, _, _ in JAPAN_ADDITIONAL_FIXED:
        regions[region] = regions.get(region, 0) + 1
    log("地区分布:")
    for r, c in regions.items():
        log(f"  {r}: {c} 个")

    # 阶段1: 查询站点
    log(f"\n{'=' * 80}")
    log("阶段1: 查询站点映射")
    log(f"{'=' * 80}")

    station_map = {}
    current_region = None
    for i, (icao, name, region, lat, lon, alt) in enumerate(JAPAN_ADDITIONAL_FIXED, 1):
        if region != current_region:
            log(f"\n【{region}】")
            current_region = region

        log(f"  [{i}/{len(JAPAN_ADDITIONAL_FIXED)}] {icao} {name} ({lat:.4f}, {lon:.4f})")
        sid, row = find_station_robust(lat, lon)
        if sid:
            sname = row.get('name', '?')
            dist = row.get('distance', None)
            log(f"    ✅ {sid} ({sname}) 距离={dist:.1f}km" if dist else f"    ✅ {sid} ({sname})")
            station_map[icao] = (sid, sname, name, region)
        else:
            log(f"    ❌ 未找到")
            station_map[icao] = (None, None, name, region)
        time.sleep(0.3)

    found = sum(1 for v in station_map.values() if v[0])
    log(f"\n站点查询: {found}/{len(station_map)} 成功")

    # 阶段2: 下载数据
    log(f"\n{'=' * 80}")
    log("阶段2: 下载2025和2026年数据")
    log(f"{'=' * 80}")

    summary = []
    for period_name, start, end in PERIODS:
        log(f"\n【{period_name}年】")
        out_dir = OUTPUT_BASE / period_name

        for icao, (sid, sname, name, region) in station_map.items():
            if sid is None:
                summary.append({'icao': icao, 'name': name, 'region': region,
                               'period': period_name, 'daily_count': 0, 'hourly_count': 0,
                               'status': 'no_station'})
                continue

            # 日数据
            daily_cnt = 0
            try:
                df = Daily(sid, start, end).fetch()
                if len(df) > 0:
                    df.to_csv(out_dir / f"daily_{icao}.csv", encoding='utf-8-sig')
                    daily_cnt = len(df)
            except Exception as e:
                log(f"  {icao} 日数据失败: {e}")

            time.sleep(0.3)

            # 小时数据
            hourly_cnt = 0
            try:
                df_h = Hourly(sid, start, end).fetch()
                if len(df_h) > 0:
                    df_h.to_csv(out_dir / f"hourly_{icao}.csv", encoding='utf-8-sig')
                    hourly_cnt = len(df_h)
            except Exception as e:
                log(f"  {icao} 小时数据失败: {e}")

            preview = ""
            if daily_cnt > 0:
                try:
                    df_check = pd.read_csv(out_dir / f"daily_{icao}.csv", index_col='time', parse_dates=['time'])
                    tavg = df_check['tavg'].mean()
                    tmax = df_check['tmax'].max()
                    tmin = df_check['tmin'].min()
                    prcp = df_check['prcp'].sum() if 'prcp' in df_check.columns else 0
                    preview = f" 均温={tavg:.1f}°C, 极值={tmin:.1f}~{tmax:.1f}°C, 降水={prcp:.0f}mm"
                except Exception:
                    pass

            log(f"  {icao} {name}: 日{daily_cnt}条, 时{hourly_cnt}条{preview}")
            summary.append({'icao': icao, 'name': name, 'region': region,
                           'period': period_name, 'daily_count': daily_cnt,
                           'hourly_count': hourly_cnt, 'status': 'ok' if daily_cnt > 0 else 'no_data'})
            time.sleep(0.3)

    # 汇总
    log(f"\n{'=' * 80}")
    log("补充下载汇总")
    log(f"{'=' * 80}")
    log(f"\n{'ICAO':<7}{'机场':<10}{'地区':<8}{'2025日数据':>12}{'2025小时':>10}{'2026日数据':>12}{'2026小时':>10}")
    log("-" * 75)

    for icao, (_, _, name, region) in station_map.items():
        p25 = [s for s in summary if s['icao'] == icao and s['period'] == '2025']
        p26 = [s for s in summary if s['icao'] == icao and s['period'] == '2026']
        d25 = p25[0]['daily_count'] if p25 else 0
        h25 = p25[0]['hourly_count'] if p25 else 0
        d26 = p26[0]['daily_count'] if p26 else 0
        h26 = p26[0]['hourly_count'] if p26 else 0
        log(f"{icao:<7}{name:<10}{region:<8}{d25:>12}{h25:>10}{d26:>12}{h26:>10}")

    total_d25 = sum(s['daily_count'] for s in summary if s['period'] == '2025')
    total_h25 = sum(s['hourly_count'] for s in summary if s['period'] == '2025')
    total_d26 = sum(s['daily_count'] for s in summary if s['period'] == '2026')
    total_h26 = sum(s['hourly_count'] for s in summary if s['period'] == '2026')

    log("-" * 75)
    log(f"{'合计':<25}{total_d25:>12}{total_h25:>10}{total_d26:>12}{total_h26:>10}")

    success = sum(1 for s in summary if s['status'] == 'ok') // 2  # 两个时期
    log(f"\n新增机场成功: {success}/{len(station_map)}")
    log(f"日本机场总数: 8(原有) + {success}(新增) = {8 + success}")


if __name__ == "__main__":
    main()
