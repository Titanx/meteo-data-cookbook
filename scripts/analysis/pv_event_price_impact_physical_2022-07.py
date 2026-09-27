"""2022-07 光伏缺口事件价格冲击: 物理口径统一版 (P50/P90/P99 情景)

背景: PS-022/023 的 2022 推演用物理晴空反事实, 但弹性标定用 P95 包络 -> 口径不一致。
      本脚本改用同口径(物理晴空)的 2025/2026 弹性重新推演, 并与 P95 口径对比。
输入: data/nsrdb/pv_counterfactual_hourly_2022-07.csv   (PS-022 晴空反事实, 含 shortfall)
      data/ercot/shortfall_definition_comparison.csv     (两口径分位弹性)
输出: stdout + data/nsrdb/pv_event_price_impact_physical_2022-07.csv
"""
import numpy as np
import pandas as pd

D = r"c:\work\meteo\data"
SRC = rf"{D}\nsrdb\pv_counterfactual_hourly_2022-07.csv"
CMP = rf"{D}\ercot\shortfall_definition_comparison.csv"
OUT = rf"{D}\nsrdb\pv_event_price_impact_physical_2022-07.csv"
BASE_PRICE = 182.0
HEATWAVE = pd.date_range("2022-07-13", "2022-07-18")
TAUS = [0.50, 0.90, 0.99]


def betas(defn):
    c = pd.read_csv(CMP)
    out = {}
    for t in TAUS:
        v = c[(c["definition"] == defn) &
              (c["item"] == f"q{int(t*100)}_pct_per_gw")]["value"]
        out[t] = float(v.mean()) / 100.0
    o = c[(c["definition"] == defn) &
          (c["item"] == "ols_mean_pct_per_gw")]["value"]
    out["ols"] = float(o.mean()) / 100.0
    return out


def main():
    b_phys = betas("物理晴空")
    b_p95 = betas("P95 包络")
    print("弹性 (2025+2026 平均, %/GW):")
    print(f"  {'口径':<10s}{'OLS均值':>9s}{'Q50':>8s}{'Q90':>8s}{'Q99':>8s}")
    for lab, b in (("物理晴空", b_phys), ("P95包络", b_p95)):
        print(f"  {lab:<10s}{b['ols']*100:>9.2f}{b[0.5]*100:>8.2f}"
              f"{b[0.9]*100:>8.2f}{b[0.99]*100:>8.2f}")

    df = pd.read_csv(SRC, index_col=0, parse_dates=True)
    ev = df[(df["shortfall"] >= 1500) & (df.index.hour >= 15)
            & (df.index.hour <= 23)].copy()
    print(f"\n事件小时 {len(ev)} 个, 缺电 {ev['shortfall'].sum()/1000:.1f} GWh")

    rows = []
    for t, r in ev.iterrows():
        sw = r["shortfall"] / 1000.0
        rec = {"time_utc": t, "shortfall_mw": r["shortfall"],
               "demand_mw": r["demand"]}
        for tau in TAUS:
            for lab, b in (("phys", b_phys), ("p95", b_p95)):
                up = (np.exp(b[tau] * sw) - 1) * 100.0
                rec[f"up_{lab}_p{int(tau*100)}"] = up
        rec["up_phys_ols"] = (np.exp(b_phys["ols"] * sw) - 1) * 100.0
        rows.append(rec)
    e = pd.DataFrame(rows).set_index("time_utc")
    hw = e.index.normalize().isin(HEATWAVE)

    print(f"\n{'时刻UTC':<15s}{'缺口GW':>8s}{'需求GW':>7s}"
          f"{'物理P50':>8s}{'物理P90':>8s}{'物理P99':>8s}{'P95口径P99':>11s}")
    for t, r in e.iterrows():
        tag = " 热浪" if t.normalize() in HEATWAVE else ""
        print(f"{t.strftime('%m-%d %H:%M'):<15s}{r['shortfall_mw']/1000:>8.2f}"
              f"{r['demand_mw']/1000:>7.1f}{r['up_phys_p50']:>8.1f}"
              f"{r['up_phys_p90']:>8.1f}{r['up_phys_p99']:>8.1f}"
              f"{r['up_p95_p99']:>11.1f}{tag}")

    print(f"\n=== 汇总 ({len(e)} 事件小时, 热浪 {hw.sum()}) ===")
    for lab, name in (("phys", "物理口径(推荐)"), ("p95", "P95包络口径")):
        print(f"  [{name}]")
        for tau in TAUS:
            c = f"up_{lab}_p{int(tau*100)}"
            print(f"    P{int(tau*100):<3d}: 中位 +{e[c].median():.1f}%  "
                  f"最大 +{e[c].max():.1f}%  | 按 $182 折算 中位 "
                  f"+${BASE_PRICE*e[c].median()/100:.0f} 最大 "
                  f"+${BASE_PRICE*e[c].max()/100:.0f} /MWh")
    sw = e["shortfall_mw"] / 1000
    print(f"\n  缺口: 中位 {sw.median():.2f} GW, 最大 {sw.max():.2f} GW "
          f"({sw.idxmax().strftime('%m-%d %H:%M')})")
    print(f"  PS-022 参考: 中位 +11.0%, 最大 +25.0%")
    if hw.sum():
        h = e[hw]
        print(f"  热浪期 ({len(h)} 事件, {h['shortfall_mw'].sum()/1000:.1f} GWh): "
              f"物理 P50 中位 +{h['up_phys_p50'].median():.1f}% / "
              f"P99 中位 +{h['up_phys_p99'].median():.1f}% "
              f"(最大 +{h['up_phys_p99'].max():.1f}%)")

    e.to_csv(OUT)
    print(f"\n已保存: {OUT}")


if __name__ == "__main__":
    main()
