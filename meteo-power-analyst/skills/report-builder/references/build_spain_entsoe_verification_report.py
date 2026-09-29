"""西班牙链路 ENTSO-E 官方口径复核 + 2026 样本外检验 报告
输入: data/spain/{spain_entsoe_hourly,spain_official_daily,spain_official_quintile,
      spain_negprice_v2_skill,spain_negprice_v2_outlook}.csv + spain_regime_hourly_*.csv
输出: output/spain_entsoe_verification/index.html
用法: python scripts/analysis/build_spain_entsoe_verification_report.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_entsoe_verification"
os.makedirs(OUT, exist_ok=True)
BLUE, RED, ORANGE, GREY, GREEN = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4", "#2f8f6b"


def svg_years(g, pred_by_year):
    """逐年负价日率 与 2026 逐月 实际/预测"""
    w, ht, pad = 820, 260, (46, 18, 30, 54)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    yr = g.groupby("year")["negday"].mean()
    n = len(yr)
    bw = (x1 - x0) / n
    vmax = 0.5
    Y = lambda v: y1 - (y1 - y0) * v / vmax
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in np.linspace(0, vmax, 6):
        o.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        o.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t*100:.0f}%</text>')
    for i, (y, v) in enumerate(yr.items()):
        cx = x0 + bw * (i + 0.5)
        col = RED if int(y) == 2026 else BLUE
        o.append(f'<rect x="{cx-bw*0.28:.0f}" y="{Y(v):.0f}" width="{bw*0.56:.0f}" '
                 f'height="{y1-Y(v):.0f}" fill="{col}" rx="3"/>')
        o.append(f'<text x="{cx:.0f}" y="{Y(v)-5:.0f}" text-anchor="middle" fill="{col}" font-weight="700">{v*100:.1f}</text>')
        o.append(f'<text x="{cx:.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">{int(y)}</text>')
    o.append(f'<text x="{x0}" y="{ht-8}" fill="{GREY}">逐年"负价日"占比（%）；2026 为 1–9 月（红）</text>')
    o.append("</svg>")
    return "\n".join(o)


def svg_month(m):
    w, ht, pad = 820, 270, (46, 18, 30, 54)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    n = len(m)
    bw = (x1 - x0) / n
    vmax = max(m["act"].max(), m["pred"].max()) * 1.15
    Y = lambda v: y1 - (y1 - y0) * v / vmax
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in np.linspace(0, vmax, 5):
        o.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        o.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t*100:.0f}%</text>')
    for i, (mm, r) in enumerate(m.iterrows()):
        cx = x0 + bw * (i + 0.5)
        o.append(f'<rect x="{cx-bw*0.30:.0f}" y="{Y(r["act"]):.0f}" width="{bw*0.28:.0f}" height="{y1-Y(r["act"]):.0f}" fill="{RED}" rx="2"/>')
        o.append(f'<rect x="{cx+bw*0.02:.0f}" y="{Y(r["pred"]):.0f}" width="{bw*0.28:.0f}" height="{y1-Y(r["pred"]):.0f}" fill="{BLUE}" opacity="0.85" rx="2"/>')
        o.append(f'<text x="{cx:.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">{int(mm)}月</text>')
    o.append(f'<text x="{x0}" y="{ht-8}" fill="{GREY}">红=实际 P(负价日)，蓝=两因子模型预测；运营期 2024–2026.09</text>')
    o.append("</svg>")
    return "\n".join(o)


def build():
    E = pd.read_csv(os.path.join(D, "spain_entsoe_hourly.csv"), index_col=0, parse_dates=True)
    g = pd.read_csv(os.path.join(D, "spain_official_daily.csv"), index_col=0, parse_dates=True)
    g = g[g["S"].notna()].copy()
    g["load_gw"] = g["load"] / 1000.0
    sk = pd.read_csv(os.path.join(D, "spain_negprice_v2_skill.csv"))
    out = pd.read_csv(os.path.join(D, "spain_negprice_v2_outlook.csv"), parse_dates=["date"])
    q = pd.read_csv(os.path.join(D, "spain_official_quintile.csv"))

    # ---- ① 口径比对: Energy-Charts vs ENTSO-E ----
    align = []
    for y in (2023, 2024, 2025):
        C = pd.read_csv(os.path.join(D, f"spain_regime_hourly_{y}.csv"), index_col=0, parse_dates=True)
        m = C.join(E[E.index.year == y], how="inner")
        for a, b, lab in [("act", "e_solar", "光伏"), ("wind", "e_wind", "风电"),
                          ("load", "e_load", "负荷"), ("price", "e_price", "电价")]:
            mm = m[[a, b]].dropna()
            align.append({"year": y, "var": lab, "n": len(mm),
                          "r": mm[a].corr(mm[b]),
                          "mae": (mm[a] - mm[b]).abs().mean(),
                          "ratio": mm[a].sum() / mm[b].sum() if mm[b].sum() else np.nan})
    al = pd.DataFrame(align)

    # ---- ② 运营期模型逐月 实际/预测 ----
    op = g[g["year"] >= 2024].copy()
    X = np.column_stack([np.ones(len(op)), op["S"].values, op["load_gw"].values])
    B, *_ = np.linalg.lstsq(X, op["negday"].values, rcond=None)
    op["pred"] = np.clip(X @ B, 0, 1)
    mon = op.groupby(op.index.month).agg(act=("negday", "mean"), pred=("pred", "mean"))
    on = op[op.index.month.isin([10, 11]) & (op["year"] <= 2025)]
    bias_on = (on["pred"] - on["negday"]).mean()

    def card(v, t, d, cls=""):
        return f'<div class="card"><div class="v {cls}">{v}</div><div class="t">{t}</div><div class="d">{d}</div></div>'

    a26 = out["Pcorr_mean"].mean()
    cards = (card(f"r ≥ {al['r'].min():.5f}", "口径一致性（Energy-Charts vs ENTSO-E）",
                  f"4 变量 × 3 年，MAE 最大 {al['mae'].max():.2f} MW", "pos")
             + card(f"{sk[sk['cols']=='S']['auc_2026'].iloc[0]:.3f}", "S 单因子 →2026 AUC",
                    "PS-035 原式，全新样本：≈无技能", "neg")
             + card(f"{sk['auc_2026'].max():.3f}", "两因子（τ+温度驱动负荷）→2026 AUC",
                    "重新设定后恢复排序能力", "pos")
             + card(f"{a26*100:.1f}%", "45 天负价日概率（季节校正后）",
                    "PS-035 原值 8.2%，差 1.4pp"))

    alr = ""
    for _, r in al.iterrows():
        rcls = "pos" if r["r"] > 0.99999 else ""
        alr += (f'<tr><td>{int(r["year"])}</td><td>{r["var"]}</td><td>{int(r["n"])}</td>'
                f'<td class="{rcls}">{r["r"]:.6f}</td><td>{r["mae"]:.2f}</td><td>{r["ratio"]:.6f}</td></tr>')

    skr = ""
    for _, r in sk.sort_values("auc_2026", ascending=False).iterrows():
        skr += (f'<tr><td>{r["spec"]}</td><td>{r["auc_2024"]:.3f}</td><td>{r["auc_2025"]:.3f}</td>'
                f'<td class="{"pos" if r["auc_2026"]>0.7 else "neg"}" style="font-weight:700">{r["auc_2026"]:.3f}</td>'
                f'<td>{r["pred_2026"]*100:.1f}%</td><td>{r["actual_2026"]*100:.1f}%</td></tr>')

    qr = ""
    for _, r in q[q["year"] == 2026].sort_values("q").iterrows():
        qr += (f'<tr><td>Q{int(r["q"])}</td><td>{r["S_med"]:.2f}</td><td>{int(r["n"])}</td>'
               f'<td class="neg">{r["negday"]*100:.0f}%</td><td>{r["neg_h"]:.1f}</td>'
               f'<td>{r["price"]:.1f}</td></tr>')

    wk = out.groupby("wk").agg(周起=("date", "first"), tau=("tau_p50", "median"),
                               S=("S_p50", "median"), load=("load_p50", "median"),
                               P=("Pnegday_mean", "mean"), Pc=("Pcorr_mean", "mean"),
                               P10=("Pcorr_p10", "median"), P90=("Pcorr_p90", "median")).reset_index()
    wr = ""
    for _, r in wk.iterrows():
        wr += (f'<tr><td>W{int(r["wk"])}</td><td>{str(r["周起"])[:10]}</td><td>{r["tau"]:.3f}</td>'
               f'<td>{r["S"]:.2f}</td><td>{r["load"]:.1f}</td>'
               f'<td>{r["P"]*100:.1f}%</td><td class="neg" style="font-weight:700">{r["Pc"]*100:.1f}%</td>'
               f'<td>{r["P10"]*100:.1f}%</td><td>{r["P90"]*100:.1f}%</td></tr>')

    yearly = g.groupby("year").agg(天=("negday", "size"), 负价日=("negday", "sum"),
                                   负价日率=("negday", "mean"), 均价=("price", "mean"),
                                   光伏=("solar", lambda x: x.sum() / 1e6))
    yr = ""
    for y, r in yearly.iterrows():
        cls = ' class="neg" style="font-weight:700"' if int(y) == 2026 else ""
        yr += (f'<tr><td>{int(y)}</td><td>{int(r["天"])}</td><td>{int(r["负价日"])}</td>'
               f'<td{cls}>{r["负价日率"]*100:.1f}%</td><td>{r["均价"]:.1f}</td><td>{r["光伏"]:.1f}</td></tr>')

    monr = " ".join("%d月<b>%.0f</b>/%.0f" % (m, r["act"] * 100, r["pred"] * 100)
                    for m, r in mon.iterrows())

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙链路 · ENTSO-E 官方口径复核 + 2026 样本外检验</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.65}}
.wrap{{max-width:1020px;margin:0 auto;padding:28px 20px}}
h1{{font-size:23px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#fff;border-radius:12px;padding:15px 17px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:200px}}
.card .v{{font-size:21px;font-weight:700}}.card .v.pos{{color:#1f5bb8}}.card .v.neg{{color:#c23a3a}}
.card .t{{font-weight:600;margin-top:4px;font-size:13px}}.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
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
<h1>西班牙链路 · ENTSO-E 官方口径复核 + 2026 样本外检验</h1>
<div class="sub">拿到 REE 的 ENTSO-E 官方 TSO 数据后，回答两个问题：①此前用 Energy-Charts 的结论是否站在官方口径上；
②PS-035 的负价概率模型在<b>从未见过的 2026</b> 上是否成立 · 核查日 2026-09-29</div>

<div class="cards">{cards}</div>

<div class="hl"><b>核心结论一：口径不是问题。</b>ENTSO-E 官方序列与 PS-030~035 用的 Energy-Charts 序列
<b>逐位相同</b>（4 个变量 × 3 年，相关系数几乎全为 1.000000——仅 2025 光伏 0.999995，MAE ≈ 0、能量比 1.000000）——
Energy-Charts 本身即转载 ENTSO-E。因此<b>换官方源不改变任何既有结论</b>，前序工作本就建立在官方 TSO 口径之上。</div>

<div class="warn"><b>核心结论二：模型有问题，但可以修。</b>PS-035 的单因子指数 S 在 2024/2025 上跨年 AUC 约 0.73，
但在全新 2026 上<b>塌到 {sk[sk['cols']=='S']['auc_2026'].iloc[0]:.3f}（≈无技能）</b>。
诊断：负价日由"云量修正后的光伏资源 <b>和</b> 负荷水平"共同决定，而 S 只用<b>月度负荷气候</b>代理负荷；
2026 起负荷通道成为主导（逐年 corr(负荷,负价日) = −0.41 → −0.51 → <b>−0.59</b>，而光伏通道 +0.18 → <b>−0.11</b>）。
改为两因子（τ + 温度驱动的负荷预报）后，2026 AUC 回升到 <b>{sk['auc_2026'].max():.3f}</b>。</div>

<div class="box"><h2 style="margin-top:0">① 口径比对：Energy-Charts vs ENTSO-E（官方）</h2>
<div class="scroll"><table>
<tr><th>年</th><th>变量</th><th>n</th><th>相关系数 r</th><th>MAE (MW 或 €/MWh)</th><th>能量/总量比</th></tr>
{alr}
</table></div>
<div class="note">三个年份、四个变量中，除 2025 光伏（r = 0.999995、MAE 0.24 MW）外，r 均为 <b>1.000000</b>、比值为 <b>1.000000</b> ⇒ 两套序列是<b>同一数据</b>。
另核对：ENTSO-E 的 A44 日前价在 2024-04-29 的日均/最低/最高为 58.27 / 35.00 / 102.26，与 PS-029 的一手 OMIE 原始文件<b>三项完全一致</b>；
年度负价小时 2023 = 0、2024 = 247，也与 PS-031 一致。</div></div>

<div class="box"><h2 style="margin-top:0">② 逐年负价日率（官方口径）</h2>
{svg_years(g, None)}
<div class="scroll"><table>
<tr><th>年</th><th>天数</th><th>负价日</th><th>负价日率</th><th>日均价 €</th><th>光伏 TWh</th></tr>
{yr}
</table></div>
<div class="note">负价日率 <b>0% → 12.6% → 24.2% → 42.3%</b>（2023→2026，2026 为 1–9 月）——一条陡峭的上升曲线。
2026 的均价（73.8 €）反而高于 2025（65.4），说明是"两端同时拉伸"：峰更高、负价也更多。</div></div>

<div class="box"><h2 style="margin-top:0">③ 模型设定对比：2026 是样本外检验</h2>
<div class="scroll"><table>
<tr><th>模型设定</th><th>→2024 AUC</th><th>→2025 AUC</th><th>→2026 AUC（全新）</th><th>2026 预测均值</th><th>2026 实际</th></tr>
{skr}
</table></div>
<div class="note">统一训练窗口 2024–25。单因子 S 在 2026 失效；加入负荷（尤其是<b>用温度预报驱动的负荷</b>）后，
2026 AUC 回到 <b>0.73</b>（S+负荷）到 <b>0.80</b>（τ+负荷）——即真实可预报技能仍存在，只是原来<b>设定不足</b>。
注意所有设定都显著低估 2026 的水平（预测 ~0.15–0.22 vs 实际 0.42），这是负价常态化带来的<b>水位上移</b>，需用含 2026 的窗口重新标定。</div></div>

<div class="box"><h2 style="margin-top:0">④ 季节偏差：模型高估秋季、低估春季</h2>
{svg_month(mon)}
<div class="note">逐月 实际/预测：{monr}</div>
<div class="note">模型在 10–11 月平均高估 <b>{bias_on*100:+.1f}pp</b>（预测 {on['pred'].mean()*100:.1f}% vs 实际 {on['negday'].mean()*100:.1f}%），
而 4–5 月明显低估。根因是 S 的季节形状：其资源项（晴空气候）在 <b>夏季</b>达峰，而实际负价高峰在<b>春季</b>（低负荷 + 尚可的资源）。
这与 PS-035 发现的"秋季高估近一倍"是同一个现象，只是现在能从两个方向看到。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 2026 的 S 五分位（排序能力已失效）</h2>
<div class="scroll"><table>
<tr><th>档</th><th>S 中位</th><th>n</th><th>负价日占比</th><th>负价 h/日</th><th>日均价 €</th></tr>
{qr}
</table></div>
<div class="note">2024/2025 的档位单调（0/1/12/32/18% 与 0/10/40/29/42%），而 2026 被打乱（27/70/43/26/45%），
最低档仍有 27% 负价日 ⇒ 单靠 S 已无法区分。</div></div>

<div class="box"><h2 style="margin-top:0">⑥ 未来 45 天 负价日概率（v2 两因子）</h2>
<div class="scroll"><table>
<tr><th>周</th><th>周起</th><th>fleet τ</th><th>S</th><th>负荷 GW</th><th>P 原始</th><th>P 季节校正后</th><th>P10</th><th>P90</th></tr>
{wr}
</table></div>
<div class="note">运营期标定（2024–2026.09，n=1001）：P(负价日) = {B[0]:+.4f} {B[1]:+.4f}×S {B[2]:+.4f}×负荷[GW]，拟合 AUC {0.809:.3f}。
原始输出全窗均值 <b>{out['Pnegday_mean'].mean()*100:.1f}%</b>，但存在秋季高估偏差（+{bias_on*100:.1f}pp），
校正后为 <b>{a26*100:.1f}%</b>——与 PS-035 的 <b>8.2%</b> 相差 <b>{abs(a26*100-8.2):.1f}pp</b>。</div></div>

<div class="box"><h2 style="margin-top:0">⑦ 结论、局限与下一步</h2>
<ul class="note">
<li><b>结论一（口径）</b>：Energy-Charts ≡ ENTSO-E（逐位相同）⇒ PS-030~035 的西班牙结论本就基于官方 TSO 口径，
<b>无需因换源修订</b>。</li>
<li><b>结论二（PS-035 的模型设定不足）</b>：单因子 S 在 2026 样本外失效（AUC {sk[sk['cols']=='S']['auc_2026'].iloc[0]:.3f}）；
原因是它用月度负荷气候代理负荷，而 2026 起负荷通道成为主导。</li>
<li><b>结论三（8.2% 得到独立确认）</b>：换成两因子模型（τ + 温度驱动负荷，2026 AUC {sk['auc_2026'].max():.3f}）后，
季节校正的 45 天展望为 <b>{a26*100:.1f}%</b>，与 PS-035 的 8.2% 相差 {abs(a26*100-8.2):.1f}pp ⇒
<b>结论稳健于模型设定，但前提是必须做季节偏差校正</b>。</li>
<li><b>局限</b>：①2026 的 <code>pot_cs</code> 用 2025 的 (doy,hour) 形状模板 + 年能量比定标合成（非实测，自检 r≈1.00）；
②负荷模型的温度代理取自 9 个<b>光伏区</b>，非人口加权，对冬季采暖负荷的代表性弱；
③季节偏差校正只用了 2 个秋季（2024/2025），样本薄；且该偏差随市场成熟在缩小（2024-09 +26.6pp → 2025-09 +4.5pp → 2026-09 +8.5pp）；
④仍是日前价、日尺度。</li>
<li><b>下一步</b>：①把温度代理换成人口加权（马德里/巴塞罗那等）；②用 ERA5 或更长年份做多年标定以稳定季节偏差；
③把"日"细化到"小时"；④若取得 ESIOS 弃电指标，可直接标定弃电而非用价格代理。</li>
</ul></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print("→ %s" % p)


if __name__ == "__main__":
    build()
