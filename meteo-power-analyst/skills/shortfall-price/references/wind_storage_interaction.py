"""风电缺口弹性跨年结构 + 储能交互 (2025-01 ~ 2026-09, PS-028 跨年检验 + PS-045 联动)

动机: PS-028 三结论在 9/30 刷新数据下复算全部保持 (缺口 -2.80/-3.18, 低风异常
+7.37/+7.43, 控制实际风电后 ≈ 0)。本脚本回答其后的结构问题:

  A. 季节结构: 风电缺口/低风异常弹性是否有光伏那样的年内形状? 同季跨年漂移多大?
  B. 储能交互: 容量扩张 (3.1→9.9 GW) 是否削弱"弃风→低价"传导 / "低风→高价"传导?
  C. 事件机制: 高弃风/低风异常事件的储能净响应两年如何变化 (对照 PS-045 云冲击翻负)?
  D. 负价结构: 高弃风小时负价占比 13.2%→11.6% 的下降是需求还是储能吸收?
  E. 价差分解: ln(RTM/DAM) 口径下弃风 (DAM 部分可见) 与低风异常 (不可见) 的传导差异。

输入: data/ercot/wind_power_hourly_2025_2026.csv (PS-028 口径的 w_short/w_drought),
      data/ercot/battery_attribution_panel.csv (PS-045 的 bat_net/bat_dis/cap_mw)
输出: data/ercot/wind_storage_results.csv + 控制台全量结果
"""
import numpy as np
import pandas as pd

WH = r"c:\work\meteo\data\ercot\wind_power_hourly_2025_2026.csv"
BP = r"c:\work\meteo\data\ercot\battery_attribution_panel.csv"
OUT = r"c:\work\meteo\data\ercot\wind_storage_results.csv"
ROWS = []


def rec(section, item, est=None, se=None, n=None, note=""):
    ROWS.append({"section": section, "item": item,
                 "estimate": est, "se": se, "n": n, "note": note})
    if est is None:
        print(f"  {item}  {note}")
    else:
        se_s = f" (SE {se:.3f})" if se is not None and se == se else ""
        print(f"  {item}  {est:+.3f}{se_s}  n={n}  {note}")


