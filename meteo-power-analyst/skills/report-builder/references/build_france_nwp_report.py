# -*- coding: utf-8 -*-
"""PS-043 报告: 用真实 NWP 预报填法国侧 —— 短期(D-1~D-7)能恢复区域通道吗?

输出: output/spain_negprice_nwpfr/index.html
用法: python scripts/analysis/build_france_nwp_report.py
"""
import os
import re

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_negprice_nwpfr"
BLUE, ORANGE, GREEN, RED, GREY = "#1f5bb8", "#e5853a", "#2f8f6b", "#c23a3a", "#8fa4b8"


def leadchart(lq):
    """逐 lead MAE 柱 + 分段偏差标注"""
    W, H, L, R, T, B = 660, 300, 56, 16, 20, 46
    vmax = 100.0

    def X(i):
        return L + (i + 0.5) * (W - L - R) / len(lq)

    def Y(v):
        return H - B - v / vmax * (H - T - B)

    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">']
    s.append(f'<rect x="{L}" y="{T}" width="{W-L-R}" height="{H-T-B}" fill="#fbfdff" stroke="#e3ecf4"/>')
    for g in np.arange(0, vmax + 1, 20):
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#eef3f7"/>' % (L, Y(g), W - R, Y(g)))
        s.append('<text x="%.1f" y="%.1f" font-size="10" fill="#9ab0c2" text-anchor="end">%d</text>'
                 % (L - 6, Y(g) + 3, g))
    bw = (W - L - R) / len(lq) * 0.5
    for i, (_, r) in enumerate(lq.iterrows()):
        mae = float(r.iloc[3])
        col = GREEN if i < 3 else (ORANGE if i < 5 else RED)
        s.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.85"/>'
                 % (X(i) - bw / 2, Y(mae), bw, H - B - Y(mae), col))
        s.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="#22303c" text-anchor="middle">%.0f</text>'
                 % (X(i), Y(mae) - 5, mae))
        s.append('<text x="%.1f" y="%.1f" font-size="11" fill="#6b8296" text-anchor="middle">%s</text>'
                 % (X(i), H - B + 16, r.iloc[0]))
    s.append('<text x="%.1f" y="%.1f" font-size="11" fill="#6b8296" text-anchor="middle">'
             '预报时效 lead</text>' % ((L + W - R) / 2, H - 10))
    s.append('<text x="13" y="%.1f" font-size="11" fill="#6b8296" transform="rotate(-90 13 %.1f)" '
             'text-anchor="middle">正午 GHI 指数 MAE (W/m²)</text>' % ((T + H - B) / 2, (T + H - B) / 2))
    s.append('<rect x="%.1f" y="%.1f" width="10" height="10" fill="%s" opacity="0.85"/>' % (L + 8, T + 8, GREEN))
    s.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="#22303c">两段同质 (主分析 D1–D3)</text>' % (L + 24, T + 17))
    s.append('<rect x="%.1f" y="%.1f" width="10" height="10" fill="%s" opacity="0.85"/>' % (L + 210, T + 8, ORANGE))
    s.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="#22303c">早段略偏</text>' % (L + 226, T + 17))
    s.append('<rect x="%.1f" y="%.1f" width="10" height="10" fill="%s" opacity="0.85"/>' % (L + 330, T + 8, RED))
    s.append('<text x="%.1f" y="%.1f" font-size="10.5" fill="#22303c">归档早段损坏，主分析弃用</text>' % (L + 346, T + 17))
    s.append('</svg>')
    return "".join(s)


def aucbars(items, vmin=0.60, vmax=0.95):
    """AUC 横向对比条"""
    h = ""
    for lab, v, col, note in items:
        w = max(2.0, (v - vmin) / (vmax - vmin) * 100)
        h += ('<div style="display:flex;align-items:center;margin:6px 0;font-size:12.5px">'
              '<div style="width:290px;color:#3c556b">%s</div>'
              '<div style="flex:1;background:#eef3f7;border-radius:3px;height:15px;position:relative">'
              '<div style="width:%.1f%%;height:15px;background:%s;border-radius:3px"></div></div>'
              '<div style="width:52px;text-align:right;font-weight:700;color:%s">%.3f</div>'
              '<div style="width:180px;color:#8497a8;padding-left:10px">%s</div></div>'
              % (lab, w, col, col, v, note))
    return h


