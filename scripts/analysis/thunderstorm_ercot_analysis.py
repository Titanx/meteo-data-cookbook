"""雷暴大风事件 × ERCOT 电价/发电联动分析

分析逻辑:
1. 从 Meteostat 美洲机场小时数据中筛选雷暴大风事件
   (本小时风速 >20 m/s, 前后小时 ≤5 m/s)
2. 定位 ERCOT 区域（德州）的机场: KDFW(达拉斯), KIAH(休斯顿) 等
3. 对每个德州雷暴事件, 提取前后 6 小时窗口的:
   - ERCOT RTM 电价 (15分钟级, 4 枢纽 + 4 负荷区 = 8 个结算点)
   - ERCOT Solar 发电量 (小时级)
   - ERCOT Wind 发电量 (小时级)
   - ERCOT 总负荷 (小时级)
4. 生成联动分析报告:
   - 事件列表
   - 每个事件的价格/发电变化对比
   - 可视化图表 (HTML)

输出:
  c:\\work\\meteo\\output\\thunderstorm_ercot_analysis.html
  c:\\work\\meteo\\output\\thunderstorm_ercot_events.csv
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import pandas as pd
import numpy as np
from pathlib import Path
from glob import glob
from datetime import timedelta
import json

# ── 路径 ──
METEOSTAT_DIR = Path(r"c:\work\meteo\data\meteostat\americas")
ERCOT_DIR = Path(r"c:\work\meteo\data\ercot")
OUTPUT_DIR = Path(r"c:\work\meteo\output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 德州机场 ICAO 代码 (ERCOT 区域内)
# KDFW=达拉斯, KIAH=休斯顿, 其他德州机场可能数据不足
TEXAS_AIRPORTS = ["KDFW", "KIAH"]

# 雷暴大风判定阈值
WIND_THRESHOLD = 20  # m/s, 本小时风速最低阈值
WIND_SPIKE = 15  # m/s, 本小时比前小时骤增 ≥ 此值即为雷暴骤风
MAX_WIND = 40  # m/s, 排除 > 此值的可疑数据

# 分析窗口 (小时)
WINDOW_BEFORE = 6
WINDOW_AFTER = 6


def log(msg):
    print(f"[{pd.Timestamp.now():%H:%M:%S}] {msg}", flush=True)


def load_meteostat_airport(icao, year):
    """加载单个机场的年度小时数据"""
    fpath = METEOSTAT_DIR / str(year) / f"hourly_{icao}.csv"
    if not fpath.exists():
        return None
    df = pd.read_csv(fpath)
    # Meteostat 列: time, temp, dwpt, rhum, prcp, snow, wdir, wspd, wpgt, pres, coco
    if "time" not in df.columns:
        return None
    df["time"] = pd.to_datetime(df["time"])
    # 统一为 UTC tz-aware
    if df["time"].dt.tz is None:
        df["time"] = df["time"].dt.tz_localize("UTC")
    if "wspd" in df.columns:
        df["wspd"] = pd.to_numeric(df["wspd"], errors="coerce")
    if "prcp" in df.columns:
        df["prcp"] = pd.to_numeric(df["prcp"], errors="coerce")
    return df


def find_thunderstorm_events(df, icao):
    """筛选雷暴骤风事件: 本小时风速 >20 m/s 且比前小时骤增 ≥15 m/s

    德州常年多风（KDFW 均值 16 m/s），绝对阈值的"前后静风"条件不适用。
    改用"风速骤变"逻辑: 本小时比前小时骤增 ≥15 m/s，更符合雷暴过境特征。
    """
    events = []
    if df is None or "wspd" not in df.columns:
        return events

    df = df.sort_values("time").reset_index(drop=True)
    wspd = df["wspd"].values
    times = df["time"].values
    prcp = df["prcp"].values if "prcp" in df.columns else np.full(len(df), np.nan)

    for i in range(1, len(df)):
        if pd.isna(wspd[i]) or pd.isna(wspd[i - 1]):
            continue
        # 本小时风速 > 最低阈值
        if wspd[i] <= WIND_THRESHOLD:
            continue
        # 风速骤增: 本小时 - 前小时 ≥ 骤变阈值
        spike = wspd[i] - wspd[i - 1]
        if spike < WIND_SPIKE:
            continue
        # 排除 >40 m/s 的可疑数据
        if wspd[i] > MAX_WIND:
            continue

        events.append({
            "icao": icao,
            "time": pd.Timestamp(times[i]).tz_localize("UTC") if pd.Timestamp(times[i]).tz is None else pd.Timestamp(times[i]),
            "wspd": wspd[i],
            "wspd_prev": wspd[i - 1],
            "wspd_spike": spike,
            "prcp": prcp[i] if not pd.isna(prcp[i]) else 0,
        })
    return events


def load_ercot_rtm(hub, start, end):
    """加载 ERCOT RTM 电价数据"""
    fpath = ERCOT_DIR / f"ercot_rtm_{hub}_2025-01-01_2026-07-23.csv"
    if not fpath.exists():
        return None
    df = pd.read_csv(fpath)
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"])
    if df["interval_start_utc"].dt.tz is None:
        df["interval_start_utc"] = df["interval_start_utc"].dt.tz_localize("UTC")
    df["spp"] = pd.to_numeric(df["spp"], errors="coerce")
    mask = (df["interval_start_utc"] >= start) & (df["interval_start_utc"] <= end)
    return df[mask].copy()


def load_ercot_fuel_data(fuel_code, start, end):
    """加载 ERCOT 燃料类型发电数据"""
    # 需要跨月加载, 从所有月份文件中拼接
    all_dfs = []
    for f in sorted(glob(str(ERCOT_DIR / "ercot_fuel_type_data_*.csv"))):
        df = pd.read_csv(f)
        if fuel_code == "SUN":
            df = df[df["fuel_code"] == "SUN"]
        elif fuel_code == "WND":
            df = df[df["fuel_code"] == "WND"]
        elif fuel_code == "D":
            # 从 region_data 加载负荷
            continue
        all_dfs.append(df)
    if not all_dfs:
        return None
    df = pd.concat(all_dfs, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"])
    if df["time"].dt.tz is None:
        df["time"] = df["time"].dt.tz_localize("UTC")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    mask = (df["time"] >= start) & (df["time"] <= end)
    return df[mask].copy()


def load_ercot_demand(start, end):
    """加载 ERCOT 负荷数据"""
    all_dfs = []
    for f in sorted(glob(str(ERCOT_DIR / "ercot_region_data_*.csv"))):
        df = pd.read_csv(f)
        df = df[df["type_code"] == "D"]
        all_dfs.append(df)
    if not all_dfs:
        return None
    df = pd.concat(all_dfs, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"])
    if df["time"].dt.tz is None:
        df["time"] = df["time"].dt.tz_localize("UTC")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    mask = (df["time"] >= start) & (df["time"] <= end)
    return df[mask].copy()


def analyze_event(event, rtm_data, solar_data, wind_data, demand_data):
    """分析单个雷暴事件前后的电价/发电变化"""
    event_time = event["time"]
    window_start = event_time - timedelta(hours=WINDOW_BEFORE)
    window_end = event_time + timedelta(hours=WINDOW_AFTER)

    result = {
        **event,
        "window_start": window_start,
        "window_end": window_end,
    }

    # RTM 电价分析
    price_stats = {}
    for hub, df in rtm_data.items():
        if df is None or len(df) == 0:
            continue
        mask = (df["interval_start_utc"] >= window_start) & (df["interval_start_utc"] <= window_end)
        window_df = df[mask]
        if len(window_df) == 0:
            continue
        # 事件时刻的价格
        event_mask = (df["interval_start_utc"] >= event_time - timedelta(minutes=15)) & \
                     (df["interval_start_utc"] <= event_time + timedelta(minutes=15))
        event_price = df[event_mask]["spp"].values
        event_price = event_price[0] if len(event_price) > 0 else np.nan

        # 事件前 6 小时均价
        before_mask = (df["interval_start_utc"] >= window_start) & (df["interval_start_utc"] < event_time)
        before_price = df[before_mask]["spp"].mean()

        # 事件后 6 小时均价
        after_mask = (df["interval_start_utc"] > event_time) & (df["interval_start_utc"] <= window_end)
        after_price = df[after_mask]["spp"].mean()

        # 窗口内最高/最低
        window_max = window_df["spp"].max()
        window_min = window_df["spp"].min()

        price_stats[hub] = {
            "event_price": event_price,
            "before_avg": before_price,
            "after_avg": after_price,
            "window_max": window_max,
            "window_min": window_min,
            "spike_ratio": event_price / before_price if before_price and before_price > 0 else np.nan,
        }

    result["price_stats"] = price_stats

    # Solar 发电分析
    if solar_data is not None and len(solar_data) > 0:
        mask = (solar_data["time"] >= window_start) & (solar_data["time"] <= window_end)
        solar_window = solar_data[mask]
        if len(solar_window) > 0:
            event_solar = solar_window.iloc[(solar_window["time"] - event_time).abs().argsort()[:1]]["value"].values
            result["solar_event"] = event_solar[0] if len(event_solar) > 0 else np.nan
            result["solar_before_avg"] = solar_window[solar_window["time"] < event_time]["value"].mean()
            result["solar_after_avg"] = solar_window[solar_window["time"] > event_time]["value"].mean()
            result["solar_max"] = solar_window["value"].max()
            result["solar_min"] = solar_window["value"].min()
        else:
            result["solar_event"] = np.nan
    else:
        result["solar_event"] = np.nan

    # Wind 发电分析
    if wind_data is not None and len(wind_data) > 0:
        mask = (wind_data["time"] >= window_start) & (wind_data["time"] <= window_end)
        wind_window = wind_data[mask]
        if len(wind_window) > 0:
            event_wind = wind_window.iloc[(wind_window["time"] - event_time).abs().argsort()[:1]]["value"].values
            result["wind_event"] = event_wind[0] if len(event_wind) > 0 else np.nan
            result["wind_before_avg"] = wind_window[wind_window["time"] < event_time]["value"].mean()
            result["wind_after_avg"] = wind_window[wind_window["time"] > event_time]["value"].mean()
            result["wind_max"] = wind_window["value"].max()
            result["wind_min"] = wind_window["value"].min()
        else:
            result["wind_event"] = np.nan
    else:
        result["wind_event"] = np.nan

    # 负荷分析
    if demand_data is not None and len(demand_data) > 0:
        mask = (demand_data["time"] >= window_start) & (demand_data["time"] <= window_end)
        demand_window = demand_data[mask]
        if len(demand_window) > 0:
            result["demand_event"] = demand_window.iloc[(demand_window["time"] - event_time).abs().argsort()[:1]]["value"].values[0]
            result["demand_before_avg"] = demand_window[demand_window["time"] < event_time]["value"].mean()
            result["demand_after_avg"] = demand_window[demand_window["time"] > event_time]["value"].mean()
        else:
            result["demand_event"] = np.nan
    else:
        result["demand_event"] = np.nan

    return result


def generate_html_report(events, analyses, output_path):
    """生成 HTML 分析报告"""
    log("生成 HTML 报告...")

    # 事件汇总表
    event_rows = ""
    for a in analyses:
        event_time_str = a["time"].strftime("%Y-%m-%d %H:%M UTC")
        # 找最显著的 Hub
        best_hub = None
        best_ratio = 1.0
        for loc in ["HB_NORTH", "HB_HOUSTON", "HB_SOUTH", "HB_WEST"]:
            stats = a.get("price_stats", {}).get(loc)
            if stats is None:
                continue
            ratio = stats.get("spike_ratio", 1.0)
            if not np.isnan(ratio) and ratio > best_ratio:
                best_ratio = ratio
                best_hub = loc

        # 找最显著的 Load Zone
        best_lz = None
        best_lz_ratio = 1.0
        for loc in ["LZ_NORTH", "LZ_HOUSTON", "LZ_SOUTH", "LZ_WEST"]:
            stats = a.get("price_stats", {}).get(loc)
            if stats is None:
                continue
            ratio = stats.get("spike_ratio", 1.0)
            if not np.isnan(ratio) and ratio > best_lz_ratio:
                best_lz_ratio = ratio
                best_lz = loc

        hub_str = f"{best_hub} ({best_ratio:.1f}x)" if best_hub else "N/A"
        lz_str = f"{best_lz} ({best_lz_ratio:.1f}x)" if best_lz else "N/A"
        max_ratio = max(best_ratio, best_lz_ratio)

        # 光伏变化
        solar_before = a.get("solar_before_avg", np.nan)
        solar_event = a.get("solar_event", np.nan)
        if not np.isnan(solar_before) and not np.isnan(solar_event) and solar_before > 100:
            solar_drop = (1 - solar_event / solar_before) * 100
            solar_str = f"{solar_event:.0f} MWh ({solar_drop:+.0f}%)"
        else:
            solar_str = f"{solar_event:.0f} MWh" if not np.isnan(solar_event) else "N/A"

        # 风电变化
        wind_before = a.get("wind_before_avg", np.nan)
        wind_event = a.get("wind_event", np.nan)
        if not np.isnan(wind_before) and not np.isnan(wind_event) and wind_before > 100:
            wind_change = (wind_event / wind_before - 1) * 100
            wind_str = f"{wind_event:.0f} MWh ({wind_change:+.0f}%)"
        else:
            wind_str = f"{wind_event:.0f} MWh" if not np.isnan(wind_event) else "N/A"

        event_rows += f"""
        <tr>
            <td>{a['icao']}</td>
            <td>{event_time_str}</td>
            <td>{a['wspd']:.1f} m/s</td>
            <td>{a['prcp']:.1f} mm</td>
            <td class="{'highlight' if best_ratio > 2 else ''}">{hub_str}</td>
            <td class="{'highlight' if best_lz_ratio > 2 else ''}">{lz_str}</td>
            <td>{solar_str}</td>
            <td>{wind_str}</td>
        </tr>"""

    # 极端事件详情卡片
    extreme_cards = ""
    extreme_events = [a for a in analyses if any(
        s.get("spike_ratio", 1) > 2 for s in a.get("price_stats", {}).values()
    )]
    for a in extreme_events[:8]:
        event_time_str = a["time"].strftime("%Y-%m-%d %H:%M UTC")
        cards_html = ""
        # 分两组: Hub 和 Load Zone
        hub_names = ["HB_NORTH", "HB_HOUSTON", "HB_SOUTH", "HB_WEST"]
        lz_names = ["LZ_NORTH", "LZ_HOUSTON", "LZ_SOUTH", "LZ_WEST"]

        for group_name, group_locs in [("Trading Hubs", hub_names), ("Load Zones", lz_names)]:
            group_cards = ""
            for loc in group_locs:
                stats = a.get("price_stats", {}).get(loc)
                if stats is None or np.isnan(stats.get("event_price", np.nan)):
                    continue
                before = stats.get("before_avg", 0)
                event_p = stats.get("event_price", 0)
                after = stats.get("after_avg", 0)
                max_p = stats.get("window_max", 0)
                ratio = stats.get("spike_ratio", 1)
                bar_width = min(max_p / 100, 100) if max_p > 0 else 0
                group_cards += f"""
                    <div class="hub-card">
                        <div class="hub-name">{loc}</div>
                        <div class="hub-prices">
                            <span>事件前: ${before:.1f}</span>
                            <span class="{'price-spike' if ratio > 2 else ''}">事件时: ${event_p:.1f} ({ratio:.1f}x)</span>
                            <span>事件后: ${after:.1f}</span>
                            <span>窗口最高: ${max_p:.1f}</span>
                        </div>
                        <div class="bar-container">
                            <div class="bar" style="width:{bar_width}%"></div>
                        </div>
                    </div>"""
            if group_cards:
                cards_html += f'<div class="hub-group"><div class="hub-group-title">{group_name}</div><div class="hubs-grid">{group_cards}</div></div>'

        solar_str = ""
        if not np.isnan(a.get("solar_before_avg", np.nan)) and not np.isnan(a.get("solar_event", np.nan)):
            sb = a.get("solar_before_avg", 0)
            se = a.get("solar_event", 0)
            if sb > 100:
                drop = (1 - se / sb) * 100
                solar_str = f"""
                <div class="gen-card">
                    <span class="gen-label">☀️ Solar</span>
                    <span>事件前: {sb:.0f} → 事件时: {se:.0f} MWh ({drop:+.0f}%)</span>
                </div>"""

        wind_str = ""
        if not np.isnan(a.get("wind_before_avg", np.nan)) and not np.isnan(a.get("wind_event", np.nan)):
            wb = a.get("wind_before_avg", 0)
            we = a.get("wind_event", 0)
            if wb > 100:
                change = (we / wb - 1) * 100
                wind_str = f"""
                <div class="gen-card">
                    <span class="gen-label">💨 Wind</span>
                    <span>事件前: {wb:.0f} → 事件时: {we:.0f} MWh ({change:+.0f}%)</span>
                </div>"""

        extreme_cards += f"""
        <div class="event-card">
            <h3>{a['icao']} - {event_time_str}</h3>
            <div class="event-meta">风速 {a['wspd']:.1f} m/s | 降水 {a['prcp']:.1f} mm</div>
            <div class="hubs-grid">{cards_html}</div>
            {solar_str}{wind_str}
        </div>"""

    # 统计摘要
    total_events = len(analyses)
    price_spike_events = len([a for a in analyses if any(
        s.get("spike_ratio", 1) > 2 and not np.isnan(s.get("spike_ratio", 1))
        for s in a.get("price_stats", {}).values()
    )])
    solar_drop_events = len([a for a in analyses if
        not np.isnan(a.get("solar_before_avg", np.nan)) and
        not np.isnan(a.get("solar_event", np.nan)) and
        a.get("solar_before_avg", 0) > 100 and
        a.get("solar_event", 0) < a.get("solar_before_avg", 0) * 0.5
    ])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>雷暴大风 × ERCOT 电价联动分析</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #1a5276; margin-bottom: 10px; }}
h2 {{ color: #2874a6; margin: 30px 0 15px; border-bottom: 2px solid #d4e6f1; padding-bottom: 8px; }}
h3 {{ color: #2e86c1; margin-bottom: 8px; }}
.subtitle {{ color: #666; margin-bottom: 30px; font-size: 14px; }}
.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
.stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); text-align: center; }}
.stat-number {{ font-size: 32px; font-weight: bold; color: #2874a6; }}
.stat-label {{ color: #666; font-size: 13px; margin-top: 5px; }}
table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }}
th {{ background: #2874a6; color: white; padding: 12px; text-align: left; font-size: 13px; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 13px; }}
tr:hover {{ background: #f8f9fa; }}
.highlight {{ background: #fff3cd; font-weight: bold; }}
.event-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); margin-bottom: 20px; border-left: 4px solid #e74c3c; }}
.event-meta {{ color: #666; font-size: 14px; margin-bottom: 12px; }}
.hubs-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px; margin-bottom: 10px; }}
.hub-card {{ background: #f8f9fa; padding: 12px; border-radius: 6px; }}
.hub-name {{ font-weight: bold; color: #1a5276; margin-bottom: 6px; }}
.hub-prices {{ display: flex; flex-direction: column; gap: 3px; font-size: 13px; }}
.price-spike {{ color: #e74c3c; font-weight: bold; }}
.bar-container {{ background: #e0e0e0; height: 6px; border-radius: 3px; margin-top: 6px; }}
.bar {{ background: #2874a6; height: 100%; border-radius: 3px; }}
.gen-card {{ background: #eaf7ef; padding: 10px 15px; border-radius: 6px; margin-top: 8px; font-size: 14px; }}
.gen-label {{ font-weight: bold; margin-right: 10px; }}
.hub-group {{ margin-bottom: 12px; }}
.hub-group-title {{ font-size: 13px; color: #8e44ad; font-weight: bold; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }}
.hub-card.lz {{ background: #fef9e7; }}
.hub-card.lz .hub-name {{ color: #7d3c98; }}
.note {{ background: #fffde7; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 13px; color: #7d6608; border-left: 4px solid #f1c40f; }}
</style>
</head>
<body>
<div class="container">
    <h1>雷暴大风 × ERCOT 电价联动分析</h1>
    <p class="subtitle">数据源: Meteostat 机场观测 + EIA API v2 + GridStatus.io | 分析时间: {pd.Timestamp.now():%Y-%m-%d %H:%M}</p>

    <div class="stats-grid">
        <div class="stat-card"><div class="stat-number">{total_events}</div><div class="stat-label">德州雷暴事件总数</div></div>
        <div class="stat-card"><div class="stat-number">{price_spike_events}</div><div class="stat-label">伴随电价尖峰事件</div></div>
        <div class="stat-card"><div class="stat-number">{solar_drop_events}</div><div class="stat-label">伴随光伏骤降事件</div></div>
        <div class="stat-card"><div class="stat-number">{'KDFW, KIAH'}</div><div class="stat-label">分析机场</div></div>
    </div>

    <h2>事件汇总</h2>
    <table>
        <thead><tr><th>机场</th><th>时间 (UTC)</th><th>风速</th><th>降水</th><th>Hub 电价尖峰</th><th>Load Zone 电价尖峰</th><th>Solar 发电</th><th>Wind 发电</th></tr></thead>
        <tbody>{event_rows}
        </tbody>
    </table>

    <h2>电价尖峰事件详情 (事件时价格 > 事件前均价 2 倍)</h2>
    {extreme_cards if extreme_cards else '<p style="color:#666;">无电价尖峰事件</p>'}

    <div class="note">
        <strong>分析说明:</strong><br>
        - 雷暴骤风定义: 本小时风速 >20 m/s 且比前小时骤增 ≥15 m/s, 排除 >40 m/s 可疑数据<br>
        - 电价尖峰定义: 事件时刻 RTM 价格 > 事件前 6 小时均价的 2 倍<br>
        - 光伏骤降定义: 事件时刻 Solar 发电 < 事件前 6 小时均值的 50%<br>
        - ERCOT 区域覆盖德州, KDFW=达拉斯, KIAH=休斯顿<br>
        - 结算点: 4 个交易枢纽 (HB_NORTH/SOUTH/HOUSTON/WEST) + 4 个负荷区 (LZ_NORTH/SOUTH/HOUSTON/WEST)<br>
        - 负荷区电价比枢纽更贴近终端用户区域, LZ_WEST 覆盖风电密集区<br>
        - 时间均为 UTC, 德州本地时间 = UTC-5 (CST) 或 UTC-6 (CDT)
    </div>
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"HTML 报告: {output_path}")


def main():
    log("=" * 60)
    log("雷暴大风事件 × ERCOT 电价联动分析")
    log("=" * 60)

    # 1. 筛选德州机场的雷暴事件
    log("\n[1/4] 筛选德州机场雷暴大风事件...")
    all_events = []
    for icao in TEXAS_AIRPORTS:
        for year in [2025, 2026]:
            df = load_meteostat_airport(icao, year)
            if df is None:
                log(f"  {icao} {year}: 无数据")
                continue
            events = find_thunderstorm_events(df, icao)
            log(f"  {icao} {year}: {len(events)} 个事件")
            all_events.extend(events)

    log(f"  合计: {len(all_events)} 个德州雷暴事件")
    if not all_events:
        log("  无事件, 退出")
        return

    # 2. 加载 ERCOT 数据
    log("\n[2/4] 加载 ERCOT 数据...")
    # 找数据覆盖范围
    min_time = min(e["time"] for e in all_events) - timedelta(hours=WINDOW_BEFORE + 1)
    max_time = max(e["time"] for e in all_events) + timedelta(hours=WINDOW_AFTER + 1)

    # RTM 电价 (4 枢纽 + 4 负荷区 = 8 个结算点)
    hubs = ["HB_NORTH", "HB_HOUSTON", "HB_SOUTH", "HB_WEST"]
    load_zones = ["LZ_NORTH", "LZ_HOUSTON", "LZ_SOUTH", "LZ_WEST"]
    all_locations = hubs + load_zones
    rtm_data = {}
    for loc in all_locations:
        rtm_data[loc] = load_ercot_rtm(loc, min_time, max_time)
        if rtm_data[loc] is not None:
            log(f"  RTM {loc}: {len(rtm_data[loc])} 行")

    # Solar 发电
    solar_data = load_ercot_fuel_data("SUN", min_time, max_time)
    if solar_data is not None:
        log(f"  Solar 发电: {len(solar_data)} 行")

    # Wind 发电
    wind_data = load_ercot_fuel_data("WND", min_time, max_time)
    if wind_data is not None:
        log(f"  Wind 发电: {len(wind_data)} 行")

    # 负荷
    demand_data = load_ercot_demand(min_time, max_time)
    if demand_data is not None:
        log(f"  负荷: {len(demand_data)} 行")

    # 3. 对每个事件做联动分析
    log(f"\n[3/4] 分析 {len(all_events)} 个事件...")
    analyses = []
    for i, event in enumerate(all_events):
        if (i + 1) % 5 == 0:
            log(f"  进度: {i+1}/{len(all_events)}")
        result = analyze_event(event, rtm_data, solar_data, wind_data, demand_data)
        analyses.append(result)

    # 保存事件 CSV
    csv_rows = []
    for a in analyses:
        row = {
            "icao": a["icao"],
            "time": a["time"],
            "wspd": a["wspd"],
            "prcp": a["prcp"],
            "solar_event": a.get("solar_event", np.nan),
            "solar_before_avg": a.get("solar_before_avg", np.nan),
            "wind_event": a.get("wind_event", np.nan),
            "wind_before_avg": a.get("wind_before_avg", np.nan),
            "demand_event": a.get("demand_event", np.nan),
        }
        for hub, stats in a.get("price_stats", {}).items():
            row[f"{hub}_event_price"] = stats.get("event_price", np.nan)
            row[f"{hub}_before_avg"] = stats.get("before_avg", np.nan)
            row[f"{hub}_spike_ratio"] = stats.get("spike_ratio", np.nan)
        csv_rows.append(row)
    csv_path = OUTPUT_DIR / "thunderstorm_ercot_events.csv"
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)
    log(f"事件 CSV: {csv_path}")

    # 4. 生成 HTML 报告
    log(f"\n[4/4] 生成报告...")
    html_path = OUTPUT_DIR / "thunderstorm_ercot_analysis.html"
    generate_html_report(all_events, analyses, html_path)

    # 打印关键发现
    log("\n" + "=" * 60)
    log("关键发现:")
    log("=" * 60)

    spike_events = [a for a in analyses if any(
        s.get("spike_ratio", 1) > 2 and not np.isnan(s.get("spike_ratio", 1))
        for s in a.get("price_stats", {}).values()
    )]
    log(f"  电价尖峰事件 (>2x): {len(spike_events)} / {len(analyses)}")

    solar_drops = [a for a in analyses if
        not np.isnan(a.get("solar_before_avg", np.nan)) and
        not np.isnan(a.get("solar_event", np.nan)) and
        a.get("solar_before_avg", 0) > 100 and
        a.get("solar_event", 0) < a.get("solar_before_avg", 0) * 0.5
    ]
    log(f"  光伏骤降事件 (>50%): {len(solar_drops)} / {len(analyses)}")

    for a in analyses:
        time_str = a["time"].strftime("%Y-%m-%d %H:%M")
        # 找最显著的 Hub
        best_hub = None
        best_ratio = 1.0
        for loc in ["HB_NORTH", "HB_HOUSTON", "HB_SOUTH", "HB_WEST"]:
            stats = a.get("price_stats", {}).get(loc)
            if stats is None:
                continue
            ratio = stats.get("spike_ratio", 1.0)
            if not np.isnan(ratio) and ratio > best_ratio:
                best_ratio = ratio
                best_hub = loc

        # 找最显著的 Load Zone
        best_lz = None
        best_lz_ratio = 1.0
        for loc in ["LZ_NORTH", "LZ_HOUSTON", "LZ_SOUTH", "LZ_WEST"]:
            stats = a.get("price_stats", {}).get(loc)
            if stats is None:
                continue
            ratio = stats.get("spike_ratio", 1.0)
            if not np.isnan(ratio) and ratio > best_lz_ratio:
                best_lz_ratio = ratio
                best_lz = loc

        max_ratio = max(best_ratio, best_lz_ratio)
        best_loc = best_hub if best_ratio >= best_lz_ratio else best_lz

        if best_loc and max_ratio > 1.5:
            solar_str = ""
            if not np.isnan(a.get("solar_event", np.nan)):
                solar_str = f"  Solar: {a.get('solar_event', 0):.0f} MWh"
            log(f"  {a['icao']} {time_str} | {best_loc} {max_ratio:.1f}x{solar_str}")


if __name__ == "__main__":
    main()
