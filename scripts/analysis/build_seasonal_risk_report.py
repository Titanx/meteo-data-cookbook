"""季节预报光伏缺口风险概率化 → 自包含 HTML 报告
读取 data/openmeteo_seasonal/seasonal_shortfall_risk*.csv / streak, 生成 report.
"""
import csv
import os

import pandas as pd

D = r"c:\work\meteo\data\openmeteo_seasonal"
OUT = r"c:\work\meteo\output\seasonal_shortfall_risk"
os.makedirs(OUT, exist_ok=True)


def esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load():
    daily = pd.read_csv(os.path.join(D, "seasonal_shortfall_risk.csv"),
                        encoding="utf-8-sig")
    weekly = pd.read_csv(os.path.join(D, "seasonal_shortfall_risk_weekly.csv"),
                         encoding="utf-8-sig")
    streak = pd.read_csv(os.path.join(D, "seasonal_streak_risk.csv"),
                         encoding="utf-8-sig")
    return daily, weekly, streak


def svg_timeline(daily):
    w, h, pad = 860, 300, (54, 12, 34, 44)  # l r t b
    x0, x1 = pad[3], w - pad[1]
    y0, y1 = pad[2], h - pad[0]
    tau_max = 1.0
    n = len(daily)
    xpos = lambda i: x0 + (x1 - x0) * i / max(n - 1, 1)
    ytau = lambda v: y1 - (y1 - y0) * v / tau_max
    yp = lambda v: y1 - (y1 - y0) * v / 1.0

    # grid
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
         f'font-family="Segoe UI,Arial" font-size="11">']
    for g in (0, 0.25, 0.5, 0.75, 1.0):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{ytau(g):.0f}" y2="{ytau(g):.0f}" '
                 f'stroke="#e7eef4" stroke-width="1"/>')
        s.append(f'<text x="{x0-6}" y="{ytau(g)+3:.0f}" text-anchor="end" '
                 f'fill="#8aa0b4">τ={g:.2f}</text>')

    # historical threshold lines
    for lab, lv, col in (("Q25 轻缺", 0.52, "#e5853a"),
                         ("Q10 重缺", 0.38, "#c23a3a")):
        yy = ytau(lv)
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{yy:.0f}" y2="{yy:.0f}" '
                 f'stroke="{col}" stroke-width="1" stroke-dasharray="4 3"/>')
        s.append(f'<text x="{x1-4}" y="{yy-4:.0f}" text-anchor="end" fill="{col}">{lab}</text>')

    # P_轻缺日 bars at bottom
    for i, (_, r) in enumerate(daily.iterrows()):
        rw = (x1 - x0) / n * 0.5
        cx = xpos(i)
        pv = r["P_轻缺日"]
        by = yp(pv)
        s.append(f'<rect x="{cx-rw/2:.0f}" y="{by:.0f}" width="{rw:.0f}" '
                 f'height="{y1-by:.0f}" fill="#3a7ce5" opacity="{0.25+0.55*pv:.2f}"/>')
        if pv >= 0.1:
            s.append(f'<text x="{cx:.0f}" y="{by-3:.0f}" text-anchor="middle" '
                     f'fill="#2c5fb0">{pv:.0f}</text>')

    # tau band (p10-p90) then median
    band = []
    for i, (_, r) in enumerate(daily.iterrows()):
        band.append(f'{xpos(i):.0f},{ytau(r["tau_p90"]):.0f}')
    band += [f'{xpos(j):.0f},{ytau(daily.iloc[j]["tau_p10"]):.0f}'
             for j in range(n - 1, -1, -1)]
    s.append(f'<polygon points="{" ".join(band)}" fill="#3a7ce5" opacity="0.22"/>')

    med = " ".join(f'{xpos(i):.0f},{ytau(daily.iloc[i]["tau_p50"]):.0f}'
                   for i in range(n))
    s.append(f'<polyline points="{med}" fill="none" stroke="#1f5bb8" '
             f'stroke-width="2.2"/>')

    # x labels every ~6 days
    for i in range(0, n, 6):
        dt = pd.to_datetime(daily.iloc[i]["date"])
        s.append(f'<text x="{xpos(i):.0f}" y="{h-14}" text-anchor="middle" '
                 f'fill="#8aa0b4">{dt.strftime("%m-%d")}</text>')
    s.append(f'<text x="{x0}" y="{h-26}" text-anchor="start" fill="#5b7488">'
             f'fleet 日传输率 τ (蓝带=P10-P90, 实线=中位) 叠加 P(轻缺日) 蓝色条形 → 未来45天</text>')
    s.append("</svg>")
    return "\n".join(s)


