"""
Meteostat 地面观测数据下载测试脚本

Meteostat 提供全球气象站的历史观测数据，数据来源：
- NOAA（美国国家海洋大气局）
- DWD（德国气象服务）
- 其他国家气象服务

特点：
- Python 库 meteostat，基于 Pandas
- 无需 API key（使用 bulk data interface）
- 提供小时、日、月、气候常态数据

安装: pip install meteostat

测试记录：
- 2026-07-18 测试通过，北京日数据 30 条 + 小时数据 168 条 + 站点查询
"""

from datetime import datetime
import pandas as pd
from pathlib import Path

try:
    from meteostat import Point, Daily, Hourly, Stations
except ImportError:
    print("❌ 请先安装 meteostat: pip install meteostat")
    raise


def test_daily_data():
    """测试日数据获取（北京附近）"""
    print("=" * 60)
    print("测试 1: Meteostat 日数据（北京）")
    print("=" * 60)

    # 北京坐标
    beijing = Point(39.9042, 116.4074, 70)  # 海拔约 70m

    # 时间范围：2026 年 6 月
    start = datetime(2026, 6, 1)
    end = datetime(2026, 6, 30)

    try:
        data = Daily(beijing, start, end)
        df = data.fetch()

        print(f"✅ 请求成功")
        print(f"  位置: 北京 39.9042°N, 116.4074°E")
        print(f"  时间: {start:%Y-%m-%d} ~ {end:%Y-%m-%d}")
        print(f"  记录数: {len(df)} 条")

        if len(df) > 0:
            print(f"  列名: {list(df.columns)}")
            print(f"  首条记录:\n{df.iloc[0]}")

            # 保存
            output_dir = Path("c:/work/meteo/data/meteostat")
            output_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_dir / "beijing_daily_202606.csv")
            print(f"  保存到: {output_dir / 'beijing_daily_202606.csv'}")
            return True
        else:
            print("  ⚠️ 无数据返回")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def test_hourly_data():
    """测试小时数据获取"""
    print("\n" + "=" * 60)
    print("测试 2: Meteostat 小时数据（北京）")
    print("=" * 60)

    beijing = Point(39.9042, 116.4074, 70)

    # 时间范围：2026 年 7 月前 7 天
    start = datetime(2026, 7, 1)
    end = datetime(2026, 7, 7, 23, 59)

    try:
        data = Hourly(beijing, start, end)
        df = data.fetch()

        print(f"✅ 请求成功")
        print(f"  位置: 北京")
        print(f"  时间: {start:%Y-%m-%d %H:%M} ~ {end:%Y-%m-%d %H:%M}")
        print(f"  记录数: {len(df)} 条")

        if len(df) > 0:
            print(f"  列名: {list(df.columns)}")
            print(f"  首条记录:\n{df.iloc[0]}")

            output_dir = Path("c:/work/meteo/data/meteostat")
            output_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_dir / "beijing_hourly_202607.csv")
            print(f"  保存到: {output_dir / 'beijing_hourly_202607.csv'}")
            return True
        else:
            print("  ⚠️ 无数据返回")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def test_nearby_stations():
    """测试查询附近气象站"""
    print("\n" + "=" * 60)
    print("测试 3: 查询北京附近气象站")
    print("=" * 60)

    try:
        stations = Stations()
        stations = stations.nearby(39.9042, 116.4074, radius=50000)  # 50km 内
        df = stations.fetch()

        print(f"✅ 请求成功")
        print(f"  中心: 北京 39.9042°N, 116.4074°E")
        print(f"  半径: 50 km")
        print(f"  找到站点: {len(df)} 个")

        if len(df) > 0:
            print(f"  前 5 个站点:")
            display_cols = [c for c in ["name", "country", "latitude", "longitude", "elevation"] if c in df.columns]
            print(df[display_cols].head().to_string())

            output_dir = Path("c:/work/meteo/data/meteostat")
            output_dir.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_dir / "beijing_nearby_stations.csv")
            print(f"  保存到: {output_dir / 'beijing_nearby_stations.csv'}")
            return True
        else:
            print("  ⚠️ 无站点")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


if __name__ == "__main__":
    print(f"Meteostat 地面观测数据下载测试\n")

    r1 = test_daily_data()
    r2 = test_hourly_data()
    r3 = test_nearby_stations()

    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    print(f"  日数据: {'✅ 成功' if r1 else '❌ 失败'}")
    print(f"  小时数据: {'✅ 成功' if r2 else '❌ 失败'}")
    print(f"  站点查询: {'✅ 成功' if r3 else '❌ 失败'}")
