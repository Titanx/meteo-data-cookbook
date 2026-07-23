"""ERCOT 电力市场数据下载（2025 至今）

数据来源: EIA API v2
覆盖范围: ERCOT (respondent = ERCO)
时间范围: 2025-01-01 ~ 今天
输出目录: c:\\work\\meteo\\data\\ercot\\

== 数据说明 ==

ERCOT 官网 (www.ercot.com / data.ercot.com) 部署了 Imperva Incapsula
反爬虫系统，所有 API 和文件下载均返回 403，无法通过自动化方式获取
DAM/RTM 结算点电价 (SPP) 数据。EIA ICE 批发电力数据也不包含 ERCOT 枢纽。

本脚本下载 EIA API v2 中 ERCOT 的全部可用数据，虽然不含直接电价，
但对雷暴-电力联动分析极有价值:

1. region-data (小时级):
   - Demand          实际负荷
   - DF              日前负荷预测
   - Net generation  净发电量
   - Total interchange 总交换量

2. fuel-type-data (小时级):
   - Solar   太阳能发电 ← 雷暴过境时光伏骤降的直接观测
   - Wind    风电出力   ← 雷暴大风的风电骤变
   - Coal    煤电
   - Natural Gas 天然气发电
   - Nuclear 核电
   - Hydro   水电
   - Battery storage 储能
   - Other   其他
   - Unknown energy storage 未知储能

== 获取电价数据的替代方案 ==

如需 ERCOT 电价 (LMP/SPP)，可通过以下方式获取:
1. ERCOT MIS: https://www.ercot.com/mp/data-products/data-pages
   - 需用真实浏览器手动下载 ZIP 文件（中国 IP 可能无法访问）
   - DAM SPP: reportTypeId=13060 (NP4-180-ER)
   - RTM SPP: reportTypeId=12300 (NP4-196-M)
2. GridStatus.io 免费方案 API: https://www.gridstatus.io/sign-up
   - 免费 250 次请求/月，50 万行/月，中国可访问
   - 使用 download_ercot_spp.py 脚本下载
3. Potomac Economics ERCOT 月报: https://www.potomaceconomics.com/

== 使用方法 ==
  1. 设置 EIA API key (免费注册: https://www.eia.gov/opendata/register.php):
     PowerShell: $env:EIA_API_KEY = "你的key"

  2. 运行:
     python download_ercot_prices.py

  3. 可选参数:
     --start 2025-01-01   起始日期 (默认 2025-01-01)
     --end 2026-07-22     截止日期 (默认今天)
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import argparse
import time
import json
from datetime import datetime
from pathlib import Path

import requests
import pandas as pd

# ── 常量 ──────────────────────────────────────────────
EIA_BASE = "https://api.eia.gov/v2"
ERCOT_RESPONDENT = "ERCO"
OUTPUT_DIR = Path(r"c:\work\meteo\data\ercot")
PAGE_SIZE = 5000
MAX_RETRIES = 3
RETRY_DELAY = 5

# 数据路由
ROUTES = {
    "region_data": {
        "path": "electricity/rto/region-data/data/",
        "name": "区域运行数据 (负荷/发电/交换)",
        "facet_type": "type",
    },
    "fuel_type_data": {
        "path": "electricity/rto/fuel-type-data/data/",
        "name": "燃料类型发电数据 (太阳能/风电/煤电等)",
        "facet_type": "fueltype",
    },
}


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def get_api_key():
    key = os.environ.get("EIA_API_KEY", "").strip()
    if not key:
        log("=" * 60)
        log("错误: 未找到 EIA API key!")
        log("请按以下步骤获取 (免费, 1 分钟):")
        log("  1. 访问 https://www.eia.gov/opendata/register.php")
        log("  2. 填写邮箱注册")
        log("  3. 检查邮箱获取 API key")
        log("  4. 设置环境变量:")
        log('     PowerShell: $env:EIA_API_KEY = "你的key"')
        log("=" * 60)
        sys.exit(1)
    return key


def eia_request(route_path, params, api_key, max_retries=MAX_RETRIES):
    """带重试的 EIA API 请求"""
    full_params = {"api_key": api_key, **params}
    url = f"{EIA_BASE}/{route_path}"
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=full_params, timeout=60)
            if r.status_code == 429:
                wait = 30 * (attempt + 1)
                log(f"  速率限制, 等待 {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt + 1 >= max_retries:
                raise
            wait = RETRY_DELAY * (attempt + 1)
            log(f"  请求失败 ({e}), {wait}s 后重试 ({attempt+1}/{max_retries})")
            time.sleep(wait)
    return None


def month_range(start_date, end_date):
    """生成 start_date 到 end_date 之间的所有 (year, month) 列表"""
    months = []
    y, m = start_date.year, start_date.month
    while (y, m) <= (end_date.year, end_date.month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def download_month(api_key, route_key, route_info, year, month):
    """下载指定月份的指定路由数据"""
    start_dt = datetime(year, month, 1)
    if month == 12:
        end_dt = datetime(year + 1, 1, 1)
    else:
        end_dt = datetime(year, month + 1, 1)

    start_str = start_dt.strftime("%Y-%m-%dT%H")
    end_str = end_dt.strftime("%Y-%m-%dT%H")

    all_rows = []
    offset = 0

    while True:
        params = {
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": ERCOT_RESPONDENT,
            "start": start_str,
            "end": end_str,
            "offset": offset,
            "length": PAGE_SIZE,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
        }
        data = eia_request(route_info["path"], params, api_key)
        if not data or "response" not in data:
            break

        rows = data["response"].get("data", [])
        total = int(data["response"].get("total", 0))
        all_rows.extend(rows)

        offset += len(rows)
        if offset >= total or len(rows) == 0:
            break
        time.sleep(0.3)

    return all_rows


def save_csv(rows, filepath):
    """保存为 CSV"""
    if not rows:
        return False
    df = pd.DataFrame(rows)
    # 标准化列名
    col_map = {
        "period": "time",
        "respondent": "respondent",
        "respondent-name": "respondent_name",
        "type": "type_code",
        "type-name": "type_name",
        "fueltype": "fuel_code",
        "value": "value",
        "value-units": "units",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df.to_csv(filepath, index=False)
    return True


def main():
    parser = argparse.ArgumentParser(description="下载 ERCOT 电力市场数据 (EIA API v2)")
    parser.add_argument("--start", default="2025-01-01", help="起始日期 (默认 2025-01-01)")
    parser.add_argument("--end", default=None, help="截止日期 (默认今天)")
    args = parser.parse_args()

    api_key = get_api_key()
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d") if args.end else datetime.now()

    log("ERCOT 电力市场数据下载")
    log(f"  时间范围: {start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d}")
    log(f"  数据源: EIA API v2 (respondent={ERCOT_RESPONDENT})")
    log(f"  输出目录: {OUTPUT_DIR}")
    log(f"  路由数: {len(ROUTES)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    months = month_range(start_date, end_date)
    log(f"  共 {len(months)} 个月 × {len(ROUTES)} 路由 = {len(months) * len(ROUTES)} 个文件")

    total_downloaded = 0
    total_skipped = 0
    total_failed = 0

    for route_key, route_info in ROUTES.items():
        log(f"\n{'='*60}")
        log(f"下载 {route_key}: {route_info['name']}")
        log(f"{'='*60}")

        for year, month in months:
            fname = f"ercot_{route_key}_{year}-{month:02d}.csv"
            fpath = OUTPUT_DIR / fname

            # 断点续传
            if fpath.exists() and fpath.stat().st_size > 100:
                log(f"  {year}-{month:02d} 已存在, 跳过")
                total_skipped += 1
                continue

            log(f"  下载 {route_key} {year}-{month:02d}...")
            try:
                rows = download_month(api_key, route_key, route_info, year, month)
                if rows:
                    saved = save_csv(rows, fpath)
                    if saved:
                        # 统计数据类型
                        if route_info["facet_type"] in rows[0]:
                            types = set(r.get(route_info["facet_type"], "") for r in rows)
                            log(f"    {len(rows)} 行, 类型: {sorted(types)} → {fname}")
                        else:
                            log(f"    {len(rows)} 行 → {fname}")
                        total_downloaded += 1
                    else:
                        log(f"    无数据")
                        total_failed += 1
                else:
                    log(f"    无数据 (可能是未来月份)")
                    total_failed += 1
            except Exception as e:
                log(f"    错误: {e}")
                total_failed += 1

            time.sleep(0.5)

    # 汇总
    log(f"\n{'='*60}")
    log("下载完成!")
    log(f"  新下载: {total_downloaded} 个文件")
    log(f"  已跳过: {total_skipped} 个文件")
    log(f"  失败:   {total_failed} 个文件")
    log(f"  输出目录: {OUTPUT_DIR}")

    # 生成汇总文件
    summary_path = OUTPUT_DIR / "_download_summary.json"
    summary = {
        "download_time": datetime.now().isoformat(),
        "source": "EIA API v2",
        "respondent": ERCOT_RESPONDENT,
        "date_range": f"{start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d}",
        "routes": {k: v["name"] for k, v in ROUTES.items()},
        "downloaded": total_downloaded,
        "skipped": total_skipped,
        "failed": total_failed,
        "note": "ERCOT 官网部署 Imperva 反爬虫, 无法自动获取 DAM/RTM 电价. "
                "本数据包含 ERCOT 小时级负荷/发电/燃料类型数据, 对雷暴分析极有价值. "
                "如需电价, 请使用 GridStatus.io 免费方案 API (download_ercot_spp.py).",
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log(f"  汇总: {summary_path}")


if __name__ == "__main__":
    main()
