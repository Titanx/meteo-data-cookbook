"""2022-07 光伏缺口事件的价格冲击: 分位情景推演 (改进 PS-022 单一均值外推)

改进点 (PS-022 -> 本脚本):
  PS-022 用单一条件均值弹性 β=+5.08 %/GW 给一个上浮数字;
  本脚本改用【分位数弹性曲线】β(tau), tau=.5/.9/.99, 给出:
    - 中位情景 (tau=0.5): 典型小时的价格响应
    - 上沿情景 (tau=0.9): 紧张小时
    - 极端情景 (tau=0.99): 尖峰小时
  弹性取 2025+2026 两年平均 (尾部两年一致 ±10%), 消除单年噪声。

输入: data/nsrdb/pv_counterfactual_hourly_2022-07.csv  (PS-022 晴空反事实, 含 shortfall)
      data/ercot/price_elasticity_tail.csv               (分位数弹性标定)
输出: stdout + data/nsrdb/pv_event_price_impact_tail_2022-07.csv
"""
import numpy as np
import pandas as pd

D = r"c:\work\meteo\data"
SRC = rf"{D}\nsrdb\pv_counterfactual_hourly_2022-07.csv"
ELAS = rf"{D}\ercot\price_elasticity_tail.csv"
OUT = rf"{D}\nsrdb\pv_event_price_impact_tail_2022-07.csv"

BASE_PRICE = 182.0            # 2022-07 ERCOT North 月均 $/MWh (EIA TODAY IN ENERGY)
HEATWAVE = pd.date_range("2022-07-13", "2022-07-18")
TAUS = [0.50, 0.90, 0.99]
# 极端小时价格水平的经验放大倍数 (2025/2026 白天样本 rtm_max q99 / q50)
PEAK_MULT = 6.5


def load_betas():
    e = pd.read_csv(ELAS)
    q = e[e["model"] == "qreg15"]
    out = {}
    for t in TAUS:
        s = q[q["param"] == f"sf_q{t}"]["estimate"]
        out[t] = float(s.mean()) / 100.0          # %/GW -> ln/GW
        out[f"n{t}"] = int(s.size)
    return out


def main():
    df = pd.read_csv(SRC, index_col=0, parse_dates=True)
    b = load_betas()
    print("分位数弹性 (2025+2026 平均, ln/GW -> %/GW):")
    for t in TAUS:
        print(f"  tau={t:<5} {b[t]*100:+.2f} %/GW")

    ev = df[(df["shortfall"] >= 1500) & (df.index.hour >= 15)
            & (df.index.hour <= 23)].copy()
    print(f"\n事件小时 (缺口>=1.5GW, 15-23UTC): {len(ev)} 个, "
          f"缺电 {ev['shortfall'].sum()/1000:.1f} GWh")

    rows = []
    for t, r in ev.iterrows():
        sw = r["shortfall"] / 1000.0
        rec = {"time_utc": t, "eia_mw": r["eia"], "clearsky_mw": r["cs"],
               "shortfall_mw": r["shortfall"], "demand_mw": r["demand"]}
        for tau in TAUS:
            up = (np.exp(b[tau] * sw) - 1) * 100.0
            rec[f"uplift_p{int(tau*100)}"] = up
            rec[f"usd_p{int(tau*100)}"] = BASE_PRICE * up / 100.0
        rows.append(rec)
    ev2 = pd.DataFrame(rows).set_index("time_utc")
    hw = ev2.index.normalize().isin(HEATWAVE)

    print(f"\n{'时刻UTC':<15s}{'实际':>7s}{'晴空':>7s}{'缺口GW':>8s}{'需求GW':>7s}"
          f"{'P50%':>7s}{'P90%':>7s}{'P99%':>7s}{'P99 $':>8s}")
    for t, r in ev2.iterrows():
        tag = " 热浪" if t.normalize() in HEATWAVE else ""
        print(f"{t.strftime('%m-%d %H:%M'):<15s}{r['eia_mw']:>7.0f}"
              f"{r['clearsky_mw']:>7.0f}{r['shortfall_mw']/1000:>8.2f}"
              f"{r['demand_mw']/1000:>7.1f}{r['uplift_p50']:>7.1f}"
              f"{r['uplift_p90']:>7.1f}{r['uplift_p99']:>7.1f}"
              f"{r['usd_p99']:>8.0f}{tag}")

    print(f"\n=== 汇总 ({len(ev2)} 事件小时, 热浪期 {hw.sum()}) ===")
    for tau in TAUS:
        c = f"uplift_p{int(tau*100)}"
        u = f"usd_p{int(tau*100)}"
        print(f"  tau={tau:<5}: 上浮 中位 +{ev2[c].median():.1f}% "
              f"最大 +{ev2[c].max():.1f}% | 按 $182 折算 中位 "
              f"+${ev2[u].median():.0f} 最大 +${ev2[u].max():.0f} /MWh")
    sw = ev2["shortfall_mw"] / 1000.0
    print(f"\n  缺口: 中位 {sw.median():.2f} GW, 最大 {sw.max():.2f} GW "
          f"({sw.idxmax().strftime('%m-%d %H:%M')})")
    print(f"  极端小时价格锚 (月均 ${BASE_PRICE:.0f} x {PEAK_MULT}) ~ "
          f"${BASE_PRICE*PEAK_MULT:.0f}/MWh")
    print(f"  PS-022 均值口径对照: 中位 +11.0%, 最大 +25.0%")

    # 热浪期单独汇总
    if hw.sum():
        h = ev2[hw]
        print(f"\n  热浪期 (07-13~18, {len(h)} 事件, "
              f"缺电 {h['shortfall_mw'].sum()/1000:.1f} GWh):")
        print(f"    上浮 P50 中位 +{h['uplift_p50'].median():.1f}% | "
              f"P90 中位 +{h['uplift_p90'].median():.1f}% | "
              f"P99 中位 +{h['uplift_p99'].median():.1f}% "
              f"(最大 +{h['uplift_p99'].max():.1f}%)")

    ev2.to_csv(OUT)
    print(f"\n已保存: {OUT}")


if __name__ == "__main__":
    main()
