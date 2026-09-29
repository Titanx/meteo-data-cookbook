"""
RainViewer API 详细测试 + NEXRAD L2 替代方案
"""
import requests, json, sys, os, ssl, urllib.request
from datetime import datetime, timezone

# ===== RainViewer API 详细测试 =====
print("="*60)
print("RainViewer API 详细测试")
print("="*60)

r = requests.get("https://api.rainviewer.com/public/weather-maps.json", timeout=30)
data = r.json()
print(f"HTTP 状态: {r.status_code}")

# 分析雷达数据
radar = data.get("radar", {})
past = radar.get("past", [])
nowcast = radar.get("nowcast", [])
print(f"历史帧: {len(past)}")
print(f"预报帧: {len(nowcast)}")

# 最新帧信息
if past:
    if isinstance(past[-1], dict):
        latest = past[-1]["time"]
    else:
        latest = past[-1]
    latest_dt = datetime.fromtimestamp(latest, tz=timezone.utc)
    print(f"最新帧时间: {latest_dt.isoformat()}")
    print(f"时间戳: {latest}")
    
    paths = radar.get("available", [])
    print(f"可用路径: {paths}")
    
    # 测试不同分辨率
    for res, label in [("256", "低分辨率"), ("512", "中分辨率")]:
        for z in range(3, 10):
            url = f"https://tilecache.rainviewer.com/v2/radar/{latest}/{res}/{z}/0/0.png"
            tr = requests.get(url, timeout=30)
            if tr.status_code == 200:
                print(f"  {label} z={z}: ✓ {len(tr.content)/1024:.1f} KB")
                break
        else:
            print(f"  {label}: 无法获取瓦片")

# 最近时间跨度
print(f"\n最近 24 小时帧数: {len(past)}")
if len(past) >= 2:
    if isinstance(past[-1], dict):
        t_range = past[-1]["time"] - past[0]["time"]
    else:
        t_range = past[-1] - past[0]
    print(f"时间跨度: {t_range} 秒 ({t_range/3600:.1f} 小时)")
    frame_interval = t_range / (len(past) - 1)
    print(f"平均间隔: {frame_interval:.0f} 秒")

# 德州区域瓦片测试
print(f"\n德州区域瓦片测试:")
center_x, center_y = 128, 128
for dx in [-1, 0, 1]:
    for dy in [-1, 0, 1]:
        url = f"https://tilecache.rainviewer.com/v2/radar/{latest}/256/8/{center_x+dx}/{center_y+dy}.png"
        tr = requests.get(url, timeout=30)
        s = "✓" if tr.status_code == 200 else "✗"
        if tr.status_code == 200:
            print(f"  tile 8/{center_x+dx}/{center_y+dy}: {s} ({len(tr.content)/1024:.1f} KB)")

# ===== NEXRAD L2 替代方案测试 =====
print(f"\n{'='*60}")
print("NEXRAD L2 替代方案测试")
print("="*60)

import s3fs

# 测试 noaa-nexrad-level2 的 Requester Pays
for bucket in ["noaa-nexrad-level2"]:
    for rp in [True, False]:
        try:
            fs = s3fs.S3FileSystem(anon=True, requester_pays=rp)
            items = fs.ls(f"{bucket}/")
            print(f"  {bucket} (requester_pays={rp}): ✓ {len(items)} 个目录")
        except Exception as e:
            print(f"  {bucket} (requester_pays={rp}): ✗ {str(e)[:60]}")

# NEXRAD L3 桶名测试
for bucket_name in ["noaa-nexrad-level3", "nexrad-level3", "noaa-nexrad-l3"]:
    try:
        fs = s3fs.S3FileSystem(anon=True)
        items = fs.ls(f"{bucket_name}/")
        print(f"  {bucket_name}: ✓ {len(items)} 个目录")
    except Exception as e:
        print(f"  {bucket_name}: ✗ {str(e)[:60]}")

# ===== 汇总已有数据（unidata chunks）的详细信息 =====
print(f"\n{'='*60}")
print("unidata chunks 德州站数据完整度测试")
print("="*60)

fs = s3fs.S3FileSystem(anon=True, client_kwargs={"region_name": "us-east-1"})
texas_sids = ["KFWS", "KHGX", "KEWX", "KGRK", "KMAF", "KLBB", "KDYX",
              "KDFX", "KCRP", "KBRO", "KSHV", "KLCH", "KFDR", "KTLX",
              "KAMA", "KEPZ", "KINX", "KSRX"]

print(f"{'站号':<8} {'站名':<35} {'分块数':<8} {'大小MB':<8} {'体扫ID':<20}")
print("-"*79)
for sid in texas_sids:
    try:
        sid_path = f"unidata-nexrad-level2-chunks/{sid}"
        vols = sorted(fs.ls(sid_path), reverse=True)
        if vols:
            latest_vol = vols[0]
            chunks = sorted(fs.ls(latest_vol))
            total_bytes = sum(fs.info(c).get("size", 0) for c in chunks)
            total_mb = round(total_bytes / (1024*1024), 2)
            vol_id = latest_vol.split("/")[-1][:18]
            print(f"  {sid:<8} {'✓':<35} {len(chunks):<8} {total_mb:<8} {vol_id:<20}")
    except Exception as e:
        print(f"  {sid:<8} {'✗':<35} {'-':<8} {'-':<8} {str(e)[:20]}")

# ===== 总结 =====
print(f"\n{'='*60}")
print("最终结论")
print("="*60)
print("""
匿名可获取的气象雷达数据源（ERCOT/德州区域）：

[1] NEXRAD L2 实时分块流 (unidata-nexrad-level2-chunks)
    - 访问方式: AWS S3 匿名 (fsspec/s3fs)
    - 覆盖: 18 个德州及周边 NEXRAD 雷达站
    - 数据: 体扫分块 (反射率+径向速度+谱宽+双偏振)
    - 延迟: 秒级
    - 单个体扫: 2-14 MB
    - 限制: 仅保留最近约 10 个体扫, 无历史归档

[2] RainViewer API
    - 访问方式: HTTP GET, 免费无 key
    - 覆盖: 全球 1200+ 雷达拼图, 含德州
    - 数据: 256/512 分辨率 PNG 瓦片
    - 延迟: 5 分钟
    - 限制: PNG 瓦片, 非原始反射率, 仅用于可视化

[3] noaa-nexrad-level2 (完整体扫)
    - 当前状态: ✗ Access Denied (需 AWS 凭证)
    - 可尝试: 安装 awscli 并配置凭证后访问
    - 历史数据从 1991 年至今

[4] noaa-nexrad-level3 (产品数据)
    - 当前状态: ✗ 桶不存在

建议: 优先使用 unidata chunks 实时流 + 安装 xradar 解析
""")