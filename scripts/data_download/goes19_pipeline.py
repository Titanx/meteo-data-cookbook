"""
GOES-19 (GOES-East) 卫星数据下载与真彩色图生成

数据来源: AWS Open Datasets - noaa-goes19 bucket (匿名访问)
覆盖范围: 美洲 (GOES-East, 定点 75.2°W)
产品: ABI-L1b-RadF (Full Disk 全圆盘)
特点:
- 无需注册账号、无需 AWS 凛证
- 数据为 NetCDF4 格式 (.nc)
- 实时更新 (10分钟间隔)
- 16 个通道, 可生成真彩色图

GOES-19 于 2025-04-04 接替 GOES-16 成为业务 GOES-East 卫星。
GOES-16 已停止数据分发, 转入存储位置 104.7°W。

AWS Open Datasets: https://registry.opendata.aws/noaa-goes/
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import warnings
warnings.filterwarnings('ignore')

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
from datetime import datetime, timedelta, timezone
import os
import re


BUCKET_NAME = "noaa-goes19"
OUTPUT_BASE = Path("c:/work/meteo/data/goes19")


def get_anonymous_s3():
    """获取匿名 S3 client"""
    return boto3.client('s3', config=Config(signature_version=UNSIGNED))


def list_available_times(s3, product="ABI-L1b-RadF", target_date=None, max_hours=24):
    """列出指定日期的可用时间"""
    if target_date is None:
        target_date = datetime.now(timezone.utc)

    year = target_date.strftime("%Y")
    day_of_year = target_date.timetuple().tm_yday
    day_str = f"{day_of_year:03d}"

    prefix = f"{product}/{year}/{day_str}/"
    print(f"查询: s3://{BUCKET_NAME}/{prefix}")

    hours = {}
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix, Delimiter='/'):
        for cp in page.get('CommonPrefixes', []):
            hour = cp['Prefix'].split('/')[-2]
            hours[hour] = cp['Prefix']

    print(f"可用小时: {sorted(hours.keys())}")
    return hours


def list_files_in_hour(s3, hour_prefix, channel=None):
    """列出某小时内指定通道的文件"""
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=hour_prefix, MaxKeys=500)
    contents = response.get('Contents', [])

    files = []
    for c in contents:
        key = c['Key']
        fname = Path(key).name
        # 解析通道: OR_ABI-L1b-RadF-M6C01_G19_s...
        m = re.search(r'M6C(\d+)', fname)
        if m:
            ch = int(m.group(1))
            if channel is None or ch == channel:
                files.append({
                    'key': key,
                    'name': fname,
                    'channel': ch,
                    'size_mb': c['Size'] / 1024 / 1024,
                    'last_modified': c['LastModified']
                })
    return files


def find_latest_scan_files(s3, product="ABI-L1b-RadF", target_date=None):
    """找到最近一次扫描的所有通道文件"""
    if target_date is None:
        target_date = datetime.now(timezone.utc)

    # 尝试最近几个小时
    for offset_hours in range(0, 6):
        check_date = target_date - timedelta(hours=offset_hours)
        year = check_date.strftime("%Y")
        day_of_year = check_date.timetuple().tm_yday
        day_str = f"{day_of_year:03d}"
        hour = check_date.strftime("%H")

        prefix = f"{product}/{year}/{day_str}/{hour}/"
        print(f"  尝试: {prefix}")

        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix, MaxKeys=500)
        contents = response.get('Contents', [])

        if not contents:
            continue

        # 解析所有文件, 按时间戳分组
        scans = {}
        for c in contents:
            fname = Path(c['Key']).name
            m = re.search(r's(\d{7})(\d{6})', fname)
            if m:
                scan_time_str = m.group(1) + m.group(2)
                if scan_time_str not in scans:
                    scans[scan_time_str] = []
                ch_m = re.search(r'M6C(\d+)', fname)
                if ch_m:
                    scans[scan_time_str].append({
                        'key': c['Key'],
                        'name': fname,
                        'channel': int(ch_m.group(1)),
                        'size_mb': c['Size'] / 1024 / 1024
                    })

        if scans:
            # 取最近一次扫描
            latest_scan = sorted(scans.keys())[-1]
            scan_files = scans[latest_scan]
            print(f"  找到 {len(scans)} 次扫描, 最近: {latest_scan}")
            print(f"  文件数: {len(scan_files)}")

            # 解析时间
            yyyy = int(latest_scan[:4])
            ddd = int(latest_scan[4:7])
            hh = int(latest_scan[7:9])
            mm = int(latest_scan[9:11])
            ss = int(latest_scan[11:13])
            scan_date = datetime(yyyy, 1, 1, tzinfo=timezone.utc) + timedelta(days=ddd-1, hours=hh, minutes=mm, seconds=ss)
            print(f"  扫描时间: {scan_date:%Y-%m-%d %H:%M:%S} UTC")

            return scan_files, scan_date

    return None, None


def download_scan_files(s3, scan_files, scan_date, channels=None):
    """下载指定通道的文件"""
    if channels is None:
        # 真彩色所需通道: C01(蓝), C02(红), C03(绿/nir)
        # 加上 C05(近红外) 用于改进绿色
        channels = [1, 2, 3]

    time_str = scan_date.strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_BASE / f"scan_{time_str}"
    out_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    total_size = 0
    for f in scan_files:
        if f['channel'] not in channels:
            continue
        local_path = out_dir / f['name']
        print(f"  下载 C{f['channel']:02d}: {f['size_mb']:.1f} MB")
        s3.download_file(BUCKET_NAME, f['key'], str(local_path))
        downloaded.append(local_path)
        total_size += f['size_mb']

    print(f"\n下载完成: {len(downloaded)} 文件, 共 {total_size:.1f} MB")
    print(f"输出目录: {out_dir}")
    return out_dir, downloaded


def generate_true_color(data_dir, scan_date, region_name="Full Disk"):
    """使用 satpy 生成真彩色图 (手动合成, 不依赖 pyspectral)"""
    from satpy import Scene
    from satpy.resample import get_area_def
    import numpy as np
    from PIL import Image

    print(f"\n{'=' * 60}")
    print(f"生成真彩色图: {region_name}")
    print(f"{'=' * 60}")

    # 加载场景
    print("加载 satpy Scene (abi_l1b reader)...")
    scn = Scene(reader='abi_l1b', filenames=[str(f) for f in data_dir.glob("*.nc")])

    # 加载通道 (C01=蓝, C02=红, C03=近红外)
    print("加载通道: C01, C02, C03...")
    scn.load(['C01', 'C02', 'C03'])

    # 打印各通道形状
    for ch in ['C01', 'C02', 'C03']:
        print(f"  {ch}: shape={scn[ch].shape}, resolution={scn[ch].attrs.get('resolution', 'unknown')}")

    # 手动降采样 C02 (0.5km -> 1km): 每2个像素取1个
    # 避免使用 satpy resample, 节省内存
    print("手动降采样 C02 (0.5km -> 1km)...")
    r_data = np.array(scn['C02'].values[::2, ::2])  # Red (0.64μm) 21696->10848
    g_data = np.array(scn['C03'].values)              # NIR (0.86μm) 10848
    b_data = np.array(scn['C01'].values)              # Blue (0.47μm) 10848

    print(f"  降采样后: R={r_data.shape}, G={g_data.shape}, B={b_data.shape}")

    # 归一化函数
    def normalize(arr, pct_lo=2, pct_hi=98):
        lo, hi = np.nanpercentile(arr, [pct_lo, pct_hi])
        if hi - lo < 1e-10:
            return np.zeros_like(arr)
        arr = np.clip((arr - lo) / (hi - lo), 0, 1)
        return arr

    r_n = normalize(r_data)
    g_n = normalize(g_data)
    b_n = normalize(b_data)

    # Gamma 校正
    gamma = 2.2
    rgb = np.dstack([r_n**gamma, g_n**gamma, b_n**gamma])

    time_str = scan_date.strftime("%Y%m%d_%H%M%S")

    # 保存全圆盘图
    out_path_full = data_dir / f"goes19_truecolor_{time_str}_fulldisk.png"
    # satpy 数据是上南下北, 需要翻转
    rgb_flip = np.flipud(rgb)
    img = Image.fromarray((rgb_flip * 255).astype(np.uint8))
    img.save(str(out_path_full))
    print(f"全圆盘真彩色图: {out_path_full} ({img.size[0]}x{img.size[1]})")

    # 裁剪北美区域 (15-60°N, 60-130°W)
    try:
        print("裁剪北美区域 (15-60°N, 60-130°W)...")
        scn_na = scn.crop(ll_bbox=(-130, 15, -60, 60))
        r_na = np.array(scn_na['C02'].values[::2, ::2])
        g_na = np.array(scn_na['C03'].values)
        b_na = np.array(scn_na['C01'].values)
        r_na_n = normalize(r_na)
        g_na_n = normalize(g_na)
        b_na_n = normalize(b_na)
        rgb_na = np.dstack([r_na_n**gamma, g_na_n**gamma, b_na_n**gamma])
        rgb_na = np.flipud(rgb_na)
        out_path_na = data_dir / f"goes19_truecolor_{time_str}_namerica.png"
        img_na = Image.fromarray((rgb_na * 255).astype(np.uint8))
        img_na.save(str(out_path_na))
        print(f"北美真彩色图: {out_path_na} ({img_na.size[0]}x{img_na.size[1]})")
    except Exception as e:
        print(f"北美裁剪失败: {e}")
        import traceback
        traceback.print_exc()
        out_path_na = None

    # 裁剪南美区域 (-55-15°N, 35-90°W)
    try:
        print("裁剪南美区域 (-55-15°N, 35-90°W)...")
        scn_sa = scn.crop(ll_bbox=(-90, -55, -35, 15))
        r_sa = np.array(scn_sa['C02'].values[::2, ::2])
        g_sa = np.array(scn_sa['C03'].values)
        b_sa = np.array(scn_sa['C01'].values)
        r_sa_n = normalize(r_sa)
        g_sa_n = normalize(g_sa)
        b_sa_n = normalize(b_sa)
        rgb_sa = np.dstack([r_sa_n**gamma, g_sa_n**gamma, b_sa_n**gamma])
        rgb_sa = np.flipud(rgb_sa)
        out_path_sa = data_dir / f"goes19_truecolor_{time_str}_samerica.png"
        img_sa = Image.fromarray((rgb_sa * 255).astype(np.uint8))
        img_sa.save(str(out_path_sa))
        print(f"南美真彩色图: {out_path_sa} ({img_sa.size[0]}x{img_sa.size[1]})")
    except Exception as e:
        print(f"南美裁剪失败: {e}")
        import traceback
        traceback.print_exc()
        out_path_sa = None

    return out_path_full


def main():
    print("=" * 60)
    print("GOES-19 (GOES-East) 卫星数据下载与真彩色图生成")
    print("=" * 60)
    print(f"当前 UTC 时间: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}")
    print(f"Bucket: {BUCKET_NAME}")
    print()

    s3 = get_anonymous_s3()

    # 1. 测试匿名访问
    print("步骤1: 测试 S3 匿名访问...")
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Delimiter='/', MaxKeys=20)
        prefixes = response.get('CommonPrefixes', [])
        print(f"  顶层产品目录: {[p['Prefix'] for p in prefixes[:10]]}")
        print("  匿名访问成功!")
    except Exception as e:
        print(f"  匿名访问失败: {e}")
        return

    # 2. 找到最近的扫描数据
    print("\n步骤2: 查找最近的全圆盘扫描数据...")
    scan_files, scan_date = find_latest_scan_files(s3, product="ABI-L1b-RadF")

    if scan_files is None:
        print("  未找到最近的扫描数据!")
        return

    # 统计通道分布
    channels_present = sorted(set(f['channel'] for f in scan_files))
    print(f"\n  本次扫描包含通道: {channels_present}")

    # 3. 下载真彩色所需通道 (C01, C02, C03)
    print("\n步骤3: 下载真彩色通道 (C01=蓝, C02=红, C03=近红外)...")
    out_dir, downloaded = download_scan_files(s3, scan_files, scan_date, channels=[1, 2, 3])

    if len(downloaded) < 3:
        print(f"  下载文件不足 3 个, 无法生成真彩色图!")
        return

    # 4. 生成真彩色图
    print("\n步骤4: 使用 satpy 生成真彩色图...")
    try:
        out_path = generate_true_color(out_dir, scan_date)
        print(f"\n真彩色图: {out_path}")
    except Exception as e:
        print(f"真彩色图生成失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("完成!")
    print(f"数据目录: {out_dir}")
    print(f"扫描时间: {scan_date:%Y-%m-%d %H:%M:%S} UTC")


if __name__ == "__main__":
    main()
