"""
Open-Meteo HRRR/GFS/NWP 测试脚本
重点：ERCOT 区域风电/光伏相关变量
测试时间：2026-08-12

测试内容：
1. 实时 HRRR forecast (3km, CONUS)
2. 历史 HRRR forecast (2018-01起)
3. 15分钟分辨率 HRRR
4. 80m/100m/120m 风场（风电关键）
5. 太阳辐射 GHI/DNI/DHI（光伏关键）
6. 对流参数 CAPE/CIN/Lifted Index（雷暴关联）
7. 多模型对比 (HRRR vs GFS vs NAM vs NBM)
8. 气压层变量
"""

import json, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl

SKIP_SSL = ssl.create_default_context()
SKIP_SSL.check_hostname = False
SKIP_SSL.verify_mode = ssl.CERT_NONE

def fmt(v, digits=1):
    """安全格式化数值，None 显示为 N/A"""
    return f"{v:.{digits}f}" if v is not None else "N/A"

def fmt_int(v):
    """安全格式化整数，None 显示为 N/A"""
    return f"{v:.0f}" if v is not None else "N/A"

# ERCOT 代表站点（按风电/光伏区域）
ERCOT_SITES = {
    "KFWS_Dallas":       {"lat": 32.895, "lon": -97.037, "zone": "North",     "focus": "wind+solar"},
    "KHGX_Houston":      {"lat": 29.760, "lon": -95.369, "zone": "South",     "focus": "solar+coast"},
    "KMAF_Midland":      {"lat": 31.997, "lon": -102.078, "zone": "West",     "focus": "wind"},
    "KCRP_Corpus":       {"lat": 27.800, "lon": -97.396, "zone": "Coast",    "focus": "wind+coast"},
    "KAMA_Amarillo":     {"lat": 35.222, "lon": -101.831, "zone": "Panhandle","focus": "wind"},
    "SAT_SAntonio":      {"lat": 29.425, "lon": -98.494, "zone": "South",     "focus": "solar"},
}

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    sys.stdout.flush()

def http_get_json(url, timeout=45):
    """带 SSL 跳过和超时的 HTTP GET，返回 JSON"""
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, context=SKIP_SSL, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as e:
        return 0, {"error": str(e)}


# ============================================================
# 1. 实时 HRRR 预报 - 核心风电变量
# ============================================================
def test_hrrr_realtime_wind():
    section("1. 实时 HRRR 预报 - 风电变量 (80m/100m/120m 风)")

    params = {
        "latitude": ERCOT_SITES["KFWS_Dallas"]["lat"],
        "longitude": ERCOT_SITES["KFWS_Dallas"]["lon"],
        "models": "ncep_hrrr_conus",
        "hourly": [
            "temperature_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_speed_80m",
            "wind_direction_80m",
            "wind_speed_100m",
            "wind_direction_100m",
            "wind_speed_120m",
            "wind_direction_120m",
            "wind_gusts_10m",
            "surface_pressure",
        ],
        "forecast_days": 2,
        "timezone": "America/Chicago",
    }

    import urllib.parse
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params, doseq=True)
    status, data = http_get_json(url)
    print(f"  HTTP {status}")

    if status == 200:
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        ws80 = hourly.get("wind_speed_80m", [])
        ws100 = hourly.get("wind_speed_100m", [])
        ws120 = hourly.get("wind_speed_120m", [])

        print(f"  预报时次: {len(times)}")
        print(f"  {'时次':<20} {'WS80m':<10} {'WS100m':<10} {'WS120m':<10} {'WD80m':<10}")
        print(f"  {'-'*60}")
        for i in range(min(12, len(times))):
            wd80 = hourly.get("wind_direction_80m", [])
            print(f"  {times[i]:<20} {fmt(ws80[i]):<10} {fmt(ws100[i]):<10} {fmt(ws120[i]):<10} {fmt(wd80[i]):<10}")

        # 统计
        vals = [v for v in ws80 if v is not None]
        if vals:
            print(f"  80m风统计: 均值={sum(vals)/len(vals):.1f} m/s, 最大={max(vals):.1f}, 最小={min(vals):.1f}")
    else:
        print(f"  ✗ 错误: {data}")

    return data if status == 200 else None


