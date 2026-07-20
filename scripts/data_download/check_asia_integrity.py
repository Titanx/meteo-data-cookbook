"""
东亚东南亚气象数据完整性检验
覆盖: east_southeast_asia/2025, east_southeast_asia/2026
维度: 时间覆盖、字段缺失率、异常值检测、数据质量评分
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path("c:/work/meteo/data/meteostat/east_southeast_asia")
PERIODS = [
    ("2025", pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31"), 365, 8760),
    ("2026", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-07-19"), 200, 4800),
]


def log(msg):
    print(msg, flush=True)


def load_period(period_name):
    """加载某时期所有机场数据"""
    out_dir = BASE_DIR / period_name
    airports = {}
    for f in sorted(out_dir.glob("daily_*.csv")):
        icao = f.stem.replace("daily_", "")
        df = pd.read_csv(f, parse_dates=['time'], index_col='time')
        airports.setdefault(icao, {})['daily'] = df
    for f in sorted(out_dir.glob("hourly_*.csv")):
        icao = f.stem.replace("hourly_", "")
        df = pd.read_csv(f, parse_dates=['time'], index_col='time')
        airports.setdefault(icao, {})['hourly'] = df
    return airports


def check_time_coverage(icao, daily_df, hourly_df, expected_days, expected_hours):
    """时间覆盖完整性"""
    r = {'icao': icao, 'daily_count': 0, 'hourly_count': 0,
         'daily_pct': 0, 'hourly_pct': 0, 'daily_missing': 0, 'hourly_missing': 0}
    
    if len(daily_df) > 0:
        r['daily_count'] = len(daily_df)
        r['daily_pct'] = len(daily_df) / expected_days * 100
        full_range = pd.date_range(daily_df.index.min(), daily_df.index.max(), freq='D')
        r['daily_missing'] = len(full_range.difference(daily_df.index))
    
    if len(hourly_df) > 0:
        r['hourly_count'] = len(hourly_df)
        r['hourly_pct'] = len(hourly_df) / expected_hours * 100
        full_range_h = pd.date_range(hourly_df.index.min(), hourly_df.index.max(), freq='H')
        r['hourly_missing'] = len(full_range_h.difference(hourly_df.index))
    
    return r


def check_fields(icao, daily_df, hourly_df):
    """字段缺失率"""
    r = {'icao': icao}
    
    daily_core = ['tavg', 'tmin', 'tmax', 'prcp', 'wspd', 'pres']
    for f in daily_core:
        if len(daily_df) > 0 and f in daily_df.columns:
            miss = daily_df[f].isna().sum()
            r[f'daily_{f}'] = miss / len(daily_df) * 100 if len(daily_df) > 0 else 100
        else:
            r[f'daily_{f}'] = 100.0  # 字段不存在视为全缺失
    
    hourly_core = ['temp', 'dwpt', 'rhum', 'prcp', 'wdir', 'wspd', 'pres', 'coco']
    for f in hourly_core:
        if len(hourly_df) > 0 and f in hourly_df.columns:
            miss = hourly_df[f].isna().sum()
            r[f'hourly_{f}'] = miss / len(hourly_df) * 100 if len(hourly_df) > 0 else 100
        else:
            r[f'hourly_{f}'] = 100.0
    
    return r


def check_outliers(icao, daily_df, hourly_df):
    """异常值检测"""
    outliers = []
    
    if len(daily_df) > 0:
        for col in ['tavg', 'tmin', 'tmax']:
            if col in daily_df.columns:
                vals = daily_df[col].dropna()
                # 东亚东南亚范围: -35°C ~ 50°C
                bad = vals[(vals < -35) | (vals > 50)]
                if len(bad) > 0:
                    outliers.append(f"日{col}: {len(bad)}个异常({bad.min():.1f}~{bad.max():.1f}°C)")
        
        if 'tmin' in daily_df.columns and 'tmax' in daily_df.columns:
            bad = daily_df[daily_df['tmin'] > daily_df['tmax']]
            if len(bad) > 0:
                outliers.append(f"tmin>tmax: {len(bad)}条")
        
        if 'prcp' in daily_df.columns:
            vals = daily_df['prcp'].dropna()
            heavy = vals[vals > 300]
            if len(heavy) > 0:
                outliers.append(f"日降水>300mm: {len(heavy)}条(max={heavy.max():.1f})")
    
    if len(hourly_df) > 0:
        if 'temp' in hourly_df.columns:
            vals = hourly_df['temp'].dropna()
            bad = vals[(vals < -35) | (vals > 50)]
            if len(bad) > 0:
                outliers.append(f"时temp: {len(bad)}个异常")
        
        if 'rhum' in hourly_df.columns:
            vals = hourly_df['rhum'].dropna()
            bad = vals[(vals < 0) | (vals > 100)]
            if len(bad) > 0:
                outliers.append(f"时rhum越界: {len(bad)}条")
        
        if 'pres' in hourly_df.columns:
            vals = hourly_df['pres'].dropna()
            bad = vals[(vals < 900) | (vals > 1080)]
            if len(bad) > 0:
                outliers.append(f"时pres异常: {len(bad)}条")
        
        dup = hourly_df.index.duplicated().sum()
        if dup > 0:
            outliers.append(f"重复时间戳: {dup}条")
    
    return outliers


def grade_score(pct):
    if pct >= 99: return '优'
    if pct >= 95: return '良'
    if pct >= 90: return '中'
    return '差'


def main():
    log("=" * 90)
    log("东亚东南亚气象数据完整性检验")
    log("=" * 90)

    # 加载机场元数据
    meta_path = BASE_DIR / "stations_metadata.csv"
    if meta_path.exists():
        meta_df = pd.read_csv(meta_path)
        icao_to_country = dict(zip(meta_df['icao'], meta_df['country']))
        icao_to_name = dict(zip(meta_df['icao'], meta_df['airport_name']))
    else:
        icao_to_country = {}
        icao_to_name = {}

    all_results = []

    for period_name, start, end, exp_days, exp_hours in PERIODS:
        log(f"\n{'=' * 90}")
        log(f"时期: {period_name}年 ({start:%Y-%m-%d} ~ {end:%Y-%m-%d})")
        log(f"预期: {exp_days}天, {exp_hours}小时")
        log(f"{'=' * 90}")

        airports = load_period(period_name)
        log(f"加载数据: {len(airports)} 个机场")

        # 1. 时间覆盖
        log(f"\n--- 1. 时间覆盖完整性 ---")
        log(f"{'ICAO':<7}{'机场':<16}{'国家':<8}{'日数据':<14}{'小时数据':<14}{'日缺失':>7}{'时缺失':>7}")
        log("-" * 80)

        period_results = []
        for icao, data in airports.items():
            daily = data.get('daily', pd.DataFrame())
            hourly = data.get('hourly', pd.DataFrame())
            
            cov = check_time_coverage(icao, daily, hourly, exp_days, exp_hours)
            fields = check_fields(icao, daily, hourly)
            outs = check_outliers(icao, daily, hourly)
            
            name = icao_to_name.get(icao, '')
            country = icao_to_country.get(icao, '')
            
            daily_str = f"{cov['daily_count']}/{exp_days}({cov['daily_pct']:.0f}%)"
            hourly_str = f"{cov['hourly_count']}/{exp_hours}({cov['hourly_pct']:.0f}%)"
            
            log(f"{icao:<7}{name:<16}{country:<8}{daily_str:<14}{hourly_str:<14}"
                f"{cov['daily_missing']:>7}{cov['hourly_missing']:>7}")
            
            period_results.append({
                'icao': icao, 'name': name, 'country': country,
                'period': period_name,
                **cov, **fields, 'outliers': outs
            })
        
        # 统计
        total_daily = sum(r['daily_count'] for r in period_results)
        total_hourly = sum(r['hourly_count'] for r in period_results)
        success = sum(1 for r in period_results if r['daily_count'] > 0 or r['hourly_count'] > 0)
        failed = len(period_results) - success
        log("-" * 80)
        log(f"总计: 日{total_daily}条, 时{total_hourly}条, 成功{success}/{len(period_results)}, 失败{failed}")

        # 2. 字段缺失率
        log(f"\n--- 2. 核心字段缺失率(%) ---")
        daily_fields = ['tavg', 'tmin', 'tmax', 'prcp', 'wspd', 'pres']
        hourly_fields = ['temp', 'dwpt', 'rhum', 'prcp', 'wdir', 'wspd', 'pres', 'coco']
        
        log(f"\n日数据:")
        header = f"{'ICAO':<7}{'机场':<16}{'国家':<8}" + "".join(f"{f:<8}" for f in daily_fields)
        log(header)
        log("-" * len(header))
        for r in period_results:
            row = f"{r['icao']:<7}{r['name']:<16}{r['country']:<8}"
            for f in daily_fields:
                v = r.get(f'daily_{f}', 100)
                row += f"{v:<8.0f}" if v < 100 else f"{'—':<8}"
            log(row)
        
        log(f"\n小时数据:")
        header = f"{'ICAO':<7}{'机场':<16}{'国家':<8}" + "".join(f"{f:<8}" for f in hourly_fields)
        log(header)
        log("-" * len(header))
        for r in period_results:
            row = f"{r['icao']:<7}{r['name']:<16}{r['country']:<8}"
            for f in hourly_fields:
                v = r.get(f'hourly_{f}', 100)
                row += f"{v:<8.0f}" if v < 100 else f"{'—':<8}"
            log(row)

        # 3. 异常值
        log(f"\n--- 3. 异常值检测 ---")
        has_outlier = False
        for r in period_results:
            if r['outliers']:
                has_outlier = True
                log(f"  ⚠️ {r['icao']} {r['name']}: {'; '.join(r['outliers'])}")
        if not has_outlier:
            log(f"  ✅ 所有机场均无异常值")

        # 4. 质量评分
        log(f"\n--- 4. 数据质量评分 ---")
        log(f"{'ICAO':<7}{'机场':<16}{'国家':<8}{'时间覆盖':<10}{'日字段':<10}{'时字段':<10}{'异常值':<10}{'综合':<8}")
        log("-" * 80)
        
        for r in period_results:
            # 时间覆盖
            avg_time = (r['daily_pct'] + r['hourly_pct']) / 2 if r['hourly_pct'] > 0 else r['daily_pct']
            time_g = grade_score(avg_time) if avg_time > 0 else '差'
            
            # 日数据核心字段
            daily_miss = [r.get(f'daily_{f}', 100) for f in ['tavg','tmin','tmax']]
            daily_avg = np.mean(daily_miss) if daily_miss else 100
            daily_g = '优' if daily_avg < 1 else '良' if daily_avg < 5 else '中' if daily_avg < 20 else '差'
            if r['daily_count'] == 0: daily_g = '—'
            
            # 小时数据核心字段
            hourly_miss = [r.get(f'hourly_{f}', 100) for f in ['temp','rhum','pres']]
            hourly_avg = np.mean(hourly_miss) if hourly_miss else 100
            hourly_g = '优' if hourly_avg < 1 else '良' if hourly_avg < 5 else '中' if hourly_avg < 20 else '差'
            if r['hourly_count'] == 0: hourly_g = '—'
            
            # 异常值
            out_g = '优' if len(r['outliers']) == 0 else '良' if len(r['outliers']) <= 2 else '中' if len(r['outliers']) <= 5 else '差'
            
            # 综合
            grades = [g for g in [time_g, daily_g, hourly_g, out_g] if g != '—']
            grade_order = {'优': 4, '良': 3, '中': 2, '差': 1}
            if grades:
                avg = np.mean([grade_order[g] for g in grades])
                overall = '优' if avg >= 3.5 else '良' if avg >= 2.5 else '中' if avg >= 1.5 else '差'
            else:
                overall = '—'
            
            log(f"{r['icao']:<7}{r['name']:<16}{r['country']:<8}{time_g:<10}{daily_g:<10}{hourly_g:<10}{out_g:<10}{overall:<8}")
            
            all_results.append({**r, 'time_grade': time_g, 'daily_grade': daily_g,
                               'hourly_grade': hourly_g, 'out_grade': out_g, 'overall': overall})

    # 5. 按国家汇总
    log(f"\n{'=' * 90}")
    log("按国家汇总")
    log(f"{'=' * 90}")
    log(f"{'国家':<10}{'机场数':>6}{'成功':>6}{'失败':>6}{'日数据':>10}{'小时数据':>12}{'优':>5}{'良':>5}{'中':>5}{'差':>5}")
    log("-" * 75)
    
    countries = sorted(set(r['country'] for r in all_results))
    for country in countries:
        c_data = [r for r in all_results if r['country'] == country]
        # 按ICAO去重（2025和2026会重复）
        icaos = set(r['icao'] for r in c_data)
        success = len([i for i in icaos if any(r['icao'] == i and r['daily_count'] > 0 for r in c_data)])
        failed = len(icaos) - success
        total_d = sum(r['daily_count'] for r in c_data)
        total_h = sum(r['hourly_count'] for r in c_data)
        
        # 质量分布（取2026年数据）
        c_2026 = [r for r in c_data if r['period'] == '2026']
        grades = [r.get('overall', '—') for r in c_2026]
        g_you = grades.count('优')
        g_liang = grades.count('良')
        g_zhong = grades.count('中')
        g_cha = grades.count('差')
        
        log(f"{country:<10}{len(icaos):>6}{success:>6}{failed:>6}{total_d:>10}{total_h:>12}"
            f"{g_you:>5}{g_liang:>5}{g_zhong:>5}{g_cha:>5}")

    # 总结
    log(f"\n{'=' * 90}")
    log("检验总结")
    log(f"{'=' * 90}")
    
    total_airports = len(set(r['icao'] for r in all_results))
    total_success = len([i for i in set(r['icao'] for r in all_results) 
                        if any(r['icao'] == i and r['daily_count'] > 0 for r in all_results)])
    total_failed = total_airports - total_success
    total_d = sum(r['daily_count'] for r in all_results)
    total_h = sum(r['hourly_count'] for r in all_results)
    
    log(f"  机场总数: {total_airports}")
    log(f"  成功: {total_success}, 失败: {total_failed}")
    log(f"  日数据总计: {total_d:,} 条")
    log(f"  小时数据总计: {total_h:,} 条")
    
    # 失败机场
    failed_icaos = [i for i in set(r['icao'] for r in all_results) 
                    if not any(r['icao'] == i and r['daily_count'] > 0 for r in all_results)]
    if failed_icaos:
        log(f"\n  失败机场: {', '.join(failed_icaos)}")
    
    # 质量分布
    log(f"\n  质量分布(2026年):")
    for period_name, _, _, _, _ in PERIODS:
        if period_name == '2026':
            period_data = [r for r in all_results if r['period'] == '2026']
            grades = [r.get('overall', '—') for r in period_data]
            log(f"    优: {grades.count('优')}, 良: {grades.count('良')}, "
                f"中: {grades.count('中')}, 差: {grades.count('差')}, —: {grades.count('—')}")


if __name__ == "__main__":
    main()

