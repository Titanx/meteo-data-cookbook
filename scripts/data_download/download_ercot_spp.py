"""ERCOT 结算点电价 (SPP) 下载（2025 至今）

数据来源: GridStatus.io 托管 API (免费方案)
覆盖范围: ERCOT 全部交易枢纽 (Trading Hubs)
时间范围: 2025-01-01 ~ 今天
输出目录: c:\\work\\meteo\\data\\ercot\\

== 数据说明 ==

ERCOT 官网 (www.ercot.com) 部署了 Imperva 反爬虫且对中国 IP 完全屏蔽，
EIA API 也不提供电价数据。GridStatus.io 托管 API 从中国可正常访问
（返回 401 需要 key，而非 403 封锁），免费方案每月 250 次请求 / 50 万行，
足够下载 ERCOT 全部枢纽的 2025 至今 DAM + RTM 电价。

数据集:
  1. ercot_spp_day_ahead_hourly    日前市场 SPP (小时级)
  2. ercot_spp_real_time_15_min    实时市场 SPP (15分钟级)

ERCOT 交易枢纽 (Trading Hubs):
  - HB_NORTH      北部枢纽
  - HB_SOUTH      南部枢纽
  - HB_HOUSTON    休斯顿枢纽
  - HB_PANHANDLE   锅柄枢纽（已弃用，返回空数据）
  - HB_WEST       西部枢纽

== 使用方法 ==
  1. 免费注册 GridStatus.io 账号 (1 分钟):
     https://www.gridstatus.io/sign-up

  2. 获取 API key:
     登录后访问 https://www.gridstatus.io/settings/api
     复制你的 API key

  3. 设置环境变量:
     PowerShell: $env:GRIDSTATUS_API_KEY = "你的key"

  4. 运行:
     python download_ercot_spp.py

  5. 可选参数:
     --start 2025-01-01   起始日期 (默认 2025-01-01)
     --end 2026-07-22     截止日期 (默认今天)
     --markets DAM RTM    下载类型 (默认 DAM+RTM)
     --hubs HB_NORTH      指定枢纽 (默认全部 5 个)
     --dry-run            只列出可用数据集, 不下载
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import argparse
import time
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── 常量 ──────────────────────────────────────────────
OUTPUT_DIR = Path(r"c:\work\meteo\data\ercot")

DATASETS = {
    "DAM": {
        "id": "ercot_spp_day_ahead_hourly",
        "name": "日前市场 SPP (小时级)",
        "freq": "hourly",
    },
    "RTM": {
        "id": "ercot_spp_real_time_15_min",
        "name": "实时市场 SPP (15分钟级)",
        "freq": "15min",
    },
}

# HB_PANHANDLE 已弃用，下载时返回空数据，保留在列表中以便跳过时记录
ALL_HUBS = ["HB_NORTH", "HB_SOUTH", "HB_HOUSTON", "HB_PANHANDLE", "HB_WEST"]


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def get_api_key():
    key = os.environ.get("GRIDSTATUS_API_KEY", "").strip()
    if not key:
        log("=" * 60)
        log("错误: 未找到 GridStatus.io API key!")
        log("请按以下步骤获取 (免费, 1 分钟):")
        log("  1. 访问 https://www.gridstatus.io/sign-up")
        log("  2. 注册免费账号")
        log("  3. 登录后访问 https://www.gridstatus.io/settings/api")
        log("  4. 复制你的 API key")
        log("  5. 设置环境变量:")
        log('     PowerShell: $env:GRIDSTATUS_API_KEY = "你的key"')
        log("=" * 60)
        sys.exit(1)
    return key


def main():
    parser = argparse.ArgumentParser(description="下载 ERCOT 结算点电价 (GridStatus.io API)")
    parser.add_argument("--start", default="2025-01-01", help="起始日期 (默认 2025-01-01)")
    parser.add_argument("--end", default=None, help="截止日期 (默认今天)")
    parser.add_argument("--markets", nargs="+", default=None, help="市场类型 (默认 DAM+RTM)")
    parser.add_argument("--hubs", nargs="+", default=None, help="交易枢纽 (默认全部)")
    parser.add_argument("--dry-run", action="store_true", help="只列出可用数据集, 不下载")
    args = parser.parse_args()

    api_key = get_api_key()

    import gridstatusio
    client = gridstatusio.GridStatusClient(api_key=api_key)

    start_date = args.start
    end_date = args.end or datetime.now().strftime("%Y-%m-%d")

    # 确定要下载的市场
    markets = args.markets if args.markets else ["DAM", "RTM"]
    hubs = args.hubs if args.hubs else ALL_HUBS

    log("ERCOT 结算点电价下载")
    log(f"  数据源: GridStatus.io 托管 API (免费方案)")
    log(f"  时间范围: {start_date} ~ {end_date}")
    log(f"  市场: {markets}")
    log(f"  枢纽: {hubs}")
    log(f"  输出目录: {OUTPUT_DIR}")

    # 检查 API 使用量
    try:
        usage = client.get_api_usage()
        log(f"  API 使用量: {usage}")
    except Exception as e:
        log(f"  API 使用量查询失败: {e}")

    if args.dry_run:
        log("\n列出 ERCOT 相关数据集...")
        try:
            datasets = client.list_datasets(filter_term="ercot", return_list=True)
            for ds in datasets:
                log(f"  {ds}")
        except Exception as e:
            log(f"  列出数据集失败: {e}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    total_rows = 0

    for market_key in markets:
        if market_key not in DATASETS:
            log(f"  未知市场类型: {market_key}, 跳过")
            continue

        ds = DATASETS[market_key]
        log(f"\n{'='*60}")
        log(f"下载 {market_key}: {ds['name']}")
        log(f"  数据集 ID: {ds['id']}")
        log(f"{'='*60}")

        # 获取数据集元数据
        try:
            meta = client.get_dataset_metadata(ds["id"])
            earliest = meta.get("earliest_available_time_utc", "N/A")
            log(f"  最早可用数据: {earliest}")
        except Exception as e:
            log(f"  元数据查询失败: {e}")

        for hub in hubs:
            fname = f"ercot_{market_key.lower()}_{hub}_{start_date}_{end_date}.csv"
            fpath = OUTPUT_DIR / fname

            # 断点续传
            if fpath.exists() and fpath.stat().st_size > 100:
                log(f"  {hub} 已存在, 跳过")
                total_skipped += 1
                continue

            log(f"  下载 {market_key} {hub}...")
            try:
                df = client.get_dataset(
                    ds["id"],
                    start=start_date,
                    end=end_date,
                    filter_column="location",
                    filter_value=hub,
                    verbose=False,
                )

                if df is not None and len(df) > 0:
                    df.to_csv(fpath, index=False)
                    total_rows += len(df)

                    # 统计
                    if "spp" in df.columns:
                        spp = pd.to_numeric(df["spp"], errors="coerce").dropna()
                        if len(spp) > 0:
                            log(f"    {len(df)} 行 → {fname}")
                            log(f"    价格: 均值 ${spp.mean():.2f}, 最大 ${spp.max():.2f}, 最小 ${spp.min():.2f}/MWh")
                        else:
                            log(f"    {len(df)} 行 → {fname} (价格全为空)")
                    else:
                        log(f"    {len(df)} 行 → {fname}")
                        log(f"    列: {list(df.columns)}")

                    total_downloaded += 1
                else:
                    log(f"    无数据")
                    total_failed += 1
            except Exception as e:
                log(f"    错误: {e}")
                total_failed += 1

            time.sleep(1)  # 请求间隔

    # 汇总
    log(f"\n{'='*60}")
    log("下载完成!")
    log(f"  新下载: {total_downloaded} 个文件 ({total_rows:,} 行)")
    log(f"  已跳过: {total_skipped} 个文件")
    log(f"  失败:   {total_failed} 个文件")
    log(f"  输出目录: {OUTPUT_DIR}")

    # 检查剩余 API 额度
    try:
        usage = client.get_api_usage()
        log(f"  API 使用量: {usage}")
    except Exception:
        pass

    # 生成汇总文件
    summary_path = OUTPUT_DIR / "_spp_download_summary.json"
    summary = {
        "download_time": datetime.now().isoformat(),
        "source": "GridStatus.io API (免费方案)",
        "date_range": f"{start_date} ~ {end_date}",
        "markets": markets,
        "hubs": hubs,
        "downloaded": total_downloaded,
        "skipped": total_skipped,
        "failed": total_failed,
        "total_rows": total_rows,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log(f"  汇总: {summary_path}")


if __name__ == "__main__":
    main()