# ============================================================
# 2. 实时 HRRR 预报 - 光伏变量
# ============================================================
def test_hrrr_realtime_solar():
    section("2. 实时 HRRR 预报 - 光伏变量 (GHI/DNI/DHI)")

    sites_to_test = ["KHGX_Houston", "KMAF_Midland", "KAMA_Amarillo"]
    results = {}

    for site_name, site in [(k, ERCOT_SITES[k]) for k in sites_to_test]:
        import urllib.parse
        params = {
            "latitude": site["lat"],
            "longitude": site["lon"],
            "models": "ncep_hrrr_conus",
            "hourly": [
                "shortwave_radiation",
                "direct_radiation",
                "diffuse_radiation",
                "direct_normal_irradiance",
                "cloud_cover",
                "temperature_2m",
                "relative_humidity_2m",
            ],
            "forecast_days": 2,
            "timezone": "America/Chicago",
        }
        url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params, doseq=True)
        status, data = http_get_json(url)

        if status == 200:
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            ghi = hourly.get("shortwave_radiation", [])
            dni = hourly.get("direct_normal_irradiance", [])
            dhi = hourly.get("diffuse_radiation", [])
            cloud = hourly.get("cloud_cover", [])

            # 白天时段 (GHI > 0)
            day_hours = [(t, g, d, di, c) for t, g, d, di, c in zip(times, ghi, dni, dhi, cloud) if g and g > 0]
            if day_hours:
                avg_ghi = sum(h[1] for h in day_hours) / len(day_hours)
                avg_dni = sum(h[2] for h in day_hours) / len(day_hours)
                avg_cloud = sum(h[4] for h in day_hours) / len(day_hours)
                peak_ghi = max(h[1] for h in day_hours)
                print(f"  {site_name:<20} ({site['zone']:<10}): "
                      f"白天{len(day_hours)}h, GHI均值={avg_ghi:.0f}, 峰值={peak_ghi:.0f}, "
                      f"DNI均值={avg_dni:.0f}, 云量={avg_cloud:.0f}%")
                results[site_name] = {"avg_ghi": avg_ghi, "peak_ghi": peak_ghi, "avg_cloud": avg_cloud}
        else:
            print(f"  {site_name:<20}: ✗ HTTP {status}")

    return results


# ============================================================
# 3. 实时 HRRR - 对流参数
# ============================================================
def test_hrrr_convective():
    section("3. 实时 HRRR 预报 - 对流参数 (CAPE/Lifted Index/CIN)")

    import urllib.parse
    params = {
        "latitude": ERCOT_SITES["KFWS_Dallas"]["lat"],
        "longitude": ERCOT_SITES["KFWS_Dallas"]["lon"],
        "models": "ncep_hrrr_conus",
        "hourly": [
            "cape",
            "lifted_index",
            "convective_inhibition",
            "precipitation",
            "precipitation_probability",
            "thunderstorm_probability",
            "freezing_level_height",
            "boundary_layer_height",
        ],
        "forecast_days": 2,
        "timezone": "America/Chicago",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params, doseq=True)
    status, data = http_get_json(url)

    if status == 200:
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        cape = hourly.get("cape", [])
        li = hourly.get("lifted_index", [])
        cin = hourly.get("convective_inhibition", [])
        tstorm = hourly.get("thunderstorm_probability", [])
        pbl = hourly.get("boundary_layer_height", [])

        print(f"  {'时次':<20} {'CAPE':<10} {'LiftedIdx':<10} {'CIN':<10} {'雷暴%':<8} {'PBL(m)':<8}")
        print(f"  {'-'*66}")
        for i in range(min(24, len(times))):
            print(f"  {times[i]:<20} {cape[i] if cape[i] is not None else 'N/A':<10} "
                  f"{li[i] if li[i] is not None else 'N/A':<10} "
                  f"{cin[i] if cin[i] is not None else 'N/A':<10} "
                  f"{tstorm[i] if tstorm[i] is not None else 'N/A':<8} "
                  f"{pbl[i] if pbl[i] is not None else 'N/A':<8}")

        # 统计 CAPE 事件
        cape_vals = [c for c in cape if c is not None and c > 0]
        if cape_vals:
            print(f"  CAPE>0 时次: {len(cape_vals)}/{len(times)}, 最大={max(cape_vals):.0f} J/kg")
    else:
        print(f"  ✗ Error: {data}")

    return data if status == 200 else None


