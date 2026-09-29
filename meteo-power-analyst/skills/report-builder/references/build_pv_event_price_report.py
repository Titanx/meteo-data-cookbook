"""生成 2022-07 光伏缺口×电价冲击推演 HTML 报告 (自包含, 内嵌 SVG)
输入: pv_counterfactual_hourly_2022-07.csv / pv_event_price_impact_2022-07.csv /
      pv_drop_events_2022-07.csv / price_elasticity_2025.csv /
      nsrdb_uscrn_daily.csv / ercot_pv_power_2022-07(.paramtemp).csv
输出: output/pv_event_price_impact_2022-07/pv_event_price_impact_ercot_2022-07.html
用法: python skills/report-builder/references/build_pv_event_price_report.py
"""
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data"
CTF = os.path.join(D, "nsrdb", "pv_counterfactual_hourly_2022-07.csv")
EVP = os.path.join(D, "nsrdb", "pv_event_price_impact_2022-07.csv")
DROP = os.path.join(D, "nsrdb", "pv_drop_events_2022-07.csv")
ELAS = os.path.join(D, "ercot", "price_elasticity_2025.csv")
USCRN = os.path.join(D, "uscrn", "nsrdb_uscrn_daily.csv")
PW_HRRR = os.path.join(D, "nsrdb", "ercot_pv_power_2022-07.csv")
PW_PARAM = os.path.join(D, "nsrdb", "ercot_pv_power_2022-07_paramtemp.csv")
OUT_DIR = r"c:\work\meteo\output\pv_event_price_impact_2022-07"
OUT = os.path.join(OUT_DIR, "pv_event_price_impact_ercot_2022-07.html")

C_CS = "#0969DA"    # 晴空反事实 蓝
C_EIA = "#BF3989"   # EIA 实际 品红
C_MODEL = "#06B6D4"  # 实际辐照模型 青
C_HW = "#D29922"    # 热浪 琥珀
C_EV = "#CF222E"    # 事件 红
C_DEM = "#8250DF"   # 需求 紫
GRID = "rgba(27,36,48,0.12)"
AXIS = "#64718A"
HW0, HW1 = pd.Timestamp("2022-07-13"), pd.Timestamp("2022-07-19")
BETA = 0.0508
BETA_HOT = 0.0584
PRICE = 182.0


class Fig:
    """极简 SVG 折线/柱状绘图器"""

    def __init__(self, w, h, ml, mr, mt, mb, x0, x1, lo, hi, ylab=""):
        self.w, self.h = w, h
        self.ml, self.mr, self.mt, self.mb = ml, mr, mt, mb
        self.pw, self.ph = w - ml - mr, h - mt - mb
        self.x0, self.x1, self.lo, self.hi = x0, x1, lo, hi
        self.s = [f'<svg viewBox="0 0 {w} {h}" role="img" '
                  f'style="width:100%;height:auto">']
        pad = (hi - lo) * 0.05
        self.plo, self.phi = lo - pad, hi + pad
        for frac in (0.25, 0.5, 0.75):
            yy = mt + self.ph * (1 - frac)
            self.s.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{w-mr}" '
                          f'y2="{yy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        self.s.append(f'<text x="{ml-6}" y="{mt-2}" font-size="11" '
                      f'fill="{AXIS}" text-anchor="end">{hi:.12g}</text>')
        self.s.append(f'<text x="{ml-6}" y="{mt+self.ph+10}" font-size="11" '
                      f'fill="{AXIS}" text-anchor="end">{lo:.12g}</text>')
        if ylab:
            self.s.append(f'<text x="{ml-40}" y="{mt+self.ph/2:.0f}" '
                          f'font-size="12" fill="{AXIS}" '
                          f'transform="rotate(-90 {ml-40} {mt+self.ph/2:.0f})">'
                          f'{ylab}</text>')

    def X(self, v):
        return self.ml + (v - self.x0) / (self.x1 - self.x0) * self.pw

    def Y(self, v):
        return self.mt + (1 - (v - self.plo) / (self.phi - self.plo)) * self.ph

    def band(self, x0, x1, fill):
        self.s.append(f'<rect x="{self.X(x0):.1f}" y="{self.mt}" '
                      f'width="{self.X(x1)-self.X(x0):.1f}" height="{self.ph}" '
                      f'fill="{fill}"/>')

    def hline(self, y, color, dash="4 4"):
        self.s.append(f'<line x1="{self.ml}" y1="{self.Y(y):.1f}" '
                      f'x2="{self.w-self.mr}" y2="{self.Y(y):.1f}" '
                      f'stroke="{color}" stroke-width="1.2" '
                      f'stroke-dasharray="{dash}"/>')

    def poly(self, xs, ys, color, width=2, dash=None, dot=False):
        pts = " ".join(f"{self.X(x):.1f},{self.Y(y):.1f}"
                       for x, y in zip(xs, ys))
        dd = f' stroke-dasharray="{dash}"' if dash else ""
        self.s.append(f'<polyline points="{pts}" fill="none" stroke="{color}"'
                      f' stroke-width="{width}" stroke-linejoin="round"{dd}/>')
        if dot:
            for x, y in zip(xs, ys):
                self.s.append(f'<circle cx="{self.X(x):.1f}" '
                              f'cy="{self.Y(y):.1f}" r="2.4" fill="{color}"/>')

    def area_between(self, xs, ytop, ybot, fill):
        pts = " ".join(f"{self.X(x):.1f},{self.Y(y):.1f}"
                       for x, y in zip(xs, ytop))
        pts += " " + " ".join(f"{self.X(x):.1f},{self.Y(y):.1f}"
                              for x, y in zip(reversed(xs), reversed(ybot)))
        self.s.append(f'<polygon points="{pts}" fill="{fill}" '
                      f'stroke="none"/>')

    def bars(self, xs, hs, bw, colors):
        for x, hv, c in zip(xs, hs, colors):
            y0, y1 = self.Y(0), self.Y(hv)
            self.s.append(f'<rect x="{self.X(x)-bw/2:.1f}" '
                          f'y="{min(y0,y1):.1f}" width="{bw:.1f}" '
                          f'height="{abs(y1-y0):.1f}" fill="{c}" '
                          f'rx="2"/>')

    def dots(self, xs, ys, r, color, opacity=1):
        op = f' opacity="{opacity}"' if opacity < 1 else ""
        for x, y in zip(xs, ys):
            self.s.append(f'<circle cx="{self.X(x):.1f}" cy="{self.Y(y):.1f}" '
                          f'r="{r}" fill="{color}"{op}/>')

    def txt(self, x, y, t, size=11, color=AXIS, anchor="middle", bold=False):
        b = ' font-weight="600"' if bold else ""
        self.s.append(f'<text x="{self.X(x):.1f}" y="{self.Y(y):.1f}" '
                      f'font-size="{size}" fill="{color}" '
                      f'text-anchor="{anchor}"{b}>{t}</text>')

    def atxt(self, x, y, t, size=11, color=AXIS, anchor="middle", bold=False):
        b = ' font-weight="600"' if bold else ""
        self.s.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                      f'fill="{color}" text-anchor="{anchor}"{b}>{t}</text>')

    def xticks(self, poss, labels):
        for p, lab in zip(poss, labels):
            self.atxt(self.X(p), self.h - 24, lab, anchor="middle")

    def render(self):
        self.s.append("</svg>")
        return "".join(self.s)


