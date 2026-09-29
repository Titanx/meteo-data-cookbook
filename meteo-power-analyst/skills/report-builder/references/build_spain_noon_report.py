# -*- coding: utf-8 -*-
"""PS-040 报告: 正午窗口(10-16h)份额 vs 月度份额 —— 负价机制定位与外推边界

输出: output/spain_negprice_noon/index.html
用法: python skills/report-builder/references/build_spain_noon_report.py
"""
import os
import numpy as np
import pandas as pd

NOON = r"c:\work\meteo\data\spain\spain_noon_panel.csv"
FIT = r"c:\work\meteo\data\spain\spain_noon_threshold_fit.csv"
OUT = r"c:\work\meteo\output\spain_negprice_noon"

RED, BLUE, ORANGE, PURPLE = "#c23a3a", "#1f5bb8", "#e5853a", "#7a4fd0"
GREY, GREEN = "#8fa4b8", "#2f8f6b"


def scatter(p):
    """右图: 正午份额(10-16h) vs 正午窗口负价小时占比; 左区无点为结构性零价期"""
    W, H = 660, 360
    L, R, T, B = 52, 14, 16, 40
    xr = (0.05, 0.85)
    yr = (0.0, 0.95)

    def X(v):
        return L + (v - xr[0]) / (xr[1] - xr[0]) * (W - L - R)

    def Y(v):
        return H - B - (v - yr[0]) / (yr[1] - yr[0]) * (H - T - B)

    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">']
    s.append(f'<rect x="{L}" y="{T}" width="{W-L-R}" height="{H-T-B}" fill="#fbfdff" stroke="#e3ecf4"/>')
    for g in np.arange(0, 0.91, 0.2):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#eef3f7"/>' % (L, Y(g), W - R, Y(g)))
        s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#9ab0c2" text-anchor="end">%.0f%%</text>'
                 % (L - 6, Y(g) + 3, g * 100))
    for g in np.arange(0.1, 0.86, 0.1):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#eef3f7"/>' % (X(g), T, X(g), H - B))
        s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#9ab0c2" text-anchor="middle">%.0f</text>'
                 % (X(g), H - B + 14, g * 100))
    s.append('<text x="%.1f" y="%.1f" font-size="11" fill="#6b8296" text-anchor="middle">正午份额(当地 10-16h 光伏/负荷, %%)</text>'
             % ((L + W - R) / 2, H - 6))
    s.append('<text x="14" y="%.1f" font-size="11" fill="#6b8296" transform="rotate(-90 14 %.1f)" text-anchor="middle">'
             '正午窗口负价小时占比</text>' % ((T + H - B) / 2, (T + H - B) / 2))

    d = p.dropna(subset=["noon_share_10_16", "noon_neg_frac"]).copy()
    d["year"] = [int(k[:4]) for k in d.index]
    order = [(2015, 2022, "#c9d4de", 3.0, 0.9), (2023, 2023, BLUE, 4.0, 0.95),
             (2024, 2024, ORANGE, 4.5, 0.95), (2025, 2025, PURPLE, 4.5, 0.95),
             (2026, 2026, RED, 4.5, 1.0)]
    for y0, y1, col, r, op in order:
        sub = d[(d.year >= y0) & (d.year <= y1)]
        for _, r_ in sub.iterrows():
            s.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="%.2f"/>'
                     % (X(r_.noon_share_10_16), Y(r_.noon_neg_frac), r, col, op))
    # 2026 各月标注
    for _, r_ in d[d.year == 2026].iterrows():
        s.append('<text x="%.1f" y="%.1f" font-size="9" fill="%s">%d月</text>'
                 % (X(r_.noon_share_10_16) + 5, Y(r_.noon_neg_frac) - 4, RED, int(r_.name[5:7])))
    # 秋季 2026 外推份额
    x26 = 0.617
    s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.6" stroke-dasharray="5,4"/>'
             % (X(x26), T, X(x26), H - B, GREEN))
    s.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="%s">秋季2026外推 61.7%%</text>'
             % (X(x26) + 5, T + 13, GREEN))
    s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" stroke-dasharray="3,3"/>'
             % (X(0.31), T, X(0.31), H - B, GREY))
    s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#8fa4b8">全局θ=31%%</text>' % (X(0.31) - 58, H - B - 6))
    s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" stroke-dasharray="3,3"/>'
             % (X(0.27), T, X(0.27), H - B, GREY))
    s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#8fa4b8">秋季θ=27%%</text>' % (X(0.27) - 58, T + 30))
    s.append('</svg>')
    return "".join(s)


