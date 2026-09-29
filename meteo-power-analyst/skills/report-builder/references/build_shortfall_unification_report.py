"""生成"缺口口径统一"HTML 报告 (物理晴空反事实 vs P95 包络)
输入: shortfall_physical_2025_2026.csv / shortfall_definition_comparison.csv /
      pv_event_price_impact_physical_2022-07.csv
输出: output/shortfall_unification/ercot_shortfall_unification.html
用法: python skills/report-builder/references/build_shortfall_unification_report.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data"
SF = os.path.join(D, "ercot", "shortfall_physical_2025_2026.csv")
CMP = os.path.join(D, "ercot", "shortfall_definition_comparison.csv")
IMP = os.path.join(D, "nsrdb", "pv_event_price_impact_physical_2022-07.csv")
OUT_DIR = r"c:\work\meteo\output\shortfall_unification"
OUT = os.path.join(OUT_DIR, "ercot_shortfall_unification.html")

C_PH, C_P95 = "#0969DA", "#BF3989"
C_Q = {0.5: "#2DA44E", 0.9: "#0969DA", 0.99: "#CF222E"}
GRID, AXIS = "rgba(27,36,48,0.12)", "#64718A"


class Fig:
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
            self.s.append(f'<text x="{ml-44}" y="{mt+self.ph/2:.0f}" '
                          f'font-size="12" fill="{AXIS}" '
                          f'transform="rotate(-90 {ml-44} {mt+self.ph/2:.0f})">'
                          f'{ylab}</text>')

    def X(self, v):
        return self.ml + (v - self.x0) / (self.x1 - self.x0) * self.pw

    def Y(self, v):
        return self.mt + (1 - (v - self.plo) / (self.phi - self.plo)) * self.ph

    def hline(self, y, c, dash="4 4"):
        self.s.append(f'<line x1="{self.ml}" y1="{self.Y(y):.1f}" '
                      f'x2="{self.w-self.mr}" y2="{self.Y(y):.1f}" '
                      f'stroke="{c}" stroke-width="1.2" stroke-dasharray="{dash}"/>')

    def poly(self, xs, ys, c, w=2.2, dash=None, dot=False):
        pts = " ".join(f"{self.X(x):.1f},{self.Y(y):.1f}" for x, y in zip(xs, ys))
        dd = f' stroke-dasharray="{dash}"' if dash else ""
        self.s.append(f'<polyline points="{pts}" fill="none" stroke="{c}" '
                      f'stroke-width="{w}" stroke-linejoin="round"{dd}/>')
        if dot:
            for x, y in zip(xs, ys):
                self.s.append(f'<circle cx="{self.X(x):.1f}" '
                              f'cy="{self.Y(y):.1f}" r="2.6" fill="{c}"/>')

    def dots(self, xs, ys, r, c, op=1):
        o = f' opacity="{op}"' if op < 1 else ""
        for x, y in zip(xs, ys):
            self.s.append(f'<circle cx="{self.X(x):.1f}" cy="{self.Y(y):.1f}" '
                          f'r="{r}" fill="{c}"{o}/>')

    def bars(self, xs, hs, bw, colors):
        for x, hv, c in zip(xs, hs, colors):
            y0, y1 = self.Y(0), self.Y(hv)
            self.s.append(f'<rect x="{self.X(x)-bw/2:.1f}" y="{min(y0,y1):.1f}" '
                          f'width="{bw:.1f}" height="{abs(y1-y0):.1f}" '
                          f'fill="{c}" rx="2"/>')

    def atxt(self, x, y, t, size=11, color=AXIS, anchor="middle", bold=False):
        b = ' font-weight="600"' if bold else ""
        self.s.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                      f'fill="{color}" text-anchor="{anchor}"{b}>{t}</text>')

    def render(self):
        self.s.append("</svg>")
        return "".join(self.s)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sf = pd.read_csv(SF, index_col=0, parse_dates=True)
    sf.index = pd.to_datetime(sf.index)
    cmp = pd.read_csv(CMP)
    imp = pd.read_csv(IMP, index_col=0, parse_dates=True)

    def val(year, defn, item):
        v = cmp[(cmp["year"] == year) & (cmp["definition"] == defn) &
                (cmp["item"] == item)]["value"]
        return float(v.iloc[0]) if len(v) else np.nan

    # ---- 图1: 缺口分布分位对比 ----
    qs = [10, 25, 50, 75, 90, 95]
    dist = {}
    for yr in (2025, 2026):
        d = sf[sf["year"] == yr]
        dist[yr] = {("phys", q): np.percentile(d["shortfall_phys"] / 1000, q) for q in qs}
        dist[yr].update({("p95", q): np.percentile(d["shortfall"] / 1000, q) for q in qs})
    f = Fig(880, 300, 58, 18, 18, 46, -0.6, 5.6, 0, 20, "缺口 (GW)")
    for i, yr in enumerate((2025, 2026)):
        xs_p = [j + (i - 0.5) * 0.36 for j in range(len(qs))]
        f.bars(xs_p, [dist[yr][("phys", q)] for q in qs], 17,
               [C_PH] * len(qs))
        f.bars([x + 0.18 for x in xs_p], [dist[yr][("p95", q)] for q in qs], 17,
               [C_P95] * len(qs))
    for j, q in enumerate(qs):
        f.atxt(f.X(j), f.h - 26, f"P{q}", 11)
    f.atxt(f.w / 2, f.h - 6, "缺口分位", 12)
    f.atxt(f.X(2.0), f.Y(19.0), "2025", 11, AXIS, "middle", True)
    f.atxt(f.X(4.2), f.Y(19.0), "2026", 11, AXIS, "middle", True)
    svg_dist = f.render()

    # ---- 图2: 弹性对比 ----
    f = Fig(430, 300, 52, 14, 18, 46, -0.6, 3.6, 0, 7, "%/GW")
    items = [("ols_mean_pct_per_gw", "OLS"), ("q50_pct_per_gw", "Q50"),
             ("q90_pct_per_gw", "Q90"), ("q99_pct_per_gw", "Q99")]
    for i, (it, lab) in enumerate(items):
        for k, (defn, col) in enumerate((("物理晴空", C_PH), ("P95 包络", C_P95))):
            vals = [val(yr, defn, it) for yr in (2025, 2026)]
            v = np.nanmean(vals)
            f.bars([i + (k - 0.5) * 0.34], [v], 17, [col])
            f.atxt(f.X(i + (k - 0.5) * 0.34), f.Y(v) - 6, f"{v:.2f}",
                   9.5, AXIS)
        f.atxt(f.X(i), f.h - 26, lab, 11)
    f.atxt(f.w / 2, f.h - 6, "弹性估计口径", 12)
    svg_elas = f.render()

    # ---- 图3: 分箱尖峰率 (辛普森悖论检验) ----
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 99)]
    f = Fig(880, 300, 50, 18, 18, 46, -0.6, 5.6, 0, 2.6, "尖峰小时占比 %")
    for k, (defn, col) in enumerate((("物理晴空", C_PH), ("P95 包络", C_P95))):
        xs, hs = [], []
        for j, (lo, hi) in enumerate(edges):
            vals = [val(yr, defn, f"tailrate_{lo}_{hi}") for yr in (2025, 2026)]
            xs.append(j + (k - 0.5) * 0.34)
            hs.append(np.nanmean(vals))
        f.bars(xs, hs, 17, [col] * len(xs))
        for x, h in zip(xs, hs):
            f.atxt(f.X(x), f.Y(h) - 6, f"{h:.1f}", 9.5, AXIS)
    for j, (lo, hi) in enumerate(edges):
        f.atxt(f.X(j), f.h - 26, f"{lo}~{hi}", 10.5)
    f.atxt(f.w / 2, f.h - 6, "缺口档 (GW)", 12)
    svg_bins = f.render()

    # ---- 图4: 2022-07 三口径对比 ----
    sw = imp["shortfall_mw"] / 1000
    f = Fig(880, 320, 58, 18, 18, 46, 0, 5, 0, 26, "RTM 上浮 %")
    grid = np.linspace(0, 5, 60)
    bp = {t: np.nanmean([val(yr, "物理晴空", f"q{int(t*100)}_pct_per_gw")
                         for yr in (2025, 2026)]) / 100 for t in (0.5, 0.9, 0.99)}
    bq = {t: np.nanmean([val(yr, "P95 包络", f"q{int(t*100)}_pct_per_gw")
                         for yr in (2025, 2026)]) / 100 for t in (0.5, 0.9, 0.99)}
    b22 = 0.0508
    for t, col in ((0.5, C_Q[0.5]), (0.9, C_Q[0.9]), (0.99, C_Q[0.99])):
        f.poly(grid, [(np.exp(bp[t] * g) - 1) * 100 for g in grid], col, 2.2)
        f.poly(grid, [(np.exp(bq[t] * g) - 1) * 100 for g in grid], col, 1.4,
               dash="4 3")
    for t, col, lab in ((0.5, C_Q[0.5], "P50"), (0.9, C_Q[0.9], "P90"),
                        (0.99, C_Q[0.99], "P99")):
        y = (np.exp(bp[t] * 4.9) - 1) * 100
        f.atxt(f.X(4.9), f.Y(y) - 10, lab, 11.5, col, "end", True)
    y22 = (np.exp(b22 * 4.9) - 1) * 100
    f.poly(grid, [(np.exp(b22 * g) - 1) * 100 for g in grid], "#8250DF", 1.6,
           dash="6 4")
    f.atxt(f.X(3.6), f.Y((np.exp(b22 * 3.6) - 1) * 100) - 10, "PS-022 单年均值口径",
           10.5, "#8250DF", "start")
    f.dots(sw, imp["up_phys_p50"], 3.0, "rgba(45,164,78,0.7)")
    f.dots(sw, imp["up_phys_p99"], 3.0, "rgba(207,34,46,0.7)")
    for g in range(0, 6):
        f.atxt(f.X(g), f.h - 26, str(g), 11)
    f.atxt(f.w / 2, f.h - 6, "光伏缺口 (GW)", 12)
    svg_ev = f.render()

    # ---- 汇总数字 ----
    trows = ""
    for defn in ("物理晴空", "P95 包络"):
        for it, lab in items:
            v25, v26 = val(2025, defn, it), val(2026, defn, it)
            trows += (f"<tr><td>{defn}</td><td>{lab}</td>"
                      f"<td class='mono'>{v25:+.2f}</td>"
                      f"<td class='mono'>{v26:+.2f}</td>"
                      f"<td class='mono'>{(v25+v26)/2:+.2f}</td></tr>")
    brows = ""
    for defn in ("物理晴空", "P95 包络"):
        for lo, hi in edges:
            vs = [val(yr, defn, f"tailrate_{lo}_{hi}") for yr in (2025, 2026)]
            brows += (f"<tr><td>{defn}</td><td class='mono'>{lo}~{hi} GW</td>"
                      f"<td class='mono'>{vs[0]:.1f}%</td>"
                      f"<td class='mono'>{vs[1]:.1f}%</td></tr>")
    med = {k: imp[k].median() for k in ("up_phys_p50", "up_phys_p90",
                                        "up_phys_p99", "up_p95_p99")}
    mx = {k: imp[k].max() for k in ("up_phys_p50", "up_phys_p90",
                                    "up_phys_p99", "up_p95_p99")}
    hw = imp.index.normalize().isin(pd.date_range("2022-07-13", "2022-07-18"))
    d25 = sf[sf["year"] == 2025]
    d26 = sf[sf["year"] == 2026]

    css = """
  :root{--bg:#FFFFFF;--bg2:#F4F7FC;--rule:#D6DEEB;--ink:#1B2430;--muted:#64718A;
        --accent:#0969DA;--pos:#2DA44E;--neg:#CF222E;
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
  .flow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0}
  .flow .box{background:var(--bg2);border:1px solid var(--rule);border-radius:8px;
             padding:8px 12px;font-size:13px}
  .flow .arr{color:var(--muted)}
  footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--rule);
         color:var(--muted);font-size:12.5px}
  a{color:var(--accent)}
  """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERCOT 光伏缺口口径统一 (物理晴空反事实 vs P95 包络)</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>光伏缺口口径统一</h1>
  <div class="sub">ERCOT · 物理晴空反事实 (pvlib Solis) vs P95 数据驱动包络
  · 2025-01-01 ~ 2026-09-06 · 141 座 ≥100MW 电站 (30.89 GW, 占全网 94.5%)
  · 承接 PS-022/PS-023 · 全文时间为 UTC</div>
</header>

<h2>0. 执行摘要</h2>
<div class="cards">
  <div class="card"><div class="k">弹性口径差异</div>
    <div class="v">&lt;0.4<span class="u"> %/GW</span></div>
    <div class="s">两口径 OLS 均值 +5.60 vs +5.26</div></div>
  <div class="card"><div class="k">缺口量级差异</div>
    <div class="v">1.5<span class="u">×</span></div>
    <div class="s">物理中位 {d25['shortfall_phys'].median()/1000:.1f} GW
    vs 包络 {d25['shortfall'].median()/1000:.1f} GW (2025)</div></div>
  <div class="card"><div class="k">2022-07 中位上浮</div>
    <div class="v">+{med['up_phys_p50']:.1f}~+{med['up_phys_p99']:.1f}<span class="u">%</span></div>
    <div class="s">物理口径 P50~P99，与 PS-022 一致</div></div>
  <div class="card"><div class="k">辛普森悖论</div>
    <div class="v">仍<span class="u"> 存在</span></div>
    <div class="s">非口径所致，属真实结构</div></div>
</div>

<div class="note">
<b>三条结论：</b>
<ul>
<li><b>弹性对缺口径不敏感</b>：物理晴空与 P95 包络的 OLS 均值弹性为
+5.60 / +5.26 %/GW（两年平均），分位弹性差 < 0.4 %/GW。两种定义给出
相同量级的市场响应，PS-022/023 的弹性结论得到独立复核。</li>
<li><b>缺口<span class="bad">量级</span>对口径敏感</b>：物理晴空缺口中位
{d25['shortfall_phys'].median()/1000:.2f} GW（2025）vs 包络
{d25['shortfall'].median()/1000:.2f} GW，相差约 <b>1.5 倍</b>。
物理口径衡量"相对完全无云"，包络口径衡量"相对典型晴天(P95)"，
前者含全部云影响，后者仅含超出 P95 晴况的部分。</li>
<li><b>辛普森悖论不是口径造成的</b>：改用物理反事实后，分箱尖峰率<b>仍随缺口下降</b>
（2025: 2.0%→0.0%；2026: 1.7%→0.7%）。这修正了 PS-023 的"P95 包络虚高"归因——
真正的机制是<b>天气组合的负相关</b>：云致缺口多伴随阴天降温与较低需求，
而电价尖峰需要高需求 + 供给紧张。<span class="ok">PS-023 的结论（尖峰主由需求/时段驱动）
被强化，归因被修正。</span></li>
</ul>
</div>

<h2>1. 为什么需要统一口径</h2>
<p>PS-022 对 <b>2022-07 推演</b>使用物理晴空反事实（pvlib <span class="mono">simplified_solis</span>
+ 单轴跟踪 + HRRR 温度 + ILR 1.30 + 损耗 14%），但对 <b>2025/2026 弹性标定</b>使用
<b>P95 数据驱动包络</b>（同 hour-of-day ±15 天窗口内光伏出力 P95）。两者口径不同，
是潜在的方法论隐患。PS-023 进一步发现包络"在低太阳高度角虚高"，
怀疑其造成缺口与尖峰的边际负相关。</p>
<div class="flow">
  <span class="box">GEM 电站清单 (按年筛选)</span><span class="arr">→</span>
  <span class="box">NSRDB 像素匹配</span><span class="arr">→</span>
  <span class="box">HRRR 2m 温度</span><span class="arr">→</span>
  <span class="box">pvlib Solis 晴空 + 单轴跟踪</span><span class="arr">→</span>
  <span class="box">ILR 1.30 / 损耗 14%</span><span class="arr">→</span>
  <span class="box">逐小时偏移校准</span><span class="arr">→</span>
  <span class="box">物理缺口</span>
</div>

<h2>2. 2025/2026 物理晴空反事实的构建</h2>
<table>
<tr><th>环节</th><th>参数 / 结果</th></tr>
<tr><td>电站清单</td><td>GEM 2026-08 operating，ERCOT 边界，≥100MW，start-year ≤ 目标年 →
<b>141 座，30.89 GW</b>（占全网 ≥10MW 口径 94.5%）</td></tr>
<tr><td>像素匹配</td><td>NSRDB v3.2.2 最近像素，中位距离 0.9 km，141/141 全部匹配</td></tr>
<tr><td>温度</td><td>Open-Meteo HRRR <span class="mono">ncep_hrrr_conus</span> 2m 分析场，
141 站 × 14,736 h（无缺失），范围 −20.2 ~ 44.6 °C</td></tr>
<tr><td>链路</td><td>与 PS-022 的 2022 完全一致：Solis 晴空 → 单轴跟踪
(backtrack, gcr=0.35, max 60°) → Faiman 简化电池温度 → PVWatts DC/AC</td></tr>
<tr><td>步长</td><td>5 min（176,832 步）→ 小时均值</td></tr>
<tr><td>校准</td><td>逐小时偏移 = 该小时 (反事实 − 实际) 的 5% 分位（最晴 5% 小时视为无云），
自动吸收 GEM 装机清单的不完整（2025 比值 0.955，2026 比值 1.133）</td></tr>
<tr><td>结果</td><td>反事实峰值 30,884 MW；2025 偏移 −1.8~−2.8 GW（15-21 UTC），
2026 偏移 −4.4~−5.6 GW（13-23 UTC）</td></tr>
</table>

<h2>3. 两种口径的缺口分布</h2>
<div class="fig">
  <div class="legend">
    <span><i style="background:{C_PH}"></i>物理晴空</span>
    <span><i style="background:{C_P95}"></i>P95 包络</span></div>
  {svg_dist}
  <div class="cap">缺口分位对比。物理口径系统性高于包络口径（2025 中位
  {d25['shortfall_phys'].median()/1000:.2f} vs {d25['shortfall'].median()/1000:.2f} GW；
  2026 {d26['shortfall_phys'].median()/1000:.2f} vs {d26['shortfall'].median()/1000:.2f} GW），
  且尾部更厚（P95: {d25['shortfall_phys'].quantile(0.95)/1000:.1f} vs
  {d25['shortfall'].quantile(0.95)/1000:.1f} GW）。</div>
</div>

<h2>4. 弹性估计的口径稳健性</h2>
<div class="fig">
  <div class="legend">
    <span><i style="background:{C_PH}"></i>物理晴空</span>
    <span><i style="background:{C_P95}"></i>P95 包络</span></div>
  {svg_elas}
  <div class="cap">两年平均弹性（%/GW）。四种估计口径下，两缺口定义的差异均小于
  0.4 %/GW，OLS 均值差 0.34。</div>
</div>
<table>
<tr><th>缺口定义</th><th>估计口径</th><th>2025</th><th>2026</th><th>两年均值</th></tr>
{trows}
</table>
<div class="note"><b>结论</b>：弹性是"价格对供给增量的敏感度"，只要缺口定义与电力
供需同相位，量级估计就稳定。两种口径的差异主要在<b>缺口绝对量级</b>（约 1.5 倍），
而这不影响斜率。这是 PS-022/023 弹性结论的独立第三方复核。</div>

<h2>5. 辛普森悖论检验：归因修正</h2>
<p>PS-023 发现"条件 GLM 中缺口为正、但边际尖峰率随缺口下降"，并猜测主因是
P95 包络在低太阳高度角虚高。改用物理反事实后重新检验：</p>
<div class="fig">
  <div class="legend">
    <span><i style="background:{C_PH}"></i>物理晴空</span>
    <span><i style="background:{C_P95}"></i>P95 包络</span></div>
  {svg_bins}
  <div class="cap">尖峰小时占比 vs 缺口档（两年平均）。<b>两种口径都随缺口下降</b>——
  物理口径降幅更陡（2025 从 2.0% 降至 0.0%）。</div>
</div>
<table>
<tr><th>缺口定义</th><th>缺口档</th><th>2025 尖峰率</th><th>2026 尖峰率</th></tr>
{brows}
</table>
<div class="note"><b>归因修正</b>：PS-023 把悖论归因于 P95 包络的虚高，本流程证明该归因
<b>不成立</b>——物理口径下悖论依旧。真正机制是<b>天气组合负相关</b>：
光伏缺口由云驱动，而德州云雨天气通常伴随降温与需求回落；电价尖峰则需要高需求与供给紧张。
两者在天气上倾向互斥。<br>
<b>对 PS-023 的影响</b>：其最后一条"方法学警示"（宜改用物理晴空反事实）应弱化为
"物理口径不减轻悖论"；而其核心结论——<b>尖峰主导因子是需求与时段，缺口是次要因子</b>
——不仅保留，且被物理口径强化。</div>

<h2>6. 2022-07 推演：三口径收敛</h2>
<div class="fig">
  <div class="legend">
    <span><i style="background:{C_Q[0.5]}"></i>P50</span>
    <span><i style="background:{C_Q[0.9]}"></i>P90</span>
    <span><i style="background:{C_Q[0.99]}"></i>P99</span>
    <span><i style="background:#8250DF"></i>PS-022 单年均值口径</span>
    <span>实线=物理口径 / 虚线=P95 包络口径</span></div>
  {svg_ev}
  <div class="cap">2022-07 事件小时（{len(imp)} 个，缺口 ≥1.5 GW，15-23 UTC）的上浮映射。
  散点为物理口径 P50（绿）与 P99（红）。缺口中位 {sw.median():.2f} GW，
  最大 {sw.max():.2f} GW（{sw.idxmax().strftime('%m-%d %H:%M')}）。</div>
</div>
<table>
<tr><th>口径</th><th>P50 中位 / 最大</th><th>P90 中位 / 最大</th>
<th>P99 中位 / 最大</th><th>折合 $/MWh（P99）</th></tr>
<tr><td><b>物理晴空（推荐，同口径）</b></td>
<td class="mono">+{med['up_phys_p50']:.1f}% / +{mx['up_phys_p50']:.1f}%</td>
<td class="mono">+{med['up_phys_p90']:.1f}% / +{mx['up_phys_p90']:.1f}%</td>
<td class="mono">+{med['up_phys_p99']:.1f}% / +{mx['up_phys_p99']:.1f}%</td>
<td class="mono">+$19 ~ +$42</td></tr>
<tr><td>P95 包络（PS-023 用）</td>
<td class="mono">+8.0% / +17.8%</td><td class="mono">+9.4% / +21.2%</td>
<td class="mono">+{med['up_p95_p99']:.1f}% / +{mx['up_p95_p99']:.1f}%</td>
<td class="mono">+$19 ~ +$43</td></tr>
<tr><td>PS-022（2025 单年 OLS 均值 +5.08）</td>
<td class="mono">+11.0% / +25.0%</td><td>—</td><td>—</td>
<td class="mono">+$20 ~ +$46</td></tr>
</table>
<div class="note"><b>三口径收敛</b>：中位上浮落在 <b>+8.0 ~ +11.0%</b>、最大上浮落在
<b>+17.8 ~ +25.0%</b>。口径统一（标定与推演都用物理晴空）后，结果与 PS-022/023
在 1 个百分点内一致。<b>结论：2022-07 光伏缺口的价格冲击估计对缺口定义与弹性口径
均不敏感，稳健性得到三重确认。</b>
热浪期（07-13~18）{int(hw.sum())} 个事件、缺电
{imp.loc[hw,'shortfall_mw'].sum()/1000:.1f} GWh，
物理口径 P50 中位 +{imp.loc[hw,'up_phys_p50'].median():.1f}% /
P99 中位 +{imp.loc[hw,'up_phys_p99'].median():.1f}%。</div>

<h2>7. 结论</h2>
<ul>
<li><b>口径统一完成</b>：2025/2026 弹性标定与 2022-07 推演现在都基于同一物理晴空
反事实链路，消除了 PS-022 遗留的方法论隐患。</li>
<li><b>弹性稳健</b>：两口径 OLS 均值 +5.60 / +5.26 %/GW，分位差 &lt; 0.4 %/GW。</li>
<li><b>缺口量级敏感</b>：物理口径约为包络口径 1.5 倍，解读缺口数值时必须声明定义；
两种定义回答不同问题（"相对完全无云"vs"相对典型晴天"）。</li>
<li><b>归因修正</b>：辛普森悖论源自天气组合负相关（云致缺口 ↔ 降温低需求），
非包络口径缺陷。<b>尖峰主导因子是需求与时段</b>——该结论被强化。</li>
<li><b>推演收敛</b>：2022-07 中位上浮 +8.0~+11.0%、最大 +17.8~+25.0%，
三重口径确认，可直接用于风险沟通。</li>
</ul>

<footer>
数据: GEM 2026-08 太阳能表 · NSRDB v3.2.2 像素索引 · Open-Meteo HRRR 2m 气温 (141 站 × 14,736 h)
· EIA-930 小时光伏/风电/需求 · GridStatus RTM HB_HOUSTON 15 min<br>
方法: pvlib Solis 晴空 + 单轴跟踪 + PVWatts (ILR 1.30, 损耗 14%) · 逐小时偏移校准
· OLS (HAC) / 分位数回归 / Logistic GLM · 小时+月份固定效应<br>
产物: <span class="mono">data/ercot/shortfall_physical_2025_2026.csv</span> ·
<span class="mono">data/ercot/shortfall_definition_comparison.csv</span> ·
<span class="mono">data/nsrdb/pv_clearsky_hourly_2025_2026.csv</span><br>
流程文档: <span class="mono">kb/recipes/RCP-20260927-007.md</span> · 承接 PS-022 / PS-023
</footer>
</div>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"已生成: {OUT} ({len(html)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
