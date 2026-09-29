# -*- coding: utf-8 -*-
"""PS-044 报告: 补齐 ES 侧 NWP —— D-1/D-3 西班牙负价日预警能建起来吗?

输出: output/spain_negprice_d1warning/index.html
用法: python scripts/analysis/build_spain_nwp_report.py
"""
import os
import re

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\spain"
OUT = r"c:\work\meteo\output\spain_negprice_d1warning"
BLUE, ORANGE, GREEN, RED, GREY = "#1f5bb8", "#e5853a", "#2f8f6b", "#c23a3a", "#8fa4b8"


def leadchart(lq):
    """逐 lead MAE 柱 + 分段偏差标注(西班牙)"""
    W, H, L, R, T, B = 660, 300, 56, 16, 20, 46
    vmax = 90.0

    def X(i):
        return L + (i + 0.5) * (W - L - R) / len(lq)

    def Y(v):
        return H - B - v / vmax * (H - T - B)

    s = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">']
    s.append(f'<rect x="{L}" y="{T}" width="{W-L-R}" height="{H-T-B}" fill="#fbfdff" stroke="#e3ecf4"/>')
    for g in np.arange(0, vmax + 1, 15):
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
    h = ""
    for lab, v, col, note in items:
        w = max(2.0, (v - vmin) / (vmax - vmin) * 100)
        h += ('<div style="display:flex;align-items:center;margin:6px 0;font-size:12.5px">'
              '<div style="width:330px;color:#3c556b">%s</div>'
              '<div style="flex:1;background:#eef3f7;border-radius:3px;height:15px;position:relative">'
              '<div style="width:%.1f%%;height:15px;background:%s;border-radius:3px"></div></div>'
              '<div style="width:52px;text-align:right;font-weight:700;color:%s">%.3f</div>'
              '<div style="width:190px;color:#8497a8;padding-left:10px">%s</div></div>'
              % (lab, w, col, col, v, note))
    return h


def pairbars(pairs):
    """两两对比条: (标签, NWP 预报值, 滚动基准值, 该行量程, 单位)"""
    h = ""
    for lab, a_, b_, vmax, unit in pairs:
        h += '<div style="margin:10px 0"><div style="font-size:12.5px;color:#3c556b;margin-bottom:3px">%s</div>' % lab
        for tag, v, col in (("NWP 预报", a_, GREEN), ("7 日滚动基准", b_, GREY)):
            w = max(1.5, v / vmax * 100)
            h += ('<div style="display:flex;align-items:center;font-size:11.5px">'
                  '<div style="width:104px;color:#8497a8">%s</div>'
                  '<div style="flex:1;background:#eef3f7;border-radius:3px;height:13px">'
                  '<div style="width:%.1f%%;height:13px;background:%s;border-radius:3px"></div></div>'
                  '<div style="width:120px;text-align:right;color:%s;font-weight:600">%.3f %s</div></div>'
                  % (tag, w, col, col, v, unit))
        h += "</div>"
    return h


