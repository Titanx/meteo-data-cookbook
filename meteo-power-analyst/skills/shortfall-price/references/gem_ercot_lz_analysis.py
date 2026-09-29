"""GEM 电站 × ERCOT LZ 区域电价联动分析

分析逻辑:
1. 加载 GEM 运行中光伏/风电电站 (ERCOT 区域)
2. 按坐标聚类到 ERCOT 4 个 Load Zone (LZ_NORTH, LZ_SOUTH, LZ_HOUSTON, LZ_WEST)
3. 统计各 LZ 区域装机结构 (风电/光伏容量及占比)
4. 加载 ERCOT RTM 电价数据, 对比各 LZ 区域电价特征
5. 分析装机结构与电价波动性的关联

ERCOT LZ 地理划分 (大致):
- LZ_NORTH: 达拉斯-沃斯堡以北, 含 Panhandle 风电带
- LZ_SOUTH: 圣安东尼奥以南, 含南德州沿海风电
- LZ_HOUSTON: 休斯顿及周边
- LZ_WEST: 西德州, 含大量风电和光伏
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import pandas as pd
import numpy as np
from pathlib import Path
from glob import glob
import warnings
warnings.filterwarnings('ignore')

# ── 路径 ──
GEM_DIR = Path(r"c:\work\meteo\data\gem")
ERCOT_DIR = Path(r"c:\work\meteo\data\ercot")
OUTPUT_DIR = Path(r"c:\work\meteo\output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ERCOT LZ 区域边界 (大致划分, 基于ERCOT公开地图)
# LZ_WEST: 西经100度以西 (大量风电光伏)
# LZ_NORTH: 北纬32度以上, 西经100度以东 (达拉斯+Panhandle)
# LZ_HOUSTON: 北纬31度以南, 西经97度以东 (休斯顿)
# LZ_SOUTH: 其余南部区域
def assign_lz(lat, lon):
    """根据坐标分配 ERCOT Load Zone"""
    if pd.isna(lat) or pd.isna(lon):
        return 'UNKNOWN'
    # LZ_WEST: 西德州, lon <= -100
    if lon <= -100:
        return 'LZ_WEST'
    # LZ_NORTH: 北德州, lat >= 32
    if lat >= 32:
        return 'LZ_NORTH'
    # LZ_HOUSTON: 东德州沿海, lon >= -97.5 and lat <= 31
    if lon >= -97.5 and lat <= 31:
        return 'LZ_HOUSTON'
    # LZ_SOUTH: 南德州其余区域
    if lat < 32:
        return 'LZ_SOUTH'
    return 'LZ_NORTH'


print("=" * 70)
print("1. 加载 GEM 运行中电站数据")
print("=" * 70)

# 加载 GEM 光伏和风电 (仅 ERCOT 区域 + operating)
solar = pd.read_csv(GEM_DIR / "gem_solar_2026-08.csv", low_memory=False)
wind = pd.read_csv(GEM_DIR / "gem_wind_2026-08.csv", low_memory=False)

# 筛选美国 + ERCOT 区域 + operating
ERCOT_BOUNDS = {'lat_min': 25, 'lat_max': 34, 'lon_min': -108, 'lon_max': -93}
solar_us = solar[(solar['country-area1'] == 'United States') &
                  (solar['Latitude'] >= ERCOT_BOUNDS['lat_min']) &
                  (solar['Latitude'] <= ERCOT_BOUNDS['lat_max']) &
                  (solar['Longitude'] >= ERCOT_BOUNDS['lon_min']) &
                  (solar['Longitude'] <= ERCOT_BOUNDS['lon_max'])].copy()
wind_us = wind[(wind['country-area1'] == 'United States') &
               (wind['Latitude'] >= ERCOT_BOUNDS['lat_min']) &
               (wind['Latitude'] <= ERCOT_BOUNDS['lat_max']) &
               (wind['Longitude'] >= ERCOT_BOUNDS['lon_min']) &
               (wind['Longitude'] <= ERCOT_BOUNDS['lon_max'])].copy()

# 仅 operating
solar_op = solar_us[solar_us['status'] == 'operating'].copy()
wind_op = wind_us[wind_us['status'] == 'operating'].copy()
solar_op['type'] = 'Solar'
wind_op['type'] = 'Wind'

print(f"ERCOT 运行中光伏: {len(solar_op)} 座, {solar_op['capacity'].sum():.0f} MW")
print(f"ERCOT 运行中风电: {len(wind_op)} 座, {wind_op['capacity'].sum():.0f} MW")

# 分配 LZ
solar_op['lz'] = solar_op.apply(lambda r: assign_lz(r['Latitude'], r['Longitude']), axis=1)
wind_op['lz'] = wind_op.apply(lambda r: assign_lz(r['Latitude'], r['Longitude']), axis=1)

# 合并
plants = pd.concat([solar_op[['name', 'capacity', 'type', 'lz', 'Latitude', 'Longitude', 'owner', 'start-year']],
                    wind_op[['name', 'capacity', 'type', 'lz', 'Latitude', 'Longitude', 'owner', 'start-year']]],
                   ignore_index=True)

print(f"\n各 LZ 区域装机结构 (运行中):")
print(f"{'LZ':<12} {'风电(MW)':>10} {'风电数':>6} {'光伏(MW)':>10} {'光伏数':>6} {'总计(MW)':>10} {'风电占比':>8} {'光伏占比':>8}")
print("-" * 80)
for lz in ['LZ_WEST', 'LZ_NORTH', 'LZ_SOUTH', 'LZ_HOUSTON']:
    sub = plants[plants['lz'] == lz]
    w_cap = sub[sub['type'] == 'Wind']['capacity'].sum()
    s_cap = sub[sub['type'] == 'Solar']['capacity'].sum()
    w_n = len(sub[sub['type'] == 'Wind'])
    s_n = len(sub[sub['type'] == 'Solar'])
    total = w_cap + s_cap
    w_pct = w_cap / total * 100 if total > 0 else 0
    s_pct = s_cap / total * 100 if total > 0 else 0
    print(f"{lz:<12} {w_cap:>10.0f} {w_n:>6} {s_cap:>10.0f} {s_n:>6} {total:>10.0f} {w_pct:>7.1f}% {s_pct:>7.1f}%")

# Top 电站
print(f"\n各 LZ 区域最大电站:")
for lz in ['LZ_WEST', 'LZ_NORTH', 'LZ_SOUTH', 'LZ_HOUSTON']:
    sub = plants[plants['lz'] == lz]
    if len(sub) > 0:
        top5 = sub.nlargest(5, 'capacity')[['name', 'type', 'capacity', 'Latitude', 'Longitude']]
        print(f"\n  {lz}:")
        for _, r in top5.iterrows():
            print(f"    {r['type']:5s} {r['capacity']:6.0f} MW  {r['name']}  ({r['Latitude']:.2f}, {r['Longitude']:.2f})")


print(f"\n{'=' * 70}")
print("2. 加载 ERCOT RTM 电价数据")
print("=" * 70)

# 加载 4 个 LZ 的 RTM 电价 (合并增量)
lz_list = ['LZ_WEST', 'LZ_NORTH', 'LZ_SOUTH', 'LZ_HOUSTON']
hb_list = ['HB_WEST', 'HB_NORTH', 'HB_SOUTH', 'HB_HOUSTON']

prices = {}
for sp in lz_list:
    files = sorted(glob(str(ERCOT_DIR / f"ercot_rtm_{sp}_*.csv")))
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    # GridStatus format: interval_start_utc, interval_end_utc, location, location_type, market, spp
    df['datetime'] = pd.to_datetime(df['interval_start_utc']).dt.tz_localize(None)
    df['price'] = df['spp']
    prices[sp] = df
    print(f"  {sp}: {len(df):,} rows, {df['datetime'].min()} ~ {df['datetime'].max()}")

# 各 LZ 电价统计
print(f"\n各 LZ 区域 RTM 电价统计:")
print(f"{'LZ':<12} {'均值':>10} {'中位':>10} {'std':>10} {'min':>8} {'max':>10} {'p95':>10} {'>100$/占比':>10}")
print("-" * 85)
lz_stats = {}
for sp in lz_list:
    df = prices[sp]
    p = df['price']
    p = p[p >= 0]  # 排除负值
    mean_p = p.mean()
    med_p = p.median()
    std_p = p.std()
    min_p = p.min()
    max_p = p.max()
    p95 = p.quantile(0.95)
    spike_pct = (p > 100).sum() / len(p) * 100
    lz_stats[sp] = {'mean': mean_p, 'median': med_p, 'std': std_p,
                    'min': min_p, 'max': max_p, 'p95': p95, 'spike_pct': spike_pct}
    print(f"{sp:<12} {mean_p:>10.1f} {med_p:>10.1f} {std_p:>10.1f} {min_p:>8.1f} {max_p:>10.1f} {p95:>10.1f} {spike_pct:>9.1f}%")

# 小时模式 (各 LZ 区域的日内电价曲线)
print(f"\n各 LZ 区域日内电价模式 (小时均值):")
hourly = {}
for sp in lz_list:
    df = prices[sp].copy()
    df['hour'] = df['datetime'].dt.hour
    if 'price' in df.columns:
        col = 'price'
    else:
        col = df.columns[-1]
    df[col] = df[col].clip(lower=0)
    h_mean = df.groupby('hour')[col].mean()
    hourly[sp] = h_mean

print(f"{'Hour':<6}", end="")
for sp in lz_list:
    print(f" {sp:>12}", end="")
print()
for h in range(24):
    print(f"{h:<6}", end="")
    for sp in lz_list:
        v = hourly[sp].get(h, 0)
        print(f" {v:>12.1f}", end="")
    print()

# 装机 vs 电价波动性关联
print(f"\n{'=' * 70}")
print("3. 装机结构与电价波动性关联")
print("=" * 70)

print(f"\n{'LZ':<12} {'风电(MW)':>10} {'光伏(MW)':>10} {'风光总':>10} {'电价std':>10} {'电价均值':>10} {'峰值/均值':>10}")
print("-" * 75)
for lz in lz_list:
    sub = plants[plants['lz'] == lz]
    w_cap = sub[sub['type'] == 'Wind']['capacity'].sum()
    s_cap = sub[sub['type'] == 'Solar']['capacity'].sum()
    total_re = w_cap + s_cap
    s = lz_stats[lz]
    peak_ratio = s['max'] / s['mean'] if s['mean'] > 0 else 0
    print(f"{lz:<12} {w_cap:>10.0f} {s_cap:>10.0f} {total_re:>10.0f} {s['std']:>10.1f} {s['mean']:>10.1f} {peak_ratio:>10.1f}")

# 按月统计电价 (看季节性)
print(f"\n各 LZ 区域月度电价 (2025-07 ~ 2026-09):")
for sp in lz_list:
    df = prices[sp].copy()
    df['month'] = df['datetime'].dt.to_period('M')
    if 'price' in df.columns:
        col = 'price'
    else:
        col = df.columns[-1]
    df[col] = df[col].clip(lower=0)
    m_stats = df.groupby('month')[col].agg(['mean', 'std', 'max'])
    print(f"\n  {sp}:")
    print(f"    {'Month':<10} {'Mean':>8} {'Std':>8} {'Max':>8}")
    for idx, row in m_stats.iterrows():
        print(f"    {str(idx):<10} {row['mean']:>8.1f} {row['std']:>8.1f} {row['max']:>8.1f}")

# 保存电站-LZ映射
plants.to_csv(OUTPUT_DIR / "ercot_plants_lz_mapping.csv", index=False)
print(f"\n已保存电站-LZ映射: {OUTPUT_DIR}/ercot_plants_lz_mapping.csv")

print(f"\n{'=' * 70}")
print("完成!")
print("=" * 70)