def load_pw(path):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    df.columns = ["model", "eia"]
    return df.dropna()


def group_events(ev):
    idx = ev.index
    groups = []
    for k, t in enumerate(idx):
        if groups and (t - idx[k - 1]).total_seconds() <= 3600 * 1.5:
            groups[-1].append(k)
        else:
            groups.append([k])
    return groups


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ctf = pd.read_csv(CTF, index_col=0, parse_dates=True)
    ev = pd.read_csv(EVP, index_col=0, parse_dates=True)
    drop = pd.read_csv(DROP)
    drop["start"] = pd.to_datetime(drop["start_utc"], utc=True) \
        .dt.tz_localize(None)
    elas = pd.read_csv(ELAS)
    usc = pd.read_csv(USCRN, index_col=1, parse_dates=True)
    usc.index = pd.to_datetime(usc.index)
    usc["station"] = usc.iloc[:, 0]
    pa, pb = load_pw(PW_PARAM), load_pw(PW_HRRR)

    groups = group_events(ev)
    ge = []
    for g in groups:
        sub = ev.iloc[g]
        hw = bool(sub.index.normalize().isin(
            pd.date_range("2022-07-13", "2022-07-18")).any())
        ge.append({
            "start": sub.index[0], "n": len(sub),
            "peak": sub["shortfall_mw"].max(),
            "gwh": sub["shortfall_mw"].sum() / 1000,
            "up": sub["uplift_pct_base"].max(),
            "hot": hw,
            "peak_t": sub["shortfall_mw"].idxmax(),
        })
    tot_gwh = sum(e["gwh"] for e in ge)
    hw_gwh = sum(e["gwh"] for e in ge if e["hot"])
    top = max(ge, key=lambda e: e["peak"])
    med_up = ev["uplift_pct_base"].median()
    max_up = ev["uplift_pct_base"].max()
    eia_month = ctf["eia"].sum() / 1000

    # ---------- ch1: USCRN 逐日正午比 ----------
    rat = usc.groupby(usc.index)["ratio"].median()
    f = Fig(880, 300, 56, 16, 16, 42, 0, 31, 1.0, 1.2, "NSRDB/USCRN 正午比")
    f.band(12, 18, "rgba(210,153,34,0.12)")
    f.hline(1.104, AXIS)
    f.poly(list(range(len(rat))), rat.round(3).tolist(), C_CS, 2, dot=True)
    f.atxt(f.X(22), f.Y(1.14), "热浪期", 12, C_HW, "middle", True)
    f.xticks([0, 5, 10, 15, 20, 25, 30],
             [rat.index[i].strftime("%m-%d") for i in (0, 5, 10, 15, 20, 25, 30)])
    f.atxt(f.X(28), f.Y(1.104) - 8, "非热浪中位 1.104", 11, AXIS, "start")
    svg_uscrn = f.render()
    usc_hw = rat[HW0:HW1]
    usc_nh = pd.concat([rat[:"2022-07-12"], rat["2022-07-19":]])
    drift = (usc_hw.median() / usc_nh.median() - 1) * 100

    # ---------- ch2: 温度修复对比 ----------
    def noon_win(x):
        return x["2022-07-13":"2022-07-18"].between_time("16:00", "22:00")

    ja, jb = noon_win(pa), noon_win(pb)
    b_a = (ja["model"] - ja["eia"]).mean()
    m_a = (ja["model"] - ja["eia"]).abs().mean()
    b_b = (jb["model"] - jb["eia"]).mean()
    m_b = (jb["model"] - jb["eia"]).abs().mean()
    da = pa.resample("1D").sum() / 1000
    db = pb.resample("1D").sum() / 1000
    hwd = pd.date_range("2022-07-13", "2022-07-18")
    bpd = [(da.loc[t, "model"] - da.loc[t, "eia"]) for t in hwd]
    bhd = [(db.loc[t, "model"] - db.loc[t, "eia"]) for t in hwd]

    f = Fig(430, 300, 52, 12, 16, 42, -0.5, 1.5, -450, 470, "MW")
    f.hline(0, AXIS, "2 2")
    xs = [0, 1]
    f.bars([0, 1], [b_a, b_b], 34, [C_MODEL, C_CS])
    f.bars([0.5, 1.5], [m_a, m_b], 34, ["rgba(6,182,212,0.45)",
                                       "rgba(9,105,218,0.45)"])
    f.atxt(f.X(-0.35), f.Y(0) - 6, "偏差", 11, AXIS, "end")
    f.atxt(f.X(0.5), f.Y(0) - 6, "MAE", 11, AXIS, "start")
    for x, v in [(0, b_a), (1, b_b), (0.5, m_a), (1.5, m_b)]:
        f.txt(x, v, f"{v:+.0f}", 11, "#1B2430", "middle", True)
    f.atxt(f.X(0), f.mt + 4, "温度参数化", 11, AXIS, "middle")
    f.atxt(f.X(1), f.mt + 4, "HRRR 实测温度", 11, AXIS, "middle")
    f.xticks([], [])
    f.atxt(f.w / 2, f.h - 8, "热浪期正午窗 (16-22 UTC)", 12, AXIS)
    svg_fix1 = f.render()

    f = Fig(430, 300, 52, 12, 16, 42, 0, 5, -9, 5, "GWh/日")
    f.hline(0, AXIS, "2 2")
    f.band(-0.3, 5.3, "rgba(210,153,34,0.06)")
    f.poly(list(range(6)), [round(v, 1) for v in bpd], C_MODEL, 2, dot=True)
    f.poly(list(range(6)), [round(v, 1) for v in bhd], C_CS, 2, dot=True)
    f.xticks(list(range(6)), [t.strftime("%m-%d") for t in hwd])
    svg_fix2 = f.render()

    # ---------- ch3: 全月 EIA vs 晴空 + 缺口 ----------
    xs = list(range(len(ctf)))
    f = Fig(880, 320, 56, 16, 16, 42, 0, len(ctf) - 1, 0, 11000, "MW")
    f.band(12 * 24, 18 * 24 + 23, "rgba(210,153,34,0.10)")
    f.area_between(xs, ctf["cs"].tolist(), ctf["eia"].tolist(),
                   "rgba(207,34,46,0.13)")
    f.poly(xs, ctf["cs"].tolist(), C_CS, 1.6)
    f.poly(xs, ctf["eia"].tolist(), C_EIA, 1.6)
    ex = [ctf.index.get_loc(t) for t in ev.index]
    f.dots(ex, ev["shortfall_mw"].tolist(), 3, C_EV)
    f.xticks([0, 6 * 24, 12 * 24, 18 * 24, 24 * 24, 30 * 24],
             ["07-01", "07-07", "07-13", "07-19", "07-25", "07-31"])
    svg_month = f.render()

    # ---------- ch4: 17 事件柱状 ----------
    f = Fig(880, 300, 56, 16, 16, 42, -0.8, len(ge) - 0.2, 0, 5.2, "GW")
    f.hline(0, AXIS, "2 2")
    for i, e in enumerate(ge):
        f.bars([i], [e["peak"] / 1000], 26,
               [C_HW if e["hot"] else C_CS])
        f.txt(i, e["peak"] / 1000 + 0.18, f"+{e['up']:.0f}%", 10,
              C_HW if e["hot"] else AXIS)
    f.xticks(list(range(len(ge))),
             [e["start"].strftime("%m-%d") for e in ge])
    svg_evbar = f.render()

    # ---------- ch5: 弹性外推 ----------
    gx = np.linspace(0, 5.0, 60)
    up_b = (np.exp(BETA * gx) - 1) * 100
    up_h = (np.exp(BETA_HOT * gx) - 1) * 100
    f = Fig(560, 360, 56, 16, 16, 46, 0, 5.0, 0, 34, "RTM 上浮 %")
    f.poly(gx.tolist(), up_b.round(2).tolist(), C_CS, 2)
    f.poly(gx.tolist(), up_h.round(2).tolist(), C_HW, 2, dash="6 4")
    ex = (ev["shortfall_mw"] / 1000).tolist()
    ey = ev["uplift_pct_base"].tolist()
    f.dots(ex, ey, 3.2, C_EV, 0.55)
    f.txt(3.1, (np.exp(BETA * 3.1) - 1) * 100 + 1.6,
          "基准 β=5.08%/GW", 11, C_CS, "start", True)
    f.txt(3.1, (np.exp(BETA_HOT * 3.1) - 1) * 100 - 2.6,
          "高需求 β=5.84%/GW", 11, C_HW, "start", True)
    f.txt(4.42, 25.0 + 1.8, "07-21 峰值 4.40 GW → +25.0%", 11, C_EV, "end", True)
    f.xticks([0, 1, 2, 3, 4, 5], [f"{v}" for v in range(6)])
    f.atxt(f.w / 2, f.h - 8, "光伏缺口 (GW)", 12, AXIS)
    svg_elas = f.render()

    # ---------- ch6/7: 07-13 与 07-14 案例 ----------
    def case_svg(day):
        sub = ctf.loc[day].between_time("12:00", "23:59")
        xs = list(range(len(sub)))
        f = Fig(880, 300, 56, 16, 16, 42, 0, len(sub) - 1, 0, 11000, "MW")
        f.area_between(xs, sub["cs"].tolist(), sub["eia"].tolist(),
                       "rgba(207,34,46,0.15)")
        f.poly(xs, sub["cs"].tolist(), C_CS, 2)
        f.poly(xs, sub["eia"].tolist(), C_EIA, 2)
        md = sub["demand"] / 1000
        ax2 = f
        f.s.append(f'<text x="{f.w-12}" y="{f.mt+2}" font-size="11" '
                   f'fill="{C_DEM}" text-anchor="end">需求 '
                   f'{md.min():.0f}~{md.max():.0f} GW</text>')
        f.xticks(xs[::2], [t.strftime("%H") for t in sub.index[::2]])
        f.atxt(f.w / 2, f.h - 8, "UTC (小时) · CDT = UTC-5", 12, AXIS)
        return f.render()

    svg_c13 = case_svg("2022-07-13")
    svg_c14 = case_svg("2022-07-14")

    # ---------- 表格 ----------
    def tr(*cells):
        return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    drop_rows = "".join(
        tr(r["start"].strftime("%m-%d %H:%M"), f"{int(r['hours'])}",
           f"{r['pre_mw']:.0f} → {r['trough_mw']:.0f}",
           f"{-r['d_eia_mw']:.0f}", f"{-r['d_model_mw']:.0f}",
           f"{r['explain_ratio']:.2f}", r["cause"])
        for _, r in drop.iterrows())

    def e_row(e):
        lab = e["start"].strftime("%m-%d %H:%M")
        return tr(lab, f"{e['n']}", f"{e['peak']:.0f}",
                  f"{e['gwh']:.1f}", f"+{e['up']:.1f}",
                  "热浪" if e["hot"] else "—")

    ev_rows = "".join(e_row(e) for e in
                      sorted(ge, key=lambda x: -x["gwh"]))

    e25 = elas[elas["year"] == 2025].set_index("model")
    e26 = elas[elas["year"] == 2026].set_index("model")

    def erow(name, label):
        return tr(label, f"+{e25.loc[name,'beta_per_gw_pct']:.2f}"
                   f" ({e25.loc[name,'se_per_gw_pct']:.2f})",
                   f"+{e26.loc[name,'beta_per_gw_pct']:.2f}"
                   f" ({e26.loc[name,'se_per_gw_pct']:.2f})")

    elas_rows = (erow("shortfall", "光伏缺口 (晴空反事实)")
                 + erow("shortfall_hot", "光伏缺口 · 高需求区 (≥72 GW)")
                 + tr("光伏出力水平 (控制变量)",
                       f"{e25.loc['level_solar','beta_per_gw_pct']:+.2f}"
                       f" ({e25.loc['level_solar','se_per_gw_pct']:.2f})",
                       f"{e26.loc['level_solar','beta_per_gw_pct']:+.2f}"
                       f" ({e26.loc['level_solar','se_per_gw_pct']:.2f})")
                 + tr("光伏 1h 爬坡 (控制变量)",
                      f"{e25.loc['ramp','beta_per_gw_pct']:+.2f}"
                      f" ({e25.loc['ramp','se_per_gw_pct']:.2f})",
                      f"{e26.loc['ramp','beta_per_gw_pct']:+.2f}"
                      f" ({e26.loc['ramp','se_per_gw_pct']:.2f})"))

    css = """
  :root{--bg:#FFFFFF;--bg2:#F4F7FC;--rule:#D6DEEB;--ink:#1B2430;--muted:#64718A;
        --accent:#0969DA;--accent2:#8250DF;--pos:#2DA44E;--neg:#CF222E;
        --font:'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',
               -apple-system,'Segoe UI',sans-serif}
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{font-family:var(--font);color:var(--ink);background:var(--bg);
       line-height:1.65;font-size:15px}
  .wrap{max-width:960px;margin:0 auto;padding:40px 24px 64px}
  header{border-bottom:3px solid var(--accent);padding-bottom:18px;margin-bottom:28px}
  h1{font-size:26px;font-weight:600}
  .sub{color:var(--muted);font-size:13.5px;margin-top:6px}
  h2{font-size:19px;margin:36px 0 12px;font-weight:600;
     border-left:4px solid var(--accent);padding-left:10px}
  h3{font-size:15.5px;margin:18px 0 8px}
  p{margin:8px 0}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
         gap:14px;margin:18px 0}
  .card{background:var(--bg2);border:1px solid var(--rule);border-radius:10px;
        padding:16px 18px}
  .card .k{font-size:12.5px;color:var(--muted)}
  .card .v{font-size:28px;font-weight:650;margin-top:4px}
  .card .v .u{font-size:14px;font-weight:500;color:var(--muted)}
  .card .s{font-size:12px;color:var(--muted);margin-top:4px}
  .fig{background:var(--bg2);border:1px solid var(--rule);border-radius:10px;
       padding:16px;margin:14px 0}
  .fig .cap{font-size:13px;color:var(--muted);margin-top:8px}
  .legend{display:flex;gap:18px;font-size:12.5px;color:var(--muted);
          margin-bottom:4px;flex-wrap:wrap}
  .legend i{display:inline-block;width:14px;height:3px;border-radius:2px;
            margin-right:5px;vertical-align:middle}
  table{border-collapse:collapse;width:100%;font-size:13.5px;margin:12px 0}
  th,td{border:1px solid var(--rule);padding:7px 10px;text-align:left}
  th{background:var(--bg2);font-weight:600}
  .mono{font-family:Consolas,Menlo,monospace;font-size:13px}
  .note{background:#FFF8E6;border:1px solid #EAD98A;border-radius:8px;
        padding:12px 16px;font-size:13.5px;margin:14px 0}
  .ok{color:var(--pos);font-weight:600}
  .bad{color:var(--neg);font-weight:600}
  .hw{color:var(--neg);font-weight:600}
  ul{padding-left:22px;margin:8px 0}
  li{margin:4px 0}
  .flow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0}
  .flow .box{background:var(--bg2);border:1px solid var(--rule);border-radius:8px;
             padding:8px 12px;font-size:13px}
  .flow .arr{color:var(--muted);font-size:15px}
  footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--rule);
         color:var(--muted);font-size:12.5px}
  footer a{color:var(--accent);text-decoration:none}
  a{color:var(--accent)}
  """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERCOT 光伏缺口 × 电价冲击推演 (2022-07)</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>光伏缺口 × 电价冲击推演</h1>
  <div class="sub">ERCOT · 2022 年 7 月 · 晴空反事实 (Solis) + 2025 RTM 电价弹性 (β=+5.08%/GW)
  · 出力底模: NSRDB v3.2.2 卫星辐照 + HRRR 实测温度 + pvlib 单轴跟踪 (ILR 1.30)
  · 56 座 ≥100MW 电站 (10.66 GW, 占 EIA 全网口径 ~89%) · 全文时间为 UTC (CDT = UTC-5)</div>
