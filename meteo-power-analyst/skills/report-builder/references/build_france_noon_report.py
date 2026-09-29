# -*- coding: utf-8 -*-
"""PS-042 报告: 法国正午负价的可预报化 —— "区域过剩"能预报吗?

输出: output/spain_negprice_frforecast/index.html
用法: python skills/report-builder/references/build_france_noon_report.py
"""
import os
import re

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_negprice_frforecast"
BLUE, ORANGE, GREEN, RED, GREY = "#1f5bb8", "#e5853a", "#2f8f6b", "#c23a3a", "#8fa4b8"


def relchart(rel):
    """可靠性曲线: 校准后 P vs 泊松 P"""
    W, H, L, R, T, B = 660, 320, 58, 16, 16, 42
    xr, yr = (0.0, 5.8), (0.0, 0.85)

    def X(v):
        return L + (v - xr[0]) / (xr[1] - xr[0]) * (W - L - R)

    def Y(v):
        return H - B - (v - yr[0]) / (yr[1] - yr[0]) * (H - T - B)

    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">']
    s.append(f'<rect x="{L}" y="{T}" width="{W-L-R}" height="{H-T-B}" fill="#fbfdff" stroke="#e3ecf4"/>')
    for g in np.arange(0, 0.86, 0.2):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#eef3f7"/>' % (L, Y(g), W - R, Y(g)))
        s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#9ab0c2" text-anchor="end">%.0f%%</text>'
                 % (L - 6, Y(g) + 3, g * 100))
    for g in np.arange(0, 5.9, 1.0):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#eef3f7"/>' % (X(g), T, X(g), H - B))
        s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#9ab0c2" text-anchor="middle">%.0f</text>'
                 % (X(g), H - B + 14, g))
    s.append('<text x="%.1f" y="%.1f" font-size="11" fill="#6b8296" text-anchor="middle">'
             '模型强度 λ (预期负价小时/日)</text>' % ((L + W - R) / 2, H - 6))
    s.append('<text x="13" y="%.1f" font-size="11" fill="#6b8296" transform="rotate(-90 13 %.1f)" '
             'text-anchor="middle">P(负价日)</text>' % ((T + H - B) / 2, (T + H - B) / 2))
    # 泊松口径
    lam = np.linspace(0, 5.8, 120)
    pts = " ".join("%.1f,%.1f" % (X(a), Y(min(1 - np.exp(-a), 0.85))) for a in lam)
    s.append(f'<polyline points="{pts}" fill="none" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="6 4"/>')
    # 经验曲线
    pts = " ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in zip(rel["lam"], rel["obs"]))
    s.append(f'<polyline points="{pts}" fill="none" stroke="{GREEN}" stroke-width="2.4"/>')
    for a, b, n in zip(rel["lam"], rel["obs"], rel["n"]):
        s.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" stroke="#fff" stroke-width="1.2"/>' % (X(a), Y(b), GREEN))
    s.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="%s">经验可靠性（分段 n≈%d 日）</text>'
             % (L + 12, T + 14, GREEN, int(rel["n"].iloc[0])))
    s.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="%s">泊松 1−exp(−λ)</text>'
             % (L + 12, T + 30, ORANGE))
    s.append('</svg>')
    return "".join(s)


def condheat(tab):
    """条件结构热力表"""
    cols = [c for c in tab.columns if c != "FR 正午负价h"]
    h = "<div class='scroll'><table><tr><th>FR 正午负价h ↓ / ES 正午份额 →</th>" + \
        "".join("<th>%s</th>" % c for c in cols) + "</tr>"
    for _, r in tab.iterrows():
        h += "<tr><td><b>%d h</b></td>" % r["FR 正午负价h"]
        for c in cols:
            v = float(r[c])
            op = max(0.08, min(0.95, v))
            h += ('<td style="background:rgba(194,58,58,%.2f);color:%s;font-weight:600">%.1f%%</td>'
                  % (op, "#fff" if op > 0.5 else "#22303c", v * 100))
        h += "</tr>"
    return h + "</table></div>"


