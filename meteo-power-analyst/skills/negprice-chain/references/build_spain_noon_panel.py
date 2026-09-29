# -*- coding: utf-8 -*-
"""西班牙"正午窗口"份额面板构建 (PS-040)

动机: PS-039 证明负价由"月度光伏份额"阈值驱动, 但**月度聚合掩盖了正午结构**——
      负价几乎只出现在正午光伏过剩的那几个小时。本流程把驱动量换成
      **当地时间正午窗口的 光伏/负荷 比**（下称"正午份额"）。

输入:
  · data/energy_charts/es_public_power_YYYY.json   同时含 `Solar` 与 `Load` 两个序列
    （⚠ PS-039 曾误记"该端点无负荷字段"——实测 `Load` 存在, 且 2015-2022 年能量与
      ENTSO-E A65 **完全一致**, 见自检输出。故本流程单源即可, 无需跨源对齐）
  · data/entsoe/raw/load_YYYY-MM.csv               ENTSO-E A65（仅用于一致性自检）
输出:
  data/spain/spain_noon_panel.csv   逐月: 正午窗口(9-17/10-16/11-15)的光伏TWh、负荷TWh、份额

要点:
  · 分辨率随年份变(2015-2022 小时 / 2023 起 15 分钟) ⇒ 一律先重采样到小时
  · 窗口按 **Europe/Madrid 当地时** 取, 因此必须先 tz_convert 再筛小时(夏令时自动处理)
  · Energy-Charts 的 start/end 按当地时间解释, 跨年请求会带回上一年最后 1 小时 ⇒ 拼接后按索引去重
用法: python skills/negprice-chain/references/build_spain_noon_panel.py
"""
import glob
import json
import os

import numpy as np
import pandas as pd

EC = r"c:\work\meteo\data\energy_charts"
RAW = r"c:\work\meteo\data\entsoe\raw"
LONG = r"c:\work\meteo\data\spain\spain_long_panel.csv"
OUT = r"c:\work\meteo\data\spain\spain_noon_panel.csv"

TZ = "Europe/Madrid"
WINDOWS = [(9, 17), (10, 16), (11, 15)]


def pick(j, name):
    """取 Energy-Charts 响应中的某条序列(UTC 索引, 未重采样)"""
    for p in j.get("production_types", []):
        if p.get("name") == name:
            s = pd.Series([np.nan if x is None else float(x) for x in p["data"]],
                          index=pd.to_datetime(j["unix_seconds"], unit="s", utc=True))
            return s[~s.index.duplicated()].sort_index()
    return None


def ec_hourly():
    """拼接 12 年 JSON → 逐小时 Solar / Load（先重采样到小时再拼接, 保证口径一致）"""
    frames = []
    for y in range(2015, 2027):
        f = os.path.join(EC, "es_public_power_%d.json" % y)
        if not os.path.exists(f):
            continue
        j = json.loads(open(f, encoding="utf-8").read())
        d = pd.DataFrame({"solar": pick(j, "Solar"), "load": pick(j, "Load")})
        if d["solar"].isna().all() or d["load"].isna().all():
            print("  !! %d 缺 Solar/Load, 跳过" % y)
            continue
        d = d.resample("1h").mean()          # 2023+ 的 15min → 小时
        frames.append(d)
        print("  [%d] %d 小时 | 光伏 %.1f TWh 负荷 %.1f TWh"
              % (y, len(d), d["solar"].sum() / 1e6, d["load"].sum() / 1e6))
    E = pd.concat(frames).sort_index()
    E = E[~E.index.duplicated(keep="first")]     # 跨年请求重复的小时
    return E


def entsoe_load_hourly():
    """ENTSO-E A65 逐小时（用于一致性自检）"""
    fr = []
    for f in sorted(glob.glob(os.path.join(RAW, "load_*.csv"))):
        d = pd.read_csv(f)
        if d.empty or "load_mw" not in d.columns:
            continue
        s = pd.Series(d["load_mw"].values,
                      index=pd.to_datetime(d["datetime_utc"], utc=True))
        fr.append(s)
    L = pd.concat(fr).sort_index()
    L = L[~L.index.duplicated()]
    L = L[L > 0]                                  # ENTSO-E 用 0 表示缺测
    return L.resample("1h").mean()


def entsoe_price_hourly():
    """ENTSO-E A44 日前价 逐小时（用于统计正午窗口内的负价小时占比）"""
    fr = []
    for f in sorted(glob.glob(os.path.join(RAW, "price_da_*.csv"))):
        d = pd.read_csv(f)
        if d.empty or "price_eur_mwh" not in d.columns:
            continue
        s = pd.Series(d["price_eur_mwh"].values,
                      index=pd.to_datetime(d["datetime_utc"], utc=True))
        fr.append(s)
    P = pd.concat(fr).sort_index()
    P = P[~P.index.duplicated()]
    return P.resample("1h").mean()


