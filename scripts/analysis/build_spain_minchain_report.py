"""西班牙光伏最小链路报告 (自包含 HTML)
输入: data/spain/spain_pv_hourly_2023.csv, spain_elasticity_2023.csv
输出: output/spain_minchain/index.html
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_minchain"
os.makedirs(OUT, exist_ok=True)
CAP_GW = 26.65
BLUE, RED, ORANGE, GREY, GREEN = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4", "#2f8f6b"
ILR_CAL = [(0.80, 0.92), (0.85, 0.979), (0.90, 1.036), (1.00, 1.151),
           (1.10, 1.266), (1.20, 1.381), (1.30, 1.496)]


def svg_monthly(h):
    w, ht, pad = 860, 300, (54, 16, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    m = h.resample("MS").agg(pot=("pv_pot_mw", "sum"), act=("solar_actual_mw", "sum")) / 1e3
    n = len(m)
    bw = (x1 - x0) / n
    ymax = max(m.max()) * 1.14
    yp = lambda v: y1 - (y1 - y0) * v / ymax
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for g in np.linspace(0, ymax, 5):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{yp(g):.0f}" y2="{yp(g):.0f}" stroke="#e7eef4"/>')
        s.append(f'<text x="{x0-6}" y="{yp(g)+3:.0f}" text-anchor="end" fill="{GREY}">{g:.0f}</text>')
    for i, (idx, r) in enumerate(m.iterrows()):
        x = x0 + i * bw
        s.append(f'<rect x="{x+3:.0f}" y="{yp(r["pot"]):.0f}" width="{bw/2-4:.0f}" height="{y1-yp(r["pot"]):.0f}" fill="{BLUE}" opacity="0.55"/>')
        s.append(f'<rect x="{x+bw/2:.0f}" y="{yp(r["act"]):.0f}" width="{bw/2-4:.0f}" height="{y1-yp(r["act"]):.0f}" fill="{GREEN}"/>')
        s.append(f'<text x="{x+bw/2:.0f}" y="{ht-30}" text-anchor="middle" fill="{GREY}">{idx.strftime("%m")}</text>')
    s.append(f'<text x="{x0+6}" y="{y0-6}" fill="{BLUE}">■ 模型潜力</text>')
    s.append(f'<text x="{x0+110}" y="{y0-6}" fill="{GREEN}">■ 实际 (Energy-Charts)</text>')
    s.append(f'<text x="{x1}" y="{y0-6}" text-anchor="end" fill="{GREY}">月能量 GWh</text>')
    s.append("</svg>")
    return "\n".join(s)


def svg_ilr():
    w, ht, pad = 860, 280, (54, 16, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    xs = [a for a, _ in ILR_CAL]
    ys = [b for _, b in ILR_CAL]
    X = lambda v: x0 + (x1 - x0) * (v - min(xs)) / (max(xs) - min(xs))
    Y = lambda v: y1 - (y1 - y0) * (v - 0.85) / (1.55 - 0.85)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for g in (0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(g):.0f}" y2="{Y(g):.0f}" stroke="#e7eef4"/>')
        s.append(f'<text x="{x0-6}" y="{Y(g)+3:.0f}" text-anchor="end" fill="{GREY}">{g:.1f}</text>')
    s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(1.0):.0f}" y2="{Y(1.0):.0f}" stroke="{GREEN}" stroke-width="1.6" stroke-dasharray="5 4"/>')
    s.append(f'<text x="{x1-4}" y="{Y(1.0)-5:.0f}" text-anchor="end" fill="{GREEN}">完美匹配 (比值=1)</text>')
    pts = " ".join(f"{X(a):.0f},{Y(b):.0f}" for a, b in ILR_CAL)
    s.append(f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="2.4"/>')
    for a, b in ILR_CAL:
        s.append(f'<circle cx="{X(a):.0f}" cy="{Y(b):.0f}" r="3.4" fill="{BLUE}"/>')
    s.append(f'<line x1="{X(1.30):.0f}" x2="{X(1.30):.0f}" y1="{y0}" y2="{y1}" stroke="{RED}" stroke-width="1.4" stroke-dasharray="4 3"/>')
    s.append(f'<text x="{X(1.30)-6:.0f}" y="{y0+14}" text-anchor="end" fill="{RED}">ERCOT 标定值 1.30 → 高估 50%</text>')
    s.append(f'<text x="{X(0.85):.0f}" y="{y1-8}" text-anchor="middle" fill="{GREEN}">西班牙 0.85</text>')
    for a in xs:
        s.append(f'<text x="{X(a):.0f}" y="{ht-30}" text-anchor="middle" fill="{GREY}">{a:.2f}</text>')
    s.append(f'<text x="{(x0+x1)/2:.0f}" y="{ht-10}" text-anchor="middle" fill="#5b7488">ILR (直流/交流容量比) → 年潜力/实际 比值</text>')
    s.append("</svg>")
    return "\n".join(s)


def svg_price_level(h):
    w, ht, pad = 860, 300, (54, 16, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    d = h[h["solar_actual_mw"] > 50].copy()
    d["q"] = pd.qcut(d["solar_actual_mw"], 10, labels=False, duplicates="drop")
    g = d.groupby("q").agg(p=("price", "median"), s=("solar_actual_mw", "median"))
    lo, hi = g["p"].min() * 0.9, g["p"].max() * 1.06
    X = lambda i: x0 + (x1 - x0) * i / 9
    Y = lambda v: y1 - (y1 - y0) * (v - lo) / (hi - lo)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for v in np.linspace(lo, hi, 5):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(v):.0f}" y2="{Y(v):.0f}" stroke="#e7eef4"/>')
        s.append(f'<text x="{x0-6}" y="{Y(v)+3:.0f}" text-anchor="end" fill="{GREY}">{v:.0f}</text>')
    pts = " ".join(f"{X(i):.0f},{Y(v):.0f}" for i, v in g["p"].items())
    s.append(f'<polyline points="{pts}" fill="none" stroke="{ORANGE}" stroke-width="2.4"/>')
    for i, v in g["p"].items():
        s.append(f'<circle cx="{X(i):.0f}" cy="{Y(v):.0f}" r="3.4" fill="{ORANGE}"/>')
    for i in range(10):
        s.append(f'<text x="{X(i):.0f}" y="{ht-30}" text-anchor="middle" fill="{GREY}">{i+1}</text>')
    s.append(f'<text x="{x0+6}" y="{y0-6}" fill="{ORANGE}">━ 该十分位的日前电价中位</text>')
    s.append(f'<text x="{x1}" y="{y0-6}" text-anchor="end" fill="{GREY}">€/MWh</text>')
    s.append(f'<text x="{(x0+x1)/2:.0f}" y="{ht-10}" text-anchor="middle" fill="#5b7488">实际光伏出力十分位 (1=最低, 10=最高) → 白天小时</text>')
    s.append("</svg>")
    return "\n".join(s)


def build():
    h = pd.read_csv(os.path.join(D, "spain_pv_hourly_2023.csv"), index_col=0, parse_dates=True)
    e = pd.read_csv(os.path.join(D, "spain_elasticity_2023.csv"))
    r = h["pv_pot_mw"].corr(h["solar_actual_mw"])
    ratio = h["pv_pot_mw"].sum() / h["solar_actual_mw"].sum()
    cs = h["pv_clearsky_mw"].sum() / h["solar_actual_mw"].sum()
    m = h.resample("MS").agg(p=("pv_pot_mw", "sum"), a=("solar_actual_mw", "sum"))
    mr = (m["p"] / m["a"])
    lvl = e[e["model"] == "solar_actual_mw"]["estimate_pct_per_gw"].iloc[0]
    lvse = e[e["model"] == "solar_actual_mw"]["se_pct_per_gw"].iloc[0]

    def card(v, t, d):
        return f'<div class="card"><div class="v">{v}</div><div class="t">{t}</div><div class="d">{d}</div></div>'

    cards = (card(f"{r:.4f}", "逐小时相关", "模型潜力 × 实际光伏 (2023)")
             + card(f"{ratio:.3f}", "年能量比", "标定后; 潜力 39.6 vs 实际 40.4 TWh")
             + card("0.85", "标定 ILR", "ERCOT 1.30 → 高估 50%")
             + card(f"{lvl:+.1f} %/GW", "光伏水平→电价", f"SE {lvse:.2f}; 与 ERCOT −4.9 同号"))

    rows = ""
    for _, x in m.iterrows():
        rows += (f'<tr><td>{x.name.strftime("%Y-%m")}</td><td>{x["p"]/1e3:.0f}</td>'
                 f'<td>{x["a"]/1e3:.0f}</td><td>{(x["p"]/x["a"]):.3f}</td></tr>')

    el_rows = ""
    for _, x in e.iterrows():
        cl = "neg" if x["estimate_pct_per_gw"] < 0 else "pos"
        el_rows += (f'<tr><td>{x["model"]}</td><td class="{cl}">{x["estimate_pct_per_gw"]:+.3f}</td>'
                    f'<td>{x["se_pct_per_gw"]:.3f}</td><td>{int(x["n"])}</td></tr>')

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙光伏最小链路 (免注册数据源)</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.65}}
.wrap{{max-width:980px;margin:0 auto;padding:28px 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#fff;border-radius:12px;padding:15px 17px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:165px}}
.card .v{{font-size:25px;font-weight:700;color:#1f5bb8}}.card .t{{font-weight:600;margin-top:4px}}
.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:7px 9px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
td:first-child,th:first-child{{text-align:left}}
.neg{{color:#c23a3a;font-weight:600}}.pos{{color:#1f5bb8;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}li{{margin:5px 0}}
.hl{{background:#eef5ff;border-left:3px solid #1f5bb8;padding:12px 16px;border-radius:6px;margin:14px 0}}
.ok{{color:#2f8f6b;font-weight:600}}
.scroll{{overflow-x:auto}}
</style></head><body><div class="wrap">
<h1>西班牙光伏最小链路</h1>
<div class="sub">目标：用<b>全部免注册</b>的数据源复刻 ERCOT 的 NSRDB+pvlib 出力建模（PS-021）到西班牙，并与实际发电对照 ·
2023 全年 · 120 个容量加权采样点 / 26.65 GW（GEM 西班牙光伏 96.3%）· 核查日 2026-09-28</div>

<div class="cards">{cards}</div>

<div class="hl"><b>结论</b>：链路建成且验证通过——逐小时相关 <b>r={r:.4f}</b>，标定后年能量比 <b>{ratio:.3f}</b>（潜力 {h['pv_pot_mw'].sum()/1e6:.1f} vs 实际 {h['solar_actual_mw'].sum()/1e6:.1f} TWh）。
但<b>ERCOT 的标定参数不可直接移植</b>：沿用 ERCOT 的 ILR=1.30 会高估 <b>50%</b>，西班牙需降到 <b>0.85</b>。
电价方向上"光伏出力↑→电价↓"（{lvl:+.2f} %/GW）与 ERCOT（−4.9 %/GW）<b>同号</b>，但 2023 年是负电价出现前的年份，真正有价值的区间从 2024 起。</div>

<div class="box"><h2 style="margin-top:0">① 数据源：全部免注册（实测）</h2>
<div class="scroll"><table>
<tr><th>环节</th><th>数据源</th><th>粒度/覆盖</th><th>本轮取数</th></tr>
<tr><td>电站清单</td><td>GEM 全球光伏追踪</td><td>厂站坐标/容量, 西班牙 operating ≤2023</td><td>2,080 座 / 27.66 GW → 120 采样点</td></tr>
<tr><td>辐照+气温</td><td>NASA POWER (MERRA-2)</td><td>逐小时 GHI/DNI/DHI/T2m, 全球, 2001–</td><td>120 点 × 8,760 h</td></tr>
<tr><td>辐照交叉校验</td><td>PVGIS-SARAH3 (EUMETSAT)</td><td>逐小时 POA, 欧洲, 2005–2023</td><td>前 12 大站点</td></tr>
<tr><td>实际光伏/风电/负荷</td><td>Energy-Charts (Fraunhofer ISE)</td><td>15 min, 西班牙, ENTSO-E 口径</td><td>35,040 点 (Solar 峰值 17,668 MW)</td></tr>
<tr><td>日前电价</td><td>Energy-Charts / OMIE</td><td>逐小时 (2023), €/MWh</td><td>8,760 点, 均价 87.10 €/MWh</td></tr>
</table></div>
<div class="note">NASA POWER 是本轮的关键替代：Open-Meteo 存档 API 在批量取数时触发"每小时请求上限"被硬阻断；NASA POWER 无条件放行且提供完整辐照分量（GHI/DNI/DHI），使单轴跟踪建模成为可能。</div></div>

<div class="box"><h2 style="margin-top:0">② 链路与验证</h2>
{svg_monthly(h)}
<div class="note">链路与 PS-021 完全同法：单轴跟踪 POA（±60°、backtracking、gcr 0.35）→ 电池温度 <code>Tcell = Tamb + POA/800×25</code>
→ PVWatts（γ=−0.0037、系统损耗 14%、逆变效率 0.96、AC 限幅）→ 120 点求和。
逐小时 <b>r={r:.4f}</b>（lag 0；lag±1 降至 0.90/0.95，说明时点对齐正确）；容量因子 潜力 {h['pv_pot_mw'].mean()/1e3/CAP_GW:.3f} vs 实际 {h['solar_actual_mw'].mean()/1e3/CAP_GW:.3f} —— 几乎相同。
月比值区间 <b>{mr.min():.3f}–{mr.max():.3f}</b>，夏秋偏低（0.88–0.98）、深冬偏高（1.20），提示 NASA POWER 在冬季辐照上略高估。</div>

<div class="box"><h2 style="margin-top:0">③ 关键发现：标定参数不可跨市场移植</h2>
{svg_ilr()}
<div class="note">ERCOT 的 ILR=1.30（PS-021 扫描得出）用到西班牙会高估 <b>50%</b>；把年能量标到接近实际需要 <b>ILR≈0.85</b>。
原因有三：(a) 西班牙光伏以固定倾角为主、跟踪器比例低于 ERCOT，单位容量的 POA 增益更小；
(b) 西班牙电站直流/交流比普遍低于 ERCOT 的 1.25~1.35；
(c) GEM 清单与 TSO 可见发电的口径差（分布式自消费未计入实际）。
⇒ <b>跨市场复刻时，容量/ILR 等标定参数必须重新标定</b>，这与 PS-029 "结构性差异" 的判断一致。</div>

<div class="box"><h2 style="margin-top:0">④ 电价方向与 ERCOT 一致，但分解不可识别</h2>
{svg_price_level(h)}
<div class="scroll"><table><tr><th>解释变量</th><th>弹性 %/GW</th><th>SE</th><th>n</th></tr>{el_rows}</table></div>
<div class="note">
① <b>实际光伏水平</b> {lvl:+.2f} %/GW（SE {lvse:.2f}）：光伏出力越高、电价越低，<b>与 ERCOT 的 −4.9 %/GW 同号</b>，方向规律跨市场成立。<br>
② <b>晴空缺口（云）</b> {e[e['model']=='gap_cs']['estimate_pct_per_gw'].iloc[0]:+.2f} %/GW 不显著（SE {e[e['model']=='gap_cs']['se_pct_per_gw'].iloc[0]:.2f}），与 ERCOT 的 +5 %/GW 相反；<br>
③ <b>天气缺口</b> 系数 −53.7（SE 1.8）数值异常 —— 因为缺口 = 潜力 − 实际，与"实际"近乎共线，两者系数<b>不可分开识别</b>（与 PS-028 检验 E 同一问题），该数值不应解读为因果弹性。<br>
⚠ 2023 年西班牙尚未出现负电价（当年 0 小时；首次负价在 <b>2024-04-01</b>），且当年受"伊比利亚例外"天然气限价机制影响，市场结构特殊 ⇒ <b>本表的弹性只宜作方向性参考</b>，真正有意义的高可再生/负价区间应从 2024 年起算。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 辐照源交叉校验</h2>
<div class="scroll"><table><tr><th>站点</th><th>PVGIS-SARAH3 POA (kWh/m²)</th><th>NASA POWER POA</th><th>比值</th></tr>
<tr><td>Cifuentes-Trillo</td><td>1,993.5</td><td>2,008.6</td><td>1.008</td></tr>
<tr><td>Dulcinea</td><td>2,254.4</td><td>2,123.5</td><td>0.942</td></tr>
<tr><td>Talasol</td><td>2,137.4</td><td>2,046.0</td><td>0.957</td></tr>
<tr><td>Talayuela</td><td>2,126.1</td><td>2,073.7</td><td>0.975</td></tr>
<tr><td>Mula</td><td>2,253.9</td><td>2,067.8</td><td>0.917</td></tr>
<tr><td>Amazon Cabrera</td><td>2,264.8</td><td>2,122.3</td><td>0.937</td></tr>
</table></div>
<div class="note">固定 35° 南向 POA 年总量：NASA POWER 相对卫星产品 SARAH-3 在 <b>0.92–1.01</b> 之间（多为低估 4–8%）。
作为"免注册替代方案"，NASA POWER 的资源量级可接受；但若要逼近 NSRDB 级别的辐照质量，应改用 <b>PVGIS-SARAH3</b>（同样免注册，但只给面内辐照、不分量）或注册 <b>CAMS</b>。</div></div>

<div class="box"><h2 style="margin-top:0">⑥ 结论与局限</h2>
<ul class="note">
<li><b>可行性已证实</b>：西班牙光伏链路可完全用免注册数据源（GEM + NASA POWER + Energy-Charts/OMIE）建成，验证精度 r={r:.4f}、能量比 {ratio:.3f}，与 ERCOT 链路同量级。</li>
<li><b>参数不可移植</b>是本轮最有价值的方法论结论：ILR 从 1.30 降到 0.85 才能匹配，跨市场复刻必须重标定。</li>
<li><b>局限</b>：①NASA POWER(MERRA-2) 是再分析、非卫星，冬季辐照略高估，月比值 0.88–1.20；②GEM 清单为 2026-08 快照按 start-year 回推，与 2023 真实在建/投产清单存在偏差；③实际发电取 ENTSO-E/Energy-Charts 口径，与 REE 官网口径可能略有差异；④2023 年无负电价且受"伊比利亚例外"机制影响，弹性只作方向参考；⑤论文/结论层面未做节点级或 15 分钟级对齐。</li>
<li><b>下一步</b>：把年份换到 <b>2024–2025</b>（NASA POWER 与 Energy-Charts 均覆盖），进入负电价与高弃电区间，再检验 PS-028 的"缺口=弃风"与 PS-024 的"缺口→电价"是否在西班牙重现或反转；申请 ESIOS token 以取得实时分技术出力做交叉校验。</li>
</ul></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"→ {p}")


if __name__ == "__main__":
    build()