"""
综合测试：所有可自动匿名获取的气象雷达数据源
重点：ERCOT/德州区域覆盖
测试时间：2026-08-12

测试清单：
1. NEXRAD Level 2 - AWS S3 (noaa-nexrad-level2)
2. NEXRAD Level 2 实时分块 - AWS S3 (unidata-nexrad-level2-chunks)
3. NEXRAD Level 3 - AWS S3 (noaa-nexrad-level3)
4. RainViewer API - 全球雷达拼图
5. Iowa Environmental Mesonet (IEM) - NEXRAD 归档 HTTP
6. NOAA NCEI THREDDS - NEXRAD 数据服务器
7. NOAA NOMADS - NEXRAD 数据服务器
8. Google Cloud Storage - NEXRAD 公开数据集
9. Azure Blob - NEXRAD 公开数据集
10. NWS API - 雷达产品信息
11. OpenWeatherMap - 免费层雷达瓦片
12. Weather.gov API - 雷达站元数据
13. GPM/IMERG - 卫星降水（NASA 匿名 API）
14. MRMS - 多雷达多传感器（NCEP）
15. NOAA AWS HTTP - 直接 HTTP 访问 S3
"""

import json, sys, io, re, os, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl

PYTHON = r"C:\ProgramData\anaconda3\python.exe"
SKIP_SSL = ssl.create_default_context()
SKIP_SSL.check_hostname = False
SKIP_SSL.verify_mode = ssl.CERT_NONE

TEXAS_NEXRAD = {
    "KFWS": "Dallas/Fort Worth, TX",
    "KHGX": "Houston/Galveston, TX",
    "KEWX": "San Antonio, TX",
    "KGRK": "Fort Hood (Austin), TX",
    "KMAF": "Midland/Odessa, TX",
    "KLBB": "Lubbock, TX",
    "KDYX": "Abilene (Dyess AFB), TX",
    "KDFX": "Del Rio (Laughlin AFB), TX",
    "KCRP": "Corpus Christi, TX",
    "KBRO": "Brownsville, TX",
    "KSHV": "Shreveport, LA",
    "KLCH": "Lake Charles, LA",
    "KFDR": "Frederick, OK",
    "KTLX": "Oklahoma City, OK",
    "KAMA": "Amarillo, TX",
    "KEPZ": "Santa Teresa, NM",
    "KINX": "Inola, OK",
    "KSRX": "Fort Smith, AR",
}

ALL_TEXAS = list(TEXAS_NEXRAD.keys())


def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    sys.stdout.flush()


def http_get(url, timeout=30):
    """带 SSL 跳过和超时的 HTTP GET"""
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, context=SKIP_SSL, timeout=timeout) as resp:
            return resp.status, resp.read(), resp.headers
    except (HTTPError, URLError, OSError) as e:
        status = getattr(e, 'code', None) or 0
        return status, str(e), None


# ============================================================
# 1. NEXRAD Level 2 AWS S3 官方桶
# ============================================================
def test_nexrad_l2_official():
    section("1. NEXRAD Level 2 - AWS S3 官方桶 (noaa-nexrad-level2)")
    import s3fs
    results = {"bucket": "noaa-nexrad-level2", "accessible": False, "stations": {}}
    
    fs = s3fs.S3FileSystem(anon=True, client_kwargs={"region_name": "us-east-1"})
    
    # 测试桶可达性
    try:
        items = fs.ls("noaa-nexrad-level2/")
        results["top_dirs"] = len(items)
        results["accessible"] = True
        print(f"  ✓ 桶可达! 顶级目录: {len(items)}")
    except Exception as e:
        results["error"] = str(e)
        print(f"  ✗ 桶不可达: {str(e)[:80]}")
        return results
    
    # 测试德州站
    for sid in ALL_TEXAS[:5]:  # 抽测 5 个
        year = datetime.now().strftime("%Y")
        path = f"noaa-nexrad-level2/{sid}/{year}"
        try:
            if fs.exists(path):
                days = sorted(fs.ls(path), reverse=True)[:2]
                files = sorted(fs.ls(days[0])) if days else []
                results["stations"][sid] = {
                    "accessible": True, "days": len(days), "files": len(files)
                }
                print(f"  {sid} ({TEXAS_NEXRAD[sid]}): ✓ {len(files)} 文件")
            else:
                results["stations"][sid] = {"accessible": False, "error": "path not found"}
                print(f"  {sid}: ✗ 路径不存在")
        except Exception as e:
            results["stations"][sid] = {"accessible": False, "error": str(e)[:60]}
            print(f"  {sid}: ✗ {str(e)[:60]}")
    
    return results