# ============================================================
# 4. 15分钟分辨率 HRRR
# ============================================================
def test_hrrr_15min():
    section("4. HRRR 15分钟分辨率")

    import urllib.parse
    params = {
        "latitude": ERCOT_SITES["KFWS_Dallas"]["lat"],
        "longitude": ERCOT_SITES["KFWS_Dallas"]["lon"],
        "models": "ncep_hrrr_conus_15min",
        "minutely_15": [
            "temperature_2m",
            "wind_speed_10m",
            "wind_speed_80m",
            "shortwave_radiation",
            "precipitation",
            "cape",
        ],
        "forecast_minutely_15": 48,  # 12小时
        "timezone": "America/Chicago",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params, doseq=True)
    status, data = http_get_json(url)

    if status == 200:
        m15 = data.get("minutely_15", {})
        times = m15.get("time", [])
        ws80 = m15.get("wind_speed_80m", [])
        ghi = m15.get("shortwave_radiation", [])
        print(f"  HTTP {status}, 15分钟时次: {len(times)}")
        print(f"  {'时次':<22} {'WS80m':<10} {'GHI':<10}")
        print(f"  {'-'*42}")
        for i in range(min(12, len(times))):
            print(f"  {times[i]:<22} {ws80[i] if ws80[i] is not None else 'N/A':<10} "
                  f"{ghi[i] if ghi[i] is not None else 'N/A':<10}")
    else:
        print(f"  ✗ Error: {data}")

    return data if status == 200 else None


# ============================================================
# 5. 历史 HRRR 预报
# ============================================================
def test_hrrr_historical():
    section("5. 历史 HRRR 预报 (Historical Forecast API)")

    import urllib.parse
    # 测试2024年7月某日数据（德州夏季雷暴季）
    params = {
        "latitude": ERCOT_SITES["KFWS_Dallas"]["lat"],
        "longitude": ERCOT_SITES["KFWS_Dallas"]["lon"],
        "models": "ncep_hrrr_conus",
        "start_date": "2024-07-15",
        "end_date": "2024-07-17",
        "hourly": [
            "temperature_2m",
            "wind_speed_80m",
            "wind_speed_10m",
            "shortwave_radiation",
            "cape",
            "precipitation",
        ],
        "timezone": "America/Chicago",
    }
    url = "https://historical-forecast-api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params, doseq=True)
    status, data = http_get_json(url, timeout=60)

    if status == 200:
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        print(f"  HTTP {status}, 历史时次: {len(times)}")
        if times:
            print(f"  时间范围: {times[0]} ~ {times[-1]}")
            ws80 = hourly.get("wind_speed_80m", [])
            vals = [v for v in ws80 if v is not None]
            if vals:
                print(f"  80m风: 均值={sum(vals)/len(vals):.1f}, 最大={max(vals):.1f}, 最小={min(vals):.1f} m/s")
            ghi = hourly.get("shortwave_radiation", [])
            day_ghi = [g for g in ghi if g and g > 0]
            if day_ghi:
                print(f"  白天GHI: 均值={sum(day_ghi)/len(day_ghi):.0f}, 峰值={max(day_ghi):.0f} W/m²")
            cape = hourly.get("cape", [])
            cape_vals = [c for c in cape if c is not None and c > 100]
            if cape_vals:
                print(f"  CAPE>100: {len(cape_vals)}/{len(times)} 时次, 最大={max(cape_vals):.0f} J/kg")
    else:
        print(f"  ✗ Error: {data}")

    return data if status == 200 else None


