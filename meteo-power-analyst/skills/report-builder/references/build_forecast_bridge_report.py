"""缺口→电价 日尺度转移函数 与 季节预报展望 报告
输入: data/ercot/forecast_bridge_calibration.csv, data/ercot/forecast_price_outlook.csv
输出: output/forecast_price_bridge/index.html
用法: python skills/report-builder/references/build_forecast_bridge_report.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\ercot"
OUT = r"c:\work\meteo\output\forecast_price_bridge"
os.makedirs(OUT, exist_ok=True)
BLUE, RED, ORANGE, GREY = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4"


def svg_outlook(f, wk):
    w, ht, pad = 840, 330, (54, 18, 64, 56)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    n = len(wk)
    bw = (x1 - x0) / n
    lo = min(wk["prem_p10"].min(), -1)
    hi = max(wk["prem_p90"].max(), 1)
    Y = lambda v: y1 - (y1 - y0) * (v - lo) / (hi - lo)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in np.linspace(lo, hi, 5):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        out.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t:+.0f}</text>')
    out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(0):.0f}" y2="{Y(0):.0f}" stroke="#c9d6e0"/>')
    for i, (_, r) in enumerate(wk.iterrows()):
        cx = x0 + bw * (i + 0.5)
        out.append(f'<line x1="{cx:.0f}" x2="{cx:.0f}" y1="{Y(r["prem_p10"]):.0f}" y2="{Y(r["prem_p90"]):.0f}" stroke="{ORANGE}" stroke-width="2"/>')
        out.append(f'<rect x="{cx-bw*0.2:.0f}" y="{Y(r["prem_p50"]):.0f}" width="{bw*0.4:.0f}" height="{abs(Y(0)-Y(r["prem_p50"])):.0f}" fill="{BLUE}"/>')
        out.append(f'<text x="{cx:.0f}" y="{Y(r["prem_p90"])-5:.0f}" text-anchor="middle" fill="{ORANGE}">{r["prem_p50"]:+.1f}</text>')
        out.append(f'<text x="{cx:.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">W{int(r["wk"])}</text>')
        out.append(f'<text x="{cx:.0f}" y="{ht-30}" text-anchor="middle" fill="{GREY}">{str(r["周起"])[:10]}</text>')
    out.append(f'<text x="{x0}" y="{ht-10}" fill="{GREY}">柱=白天价格溢价 P50, 竖线=P10~P90 (相对各小时气候中位, $/MWh)</text>')
    out.append("</svg>")
    return "\n".join(out)


def curve_bars(c, year):
    s = c[(c["curve"] == "neg_price") & (c["year"] == year)]
    w, ht, pad = 420, 280, (50, 14, 40, 48)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    n = len(s)
    bw = (x1 - x0) / n
    Y = lambda v: y1 - (y1 - y0) * v / 100.0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="10">']
    for t in (0, 50, 100):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        out.append(f'<text x="{x0-5}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t}%</text>')
    for i, (_, r) in enumerate(s.iterrows()):
        cx = x0 + bw * (i + 0.5)
        v = r["p_negday"] * 100
        out.append(f'<rect x="{cx-bw*0.3:.0f}" y="{Y(v):.0f}" width="{bw*0.6:.0f}" height="{y1-Y(v):.0f}" fill="{RED}"/>')
        out.append(f'<text x="{cx:.0f}" y="{Y(v)-3:.0f}" text-anchor="middle" fill="{RED}">{v:.0f}</text>')
        out.append(f'<text x="{cx:.0f}" y="{y0-6}" text-anchor="middle" fill="#5b7488">Q{int(r["bin"])}</text>')
    out.append(f'<text x="{x0}" y="{ht-8}" fill="{GREY}">西班牙 {year}: 各 gap_w 五分位的"负价日"概率</text>')
    out.append("</svg>")
    return "\n".join(out)


def build():
    c = pd.read_csv(os.path.join(D, "forecast_bridge_calibration.csv"))
    f = pd.read_csv(os.path.join(D, "forecast_price_outlook.csv"), parse_dates=["date"])
    f["wk"] = np.arange(len(f)) // 7 + 1
    wk = f.groupby("wk").agg(周起=("date", "first"), prem_p10=("prem_p10", "median"),
                             prem_p50=("prem_p50", "median"), prem_p90=("prem_p90", "median"),
                             defic=("def_p50", "median"), P_热=("P_热日", "mean"),
                             tmax=("tmax_p50", "median")).reset_index()

    ef = c[(c["market"] == "ERCOT") & (c["curve"] == "fit")].iloc[0]
    eb = c[(c["market"] == "ERCOT") & (c["curve"] == "day_premium")].sort_values("bin")
    s24 = c[(c["curve"] == "fit") & (c["year"] == 2024)].iloc[0]
    s25 = c[(c["curve"] == "fit") & (c["year"] == 2025)].iloc[0]
    q5_24 = c[(c["curve"] == "neg_price") & (c["year"] == 2024)].sort_values("bin").iloc[-1]
    q5_25 = c[(c["curve"] == "neg_price") & (c["year"] == 2025)].sort_values("bin").iloc[-1]

    def card(v, t, d, cls=""):
        return f'<div class="card"><div class="v {cls}">{v}</div><div class="t">{t}</div><div class="d">{d}</div></div>'

    cards = (card(f"+{ef['fit_b']:.1f} $/MWh", "ERCOT 缺口→白天溢价 斜率", f"但 R²={ef['fit_r2']:.3f}（技能极低）")
             + card("corr +0.06", "ERCOT 缺口 vs 白天负价小时", "云量缺口不标记负价")
             + card(f"{q5_24['p_negday']*100:.0f}% → {q5_25['p_negday']*100:.0f}%", "西班牙 gap_w 最高档",
                    "P(负价日)：2024 → 2025")
             + card(f"{wk['prem_p50'].median():+.1f} $/MWh", "ERCOT 未来45天 溢价中位",
                    f"P10~P90 区间 {wk['prem_p10'].median():+.1f} ~ {wk['prem_p90'].median():+.1f}"))

    er = ""
    for _, r in eb.iterrows():
        er += (f'<tr><td>Q{int(r["bin"])}</td><td>{r["driver"]:.2f}</td>'
               f'<td>{r["prem_mean"]:+.2f}</td><td>{r["neg_h_day"]:.2f}</td>'
               f'<td>{r["low5_h_day"]:.2f}</td><td>{r["dem_mean"]/1000:.1f}</td>'
               f'<td>{r["p_mean"]:.1f}</td></tr>')

    sr = ""
    for year in (2023, 2024, 2025):
        s = c[(c["curve"] == "neg_price") & (c["year"] == year)].sort_values("bin")
        for _, r in s.iterrows():
            sr += (f'<tr><td>{year}</td><td>Q{int(r["bin"])}</td><td>{r["driver"]:.1f}</td>'
                   f'<td>{r["p_negday"]*100:.0f}%</td><td>{r["neg_h_day"]:.1f}</td>'
                   f'<td>{r["low5_h_day"]:.1f}</td><td>{r["p_mean"]:.1f}</td></tr>')

    wr = ""
    for _, r in wk.iterrows():
        wr += (f'<tr><td>W{int(r["wk"])}</td><td>{str(r["周起"])[:10]}</td>'
               f'<td>{r["defic"]:.2f}</td><td>{r["prem_p50"]:+.2f}</td>'
               f'<td>{r["prem_p10"]:+.2f}</td><td>{r["prem_p90"]:+.2f}</td>'
               f'<td>{r["tmax"]:.0f}</td><td>{r["P_热"]*100:.0f}%</td></tr>')

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>缺口→电价：日尺度转移函数与45天展望</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.65}}
.wrap{{max-width:1040px;margin:0 auto;padding:28px 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#fff;border-radius:12px;padding:15px 17px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:190px}}
.card .v{{font-size:20px;font-weight:700;color:#1f5bb8}}.card .t{{font-weight:600;margin-top:4px}}
.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:7px 9px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
td:first-child,th:first-child{{text-align:left}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}li{{margin:6px 0}}
.hl{{background:#fff6ea;border-left:3px solid #e5853a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.warn{{background:#fdeef0;border-left:3px solid #c23a3a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}.two{{display:flex;gap:16px;flex-wrap:wrap}}.two>div{{flex:1;min-width:320px}}
</style></head><body><div class="wrap">
<h1>缺口 → 电价：日尺度转移函数与 45 天展望</h1>
<div class="sub">把 PS-027 的季节预报（未来 45 天逐日光伏缺日概率）与 PS-032/033 的"缺口→电价"判据接起来。
先标定日尺度转移函数（ERCOT 白天溢价 / 西班牙负价日），再套到季节预报上 · 核查日 2026-09-29</div>

<div class="cards">{cards}</div>

<div class="warn"><b>先导诊断（重要）</b>：季节预报能提供的是<b>云量缺口</b>（1−τ）。在 ERCOT 日尺度上，
它与电价几乎不相关（corr(deficit, 白天溢价) = +0.13，<b>R² = 0.016</b>），且<b>不标记负价</b>（corr = +0.06）。
原因是缺口与需求强负相关（五分位需求 63.8 → 55.6 GW）——云来天凉，日尺度上"缺口→涨价"被需求回落抵消，
正是 PS-024「天气组合负相关」在日尺度的重演。
⇒ <b>不能把 ERCOT 季节预报的云量信号直接当"负价预警"</b>；它只能给一个技能很低的"轻微上浮倾向"。
负价预警需要另一条驱动（西班牙的 gap_w），见 ②。</div>

<div class="hl"><b>两条可用/不可用的通道</b>：
① <b>ERCOT（季节预报可驱动，但技能低）</b>：白天溢价 = {ef['fit_a']:+.2f} {ef['fit_b']:+.2f}×缺口分数
（SE {ef['fit_se']:.2f}，R² {ef['fit_r2']:.3f}）——方向是"稀缺"，量级到缺口分数 1.0 时约 {ef['fit_a']+ef['fit_b']:+.1f} $/MWh；
② <b>西班牙（负价曲线强，但缺季节预报）</b>：gap_w 最高档的 P(负价日) 达 {q5_24['p_negday']*100:.0f}%（2024）/{q5_25['p_negday']*100:.0f}%（2025），
R² {s24['fit_r2']:.2f}/{s25['fit_r2']:.2f} ⇒ 这是目前唯一能站住的"缺口→负价"转移曲线。</div>

<div class="box"><h2 style="margin-top:0">① ERCOT：云致缺口 → 白天价格溢价（相对逐时气候）</h2>
<div class="scroll"><table>
<tr><th>缺口档</th><th>缺口分数</th><th>白天溢价 $/MWh</th><th>白天负价 h/日</th><th>白天低价 h/日</th><th>需求 GW</th><th>白天均价 $</th></tr>
{er}
</table></div>
<div class="note">白天溢价 = 13–23 UTC 电价 − 该小时全样本中位价，再取日平均（消掉日循环与季节）。
五分位显示溢价随缺口上升（+1.87 → +5.16 $/MWh），但档间非严格单调、且 R² 仅 0.016 ⇒ <b>信噪比很低</b>。
同期需求从 63.8 降到 55.6 GW，正是"云致缺口 ↔ 降温低需求"的负相关。</div></div>

<div class="box"><h2 style="margin-top:0">② 西班牙：gap_w → "负价日"概率（可用的转移曲线）</h2>
<div class="two">
<div>{curve_bars(c, 2024)}</div>
<div>{curve_bars(c, 2025)}</div>
</div>
<div class="scroll"><table>
<tr><th>年</th><th>档</th><th>gap_w GW·h</th><th>P(负价日)</th><th>负价 h/日</th><th>低价 h/日</th><th>日均价 €</th></tr>
{sr}
</table></div>
<div class="note">2023 年西班牙全年零负价 ⇒ 曲线不存在；2024/2025 曲线强且单调（最高档 52%/77%）。
拟合（线性概率）：2024 = {s24['fit_a']:+.3f} + {s24['fit_b']:.4f}×gap_w（R² {s24['fit_r2']:.2f}）；
2025 = {s25['fit_a']:+.3f} + {s25['fit_b']:.4f}×gap_w（R² {s25['fit_r2']:.2f}）。
gap_w 以 GW·h 计。</div></div>

<div class="box"><h2 style="margin-top:0">③ ERCOT 未来 45 天 白天溢价展望（套用 ①的转移函数）</h2>
{svg_outlook(f, wk)}
<div class="scroll"><table>
<tr><th>周</th><th>周起</th><th>缺口分数 P50</th><th>溢价 P50</th><th>溢价 P10</th><th>溢价 P90</th><th>最高温 P50 ℃</th><th>P(热日)</th></tr>
{wr}
</table></div>
<div class="note">把 PS-027 季节预报的逐日 τ 三分位换算为缺口分数（deficit = 1−τ），代入 ① 的线性转移函数；
竖线为成员 P10~P90。第 1 周（9/28 起）仍有热日（P_热≈59%、Tmax≈33℃）叠加多云 ⇒ 溢价最高约 +2.0 $/MWh；
其后随入秋回落，全窗中位约 {wk['prem_p50'].median():+.1f} $/MWh（区间 {wk['prem_p10'].median():+.1f} ~ {wk['prem_p90'].median():+.1f}）。</div></div>

<div class="box"><h2 style="margin-top:0">④ 结论、局限与下一步</h2>
<ul class="note">
<li><b>结论一（ERCOT 负价预警不可行）</b>：季节预报给的云量缺口在日尺度上对 ERCOT 电价近乎无信息（R² 0.016），
且不标记负价；把它的窄分布当成"负价风险"会给出虚假的高置信度。</li>
<li><b>结论二（西班牙负价曲线可用）</b>：gap_w 与负价日强相关，最高档 P(负价日) 52%/77%（2024/2025），
可作可部署的负价预警曲线——但目前<b>缺西班牙的季节预报</b>，尚不能预报化。</li>
<li><b>结论三（为什么 ERCOT 弱）</b>：云致缺口与需求负相关（云↔降温），日尺度上用需求预报"抵消"后净效应接近 0；
只有在<b>小时级</b>才显现（PS-022/024 的 +5%/GW），且方向是涨价而非负价。</li>
<li><b>局限</b>：①ERCOT 溢价定义依赖全样本逐时中位气候，含轻微前视；②季节集合欠扩散（PS-027），
传播出的溢价区间偏窄；③西班牙曲线是线性概率拟合，尾部（极高档）会超出 [0,1]；
④45 天展望用 τ 三分位近似成员分布，非逐成员传播；⑤西班牙仍用日前价。</li>
<li><b>下一步</b>：①给西班牙也建季节预报链路（Open-Meteo Seasonal 覆盖西班牙）→ 直接产出西班牙 45 天负价概率；
②ERCOT 侧改挂<b>小时级 + 需求/温度预报</b>才能恢复技能；③若能取到 ESIOS 实时/日内价，可用分钟级复核触发阈值。</li>
</ul></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f_:
        f_.write(html)
    print(f"→ {p}")


if __name__ == "__main__":
    build()
