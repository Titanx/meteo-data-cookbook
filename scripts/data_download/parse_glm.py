"""
解析 GLM L2 闪电数据文件
读取 netCDF-4 格式的 GLM 文件，提取闪击位置、能量、面积等信息
支持按区域裁剪（如 ERCOT/Texas）
"""
import h5py
import numpy as np
from datetime import datetime, timedelta
import os

# GLM 时间基准（2000-01-01 = 原点）
GLM_EPOCH = datetime(2000, 1, 1)

def parse_glm_file(filepath, bbox=None):
    """解析单个 GLM 文件，返回闪击数据
    
    Args:
        filepath: str, .nc 文件路径
        bbox: tuple of (lon_min, lat_min, lon_max, lat_max), 裁剪区域
              ERCOT Texas: (-106.5, 25.5, -93.0, 36.5)
    
    Returns:
        dict with keys:
            - flashes: structured array of flash data
            - groups: structured array of group data
            - events: structured array of event data
            - metadata: dict of file metadata
    """
    with h5py.File(filepath, 'r') as f:
        # 元数据
        metadata = {
            'satellite': f.attrs.get('platform_ID', b'').decode(),
            'instrument': f.attrs.get('instrument_ID', b'').decode(),
            'start_time': f.attrs.get('time_coverage_start', b'').decode(),
            'end_time': f.attrs.get('time_coverage_end', b'').decode(),
            'source': f.attrs.get('production_data_source', b'').decode(),
            'spatial_resolution': f.attrs.get('spatial_resolution', b'').decode(),
            'orbital_slot': f.attrs.get('orbital_slot', b'').decode(),
        }
        
        # 读取产品时间
        product_time = f['product_time'][()]
        t0 = GLM_EPOCH + timedelta(seconds=product_time)
        
        # 读取闪击数据
        n_flashes = f['flash_count'][()]
        result = {'metadata': metadata, 'product_time': t0}
        
        if n_flashes == 0:
            result['flashes'] = np.array([])
            result['groups'] = np.array([])
            result['events'] = np.array([])
            return result
        
        # 提取闪击数据（注意 scale_factor 和 _Unsigned 属性）
        # flash_area: int16 + _Unsigned=true → uint16, scale_factor=152601.86, units=m²
        # flash_energy: int16 + _Unsigned=true → uint16, scale_factor~1e-15, add_offset~2.8e-16, units=J
        area_raw = f['flash_area'][:].copy().view(np.uint16)
        area_scale = float(f['flash_area'].attrs.get('scale_factor', [1])[0])
        energy_raw = f['flash_energy'][:].copy().view(np.uint16)
        energy_scale = float(f['flash_energy'].attrs.get('scale_factor', [1])[0])
        energy_offset = float(f['flash_energy'].attrs.get('add_offset', [0])[0])
        
        flashes = {
            'id': f['flash_id'][:].copy(),
            'lat': f['flash_lat'][:].copy(),
            'lon': f['flash_lon'][:].copy(),
            'energy': energy_raw.astype(np.float64) * energy_scale + energy_offset,  # J
            'area': area_raw.astype(np.float64) * area_scale,                         # m²
            'quality_flag': f['flash_quality_flag'][:].copy(),
            'time_offset_first': f['flash_time_offset_of_first_event'][:].copy() * 1e-6,  # 秒
            'time_offset_last': f['flash_time_offset_of_last_event'][:].copy() * 1e-6,    # 秒
        }
        
        # 计算闪击绝对时间
        flash_times = [t0 + timedelta(seconds=float(off)) 
                       for off in flashes['time_offset_first']]
        flashes['time'] = np.array(flash_times, dtype='datetime64[us]')
        
        flashes['energy'] = flashes['energy'] * 1e-6  # J → MJ
        flashes['area'] = flashes['area'] * 1e-6       # m² → km²
        
        # 组装为结构化数组
        flash_dtype = [
            ('id', 'i4'), ('lat', 'f4'), ('lon', 'f4'),
            ('energy_mj', 'f4'), ('area_km2', 'f4'),
            ('quality_flag', 'i2'), ('time', 'datetime64[us]')
        ]
        flash_array = np.zeros(n_flashes, dtype=flash_dtype)
        flash_array['id'] = flashes['id']
        flash_array['lat'] = flashes['lat']
        flash_array['lon'] = flashes['lon']
        flash_array['energy_mj'] = flashes['energy']
        flash_array['area_km2'] = flashes['area']
        flash_array['quality_flag'] = flashes['quality_flag']
        flash_array['time'] = flashes['time']
        
        # 区域裁剪
        if bbox is not None and n_flashes > 0:
            lon_min, lat_min, lon_max, lat_max = bbox
            mask = (
                (flash_array['lon'] >= lon_min) &
                (flash_array['lon'] <= lon_max) &
                (flash_array['lat'] >= lat_min) &
                (flash_array['lat'] <= lat_max)
            )
            flash_array = flash_array[mask]
        
        result['flashes'] = flash_array
        result['groups'] = f['group_count'][()]
        result['events'] = f['event_count'][()]
        
        return result