def main():
    os.makedirs(OUT, exist_ok=True)
    lq = pd.read_csv(os.path.join(D, "france_nwp_leadcheck.csv"))
    fr = pd.read_csv(os.path.join(D, "france_nwp_frskill.csv"))
    two = pd.read_csv(os.path.join(D, "france_nwp_twostage.csv"))
    tw = pd.read_csv(os.path.join(D, "france_nwp_trainwin.csv"))
    hom = pd.read_csv(os.path.join(D, "france_nwp_homog.csv"))
    o25 = pd.read_csv(os.path.join(D, "france_nwp_oos2025.csv"))

    def tab(df, hi=None, hic=None):
        """按位置渲染表格(避免 itertuples 的字段名重命名问题)"""
        cols = list(df.columns)
        hi_idx = cols.index(hic) if hic in cols else None
        h = "<div class='scroll'><table><tr>" + "".join("<th>%s</th>" % c for c in cols) + "</tr>"
        for _, row in df.iterrows():
            h += "<tr>"
            for i, c in enumerate(cols):
                v = row.iloc[i]
                cls = ""
                if hi_idx is not None and i == hi_idx:
                    try:
                        cls = ' class="neg"' if float(v) >= hi else ""
                    except (TypeError, ValueError):
                        cls = ""
                h += "<td%s>%s</td>" % (cls, v)
            h += "</tr>"
        return h + "</table></div>"

    pcols = [c for c in lq.columns if c.startswith("①") or c.startswith("②")]
    lq_disp = lq.rename(columns={pcols[0]: "早段偏差 2024-07~2025-04", pcols[1]: "后段偏差 2025-05~2026-09"})
    hom_c0, o25_c0 = hom.columns[0], o25.columns[0]

    def a(of, pref, col):
        return float(of.loc[of[of.columns[0]].str.startswith(pref), col].iloc[0])

    def c_(of, sub, col):
        return float(of.loc[of[of.columns[0]].str.contains(sub), col].iloc[0])

    a1 = float(two.loc[two["设定"].str.startswith("A1 "), "**2026 AUC**"].iloc[0])
    a3 = float(two.loc[two["设定"].str.startswith("A3 "), "**2026 AUC**"].iloc[0])
    a6 = float(two.loc[two["设定"].str.startswith("A6 "), "**2026 AUC**"].iloc[0])
    a0 = float(two.loc[two["设定"].str.startswith("A0 "), "**2026 AUC**"].iloc[0])
    a1m = float(two.loc[two["设定"].str.startswith("A1m"), "**2026 AUC**"].iloc[0])
    b1 = float(two.loc[two["设定"].str.startswith("B1 "), "**2026 AUC**"].iloc[0])
    b3 = float(two.loc[two["设定"].str.startswith("B3 "), "**2026 AUC**"].iloc[0])
    fr_d1 = float(fr.loc[fr["法国侧事前特征"] == "NWP D1 天气", "**2026 AUC**"].iloc[0])
    fr_no = float(fr.loc[fr["法国侧事前特征"] == "仅核+日历(无天气)", "**2026 AUC**"].iloc[0])

    bars = aucbars([
        ("A0 仅日历（月份FE+周末）", a0, GREY, "2 个日历量"),
        ("A1 全事前：ES 滞后/滚动", a1, BLUE, "无法国通道"),
        ("A1 + FR λ（**气候学**）", float(two.loc[two['设定'].str.startswith('A2 '), '**2026 AUC**'].iloc[0]), ORANGE, "PS-042 口径"),
        ("A3 A1 + FR λ（**NWP D1**）", a3, ORANGE, "真实预报"),
        ("A6 A1 + FR 观测负价h（同期上界）", a6, GREEN, "需同期观测"),
        ("B1 ES 同期（仅国内）", b1, GREY, "需同期观测"),
        ("B3 B1 + FR λ（NWP D1）", b3, ORANGE, "真实预报"),
    ])

    frbars = aucbars([
        ("仅核电滚动 + 日历（无天气）", fr_no, GREY, "退化近乎无技能"),
        ("NWP D1 天气（光照 + 气温）", fr_d1, GREEN, "可预报"),
        ("NWP D2 天气", float(fr.loc[fr["法国侧事前特征"] == "NWP D2 天气", "**2026 AUC**"].iloc[0]), GREEN, "可预报"),
        ("NWP D3 天气", float(fr.loc[fr["法国侧事前特征"] == "NWP D3 天气", "**2026 AUC**"].iloc[0]), GREEN, "可预报"),
    ], vmin=0.5, vmax=0.9)

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>用真实 NWP 预报填法国侧：D-1~D-7 能恢复区域通道吗（PS-043）</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.62}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 20px}}
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
code{{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}}
</style></head><body><div class="wrap">
<h1>换掉气候学之后：真实的 D-1~D-7 预报能救活"区域过剩"通道吗？</h1>
<div class="sub">PS-042 证否了"用气候学把法国通道事前化"。本轮用 <b>ECMWF IFS 的历史预报（previous-runs，真正带 lead）</b>
替换它，在 2025 与 2026 两个从未参与训练的年份上重做对比 · 核查日 2026-09-29</div>

