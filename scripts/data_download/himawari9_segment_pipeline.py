"""
Himawari-9 华东真彩色图 - 仅下载所需FLDK分段
只下载 S0210(48-36°N) + S0310(36-24°N) 共6个文件/时次
satpy的GEOSegmentYAMLReader会自动用NaN填充其余分段，构建全圆盘几何
"""
import warnings
warnings.filterwarnings('ignore')
import sys
sys.stdout.reconfigure(line_buffering=True)

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
from datetime import datetime, timezone, timedelta
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from satpy import Scene
from pyresample.geometry import AreaDefinition
from PIL import Image
import glob


def log(msg):
    print(msg, flush=True)


def get_anonymous_s3():
    return boto3.client('s3', config=Config(signature_version=UNSIGNED))


def find_daytime_time_slots(bucket="noaa-himawari9", num_slots=6):
    """找到最新的白天时次(UTC 02:00-05:00, 北京时间10:00-13:00, 太阳高度角最佳)
    只下载S0210+S0310分段"""
    s3 = get_anonymous_s3()
    now_utc = datetime.now(timezone.utc)
    
    for days_back in range(0, 3):
        check_date = now_utc - timedelta(days=days_back)
        date_str = f"{check_date:%Y/%m/%d}"
        prefix = f"AHI-L1b-FLDK/{date_str}/"
        
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")
        time_prefixes = sorted([p['Prefix'] for p in resp.get('CommonPrefixes', [])])
        
        if not time_prefixes:
            continue
        
        log(f"  {date_str} 有 {len(time_prefixes)} 个时次")
        
        # 筛选白天时次: UTC 02:00-05:00 (北京 10:00-13:00)
        pattern_b = re.compile(r'_B0[123]_FLDK_')
        daytime_slots = []
        
        for tp in time_prefixes:
            time_label = tp.strip('/').split('/')[-1]
            hour = int(time_label[:2])
            # UTC 02:00-05:00 = 北京时间 10:00-13:00 (太阳高度角好)
            if 2 <= hour <= 5:
                resp2 = s3.list_objects_v2(Bucket=bucket, Prefix=tp)
                files = [obj['Key'] for obj in resp2.get('Contents', [])]
                needed_files = []
                for f in files:
                    name = f.split('/')[-1]
                    if pattern_b.search(name) and ('_S0210.' in name or '_S0310.' in name):
                        needed_files.append(f)
                
                if len(needed_files) >= 6:
                    daytime_slots.append((time_label, date_str.replace('/', ''), needed_files))
        
        if len(daytime_slots) >= num_slots:
            # 取最后num_slots个(最接近中午的)
            result = daytime_slots[-num_slots:]
            log(f"  找到 {len(result)} 个白天时次 (UTC 02:00-05:00)")
            for tl, _, _ in result:
                log(f"    {tl} UTC (北京 {int(tl[:2])+8}:{tl[2:]})")
            return result
        elif daytime_slots:
            log(f"  只找到 {len(daytime_slots)} 个白天时次")
            return daytime_slots
    
    return []


def download_segments(time_label, date_part, files, bucket="noaa-himawari9"):
    """下载一个时次的6个分段文件"""
    out_dir = Path(f"c:/work/meteo/data/himawari9/seg_{date_part}_{time_label}")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for i, key in enumerate(files):
        name = key.split('/')[-1]
        local_path = out_dir / name
        if local_path.exists():
            log(f"  [{i+1}/6] 跳过: {name}")
            continue
        log(f"  [{i+1}/6] 下载: {name}")
        s3 = get_anonymous_s3()
        s3.download_file(bucket, key, str(local_path))
    
    total_mb = sum(f.stat().st_size for f in out_dir.glob('*.bz2')) / (1024*1024)
    log(f"  完成: {len(list(out_dir.glob('*.bz2')))} 文件, {total_mb:.1f} MB")
    return out_dir


def generate_true_color(data_dir, time_label):
    """生成华东真彩色图"""
    log(f"\n--- 生成真彩图: {time_label} ---")
    
    files = sorted([str(f) for f in Path(data_dir).glob('HS_H09_*_B0[123]_*.DAT.bz2')])
    log(f"  文件数: {len(files)}")
    
    scn = Scene(filenames=files, reader='ahi_hsd')
    scn.load(['B01', 'B02', 'B03'])
    
    # 检查数据
    for band in ['B01', 'B02', 'B03']:
        vals = scn[band].values
        valid_pct = np.sum(vals > 0) / vals.size * 100
        log(f"  {band}: shape={scn[band].shape}, 有效={valid_pct:.1f}%")
    
    # 重采样到华东
    east_china_area = AreaDefinition(
        'east_china', 'East China', 'east_china',
        {'proj': 'longlat', 'datum': 'WGS84', 'ellps': 'WGS84'},
        900, 1500,
        (114.0, 23.0, 123.0, 38.0),
    )
    
    log(f"  重采样到华东区域...")
    new_scn = scn.resample(east_china_area, resampler='nearest', radius_of_influence=5000)
    
    r = new_scn['B03'].values / 100.0
    g = new_scn['B02'].values / 100.0
    b = new_scn['B01'].values / 100.0
    
    r = np.nan_to_num(r, nan=0.0)
    g = np.nan_to_num(g, nan=0.0)
    b = np.nan_to_num(b, nan=0.0)
    
    valid_r = np.sum(r > 0) / r.size * 100
    log(f"  华东区域有效像素: {valid_r:.1f}%")
    
    def stretch(img):
        mask = img > 0
        if not np.any(mask):
            return img
        p2 = np.percentile(img[mask], 2)
        p98 = np.percentile(img[mask], 98)
        return np.clip((img - p2) / (p98 - p2 + 1e-10), 0, 1)
    
    r = stretch(r) ** (1.0/2.2)
    g = stretch(g) ** (1.0/2.2)
    b = stretch(b) ** (1.0/2.2)
    
    rgb = np.dstack([r, g, b])
    log(f"  RGB shape: {rgb.shape}")
    return rgb


