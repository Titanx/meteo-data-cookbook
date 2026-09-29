# -*- coding: utf-8 -*-
"""PS-041 报告: 西班牙负价的跨境结构 —— ES–FR 耦合与"区域过剩"

输出: output/spain_negprice_xborder/index.html
用法: python scripts/analysis/build_spain_xborder_report.py
"""
import os
import re

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_negprice_xborder"
BLUE, ORANGE, GREEN, RED, GREY = "#1f5bb8", "#e5853a", "#2f8f6b", "#c23a3a", "#8fa4b8"


def scatter(df):
    W, H, L, R, T, B = 660, 330, 56, 14, 16, 40
    xr, yr = (0.15, 0.95), (-0.05, 1.0)

    def X(v):
        return L + (v - xr[0]) / (xr[1] - xr[0]) * (W - L - R)

    def Y(v):
        return H - B - (v - yr[0]) / (yr[1] - yr[0]) * (H - T - B)

    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">']
    s.append(f'<rect x="{L}" y="{T}" width="{W-L-R}" height="{H-T-B}" fill="#fbfdff" stroke="#e3ecf4"/>')
    for g in np.arange(0, 1.01, 0.25):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#eef3f7"/>' % (L, Y(g), W - R, Y(g)))
        s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#9ab0c2" text-anchor="end">%.0f%%</text>'
                 % (L - 6, Y(g) + 3, g * 100))
    for g in np.arange(0.2, 0.96, 0.1):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#eef3f7"/>' % (X(g), T, X(g), H - B))
        s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#9ab0c2" text-anchor="middle">%.0f</text>'
                 % (X(g), H - B + 14, g * 100))
    s.append('<text x="%.1f" y="%.1f" font-size="11" fill="#6b8296" text-anchor="middle">'
             '当日正午份额(当地10-16h 光伏/负荷, %%)</text>' % ((L + W - R) / 2, H - 6))
    s.append('<text x="13" y="%.1f" font-size="11" fill="#6b8296" transform="rotate(-90 13 %.1f)" '
             'text-anchor="middle">当日负价小时 / 6 h 窗口</text>' % ((T + H - B) / 2, (T + H - B) / 2))
    d = df.dropna(subset=["noon_ratio", "negh", "fr_negh_noon"]).copy()
    d["year"] = [t.year for t in d.index]
    for y, col in [(2023, "#dfe7ee"), (2024, ORANGE), (2025, "#7a4fd0"), (2026, RED)]:
        sub = d[d.year == y]
        for _, r in sub.iterrows():
            hot = r.fr_negh_noon >= 5
            s.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="%.2f"%s/>'
                     % (X(min(r.noon_ratio, 0.95)), Y(r.negh / 6.0), 4.6 if hot else 3.2, col,
                        0.95 if hot else 0.55, ' stroke="#111" stroke-width="1.2"' if hot else ""))
    s.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="#22303c">'
             '黑圈 = 法国同窗口也有 ≥5 h 负价</text>' % (L + 10, T + 14))
    s.append('</svg>')
    return "".join(s)


def bars(items, vmax=100.0):
    b = ""
    for lab, v, col, note in items:
        b += ('<div style="display:flex;align-items:center;margin:6px 0;font-size:12.5px">'
              '<div style="width:250px;color:#3c556b">%s</div>'
              '<div style="flex:1;background:#eef3f7;border-radius:3px;height:16px">'
              '<div style="width:%.1f%%;height:16px;background:%s;border-radius:3px"></div></div>'
              '<div style="width:62px;text-align:right;font-weight:700;color:%s">%.1f%%</div>'
              '<div style="width:190px;color:#8497a8;padding-left:10px">%s</div></div>'
              % (lab, v / vmax * 100, col, col, v, note))
    return b


