"""GK2A (GEO-KOMPSAT-2A) AMI L1B 数据下载

数据源: 韩国气象厅 NMSC, AWS S3 匿名访问
S3 桶: noaa-gk2a-pds
卫星: GEO-KOMPSAT-2A, 定点 128.2°E
传感器: AMI (Advanced Meteorological Imager)
分辨率: 可见光 0.5km, 红外 2km
时间: 全圆盘 10 分钟

== 16 个通道 ==
  可见光 (4): VI004, VI005, VI006, VI008 (0.5km)
  近红外 (2): NR013, NR016 (1.0km)
  水汽   (3): WV063, WV069, WV073 (2km)
  红外   (6): IR087, IR096, IR105, IR112, IR123, IR133 (2km)
  短波   (1): SW038 (1.0km)

== 文件命名 ==
  gk2a_ami_le1b_{channel}_fd020ge_{YYYYMMDDHHMM}.nc
  channel = vi004/vi005/vi006/vi008/nr013/nr016/sw038/wv063/wv069/wv073/
            ir087/ir096/ir105/ir112/ir123/ir133
  FD = Full Disk (全圆盘), 020ge = 2km GEOS 投影

== 使用方法 ==
  # 下载默认通道 (IR105 红外窗区, 最常用)
  python download_gk2a.py --start 2026-09-10 00:00 --end 2026-09-10 01:00

  # 下载多个通道
  python download_gk2a.py --channels vi006 ir105 wv073 --start 2026-09-10 00:00 --end 2026-09-10 06:00

  # 列出可用文件 (不下载)
  python download_gk2a.py --list-only --start 2026-09-10 00:00 --end 2026-09-10 01:00

  # 可见光通道 (0.5km, 文件更大)
  python download_gk2a.py --channels vi006 --start 2026-09-10 03:00 --end 2026-09-10 05:00
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import s3fs

OUTPUT_DIR = Path(r"c:\work\meteo\data\gk2a")

# 全部 16 个通道
ALL_CHANNELS = [
    "vi004", "vi005", "vi006", "vi008",  # 可见光 0.5km
    "nr013", "nr016",                      # 近红外 1.0km
    "sw038",                               # 短波 1.0km
    "wv063", "wv069", "wv073",            # 水汽 2km
    "ir087", "ir096", "ir105", "ir112", "ir123", "ir133",  # 红外 2km
]

# 默认通道: IR105 (10.5um 红外窗区, 最常用)
DEFAULT_CHANNELS = ["ir105"]

S3_BUCKET = "noaa-gk2a-pds"
S3_PREFIX = "AMI/L1B/FD"


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def generate_file_list(channels, start, end):
    """生成预期文件列表"""
    files = []
    # 按 10 分钟间隔生成
    current = start
    while current <= end:
        for ch in channels:
            fname = f"gk2a_ami_le1b_{ch}_fd020ge_{current:%Y%m%d%H%M}.nc"
            s3_path = f"{S3_BUCKET}/{S3_PREFIX}/{current:%Y%m}/{current:%d}/{current:%H}/{fname}"
            local_path = OUTPUT_DIR / f"{ch}" / fname
            files.append((s3_path, local_path, ch, current))
        # 每 10 分钟
        current += timedelta(minutes=10)
    return files


def download_files(file_list, fs, list_only=False):
    """下载文件列表"""
    total = len(file_list)
    downloaded = 0
    skipped = 0
    failed = 0

    log(f"开始下载: {total} 个文件")
    if list_only:
        for s3_path, local_path, ch, dt in file_list:
            try:
                info = fs.info(s3_path)
                size_mb = info["size"] / 1024 / 1024
                print(f"  {s3_path} ({size_mb:.1f} MB)")
            except FileNotFoundError:
                print(f"  {s3_path} (不存在)")
        return 0, 0, 0

    for i, (s3_path, local_path, ch, dt) in enumerate(file_list, 1):
        # 断点续传
        if local_path.exists() and local_path.stat().st_size > 1000:
            skipped += 1
            if i % 10 == 0:
                log(f"  [{i}/{total}] 跳过 {local_path.name}")
            continue

        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            fs.get(s3_path, str(local_path))
            size_mb = local_path.stat().st_size / 1024 / 1024
            downloaded += 1
            if i % 10 == 0 or i <= 5:
                log(f"  [{i}/{total}] {local_path.name} ({size_mb:.1f} MB)")
        except FileNotFoundError:
            failed += 1
            if failed <= 5:
                log(f"  [{i}/{total}] 不存在: {s3_path}")
        except Exception as e:
            failed += 1
            if failed <= 5:
                log(f"  [{i}/{total}] 错误: {e}")

    return downloaded, skipped, failed


def main():
    parser = argparse.ArgumentParser(description="下载 GK2A AMI L1B 数据")
    parser.add_argument("--channels", nargs="+", default=DEFAULT_CHANNELS,
                        help=f"通道列表 (默认: {DEFAULT_CHANNELS})")
    parser.add_argument("--all-channels", action="store_true",
                        help="下载全部 16 个通道")
    parser.add_argument("--start", required=True, help="起始时间 (UTC, 格式: '2026-09-10 00:00')")
    parser.add_argument("--end", required=True, help="截止时间 (UTC)")
    parser.add_argument("--list-only", action="store_true", help="只列出文件不下载")
    args = parser.parse_args()

    channels = ALL_CHANNELS if args.all_channels else args.channels
    start = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
    end = datetime.strptime(args.end, "%Y-%m-%d %H:%M")

    log("=" * 60)
    log("GK2A (GEO-KOMPSAT-2A) AMI L1B 数据下载")
    log("=" * 60)
    log(f"  通道: {channels}")
    log(f"  时间: {start} ~ {end} UTC")
    log(f"  输出: {OUTPUT_DIR}")

    # 生成文件列表
    file_list = generate_file_list(channels, start, end)
    log(f"  预期文件: {len(file_list)} 个")

    if not file_list:
        log("无文件, 退出")
        return

    # 连接 S3
    log("\n连接 S3...")
    fs = s3fs.S3FileSystem(anon=True)

    # 下载
    log("\n开始下载...")
    downloaded, skipped, failed = download_files(file_list, fs, args.list_only)

    if args.list_only:
        return

    # 汇总
    log(f"\n{'=' * 60}")
    log(f"下载完成!")
    log(f"  新下载: {downloaded}")
    log(f"  跳过(已存在): {skipped}")
    log(f"  失败/不存在: {failed}")
    log(f"  输出目录: {OUTPUT_DIR}")

    # 按通道统计
    log(f"\n按通道统计:")
    for ch in channels:
        ch_dir = OUTPUT_DIR / ch
        if ch_dir.exists():
            files = list(ch_dir.glob("*.nc"))
            total_size = sum(f.stat().st_size for f in files) / 1024 / 1024
            log(f"  {ch}: {len(files)} 文件, {total_size:.1f} MB")

    log(f"{'=' * 60}")


if __name__ == "__main__":
    main()
