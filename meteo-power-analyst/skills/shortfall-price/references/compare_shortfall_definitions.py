"""缺口径对比: 物理晴空反事实 vs P95 数据驱动包络 (2025/2026)

背景: PS-022 对 2022-07 用物理晴空反事实, 但对 2025/2026 弹性标定用 P95 包络,
      两者口径不一致; PS-023 发现 P95 包络在低太阳高度角虚高, 致缺口与尖峰
      边际负相关(辛普森悖论)。本脚本用同一回归框架对比两种缺口定义。
对比项: (1) OLS 小时均值弹性  (2) Q50/Q99 分位弹性  (3) 尾部概率 GLM
        (4) 分箱尖峰率 (检验辛普森悖论是否消失)
用法: python skills/shortfall-price/references/compare_shortfall_definitions.py
输出: stdout + data/ercot/shortfall_definition_comparison.csv
"""
import os
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.tools.sm_exceptions import IterationLimitWarning

warnings.simplefilter("ignore", IterationLimitWarning)

D = r"c:\work\meteo\data\ercot"
SF = os.path.join(D, "shortfall_physical_2025_2026.csv")
RTM = os.path.join(D, "ercot_rtm_HB_HOUSTON_2025-01-01_2026-09-07.csv")
OUT = os.path.join(D, "shortfall_definition_comparison.csv")
DEFS = [("物理晴空", "sf_phys"), ("P95 包络", "sf_p95")]
ROWS = []


def rec(year, defn, item, value, se=np.nan, n=0):
    ROWS.append({"year": year, "definition": defn, "item": item,
                 "value": value, "se": se, "n": n})


def main():
    df = pd.read_csv(SF, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index)
    df["sf_phys"] = df["shortfall_phys"] / 1000.0
    df["sf_p95"] = df["shortfall"] / 1000.0
    df["wind"] = df["wind"] / 1000.0
    df["dem"] = df["demand"] / 1000.0
    df["hour"] = df.index.hour
    df["month"] = df.index.month

    rtm = pd.read_csv(RTM)
    t = pd.to_datetime(rtm["interval_start_utc"]).dt.tz_convert("UTC") \
        .dt.tz_localize(None)
    r15 = pd.Series(rtm["spp"].astype(float).values, index=t).sort_index()
    hm = r15.resample("1h").mean()
    hx = r15.resample("1h").max()

    for year in (2025, 2026):
        d = df[df["year"] == year].copy()
        d["rtm_mean"] = hm.reindex(d.index)
        d["rtm_max"] = hx.reindex(d.index)
        d = d.dropna(subset=["rtm_mean", "rtm_max"])
        d["lnp"] = np.log(d["rtm_mean"].clip(lower=1))
        print(f"\n{'='*78}\n{year}: {len(d)} 白天小时")
        for defn, col in DEFS:
            nz = (d[col] > 0).mean()
            print(f"\n[{defn}] 缺口>0 占比 {nz*100:.0f}%, 中位 {d[col].median():.2f} GW, "
                  f"P95 {d[col].quantile(0.95):.2f} GW")
            # (1) OLS 小时均值
            f = f"lnp ~ {col} + wind + dem + C(hour) + C(month)"
            ols = smf.ols(f, d).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
            b = ols.params[col] * 100
            print(f"   OLS 条件均值: {b:+.2f} %/GW (SE {ols.bse[col]*100:.2f})")
            rec(year, defn, "ols_mean_pct_per_gw", b, ols.bse[col] * 100, len(d))
            # (2) 分位
            for tq in (0.5, 0.9, 0.99):
                r = smf.quantreg(f, d).fit(q=tq, max_iter=3000, p_tol=1e-6)
                print(f"   Q{int(tq*100):<2d}: {r.params[col]*100:+.2f} %/GW "
                      f"(SE {r.bse[col]*100:.2f})", end="")
                rec(year, defn, f"q{int(tq*100)}_pct_per_gw",
                    r.params[col] * 100, r.bse[col] * 100, len(d))
            print()
            # (3) 尾部概率 GLM (小时极值 > q99)
            thr = float(d["rtm_max"].quantile(0.99))
            d2 = d.assign(tail=(d["rtm_max"] > thr).astype(int))
            gl = smf.glm(f"tail ~ {col} + wind + dem + C(hour) + C(month)",
                         data=d2, family=sm.families.Binomial()).fit()
            orr = np.exp(gl.params[col])
            print(f"   尾部概率 GLM: lnOR {gl.params[col]:+.3f} "
                  f"(SE {gl.bse[col]:.3f}) -> OR {orr:.3f}, 尖峰阈 ${thr:.0f}")
            rec(year, defn, "glm_lnOR", gl.params[col], gl.bse[col], len(d2))
            # (4) 分箱尖峰率 (检验辛普森悖论)
            print(f"   分箱尖峰率:", end="")
            for lo, hi in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 99)]:
                s = d2[(d2[col] >= lo) & (d2[col] < hi)]
                if len(s) < 30:
                    continue
                print(f"  {lo}~{hi}GW {s['tail'].mean()*100:.1f}%(n={len(s)})",
                      end="")
                rec(year, defn, f"tailrate_{lo}_{hi}", s["tail"].mean() * 100,
                    np.nan, len(s))
            print()

    t = pd.DataFrame(ROWS)
    t.to_csv(OUT, index=False)
    print(f"\n已保存: {OUT}")


if __name__ == "__main__":
    main()