</header>

<h2>0. 执行摘要</h2>
<div class="cards">
  <div class="card"><div class="k">缺口事件</div>
    <div class="v">{len(ge)}<span class="u"> 个</span></div>
    <div class="s">{len(ev)} 个事件小时 (缺口 ≥1.5 GW, 15-23 UTC)</div></div>
  <div class="card"><div class="k">缺口总量</div>
    <div class="v">{tot_gwh:.0f}<span class="u"> GWh</span></div>
    <div class="s">占 7 月光伏实发 {eia_month:.0f} GWh 的 {tot_gwh/eia_month*100:.1f}%</div></div>
  <div class="card"><div class="k">中位 RTM 上浮</div>
    <div class="v">+{med_up:.1f}<span class="u">%</span></div>
    <div class="s">高需求弹性情景 +{ev['uplift_pct_hot'].median():.1f}%</div></div>
  <div class="card"><div class="k">最大上浮</div>
    <div class="v">+{max_up:.1f}<span class="u">%</span></div>
    <div class="s">{top['peak']/1000:.2f} GW 缺口 · {top['peak_t'].strftime('%m-%d %H:%M')}</div></div>
  <div class="card"><div class="k">热浪期缺口</div>
    <div class="v">{hw_gwh:.1f}<span class="u"> GWh</span></div>
    <div class="s">3 个事件 · 07-13 峰值缺口 {max(e['peak'] for e in ge if e['hot'])/1000:.1f} GW</div></div>
  <div class="card"><div class="k">价格锚换算</div>
    <div class="v">+{ev['price_uplift_usd_at_182'].median():.0f}
    <span class="u"> $/MWh</span></div>
    <div class="s">按 North 月均 $182 · 最大 +{ev['price_uplift_usd_at_182'].max():.0f}</div></div>