def print_glm_summary(data, title=None):
    """打印 GLM 数据摘要"""
    if title:
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
    
    meta = data['metadata']
    print(f" 卫星: {meta['satellite']} ({meta['orbital_slot']})")
    print(f" 时间: {meta['start_time']} ~ {meta['end_time']}")
    print(f" 来源: {meta['source']}")
    print(f" 分辨率: {meta['spatial_resolution']}")
    print()
    
    flashes = data['flashes']
    print(f" 闪击数: {len(flashes)}")
    print(f" Group数: {data['groups']}")
    print(f" Event数: {data['events']}")
    
    if len(flashes) > 0:
        print(f"\n 闪击统计:")
        print(f"   纬度: {flashes['lat'].min():.2f}° ~ {flashes['lat'].max():.2f}°")
        print(f"   经度: {flashes['lon'].min():.2f}° ~ {flashes['lon'].max():.2f}°")
        print(f"   能量: {flashes['energy_mj'].min():.4f} ~ {flashes['energy_mj'].max():.4f} MJ")
        print(f"   面积: {flashes['area_km2'].min():.1f} ~ {flashes['area_km2'].max():.1f} km²")
        print(f"   质量标记: 0={np.sum(flashes['quality_flag']==0)}, 1={np.sum(flashes['quality_flag']==1)}")
        
        # 按质量标记拆分
        good = flashes[flashes['quality_flag'] == 0]
        if len(good) > 0:
            print(f"\n 高质量闪击 (flag=0): {len(good)}")
            print(f"   平均能量: {good['energy_mj'].mean():.4f} MJ")
            print(f"   平均面积: {good['area_km2'].mean():.1f} km²")
    
    return data

def main():
    """测试解析已下载的样本文件"""
    data_dir = r"c:\work\meteo\data\glm\sample"
    
    # 查找 GLM 文件
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) 
             if f.endswith('.nc')]
    
    if not files:
        print("未找到 GLM 样本文件，请先运行下载脚本")
        return
    
    print(f"找到 {len(files)} 个 GLM 文件")
    
    for fpath in files[:3]:
        data = parse_glm_file(fpath)
        print_glm_summary(data, os.path.basename(fpath))
        
        # 德州区域裁剪示例
        texas_bbox = (-106.5, 25.5, -93.0, 36.5)
        data_texas = parse_glm_file(fpath, bbox=texas_bbox)
        print(f"\n 德州区域裁剪: {len(data_texas['flashes'])} 闪击")
        if len(data_texas['flashes']) > 0:
            print(f"   范围: {data_texas['flashes']['lon'].min():.1f}°W ~ {data_texas['flashes']['lon'].max():.1f}°W, "
                  f"{data_texas['flashes']['lat'].min():.1f}°N ~ {data_texas['flashes']['lat'].max():.1f}°N")

if __name__ == "__main__":
    main()