"""西班牙电力市场数据调研报告 (自包含 HTML)
用途: 调研 ESIOS/OMIE/PVGIS/ENTSO-E 等西班牙数据源, 评估复刻 ERCOT 风光缺口链路的可行性
输出: output/espana_esios_survey/index.html
"""
import os

import numpy as np
import requests

OUT = r"c:\work\meteo\output\espana_esios_survey"
os.makedirs(OUT, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}
BLUE, RED, ORANGE, GREY, GREEN = "#1f5bb8", "#c23a3a", "#e5853a", "#8aa0b4", "#2f8f6b"


def omie_day(yyyymmdd):
    u = ("https://www.omie.es/es/file-download?parents=marginalpdbc"
         f"&filename=marginalpdbc_{yyyymmdd}.1")
    r = requests.get(u, headers=H, timeout=60)
    rows = [l for l in r.text.strip().split("\n") if l.startswith("20")]
    return np.array([float(l.split(";")[4]) for l in rows])


def svg_price(px, title):
    w, ht, pad = 860, 300, (56, 16, 26, 50)
    x0, x1, y0, y1 = pad[3], w - pad[1], pad[2], ht - pad[0]
    n = len(px)
    lo, hi = min(px.min(), 0) - 5, px.max() * 1.08
    xp = lambda i: x0 + (x1 - x0) * (i + 0.5) / n
    yp = lambda v: y1 - (y1 - y0) * (v - lo) / (hi - lo)
    bw = (x1 - x0) / n * 0.72
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ht}" '
         f'font-family="Segoe UI,Arial" font-size="11">']
    for g in np.linspace(0, hi, 5):
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{yp(g):.0f}" y2="{yp(g):.0f}" stroke="#e7eef4"/>')
        s.append(f'<text x="{x0-6}" y="{yp(g)+3:.0f}" text-anchor="end" fill="{GREY}">{g:.0f}</text>')
    if lo < 0:
        s.append(f'<line x1="{x0}" x2="{x1}" y1="{yp(0):.0f}" y2="{yp(0):.0f}" '
                 f'stroke="{RED}" stroke-width="1.2" stroke-dasharray="4 3"/>')
    for i, v in enumerate(px):
        col = RED if v < 5 else (ORANGE if v < 40 else BLUE)
        top = yp(max(v, 0))
        hgt = abs(yp(v) - yp(0)) if v < 0 else (y1 - top)
        s.append(f'<rect x="{xp(i)-bw/2:.0f}" y="{top:.0f}" width="{bw:.0f}" '
                 f'height="{max(hgt,1):.0f}" fill="{col}" opacity="0.85"/>')
    step = max(1, n // 12)
    for i in range(0, n, step):
        lab = f"{i//4+1:02d}h" if n > 24 else f"{i+1:02d}h"
        s.append(f'<text x="{xp(i):.0f}" y="{ht-30}" text-anchor="middle" fill="{GREY}">{lab}</text>')
    s.append(f'<text x="{x0}" y="{y0-6}" fill="#5b7488">{title}</text>')
    s.append(f'<text x="{x0-6}" y="{yp(hi)-4:.0f}" text-anchor="end" fill="{GREY}">€/MWh</text>')
    s.append("</svg>")
    return "\n".join(s)


def build():
    px24 = omie_day("20240429")
    px24_full = px24 if len(px24) > 24 else px24      # 24 小时 (2024 为小时级 MTU)
    m24 = px24_full.mean()
    live = omie_day("20260927")
    live_neg = int((live < 0).sum())

    # 小时级重采样 (兼容 96 点 15min)
    def hourly(a):
        if len(a) == 96:
            return a.reshape(24, 4).mean(axis=1)
        return a
    h24 = hourly(px24_full)
    h_live = hourly(live)

    def card(v, t, d):
        return f'<div class="card"><div class="v">{v}</div><div class="t">{t}</div><div class="d">{d}</div></div>'

    cards = (card(f"{m24:.2f}", "西班牙日前均价", "2024-04-29 €/MWh (OMIE 实测)")
             + card(f"{px24_full.min():.0f}–{px24_full.max():.0f}", "当日最低–最高", "€/MWh, 午间长时间贴底")
             + card("403", "ESIOS 匿名访问", "需个人 token (邮件申请)")
             + card(f"{live_neg} 时段", "近期负价", "2026-09-27, 15min 时段数"))

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>西班牙电力市场数据调研 (ESIOS / OMIE / PVGIS)</title>
<style>
body{{font-family:'Segoe UI',system-ui,Arial;margin:0;background:#f4f7fa;color:#22303c;line-height:1.65}}
.wrap{{max-width:980px;margin:0 auto;padding:28px 20px}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:18px;margin:28px 0 10px;color:#1f5bb8}}
h3{{font-size:14.5px;margin:18px 0 6px;color:#2c4a63}}
.sub{{color:#6b8296;font-size:13px;margin-bottom:16px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.card{{background:#fff;border-radius:12px;padding:15px 17px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex:1;min-width:160px}}
.card .v{{font-size:24px;font-weight:700;color:#1f5bb8}}.card .t{{font-weight:600;margin-top:4px}}
.card .d{{color:#7a90a4;font-size:12px;margin-top:4px}}
.box{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:18px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}
th,td{{padding:7px 9px;border-bottom:1px solid #eef3f7;text-align:left;vertical-align:top}}
th{{color:#7a90a4;font-weight:600;background:#fafcfe}}
code{{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}}
.note{{font-size:12.5px;color:#5b7488;line-height:1.75}}li{{margin:5px 0}}
.ok{{color:#2f8f6b;font-weight:600}}.no{{color:#c23a3a;font-weight:600}}
.hl{{background:#eef5ff;border-left:3px solid #1f5bb8;padding:12px 16px;border-radius:6px;margin:14px 0}}
.scroll{{overflow-x:auto}}
a{{color:#1f5bb8}}
</style></head><body><div class="wrap">
<h1>西班牙电力市场数据调研</h1>
<div class="sub">调研对象：ESIOS（REE 数据平台）、OMIE（伊比利亚市场运营方）、PVGIS / CAMS / SARAH-3（辐照）、ENTSO-E Transparency ·
目的：评估作为 ERCOT「风光缺口 → 电价」链路（PS-021~028）的<b>外部参照市场</b>的可行性 · 核查日 2026-09-28</div>

<div class="cards">{cards}</div>

<div class="hl"><b>核心结论</b>：西班牙是当前全球<b>最极端的高可再生渗透市场</b>（2025 年风电 21.6% + 光伏 18.4% ≈ 40% 发电量），
负电价与弃电已常态化（2025 年 477~798 小时 ≤0 €/MWh，技术受限弃电由 2024 年 1.6% 升至 2025 年 3.2%、2025 年 7 月峰值约 11%）。
它对本项目的价值不是"再多一个数据源"，而是 <b>PS-028「风电缺口 = 内生弃风」结论的极端样本</b>：西班牙把"高风/高光 + 低需求 → 负价 → 弃电"这条链推到了临界点。
数据获取上：<b>OMIE 与 PVGIS 均已实测可用且无需注册</b>；ESIOS 与 ENTSO-E 需邮件申请免费 token（ESIOS 匿名请求返回 403）。</div>

<div class="box"><h2 style="margin-top:0">① 实测验证结果（本报告数据均来自实际请求）</h2>
<div class="scroll"><table>
<tr><th>数据源</th><th>用途</th><th>认证</th><th>实测</th><th>结论</th></tr>
<tr><td>OMIE 日前市场文件<br><code>marginalpdbc_YYYYMMDD.1</code></td><td>西班牙+葡萄牙日前小时/15min 电价</td>
<td>无</td><td><span class="ok">HTTP 200</span>，2024-04-29 取回 24 点，日均 <b>{m24:.2f} €/MWh</b>（与公开报道一致）</td>
<td>可直接建库，历史+当日</td></tr>
<tr><td>PVGIS 5.3 <code>seriescalc</code></td><td>逐小时辐照 G(i)+气温+风速</td><td>无</td>
<td><span class="ok">HTTP 200</span>，Seville 2023 全年 8760h（SARAH-3 辐照 + ERA5 气象）</td>
<td>可作欧洲版"NSRDB"</td></tr>
<tr><td>ESIOS <code>api.esios.ree.es</code></td><td>实时分技术发电/需求/PVPC</td><td>个人 token（邮件）</td>
<td><span class="no">HTTP 403</span>（indicators / indicators/1001 / archives 均拒）</td>
<td>需先申请 token</td></tr>
<tr><td>ENTSO-E Transparency</td><td>泛欧分技术发电/负荷/日前价/风光预测</td><td>免费 token（邮件）</td>
<td>未测（无 token）</td><td>西班牙报送方即 REE</td></tr>
</table></div>
<div class="note">注：OMIE 的 MTU 已从小时变为 <b>15 分钟</b>——2024-04-29 文件为 24 行，2026-09-27 文件为 <b>96 行</b>，解析需兼容两代格式。</div>
</div>

<div class="box"><h2 style="margin-top:0">② 你给的那一天：2024-04-29</h2>
{svg_price(h24, "2024-04-29 西班牙日前电价（OMIE 原始文件, 小时）")}
<div class="note">
当日特点：<b>双峰</b>（08h 早高峰 {px24_full.max():.2f}；22h 晚高峰 97.92 €/MWh），
<b>午间长时间贴底</b>——12~17h 连续 6 小时处于或接近全日最低 {px24_full.min():.1f} €/MWh，是光伏压价的典型"鸭子曲线"。
全日均价 <b>{m24:.2f} €/MWh</b>。<br>
⚠ 口径修正：部分二手报道只提"晚高峰 97.9 €/MWh 为最高"，但直接拉取 OMIE 原始文件显示<b>当日最高实为 08 时段 {px24_full.max():.2f} €/MWh</b>——以原始文件为准。
（该日所在的 2024 年 4 月，全月日前市场均价仅 <b>13.45 €/MWh</b>，为 2001 年以来最低月度值；4-29 是因晚高峰 + 风光回落而显著反弹的一天。）</div>
</div>

<div class="box"><h2 style="margin-top:0">③ 西班牙为什么值得作为外部参照</h2>
<h3>负电价从"罕见"变"常态"</h3>
<div class="scroll"><table>
<tr><th>年份</th><th>负/零电价小时</th><th>口径</th></tr>
<tr><td>2024-04-01</td><td>首次负价：15–18h 共 3 小时 −0.01 €/MWh；同日另有 10 小时 0 €/MWh，日均 2.76 €/MWh</td><td>OMIE 日前市场</td></tr>
<tr><td>2024</td><td><b>247 h 负价 + 537 h 零价 = 838 h（9.6%）</b>低于 1 €/MWh</td><td>研究口径 / 另口径 244 h 负价</td></tr>
<tr><td>2025</td><td><b>477 h 负价</b>（94 天），最低 −15.0 €/MWh；REE 口径 <b>798 h ≤0</b></td><td>Electricity Maps / REE 转述</td></tr>
<tr><td>2026 Q1</td><td><b>347 h 负价</b>（占 Q1 交易时段 16%）</td><td>PV Magazine 汇总</td></tr>
</table></div>
<h3>弃电（curtailment）快速上升</h3>
<ul class="note">
<li>REE 半岛系统因<b>技术限制无法并网</b>的可再生电量占比：<b>2024 年 1.6% → 2025 年 3.2%</b>。</li>
<li>2025 年 5–7 月弃电峰值 <b>7.2%</b>，<b>2025 年 7 月约 11%（历史最高）</b>，而当月 2024 年仅 0.8%；2025 年 7 月单月逾 <b>1,100 GWh</b> 未能并网。</li>
<li>2024 年维持电网运行的约束成本日均约 350 万欧元，极端日可达 1,800 万欧元。</li>
</ul>
<h3>装机与发电结构</h3>
<ul class="note">
<li>2025 年发电占比：风电 <b>21.6%</b>（58,801 GWh，连续第三年第一大电源）、核电 19%、光伏 <b>18.4%</b>（50,188 GWh，同比 +12.5%）。</li>
<li>年新增装机：光伏 8,100 MW(2023) → 9,500 MW(2024) → 10,105 MW(2025)；风电 650 / 1,300 / 1,150 MW。</li>
<li>口径提示：UNEF 称光伏占"约 23%"（含自消费/消费口径），与 REE 的 18.4%（发电量口径）不可直接比较。</li>
</ul>
<h3>2025-04-28 伊比利亚大停电</h3>
<div class="note">2025-04-28 12:33 CEST 西班牙大陆与葡萄牙全境停电，ENTSO-E 定级 <b>ICS Scale 3</b>（欧洲 20 余年来最严重），
且为<b>史上首次由过电压主导</b>的同类事故。ENTSO-E 最终报告（2026-03-20）指向多因素交互：400 kV 电压限值与脱网裕度过小、
常规机组无功/电压支撑失效、西班牙境内出力快速下降与机组连锁脱网。对本项目的含义：高逆变器（光伏）占比下的
<b>电压/无功支撑与经济性缺口是两类不同风险</b>——前者是系统安全维度，后者才是我们链路里的价格维度。</div>
</div>

<div class="box"><h2 style="margin-top:0">④ ESIOS 平台与 API 要点</h2>
<ul class="note">
<li><b>定位</b>：西班牙 TSO（Red Eléctrica）的数据门户，600+ 指标，含<b>实际计量</b>发电/需求与市场价。</li>
<li><b>认证</b>：<code>Authorization: Token token="&lt;TOKEN&gt;"</code>，token 需发邮件至 <code>consultasios@ree.es</code>（免费）；网页内置的公共 token 会变动，不适合生产。</li>
<li><b>Base URL</b>：<code>https://api.esios.ree.es</code>；端点 <code>/indicators</code>、<code>/indicators/{{id}}</code>、<code>search_indicators_by_name</code>、<code>/archives</code>。</li>
<li><b>参数</b>：<code>start_date</code>/<code>end_date</code>(ISO8601 带时区)、<code>geo_ids</code>、<code>geo_agg</code>、<code>geo_trunc</code>、<code>time_trunc</code>(five_minutes…hour/day/month/year)、<code>time_agg</code>。</li>
<li><b>响应</b>：JSON，<code>indicator.values[]</code> 每点含 <code>datetime</code>、<code>datetime_utc</code>、<code>value</code>、<code>geo_id</code>。</li>
</ul>
<h3>常用指标 ID（使用前请以 <code>/indicators</code> 元数据复核）</h3>
<div class="scroll"><table>
<tr><th>指标</th><th>ID</th><th>备注</th></tr>
<tr><td>日前/现货电价（OMIE）</td><td><b>600</b></td><td>geo_id 3=España；多个第三方口径一致</td></tr>
<tr><td>PVPC 2.0TD（小用户价）</td><td><b>1001</b></td><td>次日价约 20:15 发布</td></tr>
<tr><td>实时需求 demanda real</td><td><b>1293</b></td><td>半岛口径常配 geo 8741</td></tr>
<tr><td>实时光伏 Solar fotovoltaica</td><td><b>1295</b></td><td>与光热 1294 分列</td></tr>
<tr><td>实时风电 Eólica</td><td><b>551</b></td><td>水电 546 / 核电 549 / 联合循环 550 / 煤电 547</td></tr>
</table></div>
<div class="note">⚠ <b>必须逐指标核验 geo_id</b>：同一数字在不同指标下含义不同（例如 indicator 600 的多地域列表与半岛系统 8741/8742/8743 不一致）。
另有二手来源给出 10033/10034/10035 = 需求/风电/光伏，但来源相互冲突、未获官方确认，<b>标记为未核实</b>。
REE 另有"计划发电 PBF"与"实时 T.Real"两套口径，取数时须区分。</div>
</div>

<div class="box"><h2 style="margin-top:0">⑤ 若要把 ERCOT 链路复刻到西班牙，缺什么</h2>
<div class="scroll"><table>
<tr><th>ERCOT 元件</th><th>西班牙替代</th><th>获取门槛</th></tr>
<tr><td>NSRDB 辐照（1998~, 5min）</td><td><b>PVGIS-SARAH3</b>（逐小时, 2005–2023, 免注册）／<b>SARAH-3</b> 原生（0.05°, 30min, 1983–）／<b>CAMS Radiation</b>（1/15/60min, 2004–, 限 100 请求/天）／ERA5/ERA5-Land</td><td>PVGIS 无；CAMS 需 ADS 账号</td></tr>
<tr><td>pvlib 出力建模</td><td>不变（pvlib 通用）</td><td>无</td></tr>
<tr><td>GEM 电站清单</td><td>GEM 全球风光追踪库<b>覆盖西班牙</b>（公用事业风电约 26.8 GW 运营）</td><td>已有本地文件</td></tr>
<tr><td>EIA-930 实际分技术出力</td><td><b>ESIOS</b>（高频、西班牙口径）+ <b>ENTSO-E</b>（标准化、可回溯校验）</td><td>均需邮件 token</td></tr>
<tr><td>EIA / ERCOT 电价</td><td><b>OMIE</b>（源头市场价，已实测）／ESIOS 600／ENTSO-E 日前价</td><td>OMIE 无</td></tr>
<tr><td>RTM 实时价（15min）</td><td>西班牙无完全等价物：日前 + 日内（IDAs/连续日内）+ 平衡市场</td><td><b>结构性差异</b></td></tr>
</table></div>
<div class="hl"><b>关键结构性差异（务必注意）</b>：ERCOT 是<b>节点定价 + 实时市场（RTM）</b>体系，我们链路里的"缺口 → 实时价冲击"依赖 RTM；
而西班牙/伊比利亚是<b>分区定价（zone）+ 日前为主 + 日内连续交易</b>，缺少 ERCOT 式的 5 分钟实时结算价。
因此"缺口 → 实时尖峰"的推演在西班牙需要<b>改造口径</b>（改用日前价或日内连续价），不能直接平移。</div>
</div>

<div class="box"><h2 style="margin-top:0">⑥ 建议的下一步（按性价比排序）</h2>
<ol class="note">
<li><b>零门槛先做</b>：用 OMIE（电价）+ PVGIS（辐照）先建一个"西班牙版最小链路"——把 PS-021 的 pvlib 出力模型搬到西班牙（PVGIS 辐照 + GEM 西班牙光伏清单），与 ENTSO-E/ESIOS 的实际光伏出力对照。这一步不阻塞在任何审批上。</li>
<li><b>申请两个 token</b>：ESIOS（<code>consultasios@ree.es</code>）与 ENTSO-E（<code>transparency@entsoe.eu</code>），解锁实时分技术出力与标准化序列。</li>
<li><b>优先验证的目标问题</b>：PS-028 的"缺口 = 内生弃风"结论在西班牙这个<b>弃电 11% 的极端样本</b>上是否更加显著——即"高可再生出力 + 低需求 → 负价 → 弃电"的负相关是否比 ERCOT 更强。这是对现有结论最强的外部检验。</li>
<li><b>谨慎处理</b>：2025-04-28 大停电等系统事件会打断时序连续性，做缺口统计时须剔除；MTU 从小时转 15 分钟（2025-10 前后）也需在拼接时对齐。</li>
</ol>
</div>

<div class="box"><h2 style="margin-top:0">⑦ 局限与未决项</h2>
<ul class="note">
<li><b>ESIOS 速率限制</b>：官方公开页面未见量化条款，未能核实；不应把第三方服务（datons/python-esios）的限流当官方限制。</li>
<li><b>指标 ID 冲突</b>：10033/10034/10035 未获官方确认；1001 在个别二手资料中被误标为"日前边际价"。使用前须查 <code>/indicators</code> 元数据。</li>
<li><b>各指标历史起点不统一</b>：官方未给统一起始年，需逐指标读元数据。</li>
<li><b>负价小时数口径分歧大</b>（2025 年 477 vs 798 h），差异源于是否含零价、是否含日内市场、按小时还是半小时计量——引用时必须标口径。</li>
<li><b>PVGIS 数据止于 2023</b>（SARAH-3 版），近两年需用 CAMS 或 SARAH-3 ICDR 补足。</li>
<li>ENTSO-E 自 2025 起新增 File Library，鉴权走 Keycloak token，与旧 REST token 不同。</li>
</ul></div>

<div class="box"><h2 style="margin-top:0">来源</h2>
<div class="note">
<b>一手实测</b>：OMIE 原始文件（<code>omie.es/es/file-download?parents=marginalpdbc&amp;filename=marginalpdbc_YYYYMMDD.1</code>，2024-04-29 与 2026-09-27）、
PVGIS 5.3 API（<code>re.jrc.ec.europa.eu/api/v5_3/seriescalc</code>）、ESIOS API（<code>api.esios.ree.es</code>，返回 403）。<br><br>
<b>官方/权威</b>：
<a href="https://api.esios.ree.es/">ESIOS API 文档</a> ·
<a href="https://www.esios.ree.es/es/pagina/api">token 申请页</a> ·
<a href="https://www.omie.es/en/market-results/daily/daily-market/daily-hourly-price">OMIE 日前小时价</a> ·
<a href="https://www.omie.es/sites/default/files/2024-05/Informe%20Mensual%20Abril_%202024_ES.pdf">OMIE 2024 年 4 月月报</a> ·
<a href="https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5_en">PVGIS 5</a> ·
<a href="https://www.cmsaf.eu/EN/Highlights/Dokumente/News_38.html">CM SAF SARAH-3</a> ·
<a href="https://confluence.ecmwf.int/spaces/CKB/pages/266592908/CAMS+solar+radiation+time-series+data+documentation">CAMS 太阳辐射</a> ·
<a href="https://www.entsoe.eu/data/transparency-platform/">ENTSO-E Transparency</a> ·
<a href="https://www.entsoe.eu/publications/blackout/28-april-2025-iberian-blackout/">ENTSO-E 2025-04-28 大停电</a> ·
<a href="https://www.ree.es/es/datos/generacion/estructura-generacion">REE 发电结构</a> ·
<a href="https://www.miteco.gob.es/content/dam/miteco/es/energia/files-1/balances/Publicaciones/Documents/distrib_ele_2024/Estad%C3%ADstica%20de%20la%20Industria%20de%20la%20Energ%C3%ADa%20El%C3%A9ctrica.%20Datos%202024.pdf">MITECO 2024 电力工业统计</a> ·
<a href="https://globalenergymonitor.org/projects/global-solar-power-tracker">GEM 全球光伏追踪</a><br><br>
<b>二手（仅作交叉参考）</b>：
<a href="https://www.electricitymaps.com/grid-in-review-2025/spain">Electricity Maps 2025 西班牙</a> ·
<a href="https://www.pv-magazine.com/2026/05/08/europes-negative-electricity-price-hours-double-in-q1-amid-renewables-surpluses-market-imbalances/">PV Magazine 负价小时</a> ·
<a href="https://www.delfos.energy/es/blog-posts/curtailment-has-many-names">Delfos 弃电</a> ·
<a href="https://www.iberdrolaespana.com/en/sustainability/energy-transition/energy-mix-spain">Iberdrola 能源结构</a>
</div></div>
</div></body></html>"""
    p = os.path.join(OUT, "index.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"→ {p}")
    print(f"  2024-04-29 均价 {m24:.2f} €/MWh (n={len(px24_full)}), "
          f"2026-09-27 均价 {live.mean():.2f} (n={len(live)}, 负价 {live_neg})")


if __name__ == "__main__":
    build()