</div>
<p><b>一句话结论</b>：2022 年 7 月 ERCOT 光伏因云系/沙尘产生 {len(ge)} 个
≥1.5 GW 的出力缺口 (共 {tot_gwh:.0f} GWh, 其中热浪核心期 {hw_gwh:.1f} GWh)。
用 2025 年 RTM 面板数据标定的缺口→电价半弹性 (+5.08%/GW, 2026 年复验 +5.43%/GW)
外推，事件小时批发电价条件均值上浮中位 <span class="bad">+{med_up:.1f}%</span>、
最大 <span class="bad">+{max_up:.1f}%</span>；按当月 North 枢纽月均
$182/MWh 折算约 <span class="bad">+{ev['price_uplift_usd_at_182'].median():.0f}~+{ev['price_uplift_usd_at_182'].max():.0f} $/MWh</span>。
全部 7 个骤降事件均可由云/辐照解释，<b>无弃光信号</b>。</p>

<h2>1. 方法链</h2>
<div class="flow">
  <span class="box">GEM 电站坐标<br><small>56 座 / 10.66 GW</small></span><span class="arr">→</span>
  <span class="box">NSRDB 5min 辐照<br><small>GHI/DNI/DHI 2km</small></span><span class="arr">→</span>
  <span class="box">pvlib 单轴跟踪 POA<br><small>+ HRRR 2m 温度</small></span><span class="arr">→</span>
  <span class="box">PVWatts 出力<br><small>ILR 1.30 / 损耗 14%</small></span><span class="arr">→</span>
  <span class="box" style="border-color:{C_CS}">晴空反事实<br><small>Solis 模型</small></span><span class="arr">→</span>
  <span class="box" style="border-color:{C_EV}">缺口 = 反事实 − 实际<br><small>逐小时偏移校准</small></span><span class="arr">→</span>
  <span class="box" style="border-color:{C_DEM}">2025 RTM 弹性<br><small>ln(RTM) 面板回归</small></span><span class="arr">→</span>
  <span class="box" style="border-color:{C_HW}">电价冲击<br><small>exp(β·GW)−1</small></span>