def main():
    os.makedirs(OUT, exist_ok=True)
    lq = pd.read_csv(os.path.join(D, "spain_nwp_leadcheck.csv"))
    st1 = pd.read_csv(os.path.join(D, "spain_nwp_stage1.csv"))
    warn = pd.read_csv(os.path.join(D, "spain_nwp_warning.csv"))
    o25 = pd.read_csv(os.path.join(D, "spain_nwp_oos2025.csv"))
    rel = pd.read_csv(os.path.join(D, "spain_nwp_reliability.csv"))
    cal = pd.read_csv(os.path.join(D, "spain_nwp_warn2026.csv"), index_col=0, parse_dates=True)

    def tab(df, hi=None, hic=None):
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

    def w(sub, col="**2026 AUC**"):
        return float(warn.loc[warn["设定"].str.startswith(sub), col].iloc[0])

    def oo(sub, col="**2025 AUC**"):
        return float(o25.loc[o25[o25.columns[0]].str.startswith(sub), col].iloc[0])

    def s1(pair, col):
        return float(st1.loc[st1["设定"] == pair, col].iloc[0])

    w0, w1, w2, w2r, w2l, w3 = w("W0"), w("W1"), w("W2 "), w("W2r"), w("W2l"), w("W3")
    w4, w5, w6, w7, w8 = w("W4"), w("W5"), w("W6"), w("W7"), w("W8")
    o_w1, o_w2, o_w2r, o_w2l = oo("W1 持续性骨架"), oo("W2 W1 + ES D1"), oo("W2r"), oo("W2l")
    o_w5, o_w6 = oo("W5"), oo("W6")
    r_d1 = s1("NWP D1", "2026 MAE")
    r_d1_roll = s1("NWP D1", "滚动基准 2026 MAE")
    # 负荷行(D1)
    ld = st1[(st1["目标"] == "负荷 load_GWh") & (st1["设定"] == "NWP D1")].iloc[0]

    top30 = cal.sort_values("p_cal", ascending=False).head(30).reset_index()
    top30["date"] = top30["date"].dt.strftime("%Y-%m-%d")
    hit = 100 * top30["negday"].mean()
    base = 100 * cal["negday"].mean()
    lam_mean_poi = float((1 - np.exp(-cal["lam"])).mean())
    p_mean_cal = float(cal["p_cal"].mean())
    y_mean = float(cal["negday"].mean())
    br_poi = float(np.mean((1 - np.exp(-cal["lam"]) - cal["negday"]) ** 2))
    br_cal = float(np.mean((cal["p_cal"] - cal["negday"]) ** 2))

    pcols = [c for c in lq.columns if c.startswith("①") or c.startswith("②")]
    lq_disp = lq.rename(columns={pcols[0]: "早段偏差 2024-07~2025-04", pcols[1]: "后段偏差 2025-05~2026-09"})

    bars = aucbars([
        ("W0 仅日历（月份FE + 周末）", w0, GREY, "2 个日历量"),
        ("W1 持续性骨架（ES 滞后/滚动）", w1, BLUE, "PS-043 A1 基线"),
        ("W2 W1 + ES 份额/负荷 <b>D1</b> 预报", w2, GREEN, "本轮新增"),
        ("W3 W1 + ES 份额/负荷 <b>D3</b> 预报", w3, GREEN, "本轮新增"),
        ("W4 W1 + 原始 NWP（光照+气温）", w4, ORANGE, "不经过份额层"),
        ("W5 W1 + <b>同期实际</b>份额/负荷（上界）", w5, RED, "需同期观测"),
        ("W6 W1 + <b>完美气象</b> ERA5（上界）", w6, ORANGE, "气象理论天花板"),
        ("W8 W1 + FR 同期负价h（参照）", w8, RED, "需同期观测"),
    ])

    bars2 = aucbars([
        ("W1 持续性骨架", w1, BLUE, "起点"),
        ("W2r + 仅<b>份额</b> D1 预报", w2r, ORANGE, "2026 未增益"),
        ("W2l + 仅<b>负荷</b> D1 预报", w2l, GREEN, "2026 的增益来源"),
        ("W2 + 份额与负荷 D1 预报", w2, GREEN, "合计"),
    ])

    pair = pairbars([
        ("正午份额 noon_ratio", 0.0690, 0.0786, 0.09, ""),
        ("负荷 load_GWh (GWh/日)", float(ld["2026 MAE"]), float(ld["滚动基准 2026 MAE"]), 55.0, "GWh"),
    ])

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>补齐 ES 侧 NWP：D-1/D-3 西班牙负价日预警（PS-044）</title>
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
.kv{{display:flex;gap:18px;flex-wrap:wrap;margin:6px 0 2px}}
.kv div{{background:#f7fafc;border:1px solid #e9f0f6;border-radius:8px;padding:8px 12px;font-size:12.5px}}
.kv b{{font-size:16px;color:#1f5bb8}}
</style></head><body><div class="wrap">
<h1>把西班牙侧的"过去 7 天平均"换成 D-1 预报：预警能提升多少？</h1>
<div class="sub">PS-042/043 已证否"法国通道"在预报语境下的价值。本轮补齐<b>西班牙光伏区自身的 NWP 预报</b>
（ECMWF IFS previous-runs，D1–D7，24 个 GEM 容量加权点位），把 <code>noon_ratio</code> / <code>load_GWh</code>
也换成<b>预报量</b>，建成完全可运营的 D-1/D-3 预警 · 核查日 2026-09-29</div>

<div class="hl"><b>结论一：西班牙侧自己<b>是可预报的</b>，而且比法国侧更干净。</b>
用 NWP 预报的光照 + 气温预测西班牙正午份额 <code>noon_ratio</code>，2026 训练外 R² <b>0.756</b>、MAE <b>0.069</b>
（7 日滚动基准 0.079）；预测日负荷 MAE <b>{float(ld['2026 MAE']):.1f} GWh</b>（滚动基准 {float(ld['滚动基准 2026 MAE']):.1f} GWh，改善约 <b>52%</b>）；
直接预测"正午负价日"的 2026 AUC 达 <b>0.880</b>，而只用滞后量只有 <b>0.774</b>。</div>

<div class="warn"><b>结论二（核心）：但把它接进预警后，增量很小且不稳定。</b>
在持续性骨架上（W1，2026 AUC <b>{w1:.3f}</b>）：加份额/负荷 <b>D1 预报</b> → <b>{w2:.3f}</b>（<b>{w2 - w1:+.3f}</b>），
加 <b>D3 预报</b> → <b>{w3:.3f}</b>（{w3 - w1:+.3f}）。
而在第二个样本外年 2025 上，同样设定给 <b>{o_w2:.3f}</b>（基线 {o_w1:.3f}，<b>{o_w2 - o_w1:+.3f}</b>）
⇒ <b>两年符号一致，但量级差 7 倍</b>，且增益来源会翻转（2026 靠<b>负荷</b>预报 {w2l - w1:+.3f}、份额反而 {w2r - w1:+.3f}；
2025 靠<b>份额</b>预报 {o_w2r - o_w1:+.3f}、负荷反而 {o_w2l - o_w1:+.3f}）。</div>

<div class="bad"><b>结论三：这条通道的上界本身就不高。</b>
把明天的份额/负荷换成<b>真实观测值</b>（W5），2026 AUC 只到 <b>{w5:.3f}</b>（{w5 - w1:+.3f}）；
换成<b>完美气象</b>观测（W6）也只有 <b>{w6:.3f}</b>（{w6 - w1:+.3f}）。
⇒ 即使 D-1 预报做到完美，也只能再多拿约 0.01–0.02 AUC。<b>原始气象量（不经过"份额/负荷"这一层变换）几乎没有信息</b>：
W4（原始 NWP）{w4:.3f}、W6（完美气象）{w6:.3f}，都不优于 W1。</div>

<div class="box"><h2 style="margin-top:0">① lead 同质性筛查（PF-015 在西班牙侧同样成立）</h2>
{leadchart(lq)}
<div class="note">D1–D3 的 MAE 为 <b>{lq['MAE'].iloc[0]:.1f} / {lq['MAE'].iloc[1]:.1f} / {lq['MAE'].iloc[2]:.1f} W/m²</b>，
相关 0.988–0.997；D6/D7 跳到 {lq['MAE'].iloc[5]:.0f} / {lq['MAE'].iloc[6]:.0f} W/m²。</div>
<h3>分段偏差（W/m²）—— 判定归档是否同质</h3>
{tab(lq_disp)}
<div class="bad">与 PS-043 完全相同的缺陷：<b>D6/D7 在 2024-07~2025-04 段系统性偏高</b>
（D7 偏差 {lq[pcols[0]].iloc[6]:+.0f} W/m²，后段却是 {lq[pcols[1]].iloc[6]:+.0f}）
⇒ 主分析只用 <b>D1–D3</b>。<b>这是同一个坑的第二次复现</b>，说明 PF-015 应作为"用任何历史预报归档"的前置检查。</div></div>

<div class="box"><h2 style="margin-top:0">② 西班牙侧可预报性：NWP 预报 → 份额 / 负荷 / 正午负价 h</h2>
<h3>预报量相对"7 日滚动基准"的改进（2026）</h3>
{pair}
<div class="note">负荷的改进最显著（MAE {float(ld['2026 MAE']):.1f} vs {float(ld['滚动基准 2026 MAE']):.1f} GWh），
因为气温驱动的日负荷波动无法由过去 7 天平均捕捉；正午份额的改进较小（0.069 vs 0.079），
因为它由"装机水位（滚动量能捕捉）+ 当天天气（预报能捕捉）"两部分构成。</div>
{tab(st1)}
<h3>正午负价日的排序能力</h3>
<div class="note">直接以 <code>negh_noon</code> 为泊松目标、特征 = NWP D1/D2/D3 + 滞后负价：
2026 AUC <b>0.880 / 0.879 / 0.878</b>，而<b>只用滞后量</b>为 0.774 ⇒ 西班牙侧的"资源通道"
在短期是<b>真实可预报</b>的（这一点与法国通道完全不同，后者即使有真实预报也换不来增益）。</div></div>

<div class="box"><h2 style="margin-top:0">③ D-1/D-3 预警：持续性骨架 vs 预报量 vs 上界</h2>
{bars}
<h3>完整设定表（训练 2024-07~2025-12 → 测试 2026）</h3>
{tab(warn, hi=0.85, hic="**2026 AUC**")}
<div class="note"><b>关键对照</b>：W1 持续性骨架 {w1:.3f}；W2/W3（+D1/D3 预报）{w2:.3f}/{w3:.3f}；
W5（+同期实际，上界）{w5:.3f}；W7（仅同期国内基本面，= PS-043 的 B1）{w7:.3f}；
W8（+FR 同期负价 h，PS-041/043 的参照）{w8:.3f}。<br>
⇒ ①西班牙自身的持续性（{w1:.3f}）已经<b>强于</b>同期国内份额/负荷（{w7:.3f}）；
②这条通道的<b>上界</b>是 {w5:.3f}（+{w5 - w1:.3f}），D-1 预报只回收了其中一小部分。</div>
<h3>增益来自份额还是负荷？</h3>
{bars2}
<div class="warn">2026 的增量几乎全部来自<b>负荷 D1 预报</b>（{w2l:.3f}），份额预报反而不增益（{w2r:.3f}）；
2025 恰好相反（份额 {o_w2r:.3f} vs 负荷 {o_w2l:.3f}）。
⇒ 单看任一年都会得出"某一条管道有效"的结论，而两年合看只能得出"<b>不稳定</b>"。</div></div>

<div class="box"><h2 style="margin-top:0">④ 第二个样本外年：训练 2024-07~2024-12（184 日）→ 测试 2025</h2>
{tab(o25, hi=0.92, hic="**2025 AUC**")}
<div class="note">基线 {o_w1:.3f} → 加 D1 预报 {o_w2:.3f}（<b>{o_w2 - o_w1:+.3f}</b>）；
同期实际上界 {o_w5:.3f}；完美气象上界 {o_w6:.3f}。<br>
⚠ 本表两处"水平"不可用：W5（同期实际）MAE 8.9 h/日、W8（FR 同期负价 h）MAE <b>226.6 h/日</b>——
又是 PS-041 §8-1 的 <b>对数链接 × 无界变量</b>外推爆炸（仅 184 日训练）。
<b>排序（AUC）与水平（MAE）必须分开评估与使用</b>。</div></div>

<div class="box"><h2 style="margin-top:0">⑤ 概率校准与 2026 预警日历（运营模型 = W1 持续性骨架）</h2>
<div class="kv">
<div>泊松 <code>1−exp(−λ)</code> 均值 <b>{lam_mean_poi:.3f}</b></div>
<div>校准后均值 <b>{p_mean_cal:.3f}</b></div>
<div>2026 实际负价日比例 <b>{y_mean:.3f}</b></div>
<div>Brier：泊松 {br_poi:.4f} → 校准 <b>{br_cal:.4f}</b></div>
</div>
{tab(rel)}
<div class="warn"><b>校准能修形状，修不了水位。</b>泊松概率把 2026 高估了 {lam_mean_poi - y_mean:+.3f}；
用<u>训练期</u>经验曲线校准后反而<b>低估</b> {p_mean_cal - y_mean:+.3f}——
因为 2026 的负价水位比训练期（2024-07~2025-12）高得多（装机增长 + 份额跃升）。
Brier 由 {br_poi:.4f} 降到 {br_cal:.4f}（形状更准），但<b>水位必须再加一层跨年校正</b>
（与 PS-037"季节偏差校正不可省"同源）。</div>
<h3>2026 校准概率最高的 30 日</h3>
<div class="note">命中率 <b>{hit:.1f}%</b>（30 日里 {int(top30['negday'].sum())} 日为负价日），
而 2026 全期基准只有 <b>{base:.1f}%</b> ⇒ 提升 <b>{hit / base:.1f}×</b>。
预警档位由可靠性曲线的 8 个分箱给出（最高档 ≈ {rel['p'].iloc[-1]:.2f}）。</div>
{tab(top30[['date', 'lam', 'p_cal', 'negday', 'negh']])}
</div>

<div class="box"><h2 style="margin-top:0">⑥ 结论与下一步</h2>
<ul class="note">
<li><b>西班牙侧可预报，法国侧不可预报</b>——这是本轮最重要的<b>不对称</b>：用同一套 NWP 与同一套流程，
把 <code>negh_noon</code> 直接作为目标时，西班牙侧 AUC 从 0.774（仅滞后）升到 <b>0.880</b>；
而 PS-043 在法国侧加真实 D-1~D-7 预报只换来 +0.001。</li>
<li><b>但对"西班牙负价日"这个最终目标的增量依然很小</b>（2026 {w2 - w1:+.3f}、2025 {o_w2 - o_w1:+.3f}），
原因是<b>上界低</b>：即使换成同期真实份额/负荷也只 +{w5 - w1:.3f}。
西班牙负价日的日内排序信息，主要已经装在"<b>它昨天也负价了</b>"这件事里。</li>
<li><b>产品形态确定下来</b>：D-1 预警 = <b>西班牙自身持续性为骨架</b>（2026 AUC {w1:.3f}）
+ <b>ES 侧 D1 份额/负荷预报</b>（+{w2 - w1:+.3f}，不稳定）+ <b>经验可靠性校准</b>（形状可用、水位需跨年校正）；
法国侧降级为<b>当期诊断</b>变量。2026 概率前 30 日命中率 <b>{hit:.1f}%</b>（基准 {base:.1f}%）。</li>
<li><b>原始气象不是有效特征</b>：W4（原始 NWP）/ W6（完美气象）均不优于 W1
⇒ NWP 必须先经过"<b>份额/负荷</b>"这一层物理变换才进模型。这条对 ERCOT 侧的"缺口→电价"链同样适用。</li>
<li><b>下一步</b>：① 跨年水位校正（把 PS-037 的季节校正并进来），把校准概率变成可直接发布的档位；
② NegativeBinomial / 准泊松修正过散布，给区间而非点值；
③ 接入法国核电日前可用容量（PS-043 §7-4），压缩法国侧不确定性；
④ 待 ENTSO-E 网关恢复后补 A11 单一边界流（PS-041 §8-4）。</li>
</ul></div>

<div class="note" style="margin-top:6px">数据：Open-Meteo <code>previous-runs-api</code>（ECMWF IFS，D1–D7 历史预报，2024-07~2026-09）
+ <code>archive-api</code>（ERA5 实测辐照/气温），西班牙 24 个 GEM 容量加权点位（1° 网格，覆盖 79.6% 装机）；
价格/负荷/份额沿用 Energy-Charts 面板。方法与产物见 <code>PS-044</code>；
上游 <code>PS-043</code>（法国侧 NWP）、<code>PS-042</code>（可预报性检验）、<code>PS-041</code>（跨境结构）、<code>PS-040/039</code>（正午窗口、份额阈值）。</div>
</div></body></html>"""
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("→ %s" % os.path.join(OUT, "index.html"))


if __name__ == "__main__":
    main()
