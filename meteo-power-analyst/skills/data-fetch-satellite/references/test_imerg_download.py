"""
IMERG 降水数据下载测试脚本
日期：2026-09-07
测试内容：
1. earthaccess CMIP 搜索（数据集发现）
2. 30 分钟产品（GPM_3IMERGHH）文件列表和下载
3. 日产品（GPM_3IMERGDF）下载
4. 德州/ERCOT 区域子集化下载
5. HDF5 数据读取和验证
6. 数据量/速度评估
"""

import json, os, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# 配置
# ============================================================
# 凭证存储在 ~/_netrc，无需硬编码
import earthaccess
earthaccess.login(strategy='netrc')

OUTPUT_DIR = Path(__file__).parent / "imerg_test"
OUTPUT_DIR.mkdir(exist_ok=True)

# ERCOT 区域边界（德州 + 周边）
ERCOT_BBOX = (-106.5, 25.5, -93.0, 36.5)  # (west, south, east, north)

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    sys.stdout.flush()


# ============================================================
# 1. 数据集搜索与发现
# ============================================================
def test_discover_datasets():
    section("1. 数据集搜索与发现")
    import earthaccess

    # 搜索 IMERG 相关数据集
    keywords = ["GPM_3IMERGHH", "GPM_3IMERGDF", "GPM_3IMERGM"]
    found = {}

    for kw in keywords:
        results = earthaccess.search_datasets(short_name=kw, count=1)
        if results:
            for r in results:
                try:
                    summ = r.summary()
                    if isinstance(summ, dict):
                        title = summ.get('title', str(r)[:80])
                    else:
                        title = str(r)[:80]
                    print(f"  ✅ {kw}: {title}")
                    found[kw] = r
                except Exception as e:
                    print(f"  ✅ {kw}: {str(r)[:80]}")
                    found[kw] = r
        else:
            results = earthaccess.search_datasets(keyword=kw, count=1)
            if results:
                print(f"  ✅ {kw}: {str(results[0])[:80]}")
                found[kw] = results[0]
            else:
                print(f"  ❌ {kw}: 未找到")

    return found


# ============================================================
# 2. 30 分钟产品文件列表
# ============================================================
def test_search_granules(days_back=3):
    """搜索最近几天的 IMERG 30 分钟数据"""
    section(f"2. 搜索 IMERG 30 分钟数据（最近 {days_back} 天）")
    import earthaccess

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)

    results = earthaccess.search_data(
        short_name="GPM_3IMERGHH",
        bounding_box=ERCOT_BBOX,
        temporal=(start, end),
        count=20,
    )

    print(f"  搜索时间范围: {start.isoformat()} ~ {end.isoformat()}")
    print(f"  找到 {len(results)} 个文件")

    if results:
        # 显示前 5 个文件信息
        for i, r in enumerate(results[:5]):
            print(f"  [{i+1}] {r.data_links()[0][:100]}...")
            print(f"      大小: {r.size():.1f} MB" if r.size() > 0 else "      大小: 未知")

        # 按日期分组统计
        print(f"\n  文件时间分布:")
        for r in results:
            t = r.temporal()
            if t:
                print(f"  - {t[0].strftime('%Y-%m-%d %H:%M')} UTC")

    return results