</div>
<p>底模 (实际辐照链路) 已对 EIA-930 实际出力验证：小时 r = 0.9976、MAE 174 MW
(EIA 峰值的 1.8%)，详见 <a href="../nsrdb_pvlib_2022-07/nsrdb_pvlib_ercot_2022-07.html">
前置报告</a>。本报告在其上增加三块：① 温度链路修复 (§2)；② 缺口事件识别 (§3、§5)；
③ 缺口→电价弹性标定与外推 (§4、§5)。</p>

<h2>2. 出力模型修复：温度链路</h2>
<h3>2.1 问题定位：热浪期正午低估不是卫星反演的锅</h3>
<p>PS-021 底模在 07-13~18 热浪核心期正午低估 10~20%。候选原因有二：
极端高温下组件温度被低估，或热浪期气溶胶/霾使 NSRDB 卫星反演辐照偏低。
用 <b>USCRN 8 座德州地面基准站</b> (5 分钟 pyranometer 实测) 与 NSRDB 同像素交叉验证：</p>
<div class="fig">
  <div class="legend"><span><i style="background:{C_CS}"></i>NSRDB/USCRN 正午辐照比 (8 站日中位)</span>
  <span><i style="background:{C_HW}"></i>热浪窗口 07-13~18</span></div>
  {svg_uscrn}
  <div class="cap">NSRDB 卫星辐照系统性高于 USCRN 地面实测 ~10% (正午比非热浪日中位 1.104)
  —— 该水平差为卫星-地面已知偏差，已被 ILR/损耗标定吸收。
  关键判据：热浪期比值中位 {usc_hw.median():.3f} vs 非热浪 {usc_nh.median():.3f}
  (相对漂移 {drift:+.1f}%)，远小于站间离散 (分站中位 1.067~1.188)，
  <b>排除"热浪期反演劣化"假设</b>。</div>