<div class="hl"><b>结论一：法国正午负价<b>本身</b>是可预报的。</b>
用 NWP 预报的光照 + 气温（D1/D2/D3）预测法国当日正午是否负价，2026 AUC <b>{fr_d1:.3f}～0.797</b>
（逐日 MAE 1.49–1.51 h）；而"只用核电滚动 + 日历、不含天气"退化到 <b>{fr_no:.3f}</b>。
⇒ 法国的负价由<b>当天天气</b>决定，而天气在 1–3 天内报得很准。</div>

<div class="bad"><b>结论二（核心，仍是否定）：但把它接到西班牙侧，增益≈0。</b>
在"全事前可得"的西班牙模型上（ES 滞后/滚动，2026 AUC <b>{a1:.3f}</b>），
加入 NWP 驱动的法国通道后 AUC <b>{a3:.3f}</b>（<b>{a3 - a1:+.3f}</b>）；
加入气候学版本反而 {float(two.loc[two['设定'].str.startswith('A2 '), '**2026 AUC**'].iloc[0]) - a1:+.3f}。
对照：加入<b>同期观测</b>的法国负价小时（不可用于预报）能到 <b>{a6:.3f}</b>（{a6 - a1:+.3f}）。
⇒ 法国通道携带的信息属于"<b>当下</b>"，而不是"<b>未来</b>"；它在 D-1 就已几乎被西班牙自身的持续性吸收。</div>

<div class="warn"><b>结论三（顺带修正 PS-042 的基线）：PS-042 的 0.751/0.753 被月份哑变量压低了约 0.08。</b>
同一特征式、只换训练窗口：0.751（训练 2023-2025）→ 0.761（训练 2024-2025）；
但把 <b>11 个月份哑变量</b>去掉后跳到 <b>{a1:.3f}</b>。
即"让模型自由学年内季节形状"在<b>日尺度</b>同样过拟合——与 PS-038 在月尺度观察到的现象一致。</div>

<div class="box"><h2 style="margin-top:0">① 先做 lead 同质性筛查（否则会误判 D6/D7）</h2>
{leadchart(lq)}
<div class="note">用同一批法国点位算"正午 GHI 指数"，与 ERA5 实测对照。D1–D3 的 MAE 为 <b>{lq['MAE'].iloc[0]:.1f} / {lq['MAE'].iloc[1]:.1f} / {lq['MAE'].iloc[2]:.1f} W/m²</b>，
相关 0.985–0.996；D6/D7 的 MAE 跳到 {lq['MAE'].iloc[5]:.0f} / {lq['MAE'].iloc[6]:.0f} W/m²。</div>
<h3>分段偏差（W/m²）—— 判定归档是否同质</h3>
{tab(lq_disp)}
<div class="bad"><b>归档缺陷：</b>previous-runs 的 <b>D6/D7 在 2024-07~2025-04 段系统性偏高</b>
（D7 偏差 {lq[pcols[0]].iloc[6]:+.0f} W/m²，约为实测的 1.4–1.6 倍），2025-05 起才恢复正常
（{lq[pcols[1]].iloc[6]:+.0f}）。若不筛查就直接用，训练集与测试集的 lead 分布不一致，
会<b>把 D7 的真实技能低估</b>。<br>
<b>处置</b>：主分析只用 <b>D1–D3</b>；D5/D7 另在"同质窗"（训练 2025-05 起）内评估（见 §④）。</div></div>

