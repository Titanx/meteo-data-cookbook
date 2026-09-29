"""西班牙负价概率预报报告
输入: data/spain/spain_negprice_calibration.csv, spain_negprice_outlook.csv
输出: output/spain_negprice_forecast/index.html
用法: python scripts/analysis/build_spain_negprice_report.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_negprice_forecast"
os.makedirs(OUT, exist_ok=True)
BLUE, RED, ORANGE, GREY, GREEN = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4", "#2f8f6b"


def svg_weekly(wk):
    w, ht, pad = 820, 300, (52, 18, 40, 52)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    n = len(wk)
    bw = (x1 - x0) / n
    vmax = max(wk["P_raw"].max(), 0.05) * 1.2
    Y = lambda v: y1 - (y1 - y0) * v / vmax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in np.linspace(0, vmax, 4):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        out.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t*100:.0f}%</text>')
    for i, (_, r) in enumerate(wk.iterrows()):
        cx = x0 + bw * (i + 0.5)
        out.append(f'<rect x="{cx-bw*0.30:.0f}" y="{Y(r["P"]) :.0f}" width="{bw*0.30:.0f}" '
                   f'height="{y1-Y(r["P"]):.0f}" fill="{BLUE}"/>')
        out.append(f'<rect x="{cx:.0f}" y="{Y(r["P_raw"]):.0f}" width="{bw*0.30:.0f}" '
                   f'height="{y1-Y(r["P_raw"]):.0f}" fill="{GREY}" opacity="0.55"/>')
        out.append(f'<text x="{cx-bw*0.15:.0f}" y="{Y(r["P"])-4:.0f}" text-anchor="middle" fill="{BLUE}">{r["P"]*100:.1f}</text>')
        out.append(f'<text x="{cx+bw*0.15:.0f}" y="{Y(r["P_raw"])-4:.0f}" text-anchor="middle" fill="{GREY}">{r["P_raw"]*100:.1f}</text>')
        out.append(f'<text x="{cx:.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">W{int(r["wk"])}</text>')
        out.append(f'<text x="{cx:.0f}" y="{ht-28}" text-anchor="middle" fill="{GREY}">{str(r["周起"])[:10]}</text>')
    out.append(f'<text x="{x0}" y="{ht-8}" fill="{GREY}">蓝=季节校正后, 灰=未校正(偏乐观); 数值为"负价日"概率(%)</text>')
    out.append("</svg>")
    return "\n".join(out)


def build():
    cal = pd.read_csv(os.path.join(D, "spain_negprice_calibration.csv"))
    out = pd.read_csv(os.path.join(D, "spain_negprice_outlook.csv"), parse_dates=["date"])
    q = cal[cal["curve"] == "quintile"].sort_values("bin")
    fit = cal[cal["curve"] == "fit"].iloc[0]
    chk = cal[cal["curve"] == "season_check"].iloc[0]
    wk = out.groupby("wk").agg(周起=("date", "first"), tau=("tau_p50", "median"),
                               S=("S_p50", "median"), P=("Pnegday_mean", "mean"),
                               P_raw=("Pneg_raw_mean", "mean"),
                               P90=("Pnegday_p90", "median")).reset_index()

    def card(v, t, d, cls=""):
        return f'<div class="card"><div class="v {cls}">{v}</div><div class="t">{t}</div><div class="d">{d}</div></div>'

    cards = (card("0.72", "跨年 AUC（2024↔2025）", "唯一可预报驱动的排序能力", "pos")
             + card(f"{q['p_negday'].max()*100:.0f}%", "指数高档 P(负价日)", "标定样本 2024–25 合并（Q4）", "neg")
             + card("2×", "秋季原始高估倍数", f"实测 {chk['p_negday']*100:.1f}% vs 原始 {chk['neg_h']*100:.1f}%", "neg")
             + card(f"{out['Pnegday_mean'].mean()*100:.1f}%", "未来45天 负价日概率均值", "季节校正后（入秋走低）"))

    rows = ""
    for _, r in q.iterrows():
        rows += (f'<tr><td>Q{int(r["bin"])}</td><td>{r["S_med"]:.2f}</td><td>{int(r["n"])}</td>'
                 f'<td class="neg">{r["p_negday"]*100:.0f}%</td><td>{r["neg_h"]:.1f}</td>'
                 f'<td>{r["price"]:.1f}</td></tr>')

    wr = ""
    for _, r in wk.iterrows():
        wr += (f'<tr><td>W{int(r["wk"])}</td><td>{str(r["周起"])[:10]}</td><td>{r["tau"]:.3f}</td>'
               f'<td>{r["S"]:.2f}</td><td class="neg">{r["P"]*100:.1f}%</td>'
               f'<td>{r["P_raw"]*100:.1f}%</td><td>{r["P90"]*100:.1f}%</td></tr>')

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙 负价概率季节预报</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.65}}
.wrap{{max-width:1000px;margin:0 auto;padding:28px 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#fff;border-radius:12px;padding:15px 17px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:190px}}
.card .v{{font-size:21px;font-weight:700}}.card .v.pos{{color:#1f5bb8}}.card .v.neg{{color:#c23a3a}}
.card .t{{font-weight:600;margin-top:4px}}.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:7px 9px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
td:first-child,th:first-child{{text-align:left}}
.neg{{color:#c23a3a;font-weight:600}}.pos{{color:#1f5bb8;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}li{{margin:6px 0}}
.hl{{background:#eef6ef;border-left:3px solid #2f8f6b;padding:12px 16px;border-radius:6px;margin:14px 0}}
.warn{{background:#fff6ea;border-left:3px solid #e5853a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}
</style></head><body><div class="wrap">
<h1>西班牙 负价概率：季节预报链路（未来 45 天）</h1>
<div class="sub">PS-034 判定"ERCOT 预报桥不成立"，但西班牙负价的可预报性另有结构。本流程为西班牙建季节预报链路：
Open-Meteo Seasonal 50 成员逐日短波 → 9 个光伏区逐站晴空（haurwitz）→ fleet 传输率 τ → 可预报指数
<b>S = 晴空气候(doy) × τ / 负荷气候(月,工作日)</b> → 历史标定 P(负价日) → 逐成员传播到未来 45 天 · 核查日 2026-09-29</div>

<div class="cards">{cards}</div>

<div class="hl"><b>结论：这条链在西班牙是可用的（中等技能），与 ERCOT 的"不成立"形成对照。</b>
把可预报的"资源/负荷"指数 S 用作打分，<b>跨年 AUC 双向均为 0.72</b>（train 2024→test 2025 与反向一致），
指数高档的负价日占比达 <b>{q['p_negday'].max()*100:.0f}%</b>（全年基准 18%）。
关键差别在于：ERCOT 的云量缺口与需求负相关、日尺度被抵消；而西班牙的负价由<b>资源（晴空辐照，季节性可算）+ 负荷</b>共同决定，
两者都可预报。</div>

<div class="warn"><b>必须注意的校准偏差</b>：把标定曲线直接用于当前窗口（9/29–11/12）会<b>高估近一倍</b>——
历史同窗口实测 P(负价日) = <b>{chk['p_negday']*100:.1f}%</b>，而原始模型给出 <b>{chk['neg_h']*100:.1f}%</b>（+{(chk['neg_h']-chk['p_negday'])*100:.1f}pp）。
原因是 S 未完全捕捉"春季负价高发、入秋转弱"的季节结构。因此对截距做了**季节偏差校正**（{fit['p_negday']:+.3f} → {fit['p_negday']-(chk['neg_h']-chk['p_negday']):+.3f}），
下图与表中"P"为校正后、"P_raw"为未校正原值，两者都给出以便判断。</div>

<div class="box"><h2 style="margin-top:0">① 标定曲线（2024–25 合并；指数 S 五分位）</h2>
<div class="scroll"><table>
<tr><th>档</th><th>S 中位</th><th>n</th><th>负价日占比</th><th>负价 h/日</th><th>日均价 €</th></tr>
{rows}
</table></div>
<div class="note">线性概率：P(负价日) = {fit['p_negday']:+.3f} + {fit['neg_h']:.3f}×S。曲线在 Q1→Q4 单调上升（0% → 32%），Q5 略回落（26%）——
说明极高资源日反而可能伴随较高负荷（夏季），故线性外推到最高档需谨慎。</div></div>

<div class="box"><h2 style="margin-top:0">② 未来 45 天 负价日概率（逐周，校正后 vs 未校正）</h2>
{svg_weekly(wk)}
<div class="scroll"><table>
<tr><th>周</th><th>周起</th><th>fleet τ P50</th><th>S P50</th><th>P(负价日)</th><th>P_raw</th><th>P90</th></tr>
{wr}
</table></div>
<div class="note">校正后全窗均值 <b>{out['Pnegday_mean'].mean()*100:.1f}%</b>（未校正 {out['Pneg_raw_mean'].mean()*100:.1f}%），
从 W1 约 {wk.iloc[0]['P']*100:.1f}% 递减至 W7 约 {wk.iloc[-1]['P']*100:.1f}% —— 与"入秋后负价转弱"的季节结构一致。
逐成员传播（50 成员）给出的 P90 上限见右列，可作为"高资源 + 低负荷"情景的上界。</div></div>

<div class="box"><h2 style="margin-top:0">③ 结论、局限与下一步</h2>
<ul class="note">
<li><b>结论一（可预报性成立）</b>：西班牙负价日可由"晴空资源（季节性可算）+ 传输率（季节预报）+ 负荷气候"构成的指数 S 预报，
跨年 AUC 0.72 双向一致，最高档负价日占比 26~32%。</li>
<li><b>结论二（对照 ERCOT）</b>：同一套思路在 ERCOT 失效（PS-034），因为 ERCOT 的驱动是"云量缺口"且被需求回落抵消；
西班牙的有效驱动是"资源/负荷"而非"缺口"——<b>可预报性取决于驱动是否外生且可算</b>。</li>
<li><b>结论三（校准是必需的一步）</b>：不做季节校正会把入秋概率高估近一倍；校正后全窗约 8%。</li>
<li><b>局限</b>：①标定仅 2024/2025 两年（2023 零负价，曲线不存在），样本小；②S 中的负荷用**气候**而非真实预报，
未纳入温度异常；③τ 由 haurwitz 水平面晴空定义，与历史 POA 链路存在尺度差（已用窗口中位校正 k=1.05，仍非严格一致）；
④线性概率模型在两端会被 clip，尾部不精确；⑤用日前价，未含日内连续价；⑥季节集合欠扩散，P10~P90 区间偏窄。</li>
<li><b>下一步</b>：①把负荷气候换成**温度驱动的负荷预报**（季节预报已含 temperature_2m_max）；
②扩到 2022–2023 之外的更多年份或用 ERA5 回算做多年标定；③若拿到 ESIOS 日内/实时价，可把"日"细化到"小时"。</li>
</ul></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f_:
        f_.write(html)
    print(f"→ {p}")


if __name__ == "__main__":
    build()
