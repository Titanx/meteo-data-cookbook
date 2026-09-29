"""西班牙 负价模型 v3（趋势 + logit + 强度）报告 (PS-038)
输入: data/spain/{spain_official_daily,spain_negprice_v3_skill,spain_negprice_v3_skill_train23,
      spain_negprice_v3_reliability,spain_negprice_v3_outlook,spain_negprice_v3_scenarios}.csv
输出: output/spain_negprice_v3/index.html
用法: python scripts/analysis/build_spain_negprice_v3_report.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_negprice_v3"
os.makedirs(OUT, exist_ok=True)
BLUE, RED, ORANGE, GREY, GREEN, PURPLE = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4", "#2f8f6b", "#7a5aa8"
MON = "1月 2月 3月 4月 5月 6月 7月 8月 9月 10月 11月 12月".split()


def svg_monthly(ml):
    """逐月负价日率: 2024/2025/2026 三条线"""
    w, ht, pad = 820, 300, (46, 20, 40, 56)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    vmax = 0.85
    X = lambda i: x0 + (x1 - x0) * i / 11
    Y = lambda v: y1 - (y1 - y0) * v / vmax
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in np.linspace(0, vmax, 6):
        o.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        o.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t*100:.0f}%</text>')
    for i, lab in enumerate(MON):
        o.append(f'<text x="{X(i):.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">{lab}</text>')
    for year, col, dash in ((2024, BLUE, ""), (2025, ORANGE, ""), (2026, RED, ' stroke-dasharray="5,3"')):
        ser = ml[year]
        pts = [(X(i), Y(ser[i])) for i in range(12) if not np.isnan(ser[i])]
        if not pts:
            continue
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.2"%s/>'
                 % (" ".join("%.1f,%.1f" % p for p in pts), col, dash))
        for i in range(12):
            if np.isnan(ser[i]):
                continue
            o.append(f'<circle cx="{X(i):.1f}" cy="{Y(ser[i]):.1f}" r="3.2" fill="{col}"/>')
    for j, (year, col) in enumerate(((2024, BLUE), (2025, ORANGE), (2026, RED))):
        o.append(f'<circle cx="{x0+14+j*88}" cy="{ht-12}" r="4" fill="{col}"/>'
                 f'<text x="{x0+22+j*88}" y="{ht-8}" fill="#5b7488">{year}</text>')
    o.append("</svg>")
    return "\n".join(o)


def svg_reliability(rel):
    w, ht, pad = 420, 300, (46, 20, 40, 56)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    Y = lambda v: y1 - (y1 - y0) * v
    X = lambda v: x0 + (x1 - x0) * v
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in np.linspace(0, 1, 6):
        o.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        o.append(f'<line x1="{X(t):.0f}" x2="{X(t):.0f}" y1="{y0}" y2="{y1}" stroke="#eef3f7"/>')
        o.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t:.1f}</text>')
        o.append(f'<text x="{X(t):.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">{t:.1f}</text>')
    o.append(f'<line x1="{X(0):.0f}" y1="{Y(0):.0f}" x2="{X(1):.0f}" y2="{Y(1):.0f}" stroke="{GREY}" stroke-dasharray="4,3"/>')
    for spec, col, mk in (("P · logit S+负荷+趋势", BLUE, "circle"),
                          ("P · logit S+负荷+趋势+季节", PURPLE, "square")):
        s = rel[rel["spec"] == spec].sort_values("bin")
        pts = " ".join("%.1f,%.1f" % (X(r.p_mean), Y(r.actual)) for r in s.itertuples())
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.2"/>')
        for r in s.itertuples():
            o.append(f'<circle cx="{X(r.p_mean):.1f}" cy="{Y(r.actual):.1f}" r="4.2" fill="{col}"/>')
    for j, (spec, col) in enumerate((("含趋势（主用）", BLUE), ("含自由季节项（过拟合）", PURPLE))):
        o.append(f'<circle cx="{x0+12+j*150}" cy="{ht-12}" r="4" fill="{col}"/>'
                 f'<text x="{x0+20+j*150}" y="{ht-8}" fill="#5b7488">{spec}</text>')
    o.append(f'<text x="{(x0+x1)/2:.0f}" y="{y0+16}" text-anchor="middle" fill="{GREY}">2026 预测概率</text>')
    o.append(f'<text x="{x0-38}" y="{(y0+y1)/2:.0f}" fill="{GREY}" transform="rotate(-90 {x0-38} {(y0+y1)/2:.0f})" text-anchor="middle">实际负价日率</text>')
    o.append("</svg>")
    return "\n".join(o)


def svg_outlook(o_df, scen, ps035, ps037c):
    w, ht, pad = 820, 320, (46, 20, 46, 56)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    n = len(o_df)
    X = lambda i: x0 + (x1 - x0) * i / max(n - 1, 1)
    vmax = 0.35
    Y = lambda v: y1 - (y1 - y0) * min(v, vmax) / vmax
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in np.linspace(0, vmax, 6):
        o.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        o.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t*100:.0f}%</text>')
    band = " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in enumerate(o_df["P_c90"]))
    band += " " + " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in reversed(list(enumerate(o_df["P_c10"]))))
    o.append(f'<polygon points="{band}" fill="{BLUE}" opacity="0.15"/>')
    o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4"/>'
             % (" ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in enumerate(o_df["P_c50"])), BLUE))
    for lab, val, col, dsh in (("A 趋势口径", scen["A_trend"], RED, "6,3"),
                               ("B 秋季残差口径", scen["B_autumn_resid"], ORANGE, ""),
                               ("C 同年比例口径", scen["C_same_ratio"], GREEN, "3,3"),
                               ("PS-035（8.2%）", ps035, GREY, "2,3")):
        yy = Y(val)
        o.append(f'<line x1="{x0}" x2="{x1}" y1="{yy:.0f}" y2="{yy:.0f}" stroke="{col}" stroke-width="1.6" stroke-dasharray="{dsh}"/>')
        o.append(f'<text x="{x1-2}" y="{yy-5:.0f}" text-anchor="end" fill="{col}" font-weight="700">{lab} {val*100:.1f}%</text>')
    for i in (0, 14, 29, 44):
        o.append(f'<text x="{X(i):.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">{str(o_df["date"].iloc[i])[5:10]}</text>')
    o.append(f'<text x="{x0}" y="{ht-8}" fill="{GREY}">蓝线=模型 P50（B 口径，含 50 成员 P10–P90 带）；横线=三种情景的窗口均值</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    g = pd.read_csv(os.path.join(D, "spain_official_daily.csv"), index_col=0, parse_dates=True)
    g = g[g["S"].notna()]
    sk = pd.read_csv(os.path.join(D, "spain_negprice_v3_skill.csv"))
    sk23 = pd.read_csv(os.path.join(D, "spain_negprice_v3_skill_train23.csv"))
    rel = pd.read_csv(os.path.join(D, "spain_negprice_v3_reliability.csv"))
    od = pd.read_csv(os.path.join(D, "spain_negprice_v3_outlook.csv"), parse_dates=["date"])
    sc = pd.read_csv(os.path.join(D, "spain_negprice_v3_scenarios.csv"))
    scen = dict(zip(sc["scenario"], sc["window_mean"]))
    ps035, ps037c = scen["PS-035"], scen["PS-037_corrected"]

    # 逐月矩阵
    mat = (g.pivot_table(index=g.index.month, columns=g.index.year, values="negday", aggfunc="mean") * 100)
    ml = {y: [mat.loc[m, y] / 100 if (m in mat.index and y in mat.columns and pd.notna(mat.loc[m, y]))
              else np.nan for m in range(1, 13)] for y in (2024, 2025, 2026)}
    mrows = ""
    for m in range(1, 13):
        cells = "".join('<td>%s</td>' % ("%.1f" % mat.loc[m, y] if (m in mat.index and y in mat.columns and pd.notna(mat.loc[m, y])) else "–")
                        for y in (2023, 2024, 2025, 2026))
        mrows += "<tr><td>%s</td>%s</tr>" % (MON[m - 1], cells)
    hr = g.pivot_table(index=g.index.month, columns=g.index.year, values="negh", aggfunc="mean")

    # 逐年
    yearly = g.groupby("year").agg(天=("negday", "size"), 负价日率=("negday", "mean"),
                                   负价h日均=("negh", "mean"), 均价=("price", "mean"))
    yr = "".join("<tr><td>%d</td><td>%d</td><td%s>%.1f%%</td><td>%.2f</td><td>%.1f</td></tr>"
                 % (int(y), int(r["天"]), ' class="neg" style="font-weight:700"' if int(y) == 2026 else "",
                    r["负价日率"] * 100, r["负价h日均"], r["均价"]) for y, r in yearly.iterrows())

    # 设定比较表
    def skill_table(df):
        out = ""
        for r in df.itertuples():
            cls = ' class="pos" style="font-weight:700"' if r.auc_2026 > 0.85 else (
                ' class="neg"' if r.auc_2026 < 0.80 else ' style="font-weight:700"')
            br = "–" if pd.isna(r.brier_2026) else "%.4f" % r.brier_2026
            out += ("<tr><td>%s</td><td>%d</td><td>%.3f</td><td>%.3f</td><td%s>%.3f</td>"
                    "<td>%.3f</td><td>%.3f</td><td>%s</td></tr>"
                    % (r.spec, r.k_params, r.auc_2024, r.auc_2025, cls, r.auc_2026,
                       r.predmean_2026, r.actual_2026, br))
        return out

    # 可靠性表
    rr = ""
    for spec in ("P · logit S+负荷+趋势", "P · logit S+负荷+趋势+季节"):
        s = rel[rel["spec"] == spec].sort_values("bin")
        for r in s.itertuples():
            rr += ("<tr><td>%s</td><td>Q%d</td><td>%d</td><td>%.3f</td><td>%.3f</td><td%s>%+.3f</td></tr>"
                   % (("含趋势（主用）" if "季节" not in spec else "含自由季节项"), int(r.bin) + 1,
                      int(r.n), r.p_mean, r.actual,
                      ' class="neg"' if abs(r.gap) > 0.15 else "", r.gap))

    # 展望周表
    wk = od.groupby("wk").agg(周起=("date", "first"), tau=("tau_p50", "median"), S=("S_p50", "median"),
                              load=("load_p50", "median"), A=("P_mean", "mean"), B=("P_corr", "mean"),
                              P10=("P_c10", "median"), P50=("P_c50", "median"), P90=("P_c90", "median"),
                              H=("H_corr", "mean")).reset_index()
    wr = ""
    for _, r in wk.iterrows():
        wr += ("<tr><td>W%d</td><td>%s</td><td>%.3f</td><td>%.2f</td><td>%.1f</td>"
               "<td>%.1f%%</td><td class='neg' style='font-weight:700'>%.1f%%</td>"
               "<td>%.1f%%</td><td>%.1f%%</td><td>%.1f%%</td><td>%.2f</td></tr>"
               % (int(r["wk"]), str(r["周起"])[:10], r["tau"], r["S"], r["load"],
                  r["A"] * 100, r["B"] * 100, r["P10"] * 100, r["P50"] * 100, r["P90"] * 100, r["H"]))

    scrows = ""
    for _, r in sc.iterrows():
        nm = {"A_trend": "A · 趋势口径", "B_autumn_resid": "B · 秋季残差口径",
              "C_same_ratio": "C · 同年比例口径", "PS-037_corrected": "参照 · PS-037（线性+概率域 clip）",
              "PS-035": "参照 · PS-035 原式"}[r["scenario"]]
        scrows += ("<tr><td>%s</td><td style='font-weight:700'>%.1f%%</td><td>%.1f 天</td><td>%s</td></tr>"
                   % (nm, r["window_mean"] * 100, r["window_mean"] * 45, r["note"]))

    b19 = sk23[sk23["spec"] == "P · logit S+负荷+趋势"].iloc[0]
    b23 = sk23[sk23["spec"] == "P · logit S+负荷+趋势+季节"].iloc[0]
    hbest = sk23[sk23["spec"] == "H · 泊松 S+负荷"].iloc[0]

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙负价模型 v3 · 趋势 / logit / 强度</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.62}}
.wrap{{max-width:1060px;margin:0 auto;padding:28px 20px}}
h1{{font-size:23px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
h3{{font-size:14px;margin:16px 0 6px;color:#3c556b}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:14px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:7px 9px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
td:first-child,th:first-child{{text-align:left}}
.neg{{color:#c23a3a;font-weight:600}}.pos{{color:#1f5bb8;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}
.hl{{background:#eef6ef;border-left:3px solid #2f8f6b;padding:12px 16px;border-radius:6px;margin:14px 0}}
.warn{{background:#fff6ea;border-left:3px solid #e5853a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}li{{margin:5px 0}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:820px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<h1>西班牙负价模型 v3 · 趋势 / logit / 强度</h1>
<div class="sub">修正 PS-037 的三个遗留问题：水位低估、P10 退化、季节校正靠事后平移 · 核查日 2026-09-29 · 逐日样本 1366 天（2023-01 ~ 2026-09）</div>

<div class="hl"><b>结论一：趋势项修好了"水位"。</b>负价日率 2023→2026 为 <b>0% → 12.6% → 24.2% → 42.4%</b>，而 PS-037 的模型把 2026 均值预测成 0.10~0.17（实际 0.424）。加入时间趋势项后，2026 预测均值回到 <b>{b19.predmean_2026:.3f}</b>，<b>Brier 由 {sk23[sk23['spec']=='P · 线性 S+负荷 (PS-037 基线)'].iloc[0].brier_2026:.4f} 降到 {b19.brier_2026:.4f}</b>——这是本流程最大的单项改善。</div>

<div class="warn"><b>结论二：但"自由季节形状 + 趋势"会过冲到不可用。</b>把年内季节谐波交给数据自己学（训练 2024-25），2024/2025 的 AUC 冲到 0.918/0.953，<b>2026 却掉到 {b23.auc_2026:.3f}</b>，且预测均值 0.576 vs 实际 0.424、分箱严重过度自信——典型的两年样本过拟合。<b>2 年的秋季不足以学出可泛化的季节形状</b>，这也解释了 PS-035"事后平移截距"反而更稳的原因。</div>

<div class="hl"><b>结论三：把目标从"负价日"换成"负价小时强度"是排序能力的最大增益。</b>泊松强度模型 2026 AUC <b>{hbest.auc_2026:.3f}</b>（二元 logit 最好 {b19.auc_2026:.3f}）；但它的水平需要重新标定（预测 {hbest.predmean_2026:.2f} vs 实际 {hbest.actual_2026:.2f} h/日），且数据<b>过度离散</b>（离散度 ≈ 2.7），标准误被低估。</div>

<div class="box"><h2 style="margin-top:0">① 关键诊断：2026 的季节形状与往年完全不同</h2>
{svg_monthly(ml)}
<div class="scroll"><table>
<tr><th>月</th><th>2023</th><th>2024</th><th>2025</th><th>2026</th></tr>
{mrows}
</table></div>
<div class="note">负价<b>日率（%）</b>。2024/2025 的峰值在 <b>4–5 月</b>，10–12 月几乎归零；而 <b>2026 的峰值在 2–5 月（78.6% / 61.3% / 70.0% / 61.3%），9 月却只有 13.8%</b>。
即：<b>2026 的"高"主要来自冬末—春季，秋季并不比往年高多少</b> —— 这正是"趋势项在季节尺度上过冲"的根源，也是本次展望不确定性的来源。</div>
<div class="note">对照负价 <b>小时强度（h/日）</b>：2026 年 2 月 5.29 h/日、4 月 4.60，而 9 月 0.79、2024-10 仅 0.16 ⇒ 秋季在结构上仍是低风险季。</div></div>

<div class="box"><h2 style="margin-top:0">② 模型设定比较（样本外：train 2023-25 → test 2026）</h2>
<div class="scroll"><table>
<tr><th>设定</th><th>参数数</th><th>→2024 AUC</th><th>→2025 AUC</th><th>→2026 AUC</th><th>2026 预测均</th><th>2026 实际</th><th>Brier</th></tr>
{skill_table(sk23)}
</table></div>
<div class="note">统一训练 2023-2025（含 2023 的"零负价"，为趋势项提供真实信息）。读法：<br>
• <b>加趋势</b>：AUC 略降（{sk23.iloc[0].auc_2026:.3f} → {b19.auc_2026:.3f}），但<b>校准大幅改善</b>（预测均 0.103 → 0.459，Brier 0.305 → 0.206）⇒ 趋势买到的是"水位"不是"排序"。<br>
• <b>换 logit</b>：几乎不影响 AUC，但<b>概率不再被 clip</b>，于是可以用 Brier/可靠性评估，且 P10 不再退化为 0。<br>
• <b>加自由季节项</b>：训练年 AUC 高得可疑（0.916/0.953），2026 反而<b>更差</b>（{b23.auc_2026:.3f}）⇒ 过拟合。<br>
• <b>换目标为负价小时（泊松）</b>：2026 AUC <b>{hbest.auc_2026:.3f}</b>，成为最好的排序器——但水平需重标定。</div>
<div class="scroll"><table>
<tr><th>设定</th><th>参数数</th><th>→2024 AUC</th><th>→2025 AUC</th><th>→2026 AUC</th><th>2026 预测均</th><th>2026 实际</th><th>Brier</th></tr>
{skill_table(sk)}
</table></div>
<div class="note">同一张表在 <b>train 2024-25 → test 2026</b>（与 PS-037 严格可比）下的结果，结论一致：趋势改善校准、自由季节项损害样本外。PS-037 报告的"PS-035 原式 2026 AUC 0.491"在这里以 <b>线性 S+负荷 = 0.811</b> 复现（PS-037 的 0.491 对应"无负荷项"的单因子版本）。</div></div>

<div class="box"><h2 style="margin-top:0">③ 2026 可靠性检验（train 2023-25，等样本五分位）</h2>
<div class="grid">
<div>{svg_reliability(rel)}</div>
<div class="scroll"><table>
<tr><th>设定</th><th>档</th><th>n</th><th>预测均</th><th>实际</th><th>偏差</th></tr>
{rr}
</table></div>
</div>
<div class="note">虚线为完美校准。含趋势的主用模型基本贴着对角线（最大偏差 {rel[rel['spec']=='P · logit S+负荷+趋势']['gap'].abs().max():.3f}），
最低档仍偏保守（预测 0.042 vs 实际 0.218）；含自由季节项则<b>中高档严重过度自信</b>（预测 0.673 vs 实际 0.241）。
⇒ 结论：<b>季节形状不可交给 2 年数据自由拟合</b>，但"趋势 + 负荷 + S"的 logit 在概率尺度上是可信的。</div></div>

<div class="box"><h2 style="margin-top:0">④ 未来 45 天（2026-09-29 ~ 11-12）：三情景分歧是主要结论</h2>
{svg_outlook(od, scen, ps035, ps037c)}
<div class="scroll"><table>
<tr><th>情景</th><th>45 天窗口均值</th><th>折算负价日数</th><th>含义</th></tr>
{scrows}
</table></div>
<div class="note">A/B/C 都是同一模型的合法外推，差别只在"负价常态化趋势如何延续到秋季"：<br>
• <b>A 趋势口径（{scen['A_trend']*100:.1f}%）</b>：完全相信趋势项线性外推。但 2026 的"高"集中在冬春（见①），据此外推秋季会明显过冲。<br>
• <b>B 秋季残差口径（{scen['B_autumn_resid']*100:.1f}%）</b>：假定"秋季相对趋势偏弱"这一残差在 2026 重复（与 PS-037 同思路，但改在<b>链接空间</b>平移，不再 clip）。<br>
• <b>C 同年比例口径（{scen['C_same_ratio']*100:.1f}%）</b>：用 2024/2025 稳定的"10–11 月 / 全年"比例（0.261 / 0.271）乘 2026 年率（42.4%）。<br>
⇒ <b>PS-035 的 8.2% 与 PS-037 的 6.8% 都落在 C（11.3%）之下</b>：它们相当于"秋季继续保持异常偏弱"。若 2026 秋季与全年同步，真实值更可能接近 11%（C）。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 逐周展望（B 口径，含 50 成员 P10–P90）</h2>
<div class="scroll"><table>
<tr><th>周</th><th>周起</th><th>fleet τ</th><th>S</th><th>负荷 GW</th><th>A 趋势口径</th><th>B 秋季残差</th><th>P10</th><th>P50</th><th>P90</th><th>负价 h/日</th></tr>
{wr}
</table></div>
<div class="note">两周内概率最高（W2 10 月初 {wk.loc[2,'B']*100:.1f}%），11 月中旬随入秋与资源下降而回落。
<b>P10–P90 带已不再是单点</b>（logit 无 clip 所致）：W1 为 {wk.loc[1,'P10']*100:.1f}%–{wk.loc[1,'P90']*100:.1f}%。<br>
注意成员间离散度本身较小——真正的不确定性来自<b>口径选择（A/B/C 相差 5 倍）而非季节集合</b>，这一点必须明确。</div></div>

<div class="box"><h2 style="margin-top:0">⑥ 结论、局限与下一步</h2>
<ul class="note">
<li><b>可用结论</b>：①负价水位的确在快速上移，<b>趋势项是把 2026 校准拉回可用的关键</b>（Brier 0.305 → 0.206）；②概率模型应使用 <b>logit</b>（可评估、不退化）；③<b>"负价小时强度"比"是否负价日"信息量更大</b>，2026 AUC {hbest.auc_2026:.3f} 为全部设定最高；④秋季 45 天的负价日概率<b>约在 11%（C）~ 21%（B）之间</b>，A 口径的 62% 视为上界而非预期。</li>
<li><b>为什么仍不能给单一数字</b>：2026 的季节形状与 2024/25 完全不同（冬春极高、秋季平平），因此"趋势 + 季节"无法用 2 年数据分辨。这是<b>数据年限不足</b>的问题，不是方法问题。</li>
<li><b>局限</b>：①训练仅 3 年（2023 零负价、2024/2025 各一年秋季），季节项不可识别；②趋势项与"装机渗透率上升"混淆，未能分离（GEM 只有年度装机）；③泊松模型过度离散（≈2.7），标准误偏小，且水平需重标定；④2026 的 `pot_cs` 仍是 PS-037 的合成值；⑤负荷温度代理取 9 个光伏区（非人口加权），冬季采暖代表性弱；⑥仍用日前价、日尺度。</li>
<li><b>下一步</b>：①用 <b>NegativeBinomial</b> 或带离散参数的泊松替换泊松，修正过度离散；②把趋势项换成<b>可解释的渗透率变量</b>（按月的累计光伏装机/负荷比）；③用 <b>ERA5 回算 2015–2022</b> 扩到 8~10 年，让季节项可识别；④负荷改用<b>人口加权</b>温度；⑤把"日"细化到"小时"（负价小时可直接用小时模型）。</li>
</ul></div>

<div class="note" style="margin-top:6px">数据源：ENTSO-E 官方（A44/A75/A65，PS-036）、Open-Meteo Seasonal（50 成员 × 45 天）、Open-Meteo Archive 温度。
方法与产物见 <code>PS-038</code>；上游为 <code>PS-035</code>（原始链路）与 <code>PS-037</code>（官方口径复核 + 2026 样本外）。</div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("→ %s" % p)


if __name__ == "__main__":
    main()