</div>
<h3>2.2 修复：HRRR 实测 2m 温度替换参数化</h3>
<p>改用 Open-Meteo 历史预报 API 的 <b>HRRR 2m 分析温度</b> (56 站 × 744 小时,
16.2~44.3 °C, 逐时线性插值到 5min)，热浪期"一刀切 39°C"参数化被真实逐时温度场替换。
同时 ILR 由 1.25 上调至 <b>1.30</b> (在热浪/非热浪 × 正午/全月四个窗口扫描中取得最优平衡:
全月能量偏差 +1.4%、热浪正午 +0.5%)。</p>
<div class="fig">
  <div class="legend"><span><i style="background:{C_MODEL}"></i>温度参数化版</span>
  <span><i style="background:{C_CS}"></i>HRRR 实测温度版</span></div>
  {svg_fix1}
  {svg_fix2}
  <div class="cap">左：热浪正午窗 (16-22 UTC) 偏差由 <span class="bad">{b_a:+.0f} MW</span>
  → <span class="ok">{b_b:+.0f} MW</span>，MAE 由 {m_a:.0f} → {m_b:.0f} MW。
  右：热浪期逐日能量偏差，参数化版每日低估 4.8~7.5 GWh，HRRR 版收窄至 1.2~4.6 GWh
  (07-18 极端日仍有残余 -4.55 GWh，指向 44°C 峰值下温度外其他损耗)。
  全月口径：MAE 185 → 174 MW，能量偏差 -2.1% → +1.4%，r 保持 0.9976。</div>
</div>
<h3>2.3 最终标定参数</h3>
<table>
<tr><th>参数</th><th>值</th><th>依据</th></tr>
<tr><td>跟踪</td><td>N-S 单轴, max_angle 60°, backtrack gcr=0.35</td><td>真实电站标配</td></tr>
<tr><td>ILR (DC:AC)</td><td class="mono">1.30</td><td>四窗口扫描最优；吸收 NSRDB+10% 辐照水平差</td></tr>
<tr><td>系统损耗</td><td class="mono">14%</td><td>PVWatts 默认</td></tr>
<tr><td>温度</td><td class="mono">HRRR 2m 实测, Tcell=Tamb+POA/800×25</td><td>替换 25→39°C 参数化</td></tr>
<tr><td>温度系数</td><td class="mono">γ = −0.37%/°C</td><td>现代晶硅组件典型值</td></tr>
<tr><td>验证 (743h)</td><td class="mono">r=0.9976 · MAE 174 MW · 能量 +1.4% · 热浪正午 +0.5%</td>
<td>vs EIA-930 (−1h 平移)</td></tr>
</table>

<h2>3. 光伏骤降事件识别：7 个事件全部云主导</h2>
<p>用<b>实际辐照底模</b> (而非晴空反事实) 检验 EIA 陡降小时：若 NSRDB 实际辐照驱动的
模型出力同步下降且幅度相当，则骤降由云/辐照主导；若 EIA 降幅远大于模型，残差才可能指向
弃光/降额。检出 7 个骤降事件 (2h 内降幅 ≥1.5 GW)：</p>
<table>
<tr><th>起点 (UTC)</th><th>持续 h</th><th>EIA 峰→谷 MW</th><th>EIA 降幅</th>
<th>模型降幅</th><th>解释比</th><th>归因</th></tr>
{drop_rows}
</table>
<p>解释比 (模型降幅/EIA 降幅) 全部 ≥0.95，<b>无弃光信号</b>。注意 07-13 未入选——
当日傍晚出力是<b>渐进下降</b> (最大步长 ~1.3 GW/h，低于单小时骤降阈值)，
但按"对晴空的缺口"口径它是全月第二大事件 (§5.4)：两种口径互补，
骤降口径看时间导数，缺口口径看水平差。</p>