# ============================================================
# 6. 多站点 HRRR 批量测试
# ============================================================
def test_hrrr_multisite():
    section("6. 多站点 HRRR 批量测试 - 80m 风场对比")

    import urllib.parse
    # 构建批量坐标（逗号分隔）
    lats = ",".join(str(ERCOT_SITES[s]["lat"]) for s in ERCOT_SITES)
    lons = ",".join(str(ERCOT_SITES[s]["lon"]) for s in ERCOT_SITES)
    site_names = list(ERCOT_SITES.keys())

    params = {
        "latitude": lats,
        "longitude": lons,
        "models": "ncep_hrrr_conus",
        "hourly": [
            "wind_speed_80m",
            "wind_speed_10m",
            "shortwave_radiation",
            "temperature_2m",
        ],
        "forecast_hours": 6,  # 仅未来6小时
        "timezone": "America/Chicago",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params, doseq=True)
    status, data = http_get_json(url, timeout=60)

    if status == 200:
        print(f"  HTTP {status}, 同时请求 {len(site_names)} 个站点")
        for i, name in enumerate(site_names):
            hourly = data[i]["hourly"]
            times = hourly.get("time", [])
            ws80 = hourly.get("wind_speed_80m", [])
            ws10 = hourly.get("wind_speed_10m", [])
            ghi = hourly.get("shortwave_radiation", [])
            temp = hourly.get("temperature_2m", [])

            avg_ws80 = sum(v for v in ws80 if v is not None) / len([v for v in ws80 if v is not None]) if any(v is not None for v in ws80) else 0
            avg_ghi = sum(v for v in ghi if v is not None and v > 0) / len([v for v in ghi if v is not None and v > 0]) if any(v is not None and v > 0 for v in ghi) else 0
            print(f"  {name:<20} ({ERCOT_SITES[name]['zone']:<10}): "
                  f"WS80m={avg_ws80:.1f} m/s, "
                  f"GHI={avg_ghi:.0f} W/m², "
                  f"T={temp[0] if temp and temp[0] is not None else 'N/A':<8}°C")
    else:
        print(f"  ✗ Error: {data}")

    return data if status == 200 else None


# ============================================================
# 7. 多模型对比：HRRR vs GFS vs NAM vs NBM
# ============================================================
def test_model_comparison():
    section("7. 多模型对比 - KFWS(达拉斯) 80m风")

    models = [
        ("HRRR 3km",   "ncep_hrrr_conus"),
        ("GFS 0.11°",  "ncep_gfs_seamless"),
        ("NAM 3km",    "ncep_nam_conus"),
        ("NBM 2.5km",  "ncep_nbm_conus"),
    ]

    import urllib.parse
    for model_name, model_key in models:
        params = {
            "latitude": ERCOT_SITES["KFWS_Dallas"]["lat"],
            "longitude": ERCOT_SITES["KFWS_Dallas"]["lon"],
            "models": model_key,
            "hourly": [
                "wind_speed_80m",
                "wind_speed_10m",
                "temperature_2m",
                "surface_pressure",
            ],
            "forecast_hours": 12,
            "timezone": "America/Chicago",
        }
        url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params, doseq=True)
        status, data = http_get_json(url, timeout=45)

        if status == 200:
            hourly = data.get("hourly", {})
            ws80 = hourly.get("wind_speed_80m", [])
            vals = [v for v in ws80 if v is not None]
            if vals:
                print(f"  {model_name:<15}: 80m风均值={sum(vals)/len(vals):.1f} m/s, "
                      f"最大={max(vals):.1f}, 时次={len(vals)}")
        else:
            print(f"  {model_name:<15}: ✗ HTTP {status}")