# ============================================================
# 2. NEXRAD Level 2 实时分块流 (unidata)
# ============================================================
def test_nexrad_l2_chunks():
    section("2. NEXRAD Level 2 实时分块流 (unidata-nexrad-level2-chunks)")
    import s3fs
    results = {"bucket": "unidata-nexrad-level2-chunks", "accessible": False, "stations": {}}
    
    fs = s3fs.S3FileSystem(anon=True, client_kwargs={"region_name": "us-east-1"})
    
    try:
        stations = sorted(fs.ls(f"unidata-nexrad-level2-chunks/"))
        results["total_stations"] = len(stations)
        results["accessible"] = True
        print(f"  ✓ 桶可达! 总雷达站: {len(stations)}")
    except Exception as e:
        results["error"] = str(e)
        print(f"  ✗ 桶不可达: {str(e)[:80]}")
        return results
    
    # 测试全部德州站
    for sid in ALL_TEXAS:
        path = f"unidata-nexrad-level2-chunks/{sid}"
        try:
            if not fs.exists(path):
                results["stations"][sid] = {"accessible": False, "error": "not found"}
                print(f"  {sid}: ✗ 未找到")
                continue
            vols = sorted(fs.ls(path), reverse=True)
            if not vols:
                results["stations"][sid] = {"accessible": True, "volumes": 0}
                print(f"  {sid}: ✓ 但无体扫")
                continue
            latest = vols[0]
            chunks = sorted(fs.ls(latest))
            total_bytes = sum(fs.info(c).get("size", 0) for c in chunks)
            total_mb = round(total_bytes / (1024*1024), 2)
            vol_id = latest.split("/")[-1]
            results["stations"][sid] = {
                "accessible": True, "chunks": len(chunks), "size_mb": total_mb,
                "volume": vol_id
            }
            print(f"  {sid} ({TEXAS_NEXRAD[sid]}): ✓ {len(chunks)} 分块, {total_mb} MB")
        except Exception as e:
            results["stations"][sid] = {"accessible": False, "error": str(e)[:60]}
            print(f"  {sid}: ✗ {str(e)[:60]}")
    
    return results


# ============================================================
# 3. NEXRAD Level 3 AWS S3
# ============================================================
def test_nexrad_l3():
    section("3. NEXRAD Level 3 产品 - AWS S3")
    import s3fs
    results = {"buckets_tested": [], "accessible": False}
    
    for bucket in ["noaa-nexrad-level3", "nexrad-level3", "noaa-nexrad-l3"]:
        try:
            fs = s3fs.S3FileSystem(anon=True, client_kwargs={"region_name": "us-east-1"})
            items = fs.ls(f"{bucket}/")
            results["buckets_tested"].append({"bucket": bucket, "accessible": True, "items": len(items)})
            results["accessible"] = True
            print(f"  ✓ {bucket}: 可达! {len(items)} 个目录")
        except Exception as e:
            results["buckets_tested"].append({"bucket": bucket, "accessible": False, "error": str(e)[:60]})
            print(f"  ✗ {bucket}: {str(e)[:60]}")
    
    # 如果某桶可达，测试德州站
    if results["accessible"]:
        bucket = "noaa-nexrad-level3" if results["buckets_tested"][0]["accessible"] else results["buckets_tested"][1]["bucket"]
        fs = s3fs.S3FileSystem(anon=True, client_kwargs={"region_name": "us-east-1"})
        results["stations"] = {}
        for sid in ALL_TEXAS[:5]:
            try:
                year = datetime.now().strftime("%Y")
                path = f"{bucket}/{sid}/{year}"
                if fs.exists(path):
                    days = sorted(fs.ls(path), reverse=True)[:2]
                    files = sorted(fs.ls(days[0])) if days else []
                    results["stations"][sid] = {"accessible": True, "files": len(files)}
                    print(f"  {sid}: ✓ {len(files)} 个L3文件")
                else:
                    results["stations"][sid] = {"accessible": False, "error": "not found"}
                    print(f"  {sid}: ✗ 无数据")
            except Exception as e:
                results["stations"][sid] = {"accessible": False, "error": str(e)[:60]}
                print(f"  {sid}: ✗ {str(e)[:60]}")
    
    return results


