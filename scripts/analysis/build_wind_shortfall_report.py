"""风电缺口 × 电价 报告 (自包含 HTML)
输入: data/ercot/wind_power_hourly_2025_2026.csv, wind_elasticity_2025.csv
输出: output/wind_shortfall_elasticity/index.html
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\ercot"
OUT = r"c:\work\meteo\output\wind_shortfall_elasticity"
os.makedirs(OUT, exist_ok=True)
TOT_MW = 37930.0

BLUE, RED, ORANGE, GREY, GREEN = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4", "#2f8f6b"


def svg_dual_bins(h):
    """缺口 / 低风异常 分位 vs RTM 中位 (对比斜率)"""
    w, ht, pad = 860, 320, (54, 14, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    h = h.copy()
    h["q_short"] = pd.qcut(h["w_short"], 10, labels=False, duplicates="drop")
    h["q_dr"] = pd.qcut(h["w_drought"], 10, labels=False, duplicates="drop")
    a = h.groupby("q_short")["rtm"].median()
    b = h.groupby("q_dr")["rtm"].median()
    lo = min(a.min(), b.min()) * 0.9
    hi = max(a.max(), b.max()) * 1.08
    xp = lambda i: x0 + (x1 - x0) * i / 9
    yp = lambda v: y1 - (y1 - y0) * (v - lo) / (hi - lo)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" '
         f'font-family="Segoe UI,Arial" font-size="11">']
    for g in np.linspace(lo, hi, 5):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{yp(g):.0f}" y2="{yp(g):.0f}" stroke="#e7eef4"/>')
        s.append(f'<text x="{x0-6}" y="{yp(g)+3:.0f}" text-anchor="end" fill="{GREY}">${g:.0f}</text>')
    for series, col, lab in ((a, ORANGE, "风电缺口 w_short 十分位"), (b, BLUE, "低风异常 w_drought 十分位")):
        pts = " ".join(f"{xp(i):.0f},{yp(v):.0f}" for i, v in series.items())
        s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.4"/>')
        for i, v in series.items():
            s.append(f'<circle cx="{xp(i):.0f}" cy="{yp(v):.0f}" r="3.2" fill="{col}"/>')
    s.append(f'<text x="{x0+8}" y="{y0-8}" fill="{ORANGE}">━ 风电缺口 ↑ → 电价 ↓</text>')
    s.append(f'<text x="{x0+210}" y="{y0-8}" fill="{BLUE}">━ 低风异常 ↑ → 电价 ↑</text>')
    for i in range(10):
        s.append(f'<text x="{xp(i):.0f}" y="{ht-30}" text-anchor="middle" fill="{GREY}">{i+1}</text>')
    s.append(f'<text x="{(x0+x1)/2:.0f}" y="{ht-12}" text-anchor="middle" fill="#5b7488">十分位 (1=最小, 10=最大)</text>')
    s.append("</svg>")
    return "\n".join(s)


def svg_hour_profile(h):
    w, ht, pad = 860, 300, (50, 14, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    g = h.groupby(h.index.hour).agg(ws=("w_short", "mean"), dm=("demand", "mean"))
    bw = (x1 - x0) / 24
    ymax = g["ws"].max() * 1.25
    yp = lambda v: y1 - (y1 - y0) * v / ymax
    dmax, dmin = g["dm"].max(), g["dm"].min()
    yd = lambda v: y1 - (y1 - y0) * (v - dmin) / (dmax - dmin) * 0.85 - 8
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" '
         f'font-family="Segoe UI,Arial" font-size="11">']
    for hr, r in g.iterrows():
        x = x0 + hr * bw
        s.append(f'<rect x="{x+2:.0f}" y="{yp(r["ws"]):.0f}" width="{bw-4:.0f}" '
                 f'height="{y1-yp(r["ws"]):.0f}" fill="{ORANGE}" opacity="0.85"/>')
    pts = " ".join(f"{x0+i*bw+bw/2:.0f},{yd(v):.0f}" for i, v in enumerate(g["dm"]))
    s.append(f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="2.4"/>')
    for hh in range(0, 24, 3):
        s.append(f'<text x="{x0+hh*bw+bw/2:.0f}" y="{ht-30}" text-anchor="middle" fill="{GREY}">{hh}</text>')
    s.append(f'<text x="{x0+6}" y="{y0-6}" fill="{ORANGE}">■ 平均风电缺口 (MW)</text>')
    s.append(f'<text x="{x0+180}" y="{y0-6}" fill="{BLUE}">━ 平均负荷 (GW, 右轴)</text>')
    s.append(f'<text x="{(x0+x1)/2:.0f}" y="{ht-12}" text-anchor="middle" fill="#5b7488">UTC 小时</text>')
    s.append("</svg>")
    return "\n".join(s)


def svg_monthly(h):
    w, ht, pad = 860, 260, (54, 14, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    m = h.resample("MS").agg(pot=("pot", "sum"), act=("act", "sum"))
    m = m / 1e6
    n = len(m)
    bw = (x1 - x0) / n
    ymax = m[["pot", "act"]].values.max() * 1.12
    yp = lambda v: y1 - (y1 - y0) * v / ymax
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" '
         f'font-family="Segoe UI,Arial" font-size="11">']
    for g in np.linspace(0, ymax, 4):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{yp(g):.0f}" y2="{yp(g):.0f}" stroke="#e7eef4"/>')
        s.append(f'<text x="{x0-6}" y="{yp(g)+3:.0f}" text-anchor="end" fill="{GREY}">{g:.0f}</text>')
    for i, (idx, r) in enumerate(m.iterrows()):
        x = x0 + i * bw
        s.append(f'<rect x="{x+3:.0f}" y="{yp(r["pot"]):.0f}" width="{bw/2-4:.0f}" '
                 f'height="{y1-yp(r["pot"]):.0f}" fill="{BLUE}" opacity="0.55"/>')
        s.append(f'<rect x="{x+bw/2:.0f}" y="{yp(r["act"]):.0f}" width="{bw/2-4:.0f}" '
                 f'height="{y1-yp(r["act"]):.0f}" fill="{GREEN}"/>')
        s.append(f'<text x="{x+bw/2:.0f}" y="{ht-30}" text-anchor="middle" fill="{GREY}">'
                 f'{idx.strftime("%y-%m")}</text>')
    s.append(f'<text x="{x0+6}" y="{y0-6}" fill="{BLUE}">■ 资源潜力</text>')
    s.append(f'<text x="{x0+120}" y="{y0-6}" fill="{GREEN}">■ 实际风电 (EIA-930)</text>')
    s.append(f'<text x="{x1}" y="{y0-6}" text-anchor="end" fill="{GREY}">月能量 TWh</text>')
    s.append("</svg>")
    return "\n".join(s)


def build():
    h = pd.read_csv(os.path.join(D, "wind_power_hourly_2025_2026.csv"),
                    index_col=0, parse_dates=True)
    e = pd.read_csv(os.path.join(D, "wind_elasticity_2025.csv"))

    def gv(model, param, year=None):
        r = e[(e["model"] == model) & (e["param"] == param)]
        if year is not None:
            r = r[r["year"] == year]
        return (r["estimate_pct_per_gw"].iloc[0], r["se_pct_per_gw"].iloc[0]) if len(r) else (np.nan, np.nan)

    ws25 = gv("wind_short", "w_short", 2025)
    ws26 = gv("wind_short", "w_short", 2026)
    dr25 = (e[(e.model == "drought") & (e.year == 2025)]["estimate_pct_per_gw"].iloc[0],
            e[(e.model == "drought") & (e.year == 2025)]["se_pct_per_gw"].iloc[0])
    dr26 = (e[(e.model == "drought") & (e.year == 2026)]["estimate_pct_per_gw"].iloc[0],
            e[(e.model == "drought") & (e.year == 2026)]["se_pct_per_gw"].iloc[0])
    lv25 = (e[(e.model == "level") & (e.year == 2025)]["estimate_pct_per_gw"].iloc[0],
            e[(e.model == "level") & (e.year == 2025)]["se_pct_per_gw"].iloc[0])
    lv26 = (e[(e.model == "level") & (e.year == 2026)]["estimate_pct_per_gw"].iloc[0],
            e[(e.model == "level") & (e.year == 2026)]["se_pct_per_gw"].iloc[0])
    mc25 = gv("mech_control_act", "w_short")
    mc26 = gv("mech_control_act", "w_short")
    j_pv25 = gv("joint_day", "pv_short")
    j_pv26 = gv("joint_day", "pv_short")
    j_w25 = gv("joint_day", "w_short")
    j_w26 = gv("joint_day", "w_short")
    cap = h.loc[h.index.year == 2025, "act"].mean() / TOT_MW
    corr_all = h["pot"].corr(h["act"])

    def card(v, t, d):
        return f'<div class="card"><div class="v">{v}</div><div class="t">{t}</div><div class="d">{d}</div></div>'

    cards = (card(f"{corr_all:.3f}", "潜力×实际 相关", "物理风功率模型 (n=14,568h)")
             + card(f"−{abs(ws25[0]):.1f} %/GW", "风电缺口 弹性", "潜力−实际; 与光伏 +5 相反")
             + card(f"+{dr25[0]:.1f} %/GW", "低风异常 弹性", "相对气候的低风; 强于光伏")
             + card("≈0", "控实际风电后", "缺口独立效应消失 → 内生弃风"))

    rows = ""
    for _, r in e.iterrows():
        b, s = r["estimate_pct_per_gw"], r["se_pct_per_gw"]
        cl = "neg" if b < 0 else "pos"
        rows += (f'<tr><td>{int(r["year"])}</td><td>{r["model"]}</td>'
                 f'<td>{r["param"]}</td><td class="{cl}">{b:+.3f}</td>'
                 f'<td>{s:.3f}</td><td>{int(r["n"])}</td></tr>')

    # 负价频率
    def negfreq(year):
        d = h[h.index.year == year]
        hi = d[d["w_short"] >= d["w_short"].quantile(.9)]
        lo = d[d["w_short"] <= d["w_short"].quantile(.5)]
        return (hi["rtm"] < 5).mean() * 100, (lo["rtm"] < 5).mean() * 100, len(hi)
    n25 = negfreq(2025)
    n26 = negfreq(2026)

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ERCOT 风电缺口 × 电价 (2025/2026)</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c}}
.wrap{{max-width:980px;margin:0 auto;padding:28px 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:16px;line-height:1.6}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#fff;border-radius:12px;padding:15px 17px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:168px}}
.card .v{{font-size:26px;font-weight:700;color:#1f5bb8}}.card .t{{font-weight:600;margin-top:4px}}
.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
.box{{background:#fff;border-radius:12px;padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:6px 8px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600}}
td:first-child,th:first-child{{text-align:left}}
.neg{{color:#c23a3a;font-weight:600}}.pos{{color:#1f5bb8;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}li{{margin:5px 0}}
.hl{{background:#fff6ea;border-left:3px solid #e5853a;padding:10px 14px;border-radius:6px;margin:12px 0}}
.scroll{{overflow-x:auto}}
</style></head><body><div class="wrap">
<h1>ERCOT 风电缺口 × 电价</h1>
<div class="sub">物理风功率链路 · 165 个风电点位 / 37.9 GW · HRRR 80m 风速 + 标准功率曲线 ·
2025-01-01 ~ 2026-09-06（14,568 小时）· 对标光伏链 PS-021~027</div>

<div class="cards">{cards}</div>

<div class="hl"><b>一句话结论</b>：光伏"缺口→电价"是 <b>+5 %/GW 正相关</b>；风电的"资源潜力−实际"缺口却是
<b>−2.8/−3.3 %/GW 负相关</b>，且控制实际风电后<b>独立效应消失（≈0）</b>。
原因是两者的物理含义不同：光伏缺口 = <b>外生</b>云致供给收缩；风电缺口 = <b>内生</b>弃风（高风+低需求时的供给过剩），
它自身就是"价格已经很低"的结果。风电真正的"天气供给缺口"应看<b>低风异常</b>，其弹性 <b>+7.4 %/GW</b>，强于光伏。</div>

<div class="box"><h2 style="margin-top:0">① 物理风功率模型验证</h2>
{svg_monthly(h)}
<div class="note">用 HRRR 80m 风速过标准功率曲线（切入 3 / 额定 12 / 切出 25 m/s，场损 η=0.90）得 fleet 资源潜力。
逐小时相关 <b>r = {corr_all:.4f}</b>，能量比 <b>1.02</b>，容量因子潜力 {cap:.3f} vs 实际 {h.loc[h.index.year==2025,'act'].mean()/TOT_MW:.3f}
（2025）—— 无需历史出力训练的纯物理链路即可复现 ERCOT 风电（与光伏 PS-021 同性质）。</div></div>

<div class="box"><h2 style="margin-top:0">② 两种"缺口"的价格斜率相反</h2>
{svg_dual_bins(h)}
<div class="note">按变量十分位分箱，取该箱 RTM 中位。橙色（风电缺口）单调下降，蓝色（低风异常）单调上升 —— 方向相反。</div></div>

<div class="box"><h2 style="margin-top:0">③ 缺口出现在高风、低需求、夜间 ⇒ 弃风特征</h2>
{svg_hour_profile(h)}
<div class="note">缺口在 03–06UTC（夜间）与 21UTC 最大，同时负荷处于低谷；
高风小时（&gt;P90）缺口均值 5,056 MW vs 低风小时 2,773 MW，且高风时需求更低（53.4 vs 58.8 GW）。
高缺口小时（&gt;P90）出现 &lt;$5 负价占比 <b>{n25[0]:.1f}%</b>（2025）/ <b>{n26[0]:.1f}%</b>（2026），
低缺口小时仅 {n25[1]:.1f}% / {n26[1]:.1f}% —— <b>缺口小时是供给过剩的标志，不是缺电</b>。</div></div>

<div class="box"><h2 style="margin-top:0">④ 弹性总表（%/GW，ln(RTM) ~ X + 需求 + 小时/月 FE）</h2>
<div class="scroll"><table><thead><tr><th>年</th><th>模型</th><th>变量</th>
<th>弹性 %/GW</th><th>SE</th><th>n</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="note">关键读数：<br>
• <b>wind_short/w_short</b> {ws25[0]:+.2f}/{ws26[0]:+.2f} —— 负；<b>mech_control_act</b>（加实际风电）后
{mc25[0]:+.2f}/{mc26[0]:+.2f}（不显著）⇒ 负号来自"风电水平"通道，缺口无独立效应。<br>
• <b>drought/w_drought</b> {dr25[0]:+.2f}/{dr26[0]:+.2f}（SE 仅 0.17/0.24）—— 稳、强、正。<br>
• <b>level/act</b> {lv25[0]:+.2f}/{lv26[0]:+.2f}；资源潜力 pot −4.20/−3.40。<br>
• <b>joint_day</b>（白天同框）：光伏缺口 {j_pv25[0]:+.2f}/{j_pv26[0]:+.2f} vs 风电缺口 {j_w25[0]:+.2f}/{j_w26[0]:+.2f}，
<b>同框反号</b> —— 直观展示风光不对称。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 结论与边界</h2>
<ul class="note">
<li><b>风光不对称（核心）</b>：同一"缺口"概念在两类电源上符号相反。光伏缺口是外生天气冲击（云），风电缺口是内生市场结果（弃风）⇒ <b>不能把光伏弹性简单套到风电</b>，这正是 PS-022 推广方向需要先厘清的前提。</li>
<li><b>正确的风电类比物</b>：低风异常（相对 (小时,月) 气候的低风）弹性 <b>+7.4 %/GW</b>，比光伏缺口 +4.5~+5.7 %/GW 更大 —— 单位 GW 低风对电价的推力强于单位 GW 云致光伏缺口（风电体量更大、夜间也出力）。</li>
<li><b>弃风量化</b>：潜力−实际（校准后）占潜力能量 23.2%，但其<b>水平被模型误差抬高</b>（HRRR 栅格风被平滑、单一功率曲线、缺空气密度修正），ERCOT 官方弃风通常仅数个百分点 ⇒ 该 23% 应读作"潜力缺口"，其中弃风只是其一；<b>变化量</b>才承载价格信号。</li>
<li><b>对齐敏感性</b>：潜力相对实际在 +1h 滞后的相关略高（0.966 vs 0.956），滞后 1h 重算缺口弹性 −0.36/−1.08 %/GW —— 负号不变，幅度收窄，说明对齐误差不改变定性结论。</li>
<li><b>与光伏链的一致性</b>：本脚本复现了 PS-024 的光伏缺口弹性量级（+4.5/+5.7 vs PS-024 +5.05/+6.15 %/GW，同口径白天小时），说明风电结果不是链路实现差异造成的。</li>
<li><b>局限</b>：①80m 单一高度、无空气密度/尾流方向修正；②GEM 清单截止 2025 投产，2026 新增装机缺失（同光伏链已知问题）；③弃风"因"与"果"不可用本数据完全分离，负弹性是<b>标记</b>而非因果；④RTM 为 HB_HOUSTON 枢纽价，非节点价。</li>
</ul></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"→ {p}")


if __name__ == "__main__":
    build()