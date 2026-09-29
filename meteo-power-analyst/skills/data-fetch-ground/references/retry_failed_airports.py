"""
重试失败的机场: 宁波ZSNB, 兰州ZLLL
策略: 扩大搜索半径到100km/200km/500km
保存: 按ICAO号独立文件 (daily_{ICAO}.csv, hourly_{ICAO}.csv)
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

# 失败的机场
FAILED_AIRPORTS = [
    ("ZSNB", "宁波栎社", 29.8267, 121.4589, 4),
    ("ZLLL", "兰州中川", 36.5152, 103.6202, 1947),
]

START = datetime(2026, 1, 1)
END   = datetime(2026, 7, 19, 23, 59)

# 输出到全国目录，按ICAO号命名
OUTPUT_DIR = Path("c:/work/meteo/data/meteostat/china_2026")


def log(msg):
    print(msg, flush=True)


def find_station_with_expanding_radius(lat, lon, icao):
    """逐级扩大半径搜索站点"""
    for radius_km in [30, 50, 100, 200, 500]:
        try:
            stations = Stations().nearby(lat, lon, radius=radius_km * 1000)
            df = stations.fetch()
            if len(df) > 0:
                sid = df.index[0]
                row = df.iloc[0]
                dist = row.get('distance', None)
                log(f"  ✅ 半径{radius_km}km找到: ID={sid}, 名称={row.get('name','?')}, 距离={dist:.1f}km" if dist else f"  ✅ 半径{radius_km}km找到: ID={sid}")
                return sid, row
        except Exception as e:
            log(f"  半径{radius_km}km查询异常: {e}")
        time.sleep(0.3)
    return None, None


def try_direct_station_lookup(icao, lat, lon):
    """尝试直接用ICAO代码作为站点ID查询"""
    # Meteostat 有时用ICAO代码作为站点ID
    candidates = [icao, icao.upper()]
    for sid_try in candidates:
        try:
            data = Daily(sid_try, START, END)
            df = data.fetch()
            if len(df) > 0:
                log(f"  ✅ 直接用ICAO代码 {sid_try} 查询成功: {len(df)}条日数据")
                # 获取站点信息
                stations = Stations()
                stations = stations.id(sid_try)
                sdf = stations.fetch()
                if len(sdf) > 0:
                    return sid_try, sdf.iloc[0]
                return sid_try, pd.Series({'name': sid_try})
        except Exception:
            pass
    return None, None


def download_and_save(station_id, icao, name):
    """下载日/小时数据，按ICAO号保存独立文件"""
    # 日数据
    daily_path = OUTPUT_DIR / f"daily_{icao}.csv"
    try:
        data = Daily(station_id, START, END)
        df = data.fetch()
        if len(df) > 0:
            df.to_csv(daily_path, encoding='utf-8-sig')
            log(f"  日数据: {len(df)} 条 → {daily_path.name}")
        else:
            log(f"  日数据: 无数据")
            df = pd.DataFrame()
    except Exception as e:
        log(f"  日数据失败: {e}")
        df = pd.DataFrame()
    
    time.sleep(0.5)
    
    # 小时数据
    hourly_path = OUTPUT_DIR / f"hourly_{icao}.csv"
    try:
        data = Hourly(station_id, START, END)
        df_h = data.fetch()
        if len(df_h) > 0:
            df_h.to_csv(hourly_path, encoding='utf-8-sig')
            log(f"  小时数据: {len(df_h)} 条 → {hourly_path.name}")
        else:
            log(f"  小时数据: 无数据")
            df_h = pd.DataFrame()
    except Exception as e:
        log(f"  小时数据失败: {e}")
        df_h = pd.DataFrame()
    
    return df, df_h


def main():
    log("=" * 70)
    log("重试失败机场下载 (按ICAO号保存独立文件)")
    log("=" * 70)
    log(f"失败机场: {[a[0] for a in FAILED_AIRPORTS]}")
    log(f"输出目录: {OUTPUT_DIR}")
    log(f"文件命名: daily_{{ICAO}}.csv, hourly_{{ICAO}}.csv")
    log("")

    results = []

    for icao, name, lat, lon, alt in FAILED_AIRPORTS:
        log(f"\n{'─' * 60}")
        log(f"{icao} {name} ({lat:.4f}°N, {lon:.4f}°E, {alt}m)")
        log(f"{'─' * 60}")

        # 策略1: 直接用ICAO代码作为站点ID
        log(f"\n策略1: 直接用ICAO代码查询")
        sid, station_row = try_direct_station_lookup(icao, lat, lon)

        # 策略2: 扩大半径搜索
        if sid is None:
            log(f"\n策略2: 扩大半径搜索附近站点")
            sid, station_row = find_station_with_expanding_radius(lat, lon, icao)

        if sid is None:
            log(f"\n❌ {icao} {name} 仍无法找到站点 (500km内无站点)")
            results.append({'icao': icao, 'name': name, 'station_id': None,
                            'daily_count': 0, 'hourly_count': 0, 'status': 'failed'})
            continue

        # 下载并保存
        sname = station_row.get('name', 'unknown')
        slat = station_row.get('latitude', None)
        slon = station_row.get('longitude', None)
        log(f"\n使用站点: ID={sid}, 名称={sname}, 坐标=({slat}, {slon})")

        daily_df, hourly_df = download_and_save(sid, icao, name)

        # 预览
        if len(daily_df) > 0:
            tavg = daily_df['tavg'].mean()
            tmax = daily_df['tmax'].max()
            tmin = daily_df['tmin'].min()
            prcp = daily_df['prcp'].sum() if 'prcp' in daily_df.columns else 0
            log(f"  温度: 均值={tavg:.1f}°C, 极值={tmin:.1f}~{tmax:.1f}°C, 降水={prcp:.0f}mm")
            log(f"  日期范围: {daily_df.index[0]} ~ {daily_df.index[-1]}")

        results.append({'icao': icao, 'name': name, 'station_id': sid,
                        'station_name': sname,
                        'daily_count': len(daily_df), 'hourly_count': len(hourly_df),
                        'status': 'ok' if len(daily_df) > 0 else 'no_data'})

    # 汇总
    log("\n" + "=" * 70)
    log("重试结果汇总")
    log("=" * 70)
    log(f"\n{'ICAO':<8}{'机场':<12}{'站点ID':<12}{'日数据':>8}{'小时数据':>10}{'状态':<10}")
    log("-" * 60)
    for r in results:
        log(f"{r['icao']:<8}{r['name']:<12}{str(r.get('station_id','')):<12}"
            f"{r['daily_count']:>8}{r['hourly_count']:>10}{r['status']:<10}")

    success = sum(1 for r in results if r['status'] == 'ok')
    log(f"\n成功: {success}/{len(results)}")


if __name__ == "__main__":
    main()