def bars(items):
    vmax = 66.0
    b = ""
    for lab, v, col, note in items:
        b += ('<div style="display:flex;align-items:center;margin:6px 0;font-size:12.5px">'
              '<div style="width:215px;color:#3c556b">%s</div>'
              '<div style="flex:1;background:#eef3f7;border-radius:3px;height:16px">'
              '<div style="width:%.1f%%;height:16px;background:%s;border-radius:3px"></div></div>'
              '<div style="width:56px;text-align:right;font-weight:700;color:%s">%.1f%%</div>'
              '<div style="width:150px;color:#8497a8;padding-left:10px">%s</div></div>'
              % (lab, v / vmax * 100, col, col, v, note))
    return b


def main():
    os.makedirs(OUT, exist_ok=True)
    p = pd.read_csv(NOON).set_index("ym")
    p["m"] = [int(k[5:7]) for k in p.index]
    p["y"] = [int(k[:4]) for k in p.index]

    # 年度概览
    rows = ""
    for y, r in p.groupby("y").agg(午=("noon_share_10_16", lambda x: x.mean() * 100),
                                   全=("solar_share", lambda x: x.mean() * 100),
                                   负价h=("neg_h", "sum"),
                                   窗口h=("neg_noon_h", "sum")).iterrows():
        rows += ("<tr><td>%d</td><td>%.1f</td><td>%.1f</td><td%s>%d</td><td>%d</td></tr>"
                 % (y, r.午, r.全, ' class="neg"' if r.窗口h else "", int(r.负价h), int(r.窗口h)))

    # 2024-2026 逐月对照
    rows2 = ""
    for k, r in p[p.y >= 2024].iterrows():
        rows2 += ("<tr><td>%s</td><td>%.1f</td><td>%d</td><td%s>%d</td><td%s>%.1f</td><td>%d</td></tr>"
                  % (k, r.noon_share_10_16 * 100, int(r.n_noon_h), ' class="neg"' if r.neg_noon_h else "",
                     int(r.neg_noon_h), ' class="neg"' if r.noon_neg_frac > 0.3 else "",
                     r.noon_neg_frac * 100, int(r.neg_h)))

    fit = pd.read_csv(FIT)

    SCEN = [("PS-037（官方口径复核）", 6.8, GREY, "45 天，两因子"),
            ("2025 年秋季实测", 6.5, GREY, "基准年"),
            ("**PS-040 秋季正午θ=27%**", 8.2, GREEN, "2 个非零点"),
            ("PS-035（原式 S 指数）", 8.2, GREY, "45 天"),
            ("**PS-039 秋季月度θ=10.5%**", 8.6, GREEN, "2 个非零点"),
            ("PS-038 C 同年比例", 11.3, BLUE, "比例口径"),
            ("**PS-039 全局月度θ=16%**", 17.1, GREEN, "全样本阈值"),
            ("**PS-040 有界 logistic**", 20.1, ORANGE, "全样本 logistic"),
            ("PS-038 B 秋季残差", 21.4, ORANGE, "残差口径"),
            ("**PS-040 全局正午θ=31%**", 31.6, RED, "线性外推饱和"),
            ("PS-038 A 趋势外推", 62.0, RED, "过冲上界")]

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙负价: 正午窗口份额 vs 月度份额（PS-040）</title>
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
<h1>正午窗口份额 vs 月度份额：机制定位与外推边界</h1>
<div class="sub">PS-039 用<b>月度</b>光伏份额得到 θ=16% 的爆发阈值。本流程把驱动量换成
<b>当地时间 10–16h 窗口的光伏/负荷比</b>（"正午份额"），检验是否更贴合机制、并考察秋季 2026 外推是否收敛 · 核查日 2026-09-29</div>

<div class="hl"><b>结论一：正午窗口就是负价的"现场"——72% 的负价小时落在当地 10–16h。</b>
2024/2025/2026 三年稳定为 <b>71% / 72% / 72%</b>（窗口 6 h × 30 天 ≈ 全月小时的 25%）。
正午份额从 2015 年的 11.1% 单调升到 2026 年的 <b>63.5%</b>。</div>

<div class="warn"><b>结论二：换驱动量只买到很小的改善，且改善在"偏差"而非"误差"。</b>
全样本 MAE <b>11.0 → 10.4 h/月</b>（9–17h 窗口最优）、R² 0.339 → 0.363；
样本外 MAE 几乎不变（55.6 → 55.7），但**系统性低估明显减轻**（偏差 −29.2 → <b>−24.5</b> h/月）。
⇒ 正午份额是更"正确"的驱动，但**不是**更强的预测器。</div>

