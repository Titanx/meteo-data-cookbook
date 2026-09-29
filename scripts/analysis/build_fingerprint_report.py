"""缺口工况指纹报告
输入: data/ercot/shortfall_fingerprint_summary.csv
输出: output/shortfall_fingerprint/index.html
用法: python scripts/analysis/build_fingerprint_report.py
"""
import os

import pandas as pd

D = r"c:\work\meteo\data\ercot"
OUT = r"c:\work\meteo\output\shortfall_fingerprint"
os.makedirs(OUT, exist_ok=True)
EXO, ENDO, GREY = "#e5853a", "#1f5bb8", "#8aa0b4"
NM = {"外生": "外生缺口", "内生": "内生缺口"}
TECH = {"PV": "光伏", "Wind": "风电"}


def bars_ercot(g):
    w, ht, pad = 840, 330, (54, 18, 40, 56)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    cells = list(g.index)
    n = len(cells)
    bw = (x1 - x0) / n
    vmax = max(g["lo_neg"].max(), g["hi_neg"].max(), 1.0) * 1.25
    Y = lambda v: y1 - (y1 - y0) * v / vmax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in (0, vmax / 2, vmax):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        out.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t:.0f}%</text>')
    for i, c in enumerate(cells):
        cx = x0 + bw * (i + 0.5)
        for j, (col, lbl) in enumerate((("lo_neg", "最低两档"), ("hi_neg", "最高两档"))):
            v = g.loc[c, col]
            bx = cx + (j - 0.5) * bw * 0.3
            out.append(f'<rect x="{bx-bw*0.13:.0f}" y="{Y(v):.0f}" width="{bw*0.26:.0f}" height="{y1-Y(v):.0f}" '
                       f'fill="{ENDO if j==1 else GREY}" opacity="{1 if j==1 else 0.55}"/>')
            out.append(f'<text x="{bx:.0f}" y="{Y(v)-4:.0f}" text-anchor="middle" fill="#44586b">{v:.1f}</text>')
        out.append(f'<text x="{cx:.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">{c}</text>')
    out.append(f'<text x="{x0}" y="{ht-10}" fill="{GREY}">深蓝=最高两档缺口小时, 浅灰=最低两档; 数值为负电价频率(%)</text>')
    out.append("</svg>")
    return "\n".join(out)


def bars_spain(g):
    w, ht, pad = 840, 320, (54, 18, 40, 56)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    years = list(g.index)
    n = len(years)
    bw = (x1 - x0) / n
    vmax = max(g["exo"].max(), g["endo"].max(), 1.0) * 1.25
    Y = lambda v: y1 - (y1 - y0) * v / vmax
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" font-family="Segoe UI,Arial" font-size="11">']
    for t in (0, vmax / 2, vmax):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.0f}" y2="{Y(t):.0f}" stroke="#eef3f7"/>')
        out.append(f'<text x="{x0-6}" y="{Y(t)+3:.0f}" text-anchor="end" fill="{GREY}">{t:.0f}%</text>')
    for i, yr in enumerate(years):
        cx = x0 + bw * (i + 0.5)
        for j, (col, colr) in enumerate((("exo", EXO), ("endo", ENDO))):
            v = g.loc[yr, col]
            bx = cx + (j - 0.5) * bw * 0.34
            out.append(f'<rect x="{bx-bw*0.15:.0f}" y="{Y(v):.0f}" width="{bw*0.3:.0f}" height="{y1-Y(v):.0f}" fill="{colr}"/>')
            out.append(f'<text x="{bx:.0f}" y="{Y(v)-4:.0f}" text-anchor="middle" fill="{colr}">{v:.1f}</text>')
        out.append(f'<text x="{cx:.0f}" y="{y0-8}" text-anchor="middle" fill="#5b7488">{yr}</text>')
    out.append(f'<text x="{x0+10}" y="{y0-8}" fill="{EXO}">■ 外生缺口(高档)</text>')
    out.append(f'<text x="{x0+200}" y="{y0-8}" fill="{ENDO}">■ 内生缺口(高档)</text>')
    out.append(f'<text x="{x0}" y="{ht-10}" fill="{GREY}">西班牙光伏: 最高两档缺口小时的负电价频率(%)</text>')
    out.append("</svg>")
    return "\n".join(out)


