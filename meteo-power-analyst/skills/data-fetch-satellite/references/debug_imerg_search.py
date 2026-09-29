"""
IMERG 下载测试 - 先登录后下载
"""
import earthaccess
from datetime import datetime, timezone, timedelta
import time
from pathlib import Path

# 凭证存储在 ~/_netrc
auth = earthaccess.login(strategy='netrc')
print(f"登录状态: {auth.authenticated}")

OUT = Path("./imerg_test")
OUT.mkdir(exist_ok=True)

# 1. 搜索 30 分钟产品
print("\n=== 1. 搜索 GPM_3IMERGHH (2024-07-15, ERCOT) ===")
results = earthaccess.search_data(
    short_name="GPM_3IMERGHH",
    bounding_box=(-106.5, 25.5, -93.0, 36.5),
    temporal=(datetime(2024, 7, 15, tzinfo=timezone.utc),
              datetime(2024, 7, 16, tzinfo=timezone.utc)),
    count=10,
)
print(f"找到 {len(results)} 个文件")
for r in results[:3]:
    links = r.data_links()
    print(f"  - {links[0][:100] if links else '无链接'}")
    print(f"    大小: {r.size:.1f} MB" if r.size > 0 else "    大小: 未知")

# 2. 下载第一个 30 分钟文件
if results:
    print("\n=== 2. 下载 30 分钟文件 ===")
    target = results[0]
    t0 = time.time()
    files = earthaccess.download(target, str(OUT))
    elapsed = time.time() - t0
    if files:
        f = Path(files[0])
        print(f"✅ 下载成功: {f.name}")
        print(f"大小: {f.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"速度: {f.stat().st_size / 1024 / 1024 / elapsed:.1f} MB/s" if elapsed > 0 else "速度: < 1s")
    else:
        print("❌ 下载失败 (返回空列表)")

# 3. 搜索并下载日产品
print("\n=== 3. 搜索 GPM_3IMERGDF (2024-07-15) ===")
results2 = earthaccess.search_data(
    short_name="GPM_3IMERGDF",
    bounding_box=(-106.5, 25.5, -93.0, 36.5),
    temporal=(datetime(2024, 7, 15, tzinfo=timezone.utc),
              datetime(2024, 7, 16, tzinfo=timezone.utc)),
    count=5,
)
print(f"找到 {len(results2)} 个文件")
for r in results2[:2]:
    links = r.data_links()
    print(f"  - {links[0][:100] if links else '无链接'}")
    print(f"    大小: {r.size:.1f} MB" if r.size > 0 else "    大小: 未知")

if results2:
    print("\n=== 4. 下载日产品 ===")
    target = results2[0]
    t0 = time.time()
    files = earthaccess.download(target, str(OUT))
    elapsed = time.time() - t0
    if files:
        f = Path(files[0])
        print(f"✅ 下载成功: {f.name}")
        print(f"大小: {f.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"速度: {f.stat().st_size / 1024 / 1024 / elapsed:.1f} MB/s" if elapsed > 0 else "速度: < 1s")
    else:
        print("❌ 下载失败")

# 4. 读取 HDF5 验证
print("\n=== 5. 读取 HDF5 验证 ===")
try:
    import h5py
    import numpy as np
    for f in sorted(OUT.glob("*.HDF5")):
        print(f"\n读取: {f.name}")
        with h5py.File(str(f), 'r') as hf:
            # 打印顶层结构
            def show(name, obj):
                if isinstance(obj, h5py.Dataset):
                    print(f"  📊 {name}: shape={obj.shape}, dtype={obj.dtype}")
            hf.visititems(show)
            
            # 查找降水数据
            for key in ['precipitation', 'precipitationCal', 'HQprecipitation', 'precipitationQualityIndex']:
                if key in hf:
                    ds = hf[key]
                    data = ds[:]
                    valid = data[~np.isnan(data)] if data.dtype.kind == 'f' else data[data != -9999.0]
                    print(f"\n  🌧️ {key}: shape={data.shape}")
                    print(f"     有效值: {valid.size}")
                    print(f"     min={np.nanmin(data):.3f}, max={np.nanmax(data):.3f}, mean={np.nanmean(data):.3f}")
            
            # 经纬度
            for k in ['lon', 'lat', 'longitude', 'latitude']:
                if k in hf:
                    d = hf[k][:]
                    print(f"  🌐 {k}: {d.min():.2f} ~ {d.max():.2f}, shape={d.shape}")
                    
except ImportError as e:
    print(f"⚠️ 需要安装 h5py: {e}")

# 5. 下载文件清单
print(f"\n=== 下载目录文件 ===")
for f in sorted(OUT.glob("*")):
    if f.is_file() and f.suffix != '.json':
        print(f"  {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")