<div class="warn"><b>结论三：秋季 2026 的水平依旧无法由份额钉死，区间反而变宽。</b>
同一驱动量下，四种设定给出 <b>8.2% / 20.1% / 31.6%</b>（外加 PS-039 的 8.6%/17.1%）。
根因是"份额 → 负价"的映射**本身不单调、季节依赖强**：
同为 59–64% 的正午份额，2025 年 5 月窗口负价占比高达 <b>86.6%</b>，而 2024 年 5 月只有 <b>14.0%</b>；
2026 年内更是**份额越高、占比越低**（3 月 58.7%→52.2%，9 月 77.6%→11.5%）。
⇒ **PS-039 的 8.6%–17.1% 应保留，不应据此收窄。**</div>

<div class="box"><h2 style="margin-top:0">① 驱动量对比（全样本, 目标 = 逐月负价小时）</h2>
<div class="scroll"><table>
<tr><th>设定</th><th>θ</th><th>R²</th><th>MAE (h/月)</th><th>说明</th></tr>
<tr><td>线性趋势</td><td>—</td><td>0.214</td><td>17.5</td><td>PS-038 口径</td></tr>
<tr><td>月度份额（PS-039）</td><td>16.0%</td><td>0.339</td><td>11.0</td><td>月度光伏/需求</td></tr>
<tr><td><b>正午份额 9–17h</b></td><td><b>28.0%</b></td><td><b>0.363</b></td><td><b>10.4</b></td><td>8 h 窗口</td></tr>
<tr><td>正午份额 10–16h</td><td>31.0%</td><td>0.354</td><td>10.6</td><td>6 h 窗口（主口径）</td></tr>
<tr><td>正午份额 11–15h</td><td>31.0%</td><td>0.349</td><td>10.8</td><td>4 h 窗口</td></tr>
<tr><td>月度份额 + 月份FE</td><td>16.5%</td><td>0.415</td><td>13.3</td><td>吸收季节形状</td></tr>
<tr><td>正午份额 10–16h + 月份FE</td><td>32.0%</td><td>0.419</td><td>13.8</td><td>同上</td></tr>
</table></div>
<div class="note">窗口越宽越好（含更多肩部小时），但三者都在**同一水平**上小幅优于月度口径；
加月份固定效应后 R² 上升而 MAE 变差（灵活度买到的是季节形状，不是逐月精度）。</div></div>

<div class="box"><h2 style="margin-top:0">② 样本外：逐年扩展窗口</h2>
<div class="scroll"><table>
<tr><th>训练至</th><th>测试月数</th><th>月度份额</th><th>正午 10–16h</th><th>正午 11–15h</th><th>线性趋势</th></tr>
{"".join("<tr><td>≤%d</td><td>%d</td><td>MAE %.1f (%+.1f)</td><td>MAE %.1f (<b>%+.1f</b>)</td><td>MAE %.1f (%+.1f)</td><td>MAE %.1f (%+.1f)</td></tr>" % (
    int(r.train_to), int(r.n_test), r.mae_solar_share, r.bias_solar_share,
    r.mae_noon_share_10_16, r.bias_noon_share_10_16, r.mae_noon_share_11_15, r.bias_noon_share_11_15,
    r.mae_trend, r.bias_trend) for r in fit.itertuples())}
</table></div>
<div class="note">MAE 三者几乎相同（正午仅 0.1–0.4 之差），但**偏差**明显分化：
训练至 ≤2025 时月度口径低估 −29.2 h/月，正午口径只低估 <b>−24.5</b>。份额升得越快，
"用历史水平拟合"就落后越多；正午口径落后得更少。⚠ "训练至 2023"一行退化（此前负价全为 0）。</div></div>

<div class="box"><h2 style="margin-top:0">③ 为什么份额钉不死水平：同份额、不同季节</h2>
<div class="two"><div>{scatter(p)}</div>
<div class="note">横轴 = 正午份额，纵轴 = 正午窗口内负价小时占比。
灰点 2015–2022（结构性零价期，全部贴底），蓝 2023，橙 2024，紫 2025，红 2026（带月份标注）。
绿虚线 = 2026 年 10–11 月外推份额 61.7%。<br><br>
读图要点：<br>
<b>①</b> 灰点在份额 10–41% 区间全部为 0，橙/紫/红在 38% 以上明显抬升 ⇒ 阈值现象真实存在。<br>
<b>②</b> 但同一份额下纵向散布极大：2025-05（58.7%）达 86.6%，2024-05（64.1%）仅 14.0%。<br>
<b>③</b> 2026 年（红）呈**负斜率**：3 月 58.7%→52.2%，8 月 79.8%→17.7%，9 月 77.6%→11.5%
（夏季负荷高、光伏分布更散，同样份额下正午过剩更少）。<br>
⇒ 单靠份额无法定水平，**季节/月份上下文不可缺**。</div></div></div>

