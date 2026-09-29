"""NSRDB+pvlib 模型出力 vs EIA 实际出力深入对比 (ERCOT, 2022-07)
输入: data/nsrdb/ercot_pv_power_2022-07.csv (hourly, pvlib_mw / eia_mw)
分析: 昼夜平均曲线 / 日能量相关 / 偏差最大事件 / 爬坡率分布
用法: python skills/pv-power-model/references/nsrdb_eia_comparison.py
"""
import numpy as np
import pandas as pd

CSV = r"c:\work\meteo\data\nsrdb\ercot_pv_power_2022-07.csv"
OUT = r"c:\work\meteo\data\nsrdb\nsrdb_eia_comparison_summary.md"


def main():
    df = pd.read_csv(CSV, index_col=0, parse_dates=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.columns = ["model", "eia"]
    df["hour_local"] = df.index.hour - 5  # CDT

    lines = ["# NSRDB+pvlib 模型 vs EIA 实际 (ERCOT 光伏, 2022-07)", ""]

    # 1. 昼夜平均曲线 (鸭子曲线形状)
    diurnal = df.groupby("hour_local")[["model", "eia"]].mean()
    lines.append("## 1. 昼夜平均出力曲线 (CDT, MW)")
    lines.append("| 时段 | 模型 | EIA | 偏差 |")
    lines.append("|---|---|---|---|")
    for h, row in diurnal.iterrows():
        if row["model"] > 50 or row["eia"] > 50:
            lines.append(f"| {h:02d} | {row['model']:.0f} | {row['eia']:.0f} | "
                         f"{row['model']-row['eia']:+.0f} |")
    shape_r = diurnal["model"].corr(diurnal["eia"])
    lines.append(f"\n昼夜曲线形状相关: r={shape_r:.4f}\n")

    # 2. 日能量相关
    daily = df[["model", "eia"]].resample("1D").sum() / 1000  # GWh
    daily_r = daily["model"].corr(daily["eia"])
    daily_mae = (daily["model"] - daily["eia"]).abs().mean()
    daily_bias = (daily["model"] - daily["eia"]).mean()
    lines.append("## 2. 日能量 (GWh)")
    lines.append(f"- 日能量相关: r={daily_r:.4f}")
    lines.append(f"- 日能量 MAE: {daily_mae:.2f} GWh | 平均偏差: {daily_bias:+.2f} GWh")
    lines.append(f"- 模型 31 天总量 {daily['model'].sum():.1f} vs EIA {daily['eia'].sum():.1f} GWh\n")

    # 3. 偏差最大的 10 个小时 (绝对偏差)
    df["dev"] = df["model"] - df["eia"]
    df["dev_pct"] = 100 * df["dev"] / df["eia"].replace(0, np.nan)
    worst = df.reindex(df["dev"].abs().sort_values(ascending=False).index).head(10)
    lines.append("## 3. 偏差最大的 10 个小时")
    lines.append("| UTC 时间 | 模型 MW | EIA MW | 偏差 MW | 偏差% |")
    lines.append("|---|---|---|---|---|")
    for t, row in worst.iterrows():
        lines.append(f"| {t.strftime('%m-%d %H:%M')} | {row['model']:.0f} | "
                     f"{row['eia']:.0f} | {row['dev']:+.0f} | "
                     f"{row['dev_pct']:+.1f}% |")

    # 4. 爬坡率分布 (1h)
    m_ramp = df["model"].diff().dropna()
    e_ramp = df["eia"].diff().dropna()
    lines.append("\n## 4. 1 小时爬坡率 (MW/h)")
    lines.append(f"- 模型 P95 |爬坡|: {m_ramp.abs().quantile(0.95):.0f} | "
                 f"EIA: {e_ramp.abs().quantile(0.95):.0f}")
    lines.append(f"- 模型最大 |爬坡|: {m_ramp.abs().max():.0f} | "
                 f"EIA: {e_ramp.abs().max():.0f}")
    lines.append(f"- 爬坡相关: r={m_ramp.corr(e_ramp):.4f}")

    # 5. 高出力时段 (EIA > 6 GW) 精度
    hi = df[df["eia"] > 6000]
    lines.append("\n## 5. 高出力时段 (EIA>6GW) 精度")
    if len(hi) > 5:
        lines.append(f"- 样本 {len(hi)} h | 相关 r={hi['model'].corr(hi['eia']):.4f} | "
                     f"MAE {abs(hi['model']-hi['eia']).mean():.0f} MW | "
                     f"平均偏差 {(hi['model']-hi['eia']).mean():+.0f} MW")

    # 6. 事件日分析: 模型-实际日能量偏差最大与最小的 3 天
    daily["dev"] = daily["model"] - daily["eia"]
    lines.append("\n## 6. 日能量偏差极值日")
    for tag, sub in [("模型高估最重", daily.nlargest(3, "dev")),
                     ("模型低估最重", daily.nsmallest(3, "dev"))]:
        lines.append(f"**{tag}**")
        for t, row in sub.iterrows():
            lines.append(f"- {t.date()}: 模型 {row['model']:.2f} vs 实际 "
                         f"{row['eia']:.2f} GWh ({row['dev']:+.2f})")

    text = "\n".join(lines)
    print(text)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\n已保存: {OUT}")


if __name__ == "__main__":
    main()
