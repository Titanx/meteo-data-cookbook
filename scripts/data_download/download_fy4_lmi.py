"""
FY-4A LMI 闪电数据下载

FY-4A LMI (Lightning Mapping Imager) 是中国风云四号A星的闪电成像仪，
搭载在 FY-4A（104.7°E）静止轨道卫星上，提供中国及周边区域的闪电探测数据。

数据获取方式：
1. NSMC 官方门户（需注册，推荐实时数据）：
   https://satellite.nsmc.org.cn/DataPortal/cn/home/index.html
   选择卫星: FY-4A → 仪器: LMI → 设置时间范围 → 检索下载

2. 中科院订正数据集（公开下载，2019-2023，推荐科研）：
   https://doi.org/10.11888/Atmos.tpdc.303312
   CSV + NetCDF 格式，每日文件，包含订正后的时间/位置/辐射强度/云顶高度

3. CMACloud-sat API（需申请账号）：
   联系 dataserver@cma.gov.cn 获取工具包和账号

数据格式说明：
- 文件名: FY4A-_LMI---_N_REGX_1047E_L2-_LMI{S/G/F}_SING_NUL_yyyyMMddHHmmss_yyyMMddHHmmss_7800M_NXXV1.NC
  - LMIE: Event 产品（单像素事件）
  - LMIG: Group 产品（相邻事件聚类）
  - LMIF: Flash 产品（完整闪电）
- 格式: NetCDF (CF-1.7)
- 空间分辨率: 7.8 km 星下点
- 时间分辨率: 1 分钟/文件
"""
import os
import sys
import requests
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import re

# ============================================================
# NSMC 数据下载（需注册账号，手动获取 Cookie）
# ============================================================

def download_nsmc_with_cookies(cookie_str, satellite, product, date, output_dir,
                                start_hour=0, end_hour=23):
    """通过 NSMC 数据门户下载（需手动提供 Cookie）

    Args:
        cookie_str: 浏览器登录 NSMC 后获取的 Cookie 字符串
        satellite: 'FY4A'
        product: 'LMIE' (Event), 'LMIG' (Group), 'LMIF' (Flash)
        date: datetime.date, 目标日期
        output_dir: 输出目录
        start_hour: 开始小时
        end_hour: 结束小时
    """
    print("=" * 60)
    print("NSMC 数据下载说明")
    print("=" * 60)
    print()
    print("由于 NSMC 门户需要注册登录，请按以下步骤操作：")
    print()
    print("1. 注册账号：https://satellite.nsmc.org.cn/DataPortal/cn/home/index.html")
    print("2. 登录后选择：卫星=FY-4A → 仪器=LMI → 设置时间 → 检索")
    print("3. 在浏览器开发者工具中复制 Cookie 后传入本脚本")
    print()
    print("或者直接从网页手动下载，不使用本脚本。")
    print()
    print("更简单的方式：使用中科院发布的公开订正数据集 ↓")
    print("  https://doi.org/10.11888/Atmos.tpdc.303312")
    print("=" * 60)
    return []


def download_corrected_dataset(output_dir, year_range=(2019, 2023)):
    """下载中科院发布的 FY-4A LMI 订正数据集（公开下载）

    数据集来源：国家青藏高原科学数据中心
    数据涵盖 2019-2023 年每年 3-9 月，北半球观测区域
    CSV + NetCDF 格式，每日文件

    Args:
        output_dir: 输出目录
        year_range: 年份范围元组 (start, end)
    """
    base_url = "https://data.tpdc.ac.cn/data/5c27e642-3490-44b0-9a0b-1f0c0a5f5f80"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FY-4A LMI 订正数据集下载")
    print("=" * 60)
    print(f"数据来源: 国家青藏高原科学数据中心")
    print(f"DOI: 10.11888/Atmos.tpdc.303312")
    print(f"范围: {year_range[0]}-{year_range[1]} 年 3-9 月")
    print(f"输出: {output_dir}")
    print()

    # 该数据集通过 TPDE 门户下载，需要先访问页面获取文件列表
    # 这里提供手动下载指引
    print("请访问以下链接查看和下载数据：")
    print(f"  {base_url}")
    print()
    print("或者直接联系数据作者获取批量下载链接。")
    print("引用文章: Zhang et al. (2026), ESSD")
    print("  https://doi.org/10.5194/essd-18-5773-2026")
    print()

    return []


def main():
    parser = argparse.ArgumentParser(
        description='FY-4A LMI 闪电数据下载'
    )
    parser.add_argument('--source', '-s', default='nsmc',
                      choices=['nsmc', 'corrected', 'guide'],
                      help='数据源: nsmc(官方实时), corrected(订正数据集), guide(仅指引)')
    parser.add_argument('--output', '-o',
                      default=r'c:\work\meteo\data\fy4\lmi',
                      help='输出目录')
    parser.add_argument('--cookie', '-c', default='',
                      help='NSMC 登录 Cookie（仅 nsmc 源需要）')
    parser.add_argument('--product', '-p', default='LMIE',
                      choices=['LMIE', 'LMIG', 'LMIF'],
                      help='产品类型: LMIE(Event), LMIG(Group), LMIF(Flash)')
    parser.add_argument('--date', '-d', 
                      help='下载日期 (YYYY-MM-DD)，默认当天')
    parser.add_argument('--year-start', type=int, default=2019,
                      help='订正数据集年份起始（仅 corrected 源）')
    parser.add_argument('--year-end', type=int, default=2023,
                      help='订正数据集年份结束（仅 corrected 源）')
    args = parser.parse_args()

    if args.source == 'nsmc':
        download_nsmc_with_cookies(
            args.cookie, 'FY4A', args.product,
            datetime.strptime(args.date, '%Y-%m-%d').date() if args.date else datetime.now().date(),
            args.output
        )
    elif args.source == 'corrected':
        download_corrected_dataset(args.output, (args.year_start, args.year_end))
    else:
        print("=" * 60)
        print("FY-4A LMI 数据获取指引")
        print("=" * 60)
        print()
        print("方案一：NSMC 官方门户（实时数据，需注册）")
        print("  地址: https://satellite.nsmc.org.cn/DataPortal/cn/home/index.html")
        print("  步骤: 卫星=FY-4A → 仪器=LMI → 设置时间范围 → 检索 → 下载")
        print()
        print("方案二：中科院订正数据集（2019-2023，公开，推荐科研）")
        print("  地址: https://doi.org/10.11888/Atmos.tpdc.303312")
        print("  格式: CSV + NetCDF，每日文件")
        print("  包含: 订正后的闪电事件时间、经纬度、辐射强度、云顶高度")
        print()
        print("方案三：CMACloud-sat API（需申请账号 + 工具包）")
        print("  联系: dataserver@cma.gov.cn")
        print()
        print("解析脚本: scripts/data_download/parse_fy4_lmi.py")
        print("=" * 60)

if __name__ == "__main__":
    main()