"""探空廓线数据下载 (怀俄明大学新 WSGI 接口)

数据来源: University of Wyoming Atmospheric Science Radiosonde Archive
URL: http://weather.uwyo.edu/wsgi/sounding
覆盖范围: 全球探空站 (美国高分辨率 + 中国/日本标准分辨率)
时间范围: 1973 至今 (默认 2025-01-01 ~ 今天)
输出目录: c:\\work\\meteo\\data\\sounding\\

== 重要说明 ==

2026年怀俄明大学迁移到新服务器，旧 CGI 接口 (/cgi-bin/sounding) 已废弃 (404)。
新 WSGI 接口 URL 格式:
  /wsgi/sounding?datetime=YYYY-MM-DD+HH:00:00&id=站号&src=UNKNOWN&type=TEXT:LIST

新接口特点:
  - 支持 3 小时频次 (0/3/6/9/12/15/18/21Z)，比旧接口 00/12Z 更密
  - 中国探空数据可直接获取 (无需 BUFR 转换)
  - 支持 TEXT:LIST (表格), TEXT:CSV (逗号分隔), PNG:SKEWT (Skew-T 图)
  - 美国站高分辨率 (~4500-7000 行/次, 1秒级)
  - 中国站标准分辨率 (~120-145 行/次, 规定层)
  - 11 个变量: PRES HGHT TEMP DWPT RELH MIXR DRCT SPED THTA THTE THTV
  - 零缺测 (测试确认)

== 网络注意 ==

中国网络访问需跳过 SSL 证书验证 (代理拦截 HTTPS)。
脚本已内置 ssl.CERT_NONE 处理。

== 站点列表 ==

ERCOT/德州区域 (配合 ERCOT 电价/负荷分析):
  72249  Midland, TX        西德州 (风电密集区)
  72251  Fort Worth, TX     北德中部
  72340  Shreveport, LA     东德州/路易斯安那边境

东亚区域 (配合向日葵卫星数据分析):
  57494  武汉               华中
  58362  上海               华东
  54857  青岛               华北沿海
  57083  郑州               华中
  58238  南京               华东
  47401  日本               (站点待确认名称)
  47678  日本               (站点待确认名称)

== 使用方法 ==

  1. 下载全部站点最近7天 (00Z + 12Z):
     python download_sounding.py --days 7

  2. 下载指定日期范围全部站点:
     python download_sounding.py --start 2025-01-01 --end 2026-08-11

  3. 只下载 ERCOT 区域:
     python download_sounding.py --region texas --start 2025-06-01

  4. 只下载东亚区域:
     python download_sounding.py --region asia --start 2025-06-01

  5. 指定站点和时次:
     python download_sounding.py --stations 72249 57494 --hours 0 12

  6. 3小时频次 (更密但数据量大):
     python download_sounding.py --hours 0 3 6 9 12 15 18 21 --days 7

  7. 测试模式 (只下载1个站点1天):
     python download_sounding.py --dry-run

  8. 强制重新下载 (覆盖已有文件):
     python download_sounding.py --force --days 3
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import ssl
import json
import time
import re
import io
import argparse
import urllib.request
import urllib.parse
import urllib.error
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# ── 常量 ──────────────────────────────────────────────
OUTPUT_DIR = Path(r"c:\work\meteo\data\sounding")
BASE_URL = "http://weather.uwyo.edu/wsgi/sounding"

# SSL: 跳过证书验证 (中国网络代理常拦截 HTTPS)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

socket.setdefaulttimeout(60)

# ── 站点列表 ──────────────────────────────────────────
# 注意: 站点名称从 HTML 中动态提取，这里的名称仅用于初始显示
STATIONS = {
    # ERCOT/德州区域
    "72249": {"name": "Fort Worth", "region": "texas", "country": "US", "lat": 32.83, "lon": -97.30},
    "72251": {"name": "Dallas-FW", "region": "texas", "country": "US", "lat": 32.90, "lon": -97.04},
    "72340": {"name": "Shreveport", "region": "texas", "country": "US", "lat": 32.45, "lon": -93.82},
    # 东亚区域
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


def log(msg, end="\n"):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True, end=end)


def fetch_sounding(station_id, dt_str, max_retries=3):
    """从怀俄明大学下载单个探空数据

    Args:
        station_id: WMO 站号 (如 "72249")
        dt_str: 日期时间字符串 "YYYY-MM-DD HH:00:00"
        max_retries: 最大重试次数

    Returns:
        dict with keys: success, df, station_info, error, rows
    """
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
            resp = urllib.request.urlopen(req, timeout=60, context=SSL_CTX)
            html = resp.read().decode("utf-8", errors="replace")

            # 检查错误
            if len(html) < 500:
                return {"success": False, "error": "Response too short", "rows": 0}

            # 提取 PRE 块
            pre_match = re.search(r'<PRE>(.*?)</PRE>', html, re.DOTALL)
            if not pre_match:
                # 检查是否有明确的 "no data" 消息
                if "Can't get" in html or "not found" in html.lower():
                    return {"success": False, "error": "No data for this time", "rows": 0}
                return {"success": False, "error": "No <PRE> block found", "rows": 0}

            pre_text = pre_match.group(1).strip()
            lines = pre_text.split('\n')

            # 提取站点信息和热力指数 (新 WSGI 格式)
            station_info = {}

            # 站点名称: "Observations for Station XXXXX at 12 UTC 10 Aug 2026 FORT WORTH, TX., USA"
            name_match = re.search(r'Observations for Station \S+ at .*?UTC .*?([A-Z][A-Z\s,.\-]+?)(?:<|$)', html)
            if name_match:
                station_info["station_name_from_html"] = name_match.group(1).strip().rstrip('.,')

            # 经纬度: "Latitude: 32.835 Longitude: -97.297"
            lat_match = re.search(r'Latitude:\s*(-?[\d.]+)', html)
            lon_match = re.search(r'Longitude:\s*(-?[\d.]+)', html)
            if lat_match:
                station_info["latitude"] = lat_match.group(1)
            if lon_match:
                station_info["longitude"] = lon_match.group(1)

            # 热力指数: 新格式在可折叠表格中，格式为 CODE/Full Name/value/unit
            # 提取所有 "Full Name" -> "value" 对
            # 先尝试从纯文本中提取 (去掉 HTML 标签后的文本)
            plain_text = re.sub(r'<[^>]+>', '\n', html)
            plain_text = re.sub(r'\n\s*\n', '\n', plain_text)

            # 搜索已知指数名称后的数值
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

            # 找表头行 (以 PRES 开头)
            header_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("PRES") and "HGHT" in line:
                    header_idx = i
                    break

            if header_idx is None:
                return {"success": False, "error": "No data header found", "rows": 0}

            # 解析列名
            col_names = lines[header_idx].strip().split()

            # 解析数据行 (跳过表头行和单位行)
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
            if e.code == 404:
                return {"success": False, "error": f"HTTP 404: Data not found", "rows": 0}
            elif e.code == 400:
                return {"success": False, "error": f"HTTP 400: Bad request (no sounding)", "rows": 0}
            elif attempt < max_retries - 1:
                log(f"    HTTP {e.code}, 重试 {attempt+1}/{max_retries}...")
                time.sleep(3)
            else:
                return {"success": False, "error": f"HTTP {e.code}: {e.reason}", "rows": 0}

        except (socket.timeout, urllib.error.URLError) as e:
            if attempt < max_retries - 1:
                log(f"    超时/连接错误, 重试 {attempt+1}/{max_retries}...")
                time.sleep(5)
            else:
                return {"success": False, "error": f"{type(e).__name__}: {e}", "rows": 0}

        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}", "rows": 0}

    return {"success": False, "error": "Max retries exceeded", "rows": 0}


def generate_date_hours(start_date, end_date, hours):
    """生成日期×时次的列表"""
    result = []
    current = start_date
    while current <= end_date:
        for hour in hours:
            result.append(current)
        current += timedelta(days=1)
    # 修正: 每天每个时次一个条目
    result = []
    current = start_date
    while current <= end_date:
        for hour in hours:
            result.append((current, hour))
        current += timedelta(days=1)
    return result


def main():
    parser = argparse.ArgumentParser(description="下载探空廓线数据 (怀俄明大学 WSGI 接口)")
    parser.add_argument("--start", default=None, help="起始日期 (默认: 7天前)")
    parser.add_argument("--end", default=None, help="截止日期 (默认: 今天)")
    parser.add_argument("--days", type=int, default=None, help="下载最近N天 (快捷方式)")
    parser.add_argument("--region", default="all", choices=["texas", "asia", "all"],
                        help="区域: texas(ERCOT), asia(东亚), all(全部)")
    parser.add_argument("--stations", nargs="+", default=None, help="指定站号 (覆盖 --region)")
    parser.add_argument("--hours", nargs="+", type=int, default=[0, 12],
                        help="观测时次 UTC (默认 0 12; 可选 0 3 6 9 12 15 18 21)")
    parser.add_argument("--force", action="store_true", help="强制重新下载 (覆盖已有文件)")
    parser.add_argument("--dry-run", action="store_true", help="测试模式: 1站1天")
    args = parser.parse_args()

    # 确定日期范围
    now_utc = datetime.now(timezone.utc)
    if args.days:
        end_date = now_utc.date()
        start_date = end_date - timedelta(days=args.days - 1)
    else:
        end_date = datetime.strptime(args.end or now_utc.strftime("%Y-%m-%d"), "%Y-%m-%d").date()
        start_date = datetime.strptime(args.start or (end_date - timedelta(days=6)).strftime("%Y-%m-%d"), "%Y-%m-%d").date()

    # 确定站点
    if args.stations:
        station_ids = [s for s in args.stations if s in STATIONS]
        invalid = [s for s in args.stations if s not in STATIONS]
        if invalid:
            log(f"警告: 未知站号将被跳过: {invalid}")
    else:
        station_ids = REGION_FILTERS.get(args.region, REGION_FILTERS["all"])

    # 测试模式
    if args.dry_run:
        station_ids = ["72249"]
        start_date = end_date - timedelta(days=1)
        args.hours = [12]

    log("=" * 70)
    log("探空廓线数据下载")
    log(f"  数据源: 怀俄明大学 WSGI 接口 ({BASE_URL})")
    log(f"  日期范围: {start_date} ~ {end_date}")
    log(f"  观测时次: {args.hours}Z (UTC)")
    log(f"  站点数: {len(station_ids)}")
    log(f"  站点列表:")
    for sid in station_ids:
        info = STATIONS[sid]
        log(f"    {sid} {info['name']:<15} ({info['country']}) [{info['region']}]")

    # 计算总请求数
    date_hours = generate_date_hours(start_date, end_date, args.hours)
    total_requests = len(station_ids) * len(date_hours)
    log(f"  总请求数: {total_requests} ({len(station_ids)} 站 × {len(date_hours)} 时次)")
    log(f"  输出目录: {OUTPUT_DIR}")
    log(f"  覆盖已有: {'是' if args.force else '否 (断点续传)'}")
    log("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 统计
    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    total_no_data = 0
    total_rows = 0
    failed_list = []
    station_info_cache = {}

    request_count = 0
    start_time = time.time()

    for station_id in station_ids:
        station_info = STATIONS[station_id]
        station_name = station_info["name"]

        log(f"\n{'='*60}")
        log(f"站点 {station_id} ({station_name})")
        log(f"{'='*60}")

        station_dir = OUTPUT_DIR / station_id
        station_dir.mkdir(parents=True, exist_ok=True)

        for date_val, hour in date_hours:
            request_count += 1
            dt_str = f"{date_val.strftime('%Y-%m-%d')} {hour:02d}:00:00"
            fname = f"sounding_{station_id}_{date_val.strftime('%Y%m%d')}{hour:02d}Z.csv"
            fpath = station_dir / fname

            # 断点续传
            if fpath.exists() and not args.force:
                total_skipped += 1
                continue

            # 进度
            elapsed = time.time() - start_time
            if request_count > 1:
                avg_time = elapsed / (request_count - 1)
                remaining = avg_time * (total_requests - request_count)
                log(f"  [{request_count}/{total_requests}] {station_id} {dt_str} "
                    f"(剩余~{remaining/60:.0f}min)", end=" ")
            else:
                log(f"  [{request_count}/{total_requests}] {station_id} {dt_str}", end=" ")

            # 下载
            result = fetch_sounding(station_id, dt_str)

            if result["success"]:
                df = result["df"]
                info = result["station_info"]

                # 添加元数据列
                df.insert(0, "station_id", station_id)
                df.insert(1, "station_name", station_name)
                df.insert(2, "datetime_utc", dt_str)
                df.insert(3, "obs_hour_z", hour)

                # 添加站点信息和热力指数
                if info:
                    # 使用 HTML 中的站点名称 (如果有)
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

                # 保存
                df.to_csv(fpath, index=False)
                total_downloaded += 1
                total_rows += len(df)

                # 缓存站点信息
                if station_id not in station_info_cache and info:
                    station_info_cache[station_id] = info

                # 日志
                pres_col = df.get("PRES", pd.Series())
                if len(pres_col) > 0:
                    pmin, pmax = pres_col.min(), pres_col.max()
                    temp_col = pd.to_numeric(df.get("TEMP", pd.Series()), errors='coerce')
                    tmin, tmax = temp_col.min(), temp_col.max()
                    cape = info.get("CAPE", "N/A")
                    log(f"✓ {len(df)}行 P:[{pmin:.0f}-{pmax:.0f}]hPa T:[{tmin:.0f}-{tmax:.0f}]°C CAPE={cape}")
                else:
                    log(f"✓ {len(df)}行")
            else:
                err = result["error"]
                if "404" in err or "No data" in err or "400" in err:
                    total_no_data += 1
                    log(f"-- 无数据 ({err})")
                else:
                    total_failed += 1
                    failed_list.append({
                        "station_id": station_id,
                        "datetime": dt_str,
                        "error": err,
                    })
                    log(f"✗ 失败: {err}")

            # 请求间隔
            time.sleep(0.5)

    # 汇总
    elapsed_total = time.time() - start_time
    log(f"\n{'='*70}")
    log("下载完成!")
    log(f"  新下载: {total_downloaded} 个文件 ({total_rows:,} 行)")
    log(f"  已跳过: {total_skipped} 个文件 (断点续传)")
    log(f"  无数据: {total_no_data} 个 (该时次无探空观测)")
    log(f"  失败:   {total_failed} 个 (网络/解析错误)")
    log(f"  总耗时: {elapsed_total/60:.1f} 分钟")
    log(f"  平均速度: {elapsed_total/max(request_count,1):.1f} 秒/请求")
    log(f"  输出目录: {OUTPUT_DIR}")

    if failed_list:
        log(f"\n  失败列表 (前10个):")
        for f in failed_list[:10]:
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
        "source": "Wyoming WSGI",
        "url": BASE_URL,
        "date_range": f"{start_date} ~ {end_date}",
        "hours": args.hours,
        "stations": {sid: STATIONS[sid] for sid in station_ids},
        "total_requests": total_requests,
        "downloaded": total_downloaded,
        "skipped": total_skipped,
        "no_data": total_no_data,
        "failed": total_failed,
        "total_rows": total_rows,
        "elapsed_minutes": round(elapsed_total / 60, 1),
        "failed_list": failed_list[:50],
    }
    summary_path = OUTPUT_DIR / "_download_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log(f"  汇总: {summary_path}")


if __name__ == "__main__":
    main()