def svg_weekly(weekly):
    w, h, pad = 860, 240, (54, 12, 26, 44)
    x0, x1 = pad[3], w - pad[1]
    y0, y1 = pad[2], h - pad[0]
    n = len(weekly)
    bw = (x1 - x0) / n
    xc = lambda i: x0 + bw * (i + 0.5)
    yv = lambda v: y1 - (y1 - y0) * v / 0.30
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
         f'font-family="Segoe UI,Arial" font-size="11">']
    for g in (0, 0.1, 0.2, 0.3):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{yv(g):.0f}" y2="{yv(g):.0f}" '
                 f'stroke="#e7eef4"/>')
        s.append(f'<text x="{x0-6}" y="{yv(g)+3:.0f}" text-anchor="end" fill="#8aa0b4">{g}</text>')
    colors = {"P_轻缺日周均": "#3a7ce5", "P_重缺日周均": "#c23a3a",
              "P_危险周均": "#e5853a"}
    keys = list(colors)
    wb = bw * 0.8 / 3
    for i, grp in enumerate(zip(*[weekly[k] for k in keys])):
        cx = xc(i)
        for j, (k, v) in enumerate(zip(keys, grp)):
            x = cx - wb * 1.5 + j * wb
            s.append(f'<rect x="{x:.0f}" y="{yv(v):.0f}" width="{wb-2:.0f}" '
                     f'height="{y1-yv(v):.0f}" fill="{colors[k]}"/>')
            if v > 0.01:
                s.append(f'<text x="{x+wb/2:.0f}" y="{yv(v)-3:.0f}" text-anchor="middle" '
                         f'fill="#5b7488">{v:.2f}</text>')
    for i, (_, r) in enumerate(weekly.iterrows()):
        s.append(f'<text x="{xc(i):.0f}" y="{h-14}" text-anchor="middle" fill="#8aa0b4">'
                 f'W{int(r["周"])}\n</text>')
    s.append(f'<text x="{x0}" y="{h-26}" text-anchor="start" fill="#5b7488">'
             f'逐周风险: 蓝=轻缺 / 红=重缺 / 橙=危险云系(缺∧热)</text>')
    # legend
    for j, k in enumerate(keys):
        yy = 18
        s.append(f'<rect x="{x0+j*120:.0f}" y="{yy-9}" width="12" height="12" fill="{colors[k]}"/>')
        s.append(f'<text x="{x0+j*120+16:.0f}" y="{yy}" fill="#5b7488">{k}</text>')
    s.append("</svg>")
    return "\n".join(s)


