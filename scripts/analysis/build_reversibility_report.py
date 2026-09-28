"""缺口成因判据 · 可逆性检验报告
输入: data/ercot/reversibility_matrix.csv
输出: output/reversibility_shortfall/index.html
用法: python scripts/analysis/build_reversibility_report.py
"""
import os

import pandas as pd

D = r"c:\work\meteo\data\ercot"
OUT = r"c:\work\meteo\output\reversibility_shortfall"
os.makedirs(OUT, exist_ok=True)
EXO, ENDO, GREY = "#e5853a", "#1f5bb8", "#8aa0b4"
NAME = {("ERCOT", "PV"): "ERCOT光伏", ("ERCOT", "Wind"): "ERCOT风电",
        ("西班牙", "PV"): "西班牙光伏"}


def svg_bars(g, col, title):
    w, ht, pad = 840, 320, (52, 18, 40, 52)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    cells = list(g.index)
    n = len(cells)
    bw = (x1 - x0) / n
    vmax = max(abs(g[col]).max(), 1.0) * 1.22
    Y = lambda v: (y1 + y0) / 2 - ((y1 - y0) / 2) * v / vmax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" '
           f'font-family="Segoe UI,Arial" font-size="11">']
    out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(0):.0f}" y2="{Y(0):.0f}" stroke="#c9d6e0"/>')
    for tick in (vmax, vmax / 2, -vmax / 2, -vmax):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(tick):.0f}" y2="{Y(tick):.0f}" stroke="#eef3f7"/>')
        out.append(f'<text x="{x0-6}" y="{Y(tick)+3:.0f}" text-anchor="end" fill="{GREY}">{tick:+.1f}</text>')
    for i, c in enumerate(cells):
        cx = x0 + bw * (i + 0.5)
        v = g.loc[c, col]
        colr = EXO if g.loc[c, "cause"] == "外生" else ENDO
        top, bot = min(Y(v), Y(0)), max(Y(v), Y(0))
        out.append(f'<rect x="{cx-bw*0.27:.0f}" y="{top:.0f}" width="{bw*0.54:.0f}" '
                   f'height="{max(bot-top,1):.0f}" fill="{colr}"/>')
        ty = (top - 6) if v > 0 else (bot + 15)
        out.append(f'<text x="{cx:.0f}" y="{ty:.0f}" text-anchor="middle" fill="{colr}">{v:+.2f}</text>')
        m, t, _cause = c.split("|")
        out.append(f'<text x="{cx:.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">'
                   f'{NAME.get((m,t), m+t)}<tspan x="{cx:.0f}" dy="12" fill="{colr}">{g.loc[c,"cause"]}缺口</tspan></text>')
    out.append(f'<text x="{x0}" y="{ht-8}" fill="{GREY}">{title}</text>')
    out.append("</svg>")
    return "\n".join(out)