def build():
    s = pd.read_csv(os.path.join(D, "shortfall_fingerprint_summary.csv"))
    e = s[s["market"] == "ERCOT"].copy()
    e["k"] = e["tech"].map(TECH) + "·" + e["cause"].map(NM)
    eg = e.groupby("k").agg(lo_neg=("lo_neg_freq", "mean"), hi_neg=("hi_neg_freq", "mean"),
                            lo_low=("lo_low_freq", "mean"), hi_low=("hi_low_freq", "mean"),
                            lo_p=("lo_price_med", "mean"), hi_p=("hi_price_med", "mean"),
                            lo_d=("lo_dem_med", "mean"), hi_d=("hi_dem_med", "mean"),
                            corr=("corr_gap_price", "mean")).loc[
        ["光伏·外生缺口", "光伏·内生缺口", "风电·外生缺口", "风电·内生缺口"]]

    sp = s[s["market"] == "西班牙"]
    sg = sp.pivot_table(index="year", columns="cause", values="hi_neg_freq") \
        .rename(columns={"外生": "exo", "内生": "endo"})

    def card(v, t, d, cls=""):
        return f'<div class="card"><div class="v {cls}">{v}</div><div class="t">{t}</div><div class="d">{d}</div></div>'

    pv_in = eg.loc["光伏·内生缺口"]
    wd_ex = eg.loc["风电·外生缺口"]
    cards = (card(f"{pv_in['lo_neg']:.1f}% → {pv_in['hi_neg']:.1f}%", "ERCOT 光伏·内生缺口",
                  "最低→最高档的负价频率", "neg")
             + card(f"{wd_ex['lo_neg']:.1f}% → {wd_ex['hi_neg']:.1f}%", "ERCOT 风电·外生缺口(低风)",
                    "负价频率不升反降 ⇒ 真稀缺", "pos")
             + card(f"{sg.loc[2023,'endo']:.0f}% → {sg.loc[2025,'endo']:.0f}%", "西班牙 光伏·内生缺口",
                    "高缺口档负价频率 (2023→2025)", "neg")
             + card(f"{pv_in['lo_d']/1000:.1f} → {pv_in['hi_d']/1000:.1f} GW", "ERCOT 光伏·内生缺口",
                    "低→高缺口档的需求中位", "neg"))

    rows = ""
    for c, r in eg.iterrows():
        cls = "neg" if r["hi_low"] > r["lo_low"] else "pos"
        rows += (f'<tr><td>{c}</td><td>{r["lo_low"]:.1f}%</td><td>{r["hi_low"]:.1f}%</td>'
                 f'<td>{r["lo_neg"]:.1f}%</td><td>{r["hi_neg"]:.1f}%</td>'
                 f'<td>{r["lo_p"]:.1f}</td><td>{r["hi_p"]:.1f}</td>'
                 f'<td>{r["lo_d"]/1000:.1f}</td><td>{r["hi_d"]/1000:.1f}</td>'
                 f'<td class="{cls}">{r["corr"]:+.2f}</td></tr>')

    srows = ""
    for yr in sg.index:
        srows += (f'<tr><td>{yr}</td><td>{sg.loc[yr,"exo"]:.1f}%</td>'
                  f'<td class="neg">{sg.loc[yr,"endo"]:.1f}%</td></tr>')

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>缺口工况指纹 · 外生 vs 内生</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.65}}
.wrap{{max-width:1010px;margin:0 auto;padding:28px 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 10px;color:#1f5bb8}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#fff;border-radius:12px;padding:15px 17px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:190px}}
.card .v{{font-size:21px;font-weight:700}}.card .v.neg{{color:#c23a3a}}.card .v.pos{{color:#1f5bb8}}
.card .t{{font-weight:600;margin-top:4px}}.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:7px 9px;border-bottom:1px solid #eef3f7;text-align:right}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
td:first-child,th:first-child{{text-align:left}}
.neg{{color:#c23a3a;font-weight:600}}.pos{{color:#1f5bb8;font-weight:600}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}li{{margin:6px 0}}
.hl{{background:#fff6ea;border-left:3px solid #e5853a;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}
</style></head><body><div class="wrap">
<h1>缺口“工况指纹”：外生 vs 内生（ERCOT × 西班牙）</h1>
<div class="sub">PS-032 证明"外生缺口→正、内生缺口→负"只是方向相容，且仅"内生→负"稳健。
本流程把符号落到可观测工况上：按缺口分位分组，比较各组的<b>低价/负价频率、价格中位、需求中位</b> ——
ERCOT 2025/2026 × 光伏/风电；西班牙 2023/2024/2025 × 光伏（含"无负价→负价常态化"的时间截面） · 核查日 2026-09-29</div>

<div class="cards">{cards}</div>

<div class="hl"><b>机制结论</b>：<b>内生缺口（潜力−实际）是货真价实的"供给过剩标记"</b>——
ERCOT 光伏高缺口档负价频率 {pv_in['lo_neg']:.1f}% → <b>{pv_in['hi_neg']:.1f}%</b>（需求同向下降 {pv_in['lo_d']/1000:.1f} → {pv_in['hi_d']/1000:.1f} GW）、
ERCOT 风电 {eg.loc['风电·内生缺口','lo_neg']:.1f}% → {eg.loc['风电·内生缺口','hi_neg']:.1f}%、西班牙光伏 2025 达 <b>{sg.loc[2025,'endo']:.0f}%</b>。
而<b>外生缺口不含过剩信号</b>：ERCOT 风电低风异常高的小时，负价频率反而从 {wd_ex['lo_neg']:.1f}% 降到 <b>{wd_ex['hi_neg']:.1f}%</b>、价格中位上升，是<b>真稀缺</b>；
ERCOT 光伏晴空缺口则无稳定标记（相关系数两年 {eg.loc['光伏·外生缺口','corr']:+.2f}，符号不定）。
另有一条时间向证据：<b>西班牙内生缺口高值档的负价频率 0%（2023，当年零负价）→ 15.7%（2024）→ 33.4%（2025）</b>，与负价小时数 0→247→544 同步。</div>

<div class="box"><h2 style="margin-top:0">① ERCOT：高缺口档 vs 低缺口档的负价频率</h2>
{bars_ercot(eg)}
<div class="note">两个"内生"指纹（光伏、风电）在最高两档缺口时负价频率明显抬升；风电"外生"（低风异常）恰好相反。
光伏"外生"（晴空缺口）两年不稳定 ⇒ 与 PS-032「外生正号不稳健」一致。</div></div>

<div class="box"><h2 style="margin-top:0">② ERCOT 明细（2025/2026 均值；价格 $/MWh，需求 GW）</h2>
<div class="scroll"><table>
<tr><th>指纹</th><th>低价频率<br>低档</th><th>低价频率<br>高档</th><th>负价频率<br>低档</th><th>负价频率<br>高档</th>
<th>价格中位<br>低档</th><th>价格中位<br>高档</th><th>需求中位<br>低档</th><th>需求中位<br>高档</th><th>corr(缺口,价格)</th></tr>
{rows}
</table></div></div>

<div class="box"><h2 style="margin-top:0">③ 西班牙：时间截面（高缺口档负价频率）</h2>
{bars_spain(sg)}
<div class="note">2023 年西班牙<b>全年零负价</b>，两口径高缺口档负价频率均为 0%；2024 起负价常态化、弃电抬升，
内生缺口高值档负价频率升至 15.7%，2025 达 33.4% ⇒ <b>同一技术跨年份，随弃电普及，"内生缺口=过剩"的标记逐年增强</b>，
部分回应了 PS-032「无法做时间向可逆性检验」的缺口。</div></div>

<div class="box"><h2 style="margin-top:0">④ 结论、局限与下一步</h2>
<ul class="note">
<li><b>结论一（机制坐实）</b>：内生缺口高的时段 = 低需求 + 负价/低价高发；两个市场、两种电源一致 ⇒
"内生缺口 = 供给过剩标记"不只是回归符号，而是可观测工况。</li>
<li><b>结论二（对照清晰）</b>：风电低风异常（外生）高的小时负价更少、价格更高，是稀缺；说明判据的"外生/内生"二分在机制上确有区分度。</li>
<li><b>结论三（时间向）</b>：西班牙 2023→2025 内生缺口高值档负价频率 0%→15.7%→33.4%，与负价小时数同步 ⇒ 该标记随市场成熟度增强。</li>
<li><b>局限</b>：①ERCOT 光伏外生缺口（晴空）本身受太阳高度角/季节主导，不是干净的云量代理，两年不稳定；
②ERCOT 光伏内生缺口含约 23% 模型残差（弃光仅数个百分点），低档/高档次序含噪声；
③分组为等样本十分位，跨市场档位不可直接比大小；④西班牙仍用日前价。</li>
<li><b>下一步</b>：①把这套"缺口档位→负价频率"曲线当作<b>简化预警曲线</b>，接入 PS-027 的季节辐照预报（预报 τ → 缺口档 → 负价概率）；
②补 ERCOT 2022 小时电价，做 PV 的"无弃光年份"反向对照。</li>
</ul></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"→ {p}")


if __name__ == "__main__":
    build()
