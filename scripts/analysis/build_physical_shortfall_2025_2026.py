"""物理晴空反事实缺口 vs P95 数据驱动包络缺口 (2025/2026 ERCOT)

目的: PS-023 发现 P95 包络口径在低太阳高度角虚高(大缺口落清晨/黄昏),
      致缺口与尖峰边际负相关(辛普森悖论)。本脚本用与 PS-022(2022-07) 完全
      相同的物理晴空反事实替代包络, 统一两个场景的缺口径, 并对比两种口径。
校准: 与 PS-022 一致 —— 逐小时偏移 = 该小时 (反事实 - 实际) 的 5% 分位
      (最晴 5% 小时视为无云, 其差值即系统性偏差, 自动吸收装机清单不完整)
用法: python scripts/analysis/build_physical_shortfall_2025_2026.py
输出: data/ercot/shortfall_physical_2025_2026.csv
"""
import numpy as np
import pandas as pd

CS = r"c:\work\meteo\data\nsrdb\pv_clearsky_hourly_2025_2026.csv"
PANEL = {2025: r"c:\work\meteo\data\ercot\ercot_hourly_panel_2025.csv",
         2026: r"c:\work\meteo\data\ercot\ercot_hourly_panel_2026.csv"}
OUT = r"c:\work\meteo\data\ercot\shortfall_physical_2025_2026.csv"


def main():
    cs = pd.read_csv(CS, index_col=0, parse_dates=True)
    cs.index = pd.to_datetime(cs.index, utc=True).tz_localize(None)
    cs = cs[~cs.index.duplicated(keep="first")]
    print(f"晴空反事实 {len(cs)} 小时, 峰值 {cs['clearsky_mw'].max():.0f} MW")

    out = []
    for year, path in PANEL.items():
        p = pd.read_csv(path, index_col=0, parse_dates=True)
        p.index = pd.to_datetime(p.index)
        m = p.join(cs, how="inner")
        m = m[m["solar"] > 50].copy()
        raw = m["clearsky_mw"] - m["solar"]
        off_h = raw.groupby(m.index.hour).quantile(0.05)
        m["shortfall_phys"] = (raw - off_h.reindex(m.index.hour).values) \
            .clip(lower=0)
        m["raw_gap"] = raw
        m["year"] = year
        print(f"\n{year}: {len(m)} 白天小时")
        print(f"  EIA 峰值 {m['solar'].max():.0f} vs 反事实峰值 "
              f"{m['clearsky_mw'].max():.0f} MW (比值 "
              f"{m['solar'].max()/m['clearsky_mw'].max():.3f})")
        print(f"  逐小时偏移 (UTC): " + ", ".join(
            f"{h:02d}:{v:+.0f}" for h, v in off_h.items()))
        print(f"  偏移/反事实(该小时中位) 比: " + ", ".join(
            f"{h:02d}:{off_h[h]/m.loc[m.index.hour==h,'clearsky_mw'].median():+.2%}"
            for h in sorted(off_h.index)))
        print(f"  缺口 (物理): 中位 {m['shortfall_phys'].median():.0f}, "
              f"P95 {m['shortfall_phys'].quantile(0.95):.0f} MW")
        print(f"  缺口 (P95包络): 中位 {m['shortfall'].median():.0f}, "
              f"P95 {m['shortfall'].quantile(0.95):.0f} MW")
        # 低太阳高度角时段占比 (清晨/黄昏 15-16 与 00-02 UTC)
        print(f"  夏季 22-02 UTC 时段占比: 物理 {100*((m.index.hour>=22)|(m.index.hour<=2)).mean():.0f}%")
        out.append(m[["year", "solar", "wind", "demand", "rtm", "dam",
                      "clearsky_mw", "raw_gap", "shortfall_phys", "shortfall"]])

    df = pd.concat(out)
    df.index.name = "time_utc"
    df.to_csv(OUT)
    print(f"\n已保存: {OUT} ({len(df)} 行)")


if __name__ == "__main__":
    main()