def main():
    print("读取 Energy-Charts 12 年 Solar + Load ...")
    E = ec_hourly()
    print("合并小时序列: %d 小时, %s ~ %s" % (len(E), E.index.min(), E.index.max()))

    # ---- 自检: Energy-Charts Load vs ENTSO-E A65 ----
    L = entsoe_load_hourly()
    m = pd.concat([E["load"].rename("ec"), L.rename("entsoe")], axis=1).dropna()
    print("\n[自检] EC `Load` vs ENTSO-E A65: 共同 %d 小时 | r=%.6f | 能量比=%.6f | MAE=%.1f MW"
          % (len(m), m.ec.corr(m.entsoe), m.ec.sum() / m.entsoe.sum(),
             (m.ec - m.entsoe).abs().mean()))
    for y in (2015, 2020, 2025):
        mm = m[m.index.year == y]
        print("       %d: EC %.1f TWh vs ENTSO-E %.1f TWh"
              % (y, mm.ec.sum() / 1e6, mm.entsoe.sum() / 1e6))

    # ---- 换算到当地时, 取正午窗口 ----
    idx = E.index.tz_convert(TZ)
    E = E.set_axis(idx)
    print("\n当地时索引: %s ~ %s (%s)" % (E.index[0], E.index[-1], TZ))

    rows = {}
    for a, b in WINDOWS:
        w = E[(E.index.hour >= a) & (E.index.hour < b)]
        g = w.groupby([w.index.year, w.index.month])
        s = g["solar"].sum() / 1e6
        l = g["load"].sum() / 1e6
        n = g["solar"].size()
        tag = "%d%d" % (a, b)
        for k in s.index:
            ym = "%04d-%02d" % k
            r = rows.setdefault(ym, {})
            r["n_h_w%d_%d" % (a, b)] = int(n.loc[k])
            r["noon_solar_TWh_%d_%d" % (a, b)] = float(s.loc[k])
            r["noon_load_TWh_%d_%d" % (a, b)] = float(l.loc[k])
            r["noon_share_%d_%d" % (a, b)] = float(s.loc[k] / l.loc[k]) if l.loc[k] else np.nan

    # ---- 正午窗口(10-16h 当地时)内的负价小时与占比 ----
    #     用于给"线性阈值"之外提供一个**天然饱和**的目标(窗口负价小时占比 ∈ [0,1])
    P = entsoe_price_hourly().tz_convert(TZ)
    w = P[(P.index.hour >= 10) & (P.index.hour < 16)]
    t = pd.DataFrame({"p": w})
    t["ok"] = t["p"].notna().astype(int)
    t["neg"] = (t["p"] < 0).astype(int)
    gg = t.groupby([t.index.year, t.index.month]).sum(numeric_only=True)
    for k in gg.index:
        ym = "%04d-%02d" % k
        r = rows.setdefault(ym, {})
        ok, ng = int(gg.loc[k, "ok"]), int(gg.loc[k, "neg"])
        r["n_noon_h"] = ok
        r["neg_noon_h"] = ng
        r["noon_neg_frac"] = (ng / ok) if ok else np.nan
    p = pd.DataFrame([{"ym": k, **v} for k, v in rows.items()]).set_index("ym").sort_index()
    print("\n正午窗口(10-16h)负价统计: 覆盖 %d 月 | 负价小时合计 %d h"
          % (int(p["neg_noon_h"].notna().sum()), int(p["neg_noon_h"].sum())))

    # ---- 并入负价小时(来自 PS-039 长面板) 便于直接建模 ----
    lp = pd.read_csv(LONG).set_index("ym")
    p["neg_h"] = lp["neg_h"]
    p["solar_share"] = lp["solar_share"]
    p["load_TWh"] = lp["load_TWh"]
    p["solar_TWh"] = lp["solar_TWh"]

    full = pd.period_range("2015-01", "2026-09", freq="M").astype(str)
    p = p.reindex(full)
    p.index.name = "ym"
    p.reset_index().to_csv(OUT, index=False)
    print("\n→ %s  (%d 月, 缺 %d)" % (OUT, len(p), int(p["noon_share_10_16"].isna().sum())))

    # ---- 概览 ----
    print("\n正午份额(10-16h) 年度均值 %:")
    t = p[p["noon_share_10_16"].notna()].copy()
    t["year"] = [int(x[:4]) for x in t.index]
    g = t.groupby("year").agg(午前份额=("noon_share_10_16", lambda x: x.mean() * 100),
                              全天份额=("solar_share", lambda x: x.mean() * 100),
                              负价h=("neg_h", "sum"))
    print(g.round(1).to_string())
    print("\n窗口敏感性(全样本 正午份额 vs 负价h 的相关系数):")
    for c in ["noon_share_9_17", "noon_share_10_16", "noon_share_11_15"]:
        tt = p[[c, "neg_h"]].dropna()
        print("  %-9s r=%.4f (n=%d)" % (c.replace("noon_share_", ""), tt[c].corr(tt["neg_h"]), len(tt)))


if __name__ == "__main__":
    main()