<div class="box"><h2 style="margin-top:0">② 法国侧：NWP 天气 → 法国正午负价</h2>
{frbars}
<div class="note">特征 = 正午 GHI 指数 + 正午气温 + <b>核电 7 日滚动</b>（排产慢，属事前可得）+ 周末，
泊松对数链接，训练 2024-07~2025-12，测试 2026。</div>
{tab(fr, hi=0.75, hic="**2026 AUC**")}
<div class="note">三个 lead 的 AUC/MAE/Spearman 几乎相同（0.791/0.797/0.795；1.51/1.49/1.48 h；0.50/0.51/0.51）
⇒ 在这条链上 <b>D-1 与 D-3 的信息量等价</b>，因为法国负价由"当天光照 + 周末 + 核电"决定，而这几个量在 3 天内都报得准。
加月份 FE 反而使样本外从 0.791 掉到 0.774（又是季节项过拟合）。</div></div>

<div class="box"><h2 style="margin-top:0">③ 两阶段：接到西班牙侧后增益≈0</h2>
{bars}
<h3>完整设定表（训练 2024-07~2025-12 → 测试 2026）</h3>
{tab(two, hi=0.86, hic="**2026 AUC**")}
<div class="note">
<b>A 系列（全部事前可得）</b>：仅日历 {a0:.3f} → 加 ES 滞后/滚动 <b>{a1:.3f}</b> → 再加 NWP 驱动的法国通道 <b>{a3:.3f}</b>
（<b>{a3 - a1:+.3f}</b>）。<br>
<b>B 系列（ES 侧用同期观测，仅作对照）</b>：仅国内 {b1:.3f} → 加 NWP 法国通道 {b3:.3f}（{b3 - b1:+.3f}）→
加同期法国观测 {float(two.loc[two['设定'].str.startswith('B4 '), '**2026 AUC**'].iloc[0]):.3f}
（{float(two.loc[two['设定'].str.startswith('B4 '), '**2026 AUC**'].iloc[0]) - b1:+.3f}）。<br>
⇒ <b>无�increment来自"未来"的法国状态；有增量的只有"当下"的法国状态。</b></div>
<h3>诊断：0.751 → 0.838 的差异来自哪里？</h3>
{tab(tw)}
<div class="warn">同一特征式（ES 滞后/滚动 + 月份FE）换训练窗口只值 <b>0.010</b>（0.751 → 0.761）；
把月份 FE 去掉后同族模型达到 <b>{a1:.3f}</b>。⇒ PS-042 的"P 系列"基线被
<b>11 个月份哑变量在 18 个月样本上的过拟合</b>压低了约 0.08 AUC。
这不是 PS-042 结论的错误（"FR 通道不增益"依旧成立），而是它的<b>基线偏低</b>，
使区域通道看起来还有空间——换成正确基线后，空间更小。</div>
<h3>稳健性：λ 不做年内标准化</h3>
<div class="note">FR 强度 λ 在入 ES 模型前做了"年内 z-score"（理由是法国负价的年度水位由装机增长决定、天气不可预报，而 AUC 是年内排序）。
把标准化去掉、直接用原始尺度 λ，2026 AUC 仍为 <b>0.839 / 0.839 / 0.839</b>（D1/D2/D3）——与标准化版本完全一致
⇒ 结论不是标准化带来的。</div></div>

