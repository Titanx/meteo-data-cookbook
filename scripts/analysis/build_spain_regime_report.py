"""西班牙光伏链路 · 市场区间对比报告 (2023 vs 2024 vs 2025)
输入: data/spain/spain_regime_summary.csv, spain_regime_elasticity.csv
输出: output/spain_regime/index.html
"""
import os

import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_regime"
os.makedirs(OUT, exist_ok=True)
BLUE, RED, ORANGE, GREY, GREEN = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4", "#2f8f6b"


def svg_negbar(s):
    w, ht, pad = 860, 260, (56, 16, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    n = len(s)
    bw = (x1 - x0) / n
    ymax = max(s["neg_h"].max(), 1) * 1.25
    Y = lambda v: y1 - (y1 - y0) * v / ymax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for g in [0, 200, 400, 600]:
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(g):.0f}" y2="{Y(g):.0f}" stroke="#e7eef4"/>')
        out.append(f'<text x="{x0-6}" y="{Y(g)+3:.0f}" text-anchor="end" fill="{GREY}">{g}</text>')
    for i, (_, r) in enumerate(s.iterrows()):
        cx = x0 + bw * (i + 0.5)
        w2 = bw * 0.34
        out.append(f'<rect x="{cx-w2-3:.0f}" y="{Y(r["neg_h"]):.0f}" width="{w2:.0f}" height="{y1-Y(r["neg_h"]):.0f}" fill="{RED}"/>')
        out.append(f'<rect x="{cx+3:.0f}" y="{Y(r["neg_pct"]*30):.0f}" width="{w2:.0f}" height="{y1-Y(r["neg_pct"]*30):.0f}" fill="{ORANGE}" opacity="0.75"/>')
        out.append(f'<text x="{cx-w2/2-3:.0f}" y="{Y(r["neg_h"])-4:.0f}" text-anchor="middle" fill="{RED}">{int(r["neg_h"])}</text>')
        out.append(f'<text x="{cx+w2/2+3:.0f}" y="{Y(r["neg_pct"]*30)-4:.0f}" text-anchor="middle" fill="{ORANGE}">{r["neg_pct"]:.1f}%</text>')
        out.append(f'<text x="{cx:.0f}" y="{ht-30}" text-anchor="middle" fill="#5b7488">{int(r["year"])} ({r["GW"]:.1f} GW)</text>')
    out.append(f'<text x="{x0}" y="{y0-6}" fill="{RED}">■ 负电价小时数</text>')
    out.append(f'<text x="{x0+150}" y="{y0-6}" fill="{ORANGE}">■ 负价占比 (%, 右移3倍便于同轴)</text>')
    out.append("</svg>")
    return "\n".join(out)


def svg_mech(s):
    w, ht, pad = 860, 280, (56, 16, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    n = len(s)
    bw = (x1 - x0) / n
    ymax = 65.0
    Y = lambda v: y1 - (y1 - y0) * v / ymax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for g in [0, 20, 40, 60]:
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(g):.0f}" y2="{Y(g):.0f}" stroke="#e7eef4"/>')
        out.append(f'<text x="{x0-6}" y="{Y(g)+3:.0f}" text-anchor="end" fill="{GREY}">{g}%</text>')
    series = [("negfreq_highgap", RED, "高缺口小时(>P90)"),
              ("quad_negfreq", ORANGE, "高光伏×低负荷象限"),
              ("negfreq_lowgap", BLUE, "低缺口小时(≤中位)")]
    for j, (k, col, lab) in enumerate(series):
        for i, (_, r) in enumerate(s.iterrows()):
            cx = x0 + bw * (i + 0.5) + (j - 1) * bw * 0.26
            v = r[k]
            out.append(f'<rect x="{cx-bw*0.11:.0f}" y="{Y(v):.0f}" width="{bw*0.22:.0f}" height="{y1-Y(v):.0f}" fill="{col}"/>')
            out.append(f'<text x="{cx:.0f}" y="{Y(v)-4:.0f}" text-anchor="middle" fill="{col}">{v:.1f}</text>')
        out.append(f'<text x="{x0+30+j*250}" y="{y0-8}" fill="{col}">■ {lab}</text>')
    for i, (_, r) in enumerate(s.iterrows()):
        out.append(f'<text x="{x0+bw*(i+0.5):.0f}" y="{ht-30}" text-anchor="middle" fill="#5b7488">{int(r["year"])}</text>')
    out.append(f'<text x="{(x0+x1)/2:.0f}" y="{ht-10}" text-anchor="middle" fill="#5b7488">该组小时内出现负电价的频率</text>')
    out.append("</svg>")
    return "\n".join(out)


