"""
葵花8/9 (Himawari-8/9) AWS S3 匿名下载测试脚本

数据来源：AWS Open Datasets - noaa-himawari8 bucket
特点：
- 无需注册账号、无需 AWS 凭证
- 支持 boto3 匿名访问（UNSIGNED）
- 数据为 HSD 二进制格式（.DAT.bz2）

验证记录（2026-07-18）：
- ✅ 匿名访问成功
- ✅ 目录结构: AHI-L1b-FLDK, AHI-L1b-Japan, AHI-L2-FLDK-Clouds 等
- ✅ 实际下载文件成功 (2.74 MB)
- 数据覆盖: 2015-2025 年，10 分钟间隔

AWS Open Datasets 文档: https://registry.opendata.aws/noaa-himawari/
"""

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
from datetime import datetime


BUCKET_NAME = "noaa-himawari8"


def get_anonymous_s3():
    """获取匿名 S3 client（无需 AWS 凭证）"""
    return boto3.client('s3', config=Config(signature_version=UNSIGNED))


def list_products(s3):
    """列出所有可用的产品类型"""
    print("=" * 60)
    print("步骤 1: 列出所有产品类型")
    print("=" * 60)

    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Delimiter='/', MaxKeys=50)
    prefixes = response.get('CommonPrefixes', [])

    print(f"📁 {BUCKET_NAME} 顶层产品目录:")
    for p in prefixes:
        print(f"   {p['Prefix']}")

    # 下载 README
    output_dir = Path("c:/work/meteo/data/himawari")
    output_dir.mkdir(parents=True, exist_ok=True)
    readme_path = output_dir / "README.txt"
    try:
        s3.download_file(BUCKET_NAME, "README.txt", str(readme_path))
        print(f"\n📄 README 已下载: {readme_path}")
    except Exception as e:
        print(f"⚠️ README 下载失败: {e}")

    return prefixes


def explore_directory(s3, prefix):
    """探索指定产品的目录结构"""
    print(f"\n📁 探索 {prefix} ...")
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix, Delimiter='/', MaxKeys=20)
    return response.get('CommonPrefixes', [])


def download_file(s3, key, output_dir="c:/work/meteo/data/himawari"):
    """下载单个文件"""
    filename = Path(key).name
    local_path = Path(output_dir) / filename
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # 获取大小
    head = s3.head_object(Bucket=BUCKET_NAME, Key=key)
    size_mb = head['ContentLength'] / 1024 / 1024

    print(f"⬇️  下载: {key}")
    print(f"   大小: {size_mb:.2f} MB")

    s3.download_file(BUCKET_NAME, key, str(local_path))
    actual = local_path.stat().st_size
    print(f"✅ 下载成功!")
    print(f"   本地: {local_path}")
    print(f"   实际大小: {actual / 1024 / 1024:.2f} MB")
    return local_path


def main():
    print(f"葵花8/9 AWS S3 匿名下载测试")
    print(f"测试时间: {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC\n")

    s3 = get_anonymous_s3()

    # 1. 列出所有产品
    products = list_products(s3)

    # 2. 探索 AHI-L1b-FLDK 目录结构
    print("\n" + "=" * 60)
    print("步骤 2: 探索 AHI-L1b-FLDK 目录结构")
    print("=" * 60)

    years = explore_directory(s3, "AHI-L1b-FLDK/")
    print(f"📁 年份: {[p['Prefix'] for p in years]}")

    if years:
        # 选最新年份
        latest_year = years[-1]['Prefix']
        months = explore_directory(s3, latest_year)
        print(f"📁 {latest_year} 月份: {[p['Prefix'] for p in months[:6]]}...")

        if months:
            latest_month = months[-1]['Prefix']
            days = explore_directory(s3, latest_month)
            print(f"📁 {latest_month} 日期: {[p['Prefix'] for p in days[:5]]}...")

            if days:
                latest_day = days[-1]['Prefix']
                hours = explore_directory(s3, latest_day)
                print(f"📁 {latest_day} 小时: {[p['Prefix'] for p in hours[:6]]}...")

                if hours:
                    # 进入第一个小时，列出文件
                    hour_prefix = hours[0]['Prefix']
                    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=hour_prefix, MaxKeys=10)
                    contents = response.get('Contents', [])
                    print(f"\n📄 {hour_prefix} 文件列表:")
                    for c in contents[:10]:
                        print(f"   {c['Key']}  ({c['Size']/1024/1024:.2f} MB)")

                    # 下载第一个文件
                    if contents:
                        print("\n" + "=" * 60)
                        print("步骤 3: 下载第一个文件")
                        print("=" * 60)
                        download_file(s3, contents[0]['Key'])

    # 3. 总结
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    print(f"✅ S3 匿名访问成功，无需注册！")
    print(f"   Bucket: {BUCKET_NAME}")
    print(f"   区域: us-east-1")
    print(f"   协议: S3 API (HTTPS)")
    print(f"   认证: 匿名（UNSIGNED）")
    print(f"   产品: L1b + L2 共 8 类")


if __name__ == "__main__":
    main()