# ============================================================
# 3. 下载日聚合产品
# ============================================================
def test_download_daily():
    """下载最近 1 天的 IMERG 日产品"""
    section("3. 下载 IMERG 日产品 (GPM_3IMERGDF)")
    import earthaccess

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    # 搜索日产品
    results = earthaccess.search_data(
        short_name="GPM_3IMERGDF",
        bounding_box=ERCOT_BBOX,
        temporal=(start, end),
        count=5,
    )

    print(f"  搜索时间: {start.isoformat()} ~ {end.isoformat()}")
    print(f"  找到 {len(results)} 个文件")

    if results:
        # 下载第一个文件
        target = results[0]
        print(f"  下载文件: {target.data_links()[0][:100]}...")
        print(f"  文件大小: {target.size():.1f} MB")

        t0 = time.time()
        files = earthaccess.download(target, str(OUTPUT_DIR))
        elapsed = time.time() - t0

        if files:
            local_path = Path(files[0])
            print(f"  ✅ 下载完成: {local_path.name}")
            print(f"     大小: {local_path.stat().st_size / 1024 / 1024:.2f} MB")
            print(f"     耗时: {elapsed:.1f} 秒")
            print(f"     速度: {local_path.stat().st_size / 1024 / 1024 / elapsed:.1f} MB/s")
            return local_path
        else:
            print(f"  ❌ 下载失败")
    else:
        print(f"  ⚠️ 未找到文件，尝试更早的日期...")
        # 尝试更早的日期
        for days_ago in [3, 7, 14, 30]:
            start = (datetime.now(timezone.utc) - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            results = earthaccess.search_data(
                short_name="GPM_3IMERGDF",
                bounding_box=ERCOT_BBOX,
                temporal=(start, end),
                count=5,
            )
            if results:
                print(f"  在 {days_ago} 天前找到 {len(results)} 个文件")
                target = results[0]
                t0 = time.time()
                files = earthaccess.download(target, str(OUTPUT_DIR))
                elapsed = time.time() - t0
                if files:
                    local_path = Path(files[0])
                    print(f"  ✅ 下载完成: {local_path.name}")
                    print(f"     大小: {local_path.stat().st_size / 1024 / 1024:.2f} MB")
                    print(f"     耗时: {elapsed:.1f} 秒")
                    return local_path
                break
            else:
                print(f"  {days_ago} 天前仍无数据")

    return None


# ============================================================
# 4. HDF5 数据读取与验证
# ============================================================
def test_read_hdf5(file_path: Path):
    """读取 HDF5 文件，检查数据内容"""
    section("4. HDF5 数据读取与验证")

    if not file_path or not file_path.exists():
        print("  ❌ 文件不存在，跳过")
        return

    try:
        import h5py
        with h5py.File(str(file_path), 'r') as f:
            print(f"  ✅ 文件打开成功")
            print(f"  文件结构:")

            def print_group(name, obj):
                if isinstance(obj, h5py.Dataset):
                    if hasattr(obj, 'shape') and len(obj.shape) > 0:
                        print(f"  📊 {name}: shape={obj.shape}, dtype={obj.dtype}")
                        # 读取少量数据验证
                        if obj.shape[0] > 0:
                            data = obj[0:min(5, obj.shape[0])]
                            print(f"     前5个值: {data}")
                else:
                    print(f"  📁 {name}/")

            f.visititems(print_group)

            # 检查经纬度
            if 'lon' in f:
                lon = f['lon'][:]
                print(f"\n  🌐 经度范围: {lon.min():.2f} ~ {lon.max():.2f}")
            if 'lat' in f:
                lat = f['lat'][:]
                print(f"  🌐 纬度范围: {lat.min():.2f} ~ {lat.max():.2f}")

            # 检查降水数据
            for key in ['precipitation', 'precipitationCal', 'HQprecipitation', 'precipitationQualityIndex']:
                if key in f:
                    ds = f[key]
                    data = ds[:]
                    print(f"\n  🌧️ {key}:")
                    print(f"     shape: {data.shape}")
                    print(f"     有效值: {data[~np.isnan(data) if data.dtype.kind == 'f' else (data != -9999.0)].size}")
                    print(f"     统计: min={np.nanmin(data):.2f}, max={np.nanmax(data):.2f}, mean={np.nanmean(data):.2f}")

    except ImportError as e:
        print(f"  ❌ 缺少依赖库: {e}")
        print(f"  请安装: pip install h5py numpy")
    except Exception as e:
        print(f"  ❌ 读取失败: {type(e).__name__}: {e}")


# ============================================================
# 5. 30 分钟产品完整下载测试
# ============================================================
def test_download_30min():
    """下载最近 2 个 30 分钟文件"""
    section("5. IMERG 30 分钟产品下载测试")
    import earthaccess

    # 搜索最近 2 天的半小时数据
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=2)

    results = earthaccess.search_data(
        short_name="GPM_3IMERGHH",
        bounding_box=ERCOT_BBOX,
        temporal=(start, end),
        count=5,
    )

    print(f"  搜索范围: {start.isoformat()} ~ {end.isoformat()}")
    print(f"  找到 {len(results)} 个文件")

    if results:
        # 下载最近的 2 个文件
        for i, r in enumerate(results[:2]):
            print(f"\n  [{i+1}] 下载文件...")
            t0 = time.time()
            files = earthaccess.download(r, str(OUTPUT_DIR))
            elapsed = time.time() - t0
            if files:
                local_path = Path(files[0])
                print(f"     ✅ {local_path.name}")
                print(f"     大小: {local_path.stat().st_size / 1024 / 1024:.2f} MB")
                print(f"     耗时: {elapsed:.1f} 秒")
            else:
                print(f"     ❌ 下载失败")
    else:
        print(f"  ⚠️ 最近 2 天无数据，可能是 Late/Final 延迟")


