"""生成 ERCOT RTM 尾部尖峰弹性标定 HTML 报告 (自包含, 内嵌 SVG)
输入: price_elasticity_tail.csv / ercot_hourly_panel_{2025,2026}.csv /
      ercot_rtm_HB_HOUSTON_*.csv / pv_event_price_impact_tail_2022-07.csv
输出: output/price_tail_elasticity/ercot_rtm_tail_elasticity.html
用法: python scripts/analysis/build_price_tail_report.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data"
ELAS = os.path.join(D, "ercot", "price_elasticity_tail.csv")
PN = {2025: os.path.join(D, "ercot", "ercot_hourly_panel_2025.csv"),
      2026: os.path.join(D, "ercot", "ercot_hourly_panel_2026.csv")}
RTM = os.path.join(D, "ercot", "ercot_rtm_HB_HOUSTON_2025-01-01_2026-09-07.csv")
TAIL = os.path.join(D, "nsrdb", "pv_event_price_impact_tail_2022-07.csv")
OUT_DIR = r"c:\work\meteo\output\price_tail_elasticity"
OUT = os.path.join(OUT_DIR, "ercot_rtm_tail_elasticity.html")

C25, C26, C_MEAN = "#0969DA", "#BF3989", "#D29922"
C_P50, C_P90, C_P99 = "#2DA44E", "#0969DA", "#CF222E"
GRID, AXIS = "rgba(27,36,48,0.12)", "#64718A"
TAUS = [0.50, 0.75, 0.90, 0.95, 0.99, 0.995]


class Fig:
    """极简 SVG 折线/柱状绘图器"""

    def __init__(self, w, h, ml, mr, mt, mb, x0, x1, lo, hi, ylab=""):
        self.w, self.h, self.ml, self.mr, self.mt, self.mb = w, h, ml, mr, mt, mb
        self.pw, self.ph = w - ml - mr, h - mt - mb
        self.x0, self.x1, self.lo, self.hi = x0, x1, lo, hi
        self.s = [f'<svg viewBox="0 0 {w} {h}" role="img" '
                  f'style="width:100%;height:auto">']
        pad = (hi - lo) * 0.05
        self.plo, self.phi = lo - pad, hi + pad
        for frac in (0.25, 0.5, 0.75):
            yy = mt + self.ph * (1 - frac)
            self.s.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{w-mr}" '
                          f'y2="{yy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        self.s.append(f'<text x="{ml-6}" y="{mt-2}" font-size="11" '
                      f'fill="{AXIS}" text-anchor="end">{hi:.12g}</text>')
        self.s.append(f'<text x="{ml-6}" y="{mt+self.ph+10}" font-size="11" '
                      f'fill="{AXIS}" text-anchor="end">{lo:.12g}</text>')
        if ylab:
            self.s.append(f'<text x="{ml-42}" y="{mt+self.ph/2:.0f}" '
                          f'font-size="12" fill="{AXIS}" '
                          f'transform="rotate(-90 {ml-42} {mt+self.ph/2:.0f})">'
                          f'{ylab}</text>')

    def X(self, v):
        return self.ml + (v - self.x0) / (self.x1 - self.x0) * self.pw

    def Y(self, v):
        return self.mt + (1 - (v - self.plo) / (self.phi - self.plo)) * self.ph

    def band(self, x0, x1, fill):
        self.s.append(f'<rect x="{self.X(x0):.1f}" y="{self.mt}" '
                      f'width="{self.X(x1)-self.X(x0):.1f}" height="{self.ph}" '
                      f'fill="{fill}"/>')

    def hline(self, y, color, dash="4 4"):
        self.s.append(f'<line x1="{self.ml}" y1="{self.Y(y):.1f}" '
                      f'x2="{self.w-self.mr}" y2="{self.Y(y):.1f}" '
                      f'stroke="{color}" stroke-width="1.2" '
                      f'stroke-dasharray="{dash}"/>')

    def vline(self, x, color, dash="3 3"):
        self.s.append(f'<line x1="{self.X(x):.1f}" y1="{self.mt}" '
                      f'x2="{self.X(x):.1f}" y2="{self.mt+self.ph}" '
                      f'stroke="{color}" stroke-width="1.2" '
                      f'stroke-dasharray="{dash}"/>')

    def poly(self, xs, ys, color, width=2, dash=None, dot=False):
        pts = " ".join(f"{self.X(x):.1f},{self.Y(y):.1f}" for x, y in zip(xs, ys))
        dd = f' stroke-dasharray="{dash}"' if dash else ""
        self.s.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                      f'stroke-width="{width}" stroke-linejoin="round"{dd}/>')
        if dot:
            for x, y in zip(xs, ys):
                self.s.append(f'<circle cx="{self.X(x):.1f}" '
                              f'cy="{self.Y(y):.1f}" r="2.6" fill="{color}"/>')

    def dots(self, xs, ys, r, color, opacity=1):
        op = f' opacity="{opacity}"' if opacity < 1 else ""
        for x, y in zip(xs, ys):
            self.s.append(f'<circle cx="{self.X(x):.1f}" cy="{self.Y(y):.1f}" '
                          f'r="{r}" fill="{color}"{op}/>')

    def bars(self, xs, hs, bw, colors):
        for x, hv, c in zip(xs, hs, colors):
            y0, y1 = self.Y(0), self.Y(hv)
            self.s.append(f'<rect x="{self.X(x)-bw/2:.1f}" '
                          f'y="{min(y0,y1):.1f}" width="{bw:.1f}" '
                          f'height="{abs(y1-y0):.1f}" fill="{c}" rx="2"/>')

    def atxt(self, x, y, t, size=11, color=AXIS, anchor="middle", bold=False):
        b = ' font-weight="600"' if bold else ""
        self.s.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                      f'fill="{color}" text-anchor="{anchor}"{b}>{t}</text>')

    def render(self):
        self.s.append("</svg>")
        return "".join(self.s)


def est(e, model, param, year=None):
    q = e[(e["model"] == model) & (e["param"] == param)]
    if year is not None:
        q = q[q["year"] == year]
    return q["estimate"].values


def est2(e, model, param, year=None):
    """返回 (点估计, 标准误)"""
    q = e[(e["model"] == model) & (e["param"] == param)]
    if year is not None:
        q = q[q["year"] == year]
    return float(q["estimate"].values[0]), float(q["se"].values[0])


def compute_bins():
    """小时极值口径的尖峰率分箱 (实际值)"""
    rtm = pd.read_csv(RTM)
    t = pd.to_datetime(rtm["interval_start_utc"]).dt.tz_convert("UTC") \
        .dt.tz_localize(None)
    s = pd.Series(rtm["spp"].astype(float).values, index=t).sort_index()
    hmax = s.resample("1h").max()
    out = {}
    for yr in (2025, 2026):
        pp = pd.read_csv(PN[yr], index_col=0, parse_dates=True)
        pp = pp[pp["solar"] > 50]
        hm = hmax.reindex(pp.index)
        ok = hm.notna()
        pp, hm = pp[ok], hm[ok]
        thr = hm.quantile(0.99)
        tail = hm > thr
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 99)]
        rows = []
        for lo, hi in edges:
            sel = (pp["shortfall"] / 1000 >= lo) & (pp["shortfall"] / 1000 < hi)
            if sel.sum() < 30:
                continue
            rows.append((f"{lo}~{hi}", int(sel.sum()),
                         float(tail[sel].mean() * 100), float(thr)))
        out[yr] = rows
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    e = pd.read_csv(ELAS)
    ev = pd.read_csv(TAIL, index_col=0, parse_dates=True)
    bins = compute_bins()

    b25 = [float(est(e, "qreg15", f"sf_q{t}", 2025)[0]) for t in TAUS]
    b26 = [float(est(e, "qreg15", f"sf_q{t}", 2026)[0]) for t in TAUS]
    m25 = float(est(e, "OLS_hourmean_HAC", "sf", 2025)[0])
    m26 = float(est(e, "OLS_hourmean_HAC", "sf", 2026)[0])
    u25 = [float(est(e, "qreg_hourmax_usd", f"sf_usd_q{t}", 2025)[0]) for t in TAUS]
    u26 = [float(est(e, "qreg_hourmax_usd", f"sf_usd_q{t}", 2026)[0]) for t in TAUS]
    avg_b = {t: (a + b) / 2 for t, a, b in zip(TAUS, b25, b26)}

    # 图1: beta(tau) 曲线
    f = Fig(880, 300, 56, 18, 18, 44, 0.45, 1.02, 3.2, 5.6, "缺口弹性 %/GW")
    f.hline(m25, C_MEAN, "5 4")
    f.atxt(f.w - 28, f.Y(m25) - 7, f"2025 均值口径 +{m25:.2f}", 11, C_MEAN, "end")
    f.poly(TAUS, b25, C25, 2.4, dot=True)
    f.poly(TAUS, b26, C26, 2.4, dot=True)
    for t, v in zip(TAUS, b25):
        f.atxt(f.X(t), f.Y(v) - 12, f"{v:.2f}", 10.5, C25)
    for t, v in zip(TAUS, b26):
        f.atxt(f.X(t), f.Y(v) + 18, f"{v:.2f}", 10.5, C26)
    f.vline(0.99, AXIS, "3 3")
    f.atxt(f.X(0.99), f.mt + 12, "P99", 11, AXIS, "end", True)
    for t in TAUS:
        f.atxt(f.X(t), f.h - 26, f"τ={t:g}", 11)
    f.atxt(f.w / 2, f.h - 6, "分位 τ (对 RTM 价格分布)", 12)
    svg_beta = f.render()

    # 图2: 原始尺度 $/GW
    f = Fig(430, 300, 58, 14, 18, 44, 0.45, 1.02, 0.6, 2.9, "缺口边际冲击 $/GW")
    f.poly(TAUS, u25, C25, 2.4, dot=True)
    f.poly(TAUS, u26, C26, 2.4, dot=True)
    for t, v in zip(TAUS, u25):
        f.atxt(f.X(t), f.Y(v) - 11, f"{v:.1f}", 10.5, C25)
    f.atxt(f.X(1.0), f.Y(u26[-1]) + 16, f"{u26[-1]:.1f}", 10.5, C26)
    for t in [0.5, 0.75, 0.99, 0.995]:
        f.atxt(f.X(t), f.h - 26, f"{t:g}", 11)
    f.atxt(f.w / 2, f.h - 6, "分位 τ", 12)
    svg_usd = f.render()

    # 图3: 尖峰率分箱
    f = Fig(430, 300, 46, 14, 18, 44, -0.6, 5.6, 0.0, 1.8, "尖峰小时占比 %")
    labs = [r[0] for r in bins[2025]]
    for i, yr in enumerate((2025, 2026)):
        rows = bins[yr]
        xs = [j + (i - 0.5) * 0.34 for j in range(len(rows))]
        hs = [r[2] for r in rows]
        f.bars(xs, hs, 15, [C25 if yr == 2025 else C26] * len(rows))
    for j, r in enumerate(bins[2025]):
        f.atxt(f.X(j), f.h - 26, r[0], 10.5)
    f.atxt(f.w / 2, f.h - 6, "光伏缺口 (GW)", 12)
    f.atxt(f.X(0.3), f.Y(1.62), "2025", 11, C25, "middle", True)
    f.atxt(f.X(1.1), f.Y(1.62), "2026", 11, C26, "middle", True)
    svg_bins = f.render()

    # 图4: 2022-07 分位情景
    sw = ev["shortfall_mw"] / 1000
    f = Fig(880, 330, 58, 18, 18, 46, 0, 5, 0, 26, "RTM 上浮 %")
    grid = np.linspace(0, 5, 60)
    for tau, col, lab in ((0.50, C_P50, "P50 中位情景"),
                          (0.90, C_P90, "P90 紧张情景"),
                          (0.99, C_P99, "P99 尖峰情景")):
        ys = [(np.exp(avg_b[tau] / 100 * g) - 1) * 100 for g in grid]
        f.poly(grid, ys, col, 2.2)
    f.dots(sw, ev["uplift_p50"], 3.0, "rgba(45,164,78,0.75)")
    f.dots(sw, ev["uplift_p99"], 3.0, "rgba(207,34,46,0.75)")
    f.atxt(f.X(4.9), f.Y((np.exp(avg_b[0.50] / 100 * 4.9) - 1) * 100) - 12,
           "P50", 11.5, C_P50, "end", True)
    f.atxt(f.X(4.9), f.Y((np.exp(avg_b[0.90] / 100 * 4.9) - 1) * 100) - 12,
           "P90", 11.5, C_P90, "end", True)
    f.atxt(f.X(4.9), f.Y((np.exp(avg_b[0.99] / 100 * 4.9) - 1) * 100) - 12,
           "P99", 11.5, C_P99, "end", True)
    f.vline(4.40, AXIS, "3 3")
    f.atxt(f.X(4.40), f.mt + 12, "07-21 最大缺口 4.40 GW", 10.5, AXIS, "end")
    for g in range(0, 6):
        f.atxt(f.X(g), f.h - 26, str(g), 11)
    f.atxt(f.w / 2, f.h - 6, "光伏缺口 (GW)", 12)
    svg_ev = f.render()

    # 图5: 稳健性口径对比
    hb = {}
    for yr in (2025, 2026):
        for lab, mod in (("极值", "hourly_lnp_max"), ("均值", "hourly_lnp_mean")):
            ols = float(est(e, mod + "_ols", "sf", yr)[0])
            q = {t: float(est(e, mod, f"sf_q{t}", yr)[0]) for t in (0.5, 0.9, 0.99)}
            hb[(yr, lab)] = (ols, q)
    f = Fig(880, 290, 56, 18, 18, 60, -0.5, 3.5, 3.0, 6.0, "缺口弹性 %/GW")
    keys = [(2025, "均值"), (2025, "极值"), (2026, "均值"), (2026, "极值")]
    for i, k in enumerate(keys):
        ols, q = hb[k]
        f.bars([i], [ols], 22, [C25 if k[0] == 2025 else C26])
    for i, k in enumerate(keys):
        ols, q = hb[k]
        for j, t in enumerate((0.5, 0.9, 0.99)):
            x = i + (j - 1) * 0.26
            f.bars([x], [q[t]], 13, ["rgba(27,36,48,0.30)"] * 1)
            f.atxt(f.X(x), f.Y(q[t]) - 5, f"{q[t]:.1f}", 9.5, AXIS)
        f.atxt(f.X(i), f.Y(ols) - 7, f"{ols:.1f}", 10.5, "#1B2430", "middle", True)
        f.atxt(f.X(i), f.h - 42, f"{k[0]} {k[1]}", 11)
    f.atxt(f.X(0.9), f.mt + 14, "实心=OLS均值  ▍灰=Q50/Q90/Q99",
           10.5, AXIS, "start")
    f.atxt(f.w / 2, f.h - 8, "因变量口径 (小时粒度, 无伪重复)", 12)
    svg_rob = f.render()

    # ---- 汇总数字 ----
    med50, mx50 = ev["uplift_p50"].median(), ev["uplift_p50"].max()
    med90, mx90 = ev["uplift_p90"].median(), ev["uplift_p90"].max()
    med99, mx99 = ev["uplift_p99"].median(), ev["uplift_p99"].max()
    sw = ev["shortfall_mw"] / 1000
    hw = ev.index.normalize().isin(pd.date_range("2022-07-13", "2022-07-18"))
    hwg = ev.loc[hw, "shortfall_mw"].sum() / 1000
    quad, quad_s = est2(e, "quad_hourmean_HAC", "sf2", 2025)
    quad_ev, quad_ev_s = est2(e, "quad_event_range_HAC", "sf2", 2025)
    quad26, quad26_s = est2(e, "quad_hourmean_HAC", "sf2", 2026)
    q99m = float(est(e, "quad_q99_15min", "sf2", 2025)[0])
    lnor25, se25 = est2(e, "glm_tail_hour", "lnOR", 2025)
    lnor26, se26 = est2(e, "glm_tail_hour", "lnOR", 2026)

    css = """
  :root{--bg:#FFFFFF;--bg2:#F4F7FC;--rule:#D6DEEB;--ink:#1B2430;--muted:#64718A;
        --accent:#0969DA;--accent2:#8250DF;--pos:#2DA44E;--neg:#CF222E;
        --font:'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',
               -apple-system,'Segoe UI',sans-serif}
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{font-family:var(--font);color:var(--ink);background:var(--bg);
       line-height:1.65;font-size:15px}
  .wrap{max-width:960px;margin:0 auto;padding:40px 24px 64px}
  header{border-bottom:3px solid var(--accent);padding-bottom:18px;margin-bottom:28px}
  h1{font-size:26px;font-weight:600}
  .sub{color:var(--muted);font-size:13.5px;margin-top:6px}
  h2{font-size:19px;margin:36px 0 12px;font-weight:600;
     border-left:4px solid var(--accent);padding-left:10px}
  h3{font-size:15.5px;margin:18px 0 8px}
  p{margin:8px 0}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
         gap:14px;margin:18px 0}
  .card{background:var(--bg2);border:1px solid var(--rule);border-radius:10px;
        padding:16px 18px}
  .card .k{font-size:12.5px;color:var(--muted)}
  .card .v{font-size:28px;font-weight:650;margin-top:4px}
  .card .v .u{font-size:14px;font-weight:500;color:var(--muted)}
  .card .s{font-size:12px;color:var(--muted);margin-top:4px}
  .fig{background:var(--bg2);border:1px solid var(--rule);border-radius:10px;
       padding:16px;margin:14px 0}
  .fig .cap{font-size:13px;color:var(--muted);margin-top:8px}
  .legend{display:flex;gap:18px;font-size:12.5px;color:var(--muted);
          margin-bottom:4px;flex-wrap:wrap}
  .legend i{display:inline-block;width:14px;height:3px;border-radius:2px;
            margin-right:5px;vertical-align:middle}
  table{border-collapse:collapse;width:100%;font-size:13.5px;margin:12px 0}
  th,td{border:1px solid var(--rule);padding:7px 10px;text-align:left}
  th{background:var(--bg2);font-weight:600}
  .mono{font-family:Consolas,Menlo,monospace;font-size:13px}
  .note{background:#FFF8E6;border:1px solid #EAD98A;border-radius:8px;
        padding:12px 16px;font-size:13.5px;margin:14px 0}
  .ok{color:var(--pos);font-weight:600}
  .bad{color:var(--neg);font-weight:600}
  ul{padding-left:22px;margin:8px 0}
  li{margin:4px 0}
  footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--rule);
         color:var(--muted);font-size:12.5px}
  a{color:var(--accent)}
  """

    rows_beta = "".join(
        f"<tr><td class='mono'>τ={t:g}</td><td>{a:+.2f}</td><td>{b:+.2f}</td>"
        f"<td>{(a+b)/2:+.2f}</td></tr>"
        for t, a, b in zip(TAUS, b25, b26))
    rows_usd = "".join(
        f"<tr><td class='mono'>τ={t:g}</td><td>${a:.2f}</td><td>${b:.2f}</td></tr>"
        for t, a, b in zip(TAUS, u25, u26))
    rows_rob = "".join(
        f"<tr><td>{yr}</td><td>{lab}</td><td class='mono'>{hb[(yr,lab)][0]:+.2f}</td>"
        f"<td class='mono'>{hb[(yr,lab)][1][0.5]:+.2f}</td>"
        f"<td class='mono'>{hb[(yr,lab)][1][0.9]:+.2f}</td>"
        f"<td class='mono'>{hb[(yr,lab)][1][0.99]:+.2f}</td></tr>"
        for yr, lab in keys)
    rows_bin = "".join(
        f"<tr><td class='mono'>{r[0]} GW</td><td>{r[1]}</td>"
        f"<td class='mono'>{r[2]:.1f}%</td></tr>" for r in bins[2025])
    rows_bin26 = "".join(
        f"<tr><td class='mono'>{r[0]} GW</td><td>{r[1]}</td>"
        f"<td class='mono'>{r[2]:.1f}%</td></tr>" for r in bins[2026])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERCOT RTM 尾部尖峰弹性标定与极端场景外推</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>RTM 尾部尖峰弹性标定与极端场景外推</h1>
  <div class="sub">ERCOT · HB_HOUSTON · 2025-01-01 ~ 2026-09-06 · 15 分钟 RTM 58,940 条
  · 分位数回归 + 凸性检验 + 尾部概率 + 2022-07 分位情景推演
  · 承接 PS-022（光伏缺口 × 电价冲击）· 全文时间为 UTC</div>
</header>

<h2>0. 执行摘要</h2>
<div class="cards">
  <div class="card"><div class="k">尖峰口径损耗</div>
    <div class="v">2.4<span class="u">×</span></div>
    <div class="s">15min 最高 $3777 vs 小时均值最高 $1561</div></div>
  <div class="card"><div class="k">尾部弹性 (2025)</div>
    <div class="v">+{b25[-1]:.2f}<span class="u"> %/GW</span></div>
    <div class="s">τ=0.995 vs 中位 +{b25[0]:.2f}（单调上升）</div></div>
  <div class="card"><div class="k">原始尺度尾部放大</div>
    <div class="v">2.4<span class="u">×</span></div>
    <div class="s">缺口 +1GW：中位 +$1.0 vs P99 +$2.4</div></div>
  <div class="card"><div class="k">2022-07 上浮区间</div>
    <div class="v">+{med50:.1f}~+{med99:.1f}<span class="u"> %</span></div>
    <div class="s">中位缺口 2.06 GW，P50~P99 情景</div></div>
</div>

<div class="note">
<b>核心结论（三条，含对 PS-022 的修正）：</b>
<ul>
<li><b>纳入尖峰不改变百分比结论，但改变绝对水平认知</b>：小时平均把极端小时价格抹平
2.4 倍（$3777→$1561），但弹性是尺度不变的斜率，PS-022 的弹性估计
（+5.08 %/GW）无系统性偏误。</li>
<li><b>未发现尾部弹性系统性放大</b>：15min 分位弹性 2025 单调升（+{b25[0]:.2f}→+{b25[-1]:.2f}），
2026 基本平坦（+{b26[0]:.2f}→+{b26[-1]:.2f}）；两年不一致，且均值口径
（+{m25:.2f}/+{m26:.2f}）落在高分位区间内。原始尺度上尾部边际冲击为中位的 2.4 倍
（$1.0→$2.4/GW），但<b>相对变化反而更小</b>，两者自洽。</li>
<li><b>PS-022 的"高需求 ×1.15 放大"不成立</b>：子样本法两年方向相反
（2025 +5.84 高于均值，2026 +4.33 低于均值）；全样本交互项法两年一致为负增量
（-1.95 / -1.00）。原 +5.84 的高需求情景属高估。</li>
</ul>
</div>

<h2>1. 为什么要给"尖峰"单独建模</h2>
<p>PS-022 的弹性标定以 <span class="mono">小时均值 ln(RTM)</span> 为因变量。ERCOT 实时市场按
15 分钟结算，日内尖峰常只持续 1~2 个结算区间，小时平均会系统性削平极值：</p>
<table>
<tr><th>口径</th><th>最高价</th><th>q99 阈值</th><th>中位价</th></tr>
<tr><td>15 分钟原始</td><td class="mono">$3777</td><td class="mono">$146</td><td class="mono">$26</td></tr>
<tr><td>小时均值</td><td class="mono">$1561</td><td class="mono">$143</td><td class="mono">$26</td></tr>
<tr><td>白天样本内 15min</td><td class="mono">$2261</td><td>—</td><td>—</td></tr>
<tr><td>白天样本内 小时均值</td><td class="mono">$1511</td><td>—</td><td>—</td></tr>
</table>
<div class="note">分位阈值几乎不受影响（$146 vs $143），说明尖峰<b>不是</b>短于 15 分钟的孤立脉冲；
被抹平的是<b>最极端的小时</b>（2.4 倍）。因此"纳入尖峰"的作用点在极端情景的
<b>价格水平</b>，而非弹性斜率。</div>

<h2>2. 分位弹性曲线 β(τ)</h2>
<p>把因变量换成 15 分钟 RTM，对 <span class="mono">Q_τ(ln RTM) ~ 缺口 + 风电 + 需求 + 小时FE + 月份FE</span>
逐分位回归（缺口单位 GW，系数 ×100 得 %/GW）：</p>
<div class="fig">
  <div class="legend"><span><i style="background:{C25}"></i>2025</span>
  <span><i style="background:{C26}"></i>2026</span>
  <span><i style="background:{C_MEAN}"></i>2025 均值口径（PS-022）</span></div>
  {svg_beta}
  <div class="cap">缺口弹性随分位 τ 的变化。2025 单调上升 (+{b25[0]:.2f}→+{b25[-1]:.2f})，
  2026 平坦甚至回落 (+{b26[0]:.2f}→+{b26[-1]:.2f})。15min 与小时供需对齐，1 小时内 4 条
  伪重复使标准误偏小，点估计不受影响。</div>
</div>
<table>
<tr><th>分位 τ</th><th>2025 %/GW</th><th>2026 %/GW</th><th>两年均值</th></tr>
{rows_beta}
<tr><td><b>OLS 条件均值</b></td><td><b>{m25:+.2f}</b></td><td><b>{m26:+.2f}</b></td>
<td><b>{(m25+m26)/2:+.2f}</b></td></tr>
</table>
<p><b>读法</b>：条件均值弹性（{m25:.2f}/{m26:.2f}）高于任一分位弹性，说明
<b>价格分布的右尾对缺口的敏感度并不强于均值</b>。换句话说，极端尖峰更多由缺口之外的因素
（需求水平、备用裕度、机组强迫停运）驱动。</p>

<h2>3. 原始尺度的尾部放大</h2>
<p>换到绝对价格尺度（因变量为小时内极值 RTM，单位 $/MWh），同一 1 GW 缺口对不同价格分位的
边际冲击：</p>
<div class="fig">
  <div class="legend"><span><i style="background:{C25}"></i>2025</span>
  <span><i style="background:{C26}"></i>2026</span></div>
  {svg_usd}
  <div class="cap">缺口每 +1 GW 的边际价格冲击（$/GW）随分位上升：中位约 $1.0，
  τ=0.99 约 $2.3~2.4（<b>2.4 倍</b>）。</div>
</div>
<table>
<tr><th>分位 τ</th><th>2025 $/GW</th><th>2026 $/GW</th></tr>
{rows_usd}
</table>
<p>这与第 2 节并不矛盾：高分位价格水平本身高（$200 vs $29），同样的相对变化对应更大的
绝对变化。以 1 GW 缺口计，中位分位的相对冲击 $1.0/$29 ≈ 3.4%，而 P99 分位
$2.4/$200 ≈ 1.2% —— <b>相对弹性反而更低</b>，两口径自洽。</p>

<h2>4. 凸性检验：线性外推是否低估极端</h2>
<p>PS-022 用 <span class="mono">上浮% = exp(β·缺口GW) − 1</span> 外推，隐含 ln 尺度线性。
若真实关系超线性（凸），则会低估极端。在 ln 尺度加入缺口平方项检验：</p>
<table>
<tr><th>样本 / 口径</th><th>平方项 (per GW²)</th><th>t</th><th>判定</th></tr>
<tr><td>2025 全样本 (小时均值, HAC)</td><td class="mono">{quad:+.3f}</td>
<td class="mono">{quad/quad_s:+.1f}</td><td class="ok">边际显著</td></tr>
<tr><td>2025 事件尺度 (缺口 ≤6 GW)</td><td class="mono">{quad_ev:+.3f}</td>
<td class="mono">{quad_ev/quad_ev_s:+.1f}</td><td class="bad">不显著</td></tr>
<tr><td>2025 Q99 (15min)</td><td class="mono">{q99m:+.3f}</td><td>—</td>
<td class="bad">符号为负</td></tr>
<tr><td>2026 全样本 (小时均值, HAC)</td><td class="mono">{quad26:+.3f}</td>
<td class="mono">{quad26/quad26_s:+.1f}</td><td class="bad">不显著</td></tr>
</table>
<div class="note"><b>结论：凸性证据不成立。</b>只有 2025 全样本（受缺口长尾 sf 至 13 GW 拉动）
边际显著；压到 2022-07 事件尺度（1.5~4.4 GW）后 t=−0.9，2026 同口径 t=+0.6，
高分位甚至为负。<b>PS-022 的 ln 线性外推未被证伪，也未发现需要上调的凸性修正。</b></div>

<h2>5. 尾部概率：条件正相关与边际悖论</h2>
<p>以"小时极值价格超过 99 分位阈值"为因变量做 Logistic 回归（小时粒度，无伪重复）：</p>
<table>
<tr><th>年份</th><th>条件 lnOR (每 +1 GW, 控制需求/风电/小时/月份)</th><th>OR</th><th>边际尖峰率走向</th></tr>
<tr><td>2025</td><td class="mono">{lnor25:+.3f} (SE {se25:.3f})</td>
<td class="mono">{np.exp(lnor25):.3f}</td><td class="bad">1.5% → 0.7%（下降）</td></tr>
<tr><td>2026</td><td class="mono">{lnor26:+.3f} (SE {se26:.3f})</td>
<td class="mono">{np.exp(lnor26):.3f}</td><td class="bad">1.5% → 0.9%（下降）</td></tr>
</table>
<div class="fig">
  {svg_bins}
  <div class="cap">尖峰小时占比 vs 缺口档（2025 蓝 / 2026 品红）。两年都呈<b>下降</b>趋势：
  缺口最大的小时反而不是尖峰小时。</div>
</div>
<table>
<tr><th>缺口档</th><th>2025 n</th><th>2025 尖峰率</th></tr>
{rows_bin}
</table>
<table>
<tr><th>缺口档</th><th>2026 n</th><th>2026 尖峰率</th></tr>
{rows_bin26}
</table>
<div class="note"><b>辛普森悖论警示</b>：控制需求与时段后缺口与尖峰概率正相关（2026 显著
OR=1.39），但边际上尖峰率随缺口<b>不升反降</b>。原因是 ERA5/EIA 口径的"缺口"由
<b>P95 晴空包络 − 实际出力</b> 定义，而包络在低太阳高度角时系统性虚高，使大缺口更多落在
清晨/黄昏——而尖峰发生在傍晚需求高峰。<b>尖峰的主导因子是需求与时段，缺口是次要因子</b>；
PS-022 已用逐小时偏移缓解该口径偏差，但影响在本节独立显现。</div>

<h2>6. 高需求弹性的修正</h2>
<p>PS-022 报告"高需求区 (≥72 GW) 弹性 +5.84 %/GW，高于基准 +5.08"。本分析用两种方法复核：</p>
<table>
<tr><th>方法</th><th>2025</th><th>2026</th><th>结论</th></tr>
<tr><td>子样本法（PS-022 口径，demand ≥72 GW 内单独回归）</td>
<td class="mono">+5.84</td><td class="mono">+4.33</td>
<td class="bad">两年方向相反（2025 高、2026 低）</td></tr>
<tr><td>全样本交互项（缺口 × 1(demand≥72GW)）</td>
<td class="mono">基准 +5.21，增量 −1.95</td>
<td class="mono">基准 +5.48，增量 −1.00</td>
<td class="ok">两年一致为负增量</td></tr>
</table>
<div class="note"><b>子样本法为何不可靠</b>：demand ≥72 GW 子样本内需求标准差仅 2.80 GW
（全样本 10.52），需求变量几乎失去识别力，其与缺口的弱相关（r=−0.10）被放大为偏误，
把缺口系数从 3.26 抬到 5.84。<b>更稳健的交互项法表明高需求不放大缺口弹性，反而略弱
（合计 +3.26 / +4.48）</b>。经济含义：系统紧张时段价格由负荷边际成本主导，
光伏缺口的边际贡献被"淹没"。<b>故 2022-07 推演中的高需求情景 (+5.84) 应视为上界而非推荐值。</b></div>

<h2>7. 2022-07 分位情景推演</h2>
<p>用两年平均分位弹性把 2022-07 的 {len(ev)} 个事件小时（缺口 ≥1.5 GW，15-23 UTC，
缺电 {ev['shortfall_mw'].sum()/1000:.1f} GWh）映射为上浮区间：</p>
<div class="fig">
  {svg_ev}
  <div class="cap">散点为 2022-07 事件小时（绿=P50 口径、红=P99 口径）；曲线为分位弹性
  外推。缺口中位 {sw.median():.2f} GW、最大 {sw.max():.2f} GW（{sw.idxmax().strftime('%m-%d %H:%M')}）。</div>
</div>
<table>
<tr><th>情景</th><th>弹性 (两年均值)</th><th>中位上浮</th><th>最大上浮</th>
<th>按 $182/MWh 折算</th></tr>
<tr><td class="mono">P50 中位</td><td class="mono">{avg_b[0.50]:+.2f} %/GW</td>
<td class="mono">+{med50:.1f}%</td><td class="mono">+{mx50:.1f}%</td>
<td class="mono">+${ev['usd_p50'].median():.0f} ~ +${ev['usd_p50'].max():.0f}</td></tr>
<tr><td class="mono">P90 紧张</td><td class="mono">{avg_b[0.90]:+.2f} %/GW</td>
<td class="mono">+{med90:.1f}%</td><td class="mono">+{mx90:.1f}%</td>
<td class="mono">+${ev['usd_p90'].median():.0f} ~ +${ev['usd_p90'].max():.0f}</td></tr>
<tr><td class="mono">P99 尖峰</td><td class="mono">{avg_b[0.99]:+.2f} %/GW</td>
<td class="mono">+{med99:.1f}%</td><td class="mono">+{mx99:.1f}%</td>
<td class="mono">+${ev['usd_p99'].median():.0f} ~ +${ev['usd_p99'].max():.0f}</td></tr>
<tr><td><b>PS-022 均值口径</b></td><td class="mono">+5.08</td>
<td class="mono"><b>+11.0%</b></td><td class="mono"><b>+25.0%</b></td>
<td class="mono">+$20 ~ +$46</td></tr>
</table>
<div class="note"><b>与 PS-022 的关系</b>：PS-022 的 +11.0%/+25.0% 落在本报告分位曲线的
<b>上沿</b>（高于 P99 的 +{med99:.1f}%/+{mx99:.1f}%）。原因是条件均值弹性受右尾拉动，
数值上高于高分位弹性。<b>结论：PS-022 的极端场景推演不是低估，而是略偏保守（偏激进），
可直接沿用；本报告提供了更完整的分位上沿/下沿区间。</b>
热浪期（07-13~18）{int(hw.sum())} 个事件、缺电 {hwg:.1f} GWh，
P50 中位 +{ev.loc[hw,'uplift_p50'].median():.1f}% / P99 中位
+{ev.loc[hw,'uplift_p99'].median():.1f}%，与全月分布一致。</div>

<h2>8. 稳健性与结论</h2>
<p>为排除 15 分钟与小时供需对齐产生的伪重复，另用<b>小时粒度</b>样本（无伪重复）复核：</p>
<div class="fig">
  {svg_rob}
  <div class="cap">四种口径下的缺口弹性。实心柱为 OLS 条件均值，灰柱为 Q50/Q90/Q99。</div>
</div>
<table>
<tr><th>年份</th><th>因变量口径</th><th>OLS 均值</th><th>Q50</th><th>Q90</th><th>Q99</th></tr>
{rows_rob}
</table>
<p><b>结论</b>：</p>
<ul>
<li>缺口弹性在四种口径、两年数据下稳定落在 <b>+3.5 ~ +5.7 %/GW</b>，
PS-022 的 +5.08 位于区间中部，<b>量级结论稳健</b>。</li>
<li><b>未发现尾部弹性系统性大于均值弹性的证据</b>（2025 支持、2026 不支持）；
ln 尺度<b>无稳健凸性</b>。因此 PS-022 的线性外推在事件尺度（1.5~4.4 GW）适用。</li>
<li>真正被"小时平均"抹平的是<b>极端小时的价格水平（2.4 倍）</b>，不是斜率。
若关注绝对价格冲击或做尾部风险管理，应改用 15 分钟口径。</li>
<li><b>PS-023 对 PS-022 的两项实质修正</b>：① 高需求放大（+5.84）不成立，应降为
+3.3~+4.5；② 极端场景上浮以分位区间表达（P50 +{med50:.1f}% / P90 +{med90:.1f}% /
P99 +{med99:.1f}%）比单一均值数字更完整。</li>
<li><b>方法学警示</b>：P95 晴空包络 − 实际出力的缺口口径在低太阳高度角虚高，
使缺口与尖峰在边际上负相关；后续宜改用<b>物理晴空反事实</b>（PS-022 的 Solis 链路）
统一两个场景，消除口径不一致。</li>
</ul>

<footer>
数据: GridStatus.io RTM HB_HOUSTON 15min (2025-01-01~2026-09-06, 58,940 条) ·
EIA-930 小时光伏/风电/需求 · PS-022 晴空反事实 (NSRDB v3.2.2 + HRRR 2m + pvlib)<br>
方法: 分位数回归 (statsmodels QuantReg) · HAC 稳健标准误 · Logistic GLM · 小时/月份固定效应<br>
产物: <span class="mono">data/ercot/price_elasticity_tail.csv</span> ·
<span class="mono">data/nsrdb/pv_event_price_impact_tail_2022-07.csv</span><br>
流程文档: <span class="mono">.knowledge/tech/processes/PS-023.md</span> · 承接 PS-022
</footer>
</div>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"已生成: {OUT}  ({len(html)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