def main():
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv(os.path.join(D, "spain_xborder_daily.csv"), parse_dates=["date"]).set_index("date")
    mod = pd.read_csv(os.path.join(D, "spain_xborder_model.csv"))
    oos = pd.read_csv(os.path.join(D, "spain_xborder_oos.csv"))
    mech = pd.read_csv(os.path.join(D, "spain_xborder_mechanism.csv"))
    cor = pd.read_csv(os.path.join(D, "spain_xborder_corr.csv"))
    nm = pd.read_csv(os.path.join(D, "spain_xborder_negday_means.csv"))

    ytab = ""
    for y, r in df.dropna(subset=["negh"]).groupby("year").agg(
            日数=("negh", "size"), 负价日=("negday", "sum"), 负价h=("negh", "sum"),
            午比=("noon_ratio", "median"), 价差=("spread_noon", "median"),
            FR价=("fr_price_noon", "median"), FR负价h=("fr_negh_noon", "mean")).iterrows():
        ytab += ("<tr><td>%d</td><td>%d</td><td%s>%d</td><td%s>%d</td><td>%.1f</td>"
                 "<td>%+.2f</td><td>%.1f</td><td%s>%.2f</td></tr>"
                 % (y, r.日数, ' class="neg"' if r.负价日 else "", int(r.负价日),
                    ' class="neg"' if r.负价h else "", int(r.负价h), r.午比 * 100,
                    r.价差, r.FR价, ' class="neg"' if r.FR负价h > 1 else "", r.FR负价h))

    mrow = ""
    for r in mod.itertuples():
        mrow += ("<tr><td>%s</td><td>%d</td><td>%.0f</td><td>%.2f</td><td>%.2f</td><td%s>%.3f</td></tr>"
                 % (r.spec, r.k, r.aic, r.disp, r.mae,
                    ' class="neg"' if r.auc >= 0.88 else "", r.auc))

    orow = ""
    for r in oos.itertuples():
        orow += ("<tr><td>≤%d</td><td>%s</td><td>%d</td><td%s>%.3f</td><td>%.2f</td><td>%+.2f</td></tr>"
                 % (r.train_to, r.spec, r.n_test,
                    ' class="neg"' if r.auc >= 0.88 else "", r.auc, r.mae, r.bias))

    mtab = ""
    for v in mech["var"].unique():
        sub = mech[mech["var"] == v]
        rows = "".join("<tr><td>%s</td><td>%d</td><td>%.2f ~ %.2f</td><td%s>%.1f%%</td><td>%.2f</td></tr>"
                       % ("分位 %d" % (r.q + 1), r.n, r.lo, r.hi,
                          ' class="neg"' if r.negday_rate >= 40 else "", r.negday_rate, r.negh)
                       for r in sub.itertuples())
        mtab += ('<h3>按 %s 分位</h3><div class="scroll"><table>'
                 '<tr><th>组</th><th>日数</th><th>区间</th><th>负价日率</th><th>负价h均</th></tr>%s</table></div>'
                 % (sub["label"].iloc[0], rows))

    ctab = "".join("<tr><td>%s</td><td>%+.3f</td><td%s>%+.3f</td></tr>"
                   % (r.var, r.r, ' class="neg"' if abs(r.r_resid) >= 0.3 else "", r.r_resid)
                   for r in cor.itertuples())
    ntab = "".join("<tr><td>%s</td><td>%d</td><td>%.1f%%</td><td>%.2f</td><td>%+.2f</td><td>%.1f</td><td>%.2f</td><td>%.2f</td></tr>"
                   % ("负价日" if r.negday == 1 else "非负价日", r.日数, r.午比, r.负荷, r.价差,
                      r.FR价, r.FR负价h, r.净出口) for r in nm.itertuples())

    SC = [("仅 FR 窗口负价小时 ≥5h（n=123）", 80.5, RED, "负价日率"),
          ("仅 FR 窗口负价小时 0–4h（n=561）", 18.9, BLUE, "负价日率")]

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙负价的跨境结构：ES–FR 耦合（PS-041）</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.62}}
.wrap{{max-width:1060px;margin:0 auto;padding:28px 20px}}
h1{{font-size:23px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
h3{{font-size:14px;margin:16px 0 6px;color:#3c556b}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:14px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:6px 8px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
td:first-child,th:first-child{{text-align:left}}
.neg{{color:#c23a3a;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}
.hl{{background:#eef6ef;border-left:3px solid #2f8f6b;padding:12px 16px;border-radius:6px;margin:14px 0}}
.warn{{background:#fff6ea;border-left:3px solid #e5853a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}li{{margin:5px 0}}
.two{{display:flex;gap:18px;flex-wrap:wrap}}.two>div{{flex:1;min-width:300px}}
</style></head><body><div class="wrap">
<h1>西班牙负价的跨境结构：为什么"国内过剩"不够</h1>
<div class="sub">把 ES–FR 日前价差、FR 中午价、以及泛边界净交易接入日尺度强度模型，检验
"负价是纯国内现象"还是"区域耦合现象" · 核查日 2026-09-29</div>

<div class="hl"><b>结论一：西班牙负价是"法兰西-伊比利亚区域过剩"现象，不是纯国内现象。</b>
最能区分负价日与非负价日的变量**不是**国内正午份额（r=+0.284），而是
<b>法国在同一正午窗口是否也出现负价</b>：负价日的 FR 中午负价小时均值 <b>3.37 h</b>，非负价日仅 <b>0.28 h</b>
（r=+0.620）；在控制国内正午份额后，残差与 FR 负价小时的相关仍达 <b>+0.540</b>。</div>

<div class="hl"><b>结论二：接入 FR 状态后，模型能力大幅提升且样本外成立。</b>
全样本 AUC <b>0.808 → 0.903</b>（逐日 MAE 1.55 → 1.08 h）；
样本外 训练≤2024→2025：AUC <b>0.842 → 0.916</b>；训练≤2025→<b>2026（全新年份）</b>：AUC <b>0.761 → 0.828</b>，MAE 2.51 → 1.91。
⇒ 这解释了 PS-035/037 单因子 S 指数为何失效：<b>缺的是跨境/区域通道，不只是负荷通道</b>。</div>

<div class="warn"><b>结论三：物理出口量几乎不含信息，价格耦合才含信息。</b>
泛边界净交易与负价小时相关仅 r=+0.020，分位表上负价日率在 27%–33% 之间<b>基本平坦</b>；
而 ES−FR 价差的作用<b>非单调</b>——价差≈0（价格耦合）时负价日率最高 <b>43.9%</b>，
ES 明显更便宜（≤−17 €/MWh）时反而只有 17.5%。⇒ 决定负价的是<b>"整个区域都过剩"</b>，
不是"西班牙出口不出去"。</div>

<div class="box"><h2 style="margin-top:0">① 只有 ES–FR 是真正的外部耦合</h2>
<div class="note">同日同小时 |ES−PT| 中位 <b>0.00</b> €/MWh（均值 2.55），|ES−FR| 中位 <b>9.16</b>（均值 23.25）
⇒ 伊比利亚（ES+PT）是<b>单一价市场 MIBEL</b>，葡萄牙不构成独立的外部边界。
入口数据自检：EC 的 ES 价 vs ENTSO-E 官方 A44 逐时 r=<b>0.999984</b>、MAE 0.006 €/MWh。</div>
<h3>年度概览</h3>
<div class="scroll"><table>
<tr><th>年</th><th>日数</th><th>负价日</th><th>负价 h</th><th>午比中位%</th><th>价差中位 €/MWh</th><th>FR 中午价中位</th><th>FR 中午负价 h/日</th></tr>
{ytab}
</table></div>
<div class="note">FR 中午价中位从 2023 的 86.5 崩到 2026 的 <b>15.7</b> €/MWh——法国正午也在快速"光伏化"，
这正是西班牙负价日率从 0% 升到 42.3% 的外部条件。</div></div>

<div class="box"><h2 style="margin-top:0">② 谁带信息：相关与工作日均值</h2>
<div class="two"><div><div class="scroll"><table>
<tr><th>变量</th><th>r(负价h)</th><th>r(残差, 控国内午比后)</th></tr>
{ctab}
</table></div>
<div class="note">残差一列是"在 negh ~ 国内正午份额 之上还剩多少信息"。
<b>FR 负价小时 +0.540</b> 远高于价差 +0.055、净交易 −0.076。</div></div>
<div><div class="scroll"><table>
<tr><th>组</th><th>日数</th><th>午比</th><th>负荷 GWh</th><th>价差</th><th>FR 价</th><th>FR 负价h</th><th>净出口 GW</th></tr>
{ntab}
</table></div>
<div class="note">两个变量的分离度最惊人：<b>FR 中午价 1.15 vs 63.10</b> €/MWh、
<b>FR 负价小时 3.37 vs 0.28 h</b>；而净出口 2.94 vs 2.79 GW 几乎没差别。</div></div></div></div>

<div class="box"><h2 style="margin-top:0">③ 嵌套设定（日尺度 Poisson 强度）</h2>
<div class="scroll"><table>
<tr><th>设定</th><th>参数数</th><th>AIC</th><th>离散度</th><th>MAE (h/日)</th><th>AUC(负价日)</th></tr>
{mrow}
</table></div>
<div class="note">离散度（Pearson χ²/df）从 5.7 降到 4.5–5.1，仍显著 &gt;1 ⇒ 过度离散未消除
（NB 对照 AIC 3381 远低于 Poisson，说明计数波动本身很大）。
把 FR 中午价<b>水平</b>直接放进对数链接会外推爆炸，见 §⑤。</div>
<h3>样本外</h3>
<div class="scroll"><table>
<tr><th>训练至</th><th>设定</th><th>测试日</th><th>AUC</th><th>MAE</th><th>偏差</th></tr>
{orow}
</table></div>
<div class="note">训练≤2025→2026 是最严的检验（2026 是全新年份）。国内口径 AUC 0.761，
加入 FR 负价小时后升到 <b>0.817–0.828</b>，且 MAE 由 2.51 降到 1.91、偏差由 −1.68 收到 −0.85。</div></div>

<div class="box"><h2 style="margin-top:0">④ 机制：高正午份额日内部</h2>
<div class="note">取正午份额高于中位的 {int(mech[mech["var"]=="spread_noon"]["n"].sum())} 日，再按各变量分位看负价日率。</div>
{mtab}
<div style="margin-top:10px">{bars(SC)}</div>
<div class="note">三张表给出清晰的层次：<br>
<b>①</b> 价差<b>非单调</b>，峰值在价差≈0 处（43.9%）⇒ 价格耦合而非出口受阻；<br>
<b>②</b> 净出口几乎平坦（27–33%）⇒ 物理出口量不含信息；<br>
<b>③</b> FR 同窗口负价 5–6 h 时负价日率 <b>80.5%</b>、负价小时 5.65 h/日，而 0–4 h 时只有 18.9% / 1.05 h
⇒ <b>近乎充分的判别条件</b>。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 陷阱：把价格"水平"放进对数链接会外推爆炸</h2>
<div class="warn">设定 S7（正午份额 + 负荷 + <b>FR 中午价水平</b>）在训练≤2024→2025 时表现最好之一（AUC 0.909），
但训练≤2025→2026 时 <b>MAE 爆到 160.4 h/日、偏差 +156.8</b>——
因为 2026 年 FR 正午价跌到训练区间之外（最低 −498 €/MWh），
Poisson 的 log 链接把线性外推指数级放大。<br>
<b>改用有界特征</b>（"FR 同窗口负价小时数"∈[0,6]）后同一训练窗口 MAE 为 <b>1.91</b>、偏差 −0.93，完全稳定。</div>
<div class="note">一般化教训：<b>对数链接 + 无界水平变量 = 外推定时炸弹</b>。
凡是可能越出训练区间的水平变量（价格、净额），都应换成有界形式（计数、占比、分位、指示）或加饱和变换。</div></div>

<div class="box"><h2 style="margin-top:0">⑥ 结论与下一步</h2>
<ul class="note">
<li><b>负价的可预报性上限由"区域状态"决定</b>：只算国内光伏/负荷，日尺度 AUC 上限约 0.76–0.84；
接入"法国是否也负价"后到 0.91–0.92。⇒ PS-035/037 的 S 指数（纯国内）结构性受限，这也解释了 PS-037 观察到的
"2026 起负荷通道主导"。</li>
<li><b>对秋季展望的含义</b>：不应再用"国内份额阈值"单独外推；应把
<b>法国/区域正午价格状态</b>作为条件变量。本流程<b>不给出新的秋季 2026 数字</b>——
因为需要 FR 价格预报，而当前链路没有该预报（诚实缺口）。</li>
<li><b>下一步</b>：① 用 EC 的历史把"FR 正午负价"建成可预报量（FR 光伏/核电/负荷）；
② 把本日模型接进 PS-039/040 的秋季口径，输出条件概率 P(负价日 | 区域过剩)；③ 用 NB 处理过度离散；
④ 待 ENTSO-E 网关恢复后补 A11 单一边界流量，替换泛边界合计。</li>
</ul></div>

<div class="note" style="margin-top:6px">数据：Energy-Charts <code>/price</code>（ES/FR/PT，2023–2026；与 ENTSO-E 官方 A44 逐时 r=0.999984）、
<code>/public_power?country=es</code>（ES 光伏/负荷/泛边界净交易）。方法与产物见 <code>PS-041</code>；
上游 <code>PS-040</code>（正午窗口份额）、<code>PS-039/038/037/035</code>（负价概率链路）。</div>
</div></body></html>"""
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("→ %s" % os.path.join(OUT, "index.html"))


if __name__ == "__main__":
    main()