<div class="box"><h2 style="margin-top:0">④ 有界设定（占比 ∈ [0,1]）</h2>
<div class="note">线性 <code>max(0, share−θ)</code> 在份额远超阈值时会无界放大（外推份额 61.7% 已是全局阈值 31% 的两倍）。
改用**天然饱和**的目标：正午窗口内负价小时**占比**。
拟合 <code>logit(占比) = −6.807 + 8.539 × 正午份额</code>（伪 R²=0.559；窗口内负价小时 MAE <b>7.3 h/月</b>，实测均值 7.9）。
阈值-logistic 网格搜索落在 θ=5.0%（即退化为普通 logistic，阈值项无增益）。
⇒ 外推 61.7% 给占比 <b>17.6%</b> ⇒ 61 天窗口内约 65 h ⇒ 负价日率 <b>20.1%</b>。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 秋季 2026 的多口径对照</h2>
{bars(SCEN)}
<div class="note">秋季 2026 外推链：2025 年 10–11 月正午份额 52.7%
→ 按 2026/2025 年 1–9 月的<b>正午光伏 ×1.198</b>、<b>正午负荷 ×1.024</b> 外推 → <b>61.7%</b>
（参照：2026 年 9 月实测 <b>77.6%</b>、2026 年 1–9 月均值 63.5%）。
负价小时→负价日的换算沿用 2025 年秋季实测比 0.19 日/小时。</div>
<div class="warn">区间<b>没有收敛</b>：从 PS-039 的 8.6%–17.1%（约 2 倍）扩到 <b>8.2%–31.6%（约 4 倍）</b>。
差异不来自数据，而来自**设定**：秋季专用阈值只用 2 个非零点（下界，8.2%）；
全样本有界 logistic 用尽 2026 的样本但忽略季节（20.1%）；
全样本线性阈值在被外推到 2 倍阈值处后失效（31.6%）。
<b>PS-039 的 8.6%–17.1% 仍是本链路最可信的区间。</b></div></div>

<div class="box"><h2 style="margin-top:0">⑥ 年度概览与逐月明细</h2>
<div class="scroll"><table>
<tr><th>年</th><th>正午份额均值%</th><th>全天份额均值%</th><th>负价 h</th><th>其中窗口内 h</th></tr>
{rows}
</table></div>
<h3>2024–2026 逐月（份额 / 窗口小时 / 窗口内负价 h / 占比 / 全月负价 h）</h3>
<div class="scroll"><table>
<tr><th>月</th><th>正午份额%</th><th>窗口 h</th><th>窗口内负价 h</th><th>窗口占比%</th><th>全月负价 h</th></tr>
{rows2}
</table></div>
<div class="note">窗口小时数接近常数（168–186 h/月，缺测月更少），故"占比"与"小时数"信息等价。</div></div>

<div class="box"><h2 style="margin-top:0">⑦ 局限</h2>
<ul class="note">
<li><b>秋季外推份额 61.7% 超出秋季历史</b>（秋季最高只有 2025 的 52.7%），外推本身即最大不确定源。</li>
<li>正午份额是**窗口内**的比，未区分"光伏更多"与"负荷更低"；同样份额下两者的正午过剩形状不同。</li>
<li>未引入装机（GEM 按年）、未引入邻国净出口（西班牙负价与法国/葡萄牙耦合强）。</li>
<li>0.19 日/小时的换算沿用 2025 秋季；2026 的负价在日内更"聚簇"（窗口占比 72% 稳定，但日间重叠度可能变）。</li>
<li>交付口径为**日前价**；实时/平衡市场未纳入。</li>
</ul></div>

<div class="note">数据：ENTSO-E A44 日前价 / A65 负荷（官方）；Energy-Charts <code>public_power?country=es</code> 的
<code>Solar</code> 与 <code>Load</code> 两条序列（自检：与 A65 逐时 <b>r=0.999587</b>、能量比 <b>0.999981</b>、MAE 16.8 MW）。
方法与产物见 <code>PS-040</code>；上游 <code>PS-039</code>（月度份额阈值）、<code>PS-038/037/035</code>（西班牙负价链路）。</div>
</div></body></html>"""
    # Markdown 粗体 → HTML 粗体（正文写作时用了 **…**）
    import re
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("→ %s" % os.path.join(OUT, "index.html"))


if __name__ == "__main__":
    main()
