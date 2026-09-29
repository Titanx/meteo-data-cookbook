"""
解析 FY-4A LMI 闪电数据文件

FY-4A LMI 数据格式：NetCDF (CF-1.7)
文件名：FY4A-_LMI---_N_REGX_1047E_L2-_LMI{E/G/F}_SING_NUL_yyyyMMddHHmmss_yyyMMddHHmmss_7800M_NXXV1.NC

产品类型：
- LMIE: Event 产品（单像素事件，1分钟/文件）
- LMIG: Group 产品（相邻事件聚类）
- LMIF: Flash 产品（完整闪电）

变量说明（LMIE）：
  LON: Event Longitude, degree
  LAT: Event Latitude, degree
  ETT: Event TAI Time, ms (从2000-01-01 00:00:00 TAI起算)
  EOT: Event Observe Time, ms
  ER:  Event Radiance, μJ/m²/ster
  EFP: Event FootPrint, km
  EA:  Event Address
  EGA: Event Group Address
  EXP: Event X Pixel
  EYP: Event Y Pixel
  DQF: Data Quality Flag (0=good, 1=conditional, 2=out_of_range, 3=no_value)
"""
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import re

# FY-4A LMI TAI 时间基准（2000-01-01 TAI ≈ 1999-12-31 23:59:28 UTC）
TAI_EPOCH = datetime(2000, 1, 1)

def parse_fy4_lmi_filename(filepath):
    """解析 FY-4 LMI 文件名"""
    basename = os.path.basename(filepath)
    # FY4A-_LMI---_N_REGX_1047E_L2-_LMIE_SING_NUL_20200701000000_20200701000449_7800M_N02V1.NC
    pattern = r'FY4A-_LMI---_N_REGX_1047E_L2-_(LMI[EGF])_SING_NUL_(\d{14})_(\d{14})_7800M_N\d+V1\.NC'
    m = re.search(pattern, basename, re.IGNORECASE)
    if not m:
        return None
    return {
        'product': m.group(1),
        'start_time': datetime.strptime(m.group(2), '%Y%m%d%H%M%S'),
        'end_time': datetime.strptime(m.group(3), '%Y%m%d%H%M%S'),
    }

def parse_fy4_lmi_event(filepath, bbox=None):
    """解析 FY-4A LMI Event 产品（LMIE）

    Args:
        filepath: .NC 文件路径
        bbox: (lon_min, lat_min, lon_max, lat_max) 裁剪区域
    
    Returns:
        dict with events and metadata
    """
    info = parse_fy4_lmi_filename(filepath)
    if info is None:
        print(f"文件名解析失败，尝试直接读取: {os.path.basename(filepath)}")

    ds = xr.open_dataset(filepath, engine='h5netcdf')

    # 提取元数据
    metadata = {
        'satellite': ds.attrs.get('platform_ID', 'FY4A'),
        'instrument': ds.attrs.get('instrument_ID', 'LMI'),
        'product': info['product'] if info else 'LMIE',
        'start_time': str(ds.attrs.get('time_coverage_start', '')),
        'end_time': str(ds.attrs.get('time_coverage_end', '')),
        'spatial_resolution': ds.attrs.get('spatial_resolution', '7800m'),
        'scene_id': ds.attrs.get('scene_id', 'Region'),
        'quality_flag': int(ds.attrs.get('Data Quality', 0)),
    }

    # 提取变量
    lon = ds['LON'].values.astype(np.float32)
    lat = ds['LAT'].values.astype(np.float32)

    # TAI 时间 → UTC
    ett = ds['ETT'].values.astype(np.float64)  # ms
    # TAI 比 UTC 快 37 秒（2000-01-01 时差）
    # ETT 是 TAI 时间，从 2000-01-01 00:00:00 TAI 起算（ms）
    event_times = []
    for t_ms in ett:
        if t_ms > 0:
            dt = TAI_EPOCH + timedelta(seconds=t_ms / 1000)
            event_times.append(dt)
        else:
            event_times.append(None)

    # 辐射强度
    er = ds['ER'].values.astype(np.float32) if 'ER' in ds else None

    # 事件足迹（km²）
    efp = ds['EFP'].values.astype(np.float32) if 'EFP' in ds else None

    # 质量标志
    dqf = ds['DQF'].values.astype(np.int8) if 'DQF' in ds else None

    # Group 地址（用于关联到 Group 产品）
    ega = ds['EGA'].values.astype(np.int32) if 'EGA' in ds else None

    # 像素坐标
    exp = ds['EXP'].values.astype(np.int16) if 'EXP' in ds else None
    eyp = ds['EYP'].values.astype(np.int16) if 'EYP' in ds else None

    # 组装为结构化数组
    n = len(lon)
    dtype = [
        ('lon', 'f4'), ('lat', 'f4'),
        ('radiance', 'f4'), ('footprint_km2', 'f4'),
        ('quality_flag', 'i1'), ('group_addr', 'i4'),
        ('x_pixel', 'i2'), ('y_pixel', 'i2'),
        ('time', 'O'),  # object (datetime or None)
    ]
    events = np.zeros(n, dtype=dtype)
    events['lon'] = lon
    events['lat'] = lat
    events['radiance'] = er if er is not None else np.nan
    events['footprint_km2'] = efp if efp is not None else np.nan
    events['quality_flag'] = dqf if dqf is not None else -1
    events['group_addr'] = ega if ega is not None else -1
    events['x_pixel'] = exp if exp is not None else -1
    events['y_pixel'] = eyp if eyp is not None else -1
    events['time'] = np.array(event_times, dtype='O')

    # 区域裁剪
    if bbox is not None:
        lon_min, lat_min, lon_max, lat_max = bbox
        mask = (
            (events['lon'] >= lon_min) & (events['lon'] <= lon_max) &
            (events['lat'] >= lat_min) & (events['lat'] <= lat_max)
        )
        events = events[mask]

    ds.close()
    return {'events': events, 'metadata': metadata}