# ============================================================
# 6. 数据量估算
# ============================================================
def test_data_volume():
    """估算 ERCOT 区域 IMERG 数据量"""
    section("6. ERCOT 区域数据量估算")

    sample_file = None
    for f in OUTPUT_DIR.glob("*.HDF5"):
        sample_file = f
        break
    if not sample_file:
        for f in OUTPUT_DIR.glob("*.nc4"):
            sample_file = f
            break
    if not sample_file:
        for f in OUTPUT_DIR.glob("*"):
            if f.is_file() and f.suffix in ['.HDF5', '.nc', '.nc4', '.h5']:
                sample_file = f
                break

    if sample_file:
        size_mb = sample_file.stat().st_size / 1024 / 1024
        print(f"  样本文件: {sample_file.name}")
        print(f"  单文件大小: {size_mb:.2f} MB")

        # 估算
        daily_mb = size_mb * 48  # 30-min * 48
        monthly_gb = daily_mb * 30 / 1024
        yearly_gb = daily_mb * 365 / 1024

        print(f"\n  ERCOT 区域数据量估算:")
        print(f"  每日 (30min×48): {daily_mb:.1f} MB")
        print(f"  每月: {monthly_gb:.1f} GB")
        print(f"  每年: {yearly_gb:.1f} GB")
    else:
        print(f"  ⚠️ 未找到已下载的样本文件，无法估算")


# ============================================================
# 主函数
# ============================================================
def main():
    import numpy as np
    import earthaccess

    # 注册全局 np 别名（用于 h5py 读取）
    globals()['np'] = np

    print(f"IMERG 降水数据下载测试 - {datetime.now(timezone.utc).isoformat()}")
    print(f"ERCOT 区域: {ERCOT_BBOX}")
    print(f"输出目录: {OUTPUT_DIR}")

    all_results = {}
    all_results["test_time"] = datetime.now(timezone.utc).isoformat()

    # 测试 1: 数据集发现
    all_results["datasets"] = test_discover_datasets()

    # 测试 2: 搜索 granules
    all_results["granules"] = test_search_granules(days_back=5)

    # 测试 3: 下载日产品
    all_results["daily_file"] = test_download_daily()

    # 测试 4: 读取 HDF5
    daily_path = all_results["daily_file"]
    if daily_path:
        test_read_hdf5(daily_path)

    # 测试 5: 下载 30 分钟产品
    all_results["half_hourly"] = test_download_30min()

    # 测试 6: 数据量估算
    test_data_volume()

    # 汇总结果
    section("===== 测试汇总 =====")
    tests = [
        ("数据集搜索", all_results.get("datasets")),
        ("Granule搜索", all_results.get("granules")),
        ("日产品下载", all_results.get("daily_file")),
        ("30分钟下载", all_results.get("half_hourly")),
    ]
    for name, result in tests:
        status = "✅" if result else "❌"
        if isinstance(result, list):
            status = "✅" if len(result) > 0 else "❌"
        print(f"  {status} {name}")

    # 列出下载的文件
    print(f"\n  下载目录中的文件:")
    for f in sorted(OUTPUT_DIR.glob("*")):
        if f.is_file():
            print(f"  - {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")

    # 保存结果
    result_path = OUTPUT_DIR / "imerg_test_results.json"
    with open(result_path, "w") as f:
        json.dump({
            "test_time": all_results["test_time"],
            "ercot_bbox": ERCOT_BBOX,
            "daily_file": str(all_results.get("daily_file", "")),
            "downloaded_files": [str(f) for f in OUTPUT_DIR.glob("*") if f.is_file() and f.name != "imerg_test_results.json"],
        }, f, indent=2, default=str)
    print(f"\n  结果保存: {result_path}")


if __name__ == "__main__":
    main()