<div class="box"><h2 style="margin-top:0">④ 两个独立检验</h2>
<h3>同质窗：用短训练窗换取 lead 同质性（训练 2025-05~2025-12 → 测试 2026）</h3>
{tab(hom, hi=0.86, hic="**2026 AUC**")}
<div class="note">这样 D5/D7 可以与 D1/D3 公平比较。结果：加到 D1 {c_(hom, 'D1', '**2026 AUC**'):.3f}、
D3 {c_(hom, 'D3', '**2026 AUC**'):.3f}、
D5 {c_(hom, 'D5', '**2026 AUC**'):.3f}、
D7 {c_(hom, 'D7', '**2026 AUC**'):.3f}
（基线 {a(hom, 'A1 ', '**2026 AUC**'):.3f}）
⇒ <b>到 D7 都没有增益</b>，且增益不随 lead 变化（因为增益本身≈0）。</div>
<h3>第二个样本外年：训练 2024-07~2024-12（184 日）→ 测试 2025</h3>
{tab(o25, hi=0.90, hic="**2025 AUC**")}
<div class="note">2025 上重复出同一结论：基线 {a(o25, 'A1 ', '**2025 AUC**'):.3f}，
加 NWP 法国通道后 0.886–0.891（<b>无增益</b>），同期观测上界 0.934（+0.04）。<br>
⚠ 该表的"同期观测(上界)"MAE 高达 226.6 h/日——又是 PS-041 §8-1 的 <b>对数链接 × 无界变量</b>外推爆炸
（仅 184 日训练）。AUC 不受影响，但水平不可用。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 结论与下一步</h2>
<ul class="note">
<li><b>分层已经闭合</b>：法国负价可预报（NWP 天气，AUC≈0.79）；但"法国通道 → 西班牙负价日"的增量
在 D-1 就已被<b>西班牙自身的持续性</b>吃掉（+{a3 - a1:.3f}）。同期观测仍有 +{a6 - a1:.3f}，
说明共振的"当下"有信息、"未来"没有。</li>
<li><b>对 PS-042 的补正</b>：PS-042 说"不可事前化"，更精确的说法是
<b>"这条通道在事前之所以无用，不是因为气候学代理太粗，而是因为它的信息被本地持续性替代了"</b>。
即使用最真实的 D-1 预报也换不来增益。</li>
<li><b>PS-042 基线的修正</b>：其 P 系列（0.751/0.753）含 11 个月份哑变量，在日尺度上过拟合，
正确基线应取 <b>{a1:.3f}</b>（无月份 FE 的 ES 滞后/滚动）。这不改变结论方向，但改变了"还差多少"的判断。</li>
<li><b>真正可用的产品形态因此改变</b>：短期预警应当<b>直接以西班牙自身的持续性为骨架</b>
（2026 AUC {a1:.3f}），把法国侧当作<b>当期诊断/解释</b>变量而非预报输入；
再叠加 PS-042 §4.5 的条件结构表做情形解读。</li>
<li><b>下一步（按期望收益排序）</b>：① 把 PS-042 的条件表改造成"以持续性为骨架"的版本并做概率校准；
② 用 NegativeBinomial 修正过散布并给出区间；③ 补齐 ES 侧的 NWP（西班牙光伏区辐照预报），
把"同期份额/负荷"也换成预报量，得到完全可运营的 D-1 预警；④ 待 ENTSO-E 网关恢复后补 A11 单一边界流。</li>
</ul></div>

<div class="note" style="margin-top:6px">数据：Open-Meteo <code>previous-runs-api</code>（ECMWF IFS，D1–D7 历史预报，2024-07~2026-09，法国 20 个 GEM 容量加权点位）
+ <code>archive-api</code>（ERA5 实测辐照/气温） + Energy-Charts（法国/西班牙价格与分技术发电）。
方法与产物见 <code>PS-043</code>；上游 <code>PS-042</code>（气候学事前化）、<code>PS-041</code>（跨境结构）、<code>PS-040/039</code>（正午窗口、份额阈值）。</div>
</div></body></html>"""
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    html = html.replace("无�increment来自", "没有增量来自")
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("→ %s" % os.path.join(OUT, "index.html"))


if __name__ == "__main__":
    main()