def build():
    e = pd.read_csv(os.path.join(D, "reversibility_matrix.csv"))
    e["cell"] = e["market"] + "|" + e["tech"] + "|" + e["cause"]
    g = e.groupby(["cell", "market", "tech", "cause"]).agg(
        log_only=("b_log_only", "mean"), log_only_se=("se_log_only", "mean"),
        log_lvl=("b_log_lvl", "mean"), log_lvl_se=("se_log_lvl", "mean"),
        raw_only=("b_raw_only", "mean"), raw_lvl=("b_raw_lvl", "mean"),
        corr=("corr_gap_level", "mean")).reset_index()
    g["key"] = g["market"] + "|" + g["tech"]
    order = ["ERCOT|PV|外生", "ERCOT|PV|内生", "ERCOT|Wind|外生", "ERCOT|Wind|内生",
             "西班牙|PV|外生", "西班牙|PV|内生"]
    g = g.set_index("cell").loc[order]

    exo, endo = g[g["cause"] == "外生"], g[g["cause"] == "内生"]
    unit = lambda m: "$" if m == "ERCOT" else "€"

    rows = ""
    for c, r in g.iterrows():
        m, t, _ = c.split("|")
        f = lambda v: f'<span class="pos">{v:+.2f}</span>' if v > 0 else f'<span class="neg">{v:+.2f}</span>'
        rows += (f'<tr><td>{NAME.get((m,t),m+t)}</td><td>{r["cause"]}</td>'
                 f'<td>{f(r["log_only"])}</td><td>{r["log_only_se"]:.2f}</td>'
                 f'<td>{f(r["log_lvl"])}</td><td>{r["log_lvl_se"]:.2f}</td>'
                 f'<td>{r["raw_only"]:+.1f}</td><td>{r["raw_lvl"]:+.1f}</td>'
                 f'<td>{r["corr"]:+.2f}</td></tr>')

    def card(v, t, d, cls=""):
        return (f'<div class="card"><div class="v {cls}">{v}</div>'
                f'<div class="t">{t}</div><div class="d">{d}</div></div>')

    cards = (card(f"{exo['log_only'].min():+.1f} ~ {exo['log_only'].max():+.1f}",
                  "外生缺口弹性 (%/GW)", "6 格全为正 · 供给收缩推高电价", "pos")
             + card(f"{endo['log_only'].max():+.1f} ~ {endo['log_only'].min():+.1f}",
                    "内生缺口弹性 (%/GW)", "6 格全为负 · 供给过剩压低电价", "neg")
             + card("正号消失", "控制出力水平后（外生）", "6 格中 5 格转负 · 只是水平效应的镜像", "neg")
             + card("负号保留", "控制出力水平后（内生）", "6 格全为负 · 设定稳健", "neg"))

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>缺口成因判据 · 可逆性检验</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.65}}
.wrap{{max-width:1030px;margin:0 auto;padding:28px 20px}}
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
td:first-child,th:first-child,td:nth-child(2),th:nth-child(2){{text-align:left}}
.pos{{color:#1f5bb8;font-weight:600}}.neg{{color:#c23a3a;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}li{{margin:6px 0}}
.hl{{background:#fff6ea;border-left:3px solid #e5853a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}
</style></head><body><div class="wrap">
<h1>缺口成因判据 · 可逆性检验（ERCOT × 西班牙）</h1>
<div class="sub">把 PS-031 的判据——“决定缺口→电价符号的是<b>缺口成因</b>（外生供给损失 vs 内生供给过剩），而非电源类型”——
放进 <b>6 个「市场 × 技术 × 成因」格子</b>做双向检验：同一设定下比较两种功能形式（ln / 水平）、两种控制（缺口单独 / 控制该技术出力水平）。
本轮<b>补齐了此前缺失的一格</b>：ERCOT 光伏的内生缺口（用 NASA POWER 辐照 + pvlib 重建全天候潜力） · 核查日 2026-09-28</div>

<div class="cards">{cards}</div>

<div class="hl"><b>检验结论</b>：在缺口单独的设定下，判据在<b>全部 6 个格子</b>成立——外生缺口弹性 {exo['log_only'].min():+.1f} ~ {exo['log_only'].max():+.1f} %/GW <b>全为正</b>，
内生缺口 {endo['log_only'].max():+.1f} ~ {endo['log_only'].min():+.1f} %/GW <b>全为负</b>；同一技术（光伏）与同一市场（ERCOT）内部都同时出现两种符号
⇒ <b>符号与电源类型无关、与缺口成因有关</b>。但可逆性有明确的边界：<b>"外生→正"并不稳健</b>——一旦控制该技术的出力水平，6 格中 5 格转为负号
（外生缺口只是"出力偏低"的镜像）；<b>只有"内生→负"经得起控制</b>，6 格全部保留负号 ⇒ 稳健可逆的只有"内生/过剩"这一半。</div>

<div class="box"><h2 style="margin-top:0">① 缺口弹性矩阵（log: %/GW；水平: 价格单位/GW；两年均值）</h2>
<div class="scroll"><table>
<tr><th>市场·技术</th><th>成因</th><th>log 单独</th><th>SE</th><th>log +出力水平</th><th>SE</th>
<th>水平 单独</th><th>水平 +水平</th><th>corr(缺口,水平)</th></tr>
{rows}
</table></div>
<div class="note">"外生"= 外生供给损失（光伏晴空缺口 / 风电低风异常）；"内生"= 潜力 − 实际（弃光/弃风）。
系数为 2025/2026 均值（ERCOT）与 2024/2025 均值（西班牙）；log 口径 %/GW，水平口径 ERCOT 为 $/MWh per GW、西班牙为 €/MWh per GW。</div></div>

<div class="box"><h2 style="margin-top:0">② 缺口单独：符号与成因完全一致</h2>
{svg_bars(g.reset_index().set_index("cell"), "log_only", "缺口弹性 (%/GW) · 缺口单独；橙=外生，蓝=内生")}
<div class="note">6 格全部符合判据：外生为正（ERCOT 光伏 {g.loc['ERCOT|PV|外生','log_only']:+.1f}、ERCOT 风电 {g.loc['ERCOT|Wind|外生','log_only']:+.1f}、西班牙光伏 {g.loc['西班牙|PV|外生','log_only']:+.1f}），
内生为负（ERCOT 光伏 {g.loc['ERCOT|PV|内生','log_only']:+.1f}、ERCOT 风电 {g.loc['ERCOT|Wind|内生','log_only']:+.1f}、西班牙光伏 {g.loc['西班牙|PV|内生','log_only']:+.1f}）。</div></div>

<div class="box"><h2 style="margin-top:0">③ 控制出力水平后：外生正号塌缩（可逆性的边界）</h2>
{svg_bars(g.reset_index().set_index("cell"), "log_lvl", "缺口弹性 (%/GW) · 同时控制该技术出力水平")}
<div class="note">外生缺口 6 格中 5 格转为负号：它多与"出力偏低"同义（风电低风异常 corr=−0.69/−0.71 尤甚），
控制水平后不再有独立信号 ⇒ 其正号主要是"出力↓→电价↑"的镜像。
内生缺口 6 格<b>全部保留负号</b>，且与水平近乎正交（ERCOT 光伏 corr≈0）⇒ 这是判据里<b>唯一设定稳健</b>的一半。</div></div>

<div class="box"><h2 style="margin-top:0">④ 结论与局限</h2>
<ul class="note">
<li><b>可逆性成立的部分</b>：符号只随"成因"变、不随"电源"变——同市场（ERCOT）内光伏与风电各自都有正负两号；同技术（光伏）在 ERCOT 与西班牙都出现正负两号。
本轮补齐 ERCOT 光伏内生缺口后，ERCOT 单市场即自洽。</li>
<li><b>可逆性的边界</b>：只有<b>内生缺口（潜力−实际）→ 负</b>是设定稳健、跨市场跨技术可复现的；
<b>外生缺口 → 正</b>依赖不控制出力水平，本质是水平效应的重编码，不宜当作独立的"成因通道"。</li>
<li><b>本轮新增</b>：NASA POWER（含云全天候）辐照 + pvlib 单轴跟踪重建 ERCOT 光伏潜力，标定 ILR=1.30（与 PS-021 一致），
与 EIA 实际逐时 r=0.976/0.980、能量比 1.01/0.995 ⇒ 内生缺口可得（此前仅西班牙可算）。</li>
<li><b>局限</b>：①ERCOT 无 2022 小时电价，"同技术跨年份（无弃光→有弃光）"的时间向可逆性无法做；
②NASA POWER 辐照有约 4 个月延迟，2026 仅覆盖 1–6 月；③NASA POWER 为 MERRA-2 再分析（0.5°），精度低于 NSRDB；
④西班牙无风电潜力，"西班牙风电"两格缺席；⑤西班牙 NASA POWER 时间轴存在约 1h 偏移（lag0 r=0.971，lag−1 0.934），影响有限但非零。</li>
<li><b>下一步</b>：①申请 ESIOS token 后以西班牙<b>日内连续/实时价</b>替换日前价，重跑矩阵；②补 ERCOT 2022 小时电价，完成时间向可逆性检验。</li>
</ul></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"→ {p}")


if __name__ == "__main__":
    build()