<h2>4. 缺口→电价弹性：2025 标定，2026 复验</h2>
<p>定义光伏缺口 <span class="mono">shortfall = 晴空包络 − 实际出力</span>
(2025 年用数据驱动包络：每个 (小时, 儒略日±15d) 网格取 P95)，
在 <span class="mono">ln(RTM) ~ shortfall + 风电 + 需求 + 小时/月份固定效应</span>
面板回归中标定半弹性 β (GW 为单位)：</p>
<table>
<tr><th>变量</th><th>2025 年 β (%/GW, SE)</th><th>2026 年 (至 9 月) 复验</th></tr>
{elas_rows}
</table>
<p>两年 β = <b>+5.08 与 +5.43 %/GW</b>，一致性 ±7%，弹性结构稳定；
光伏<b>水平</b>与<b>爬坡</b>项为负 (出力整体高时压价)，与直觉一致——
即电价对"缺口"比对"水平"更敏感，缺口是真正的价格冲击因子。
高需求区 (≥72 GW) β 升至 <b>+5.84%/GW</b> (2025)，2026 年热季样本中为 +4.33%
(2026 夏季风光渗透率更高、平抑能力更强)，本报告以 2025 值为主、
高需求情景为辅做区间推演。</p>

<h2>5. 2022-07 缺口 × 电价冲击推演</h2>
<h3>5.1 晴空反事实与逐小时校准</h3>
<p>晴空反事实 = Solis 晴空辐照走同一物理链路 (单轴跟踪 / HRRR 温度 / ILR 1.30)。
缺口 = 反事实 − EIA 实际，再减去<b>逐小时</b>晴日基准偏移 (每小时的 5% 分位，
−21~782 MW：正午 ~130-340、傍晚 ~730，吸收低仰角下晴空模型对跟踪支架的系统性高估)。
若用单一全局偏移，傍晚伪信号会把事件小时从 44 虚增至 62、缺口总量虚高 43%；
逐小时校准后晴日 (07-25) 正午缺口中位仅 67 MW，与 2025 标定口径一致。</p>
<div class="fig">
  <div class="legend"><span><i style="background:{C_CS}"></i>晴空反事实</span>
  <span><i style="background:{C_EIA}"></i>EIA-930 实际</span>
  <span><i style="background:{C_EV}"></i>事件小时 (缺口点)</span>
  <span><i style="background:{C_HW}"></i>热浪窗口</span></div>
  {svg_month}
  <div class="cap">744 小时全月序列。红色区域为晴空反事实与实际出力之差；
  红点标记 44 个缺口 ≥1.5 GW 的事件小时。07-13~18 热浪期 (琥珀带) 内缺口最集中，
  但 07-21、07-09 等非热浪日的缺口绝对量更大 —— 需求侧的放大作用见 §5.4。</div>
</div>
<h3>5.2 事件汇总：{len(ge)} 个事件 (按缺口电量排序)</h3>
<div class="fig">
  <div class="legend"><span><i style="background:{C_CS}"></i>常规日事件</span>
  <span><i style="background:{C_HW}"></i>热浪期事件</span>
  (柱顶数字 = 峰值缺口的电价上浮 %)</div>
  {svg_evbar}
  <div class="cap">{len(ge)} 个事件峰值缺口 1.5~{top['peak']/1000:.1f} GW。热浪期事件
  (琥珀) 缺口未必最大，但发生在 75~78 GW 需求区间，实际价格冲击更强 (§4 高需求弹性)。</div>
</div>
<table>
<tr><th>起点 (UTC)</th><th>持续 h</th><th>峰值缺口 MW</th><th>缺口电量 GWh</th>
<th>峰值上浮 %</th><th>热浪</th></tr>
{ev_rows}
</table>
<h3>5.3 弹性外推</h3>
<div class="fig">
  <div class="legend"><span><i style="background:{C_CS}"></i>基准弹性 β=+5.08%/GW</span>
  <span><i style="background:{C_HW}"></i>高需求 β=+5.84%/GW</span>
  <span><i style="background:{C_EV}"></i>44 个事件小时</span></div>
  {svg_elas}
  <div class="cap">上浮 = (exp(β·缺口GW)−1)×100，44 个事件小时落点紧密贴基准曲线。
  中位缺口 2.06 GW → +11.0%；07-21 峰值 4.40 GW → +25.0% (高需求情景 +29.3%)。</div>
</div>
<h3>5.4 两个案例</h3>
<h3>案例 A · 07-13 热浪日：需求高峰 × 傍晚云系 = 全月最强价格冲击</h3>
<div class="fig">
  <div class="legend"><span><i style="background:{C_CS}"></i>晴空反事实</span>
  <span><i style="background:{C_EIA}"></i>EIA 实际</span>
  <span><i style="background:{C_DEM}"></i>全网需求 (右上角)</span></div>
  {svg_c13}
  <div class="cap">热浪峰值日 (需求 ~77.5 GW)。傍晚 20-23 UTC 云系过境，
  EIA 出力从 8.2 GW 跌至 3.7 GW，缺口 2.4~3.9 GW —— 恰逢晚高峰爬坡时段。
  交叉验证：实际辐照底模同小时自身降至 4.4 GW，确认云系真实；
  底模相对 EIA 的 +0.5~0.9 GW 系统性傍晚余差已被逐小时偏移吸收。
  峰值上浮 +21.9% (高需求弹性口径 +25.6%)。</div>