def save_image(rgb, output_path, time_label):
    """保存真彩色图"""
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.imshow(rgb)
    
    # 格式化时间标签
    date_str = time_label[:8]
    time_str = time_label[8:]
    title_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:]} UTC"
    
    ax.set_title(f'Himawari-9 真彩色图 - 华东\n{title_time}\n(FLDK S0210+S0310, 仅下载6/30文件)',
                 fontsize=14, fontfamily='sans-serif')
    ax.axis('off')
    
    lons = np.linspace(114, 123, 10)
    lats = np.linspace(23, 38, 16)
    ax.set_xticks(np.linspace(0, rgb.shape[1]-1, len(lons)))
    ax.set_xticklabels([f'{lon:.0f}°E' for lon in lons], fontsize=8)
    ax.set_yticks(np.linspace(0, rgb.shape[0]-1, len(lats)))
    ax.set_yticklabels([f'{lat:.0f}°N' for lat in lats[::-1]], fontsize=8)
    ax.tick_params(axis='both', which='both', length=3, labelsize=8)
    ax.text(0.02, 0.02, '114°E-123°E, 23°N-38°N\nnoaa-himawari9 S3 | FLDK S0210+S0310',
            transform=ax.transAxes, fontsize=9,
            color='white', bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    log(f"  ✅ 保存: {output_path}")


def create_animation(rgb_list, time_labels, output_path):
    """创建GIF动画"""
    log(f"\n--- 创建动画 GIF ({len(rgb_list)} 帧) ---")
    
    frames = []
    for rgb, label in zip(rgb_list, time_labels):
        fig, ax = plt.subplots(figsize=(10, 14))
        ax.imshow(rgb)
        
        date_str = label[:8]
        time_str = label[8:]
        title_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:]} UTC"
        
        ax.set_title(f'Himawari-9 真彩色图 - 华东\n{title_time}',
                     fontsize=14, fontfamily='sans-serif')
        ax.axis('off')
        
        lons = np.linspace(114, 123, 10)
        lats = np.linspace(23, 38, 16)
        ax.set_xticks(np.linspace(0, rgb.shape[1]-1, len(lons)))
        ax.set_xticklabels([f'{lon:.0f}°E' for lon in lons], fontsize=8)
        ax.set_yticks(np.linspace(0, rgb.shape[0]-1, len(lats)))
        ax.set_yticklabels([f'{lat:.0f}°N' for lat in lats[::-1]], fontsize=8)
        ax.tick_params(axis='both', which='both', length=3, labelsize=8)
        
        plt.tight_layout()
        
        fig.canvas.draw()
        w, h = fig.canvas.get_width_height()
        frame = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        frame = frame.reshape((h, w, 4))[:, :, :3]
        frames.append(frame)
        plt.close()
    
    frames_pil = [Image.fromarray(f) for f in frames]
    frames_pil[0].save(
        output_path,
        save_all=True,
        append_images=frames_pil[1:],
        duration=500,
        loop=0,
        optimize=True
    )
    log(f"  ✅ 动画保存: {output_path}")


if __name__ == "__main__":
    output_dir = Path("c:/work/meteo/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 找到白天6个时次 (UTC 02:00-05:00, 北京时间10:00-13:00)
    log("=== 查找白天时次 (UTC 02:00-05:00) ===")
    slots = find_daytime_time_slots(num_slots=6)
    
    if not slots:
        log("❌ 未找到有效时次!")
        sys.exit(1)
    
    for i, (time_label, date_part, files) in enumerate(slots):
        log(f"  时次 {i+1}: {date_part} {time_label} ({len(files)} 文件)")
    
    # 2. 下载并生成真彩图
    rgb_list = []
    time_labels = []
    
    for i, (time_label, date_part, files) in enumerate(slots):
        log(f"\n{'='*60}")
        log(f"处理时次 {i+1}/{len(slots)}: {date_part} {time_label}")
        log(f"{'='*60}")
        
        data_dir = download_segments(time_label, date_part, files)
        rgb = generate_true_color(data_dir, f"{date_part}_{time_label}")
        
        png_path = output_dir / f"east_china_seg_{date_part}_{time_label}.png"
        save_image(rgb, str(png_path), f"{date_part}_{time_label}")
        
        rgb_list.append(rgb)
        time_labels.append(f"{date_part}_{time_label}")
    
    # 3. 创建动画
    if len(rgb_list) >= 2:
        gif_path = output_dir / "east_china_seg_animation.gif"
        create_animation(rgb_list, time_labels, str(gif_path))
    
    log(f"\n{'='*60}")
    log(f"✅ 全部完成!")
    log(f"  共处理 {len(rgb_list)} 个时次")
    log(f"  每个时次仅下载6个文件(约70MB), 而非全圆盘30个文件(454MB)")
    log(f"  节省下载量: {len(rgb_list)} × (454-70) = {len(rgb_list) * 384} MB")
    log(f"{'='*60}")

