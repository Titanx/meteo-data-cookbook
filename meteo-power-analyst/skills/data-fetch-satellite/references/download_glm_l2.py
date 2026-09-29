"""
GOES GLM L2 闪电数据批量下载（AWS S3 匿名访问）
GLM: Geostationary Lightning Mapper
数据存储在 NOAA AWS Open Data，匿名访问无需认证

GLM L2: 20秒/文件，包含 Event → Group → Flash 三级结构
每个 flash 包含: 位置、能量、面积、质量标记
"""
import boto3
from botocore import UNSIGNED
from botocore.config import Config
import os
from datetime import datetime, timedelta
import argparse
import sys

def get_s3_client():
    """创建匿名 S3 客户端"""
    return boto3.client('s3', config=Config(signature_version=UNSIGNED))

def list_glm_files(s3, satellite, year, doy, hour):
    """列出指定时间的 GLM 文件
    
    Args:
        s3: boto3 S3 client
        satellite: '16'/'17'/'18'/'19'
        year: int, 4 位年
        doy: int, 年积日 (1-366)
        hour: int, 小时 (0-23)
    
    Returns:
        list of (key, size_bytes)
    """
    bucket = f'noaa-goes{satellite}'
    prefix = f"GLM-L2-LCFA/{year}/{doy:03d}/{hour:02d}/"
    
    try:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1000)
        if 'Contents' not in resp:
            return []
        return [(obj['Key'], obj['Size']) for obj in resp['Contents']]
    except Exception as e:
        print(f"错误列出文件: {e}")
        return []

def download_glm_file(s3, satellite, key, output_dir):
    """下载单个 GLM 文件
    
    Args:
        s3: boto3 S3 client
        satellite: '16'/'18'/'19'
        key: S3 key
        output_dir: 本地输出目录
    
    Returns:
        local_path: str, 本地路径，失败返回 None
    """
    bucket = f'noaa-goes{satellite}'
    filename = os.path.basename(key)
    local_path = os.path.join(output_dir, filename)
    
    if os.path.exists(local_path):
        size_local = os.path.getsize(local_path)
        # 文件存在且大小匹配则跳过
        try:
            resp = s3.head_object(Bucket=bucket, Key=key)
            size_remote = resp['ContentLength']
            if size_local == size_remote:
                print(f"  跳过，文件已存在: {filename} ({size_local/1024:.1f} KB)")
                return local_path
        except:
            pass
    
    try:
        s3.download_file(bucket, key, local_path)
        size_mb = os.path.getsize(local_path) / 1024 / 1024
        print(f"  ✓ 下载完成: {filename} ({size_mb:.3f} MB)")
        return local_path
    except Exception as e:
        print(f"  ✗ 下载失败: {filename} {e}")
        if os.path.exists(local_path):
            os.remove(local_path)
        return None

def download_range(satellite, start_dt, end_dt, output_dir, verbose=True):
    """下载指定时间范围的 GLM 数据
    
    Args:
        satellite: '16'/'18'/'19'
        start_dt: datetime (UTC)
        end_dt: datetime (UTC)
        output_dir: str, 输出目录
        verbose: bool
    
    Returns:
        list of downloaded local paths
    """
    s3 = get_s3_client()
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded = []
    current = start_dt
    
    while current <= end_dt:
        year = current.year
        doy = current.timetuple().tm_yday
        hour = current.hour
        
        if verbose:
            print(f"\n=== {year}-{doy:03d} {hour:02d}:00 UTC ===")
        
        files = list_glm_files(s3, satellite, year, doy, hour)
        if not files:
            print(f"  无文件")
            current += timedelta(hours=1)
            continue
        
        if verbose:
            print(f"  找到 {len(files)} 个文件 (20秒/文件)")
        
        for key, size in files:
            local = download_glm_file(s3, satellite, key, output_dir)
            if local:
                downloaded.append(local)
        
        current += timedelta(hours=1)
    
    if verbose:
        print(f"\n=== 下载完成 ===")
        print(f"总计下载 {len(downloaded)} 个文件")
        total_mb = sum(os.path.getsize(f) for f in downloaded) / 1024 / 1024
        print(f"总大小: {total_mb:.2f} MB")
    
    return downloaded

def main():
    parser = argparse.ArgumentParser(
        description='批量下载 GOES GLM L2 闪电数据 (AWS S3 匿名访问)'
    )
    parser.add_argument('--satellite', '-s', default='18', 
                      choices=['16', '17', '18', '19'],
                      help='卫星编号 (16: GOES-16 East, 18: GOES-18 West, 19: GOES-19 East)')
    parser.add_argument('--start', '-b', required=True, 
                      help='开始时间 UTC, 格式: YYYY-MM-DD HH:MM')
    parser.add_argument('--end', '-e', required=True, 
                      help='结束时间 UTC, 格式: YYYY-MM-DD HH:MM')
    parser.add_argument('--output', '-o', 
                      default=r'c:\work\meteo\data\glm\l2',
                      help='输出目录')
    args = parser.parse_args()
    
    # 解析时间
    try:
        start_dt = datetime.strptime(args.start, '%Y-%m-%d %H:%M')
        end_dt = datetime.strptime(args.end, '%Y-%m-%d %H:%M')
    except ValueError as e:
        print(f"时间格式错误: {e}")
        print("使用格式: YYYY-MM-DD HH:MM (UTC)")
        sys.exit(1)
    
    if start_dt >= end_dt:
        print("错误: start >= end")
        sys.exit(1)
    
    print(f"GOES GLM L2 下载")
    print(f"卫星: GOES-{args.satellite}")
    print(f"时间范围: {start_dt.isoformat()} UTC ~ {end_dt.isoformat()} UTC")
    print(f"输出目录: {args.output}")
    print()
    
    downloaded = download_range(args.satellite, start_dt, end_dt, args.output)
    print()
    
    if downloaded:
        print("示例文件:")
        for f in downloaded[:3]:
            print(f"  {f}")
    else:
        print("未下载任何文件，请检查时间范围是否正确")
        sys.exit(1)

if __name__ == "__main__":
    main()
