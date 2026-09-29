# -*- coding: utf-8 -*-
"""西班牙负价 · 跨境结构日面板 (PS-041)

输入:
  · data/energy_charts/price_{ES,FR,PT}.csv   三区日前价 (EC /price, 2023-2026; 自检 r=0.999984 vs ENTSO-E 官方)
  · data/energy_charts/es_public_power_YYYY.json  ES 光伏 / 负荷 / **跨境电力交易合计净额**
输出:
  data/spain/spain_xborder_daily.csv

口径:
  · 全部先重采样到小时 (2025-10 起为 15 分钟)
  · **日界按 Europe/Madrid 当地日**; 正午窗口 = 当地 10-16h
  · 同时给出 UTC 日界的负价小时做一致性对照(负价集中在正午, 两者应几乎相同)
  · ⚠ 跨境**电力交易**用的是 Energy-Charts `Cross border electricity trading`, 它是
    **泛边界合计净额**(FR+PT+MA+AD), 不是单一 FR 边界; 单一边界需 ENTSO-E A11,
    实测该网关当日持续限流/超时(见 PS-041 局限), 故未纳入

用法: python skills/negprice-chain/references/build_spain_xborder_daily.py
"""
import glob
import json
import os

import numpy as np
import pandas as pd

EC = r"c:\work\meteo\data\energy_charts"
RAW = r"c:\work\meteo\data\entsoe\raw"
OUT = r"c:\work\meteo\data\spain\spain_xborder_daily.csv"
TZ = "Europe/Madrid"
NOON = (10, 16)


def ec_price(zone):
    s = pd.read_csv(os.path.join(EC, "price_%s.csv" % zone),
                    parse_dates=["datetime_utc"]).set_index("datetime_utc")["price_eur_mwh"]
    s.index = pd.to_datetime(s.index, utc=True)      # 统一为 tz-aware UTC
    return s.rename("p_%s" % zone.lower())


def ec_series(name, label):
    fr = []
    for y in range(2023, 2027):
        f = os.path.join(EC, "es_public_power_%d.json" % y)
        if not os.path.exists(f):
            continue
        j = json.loads(open(f, encoding="utf-8").read())
        data = None
        for p in j.get("production_types", []):
            if p.get("name") == name:
                data = p["data"]
        if data is None:
            continue
        s = pd.Series([np.nan if x is None else float(x) for x in data],
                      index=pd.to_datetime(j["unix_seconds"], unit="s", utc=True))
        fr.append(s[~s.index.duplicated()].resample("1h").mean().rename(label))
    return pd.concat(fr).sort_index()


def official_es_price():
    fr = []
    for f in sorted(glob.glob(os.path.join(RAW, "price_da_202[3-6]-*.csv"))):
        d = pd.read_csv(f)
        if d.empty:
            continue
        fr.append(pd.Series(d["price_eur_mwh"].values,
                            index=pd.to_datetime(d["datetime_utc"], utc=True)))
    s = pd.concat(fr).sort_index()
    return s[~s.index.duplicated()].resample("1h").mean().rename("p_es_off")


