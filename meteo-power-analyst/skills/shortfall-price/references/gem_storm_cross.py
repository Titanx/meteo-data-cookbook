"""GEM 电站 × 雷暴机场坐标交叉分析"""
import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, sin, cos, asin, sqrt
import sys
sys.stdout.reconfigure(line_buffering=True)

GEM_DIR = Path(r"c:\work\meteo\data\gem")
OUTPUT_DIR = Path(r"c:\work\meteo\output")

# 机场坐标
AIRPORT_COORDS = {
    'KDFW': (32.90, -97.04, 'Dallas-Fort Worth'),
    'KIAH': (29.99, -95.34, 'Houston Intercontinental'),
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

# 加载数据
storms = pd.read_csv(OUTPUT_DIR / "thunderstorm_ercot_events.csv")
print(f"雷暴事件: {len(storms)} 次")
print(f"机场分布: {storms['icao'].value_counts().to_dict()}")

# 加载 GEM 电站
solar = pd.read_csv(GEM_DIR / "gem_solar_2026-08.csv", low_memory=False)
wind = pd.read_csv(GEM_DIR / "gem_wind_2026-08.csv", low_memory=False)
ERCOT_BOUNDS = {'lat_min': 25, 'lat_max': 34, 'lon_min': -108, 'lon_max': -93}
solar_op = solar[(solar['country-area1'] == 'United States') &
                  (solar['status'] == 'operating') &
                  (solar['Latitude'] >= ERCOT_BOUNDS['lat_min']) &
                  (solar['Latitude'] <= ERCOT_BOUNDS['lat_max']) &
                  (solar['Longitude'] >= ERCOT_BOUNDS['lon_min']) &
                  (solar['Longitude'] <= ERCOT_BOUNDS['lon_max'])].copy()
wind_op = wind[(wind['country-area1'] == 'United States') &
                (wind['status'] == 'operating') &
                (wind['Latitude'] >= ERCOT_BOUNDS['lat_min']) &
                (wind['Latitude'] <= ERCOT_BOUNDS['lat_max']) &
                (wind['Longitude'] >= ERCOT_BOUNDS['lon_min']) &
                (wind['Longitude'] <= ERCOT_BOUNDS['lon_max'])].copy()
plants = pd.concat([
    solar_op[['name', 'capacity', 'Latitude', 'Longitude']].assign(type='Solar'),
    wind_op[['name', 'capacity', 'Latitude', 'Longitude']].assign(type='Wind')
], ignore_index=True)
print(f"ERCOT 运行中电站: {len(solar_op)} 光伏 + {len(wind_op)} 风电 = {len(plants)} 座")

# 添加机场坐标
storms['lat'] = storms['icao'].map(lambda x: AIRPORT_COORDS.get(x, (None, None, ''))[0])
storms['lon'] = storms['icao'].map(lambda x: AIRPORT_COORDS.get(x, (None, None, ''))[1])
storms['airport_name'] = storms['icao'].map(lambda x: AIRPORT_COORDS.get(x, (None, None, ''))[2])
storms_valid = storms.dropna(subset=['lat', 'lon']).copy()
print(f"有坐标的雷暴事件: {len(storms_valid)}")

# 对每个雷暴事件, 找100km内的电站
results = []
for _, storm in storms_valid.iterrows():
    slat, slon = storm['lat'], storm['lon']
    nearby = []
    for _, plant in plants.iterrows():
        d = haversine(slat, slon, plant['Latitude'], plant['Longitude'])
        if d <= 150:  # 扩大到150km
            nearby.append({
                'name': plant['name'],
                'capacity': plant['capacity'],
                'type': plant['type'],
                'lat': plant['Latitude'],
                'lon': plant['Longitude'],
                'dist_km': d
            })

    wind_affected = [p for p in nearby if p['type'] == 'Wind']
    solar_affected = [p for p in nearby if p['type'] == 'Solar']

    # 最大电价飙升比 (取4个LZ的最大值)
    spike_cols = [c for c in storms.columns if 'spike_ratio' in c and 'LZ' in c]
    max_spike = 1.0
    for col in spike_cols:
        if pd.notna(storm.get(col, 1.0)):
            max_spike = max(max_spike, storm[col])

    results.append({
        'time': storm['time'],
        'icao': storm['icao'],
        'airport': storm['airport_name'],
        'lat': slat, 'lon': slon,
        'wspd': storm['wspd'],
        'prcp': storm['prcp'],
        'n_plants_150km': len(nearby),
        'affected_cap_mw': sum(p['capacity'] for p in nearby),
        'n_wind': len(wind_affected),
        'wind_cap_mw': sum(p['capacity'] for p in wind_affected),
        'n_solar': len(solar_affected),
        'solar_cap_mw': sum(p['capacity'] for p in solar_affected),
        'nearest_plant': min(nearby, key=lambda x: x['dist_km'])['name'] if nearby else '',
        'nearest_dist_km': min(p['dist_km'] for p in nearby) if nearby else 999,
        'max_lz_spike': max_spike,
        'HB_WEST_spike': storm.get('HB_WEST_spike_ratio', 1.0),
        'LZ_WEST_spike': storm.get('LZ_WEST_spike_ratio', 1.0),
    })

cross = pd.DataFrame(results)
cross.to_csv(OUTPUT_DIR / "storm_plant_cross.csv", index=False)

print(f"\n{'=' * 70}")
print("雷暴事件 × GEM 电站交叉分析 (150km 范围)")
print("=" * 70)

print(f"\n{'时间':<22} {'机场':<5} {'风速':>5} {'电站数':>6} {'受影响MW':>10} {'风电MW':>8} {'光伏MW':>8} {'最近电站':<25} {'km':>5} {'LZ_WEST飙升':>10}")
print("-" * 120)
for _, r in cross.sort_values('affected_cap_mw', ascending=False).head(20).iterrows():
    print(f"{str(r['time']):<22} {r['icao']:<5} {r['wspd']:>5.1f} {r['n_plants_150km']:>6} "
          f"{r['affected_cap_mw']:>10.0f} {r['wind_cap_mw']:>8.0f} {r['solar_cap_mw']:>8.0f} "
          f"{r['nearest_plant']:<25} {r['nearest_dist_km']:>5.0f} {r['LZ_WEST_spike']:>10.2f}")

# 统计
print(f"\n汇总统计:")
print(f"  平均受影响电站: {cross['n_plants_150km'].mean():.1f} 座")
print(f"  平均受影响装机: {cross['affected_cap_mw'].mean():.0f} MW")
print(f"  最大受影响装机: {cross['affected_cap_mw'].max():.0f} MW")
print(f"  LZ_WEST 飙升>2x 的事件: {(cross['LZ_WEST_spike'] > 2).sum()} / {len(cross)}")

# 相关性: 受影响装机 vs 电价飙升
valid = cross[(cross['LZ_WEST_spike'] > 0) & (cross['LZ_WEST_spike'] < 50)]
r_cap_price = valid['affected_cap_mw'].corr(valid['LZ_WEST_spike'])
r_wind_price = valid['wind_cap_mw'].corr(valid['LZ_WEST_spike'])
r_solar_price = valid['solar_cap_mw'].corr(valid['LZ_WEST_spike'])
print(f"\n相关性 (受影响装机 vs LZ_WEST电价飙升比):")
print(f"  总装机 vs 飙升: r={r_cap_price:+.3f}")
print(f"  风电装机 vs 飙升: r={r_wind_price:+.3f}")
print(f"  光伏装机 vs 飙升: r={r_solar_price:+.3f}")

# KDFW vs KIAH 对比
for airport in ['KDFW', 'KIAH']:
    sub = cross[cross['icao'] == airport]
    print(f"\n  {airport} ({AIRPORT_COORDS[airport][2]}): {len(sub)} 次雷暴")
    print(f"    平均受影响: {sub['n_plants_150km'].mean():.1f} 座, {sub['affected_cap_mw'].mean():.0f} MW")
    print(f"    平均 LZ_WEST 飙升: {sub['LZ_WEST_spike'].mean():.2f}x")
    print(f"    风电受影响: {sub['wind_cap_mw'].mean():.0f} MW, 光伏受影响: {sub['solar_cap_mw'].mean():.0f} MW")

print(f"\n已保存: storm_plant_cross.csv ({len(cross)} 事件)")