</div>
<h3>案例 B · 07-14 撒哈拉沙尘日：全月最长事件</h3>
<div class="fig">
  <div class="legend"><span><i style="background:{C_CS}"></i>晴空反事实</span>
  <span><i style="background:{C_EIA}"></i>EIA 实际</span></div>
  {svg_c14}
  <div class="cap">2022 年 7 月中旬撒哈拉沙尘带横跨墨西哥湾到达德州
  (2022 年沙尘过程显著抬升了德州湾岸全年 PM<sub>2.5</sub>)。
  沙尘衰减从午后持续到日落，19-23 UTC 五小时缺口 1.7~2.4 GW (10.4 GWh，
  全月第二长事件)。注意沙尘日"晴空反事实"本身也含气溶胶衰减的高估成分
  (Solis 默认 AOD 0.1)，该日缺口应视为上界 (§6)。</div>
</div>

<h2>6. 不确定性与边界</h2>
<ul>
<li><b>弹性外推跨年</b>：β 由 2025/2026 年 RTM 面板标定后外推至 2022 年市场，
隐含市场结构 (燃气边际机组、风光渗透率) 不变的假设。两年复验一致 (±7%) 提供间接支持，
但 2022 年 7 月恰逢热浪+低风 (风电出力低于常年的数日)，实际弹性可能偏向高需求情景值。</li>
<li><b>上浮为条件均值而非尾部</b>：β 给出的是小时层面的对数条件期望；
RTM 事件尾部 (稀缺定价 >$1000) 不在本框架内。$182/MWh 为 North 枢纽
<b>月均</b>批发电价，事件小时真实 RTM 波动远大于"锚×上浮%"的换算，
换算值仅作量级参考 (中位 +$20、最大 +$46/MWh)。</li>
<li><b>晴空反事实误差</b>：Solis 固定 AOD 0.1，沙尘/霾日反事实偏高 → 缺口为上界；
反事实峰值 10.4 GW vs EIA 峰值 9.7 GW (+7%)，缺口对晴空模型误差敏感，
逐小时偏移校准已消除系统性成分 (晴日缺口中位 67 MW)。</li>
<li><b>口径</b>：模型覆盖 56 座大站 10.66 GW (EIA 全网约 12 GW，89%)，
ILR 1.30 同时吸收了卫星辐照水平差与大站-全网效率差，标定量与被解释量
(2025 RTM 面板) 相互独立。需求代理 = EIA-930 全燃料出力之和 (2022-07 无 demand 字段)。</li>
<li><b>热浪残余</b>：07-18 极端日仍低估 4.55 GWh，44°C 峰值下组件温度模型
(Tcell = Tamb + POA/800×25) 与 soiling/逆变器降额可能有额外贡献，未闭合。</li>
</ul>

<h2>7. 产物索引</h2>
<table>
<tr><th>文件</th><th>说明</th></tr>
<tr><td class="mono">data/nsrdb/hrrr_t2m_2022-07.npz</td><td>HRRR 2m 温度 56 站 × 744h</td></tr>
<tr><td class="mono">data/uscrn/*.csv</td><td>USCRN 8 站 5min 地面实测 (辐照交叉验证)</td></tr>
<tr><td class="mono">data/nsrdb/ercot_pv_power_2022-07.csv</td><td>最终底模 vs EIA 小时出力</td></tr>
<tr><td class="mono">data/nsrdb/pv_drop_events_2022-07.csv</td><td>7 个骤降事件归因表</td></tr>
<tr><td class="mono">data/ercot/price_elasticity_2025.csv</td><td>2025/2026 弹性标定结果</td></tr>
<tr><td class="mono">data/nsrdb/pv_counterfactual_hourly_2022-07.csv</td><td>晴空反事实逐时表 (744h)</td></tr>
<tr><td class="mono">data/nsrdb/pv_event_price_impact_2022-07.csv</td><td>44 事件小时 × 电价冲击</td></tr>
<tr><td class="mono">skills/pv-power-model/references/nsrdb_pvlib_power.py</td><td>底模 (HRRR 温度 + ILR 1.30)</td></tr>
<tr><td class="mono">skills/pv-power-model/references/ilr_sweep_heatwave.py</td><td>ILR 四窗口扫描</td></tr>
<tr><td class="mono">skills/shortfall-price/references/identify_pv_drop_events_2022-07.py</td><td>骤降事件归因</td></tr>
<tr><td class="mono">skills/shortfall-price/references/calibrate_price_elasticity_2025.py</td><td>RTM 弹性面板标定</td></tr>
<tr><td class="mono">skills/shortfall-price/references/pv_event_price_impact_2022-07.py</td><td>缺口×冲击推演主脚本</td></tr>
</table>

<footer>
数据源：NREL NSRDB v3.2.2 (卫星辐照) · NOAA/NCEP HRRR 2m 温度 (Open-Meteo) ·
NOAA USCRN (地面基准) · EIA-930 (实际出力) · GridStatus/ERCOT (RTM 电价)。<br>
价格锚与热浪背景：
<a href="https://www.eia.gov/TODAYINENERGY/detail.php?id=55139">EIA Today in Energy #55139</a>
(2022-07 ERCOT North 月均 $182/MWh；热浪期风电显著偏低)；
2022 撒哈拉沙尘过程：
<a href="https://pubs.acs.org/doi/10.1021/acs.est.5c02205">Environ. Sci. Technol. (2025)</a> ·
<a href="https://www.aoml.noaa.gov/proj/saharan-air-layer/">NOAA AOML SAL</a>。<br>
生成时间 2026-09-27 · 全部时间为 UTC (EIA-930 已做 −1h 区间起点平移)
</footer>
</div>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已生成: {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