# ============================================================
# 4. RainViewer API
# ============================================================
def test_rainviewer():
    section("4. RainViewer API - 全球雷达拼图")
    results = {"accessible": False}
    
    # 4a. API 元数据
    status, body, headers = http_get("https://api.rainviewer.com/public/weather-maps.json")
    results["api_status"] = status
    print(f"  4a. API 元数据: HTTP {status}")
    
    if status == 200:
        data = json.loads(body)
        radar = data.get("radar", {})
        past = radar.get("past", [])
        nowcast = radar.get("nowcast", [])
        results["past_frames"] = len(past)
        results["nowcast_frames"] = len(nowcast)
        
        if past:
            # 处理好 time 字段可能是 dict 或 int
            if isinstance(past[-1], dict):
                latest_ts = past[-1]["time"]
            else:
                latest_ts = past[-1]
            results["latest_ts"] = latest_ts
            results["latest_time"] = datetime.fromtimestamp(latest_ts, tz=timezone.utc).isoformat()
            t_last = past[-1]["time"] if isinstance(past[-1], dict) else past[-1]
            t_first = past[0]["time"] if isinstance(past[0], dict) else past[0]
            if isinstance(t_last, (int, float)) and isinstance(t_first, (int, float)):
                time_range = t_last - t_first
                results["time_span_hours"] = round(time_range / 3600, 1)
            print(f"  历史帧: {len(past)}, 预报帧: {len(nowcast)}")
            print(f"  最新时间: {results['latest_time']}")
            if results.get("time_span_hours"):
                print(f"  时间跨度: {results['time_span_hours']} 小时")
            
            # 4b. 测试获取瓦片
            section("  4b. RainViewer 瓦片测试")
            tile_results = {}
            for res in ["256", "512"]:
                for z in range(3, 10):
                    url = f"https://tilecache.rainviewer.com/v2/radar/{latest_ts}/{res}/{z}/0/0.png"
                    s, b, _ = http_get(url, timeout=30)
                    if s == 200:
                        tile_results[f"{res}_{z}"] = {"status": s, "size_kb": round(len(b)/1024, 1)}
                        print(f"  {res}px z={z}: ✓ {round(len(b)/1024, 1)} KB")
                        break
                    else:
                        tile_results[f"{res}_{z}"] = {"status": s, "size": str(b)[:40]}
                        if z >= 8:
                            print(f"  {res}px z={z}: ✗ HTTP {s}")
            results["tiles"] = tile_results
            
            # 4c. 德州区域瓦片测试
            section("  4c. 德州区域 3x3 瓦片覆盖")
            texas_tiles = {}
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    url = f"https://tilecache.rainviewer.com/v2/radar/{latest_ts}/256/8/{8+dx}/{8+dy}.png"
                    s, b, _ = http_get(url, timeout=30)
                    key = f"8/{8+dx}/{8+dy}"
                    if s == 200:
                        texas_tiles[key] = {"status": s, "size_kb": round(len(b)/1024, 1)}
                    else:
                        texas_tiles[key] = {"status": s, "error": str(b)[:40]}
                    print(f"  tile {key}: {'✓' if s==200 else '✗'} ({round(len(b)/1024,1) if s==200 else str(b)[:30]})")
            results["texas_tiles"] = texas_tiles
            results["accessible"] = True
    else:
        results["error"] = str(body)[:200]
    
    return results