def main():
    print("读取小时序列 ...", flush=True)
    H = pd.concat([ec_price("ES"), ec_price("FR"), ec_price("PT"),
                   ec_series("Solar", "solar"), ec_series("Load", "load"),
                   ec_series("Cross border electricity trading", "xtrade"),
                   official_es_price()], axis=1)
    H = H[~H.index.duplicated()]
    print("小时面板 %s  %s ~ %s" % (H.shape, H.index.min(), H.index.max()), flush=True)
    print("  覆盖: " + ", ".join("%s=%d" % (c, H[c].notna().sum()) for c in H.columns), flush=True)

    m = H[["p_es", "p_es_off"]].dropna()
    print("\n[自检] EC 的 ES 价 vs ENTSO-E 官方 A44: %d 小时 r=%.6f MAE=%.3f €/MWh"
          % (len(m), m.p_es.corr(m.p_es_off), (m.p_es - m.p_es_off).abs().mean()), flush=True)

    print("\n[自检] 跨境交易序列符号定位（不预设符号, 用物理关系判定）")
    yr = H.groupby(H.index.year)["xtrade"].sum() / 1e6
    for y in [2023, 2024, 2025, 2026]:
        sub = H[H.index.year == y]
        print("   %d: 合计 %+7.2f TWh | corr(xtrade, ES价) = %+.3f"
              % (y, yr.get(y, np.nan), sub["xtrade"].corr(sub["p_es"])), flush=True)
    hh = H.dropna(subset=["xtrade", "p_es"])
    neg_h = hh.loc[hh["p_es"] < 0, "xtrade"]
    pos_h = hh.loc[hh["p_es"] >= 0, "xtrade"]
    print("   负价小时 xtrade 均值 %+8.1f MW (n=%d) | 非负价小时 %+8.1f MW (n=%d)"
          % (neg_h.mean(), len(neg_h), pos_h.mean(), len(pos_h)), flush=True)
    print("   ⇒ 负价(正午过剩)时应**出口最大**: 若 负价小时均值 > 非负价小时均值 则 **正号=净出口**, 否则 正号=净进口",
          flush=True)
    SIGN = 1.0 if neg_h.mean() > pos_h.mean() else -1.0
    print("   ⇒ 本序列判定: **正号 = %s**（后续 netexp = %.0f × xtrade）"
          % ("净出口" if SIGN > 0 else "净进口", SIGN), flush=True)

    # ---- UTC 日界下的负价小时(一致性对照) ----
    neg_utc = (H["p_es"] < 0).groupby(H.index.tz_convert("UTC").date).sum()

    # ---- 当地时 ----
    L = H.copy()
    L.index = L.index.tz_convert(TZ)
    d = L.index.normalize()
    g = L.groupby(d)

    out = pd.DataFrame(index=g.size().index)
    out["n_h"] = g["p_es"].count()
    out["negh"] = g["p_es"].apply(lambda x: int((x < 0).sum()))
    out["min_price"] = g["p_es"].min()
    out["mean_price"] = g["p_es"].mean()
    out["load_GWh"] = g["load"].sum() / 1e3
    out["solar_GWh"] = g["solar"].sum() / 1e3
    out["share_day"] = out["solar_GWh"] / out["load_GWh"].where(out["load_GWh"] > 0)
    out["xtrade_GWh"] = g["xtrade"].sum() / 1e3

    w = L[(L.index.hour >= NOON[0]) & (L.index.hour < NOON[1])]
    gw = w.groupby(w.index.normalize())
    out["n_h_noon"] = gw["p_es"].count()
    out["negh_noon"] = gw["p_es"].apply(lambda x: int((x < 0).sum()))
    out["solar_noon"] = gw["solar"].sum()
    out["load_noon"] = gw["load"].sum()
    out["noon_ratio"] = out["solar_noon"] / out["load_noon"].where(out["load_noon"] > 0)
    out["spread_noon"] = gw.apply(lambda x: float((x["p_es"] - x["p_fr"]).mean()))
    out["spread_pt_noon"] = gw.apply(lambda x: float((x["p_es"] - x["p_pt"]).mean()))
    out["fr_price_noon"] = gw["p_fr"].mean()
    out["es_price_noon"] = gw["p_es"].mean()
    # 有界(不外推爆炸)的 FR 侧特征: 窗口内 FR 负价小时数 ∈ [0,6] 与 FR 最低价
    out["fr_negh_noon"] = gw["p_fr"].apply(lambda x: int((x < 0).sum()))
    out["fr_min_noon"] = gw["p_fr"].min()
    out["pt_negh_noon"] = gw["p_pt"].apply(lambda x: int((x < 0).sum()))
    out["xtrade_noon"] = gw["xtrade"].mean() / 1e3          # GW 均值(符号见自检)
    out["netexp_noon"] = SIGN * out["xtrade_noon"]           # 统一为"正 = 净出口"
    out["netexp_GWh"] = SIGN * out["xtrade_GWh"]
    out["spread_day"] = g.apply(lambda x: float((x["p_es"] - x["p_fr"]).mean()))

    out.index = out.index.tz_localize(None)                 # 当地日期(naive), 便于与全日期轴对齐
    out.index.name = "date"
    out["year"] = out.index.year
    out["month"] = out.index.month
    out["doy"] = out.index.dayofyear
    out["negday"] = (out["negh"] > 0).astype(int)
    out["negh_utc"] = pd.Series(neg_utc).reindex([t.date() for t in out.index]).values

    mm = out[["negh", "negh_utc"]].dropna()
    print("\n[自检] 当地日 vs UTC日 负价小时: 相同 %.2f%% | 差异均值 %.2f h | 合计 %d vs %d"
          % ((mm["negh"] == mm["negh_utc"]).mean() * 100,
             (mm["negh"] - mm["negh_utc"]).abs().mean(),
             int(mm["negh"].sum()), int(mm["negh_utc"].sum())), flush=True)

    # ---- MIBEL 单一价检验: ES vs PT 对比 ES vs FR ----
    tt = out[["spread_pt_noon", "spread_noon", "fr_price_noon", "es_price_noon"]].dropna()
    print("\n[自检] MIBEL 单一价: |ES−PT| 中位 %.2f / 均值 %.2f €/MWh | |ES−FR| 中位 %.2f / 均值 %.2f"
          % (tt["spread_pt_noon"].abs().median(), tt["spread_pt_noon"].abs().mean(),
             tt["spread_noon"].abs().median(), tt["spread_noon"].abs().mean()), flush=True)
    print("   ⇒ |ES−PT| ≪ |ES−FR| ⇒ 伊比利亚为单一价(同年同小时同价), 真正的外部耦合是 **ES–FR**", flush=True)

    full = pd.date_range("2023-01-01", "2026-09-29", freq="D")
    out = out.reindex(full)
    out.index.name = "date"
    out.reset_index().to_csv(OUT, index=False)
    print("\n→ %s (%d 日)" % (OUT, len(out)), flush=True)
    print("覆盖: " + ", ".join("%s=%d" % (c, out[c].notna().sum())
                              for c in ["negh", "noon_ratio", "spread_noon", "netexp_noon"]), flush=True)

    t = out.dropna(subset=["negh"])
    g2 = t.groupby("year").agg(日数=("negh", "size"), 负价日=("negday", "sum"), 负价h=("negh", "sum"),
                               午比中位=("noon_ratio", "median"), 价差中位=("spread_noon", "median"),
                               FR价中位=("fr_price_noon", "median"), 净出口均值=("netexp_noon", "mean"))
    g2["负价日率%"] = (g2["负价日"] / g2["日数"] * 100).round(1)
    g2["午比中位"] = (g2["午比中位"] * 100).round(1)
    print(g2.round(2).to_string(), flush=True)


if __name__ == "__main__":
    main()