def svg_streak(streak):
    w, h, pad = 520, 180, (48, 12, 26, 40)
    x0, x1 = pad[3], w - pad[1]
    y0, y1 = pad[2], h - pad[0]
    mx = int(streak["max_streak_day"].max())
    counts = dict(zip(streak["max_streak_day"], streak["n_members"]))
    vals = [counts.get(i, 0) for i in range(mx + 1)]
    vmax = max(vals) or 1
    bw = (x1 - x0) / (mx + 1)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
         f'font-family="Segoe UI,Arial" font-size="11">']
    for i, v in enumerate(vals):
        x = x0 + i * bw
        hh = (y1 - y0) * v / vmax
        s.append(f'<rect x="{x+2:.0f}" y="{y1-hh:.0f}" width="{bw-4:.0f}" '
                 f'height="{hh:.0f}" fill="#3a7ce5"/>')
        if v:
            s.append(f'<text x="{x+bw/2:.0f}" y="{y1-hh-4:.0f}" text-anchor="middle" '
                     f'fill="#2c5fb0">{int(v)}</text>')
        s.append(f'<text x="{x+bw/2:.0f}" y="{h-12}" text-anchor="middle" fill="#8aa0b4">{i}</text>')
    s.append("</svg>")
    return "\n".join(s)


