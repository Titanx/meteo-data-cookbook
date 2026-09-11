"""GEM 电站 × ERCOT 电价深度分析

分析层次:
1. 风光实际出力 vs RTM 电价 (小时级量化关联)
2. 电价尖峰事件诊断 (识别+归因)
3. 风光骤降事件 → 电价响应
4. GEM 电站坐标 × 雷暴路径交叉
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import pandas as pd
import numpy as np
from pathlib import Path
from glob import glob
import warnings
warnings.filterwarnings('ignore')

GEM_DIR = Path(r"c:\work\meteo\data\gem")
ERCOT_DIR = Path(r"c:\work\meteo\data\ercot")
OUTPUT_DIR = Path(r"c:\work\meteo\output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# 1. 加载所有燃料类型发电数据
# ──────────────────────────────────────────────
print("=" * 70)
print("1. 加载 ERCOT 小时级发电数据 (燃料类型)")
print("=" * 70)

fuel_files = sorted(glob(str(ERCOT_DIR / "ercot_fuel_type_data_*.csv")))
fuel_dfs = [pd.read_csv(f) for f in fuel_files]
fuel = pd.concat(fuel_dfs, ignore_index=True)
fuel['time'] = pd.to_datetime(fuel['time'])
fuel = fuel.drop_duplicates(subset=['time', 'fuel_code'])

# 透视: 行=时间, 列=燃料类型
gen = fuel.pivot_table(index='time', columns='fuel_code', values='value', aggfunc='sum')
gen.columns = [c.strip() for c in gen.columns]
print(f"发电数据: {len(gen)} 小时, {gen.index.min()} ~ {gen.index.max()}")
print(f"燃料类型: {list(gen.columns)}")

# 风光合计
gen['wind_solar'] = gen.get('WND', 0) + gen.get('SUN', 0)
gen['total'] = gen[['BAT', 'COL', 'NG', 'NUC', 'OTH', 'SUN', 'WAT', 'WND']].sum(axis=1)
gen['re_pct'] = gen['wind_solar'] / gen['total'] * 100
gen['wind_pct'] = gen['WND'] / gen['total'] * 100
gen['solar_pct'] = gen['SUN'] / gen['total'] * 100

print(f"\n风光渗透率:")
print(f"  风电平均: {gen['WND'].mean():.0f} MWh/h ({gen['wind_pct'].mean():.1f}%)")
print(f"  光伏平均: {gen['SUN'].mean():.0f} MWh/h ({gen['solar_pct'].mean():.1f}%)")
print(f"  风光合计: {gen['wind_solar'].mean():.0f} MWh/h ({gen['re_pct'].mean():.1f}%)")
print(f"  总负荷平均: {gen['total'].mean():.0f} MWh/h")
print(f"  风电范围: {gen['WND'].min():.0f} ~ {gen['WND'].max():.0f} MWh")
print(f"  光伏范围: {gen['SUN'].min():.0f} ~ {gen['SUN'].max():.0f} MWh")

# ──────────────────────────────────────────────
# 2. 加载 4 个 Hub 的 RTM 电价 (Hub 更能反映整体区域)
# ──────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("2. 加载 RTM 电价 & 合并发电数据")
print("=" * 70)

hub_list = ['HB_WEST', 'HB_NORTH', 'HB_SOUTH', 'HB_HOUSTON']
prices = {}
for sp in hub_list:
    files = sorted(glob(str(ERCOT_DIR / f"ercot_rtm_{sp}_*.csv")))
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df['datetime'] = pd.to_datetime(df['interval_start_utc']).dt.tz_localize(None)
    df['price'] = df['spp']
    df = df[['datetime', 'price']].sort_values('datetime').reset_index(drop=True)
    prices[sp] = df
    print(f"  {sp}: {len(df):,} rows")

# 将电价聚合到小时级 (与发电数据对齐)
hourly_prices = {}
for sp in hub_list:
    df = prices[sp].copy()
    df['hour'] = df['datetime'].dt.floor('h')
    h = df.groupby('hour')['price'].mean().reset_index()
    h.columns = ['time', 'price']
    h.set_index('time', inplace=True)
    hourly_prices[sp] = h

# 合并发电+电价
merged = gen.copy()
for sp in hub_list:
    merged[f'{sp}_price'] = hourly_prices[sp]['price']
    merged[f'{sp}_price'] = merged[f'{sp}_price'].clip(lower=0)

# 去掉NaN
merged = merged.dropna(subset=['HB_WEST_price'])

print(f"\n合并后: {len(merged)} 小时")
print(f"时间范围: {merged.index.min()} ~ {merged.index.max()}")

# ──────────────────────────────────────────────
# 3. 风光出力 vs 电价 量化关联
# ──────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("3. 风光出力与电价的量化关联")
print("=" * 70)

# 相关系数
print(f"\nPearson 相关系数:")
for sp in hub_list:
    col = f'{sp}_price'
    r_wind = merged['WND'].corr(merged[col])
    r_solar = merged['SUN'].corr(merged[col])
    r_re = merged['wind_solar'].corr(merged[col])
    r_demand = merged['total'].corr(merged[col])
    print(f"  {sp}: 风电={r_wind:+.3f}, 光伏={r_solar:+.3f}, 风光={r_re:+.3f}, 负荷={r_demand:+.3f}")

# 分时段分析 (白天 vs 夜间)
merged['hour'] = merged.index.hour
merged['is_daytime'] = (merged['hour'] >= 13) & (merged['hour'] <= 23)  # UTC 13-23 = 德州7AM-5PM
print(f"\n白天 (UTC 13-23, 德州 7AM-5PM) vs 夜间相关系数:")
for sp in hub_list:
    col = f'{sp}_price'
    day = merged[merged['is_daytime']]
    night = merged[~merged['is_daytime']]
    print(f"  {sp}:")
    print(f"    白天: 风电={day['WND'].corr(day[col]):+.3f}, 光伏={day['SUN'].corr(day[col]):+.3f}")
    print(f"    夜间: 风电={night['WND'].corr(night[col]):+.3f}, 光伏={night['SUN'].corr(night[col]):+.3f}")

# 风电骤降 → 电价飙升 事件
print(f"\n{'=' * 70}")
print("4. 风电骤降事件 → 电价响应")
print("=" * 70)

# 风电骤降: 1小时内下降 >50% 且绝对值 >2000 MWh
merged['wind_delta'] = merged['WND'].diff()
merged['solar_delta'] = merged['SUN'].diff()

wind_drop = merged[(merged['wind_delta'] < -2000) & (merged['WND'].shift(1) > 5000)]
print(f"\n风电骤降事件 (1h下降>2000 MWh): {len(wind_drop)} 次")

if len(wind_drop) > 0:
    print(f"\n{'时间':<22} {'风电变化(MW)':>12} {'HB_WEST电价':>12} {'电价变化':>10} {'光伏出力':>10}")
    print("-" * 75)
    for idx, row in wind_drop.head(20).iterrows():
        prev_price = merged.loc[:idx, 'HB_WEST_price'].iloc[-2] if idx > merged.index[0] else np.nan
        price_change = row['HB_WEST_price'] - prev_price if not np.isnan(prev_price) else np.nan
        print(f"{str(idx):<22} {row['wind_delta']:>12.0f} {row['HB_WEST_price']:>12.1f} {price_change:>+10.1f} {row['SUN']:>10.0f}")

# 光伏骤降 (日落不算, 仅白天骤降)
solar_drop = merged[(merged['solar_delta'] < -5000) & (merged['SUN'].shift(1) > 8000) &
                     (merged.index.hour >= 17) & (merged.index.hour <= 23)]  # 下午
print(f"\n光伏骤降事件 (下午1h下降>5000 MWh): {len(solar_drop)} 次")

if len(solar_drop) > 0:
    print(f"\n{'时间':<22} {'光伏变化(MW)':>12} {'HB_WEST电价':>12} {'HB_HOUSTON':>12} {'电价涨幅':>10}")
    print("-" * 75)
    for idx, row in solar_drop.head(15).iterrows():
        prev_price = merged.loc[:idx, 'HB_WEST_price'].iloc[-2] if idx > merged.index[0] else np.nan
        price_change = row['HB_WEST_price'] - prev_price if not np.isnan(prev_price) else np.nan
        print(f"{str(idx):<22} {row['solar_delta']:>12.0f} {row['HB_WEST_price']:>12.1f} {row['HB_HOUSTON_price']:>12.1f} {price_change:>+10.1f}")

# ──────────────────────────────────────────────
# 4. 电价尖峰事件诊断
# ──────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("5. 电价尖峰事件诊断 (HB_WEST >$500)")
print("=" * 70)

spikes = merged[merged['HB_WEST_price'] > 500].copy()
print(f"\nHB_WEST 电价 >$500 的事件: {len(spikes)} 次")

if len(spikes) > 0:
    print(f"\n{'时间':<22} {'HB_WEST':>8} {'HB_NORTH':>8} {'HB_SOUTH':>8} {'HB_HOU':>8} {'风电':>8} {'光伏':>8} {'负荷':>8} {'RE%':>6}")
    print("-" * 100)
    for idx, row in spikes.head(25).iterrows():
        print(f"{str(idx):<22} {row['HB_WEST_price']:>8.0f} {row['HB_NORTH_price']:>8.0f} "
              f"{row['HB_SOUTH_price']:>8.0f} {row['HB_HOUSTON_price']:>8.0f} "
              f"{row['WND']:>8.0f} {row['SUN']:>8.0f} {row['total']:>8.0f} {row['re_pct']:>6.1f}")

# 尖峰事件的发电特征统计
if len(spikes) > 0:
    print(f"\n尖峰期间 vs 正常期间发电对比:")
    normal = merged[merged['HB_WEST_price'] <= 100]
    for label, sub in [('尖峰(>$500)', spikes), ('正常(<$100)', normal)]:
        print(f"  {label}: 风电={sub['WND'].mean():.0f}, 光伏={sub['SUN'].mean():.0f}, "
              f"负荷={sub['total'].mean():.0f}, RE%={sub['re_pct'].mean():.1f}%, "
              f"风电占比={sub['wind_pct'].mean():.1f}%")

# ──────────────────────────────────────────────
# 5. GEM 电站坐标 × 雷暴路径交叉
# ──────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("6. GEM 电站 × 雷暴事件交叉分析")
print("=" * 70)

# 加载雷暴事件
storm_file = OUTPUT_DIR / "thunderstorm_ercot_events.csv"
if storm_file.exists():
    storms = pd.read_csv(storm_file)
    print(f"雷暴事件: {len(storms)} 次")

    # 加载 GEM 运行中电站 (ERCOT 区域)
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

    # 检查雷暴事件的列名
    print(f"\n雷暴事件列名: {list(storms.columns)}")
    print(f"雷暴事件前3行:")
    print(storms.head(3).to_string())

    # 如果有坐标, 计算每个雷暴事件附近的电站
    if 'lat' in storms.columns or 'latitude' in storms.columns:
        lat_col = 'lat' if 'lat' in storms.columns else 'latitude'
        lon_col = 'lon' if 'lon' in storms.columns else 'longitude'
        storms_valid = storms.dropna(subset=[lat_col, lon_col]).copy()
        print(f"\n有坐标的雷暴事件: {len(storms_valid)}")

        if len(storms_valid) > 0:
            # 对每个雷暴事件, 找100km内的电站
            from math import radians, sin, cos, asin, sqrt
            def haversine(lat1, lon1, lat2, lon2):
                R = 6371
                lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
                return 2 * R * asin(sqrt(a))

            print(f"\n雷暴事件附近100km内电站 (Top 10 按受影响装机):")
            print(f"{'雷暴时间':<22} {'机场':<8} {'坐标':<20} {'受影响电站数':>8} {'受影响装机(MW)':>10} {'最近电站':>25} {'距离(km)':>8}")
            print("-" * 115)

            affected_list = []
            for _, storm in storms_valid.head(50).iterrows():
                slat, slon = storm[lat_col], storm[lon_col]
                nearby = []
                for _, plant in plants.iterrows():
                    d = haversine(slat, slon, plant['Latitude'], plant['Longitude'])
                    if d <= 100:
                        nearby.append((plant['name'], plant['capacity'], plant['type'], d))

                if nearby:
                    total_cap = sum(x[1] for x in nearby)
                    nearest = min(nearby, key=lambda x: x[3])
                    airport = storm.get('airport', storm.get('icao', '???'))
                    print(f"{str(storm.get('datetime', storm.get('time', '???'))):<22} {airport:<8} "
                          f"({slat:.2f}, {slon:.2f})   {len(nearby):>8} {total_cap:>10.0f} "
                          f"{nearest[0]:>25} {nearest[3]:>8.0f}")
                    affected_list.append({
                        'storm_time': storm.get('datetime', storm.get('time', '')),
                        'airport': airport,
                        'lat': slat, 'lon': slon,
                        'n_plants': len(nearby),
                        'affected_cap_mw': total_cap,
                        'nearest_plant': nearest[0],
                        'nearest_dist_km': nearest[3],
                        'price_spike': storm.get('price_spike_x', storm.get('max_spike_x', ''))
                    })

            affected_df = pd.DataFrame(affected_list)
            if len(affected_df) > 0:
                affected_df.to_csv(OUTPUT_DIR / "storm_plant_cross.csv", index=False)
                print(f"\n已保存: storm_plant_cross.csv ({len(affected_df)} 事件)")
                print(f"\n受影响最严重的Top 10雷暴事件:")
                top10 = affected_df.nlargest(10, 'affected_cap_mw')
                for _, r in top10.iterrows():
                    print(f"  {r['storm_time']} | {r['airport']} | "
                          f"受影响 {r['n_plants']} 座 {r['affected_cap_mw']:.0f} MW | "
                          f"最近: {r['nearest_plant']} ({r['nearest_dist_km']:.0f} km)")
    else:
        print("雷暴事件无坐标列, 跳过空间交叉")
else:
    print("未找到雷暴事件文件")

# ──────────────────────────────────────────────
# 6. 保存合并数据供后续分析
# ──────────────────────────────────────────────
merged.to_csv(OUTPUT_DIR / "ercot_hourly_gen_price.csv")
print(f"\n已保存: ercot_hourly_gen_price.csv ({len(merged)} 行)")

print(f"\n{'=' * 70}")
print("深度分析完成!")
print("=" * 70)