def main():
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv(os.path.join(D, "france_noon_panel.csv"), parse_dates=["date"]).set_index("date")
    mod = pd.read_csv(os.path.join(D, "france_neg_model.csv"))
    sk = pd.read_csv(os.path.join(D, "france_neg_frskill.csv"))
    two = pd.read_csv(os.path.join(D, "france_neg_twostage.csv"))
    oos = pd.read_csv(os.path.join(D, "france_neg_oos.csv"))
    pre = pd.read_csv(os.path.join(D, "france_neg_preexante.csv"))
    rel = pd.read_csv(os.path.join(D, "france_neg_reliability.csv"))
    tab = pd.read_csv(os.path.join(D, "france_neg_condtable.csv"))
    sea = pd.read_csv(os.path.join(D, "france_neg_season.csv"))

    # 年度概览
    ytab = ""
    for y, r in df.groupby(df.index.year).agg(
            日数=("negh", "size"), ES负价日=("negday", "sum"), ES负价h=("negh", "sum"),
            ES午比=("noon_ratio", "median"), FR午比=("fr_noon_ratio", "median"),
            FR核电=("fr_nuclear_ratio", "median"), FR负价h=("fr_negh_noon", "mean")).iterrows():
        ytab += ("<tr><td>%d</td><td>%d</td><td%s>%d</td><td%s>%d</td><td>%.1f</td><td>%.1f</td><td>%.1f</td>"
                 "<td%s>%.2f</td></tr>"
                 % (y, r.日数, ' class="neg"' if r.ES负价日 else "", int(r.ES负价日),
                    ' class="neg"' if r.ES负价h else "", int(r.ES负价h), r.ES午比 * 100,
                    r.FR午比 * 100, r.FR核电 * 100, ' class="neg"' if r.FR负价h > 1 else "", r.FR负价h))

    mrow = "".join("<tr><td>%s</td><td>%d</td><td>%.0f</td><td>%.2f</td><td>%.3f</td><td%s>%.3f</td></tr>"
                   % (r.设定, r.k, r.AIC, r.离散度, r.MAE_h, ' class="neg"' if r.AUC_负价日 >= 0.8 else "",
                      r.AUC_负价日) for r in mod.itertuples())

    srow = "".join("<tr><td>%s</td><td>%d</td><td>%.3f</td><td>%.3f</td><td%s>%.3f</td></tr>"
                   % (r._1, r.n, r.MAE_h, r._4,
                      ' class="neg"' if r.AUC_负价日 >= 0.78 else "", r.AUC_负价日) for r in sk.itertuples())

    trow = "".join("<tr><td>%s</td><td>%d</td><td>%.0f</td><td%s>%.3f</td><td>%.3f</td><td>%+.2f</td></tr>"
                   % (r.设定, r.变量数, r.AIC, ' class="neg"' if r._5 >= 0.88 else "", r._5, r._6, r.偏差)
                   for r in two.itertuples())

    orow = ""
    for r in oos.itertuples():
        orow += ("<tr><td>%s</td><td>%s</td><td>%d</td><td%s>%.3f</td><td>%.3f</td><td>%+.2f</td></tr>"
                 % (r.训练至, r.设定, r.测试日,
                    ' class="neg"' if r.AUC >= 0.81 else "", r.AUC, r.MAE_h, r.偏差))

    prow = "".join("<tr><td>%s</td><td>%d</td><td%s>%.3f</td><td>%.3f</td><td%s>%.3f</td><td>%.3f</td></tr>"
                   % (r._1, r.变量数, ' class="neg"' if r._3 >= 0.9 else "", r._3, r._4,
                      ' class="neg"' if r._5 >= 0.75 else "", r._5, r._6) for r in pre.itertuples())

    serow = ""
    for r in sea.itertuples():
        serow += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%.2f</td><td>%.3f</td><td%s>%.1f%%</td></tr>"
                  % (r.情景, "—" if pd.isna(r._2) else "%.1f%%" % (r._2 * 100),
                     "%.2f h" % r._3, r._4, r._5, ' class="neg"' if r._6 >= 0.15 else "", r._6 * 100))

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>法国正午负价的可预报化（PS-042）</title>
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
.bad{{background:#fdf0f0;border-left:3px solid #c23a3a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}li{{margin:5px 0}}
.two{{display:flex;gap:18px;flex-wrap:wrap}}.two>div{{flex:1;min-width:300px}}
code{{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}}
</style></head><body><div class="wrap">
<h1>"区域过剩"可以预报吗？——把法国正午负价做成事前量</h1>
<div class="sub">PS-041 发现西班牙负价的支配性预测量是"法国同窗口负价小时"，但那是<b>同期观测</b>。
本流程把法国侧建成独立模型，再用<b>留一年气候学</b>把它换成事前量，检验这道通道能不能在预报里用 · 核查日 2026-09-29</div>

<div class="hl"><b>结论一：法国侧的基本面可以解释法国负价。</b>
以正午（当地 10–16h）光伏份额、核电份额、周末为特征，泊松强度模型对"法国当日是否负价"的
AUC 达 <b>0.792</b>（加月份 FE <b>0.864</b>），逐日 MAE 1.09 h。法国正午份额中位从 2023 的
<b>10.2%</b> 升到 2026 年的 <b>25.1%</b>，与法国负价小时数同步上升。</div>

<div class="bad"><b>结论二（核心，负面）：这条通道<b>不能</b>用基本面气候学事前化——增量技能完全消失。</b>
两阶段模型里，把"法国负价小时"从<b>同期观测</b>换成<b>事前强度 λ</b> 后，
全样本 AUC <b>0.808 → 0.891（同期）</b> 掉回 <b>0.805（事前）</b>，比不带法国通道（0.808）还低；
2026 样本外同样：0.761 → <b>0.817</b>（同期） vs <b>0.764</b>（事前）。
⇒ PS-041 的"区域过剩"是<b>同期共振指标</b>，不是可由双方基本面预报出的驱动量。</div>

<div class="hl"><b>结论三：真正"事前可得"的是<b>持续性</b>与<b>日历</b>，其 2026 样本外 AUC 达 0.75。</b>
把同期量全部移出场（只用滞后/滚动特征），模型 2026 样本外 AUC <b>0.753</b>，高于纯日历口径的 0.680，
接近"同期国内基本面"的 0.761——但明显低于"同期区域状态"的 0.817。
⇒ 短期（D-1）预警应以<b>持续性 + 日历</b>为主力；45 天展望仍无法从区域通道获益。</div>

<div class="box"><h2 style="margin-top:0">① 法国侧：基本面 → 法国正午负价</h2>
<div class="note">窗口口径与 PS-040/041 完全一致（当地 10–16h）。法国字段集与西班牙不同，含
<code>Nuclear</code>（核电，中位约占正午负荷 <b>76%</b>）与 <code>Residual load</code>。
2026 起 Energy-Charts 的法国分辨率变为 15 分钟，已统一重采样到小时后再聚合。</div>
<div class="scroll"><table>
<tr><th>设定（Poisson，目标=法国正午负价小时∈[0,6]）</th><th>参数数</th><th>AIC</th><th>离散度</th><th>MAE (h/日)</th><th>AUC(负价日)</th></tr>
{mrow}
</table></div>
<div class="note">加入<b>核电份额</b>把 AUC 从 0.743 抬到 0.760，<b>周末</b>再到 0.792——
法国的负价机制是"核电压舱 + 光伏叠加 + 周末需求塌陷"，与西班牙（纯光伏过剩）机制不同。
离散度 2.3–3.5 仍显著 &gt;1，计数波动较大（沿用 PS-041 同一诊断）。</div>
<h3>逐年概览</h3>
<div class="scroll"><table>
<tr><th>年</th><th>日数</th><th>ES 负价日</th><th>ES 负价 h</th><th>ES 午比中位%</th><th>FR 午比中位%</th><th>FR 核电中位%</th><th>FR 负价 h/日</th></tr>
{ytab}
</table></div></div>

<div class="box"><h2 style="margin-top:0">② 可预报化的代价：留一年气候学</h2>
<div class="note">事前代理的做法：当年某日的法国光伏/核电份额 = <b>其他年份</b>同（月份, 是否周末）的均值
⇒ 不含任何同年度信息。再把它喂进法国模型，得到"事前强度 λ"。</div>
<div class="scroll"><table>
<tr><th>法国侧输入</th><th>日数</th><th>MAE (h/日)</th><th>Spearman(强度)</th><th>AUC(负价日)</th></tr>
{srow}
</table></div>
<div class="note">法国<b>自身</b>的排序能力损失不大（0.792 → 0.752），但换到西班牙侧做两阶段时，
这点损失被放大成"增量技能归零"——因为西班牙模型要的是法国状态里<b>日际跳动</b>的那部分，
而气候学代理在月内几乎是常数。</div>
<h3>两阶段：西班牙负价 ← 国内 + 法国通道（全样本）</h3>
<div class="scroll"><table>
<tr><th>设定</th><th>变量数</th><th>AIC</th><th>AUC(ES 负价日)</th><th>MAE(ES 负价h)</th><th>偏差</th></tr>
{trow}
</table></div>
<h3>样本外</h3>
<div class="scroll"><table>
<tr><th>训练至</th><th>设定</th><th>测试日</th><th>AUC</th><th>MAE</th><th>偏差</th></tr>
{orow}
</table></div></div>

<div class="box"><h2 style="margin-top:0">③ 反面：只用"事前可得"的特征能做到什么</h2>
<div class="note">同期份额、同期负荷、同期价格在 D-1 <b>都拿不到</b>。能拿到的只有<b>滞后与滚动</b>统计
（前 1 日值、前 3/7 日均值）以及日历。下表所有设定都不含任何同期量。</div>
<div class="scroll"><table>
<tr><th>设定（全部事前可得）</th><th>变量数</th><th>全样本 AUC</th><th>全样本 MAE (h/日)</th><th>2026 样本外 AUC</th><th>2026 样本外 MAE</th></tr>
{prow}
</table></div>
<div class="note">
全样本 AUC 冲到 0.93 是<b>样本内</b>数字，不能当技能；关键是最后一列——
<b>P1（日历 + 西班牙滞后负价）2026 样本外 0.753</b>，比 P0（纯日历）的 0.680 高 0.073
⇒ "负价日成串出现"这件事本身可事前利用。<br>
加法国滞后负价（P3，0.745）或法国基本面滚动（P4，0.748）<b>不再增益</b>，
再次说明区域通道的价值在"同期"而非"滞后"。</div>
<div class="note">三方对照（2026 样本外 AUC）：<b>事前可得 0.75</b> ｜ <b>同期国内基本面 0.761</b> ｜
<b>同期区域状态 0.817</b>。第一档可以立刻用于短期预警，第三档是天花板但不可预报。</div></div>

<div class="box"><h2 style="margin-top:0">④ 交付：条件结构表 + 校准修正</h2>
<div class="warn"><b>一个必须修的换算</b>：直接用泊松 <code>1−exp(−λ)</code> 把强度换成"负价日概率"会
<b>严重高估</b>——样本均值 0.449 vs 实际 0.182。原因是负价小时数<b>过散布 + 零膨胀</b>
（1368 日里 75% 是 0）。改用<b>经验可靠性曲线</b>后 P 才可用。</div>
{relchart(rel)}
<div class="note">经验曲线单调且形状正确：λ≈0.19 → P=3.5%；λ≈1.23 → 35.1%；λ≈5.40 → 76.6%。
泊松口径在整段区间都高出一大截。</div>
<h3>校准后 P(西班牙负价日 | 正午份额, 法国正午负价h)　（负荷按 600 GWh/日）</h3>
{condheat(tab)}
<div class="note">这就是 PS-041 §5 承诺的条件结构，现已量化：<b>法国是否也负价</b>的边际影响极大——
份额 55% 时，法国 0 h → <b>10.8%</b>，法国 4 h → <b>46.6%</b>；
当法国与西班牙双双正午过剩（FR≥4 h 且份额≥65%）时，负价日概率过半。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 对秋季 2026 展望的含义</h2>
<div class="note">把法国的秋季（10–11 月）气候学喂进两阶段模型，西班牙正午份额固定为 PS-040 口径的
<b>61.7%</b>。注意③已证明法国气候学不带来增量技能，所以下表只作<b>敏感性参照</b>。</div>
<div class="scroll"><table>
<tr><th>情景</th><th>FR 正午份额</th><th>E[FR 负价h/日]</th><th>E[ES 负价h/日]</th><th>泊松 P(负价日)</th><th>校准后 P(负价日)</th></tr>
{serow}
</table></div>
<div class="hl"><b>独立口径的交叉印证</b>：一条与 PS-039/040 完全不同族的路线（<b>日尺度泊松强度 + 可靠性校准</b>）
给出秋季 <b>15.8%（不带法国通道）～ 17.9%（带法国气候学）</b>，正好落在 PS-039 的
<b>8.6%–17.1%</b> 区间上沿、并高于 PS-040 的独立下界 8.2%。
⇒ 秋季数字<b>不需要修改</b>，且现在有了第三条独立支撑。</div>
<div class="note">秋季实测基准（说明为何该数字本身很敏感）：2023 年 10–11 月西班牙负价日率 <b>0%</b>（正午份额 34.9%）、
2024 年 <b>3.3%</b>（38.9%）、2025 年 <b>6.6%</b>（53.3%）。2026 年秋季份额外推到 61.7% 已<b>越出历史秋季区间</b>，
与 PS-040 的"外推不得越过线性区"是同一个警告。</div></div>

<div class="box"><h2 style="margin-top:0">⑥ 结论与下一步</h2>
<ul class="note">
<li><b>对 PS-041 的定位修正</b>：那条 +0.08 的 AUC 增益是<b>同期共振</b>带来的，不能计入预报技能。
引用"区域过剩"时必须声明它是<b>同期条件变量</b>，而不是"可预报的驱动"。</li>
<li><b>可预报的分层已清楚</b>：D-1 短期用<b>持续性 + 日历</b>（样本外 AUC 0.75）；
日尺度同期诊断用<b>国内基本面 + 区域状态</b>（0.76 → 0.82）；45 天展望仍回到
<b>国内份额阈值</b>口径（PS-039/040）。</li>
<li><b>下一步（能真正提升的只有一条）</b>：用 NWP 预报（而非气候学）填法国侧的光伏与负荷，
检验<b>短期（D-1～D-7）</b>能否把 0.75 推向 0.82——这是唯一有真实增益空间的路径。
季节尺度（45 天）已被本流程证否。</li>
<li><b>顺带修好的两件事</b>：①泊松概率换算必须过可靠性校准，否则高估约 2.5 倍；
②概率模型要报"事前可得"与"同期"两套 AUC，否则技能会被同期量虚增。</li>
</ul></div>

<div class="note" style="margin-top:6px">数据：Energy-Charts <code>/public_power?country=fr</code>（法国光伏/负荷/核电/剩余负荷，2023–2026）、
<code>/price?bzn=FR</code>（法国日前价）；西班牙侧沿用 PS-041 日面板。方法与产物见 <code>PS-042</code>；
上游 <code>PS-041</code>（跨境结构）、<code>PS-040</code>（正午窗口）、<code>PS-039</code>（份额阈值）。</div>
</div></body></html>"""
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("→ %s" % os.path.join(OUT, "index.html"))


if __name__ == "__main__":
    main()