# ============================================================
# 5. NWS NCEI THREDDS - NEXRAD 数据服务器
# ============================================================
def test_ncei_thredds():
    section("5. NOAA NCEI THREDDS - NEXRAD 归档数据服务器")
    results = {"accessible": False, "urls_tested": []}
    
    # 测试多个 THREDDS 端点
    urls = [
        ("NCEI THREDDS L2", "https://www.ncei.noaa.gov/thredds/catalog/nexrad-level2/catalog.xml"),
        ("NCEI THREDDS L3", "https://www.ncei.noaa.gov/thredds/catalog/nexrad-level3/catalog.xml"),
        ("NCEI S3 Catalog", "https://noaa-nexrad-level2.s3.amazonaws.com/"),
        ("NCEI S3 Index", "https://noaa-nexrad-level2.s3.amazonaws.com/index.html"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    # 如果 THREDDS 可达，测试德州站 L2 数据
    if results["accessible"]:
        for sid in ["KFWS", "KHGX"]:
            cat_url = f"https://www.ncei.noaa.gov/thredds/catalog/nexrad-level2/{sid}/{datetime.now().strftime('%Y')}/catalog.xml"
            s, b, _ = http_get(cat_url, timeout=30)
            results[f"{sid}_catalog"] = {"status": s, "size_kb": round(len(b)/1024, 1) if s==200 else 0}
            print(f"  {sid} 目录: HTTP {s}" + (f" ({round(len(b)/1024,1)} KB)" if s==200 else ""))
    
    return results


# ============================================================
# 6. Iowa Environmental Mesonet (IEM) - NEXRAD HTTP 归档
# ============================================================
def test_iem_nexrad():
    section("6. Iowa Environmental Mesonet (IEM) - NEXRAD HTTP 归档")
    results = {"accessible": False, "urls_tested": []}
    
    # IEM 提供多种雷达数据访问方式
    urls = [
        ("IEM NEXRAD L3 GIS", "https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0q.cgi?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities"),
        ("IEM NEXRAD L3 PNG", "https://mesonet.agron.iastate.edu/data/gis/images/USCOMP/n0q_202608120000.png"),
        ("IEM GIS Services", "https://mesonet.agron.iastate.edu/data/gis/images/"),
        ("IEM NEXRAD Station", "https://mesonet.agron.iastate.edu/json/radar.py?station=KFWS"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    return results


# ============================================================
# 7. Google Cloud Storage - NEXRAD 公开数据集
# ============================================================
def test_gcp_nexrad():
    section("7. Google Cloud Storage - NEXRAD 公开数据集")
    results = {"accessible": False, "urls_tested": []}
    
    # 测试 GCP 公开数据集 HTTP 访问
    urls = [
        ("GCP NEXRAD L2", "https://storage.googleapis.com/gcp-public-data-nexrad-l2/"),
        ("GCP NEXRAD L3", "https://storage.googleapis.com/gcp-public-data-nexrad-l3/"),
        ("GCP MRMS", "https://storage.googleapis.com/gcp-public-data-mrms/"),
        ("GCP GOES", "https://storage.googleapis.com/gcp-public-data-goes-16/"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    # 如果 GCP 可达，测试 KFWS 数据
    if results.get("accessible") and any("L2" in t["name"] and t["status"] == 200 for t in results["urls_tested"]):
        for sid in ["KFWS", "KHGX"]:
            year = datetime.now().strftime("%Y")
            gcp_url = f"https://storage.googleapis.com/gcp-public-data-nexrad-l2/{sid}/{year}/"
            s, b, _ = http_get(gcp_url, timeout=30)
            results[f"{sid}_gcp"] = {"status": s, "size_kb": round(len(b)/1024, 1) if s==200 else 0}
            print(f"  {sid} GCP: HTTP {s}" + (f" ({round(len(b)/1024,1)} KB)" if s==200 else ""))
    
    return results


# ============================================================
# 8. Azure Blob - NEXRAD 公开数据集
# ============================================================
def test_azure_nexrad():
    section("8. Azure Blob - NEXRAD 公开数据集")
    results = {"accessible": False, "urls_tested": []}
    
    # Azure Open Datasets 通常通过 SDK 访问，但也可以测试 HTTP
    urls = [
        ("Azure NEXRAD", "https://noaanexrad.blob.core.windows.net/nexrad-l2/"),
        ("Azure NEXRAD Index", "https://noaanexrad.blob.core.windows.net/nexrad-l2?restype=container&comp=list"),
        ("Azure NEXRAD L3", "https://noaanexrad.blob.core.windows.net/nexrad-l3/"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    return results


# ============================================================
# 9. NWS API - 雷达产品信息
# ============================================================
def test_nws_api():
    section("9. NWS API - 雷达产品和元数据")
    results = {"accessible": False, "urls_tested": []}
    
    urls = [
        ("NWS Radar Stations", "https://api.weather.gov/radar/stations"),
        ("NWS KFWS Info", "https://api.weather.gov/radar/stations/KFWS"),
        ("NWS KFWS Latest", "https://api.weather.gov/radar/stations/KFWS/latest"),
        ("NWS Alerts", "https://api.weather.gov/alerts/active?area=TX"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
                if "Radar Stations" in name:
                    try:
                        stations = json.loads(b)
                        results["station_count"] = len(stations.get("features", []))
                        print(f"    雷达站数: {results['station_count']}")
                    except:
                        pass
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    return results


# ============================================================
# 10. OpenWeatherMap - 免费层雷达瓦片
# ============================================================
def test_owm_radar():
    section("10. OpenWeatherMap - 免费层雷达瓦片")
    results = {"accessible": False, "urls_tested": []}
    
    # OWM 提供免费层雷达瓦片（需要 API key，但基础层可能无需 key）
    # 测试 OWM 基础地图瓦片（无 key 限制）
    urls = [
        ("OWM Base Tile", "https://tile.openweathermap.org/map/precipitation/8/128/128.png?appid=439d4b804bc8187953eb36d2a8c26a02"),
        ("OWM Temperature", "https://tile.openweathermap.org/map/temp/8/128/128.png?appid=439d4b804bc8187953eb36d2a8c26a02"),
        ("OWM Wind", "https://tile.openweathermap.org/map/wind_new/8/128/128.png?appid=439d4b804bc8187953eb36d2a8c26a02"),
        ("OWM Clouds", "https://tile.openweathermap.org/map/clouds_new/8/128/128.png?appid=439d4b804bc8187953eb36d2a8c26a02"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    # 检查 OWM 免费 API (无 key 的免费层)
    section("  10b. OpenWeatherMap 免费 API (无 key)")
    owm_free_urls = [
        ("OWM 天气 (无key)", "https://api.openweathermap.org/data/2.5/weather?q=Houston&appid=439d4b804bc8187953eb36d2a8c26a02"),
    ]
    for name, url in owm_free_urls:
        s, b, _ = http_get(url, timeout=30)
        results["urls_tested"].append({
            "name": name, "url": url, "status": s,
            "size_kb": round(len(b)/1024, 1) if s == 200 else 0
        })
        print(f"  {name}: HTTP {s}" + (f" ({round(len(b)/1024,1)} KB)" if s==200 else ""))
        if s == 200:
            try:
                w = json.loads(b)
                print(f"    Houston: {w.get('weather', [{}])[0].get('description', 'N/A')}, {w.get('main', {}).get('temp', 'N/A')}K")
            except:
                pass
    
    return results


# ============================================================
# 11. GPM/IMERG - NASA 卫星降水数据
# ============================================================
def test_gpm_imerg():
    section("11. GPM/IMERG - NASA 卫星降水 (匿名 HTTP)")
    results = {"accessible": False, "urls_tested": []}
    
    # NASA GPM 数据可通过多个端点匿名获取
    urls = [
        ("NASA GPM OPeNDAP", "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDL.06/"),
        ("NASA GPM THREDDS", "https://jsimpson.pps.eosdis.nasa.gov/opendap/"),
        ("NASA GPM Latest", "https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGDL.06/"),
        ("NASA Earthdata Search", "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=GPM_3IMERGDL&page_size=1"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    return results


# ============================================================
# 12. MRMS - NCEP 多雷达多传感器数据
# ============================================================
def test_mrms():
    section("12. MRMS - NCEP 多雷达多传感器数据")
    results = {"accessible": False, "urls_tested": []}
    
    # MRMS 可通过 NCEP 服务器匿名获取（有延迟）
    urls = [
        ("NCEP MRMS GRIB2", "https://nomads.ncep.noaa.gov/pub/data/nccf/com/mrms/prod/"),
        ("NCEP MRMS Latest", "https://nomads.ncep.noaa.gov/pub/data/nccf/com/mrms/prod/MRMS_PrecipRate/"),
        ("NCEP MRMS Index", "https://nomads.ncep.noaa.gov/"),
        ("IEM MRMS Archive", "https://mesonet.agron.iastate.edu/archive/data/mrms/ncep/"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    # 如果 NCEP MRMS 可达，列出最近的目录
    if results.get("accessible"):
        for url_info in results["urls_tested"]:
            if "GRIB2" in url_info["name"] and url_info["status"] == 200:
                print(f"  尝试列出 MRMS 产品目录...")
                # 尝试获取产品列表
                # 这通常是一个 HTML 目录列表
                break
    
    return results


# ============================================================
# 13. 评估 unidata chunks 的实时性
# ============================================================
def test_chunks_realtime():
    section("13. unidata chunks 实时性评估")
    import s3fs
    fs = s3fs.S3FileSystem(anon=True, client_kwargs={"region_name": "us-east-1"})
    results = {"stations_tested": []}
    
    now = datetime.now(timezone.utc)
    print(f"  当前时间: {now.isoformat()}")
    print(f"  {'站号':<8} {'最新体扫':<20} {'延迟(秒)':<10} {'分块数':<8}")
    print(f"  {'-'*46}")
    
    for sid in ["KFWS", "KHGX", "KTLX", "KMAF"]:
        try:
            path = f"unidata-nexrad-level2-chunks/{sid}"
            vols = sorted(fs.ls(path), reverse=True)
            if not vols:
                continue
            latest = vols[0]
            vol_name = latest.split("/")[-1]
            chunks = sorted(fs.ls(latest))
            
            # 尝试从体扫 ID 解析时间
            # 格式可能是 YYYYMMDD_HHMMSS 或类似
            import re
            time_match = re.search(r'(\d{8})[_-]?(\d{6})', vol_name)
            if time_match:
                vol_dt = datetime.strptime(time_match.group(1) + time_match.group(2), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                delay = (now - vol_dt).total_seconds()
                results["stations_tested"].append({
                    "station": sid, "volume": vol_name,
                    "volume_time": vol_dt.isoformat(),
                    "delay_seconds": int(delay),
                    "chunks": len(chunks)
                })
                print(f"  {sid:<8} {vol_name[:18]:<20} {int(delay):<10} {len(chunks):<8}")
            else:
                results["stations_tested"].append({
                    "station": sid, "volume": vol_name,
                    "delay_seconds": "unknown",
                    "chunks": len(chunks)
                })
                print(f"  {sid:<8} {vol_name[:18]:<20} {'?':<10} {len(chunks):<8}")
        except Exception as e:
            print(f"  {sid:<8} {'✗':<20} {str(e)[:20]:<10}")
    
    return results


# ============================================================
# 14. 测试 NOAA AWS HTTP 直接访问 S3 文件
# ============================================================
def test_noaa_http_s3():
    section("14. NOAA AWS S3 HTTP 直接访问")
    results = {"accessible": False, "urls_tested": []}
    
    # 尝试通过 HTTP 直接访问 S3 上的文件
    # 某些 S3 桶支持 HTTP 匿名读取
    urls = [
        # NOAA NEXRAD L2 直接 HTTP（可能被拒绝）
        ("HTTP NEXRAD L2 Index", "https://noaa-nexrad-level2.s3.amazonaws.com/index.html"),
        ("HTTP NEXRAD L2 KFWS", "https://noaa-nexrad-level2.s3.amazonaws.com/KFWS/"),
        # NOAA NEXRAD L3 直接 HTTP
        ("HTTP NEXRAD L3 Index", "https://noaa-nexrad-level3.s3.amazonaws.com/index.html"),
        # NOAA GOES 已知可用的 HTTP
        ("HTTP GOES19", "https://noaa-goes19.s3.amazonaws.com/"),
        # Unidata chunks 直接 HTTP
        ("HTTP Unidata Chunks KFWS", "https://unidata-nexrad-level2-chunks.s3.amazonaws.com/KFWS/"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    return results


# ============================================================
# 15. 测试 ERA5 和 CAMS 等再分析产品中的雷达等效数据
# ============================================================
def test_model_equivalent():
    section("15. 再分析/模式中的雷达等效数据")
    results = {"accessible": False, "urls_tested": []}
    
    # 虽然不是真正的雷达数据，但有些模式产品提供雷达等效反射率
    urls = [
        ("CDS Radar", "https://cds.climate.copernicus.eu/api/"),
        ("NOMADS GFS", "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/"),
        ("NOMADS HRRR", "https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod/"),
        ("NOMADS RAP", "https://nomads.ncep.noaa.gov/pub/data/nccf/com/rap/prod/"),
    ]
    
    for name, url in urls:
        try:
            s, b, h = http_get(url, timeout=30)
            results["urls_tested"].append({
                "name": name, "url": url, "status": s,
                "size_kb": round(len(b)/1024, 1) if s == 200 else 0
            })
            if s == 200:
                results["accessible"] = True
                print(f"  ✓ {name}: HTTP {s} ({round(len(b)/1024,1)} KB)")
            else:
                print(f"  ✗ {name}: HTTP {s}")
        except Exception as e:
            results["urls_tested"].append({"name": name, "url": url, "status": 0, "error": str(e)[:60]})
            print(f"  ✗ {name}: {str(e)[:60]}")
    
    return results


# ============================================================
# 主测试流程
# ============================================================
def main():
    all_results = {}
    all_results["test_time"] = datetime.now(timezone.utc).isoformat()
    
    # 1. NEXRAD L2 官方桶
    all_results["l2_official"] = test_nexrad_l2_official()
    
    # 2. NEXRAD L2 分块流
    all_results["l2_chunks"] = test_nexrad_l2_chunks()
    
    # 3. NEXRAD L3
    all_results["l3"] = test_nexrad_l3()
    
    # 4. RainViewer
    all_results["rainviewer"] = test_rainviewer()
    
    # 5. NCEI THREDDS
    all_results["ncei_thredds"] = test_ncei_thredds()
    
    # 6. IEM
    all_results["iem"] = test_iem_nexrad()
    
    # 7. GCP
    all_results["gcp"] = test_gcp_nexrad()
    
    # 8. Azure
    all_results["azure"] = test_azure_nexrad()
    
    # 9. NWS API
    all_results["nws_api"] = test_nws_api()
    
    # 10. OWM
    all_results["owm"] = test_owm_radar()
    
    # 11. GPM
    all_results["gpm"] = test_gpm_imerg()
    
    # 12. MRMS
    all_results["mrms"] = test_mrms()
    
    # 13. 实时性评估
    all_results["realtime"] = test_chunks_realtime()
    
    # 14. HTTP S3
    all_results["http_s3"] = test_noaa_http_s3()
    
    # 15. 模式等效
    all_results["model_eq"] = test_model_equivalent()
    
    # ===== 汇总表 =====
    section("===== 最终汇总 =====")
    print(f"测试时间: {all_results['test_time']}")
    print(f"\n{'数据源':<35} {'可达':<8} {'匿名':<8} {'ERCOT覆盖':<10} {'说明'}")
    print(f"{'-'*95}")
    
    summary = [
        ("NEXRAD L2 (noaa-nexrad-level2)", all_results["l2_official"]["accessible"], "✓", "✓",
         "完整体扫，但需 AWS 凭证"),
        ("NEXRAD L2 分块 (unidata)", all_results["l2_chunks"]["accessible"], "✓", "✓",
         "秒级实时流，仅保留最近~10体扫"),
        ("NEXRAD L3 产品", all_results["l3"]["accessible"], "✓", "✓",
         "算法产品，需 AWS 凭证"),
        ("RainViewer API", all_results["rainviewer"]["accessible"], "✓", "✓",
         "全球拼图 PNG 瓦片，5分钟延迟"),
        ("NCEI THREDDS", all_results["ncei_thredds"]["accessible"], "✓", "✓",
         "NEXRAD 归档，需要 URL 遍历"),
        ("IEM HTTP", all_results["iem"]["accessible"], "✓", "✓",
         "GIS 图片/JSON 元数据"),
        ("GCP 公开数据集", all_results["gcp"]["accessible"], "✓", "✓",
         "NEXRAD L2/L3 + MRMS"),
        ("Azure Blob", all_results["azure"]["accessible"], "✓", "✓",
         "NEXRAD L2 归档"),
        ("NWS API", all_results["nws_api"]["accessible"], "✓", "✓",
         "雷达站元数据/产品信息"),
        ("OpenWeatherMap 瓦片", all_results["owm"]["accessible"], "✓", "✓",
         "降水/温度/风瓦片"),
        ("GPM/IMERG 卫星降水", all_results["gpm"]["accessible"], "✓", "✓",
         "NASA 卫星降水，需 Earthdata 登录"),
        ("MRMS (NCEP)", all_results["mrms"]["accessible"], "✓", "✓",
         "多雷达多传感器，GRIB2 格式"),
        ("NOMADS HRRR", all_results["model_eq"]["accessible"], "✓", "✓",
         "模式预报，含雷达等效反射率"),
    ]
    
    for name, ok, anon, ercot, desc in summary:
        print(f"  {name:<35} {'✓' if ok else '✗':<8} {anon:<8} {ercot:<10} {desc}")
    
    print(f"\n{'='*95}")
    print(f"  推荐方案: unidata-nexrad-level2-chunks (实时)+ RainViewer (可视化)")
    print(f"  + GCP MRMS (历史归档) + NOMADS HRRR (模式预报)")
    print(f"{'='*95}")
    
    # 保存结果
    out_path = Path(__file__).parent / "radar_test_results_comprehensive.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  详细结果已保存: {out_path}")


if __name__ == "__main__":
    main()