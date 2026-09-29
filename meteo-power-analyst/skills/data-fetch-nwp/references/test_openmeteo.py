"""
Open-Meteo API 下载测试脚本

测试两类接口：
1. 实时预报 API: https://api.open-meteo.com/v1/forecast
2. 历史天气 API: https://archive-api.open-meteo.com/v1/archive

特点：
- 无需 API key（非商业用途，每日 < 10000 次调用）
- 支持 ERA5、ERA5-Land、IFS 等多种再分析数据
- 返回 JSON / CSV / XLSX 格式

测试记录：
- 2026-07-18 测试通过，北京 168 小时预报 + 17 天 ERA5 历史数据
"""

import requests
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timezone


def test_forecast_api():
    """测试实时预报 API"""
    print("=" * 60)
    print("测试 1: Open-Meteo 实时预报 API")
    print("=" * 60)

    # 北京坐标
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 39.9042,
        "longitude": 116.4074,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "precipitation",
            "surface_pressure",
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
        ],
        "timezone": "Asia/Shanghai",
        "forecast_days": 7,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        print(f"✅ 请求成功")
        print(f"  位置: {data['latitude']:.4f}°N, {data['longitude']:.4f}°E")
        print(f"  时区: {data['timezone']} (UTC{data['utc_offset_seconds']//3600:+d})")

        # 保存原始 JSON
        output_dir = Path("c:/work/meteo/data/openmeteo")
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "forecast_beijing.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 转为 DataFrame
        hourly_df = pd.DataFrame({
            "time": data["hourly"]["time"],
            "temp_2m_C": data["hourly"]["temperature_2m"],
            "rh_2m_pct": data["hourly"]["relative_humidity_2m"],
            "wind_speed_10m_kmh": data["hourly"]["wind_speed_10m"],
            "wind_dir_10m": data["hourly"]["wind_direction_10m"],
            "precip_mm": data["hourly"]["precipitation"],
            "pressure_hPa": data["hourly"]["surface_pressure"],
        })
        hourly_df["time"] = pd.to_datetime(hourly_df["time"])
        hourly_df.to_csv(output_dir / "forecast_beijing_hourly.csv", index=False)

        print(f"  小时数据: {len(hourly_df)} 条")
        print(f"  首条记录:\n{hourly_df.iloc[0].to_string()}")
        print(f"  保存到: {output_dir / 'forecast_beijing.json'}")
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def test_historical_api():
    """测试历史天气 API（ERA5 再分析数据）"""
    print("\n" + "=" * 60)
    print("测试 2: Open-Meteo 历史天气 API (ERA5)")
    print("=" * 60)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 39.9042,
        "longitude": 116.4074,
        "start_date": "2026-07-01",
        "end_date": "2026-07-17",
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "dew_point_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
            "surface_pressure",
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
        ],
        "timezone": "Asia/Shanghai",
        "model": "era5",
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        print(f"✅ 请求成功")
        print(f"  位置: {data['latitude']:.4f}°N, {data['longitude']:.4f}°E")
        print(f"  数据源: ERA5")
        print(f"  时区: {data['timezone']}")

        # 保存原始 JSON
        output_dir = Path("c:/work/meteo/data/openmeteo")
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "historical_beijing_era5.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 转 DataFrame
        daily_df = pd.DataFrame({
            "time": data["daily"]["time"],
            "tmax_C": data["daily"]["temperature_2m_max"],
            "tmin_C": data["daily"]["temperature_2m_min"],
            "tmean_C": data["daily"]["temperature_2m_mean"],
            "precip_mm": data["daily"]["precipitation_sum"],
        })
        daily_df.to_csv(output_dir / "historical_beijing_era5_daily.csv", index=False)

        print(f"  日数据: {len(daily_df)} 天")
        print(f"  首条记录:\n{daily_df.iloc[0].to_string()}")
        print(f"  保存到: {output_dir / 'historical_beijing_era5.json'}")
        return True
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


if __name__ == "__main__":
    print(f"测试时间: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
    print(f"Open-Meteo API 下载测试\n")

    r1 = test_forecast_api()
    r2 = test_historical_api()

    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    print(f"  实时预报 API: {'✅ 成功' if r1 else '❌ 失败'}")
    print(f"  历史天气 API: {'✅ 成功' if r2 else '❌ 失败'}")