# ============================================================
# 8. 气压层变量
# ============================================================
def test_hrrr_pressure_levels():
    section("8. HRRR 气压层变量")

    import urllib.parse
    params = {
        "latitude": ERCOT_SITES["KFWS_Dallas"]["lat"],
        "longitude": ERCOT_SITES["KFWS_Dallas"]["lon"],
        "models": "ncep_hrrr_conus",
        "hourly": [
            "temperature_2m",
            "wind_speed_10m",
        ],
        "pressure_levels": {
            "temperature": ["850", "700", "500", "300", "200"],
            "wind_speed": ["850", "700", "500", "300", "200"],
            "geopotential_height": ["850", "700", "500", "300", "200"],
        },
        "forecast_hours": 6,
        "timezone": "America/Chicago",
    }
    # 手动构建 URL（因为 pressure_levels 是嵌套参数）
    url = ("https://api.open-meteo.com/v1/forecast?"
           f"latitude={ERCOT_SITES['KFWS_Dallas']['lat']}&"
           f"longitude={ERCOT_SITES['KFWS_Dallas']['lon']}&"
           "models=ncep_hrrr_conus&"
           "hourly=temperature_2m,wind_speed_10m&"
           "pressure_levels=temperature,wind_speed,geopotential_height&"
           "pressure_levels_levels=850,700,500,300,200&"
           "forecast_hours=6&timezone=America/Chicago")
    status, data = http_get_json(url, timeout=45)

    if status == 200:
        # 气压层数据在 hourly 内，以 pressure_levels 为前缀
        hourly = data.get("hourly", {})
        print(f"  HTTP {status}, 可用变量: {[k for k in hourly.keys() if 'pressure' in k.lower() or 'temperature' in k.lower()]}")
        for level in ["850", "500", "200"]:
            temp_key = f"temperature_{level}_hPa"
            wind_key = f"wind_speed_{level}_hPa"
            hgt_key = f"geopotential_height_{level}_hPa"
            if temp_key in hourly:
                vals = [v for v in hourly[temp_key] if v is not None]
                if vals:
                    print(f"  {level}hPa: T={vals[0]:.1f}°C, "
                          f"WS={hourly[wind_key][0] if wind_key in hourly and hourly[wind_key][0] is not None else 'N/A'} m/s, "
                          f"HGT={hourly[hgt_key][0] if hgt_key in hourly and hourly[hgt_key][0] is not None else 'N/A'} gpm")
    else:
        print(f"  ✗ Error: {data}")

    return data if status == 200 else None


# ============================================================
# 主测试
# ============================================================
def main():
    all_results = {}
    all_results["test_time"] = datetime.now(timezone.utc).isoformat()

    print(f"Open-Meteo HRRR/NWP 测试 - {all_results['test_time']}")
    print(f"ERCOT 站点: {len(ERCOT_SITES)} 个")

    all_results["hrrr_wind"] = test_hrrr_realtime_wind()
    all_results["hrrr_solar"] = test_hrrr_realtime_solar()
    all_results["hrrr_convective"] = test_hrrr_convective()
    all_results["hrrr_15min"] = test_hrrr_15min()
    all_results["hrrr_historical"] = test_hrrr_historical()
    all_results["hrrr_multisite"] = test_hrrr_multisite()
    all_results["model_comparison"] = test_model_comparison()
    all_results["pressure_levels"] = test_hrrr_pressure_levels()

    # 汇总
    section("===== 测试汇总 =====")
    tests = [
        ("HRRR 实时风电变量",         all_results["hrrr_wind"]),
        ("HRRR 实时光伏变量",         all_results["hrrr_solar"]),
        ("HRRR 对流参数",             all_results["hrrr_convective"]),
        ("HRRR 15分钟分辨率",         all_results["hrrr_15min"]),
        ("HRRR 历史预报 (2024)",      all_results["hrrr_historical"]),
        ("HRRR 多站点批量",           all_results["hrrr_multisite"]),
        ("多模型对比 (HRRR/GFS/NAM/NBM)", all_results["model_comparison"]),
        ("HRRR 气压层变量",           all_results["pressure_levels"]),
    ]
    for name, result in tests:
        status = "✅" if result is not None else "❌"
        print(f"  {status} {name}")

    # 保存结果
    out_path = Path(__file__).parent / "openmeteo_hrrr_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  结果保存: {out_path}")


if __name__ == "__main__":
    main()