def ols(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
    return beta, np.sqrt(np.diag(cov))


def hour_month_fe(idx):
    h = pd.get_dummies(idx.hour, prefix="h", drop_first=True).astype(float)
    m = pd.get_dummies(idx.month, prefix="m", drop_first=True).astype(float)
    return pd.concat([h, m], axis=1).values


def fit_elastic(d, cols):
    lnp = np.log(d["rtm"].clip(lower=1)).values
    X = np.column_stack([np.ones(len(d))] + [d[c].values / 1000.0 for c in cols]
                        + [hour_month_fe(d.index)])
    beta, se = ols(X, lnp)
    names = ["const"] + cols
    return {n: (b * 100, s * 100) for n, b, s in zip(names, beta, se)}  # %/GW


def fit_spread(d, cols):
    sp = np.log((d["rtm"] / d["dam"]).clip(lower=0.02, upper=50)).values
    X = np.column_stack([np.ones(len(d))] + [d[c].values / 1000.0 for c in cols]
                        + [hour_month_fe(d.index)])
    beta, se = ols(X, sp)
    names = ["const"] + cols
    return {n: (b * 100, s * 100) for n, b, s in zip(names, beta, se)}


def same_hour_baseline(df, mask_event, col):
    """事件小时的储能净响应 = col − 同 hour-of-day ±30 天非事件小时中位数"""
    out = pd.Series(np.nan, index=df.index)
    for ts in df.index[mask_event]:
        lo = ts - pd.Timedelta(days=30)
        hi = ts + pd.Timedelta(days=30)
        base = df.loc[lo:hi]
        base = base[(base.index.hour == ts.hour) & (~mask_event.reindex(base.index, fill_value=False))]
        if len(base) >= 10 and base[col].notna().all():
            out.loc[ts] = df.loc[ts, col] - base[col].median()
    return out


def main():
    wh = pd.read_csv(WH, index_col=0, parse_dates=True)
    bp = pd.read_csv(BP, index_col=0, parse_dates=True)
    df = wh.join(bp[["bat_net", "bat_dis", "cap_mw"]], how="left")
    df["year"] = df.index.year
    df["quarter"] = df.index.quarter
    df["lnp"] = np.log(df["rtm"].clip(lower=1))
    print(f"样本 {df.index.min()} ~ {df.index.max()}  n={len(df)}")

    # ---------- A. 季度弹性路径 ----------
    print("\n== A. 季度弹性路径 (%/GW, hour+month FE) ==")
    for (y, q), d in df.groupby(["year", "quarter"]):
        r = fit_elastic(d, ["w_short", "w_drought", "demand"])
        rec("A_quarter", f"{y}Q{q}_w_short", r["w_short"][0], r["w_short"][1], len(d))
        rec("A_quarter", f"{y}Q{q}_w_drought", r["w_drought"][0], r["w_drought"][1], len(d))

    print("\n== A2. 同季跨年漂移 (PS-045 口径: Q1-Q3 池化, 季度×缺口 FE + 年份指示) ==")
    dd = df[df["quarter"] <= 3].dropna(subset=["w_short", "w_drought"]).copy()
    dd["i_y26"] = (dd["year"] == 2026).astype(float)
    for var in ("w_short", "w_drought"):
        d = dd.copy()
        d["x_y26"] = d[var] * d["i_y26"]
        d["x_Q2"] = d[var] * (d["quarter"] == 2)
        d["x_Q3"] = d[var] * (d["quarter"] == 3)
        r = fit_elastic(d, [var, "demand", "x_y26", "i_y26", "x_Q2", "x_Q3"])
        b, s = r["x_y26"]
        rec("A_drift", f"{var}_season_matched_drift", b, s, len(d),
            "2026 vs 2025 同季漂移, 显著" if abs(b) > 1.96 * s else "不显著")

    # ---------- G. 分季机制诊断 (解释弃风弹性的季节形状) ----------
    print("\n== G. 分季机制诊断: w_short 的构成随季节怎么变 ==")
    for (y, q), d in df.groupby(["year", "quarter"]):
        rec("G_diag", f"{y}Q{q}_corr_ws_wd", d["w_short"].corr(d["w_drought"]) * 100,
            None, len(d), "corr(w_short,w_drought) %")
        rec("G_diag", f"{y}Q{q}_corr_ws_dem", d["w_short"].corr(d["demand"]) * 100,
            None, len(d), "corr(w_short,demand) %")
        rec("G_diag", f"{y}Q{q}_ws_mean", d["w_short"].mean(), None, len(d),
            f"w_short 均值 MW | w_drought 均值 {d['w_drought'].mean():.0f}")

    # ---------- B. 储能容量交互 ----------
    print("\n== B. 容量交互 (cap_gw = 90 天放电 P99 容量代理; 池化 + 分年) ==")
    pooled = df.dropna(subset=["cap_mw"]).copy()
    pooled["cap_gw"] = pooled["cap_mw"] / 1000.0
    for var in ("w_short", "w_drought"):
        d = pooled.copy()
        d["x_cap"] = d[var] / 1000.0 * d["cap_gw"]
        r = fit_elastic(d, [var, "demand", "x_cap", "cap_gw"])
        b, s = r["x_cap"]
        sd = d["cap_gw"].std()
        rec("B_cap_inter", f"pooled_{var}_x_cap", b, s, len(d),
            f"%/GW per +1GW 容量 | cap SD {sd:.1f} GW ⇒ +1SD 弹性变化 {b*sd:+.2f} %/GW")
    for year in (2025, 2026):
        d = pooled[pooled["year"] == year].copy()
        for var in ("w_short", "w_drought"):
            r = fit_elastic(d, [var, "demand"])
            rec("B_cap_inter", f"{year}_{var}_base", r[var][0], r[var][1], len(d),
                "当年基准弹性")

    # ---------- C. 事件机制 ----------
    print("\n== C1. 高弃风事件 (w_short ≥ 逐年 P90) 的储能净响应 (MW) ==")
    for year in (2025, 2026):
        d = df[df["year"] == year].dropna(subset=["bat_net"])
        thr = d["w_short"].quantile(0.9)
        m = d["w_short"] >= thr
        resp = same_hour_baseline(d, m, "bat_net")
        rt = same_hour_baseline(d, m, "lnp")
        ok = resp.notna()
        rec("C_curtail_event", f"{year}_net_resp_median", resp[ok].median(), None,
            int(ok.sum()), f"阈值 {thr:.0f} MW")
        rec("C_curtail_event", f"{year}_lnp_premium_median", (np.exp(rt[ok].median()) - 1) * 100,
            None, int(ok.sum()), "RTM 溢价 % (ln 中位还原)")

    print("\n== C2. 低风异常事件 (w_drought ≥ 6 GW, 全天任意时) 的储能净响应 (MW) ==")
    for year in (2025, 2026):
        d = df[df["year"] == year].dropna(subset=["bat_net"])
        m = d["w_drought"] >= 6000
        resp = same_hour_baseline(d, m, "bat_net")
        ok = resp.notna()
        rec("C_drought_event", f"{year}_net_resp_median", resp[ok].median(), None,
            int(ok.sum()), f"事件小时 {int(m.sum())}")
        # 绝对放电水平
        ev = d[m]
        rec("C_drought_event", f"{year}_abs_net_median", ev["bat_net"].median(), None,
            len(ev), "事件小时净出力中位")
        rec("C_drought_event", f"{year}_abs_dis_median", ev["bat_dis"].median(), None,
            len(ev), "事件小时放电中位")
        rec("C_drought_event", f"{year}_resp_per_cap_pct",
            resp[ok].median() / ev["cap_mw"].median() * 100, None, len(ev),
            "净响应中位 / 容量代理中位 %")

    print("\n== C3. 高弃风事件储能净响应按容量分半 (2026 上/下半年) ==")
    d26 = df[(df["year"] == 2026)].dropna(subset=["bat_net"])
    mid = d26.index[len(d26) // 2]
    for label, part in (("H1", d26[d26.index < mid]), ("H2", d26[d26.index >= mid])):
        thr = part["w_short"].quantile(0.9)
        m = part["w_short"] >= thr
        resp = same_hour_baseline(part, m, "bat_net")
        ok = resp.notna()
        rec("C_curtail_h1h2", f"2026{label}_net_resp_median", resp[ok].median() if ok.any() else np.nan,
            None, int(ok.sum()), f"cap~{part['cap_mw'].median()/1000:.1f} GW")

    # ---------- D. 负价结构 ----------
    print("\n== D. 高弃风小时负价占比: 需求分层 × 年份 (负价 = RTM < $5) ==")
    def dbin(v):
        if v < 45000:
            return "<45GW"
        if v < 55000:
            return "45-55GW"
        return ">55GW"
    for year in (2025, 2026):
        d = df[df["year"] == year].dropna(subset=["bat_net"])
        thr = d["w_short"].quantile(0.9)
        hi = d["w_short"] >= thr
        for b in ("<45GW", "45-55GW", ">55GW"):
            for flag, tag in ((True, "hi"), (False, "lo")):
                m = (d["demand"].map(dbin) == b) & (hi == flag)
                s = d[m]
                if len(s) >= 20:
                    rec("D_negprice", f"{year}_{tag}_{b}",
                        (s["rtm"] < 5).mean() * 100, None, len(s),
                        f"RTM中位 {s['rtm'].median():.1f}")

    # ---------- E. 价差分解 ----------
    print("\n== E. 价差弹性 ln(RTM/DAM) (%/GW, hour+month FE) ==")
    d = df.dropna(subset=["dam"])
    d = d[d["dam"] > 0]
    for year in (2025, 2026):
        dy = d[d["year"] == year]
        for var in ("w_short", "w_drought"):
            r = fit_spread(dy, [var, "demand"])
            rec("E_spread", f"{year}_{var}", r[var][0], r[var][1], len(dy))

    print("\n== E2. 价差弹性分季 (仅 w_drought, 外生缺口) ==")
    for (y, q), dy in d[d["year"] >= 2025].groupby(["year", "quarter"]):
        if len(dy) < 400:
            continue
        r = fit_spread(dy, ["w_drought", "demand"])
        rec("E_spread_q", f"{y}Q{q}_w_drought", r["w_drought"][0], r["w_drought"][1], len(dy))

    # ---------- F. 联合: 光伏缺口 × 低风异常 (白天小时, 外生×外生) ----------
    print("\n== F. 风光联合外生缺口 (白天 14-23 UTC) ==")
    dd = df.join(bp[["shortfall"]].rename(columns={"shortfall": "pv_short"}),
                 how="inner")
    dd = dd[dd.index.hour.isin(range(14, 24))].dropna(subset=["pv_short"])
    for year in (2025, 2026):
        dy = dd[dd["year"] == year]
        if len(dy) < 500:
            continue
        r = fit_elastic(dy, ["pv_short", "w_drought", "demand"])
        rec("F_joint", f"{year}_pv_short", r["pv_short"][0], r["pv_short"][1], len(dy))
        rec("F_joint", f"{year}_w_drought", r["w_drought"][0], r["w_drought"][1], len(dy))

    out = pd.DataFrame(ROWS)
    out.to_csv(OUT, index=False)
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