def print_fy4_lmi_summary(data, title=None):
    """打印 FY-4 LMI 数据摘要"""
    if title:
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")

    meta = data['metadata']
    print(f" 卫星: {meta['satellite']}")
    print(f" 仪器: {meta['instrument']}")
    print(f" 产品: {meta['product']}")
    print(f" 时间: {meta['start_time']} ~ {meta['end_time']}")
    print(f" 分辨率: {meta['spatial_resolution']}")
    print(f" 质量标记: {meta['quality_flag']}")

    events = data['events']
    print(f"\n 事件数: {len(events)}")

    if len(events) > 0:
        valid = events[events['time'] != np.array(None)]
        good = events[events['quality_flag'] == 0]

        print(f" 有效事件数: {len(valid)}")
        print(f" 高质量事件 (flag=0): {len(good)}")

        print(f"\n 位置范围:")
        print(f"   经度: {events['lon'].min():.2f}°E ~ {events['lon'].max():.2f}°E")
        print(f"   纬度: {events['lat'].min():.2f}°N ~ {events['lat'].max():.2f}°N")

        if np.any(~np.isnan(events['radiance'])):
            print(f"\n 辐射强度统计:")
            rad = events['radiance']
            valid_rad = rad[~np.isnan(rad)]
            if len(valid_rad) > 0:
                print(f"   范围: {valid_rad.min():.2f} ~ {valid_rad.max():.2f} μJ/m²/ster")
                print(f"   均值: {valid_rad.mean():.2f} μJ/m²/ster")

        if len(valid) > 0:
            times = [t for t in valid['time'] if t is not None]
            if times:
                print(f"\n 时间范围: {min(times)} ~ {max(times)} UTC")

        # 质量分布
        print(f"\n 质量分布:")
        for flag_val, flag_name in [(0, 'good'), (1, 'conditional'), (2, 'out_of_range'), (3, 'no_value')]:
            count = np.sum(events['quality_flag'] == flag_val)
            if count > 0:
                print(f"   {flag_name}: {count} ({count/len(events)*100:.1f}%)")

    return data

def main():
    """测试解析 FY-4 LMI 样本文件"""
    data_dir = r"c:\work\meteo\data\fy4\lmi"

    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir)
             if f.endswith('.NC') or f.endswith('.nc')]

    if not files:
        print("未找到 FY-4 LMI 样本文件")
        print("请先从 NSMC 门户下载数据：")
        print("  https://satellite.nsmc.org.cn/DataPortal/cn/home/index.html")
        print()
        print("或下载中科院订正数据集：")
        print("  https://doi.org/10.11888/Atmos.tpdc.303312")
        return

    print(f"找到 {len(files)} 个 FY-4 LMI 文件")

    for fpath in files[:3]:
        info = parse_fy4_lmi_filename(fpath)
        if info is None:
            print(f"\n无法解析文件名: {os.path.basename(fpath)}")
            continue

        if info['product'] == 'LMIE':
            data = parse_fy4_lmi_event(fpath)
            print_fy4_lmi_summary(data, os.path.basename(fpath))

            # 中国区域裁剪示例
            china_bbox = (73.0, 18.0, 135.0, 54.0)
            data_china = parse_fy4_lmi_event(fpath, bbox=china_bbox)
            print(f"\n 中国区域裁剪: {len(data_china['events'])} 事件")
            if len(data_china['events']) > 0:
                e = data_china['events']
                print(f"   范围: {e['lon'].min():.1f}°E ~ {e['lon'].max():.1f}°E, "
                      f"{e['lat'].min():.1f}°N ~ {e['lat'].max():.1f}°N")
        else:
            print(f"\n预览: {os.path.basename(fpath)} ({info['product']})")

if __name__ == "__main__":
    main()