def build():
    s = pd.read_csv(os.path.join(D, "spain_regime_summary.csv"))
    e = pd.read_csv(os.path.join(D, "spain_regime_elasticity.csv"))
    s = s.set_index("year")

    def val(y, k):
        return s.loc[y, k]

    def card(v, t, d):
        return f'<div class="card"><div class="v">{v}</div><div class="t">{t}</div><div class="d">{d}</div></div>'

    lvl = e[(e.target == "level") & (e["var"] == "act")].set_index("year")["beta"]
    gapw = e[(e.target == "level") & (e["var"] == "gap_w")].set_index("year")["beta"]
    gapcs = e[(e.target == "level") & (e["var"] == "gap_cs")].set_index("year")["beta"]

    cards = (card("0 → 247 → 544", "负电价小时 (23/24/25)", "2023 无负价, 2025 占 6.2%")
             + card("0% → 27.6% → 55.5%", "高缺口小时负价频率", "缺口 = 供给过剩标记")
             + card(f"{lvl.loc[2023]:.1f} → {lvl.loc[2025]:.1f}", "光伏水平弹性 (€/MWh per GW)", "光伏→电价 效应逐年增强")
             + card("0.97~0.98", "逐小时相关", "物理链路三年稳定"))

    rows = ""
    for y, r in s.iterrows():
        rows += (f'<tr><td>{y}</td><td>{r["GW"]:.2f}</td><td>{r["ilr"]:.2f}</td>'
                 f'<td>{r["r"]:.4f}</td><td>{r["energy_ratio"]:.3f}</td>'
                 f'<td>{r["cf_pot"]:.3f}/{r["cf_act"]:.3f}</td>'
                 f'<td>{r["price_mean"]:.2f}</td><td>{r["price_min"]:.2f}</td>'
                 f'<td>{int(r["neg_h"])}</td><td>{r["neg_pct"]:.2f}%</td></tr>')

    el = ""
    for _, r in e.iterrows():
        unit = "%/GW" if r["target"] == "log" else "€/MWh per GW"
        cl = "neg" if r["beta"] < 0 else "pos"
        tgt = "log" if r["target"] == "log" else "水平"
        el += (f'<tr><td>{int(r["year"])}</td><td>{tgt}</td>'
               f'<td>{r["var"]}</td><td class="{cl}">{r["beta"]:+.3f}</td>'
               f'<td>{r["se"]:.3f}</td><td>{unit}</td></tr>')

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙光伏链路 · 市场区间对比 2023-2025</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.65}}
.wrap{{max-width:980px;margin:0 auto;padding:28px 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#fff;border-radius:12px;padding:15px 17px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:180px}}
.card .v{{font-size:23px;font-weight:700;color:#1f5bb8}}.card .t{{font-weight:600;margin-top:4px}}
.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:7px 9px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
td:first-child,th:first-child{{text-align:left}}
.neg{{color:#c23a3a;font-weight:600}}.pos{{color:#1f5bb8;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}li{{margin:5px 0}}
.hl{{background:#fff6ea;border-left:3px solid #e5853a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}
</style></head><body><div class="wrap">
<h1>西班牙光伏链路 · 市场区间对比（2023 → 2025）</h1>
<div class="sub">用与 PS-021/030 同法的物理链路（NASA POWER 辐照 → pvlib 单轴跟踪 → PVWatts，ILR 逐年标定），
在同一组 120 个采样点上跑 2023/2024/2025 三年，观察高可再生渗透 + 负电价 + 弃电区间下"缺口"含义的变化 · 核查日 2026-09-28</div>

<div class="cards">{cards}</div>

<div class="hl"><b>核心结论</b>：随着西班牙光伏从 26.6 GW 增至 31.3 GW、负电价从 0 小时增至 544 小时，
"资源潜力 − 实际出力"这一缺口的含义<b>从无害变为强供给过剩标记</b>——高缺口小时出现负电价的频率从 <b>0% → 27.6% → 55.5%</b>（低缺口小时仅 0~0.2%），
且高缺口小时负荷显著更低。这正是 PS-028 在 ERCOT 风电上发现的"缺口=内生弃电"机制，<b>在西班牙以光伏形式重现</b>，
说明该机制取决于<b>市场成熟度（弃电普及度）而非电源技术</b>。</div>

<div class="box"><h2 style="margin-top:0">① 三年模型验证与市场状态</h2>
<div class="scroll"><table>
<tr><th>年</th><th>装机 GW</th><th>标定 ILR</th><th>r</th><th>能量比</th><th>CF 潜力/实际</th>
<th>均价 €/MWh</th><th>最低价</th><th>负价小时</th><th>负价占比</th></tr>
{rows}
</table></div>
<div class="note">物理链路三年精度稳定（r = 0.9845 / 0.9800 / 0.9711，能量比 0.976 / 0.989 / 1.015）。
标定 ILR 由 0.85 升至 1.05 —— 仍<b>远低于 ERCOT 的 1.30</b>，再次印证 PS-030 的"标定参数不可跨市场移植"。
2024 年负价 247 小时与公开统计（Electricity Maps 口径 247 h）<b>完全一致</b>；2025 年 544 h（REE 口径 ≤0 为 798 h，本表 ≤0 计 783 h），差异源于小时/15 分钟与是否含零价的统计口径。</div></div>

<div class="box"><h2 style="margin-top:0">② 负电价常态化</h2>
{svg_negbar(s.reset_index())}
<div class="note">2023 年西班牙<b>尚未出现负电价</b>（首次负价在 2024-04-01），2024 年 247 小时、2025 年 544 小时（6.2%），
最低价由 0.00 → −2.00 → <b>−15.00 €/MWh</b>。均价同时从 87.11 降到 63~66 €/MWh。</div></div>

<div class="box"><h2 style="margin-top:0">③ 机制：缺口如何变成"供给过剩标记"</h2>
{svg_mech(s.reset_index())}
<div class="note">把白天小时按"天气缺口 = 潜力 − 实际"分位分组：<br>
• <b>高缺口组（>P90）负价频率 0% → 27.6% → 55.5%</b>；低缺口组仅 0% → 0.1% → 0.2%；<br>
• 高缺口组的负荷中位<b>更低</b>（2025: 25,437 vs 27,514 MW）—— 高缺口 ≠ 供不应求，而是高资源 + 低需求；<br>
• 缺口集中在 09–15 UTC 的正午时段（2025: 09h 1,868 MW、11h 1,413 MW、13h 1,299 MW），18h 后归零。<br>
⇒ 这与 PS-028 在 ERCOT 风电上的判据完全同构：<b>高缺口小时是弃电/供给过剩的标志，而非缺电</b>。</div></div>

<div class="box"><h2 style="margin-top:0">④ 缺口与出力的价格弹性</h2>
<div class="scroll"><table><tr><th>年</th><th>目标</th><th>变量</th><th>弹性</th><th>SE</th><th>单位</th></tr>{el}</table></div>
<div class="note">
• <b>光伏出力水平</b>：水平口径 {lvl.loc[2023]:+.2f} → {lvl.loc[2024]:+.2f} → {lvl.loc[2025]:+.2f} €/MWh per GW，
log 口径 −2.83 → −9.59 → −10.47 %/GW ⇒ <b>光伏对电价的压制效应随渗透率上升而显著增强</b>（同号且一致于 ERCOT 的 −4.9 %/GW）。<br>
• <b>晴空缺口（云）</b>：水平口径 {gapcs.loc[2023]:+.2f} → {gapcs.loc[2024]:+.2f} → {gapcs.loc[2025]:+.2f} €/MWh per GW，<b>恒为正</b> ⇒ 外生云致缺口推高电价，与 PS-024 的 +5 %/GW 同号。<br>
• <b>天气缺口（潜力−实际）</b>：水平口径 {gapw.loc[2023]:+.2f} → {gapw.loc[2024]:+.2f} → {gapw.loc[2025]:+.2f}，log 口径 −39.4 → −31.5 → −23.9 %/GW，<b>恒为负</b> ⇒ 与晴空缺口符号相反。<br>
⇒ 同一市场内，"外生天气缺口"（正）与"内生过剩缺口"（负）<b>并存且符号相反</b>，把 PS-028 的"风光不对称"升级为更一般的判据：
<b>决定缺口符号的是缺口的成因（外生供给损失 vs 内生供给过剩），而非电源类型。</b></div></div>

<div class="box"><h2 style="margin-top:0">⑤ 结论与局限</h2>
<ul class="note">
<li><b>结论一（验证 PS-028 机制）</b>：在弃电普及的市场，"潜力−实际"缺口是供给过剩标记（高缺口小时负价频率 55.5%），机制与 ERCOT 风电一致。</li>
<li><b>结论二（升级 PS-028 判据）</b>：风口不对称的根源是<b>缺口成因</b>。西班牙同一市场内晴空缺口为正、天气缺口为负，说明"技术"不是关键变量，"外生 vs 内生"才是。</li>
<li><b>结论三（渗透率效应）</b>：光伏出力对电价的压制弹性随装机从 26.6→31.3 GW 而增强（水平口径 −3.42→−4.86 €/MWh per GW），负电价与压价效应同步放大。</li>
<li><b>局限</b>：①NASA POWER（MERRA-2 再分析，非卫星）辐照精度有限，ILR 近年上升可能部分吸收清单/口径误差；②GEM 清单为 2026-08 快照按 start-year 回推，与当年真实投产存在偏差；③实际发电取 ENTSO-E/Energy-Charts 口径，与 REE 官网口径略有差异（2025 负价 544 vs 477 小时）；④西班牙无 ERCOT 式 RTM，本流程用日前价，<b>不可与 ERCOT 实时尖峰弹性直接数值对比</b>；⑤15 分钟→小时平均会削平极端值，2025 年的负价深度可能被低估。</li>
<li><b>下一步</b>：申请 ESIOS token 取 5 分钟级实际出力与日内连续价，量化"缺口→负价"的分钟级触发；把同一套判据（外生缺口 vs 内生缺口）应用到 ERCOT 已有的 2022-07 与 2025-26 数据，检验判据的可逆性。</li>
</ul></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"→ {p}")


if __name__ == "__main__":
    build()