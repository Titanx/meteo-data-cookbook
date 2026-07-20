"""
追加下载2025年全年全国46个机场气象数据
复用2026年已查到的站点ID，按ICAO号保存独立文件
时间范围: 2025-01-01 ~ 2025-12-31
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import warnings
warnings.filterwarnings('ignore')

from datetime import datetime
from pathlib import Path
import time
import pandas as pd

from meteostat import Daily, Hourly

# 复用2026年已查到的站点ID映射 (ICAO -> (station_id, name, region))
AIRPORT_STATIONS = {
    # 华北
    "ZBAA": ("54511", "北京首都", "华北"),
    "ZBAD": ("54511", "北京大兴", "华北"),
    "ZBTJ": ("ZBTJ0", "天津滨海", "华北"),
    "ZBSJ": ("53698", "石家庄正定", "华北"),
    "ZBYN": ("53772", "太原武宿", "华北"),
    "ZBHH": ("53463", "呼和浩特白塔", "华北"),
    # 东北
    "ZYTX": ("54342", "沈阳桃仙", "东北"),
    "ZYTL": ("54662", "大连周水子", "东北"),
    "ZYCC": ("54161", "长春龙嘉", "东北"),
    "ZYHB": ("50953", "哈尔滨太平", "东北"),
    # 华东
    "ZSPD": ("58367", "上海浦东", "华东"),
    "ZSSS": ("58367", "上海虹桥", "华东"),
    "ZSHC": ("58457", "杭州萧山", "华东"),
    "ZSNJ": ("58238", "南京禄口", "华东"),
    "ZSQD": ("54857", "青岛流亭", "华东"),
    "ZSAM": ("59134", "厦门高崎", "华东"),
    "ZSOF": ("58321", "合肥新桥", "华东"),
    "ZSJN": ("54823", "济南遥墙", "华东"),
    "ZSWX": ("ZSWX0", "无锡硕放", "华东"),
    "ZSWZ": ("ZSWZ0", "温州龙湾", "华东"),
    "ZSFZ": ("46689", "福州长乐", "华东"),
    "ZSNB": ("58477", "宁波栎社", "华东"),  # 重试得到的站点
    # 华中
    "ZHHH": ("57494", "武汉天河", "华中"),
    "ZGHA": ("57679", "长沙黄花", "华中"),
    "ZHCC": ("57083", "郑州新郑", "华中"),
    "ZSCN": ("58606", "南昌昌北", "华中"),
    # 华南
    "ZGGG": ("59287", "广州白云", "华南"),
    "ZGSZ": ("59493", "深圳宝安", "华南"),
    "ZGSD": ("45011", "珠海金湾", "华南"),
    "ZJHK": ("59758", "海口美兰", "华南"),
    "ZJSY": ("59948", "三亚凤凰", "华南"),
    "ZGNN": ("59431", "南宁吴圩", "华南"),
    "ZGKL": ("57957", "桂林两江", "华南"),
    # 西南
    "ZUUU": ("56294", "成都双流", "西南"),
    "ZUCK": ("57516", "重庆江北", "西南"),
    "ZPPP": ("56778", "昆明长水", "西南"),
    "ZUGY": ("57816", "贵阳龙洞堡", "西南"),
    "ZULS": ("55591", "拉萨贡嘎", "西南"),
    # 西北
    "ZLXY": ("ZLXY0", "西安咸阳", "西北"),
    "ZLLL": ("52889", "兰州中川", "西北"),  # 重试得到的站点
    "ZLXN": ("52866", "西宁曹家堡", "西北"),
    "ZLIC": ("53614", "银川河东", "西北"),
    "ZWAT": ("ZWWW0", "乌鲁木齐地窝堡", "西北"),
    # 港澳台
    "VHHH": ("45001", "香港赤鱲角", "港澳台"),
    "VMMC": ("45011", "澳门国际", "港澳台"),
    "RCTP": ("46697", "台北桃园", "港澳台"),
}

# 2025全年
START = datetime(2025, 1, 1)
END   = datetime(2025, 12, 31, 23, 59)

OUTPUT_DIR = Path("c:/work/meteo/data/meteostat/china_2025")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    print(msg, flush=True)


def main():
    log("=" * 80)
    log("追加下载2025年全国机场气象数据")
    log("=" * 80)
    log(f"机场数: {len(AIRPORT_STATIONS)}")
    log(f"时间范围: {START:%Y-%m-%d} ~ {END:%Y-%m-%d}")
    log(f"输出目录: {OUTPUT_DIR}")
    log(f"文件命名: daily_{{ICAO}}.csv, hourly_{{ICAO}}.csv")
    log("")

    summary_records = []
    current_region = None

    for i, (icao, (sid, name, region)) in enumerate(AIRPORT_STATIONS.items(), 1):
        if region != current_region:
            log(f"\n{'─' * 60}")
            log(f"【{region}】")
            log(f"{'─' * 60}")
            current_region = region

        log(f"\n[{i}/{len(AIRPORT_STATIONS)}] {icao} {name} (站点:{sid})")

        # 下载日数据
        daily_path = OUTPUT_DIR / f"daily_{icao}.csv"
        try:
            data = Daily(sid, START, END)
            daily_df = data.fetch()
            if len(daily_df) > 0:
                daily_df.to_csv(daily_path, encoding='utf-8-sig')
                tavg = daily_df['tavg'].mean()
                tmax = daily_df['tmax'].max()
                tmin = daily_df['tmin'].min()
                prcp = daily_df['prcp'].sum() if 'prcp' in daily_df.columns else 0
                log(f"  日数据: {len(daily_df)} 条, 均温={tavg:.1f}°C, 极值={tmin:.1f}~{tmax:.1f}°C, 降水={prcp:.0f}mm")
            else:
                log(f"  日数据: 无数据")
                daily_df = pd.DataFrame()
        except Exception as e:
            log(f"  日数据失败: {e}")
            daily_df = pd.DataFrame()

        time.sleep(0.3)

        # 下载小时数据
        hourly_path = OUTPUT_DIR / f"hourly_{icao}.csv"
        try:
            data = Hourly(sid, START, END)
            hourly_df = data.fetch()
            if len(hourly_df) > 0:
                hourly_df.to_csv(hourly_path, encoding='utf-8-sig')
                log(f"  小时数据: {len(hourly_df)} 条")
            else:
                log(f"  小时数据: 无数据")
                hourly_df = pd.DataFrame()
        except Exception as e:
            log(f"  小时数据失败: {e}")
            hourly_df = pd.DataFrame()

        time.sleep(0.3)

        summary_records.append({
            'icao': icao, 'name': name, 'region': region,
            'station_id': sid,
            'daily_count': len(daily_df), 'hourly_count': len(hourly_df),
            'status': 'ok' if len(daily_df) > 0 or len(hourly_df) > 0 else 'no_data'
        })

    # 保存汇总
    summary_df = pd.DataFrame(summary_records)
    summary_path = OUTPUT_DIR / "download_summary_2025.csv"
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')

    # 汇总报告
    log("\n" + "=" * 80)
    log("2025年下载汇总")
    log("=" * 80)
    log(f"\n{'ICAO':<7}{'机场':<14}{'区域':<8}{'站点ID':<10}{'日数据':>8}{'小时数据':>10}{'状态':<8}")
    log("-" * 75)

    current_region = None
    for r in summary_records:
        if r['region'] != current_region:
            if current_region is not None:
                region_items = [x for x in summary_records if x['region'] == current_region]
                r_daily = sum(x['daily_count'] for x in region_items)
                r_hourly = sum(x['hourly_count'] for x in region_items)
                log(f"{'':7}{'小计':<14}{current_region:<8}{'':10}{r_daily:>8}{r_hourly:>10}")
                log("")
            current_region = r['region']
        log(f"{r['icao']:<7}{r['name']:<14}{r['region']:<8}{str(r['station_id']):<10}"
            f"{r['daily_count']:>8}{r['hourly_count']:>10}{r['status']:<8}")

    # 最后区域小计
    region_items = [x for x in summary_records if x['region'] == current_region]
    r_daily = sum(x['daily_count'] for x in region_items)
    r_hourly = sum(x['hourly_count'] for x in region_items)
    log(f"{'':7}{'小计':<14}{current_region:<8}{'':10}{r_daily:>8}{r_hourly:>10}")

    total_daily = sum(r['daily_count'] for r in summary_records)
    total_hourly = sum(r['hourly_count'] for r in summary_records)
    success = sum(1 for r in summary_records if r['status'] == 'ok')
    failed = sum(1 for r in summary_records if r['status'] != 'ok')

    log("-" * 75)
    log(f"{'总计':<39}{total_daily:>8}{total_hourly:>10}")
    log(f"\n成功: {success}, 失败: {failed}")
    log(f"总记录数: 日数据 {total_daily} 条, 小时数据 {total_hourly} 条")
    log(f"\n输出目录: {OUTPUT_DIR}")
    log(f"汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
