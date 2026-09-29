"""
华东机场气象数据完整性检验
维度: 时间覆盖、字段缺失率、异常值检测、站点一致性
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

DATA_DIR = Path("c:/work/meteo/data/meteostat/east_china_2026")
EXPECTED_START = pd.Timestamp("2026-01-01")
EXPECTED_END   = pd.Timestamp("2026-07-19")
EXPECTED_DAYS  = (EXPECTED_END - EXPECTED_START).days + 1  # 200天
EXPECTED_HOURS = EXPECTED_DAYS * 24  # 4800小时


def log(msg):
    print(msg, flush=True)


def load_all():
    """加载所有机场数据"""
    airports = {}
    daily_files = sorted(DATA_DIR.glob("daily_*.csv"))
    for f in daily_files:
        # 文件名格式: daily_{ICAO}_{station_id}.csv
        parts = f.stem.split("_")
        icao = parts[1]
        df = pd.read_csv(f, parse_dates=['time'], index_col='time')
        airports.setdefault(icao, {})['daily'] = df
    
    hourly_files = sorted(DATA_DIR.glob("hourly_*.csv"))
    for f in hourly_files:
        parts = f.stem.split("_")
        icao = parts[1]
        df = pd.read_csv(f, parse_dates=['time'], index_col='time')
        airports.setdefault(icao, {})['hourly'] = df
    
    return airports


def check_time_coverage(icao, daily_df, hourly_df):
    """检验时间覆盖完整性"""
    result = {'icao': icao}
    
    # 日数据时间覆盖
    if len(daily_df) > 0:
        result['daily_start'] = daily_df.index.min()
        result['daily_end']   = daily_df.index.max()
        result['daily_count'] = len(daily_df)
        result['daily_expected'] = EXPECTED_DAYS
        result['daily_coverage'] = f"{len(daily_df)}/{EXPECTED_DAYS}"
        result['daily_pct'] = len(daily_df) / EXPECTED_DAYS * 100
        
        # 检查缺失日期
        full_range = pd.date_range(EXPECTED_START, EXPECTED_END, freq='D')
        missing_days = full_range.difference(daily_df.index)
        result['daily_missing_days'] = len(missing_days)
        if len(missing_days) > 0 and len(missing_days) <= 10:
            result['daily_missing_list'] = [d.strftime('%Y-%m-%d') for d in missing_days]
        elif len(missing_days) > 10:
            result['daily_missing_list'] = [d.strftime('%Y-%m-%d') for d in missing_days[:5]] + ['...']
    else:
        result['daily_count'] = 0
        result['daily_pct'] = 0
    
    # 小时数据时间覆盖
    if len(hourly_df) > 0:
        result['hourly_start'] = hourly_df.index.min()
        result['hourly_end']   = hourly_df.index.max()
        result['hourly_count'] = len(hourly_df)
        result['hourly_expected'] = EXPECTED_HOURS
        result['hourly_coverage'] = f"{len(hourly_df)}/{EXPECTED_HOURS}"
        result['hourly_pct'] = len(hourly_df) / EXPECTED_HOURS * 100
        
        # 检查缺失小时
        full_range_h = pd.date_range(EXPECTED_START, EXPECTED_END + pd.Timedelta(hours=23), freq='H')
        missing_hours = full_range_h.difference(hourly_df.index)
        result['hourly_missing_hours'] = len(missing_hours)
    else:
        result['hourly_count'] = 0
        result['hourly_pct'] = 0
    
    return result


def check_field_missing(icao, daily_df, hourly_df):
    """检验字段缺失率"""
    result = {'icao': icao}
    
    # 日数据字段缺失率
    daily_fields = ['tavg', 'tmin', 'tmax', 'prcp', 'wdir', 'wspd', 'pres', 'wpgt', 'tsun', 'snow']
    for f in daily_fields:
        if f in daily_df.columns:
            missing = daily_df[f].isna().sum() + (daily_df[f] == '').sum()
            # 也把空字符串当缺失
            valid_count = daily_df[f].notna().sum()
            result[f'daily_{f}_missing'] = f"{missing}/{len(daily_df)} ({missing/len(daily_df)*100:.1f}%)" if len(daily_df) > 0 else "N/A"
        else:
            result[f'daily_{f}_missing'] = "字段不存在"
    
    # 小时数据字段缺失率
    hourly_fields = ['temp', 'dwpt', 'rhum', 'prcp', 'wdir', 'wspd', 'pres', 'coco', 'wpgt', 'tsun', 'snow']
    for f in hourly_fields:
        if f in hourly_df.columns:
            missing = hourly_df[f].isna().sum()
            result[f'hourly_{f}_missing'] = f"{missing}/{len(hourly_df)} ({missing/len(hourly_df)*100:.1f}%)" if len(hourly_df) > 0 else "N/A"
        else:
            result[f'hourly_{f}_missing'] = "字段不存在"
    
    return result


def check_outliers(icao, daily_df, hourly_df):
    """异常值检测"""
    result = {'icao': icao, 'daily_outliers': [], 'hourly_outliers': []}
    
    # 日数据异常
    if len(daily_df) > 0:
        # 温度异常（华东合理范围: -15°C ~ 45°C）
        for col in ['tavg', 'tmin', 'tmax']:
            if col in daily_df.columns:
                vals = daily_df[col].dropna()
                outliers = vals[(vals < -15) | (vals > 45)]
                if len(outliers) > 0:
                    result['daily_outliers'].append(f"{col}: {len(outliers)}个异常 ({outliers.min():.1f}~{outliers.max():.1f}°C)")
        
        # tmin > tmax 异常
        if 'tmin' in daily_df.columns and 'tmax' in daily_df.columns:
            bad = daily_df[daily_df['tmin'] > daily_df['tmax']]
            if len(bad) > 0:
                result['daily_outliers'].append(f"tmin>tmax: {len(bad)}条")
        
        # 降水异常（单日>200mm值得检查）
        if 'prcp' in daily_df.columns:
            vals = daily_df['prcp'].dropna()
            heavy = vals[vals > 200]
            if len(heavy) > 0:
                result['daily_outliers'].append(f"prcp>200mm: {len(heavy)}条 (max={heavy.max():.1f}mm)")
        
        # 风速异常（>100km/h可能是台风，需标记）
        if 'wspd' in daily_df.columns:
            vals = daily_df['wspd'].dropna()
            strong = vals[vals > 100]
            if len(strong) > 0:
                result['daily_outliers'].append(f"wspd>100km/h: {len(strong)}条 (max={strong.max():.1f})")
        
        # 气压异常（950-1060 hPa合理）
        if 'pres' in daily_df.columns:
            vals = daily_df['pres'].dropna()
            bad = vals[(vals < 950) | (vals > 1060)]
            if len(bad) > 0:
                result['daily_outliers'].append(f"pres异常: {len(bad)}条")
    
    # 小时数据异常
    if len(hourly_df) > 0:
        # 温度
        if 'temp' in hourly_df.columns:
            vals = hourly_df['temp'].dropna()
            outliers = vals[(vals < -15) | (vals > 45)]
            if len(outliers) > 0:
                result['hourly_outliers'].append(f"temp: {len(outliers)}个异常")
        
        # 湿度（0-100%）
        if 'rhum' in hourly_df.columns:
            vals = hourly_df['rhum'].dropna()
            bad = vals[(vals < 0) | (vals > 100)]
            if len(bad) > 0:
                result['hourly_outliers'].append(f"rhum越界: {len(bad)}条")
        
        # 重复时间戳
        dup = hourly_df.index.duplicated().sum()
        if dup > 0:
            result['hourly_outliers'].append(f"重复时间戳: {dup}条")
    
    return result


def check_station_consistency(airports):
    """检查同一站点被多个机场引用的情况"""
    log("\n" + "=" * 70)
    log("4. 站点一致性检查")
    log("=" * 70)
    
    station_map = {}
    for icao, data in airports.items():
        daily = data.get('daily')
        if daily is not None and len(daily) > 0:
            # 从文件名推断站点ID
            daily_files = list(DATA_DIR.glob(f"daily_{icao}_*.csv"))
            if daily_files:
                sid = daily_files[0].stem.split("_", 2)[2]
                station_map.setdefault(sid, []).append(icao)
    
    log(f"\n站点分布:")
    for sid, icaos in station_map.items():
        if len(icaos) > 1:
            log(f"  ⚠️ 站点 {sid} 被多个机场引用: {', '.join(icaos)}")
        else:
            log(f"  ✅ 站点 {sid} → {icaos[0]}")
    
    # 检查同一站点的数据是否完全一致
    for sid, icaos in station_map.items():
        if len(icaos) > 1:
            log(f"\n  检查 {sid} 数据一致性:")
            base_df = airports[icaos[0]]['daily']
            for icao in icaos[1:]:
                other_df = airports[icao]['daily']
                if base_df.equals(other_df):
                    log(f"    ✅ {icaos[0]} 与 {icao} 日数据完全一致")
                else:
                    diff_count = (base_df != other_df).sum().sum()
                    log(f"    ⚠️ {icaos[0]} 与 {icao} 差异: {diff_count} 处")


def main():
    log("=" * 70)
    log("华东机场气象数据完整性检验")
    log(f"预期时间范围: {EXPECTED_START:%Y-%m-%d} ~ {EXPECTED_END:%Y-%m-%d}")
    log(f"预期天数: {EXPECTED_DAYS}, 预期小时数: {EXPECTED_HOURS}")
    log("=" * 70)
    
    airports = load_all()
    log(f"加载数据: {len(airports)} 个机场")
    
    # 1. 时间覆盖
    log("\n" + "=" * 70)
    log("1. 时间覆盖完整性")
    log("=" * 70)
    log(f"\n{'ICAO':<8}{'日数据':<20}{'覆盖率':<12}{'缺失日':<8}{'小时数据':<20}{'覆盖率':<12}{'缺失时':<8}")
    log("-" * 90)
    
    coverage_results = []
    for icao, data in airports.items():
        daily = data.get('daily', pd.DataFrame())
        hourly = data.get('hourly', pd.DataFrame())
        r = check_time_coverage(icao, daily, hourly)
        coverage_results.append(r)
        
        daily_str = f"{r.get('daily_count', 0)}/{EXPECTED_DAYS}"
        hourly_str = f"{r.get('hourly_count', 0)}/{EXPECTED_HOURS}"
        daily_pct = f"{r.get('daily_pct', 0):.1f}%"
        hourly_pct = f"{r.get('hourly_pct', 0):.1f}%"
        
        log(f"{icao:<8}{daily_str:<20}{daily_pct:<12}{r.get('daily_missing_days', 0):<8}"
            f"{hourly_str:<20}{hourly_pct:<12}{r.get('hourly_missing_hours', 0):<8}")
        
        if r.get('daily_missing_list'):
            log(f"        缺失日期: {', '.join(r['daily_missing_list'])}")
    
    # 统计
    total_daily = sum(r.get('daily_count', 0) for r in coverage_results)
    total_hourly = sum(r.get('hourly_count', 0) for r in coverage_results)
    log("-" * 90)
    log(f"{'合计':<8}{total_daily:<20}{'':12}{total_hourly:<20}")
    
    # 2. 字段缺失率
    log("\n" + "=" * 70)
    log("2. 字段缺失率检验")
    log("=" * 70)
    
    # 日数据字段缺失
    log("\n日数据字段缺失率:")
    daily_fields = ['tavg', 'tmin', 'tmax', 'prcp', 'wdir', 'wspd', 'pres', 'wpgt', 'tsun', 'snow']
    header = f"{'ICAO':<8}" + "".join(f"{f:<18}" for f in daily_fields)
    log(header)
    log("-" * len(header))
    
    for icao, data in airports.items():
        daily = data.get('daily', pd.DataFrame())
        r = check_field_missing(icao, daily, pd.DataFrame())
        row = f"{icao:<8}"
        for f in daily_fields:
            val = r.get(f'daily_{f}_missing', 'N/A')
            # 简化显示
            if '字段不存在' in str(val):
                row += f"{'—':<18}"
            elif 'N/A' in str(val):
                row += f"{'N/A':<18}"
            else:
                # 提取百分比
                pct_str = val.split('(')[1].rstrip(')') if '(' in val else val
                row += f"{pct_str:<18}"
        log(row)
    
    # 小时数据字段缺失
    log("\n小时数据字段缺失率:")
    hourly_fields = ['temp', 'dwpt', 'rhum', 'prcp', 'wdir', 'wspd', 'pres', 'coco', 'wpgt', 'tsun', 'snow']
    header = f"{'ICAO':<8}" + "".join(f"{f:<18}" for f in hourly_fields)
    log(header)
    log("-" * len(header))
    
    for icao, data in airports.items():
        hourly = data.get('hourly', pd.DataFrame())
        r = check_field_missing(icao, pd.DataFrame(), hourly)
        row = f"{icao:<8}"
        for f in hourly_fields:
            val = r.get(f'hourly_{f}_missing', 'N/A')
            if '字段不存在' in str(val):
                row += f"{'—':<18}"
            elif 'N/A' in str(val):
                row += f"{'N/A':<18}"
            else:
                pct_str = val.split('(')[1].rstrip(')') if '(' in val else val
                row += f"{pct_str:<18}"
        log(row)
    
    # 3. 异常值检测
    log("\n" + "=" * 70)
    log("3. 异常值检测 (华东合理范围: 温度-15~45°C, 湿度0-100%, 气压950-1060hPa)")
    log("=" * 70)
    
    for icao, data in airports.items():
        daily = data.get('daily', pd.DataFrame())
        hourly = data.get('hourly', pd.DataFrame())
        r = check_outliers(icao, daily, hourly)
        
        status = "✅ 无异常" if not r['daily_outliers'] and not r['hourly_outliers'] else "⚠️ 有异常"
        log(f"\n{icao}: {status}")
        if r['daily_outliers']:
            log(f"  日数据异常:")
            for o in r['daily_outliers']:
                log(f"    - {o}")
        if r['hourly_outliers']:
            log(f"  小时数据异常:")
            for o in r['hourly_outliers']:
                log(f"    - {o}")
    
    # 4. 站点一致性
    check_station_consistency(airports)
    
    # 5. 数据质量评分
    log("\n" + "=" * 70)
    log("5. 数据质量评分")
    log("=" * 70)
    
    log(f"\n{'ICAO':<8}{'时间覆盖':<12}{'核心字段':<12}{'异常值':<12}{'综合':<12}")
    log("-" * 56)
    
    for icao, data in airports.items():
        daily = data.get('daily', pd.DataFrame())
        hourly = data.get('hourly', pd.DataFrame())
        cov = check_time_coverage(icao, daily, hourly)
        field_r = check_field_missing(icao, daily, hourly)
        out_r = check_outliers(icao, daily, hourly)
        
        # 时间覆盖得分
        daily_pct = cov.get('daily_pct', 0)
        hourly_pct = cov.get('hourly_pct', 0)
        time_score = (daily_pct + hourly_pct) / 2
        time_grade = '优' if time_score >= 99 else '良' if time_score >= 95 else '中' if time_score >= 90 else '差'
        
        # 核心字段得分（tavg/tmin/tmax/temp/rhum/pres）
        core_missing = []
        for f in ['tavg', 'tmin', 'tmax']:
            v = field_r.get(f'daily_{f}_missing', '0/0 (0.0%)')
            if '(' in v:
                pct = float(v.split('(')[1].rstrip(')%%').rstrip('%'))
                core_missing.append(pct)
        for f in ['temp', 'rhum', 'pres']:
            v = field_r.get(f'hourly_{f}_missing', '0/0 (0.0%)')
            if '(' in v:
                pct = float(v.split('(')[1].rstrip(')%%').rstrip('%'))
                core_missing.append(pct)
        
        if core_missing:
            avg_missing = np.mean(core_missing)
            field_grade = '优' if avg_missing < 1 else '良' if avg_missing < 5 else '中' if avg_missing < 20 else '差'
        else:
            field_grade = '—'
        
        # 异常值得分
        outlier_count = len(out_r['daily_outliers']) + len(out_r['hourly_outliers'])
        out_grade = '优' if outlier_count == 0 else '良' if outlier_count <= 2 else '中' if outlier_count <= 5 else '差'
        
        # 综合
        grades = [time_grade, field_grade, out_grade]
        grade_order = {'优': 4, '良': 3, '中': 2, '差': 1, '—': 0}
        valid_grades = [g for g in grades if g != '—']
        if valid_grades:
            avg_grade = sum(grade_order[g] for g in valid_grades) / len(valid_grades)
            overall = '优' if avg_grade >= 3.5 else '良' if avg_grade >= 2.5 else '中' if avg_grade >= 1.5 else '差'
        else:
            overall = '—'
        
        log(f"{icao:<8}{time_grade:<12}{field_grade:<12}{out_grade:<12}{overall:<12}")
    
    log("\n" + "=" * 70)
    log("检验完成")
    log("=" * 70)


if __name__ == "__main__":
    main()