def build():
    daily, weekly, streak = load()
    p_mild = daily["P_轻缺日"].mean()
    p_sev = daily["P_重缺日"].mean()
    p5 = (streak[streak["max_streak_day"] >= 5]["n_members"].sum()
          / streak["n_members"].sum())
    p_haz = daily["P_危险"].max()
    haz_date = pd.to_datetime(daily.loc[daily["P_危险"].idxmax(), "date"]).date()
    tau_mid = daily["tau_p50"].median()
    sf_p90_peak = daily["sf_p90"].max()

    cards = [
        ("轻缺日均概率", f"{p_mild:.1%}", "比气候最差25%更阴的天, 未来45天日均"),
        ("重缺日均概率", f"{p_sev:.1%}", "与气候最差10%(重度缺电)天相当"),
        ("连阴≥5天概率", f"{p5:.0%}", "未来45天内出现≥5天轻缺连阴"),
        ("危险云系峰值P", f"{p_haz:.1%}", f"轻缺∧高温组合峰值 ({haz_date})"),
    ]
    card_html = ""
    for t, v, d in cards:
        card_html += (f'<div class="card"><div class="v">{v}</div>'
                      f'<div class="t">{t}</div><div class="d">{d}</div></div>')

    rows = ""
    for _, r in daily.iterrows():
        dt = pd.to_datetime(r["date"]).strftime("%m-%d")
        rows += (f'<tr><td>{dt}</td>'
                 f'<td>{r["tau_p50"]:.2f}</td><td>{r["tau_p10"]:.2f}</td>'
                 f'<td>{r["sf_p50"]:.0f}</td><td>{r["sf_p90"]:.0f}</td><td>{r["sf_p99"]:.0f}</td>'
                 f'<td>{r["P_轻缺日"]:.2f}</td><td>{r["P_重缺日"]:.2f}</td>'
                 f'<td>{r["tmax_p50"]:.1f}°</td><td>{r["P_危险"]:.2f}</td></tr>')

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>季节预报 → 光伏缺口风险概率化 (未来45天)</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c}}
.wrap{{max-width:960px;margin:0 auto;padding:28px 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:28px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:18px}}
.card{{background:#fff;border-radius:12px;padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:170px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card .v{{font-size:28px;font-weight:700;color:#1f5bb8}}.card .t{{font-weight:600;margin-top:4px}}
.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
.box{{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:6px 8px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;position:sticky;top:0;background:#fff}}
td:first-child,th:first-child{{text-align:left;font-weight:600;color:#22303c}}
.tag{{display:inline-block;background:#eaf1fb;color:#1f5bb8;border-radius:6px;
padding:1px 8px;font-size:11.5px;margin-right:6px}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.7}}
li{{margin:5px 0}}
.scroll{{overflow-x:auto}}
</style></head><body><div class="wrap">
<h1>季节预报 → 光伏缺口风险概率化</h1>
<div class="sub">Open-Meteo Seasonal (EC46/SEAS5) 50 成员聚合预报 · 未来 45 天 (2026-09-28 ~ 2026-11-11) ·
fleet = 141 座 ≥100MW 光伏电站 (30.9 GW) · 气候校准口径（相对历史缺日）</div>

<div class="cards">{card_html}</div>

<div class="box">
<h2 style="margin-top:0">① 未来45天日传输率 τ 轨迹 + 轻缺日概率</h2>
{svg_timeline(daily)}
<div class="note">τ = 日短波总量 / 晴空日总量 (纯云量指数)。灰虚线为历史 Q25(轻缺日阈)/Q10(重缺日阈)。
τ 中位 {tau_mid:.2f} vs 历史中位 0.70 → 整体接近常年阳光。最大 P90 缺口 {sf_p90_peak:.0f} GWh/日。</div>
</div>

<div class="box">
<h2 style="margin-top:0">② 逐周风险</h2>
{svg_weekly(weekly)}
</div>

<div class="box">
<div style="display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap">
<div><h2 style="margin-top:0">③ 连阴 streak 成员分布</h2>
{svg_streak(streak)}
<span class="note">最多连续轻缺天数 (50 成员) —— 无任何成员出现 ≥6 天连阴。</span></div>
<ul style="text-align:left;margin-top:24px" class="note">
<li><b>读数</b>: 未来45天整体<b>阳光正常偏低风险</b>——轻缺日均概率 {p_mild:.1%}, 重缺 {p_sev:.1%}, 无 ≥5 天连阴成员。</li>
<li><b>季节含义</b>: 时段处于暖季末/凉季初, 高温日(≥32°C)迅速归零 → <b>“缺日∧高温”危险云系结构上缺席</b>(峰值P {p_haz:.1%}), 电价冲击主轴从“云×热”转向“单纯云缺”。</li>
<li><b>信号排序</b>: 集合在 10/01-10/03 看到一段短暂的阴天窗口 (轻缺日 P 升至 0.14-0.22), 之后回落; 10月底-11月初 (W5-W6) 缺日概率小幅抬升 (0.10-0.12)。</li>
</ul>
</div>
</div>

<div class="box">
<h2 style="margin-top:0">④ 逐日明细</h2>
<div class="scroll"><table><thead>
<tr><th>日期</th><th>τ中位</th><th>τ_P10</th><th>缺口P50<br>GWh</th><th>缺口P90<br>GWh</th>
<th>缺口P99<br>GWh</th><th>P轻缺</th><th>P重缺</th><th>Tmax中位</th><th>P危险</th></tr>
</thead><tbody>{rows}</tbody></table></div>
</div>

<div class="box"><h2 style="margin-top:0">方法 & 局限（务必读）</h2>
<ul class="note">
<li><b>链路</b>: pvlib 晴空基准 → 141 站按最近站点 + 太阳容量加权 → fleet 日传输率 τ → 缺口 = 晴空日能源×(1-τ)（<b>日能源口径 = 缺口下界</b>, 日内云相位不分辨）。</li>
<li><b>气候校准</b>: seasonal 聚合逐日短波重度平滑 ⇒ 集合发散远小于真实日际变化。因此不用绝对 τ 阈值, 而用<b>历史 τ 分布 (2025-26, 602 天)</b>的 Q25/Q10 作“轻缺/重缺”相对阈值, 把预报 τ 映射成“比气候更阴”的尾部概率, 避免低估。</li>
<li><b>未校准声明</b>: 无多年季节回算 (需 WMO S2S/ECMWF 认证) ⇒ 概率为<b>原始集合频率</b>, 非校准后概率; 数值宜读相对高低(风险排序), 不宜当精确百分率。</li>
<li><b>单点 vs fleet</b>: 6 站预报覆盖少; 电站按最近站归属会导致局部云系被摊平, 或缺日概率被轻微低估。</li>
<li><b>温度-负荷</b>: 危险云系用绝对 32°C 热日; 未耦合实时负荷预测 (EIA 负荷>38°C 才见真正尖峰)。此窗口基本无热日, 结论稳健。</li>
</ul></div>
</div></body></html>"""
    path = os.path.join(OUT, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"→ {path}")


if __name__ == "__main__":
    build()