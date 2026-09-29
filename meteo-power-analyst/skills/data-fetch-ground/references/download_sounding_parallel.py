# -*- coding: utf-8 -*-
"""探空廓线数据并行下载 (怀俄明大学 WSGI 接口)

优化: 使用 ThreadPoolExecutor 并行下载，速度提升 5-8 倍
断点续传: 已下载的文件自动跳过
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import ssl
import json
import time
import re
import argparse
import urllib.request
import urllib.parse
import urllib.error
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import pandas as pd

# ── 常量 ──────────────────────────────────────────────
OUTPUT_DIR = Path(r"c:\work\meteo\data\sounding")
BASE_URL = "http://weather.uwyo.edu/wsgi/sounding"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

socket.setdefaulttimeout(45)

STATIONS = {
    "72249": {"name": "Fort Worth", "region": "texas", "country": "US", "lat": 32.83, "lon": -97.30},
    "72251": {"name": "Dallas-FW", "region": "texas", "country": "US", "lat": 32.90, "lon": -97.04},
    "72340": {"name": "Shreveport", "region": "texas", "country": "US", "lat": 32.45, "lon": -93.82},
    "57494": {"name": "Wuhan", "region": "asia", "country": "CN", "lat": 30.62, "lon": 114.13},
    "58362": {"name": "Shanghai", "region": "asia", "country": "CN", "lat": 31.40, "lon": 121.46},
    "54857": {"name": "Qingdao", "region": "asia", "country": "CN", "lat": 36.07, "lon": 120.33},
    "57083": {"name": "Zhengzhou", "region": "asia", "country": "CN", "lat": 34.72, "lon": 113.65},
    "58238": {"name": "Nanjing", "region": "asia", "country": "CN", "lat": 32.00, "lon": 118.80},
    "47401": {"name": "Japan-47401", "region": "asia", "country": "JP", "lat": 0, "lon": 0},
    "47678": {"name": "Japan-47678", "region": "asia", "country": "JP", "lat": 0, "lon": 0},
}

REGION_FILTERS = {
    "texas": ["72249", "72251", "72340"],
    "asia": ["57494", "58362", "54857", "57083", "58238", "47401", "47678"],
    "all": list(STATIONS.keys()),
}

# 线程安全打印
print_lock = threading.Lock()
stats_lock = threading.Lock()
stats = {"downloaded": 0, "skipped": 0, "failed": 0, "no_data": 0, "total_rows": 0}
failed_list = []
station_info_cache = {}


def log(msg):
    with print_lock:
        print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def fetch_sounding(station_id, dt_str, max_retries=2):
    """下载单个探空数据"""
    params = urllib.parse.urlencode({
        "datetime": dt_str,
        "id": station_id,
        "src": "UNKNOWN",
        "type": "TEXT:LIST",
    })
    url = f"{BASE_URL}?{params}"

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp = urllib.request.urlopen(req, timeout=45, context=SSL_CTX)
            html = resp.read().decode("utf-8", errors="replace")

            if len(html) < 500:
                return {"success": False, "error": "Response too short", "rows": 0}

            pre_match = re.search(r'<PRE>(.*?)</PRE>', html, re.DOTALL)
            if not pre_match:
                if "Can't get" in html or "not found" in html.lower():
                    return {"success": False, "error": "No data for this time", "rows": 0}
                return {"success": False, "error": "No <PRE> block found", "rows": 0}

            pre_text = pre_match.group(1).strip()
            lines = pre_text.split('\n')

            station_info = {}

            name_match = re.search(r'Observations for Station \S+ at .*?UTC .*?([A-Z][A-Z\s,.\-]+?)(?:<|$)', html)
            if name_match:
                station_info["station_name_from_html"] = name_match.group(1).strip().rstrip('.,')

            lat_match = re.search(r'Latitude:\s*(-?[\d.]+)', html)
            lon_match = re.search(r'Longitude:\s*(-?[\d.]+)', html)
            if lat_match:
                station_info["latitude"] = lat_match.group(1)
            if lon_match:
                station_info["longitude"] = lon_match.group(1)

            plain_text = re.sub(r'<[^>]+>', '\n', html)
            plain_text = re.sub(r'\n\s*\n', '\n', plain_text)

            indices_search = {
                "CAPE": r'(?:^|\n)\s*(?:CAPE|Convective Available Potential Energy)\s*\n\s*(-?[\d.]+)',
                "DCAPE": r'(?:^|\n)\s*(?:DCAPE|Downward CAPE)\s*\n\s*(-?[\d.]+)',
                "CINS": r'(?:^|\n)\s*(?:CINS|Convective Inhibition)\s*\n\s*(-?[\d.]+)',
                "SHOW": r'(?:^|\n)\s*(?:SHOW|Showalter Index)\s*\n\s*(-?[\d.]+)',
                "LIFT": r'(?:^|\n)\s*(?:LIFT|Lifted Index)\s*\n\s*(-?[\d.]+)',
                "TOTL": r'(?:^|\n)\s*(?:TOTL|Total Totals)\s*\n\s*(-?[\d.]+)',
                "CTOT": r'(?:^|\n)\s*(?:CTOT|Cross Totals)\s*\n\s*(-?[\d.]+)',
                "VTOT": r'(?:^|\n)\s*(?:VTOT|Vertical Totals)\s*\n\s*(-?[\d.]+)',
                "CCLP": r'(?:^|\n)\s*(?:CCLP|Convective Condensation Level)\s*\n\s*(-?[\d.]+)',
                "LCL": r'(?:^|\n)\s*(?:LCL|Lifting Condensation Level)\s*\n\s*(-?[\d.]+)',
                "LFC": r'(?:^|\n)\s*(?:LFC|Level of Free Convection)\s*\n\s*(-?[\d.]+)',
                "EQLV": r'(?:^|\n)\s*(?:EQLV|Equilibrium Level)\s*\n\s*(-?[\d.]+)',
                "BRCH": r'(?:^|\n)\s*(?:BRCH|Bulk Richardson Number)\s*\n\s*(-?[\d.]+)',
            }
            for key, pattern in indices_search.items():
                match = re.search(pattern, plain_text, re.MULTILINE)
                if match:
                    station_info[key] = match.group(1)

            header_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("PRES") and "HGHT" in line:
                    header_idx = i
                    break

            if header_idx is None:
                return {"success": False, "error": "No data header found", "rows": 0}

            col_names = lines[header_idx].strip().split()

            data_rows = []
            for line in lines[header_idx + 2:]:
                parts = line.split()
                if len(parts) >= len(col_names):
                    try:
                        row = [float(p) for p in parts[:len(col_names)]]
                        data_rows.append(row)
                    except ValueError:
                        continue

            if not data_rows:
                return {"success": False, "error": "No data rows parsed", "rows": 0}

            df = pd.DataFrame(data_rows, columns=col_names)

            return {
                "success": True,
                "df": df,
                "station_info": station_info,
                "error": None,
                "rows": len(df),
            }

        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return {"success": False, "error": f"HTTP {e.code}: No data", "rows": 0}
            elif attempt < max_retries - 1:
                time.sleep(2)
            else:
                return {"success": False, "error": f"HTTP {e.code}", "rows": 0}

        except (socket.timeout, urllib.error.URLError) as e:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return {"success": False, "error": f"{type(e).__name__}", "rows": 0}

        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}", "rows": 0}

    return {"success": False, "error": "Max retries", "rows": 0}


def download_one(station_id, station_name, date_val, hour, output_dir):
    """下载并保存单个探空记录"""
    dt_str = f"{date_val.strftime('%Y-%m-%d')} {hour:02d}:00:00"
    fname = f"sounding_{station_id}_{date_val.strftime('%Y%m%d')}{hour:02d}Z.csv"
    fpath = output_dir / station_id / fname

    # 断点续传
    if fpath.exists():
        return ("skipped", station_id, dt_str, 0, None)

    result = fetch_sounding(station_id, dt_str)

    if result["success"]:
        df = result["df"]
        info = result["station_info"]

        df.insert(0, "station_id", station_id)
        df.insert(1, "station_name", station_name)
        df.insert(2, "datetime_utc", dt_str)
        df.insert(3, "obs_hour_z", hour)

        if info:
            if "station_name_from_html" in info:
                df["station_name"] = info["station_name_from_html"]
            for key in ["latitude", "longitude", "CAPE", "DCAPE", "CINS",
                        "SHOW", "LIFT", "TOTL", "CTOT", "VTOT",
                        "CCLP", "LCL", "LFC", "EQLV", "BRCH"]:
                if key in info:
                    try:
                        df[key] = float(info[key])
                    except (ValueError, TypeError):
                        df[key] = info[key]

        df.to_csv(fpath, index=False)

        with stats_lock:
            stats["downloaded"] += 1
            stats["total_rows"] += len(df)
            if station_id not in station_info_cache and info:
                station_info_cache[station_id] = info

        return ("success", station_id, dt_str, len(df), info)
    else:
        err = result["error"]
        with stats_lock:
            if "404" in err or "No data" in err or "400" in err:
                stats["no_data"] += 1
            else:
                stats["failed"] += 1
                failed_list.append({
                    "station_id": station_id,
                    "datetime": dt_str,
                    "error": err,
                })
        return ("no_data" if "404" in err or "No data" in err or "400" in err else "failed",
                station_id, dt_str, 0, err)


def main():
    parser = argparse.ArgumentParser(description="并行下载探空廓线数据")
    parser.add_argument("--start", default=None, help="起始日期")
    parser.add_argument("--end", default=None, help="截止日期")
    parser.add_argument("--days", type=int, default=30, help="下载最近N天")
    parser.add_argument("--region", default="all", choices=["texas", "asia", "all"])
    parser.add_argument("--stations", nargs="+", default=None, help="指定站号")
    parser.add_argument("--hours", nargs="+", type=int, default=[0, 12])
    parser.add_argument("--workers", type=int, default=5, help="并行下载线程数")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    now_utc = datetime.now(timezone.utc)
    if args.days:
        end_date = now_utc.date()
        start_date = end_date - timedelta(days=args.days - 1)
    else:
        end_date = datetime.strptime(args.end or now_utc.strftime("%Y-%m-%d"), "%Y-%m-%d").date()
        start_date = datetime.strptime(args.start or (end_date - timedelta(days=6)).strftime("%Y-%m-%d"), "%Y-%m-%d").date()

    if args.stations:
        station_ids = [s for s in args.stations if s in STATIONS]
    else:
        station_ids = REGION_FILTERS.get(args.region, REGION_FILTERS["all"])

    # 生成所有任务
    tasks = []
    current = start_date
    while current <= end_date:
        for hour in args.hours:
            for sid in station_ids:
                tasks.append((sid, STATIONS[sid]["name"], current, hour))
        current += timedelta(days=1)

    total = len(tasks)

    log("=" * 70)
    log("探空廓线数据并行下载")
    log(f"  日期范围: {start_date} ~ {end_date}")
    log(f"  观测时次: {args.hours}Z")
    log(f"  站点数: {len(station_ids)}")
    log(f"  总任务数: {total}")
    log(f"  并行线程: {args.workers}")
    log(f"  断点续传: {'否' if args.force else '是'}")
    log("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for sid in station_ids:
        (OUTPUT_DIR / sid).mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    completed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for sid, name, date_val, hour in tasks:
            # 断点续传: 先检查文件是否存在
            fname = f"sounding_{sid}_{date_val.strftime('%Y%m%d')}{hour:02d}Z.csv"
            fpath = OUTPUT_DIR / sid / fname
            if fpath.exists() and not args.force:
                stats["skipped"] += 1
                completed += 1
                continue

            future = executor.submit(download_one, sid, name, date_val, hour, OUTPUT_DIR)
            futures[future] = (sid, date_val, hour)

        for future in as_completed(futures):
            completed += 1
            status, sid, dt_str, rows, extra = future.result()
            elapsed = time.time() - start_time
            progress = completed / total * 100
            eta = (elapsed / completed * (total - completed)) / 60 if completed > 0 else 0

            if status == "success":
                log(f"  [{completed}/{total}] {progress:.0f}% ✓ {sid} {dt_str} {rows}行 (剩余~{eta:.0f}min)")
            elif status == "skipped":
                pass  # 已在前面处理
            elif status == "no_data":
                log(f"  [{completed}/{total}] {progress:.0f}% -- {sid} {dt_str} 无数据")
            else:
                log(f"  [{completed}/{total}] {progress:.0f}% ✗ {sid} {dt_str} 失败: {extra}")

    elapsed_total = time.time() - start_time
    log(f"\n{'='*70}")
    log("下载完成!")
    log(f"  新下载: {stats['downloaded']} 个文件 ({stats['total_rows']:,} 行)")
    log(f"  已跳过: {stats['skipped']} 个文件 (断点续传)")
    log(f"  无数据: {stats['no_data']} 个")
    log(f"  失败:   {stats['failed']} 个")
    log(f"  总耗时: {elapsed_total/60:.1f} 分钟")
    log(f"  输出目录: {OUTPUT_DIR}")

    if failed_list:
        log(f"\n  失败列表 (前20个):")
        for f in failed_list[:20]:
            log(f"    {f['station_id']} {f['datetime']}: {f['error']}")

    # 保存站点信息
    if station_info_cache:
        info_path = OUTPUT_DIR / "_station_info.json"
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(station_info_cache, f, indent=2, ensure_ascii=False)
        log(f"  站点信息: {info_path}")

    # 保存汇总
    summary = {
        "download_time": datetime.now().isoformat(),
        "source": "Wyoming WSGI (parallel)",
        "url": BASE_URL,
        "date_range": f"{start_date} ~ {end_date}",
        "hours": args.hours,
        "stations": {sid: STATIONS[sid] for sid in station_ids},
        "total_tasks": total,
        "downloaded": stats["downloaded"],
        "skipped": stats["skipped"],
        "no_data": stats["no_data"],
        "failed": stats["failed"],
        "total_rows": stats["total_rows"],
        "elapsed_minutes": round(elapsed_total / 60, 1),
        "failed_list": failed_list[:50],
    }
    summary_path = OUTPUT_DIR / "_download_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log(f"  汇总: {summary_path}")


if __name__ == "__main__":
    main()
