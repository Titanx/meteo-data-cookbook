"""西班牙负价"爆发阈值"模型报告 (PS-039)
输入: data/spain/{spain_long_panel,spain_negprice_threshold,spain_negprice_threshold_fit}.csv
输出: output/spain_negprice_threshold/index.html
用法: python skills/report-builder/references/build_spain_threshold_report.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_negprice_threshold"
os.makedirs(OUT, exist_ok=True)
BLUE, RED, ORANGE, GREY, GREEN, PURPLE = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4", "#2f8f6b", "#7a5aa8"
YCOL = {2015: "#c9d4de", 2016: "#c9d4de", 2017: "#c9d4de", 2018: "#c9d4de", 2019: "#c9d4de",
        2020: "#b7c4d1", 2021: "#a3b4c4", 2022: "#8fa4b8", 2023: BLUE, 2024: ORANGE,
        2025: RED, 2026: PURPLE}


def svg_scatter(p, th, lin):
    w, ht, pad = 820, 380, (54, 22, 46, 60)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    xmax, ymax = 0.40, 260
    X = lambda v: x0 + (x1 - x0) * v / xmax
    Y = lambda v: y1 - (y1 - y0) * min(v, ymax) / ymax
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in np.linspace(0, ymax, 6):
        o.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        o.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t:.0f}</text>')
    for t in np.arange(0, xmax + 1e-9, 0.05):
        o.append(f'<line x1="{X(t):.0f}" x2="{X(t):.0f}" y1="{y0}" y2="{y1}" stroke="#f6f9fc"/>')
        o.append(f'<text x="{X(t):.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">{t*100:.0f}%</text>')
    o.append(f'<text x="{(x0+x1)/2:.0f}" y="{y0+22}" text-anchor="middle" fill="{GREY}">光伏发电 / 需求（月度，%）</text>')
    o.append(f'<text x="{x0-40}" y="{(y0+y1)/2:.0f}" fill="{GREY}" transform="rotate(-90 {x0-40} {(y0+y1)/2:.0f})" text-anchor="middle">月负价小时</text>')
    for r in p.itertuples():
        o.append(f'<circle cx="{X(r.solar_share):.1f}" cy="{Y(r.neg_h):.1f}" r="4" fill="{YCOL.get(int(r.year), GREY)}" opacity="0.85"/>')
    xs = np.linspace(0, xmax, 80)
    o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.6"/>'
             % (" ".join("%.1f,%.1f" % (X(v), Y(max(0.0, th["a"] + th["b"] * max(0.0, v - th["theta"])))) for v in xs), RED))
    o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="6,3"/>'
             % (" ".join("%.1f,%.1f" % (X(v), Y(max(0.0, th["a"] + th["b"] * max(0.0, v - th["theta"])))) for v in xs), RED))
    o.append(f'<line x1="{X(th["theta"]):.0f}" x2="{X(th["theta"]):.0f}" y1="{y0}" y2="{y1}" stroke="{RED}" stroke-width="1.2" stroke-dasharray="3,3"/>')
    o.append(f'<text x="{X(th["theta"])+6:.0f}" y="{y0+14}" fill="{RED}" font-weight="700">阈值 θ = {th["theta"]*100:.1f}%</text>')
    # 图例
    for j, (y, col) in enumerate([(2026, PURPLE), (2025, RED), (2024, ORANGE), (2023, BLUE), (2015, "#c9d4de")]):
        o.append(f'<circle cx="{x0+16+j*78}" cy="{ht-14}" r="4.5" fill="{col}"/>'
                 f'<text x="{x0+24+j*78}" y="{ht-10}" fill="#5b7488">{y}</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    p = pd.read_csv(os.path.join(D, "spain_negprice_threshold.csv"))
    fit = pd.read_csv(os.path.join(D, "spain_negprice_threshold_fit.csv"))
    th = {"theta": 0.160, "a": 2.1, "b": 378.6}

    # 逐年 春季/秋季 汇总
    def season(mm):
        s = p[p.month.isin(mm)].groupby("year").agg(份额=("solar_share", "mean"), h=("neg_h", "mean"))
        return s
    sp, au = season([4, 5]), season([10, 11])

    # 表: 逐月份额与负价
    piv_s = p.pivot_table(index="month", columns="year", values="solar_share") * 100
    piv_n = p.pivot_table(index="month", columns="year", values="neg_h")
    years = [2015, 2017, 2019, 2021, 2022, 2023, 2024, 2025, 2026]
    mrows = ""
    for m in range(1, 13):
        cells = ""
        for y in years:
            if m in piv_s.index and y in piv_s.columns and pd.notna(piv_s.loc[m, y]):
                share = piv_s.loc[m, y]
                nh = piv_n.loc[m, y]
                col = RED if nh > 0 else "#22303c"
                cells += f'<td style="color:{col}">{share:.0f}<span style="color:#b9c6d2">/{nh:.0f}</span></td>'
            else:
                cells += "<td>–</td>"
        mrows += f"<tr><td>{m}月</td>{cells}</tr>"

    fitr = ""
    for r in fit.itertuples():
        fitr += ("<tr><td>≤%d</td><td>%d</td><td>%.3f</td><td>%.1f</td><td>%+.1f</td>"
                 "<td>%.1f</td><td>%+.1f</td></tr>"
                 % (r.train_to, r.n_test, r.theta_train, r.mae_threshold, r.bias_threshold,
                    r.mae_trend, r.bias_trend))

    SCEN = [("PS-037（官方口径复核）", 6.8, GREY), ("2025 年秋季实测", 6.5, GREY),
            ("PS-035（原式）", 8.2, GREY), ("PS-039 秋季阈值", 8.6, GREEN),
            ("PS-038 C 同年比例", 11.3, BLUE), ("PS-039 全局阈值", 17.1, GREEN),
            ("PS-038 B 秋季残差", 21.4, ORANGE), ("PS-038 A 趋势外推", 62.0, RED)]
    bars = ""
    vmax = 66.0
    for lab, v, col in SCEN:
        ww = v / vmax * 100
        bars += ('<div style="display:flex;align-items:center;margin:5px 0;font-size:12.5px">'
                 '<div style="width:190px;color:#3c556b">%s</div>'
                 '<div style="flex:1;background:#eef3f7;border-radius:3px;height:16px">'
                 '<div style="width:%.1f%%;height:16px;background:%s;border-radius:3px"></div></div>'
                 '<div style="width:58px;text-align:right;font-weight:700;color:%s">%.1f%%</div></div>'
                 % (lab, ww, col, col, v))
    a25 = p[(p.year == 2025) & p.month.isin([10, 11])]
    a24 = p[(p.year == 2024) & p.month.isin([10, 11])]

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙负价"爆发阈值"模型（12 年历史）</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.62}}
.wrap{{max-width:1060px;margin:0 auto;padding:28px 20px}}
h1{{font-size:23px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:14px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:6px 8px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
td:first-child,th:first-child{{text-align:left}}
.neg{{color:#c23a3a;font-weight:600}}.pos{{color:#1f5bb8;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}
.hl{{background:#eef6ef;border-left:3px solid #2f8f6b;padding:12px 16px;border-radius:6px;margin:14px 0}}
.warn{{background:#fff6ea;border-left:3px solid #e5853a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}li{{margin:5px 0}}
</style></head><body><div class="wrap">
<h1>西班牙负价"爆发阈值"模型（12 年历史）</h1>
<div class="sub">PS-038 用 3 年线性趋势外推会给出 62% 的秋季概率、三情景相差 5 倍。本流程改以
<b>光伏发电 / 需求</b>为驱动、用 <b>2015–2026 共 141 个月</b>的面板检验"阈值/爆发"设定 · 核查日 2026-09-29</div>

<div class="hl"><b>结论一：负价不是"随时间爬升"，而是"越过光伏份额阈值后爆发"。</b>
2015–2023 连续 9 年负价小时恒为 0，而同期光伏份额从 5% 单调升到 2023 年的 17.6%；阈值拟合给出
<b>θ = 16.0%</b>（月度光伏发电 ÷ 月度需求），超阈值后斜率 <b>379 h/单位份额</b>。
同一样本下，阈值模型 <b>MAE 11.0 h/月 / R² 0.339</b>，明显优于线性趋势的 <b>17.5 h/月 / R² 0.214</b>。</div>

<div class="warn"><b>结论二：阈值是随季节变的，秋季门槛低得多。</b>
春季 4–5 月的份额从 2023 年 24.8%（0 h）跳到 2024 年 27.4%（<b>71 h/月</b>）——春季阈值约 <b>25–26%</b>；
而秋季 10–11 月在 <b>13.8%</b>（2024，2.5 h）就已开始出现负价，2025 年 <b>19.3%</b> 给出 10.5 h/月。
秋季专用拟合（n=22，R²=0.875）给出 θ = 10.5%。⇒ <b>用"全年单一阈值"判断秋季会高估</b>。</div>

<div class="hl"><b>结论三：12 年阈值把 5 倍的情景分歧收窄到约 9%–17%，并否掉了 62% 的趋势外推。</b>
按 2026 年 1–9 月的实际增长外推，<b>2026 年 10–11 月光伏份额 ≈ 22.7%</b>（2025 年 19.3% × 光伏 +21.1% ÷ 负荷 +2.9%）。
代入三种口径：秋季阈值 <b>8.6%</b>、同年比例 11.3%、全局阈值/月份FE <b>17.1%</b>。
⇒ <b>PS-035 的 8.2% 与 PS-037 的 6.8% 从"低于区间"变成了区间下沿的正常值</b>，
而 PS-038 情景 A 的 62% 应视为过冲上界。</div>

<div class="box"><h2 style="margin-top:0">① 12 年面板：光伏份额 vs 月负价小时</h2>
{svg_scatter(p, th, None)}
<div class="note">横轴 = 月度光伏发电 ÷ 月度需求；纵轴 = 当月负价小时。灰点 = 2015–2022（全部为 0），
蓝/橙/红/紫 = 2023/2024/2025/2026。红实线 = 阈值模型（θ=16.0%），虚线为同一模型的左侧平段。
可以看出两点：<b>① 份额低于 ~16% 时负价几乎恒为 0</b>；<b>② 超过阈值后增长极陡</b>（2025 年 5 月 29% 份额对应 239 h）。</div>
<div class="scroll"><table>
<tr><th>月</th>{"".join("<th>%d</th>" % y for y in years)}</tr>
{mrows}
</table></div>
<div class="note">表内为 <b>光伏份额% / 负价小时</b>（红色表示该月有负价）。面板为 <b>2015-01 ~ 2026-09 共 141 个月、零缺口</b>
（负荷已于 2026-09-29 回填完成），补齐前后阈值 θ 不变。</div></div>

<div class="box"><h2 style="margin-top:0">② 季节性阈值：春季 vs 秋季</h2>
<div class="scroll"><table>
<tr><th>年</th><th>春季份额%</th><th>春季负价 h/月</th><th>秋季份额%</th><th>秋季负价 h/月</th></tr>
{"".join("<tr><td>%d</td><td>%.1f</td><td%s>%.1f</td><td>%.1f</td><td%s>%.1f</td></tr>" % (
    y, sp.loc[y, "份额"] * 100, ' class="neg"' if sp.loc[y, "h"] > 0 else "", sp.loc[y, "h"],
    au.loc[y, "份额"] * 100 if y in au.index else float("nan"),
    ' class="neg"' if (y in au.index and au.loc[y, "h"] > 0) else "",
    au.loc[y, "h"] if y in au.index else float("nan")) for y in sorted(sp.index) if y >= 2020)}
</table></div>
<div class="note">春季在 <b>24.8% → 27.4%</b> 之间从"0 h"跳到"71 h/月"（2024），阈值约 25–26%；
秋季在 <b>13.8%</b> 就出现负价（2024）、19.3% 给出 10.5 h/月。差异来自正午供需结构：
秋季负荷更低、光照角度更低，同样的月度份额对应更强的正午过剩。
⇒ <b>做秋季展望必须用秋季阈值</b>，这也解释了为什么用全年拟合会高估秋季。</div></div>

<div class="box"><h2 style="margin-top:0">③ 设定对比与样本外</h2>
<div class="scroll"><table>
<tr><th>设定</th><th>参数数</th><th>R²</th><th>全样本 MAE (h/月)</th></tr>
<tr><td>线性趋势（PS-038 口径）</td><td>2</td><td>0.214</td><td>17.5</td></tr>
<tr><td><b>阈值（hockey-stick, θ=16.0%）</b></td><td>3</td><td><b>0.339</b></td><td><b>11.0</b></td></tr>
<tr><td>阈值 + 月份固定效应</td><td>13</td><td><b>0.415</b></td><td>13.3</td></tr>
<tr><td>秋季专用阈值（10–11 月, n=22）</td><td>3</td><td><b>0.875</b></td><td>—</td></tr>
</table></div>
<h3 style="font-size:14px;margin:16px 0 6px;color:#3c556b">逐年扩展窗口 → 预测后续年份逐月负价小时</h3>
<div class="scroll"><table>
<tr><th>训练至</th><th>测试月数</th><th>θ(训练)</th><th>阈值 MAE</th><th>阈值偏差</th><th>趋势 MAE</th><th>趋势偏差</th></tr>
{fitr}
</table></div>
<div class="note">样本外两类模型都<b>系统性低估</b>——因为份额本身在快速上升，任何用历史水平拟合的模型都会落后。
但阈值模型始终优于线性趋势（MAE 44.9 vs 56.2；55.6 vs 62.1），且偏差小得多（−29.2 vs −60.6）。
⚠ <b>"训练至 2023" 这一行是退化的</b>：2023 及以前负价全为 0，模型只能预测 0，故与趋势模型完全同值。</div></div>

<div class="box"><h2 style="margin-top:0">④ 情景收敛：秋季 2026 的负价日率</h2>
{bars}
<div class="note">秋季 2026 外推链：2025 年 10–11 月光伏 7.4 TWh / 负荷 38.5 TWh（份额 19.3%）
→ 按 2026/2025 年 1–9 月的<b>光伏 +21.1%</b>、<b>负荷 +2.9%</b> 外推 → <b>份额 22.7%</b>
→ 代入各口径的阈值模型 → 换算负价日率（用 2025 年秋季实测的"负价日/负价小时"比 0.19）。</div>
<div class="note"><b>收敛结果</b>：12 年阈值分析把区间从 <b>6.8%–62.0%（9 倍）</b> 压缩到
<b>8.6%–17.1%（约 2 倍）</b>，中心在 <b>9%–11%</b>。PS-035（8.2%）与 PS-037（6.8%）
落在区间下沿且不再离群；PS-038 情景 A（62%）被明确否掉。
⚠ 秋季专用阈值只有 2 个非零点（2024/2025）支撑，其 8.6% 应视为下界而非点估计；
上调到全局阈值口径则为 17.1%。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 局限与下一步</h2>
<ul class="note">
<li><b>结构性限制无法绕过</b>：12 年价格里只有 <b>3 年</b>有负价（2015–2023 恒为 0），
所以"阈值以上的响应"仍只由 2024–2026 三年确定。扩样本买到的是<b>阈值位置</b>（9 年的零值把它钉得很死），
不是阈值以上的斜率。</li>
<li><b>份额是月度聚合</b>，掩盖了正午结构与日内变化。下一步应改用<b>正午时段（10–16h 当地）的光伏/负荷比</b>，
这会让春季与秋季的阈值差异有更清晰的结构解释。</li>
<li><b>负荷口径</b>：官方负荷已于 2026-09-29 完成回填，面板 <b>2015-01~2026-09 共 141 个月零缺口</b>
（补齐最后缺失的 2018-07~12）；补齐前后阈值 θ 均为 16.0%，情景结论不变。</li>
<li><b>能量数据链</b>：光伏取自 Energy-Charts（PS-037 已证其 ≡ ENTSO-E，2015 年也逐位一致）；
⚠ 该端点的 <code>start/end</code> 按当地时间解释，跨年请求会带回上一年最后 1 小时，
按月聚合时必须<b>累加而非覆盖</b>（本流程踩过：2015-12 由 0.44 TWh 被冲成 2e-05 TWh）。</li>
<li><b>下一步</b>：① 把份额升级为"正午份额"；② 引入装机（GEM 按年）以分离"装机增长"与"资源年景"；
③ 把阈值模型接到 45 天季节预报上，做逐日版本（替代 PS-035 的 S 指数）。</li>
</ul></div>

<div class="note" style="margin-top:6px">数据：ENTSO-E A44 日前价 / A65 负荷（官方，2015-01 起）、Energy-Charts 分技术发电（2015–2026）。
方法与产物见 <code>PS-039</code>；上游为 <code>PS-038</code>（趋势/logit/强度模型）与 <code>PS-035/037</code>（西班牙负价链路与官方口径复核）。</div>
</div></body></html>"""
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("→ %s" % os.path.join(OUT, "index.html"))


if __name__ == "__main__":
    main()
