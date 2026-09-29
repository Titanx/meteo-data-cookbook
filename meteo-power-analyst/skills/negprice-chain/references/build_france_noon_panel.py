# -*- coding: utf-8 -*-
"""法国正午(当地 10-16h)日面板 —— PS-042

用途: 把 PS-041 的支配性预测量"法国同窗口负价小时数"变成**可预报量**的第一步 ——
先把法国的**光伏 / 负荷 / 核电 / 剩余负荷**压到日尺度, 并与西班牙跨境日面板对齐。

口径(与 PS-040/041 保持一致):
  · 窗口 = **当地 10–16h**(Europe/Paris; 与 Europe/Madrid 同 UTC 偏移, 即同一物理时段)
  · 发电/负荷按窗口内**小时值求和**(MW → 窗口累计, 与 ES 面板 `solar_noon`/`load_noon` 同口径),
    价格取窗口内**均值/最小值**
  · 份额用**求和之比**(尺度无关): 光伏份额 = ΣSolar/ΣLoad; 核电话语权 = ΣNuclear/ΣLoad;
    "风光核总供给" = Σ(Nuclear+Solar+Wind)/ΣLoad = PS-042 的**区域过剩代理**
  · 日界 = 当地日; 输出索引为 tz-naive 当地日期, 便于与 ES 面板对齐

输入:  data/energy_charts/fr_power_hourly.csv, data/energy_charts/price_FR.csv,
       data/spain/spain_xborder_daily.csv
输出:  data/spain/france_noon_panel.csv
用法:  python scripts/analysis/build_france_noon_panel.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

EC = Path(r"c:\work\meteo\data\energy_charts")
SP = Path(r"c:\work\meteo\data\spain")
TZ = "Europe/Paris"
NOON = (10, 16)


def load_fr_power():
    df = pd.read_csv(EC / "fr_power_hourly.csv")
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    df = df.set_index("datetime_utc").sort_index()
    return df.tz_convert(TZ)


def load_fr_price():
    p = pd.read_csv(EC / "price_FR.csv")
    p["datetime_utc"] = pd.to_datetime(p["datetime_utc"], utc=True)
    return p.set_index("datetime_utc")["price_eur_mwh"].sort_index().tz_convert(TZ)


def main():
    pw = load_fr_power()
    pr = load_fr_price()

    noon_pw = pw[(pw.index.hour >= NOON[0]) & (pw.index.hour < NOON[1])]
    noon_pr = pr[(pr.index.hour >= NOON[0]) & (pr.index.hour < NOON[1])]

    g = noon_pw.copy()
    g["date"] = g.index.date
    agg = g.groupby("date")[["Solar", "Load", "Nuclear", "Residual load",
                             "Wind onshore", "Wind offshore"]].sum()
    agg["n_h"] = g.groupby("date").size()

    p = noon_pr.copy()
    p.index = pd.Index(p.index.date, name="date")
    pgh = p.groupby("date")
    agg["fr_price_noon"] = pgh.mean()
    agg["fr_min_noon"] = pgh.min()
    agg["fr_negh_noon"] = pgh.apply(lambda x: int((x < 0).sum()))

    dens = agg["Load"].where(agg["Load"] > 0)
    agg["fr_noon_ratio"] = agg["Solar"] / dens                     # 光伏份额
    agg["fr_nuclear_ratio"] = agg["Nuclear"] / dens                # 核电份额
    agg["fr_vre_ratio"] = (agg["Nuclear"] + agg["Solar"]              # 核+光(+风) 总供给覆盖
                           + agg["Wind onshore"] + agg["Wind offshore"]) / dens
    agg["fr_resload_ratio"] = agg["Residual load"] / dens          # 剩余负荷占比(越低=区域越过剩)

    out = agg.reset_index()
    out["date"] = pd.to_datetime(out["date"])
    out = out.set_index("date").sort_index()
    out.index.name = "date"

    xb = pd.read_csv(SP / "spain_xborder_daily.csv")
    xb["date"] = pd.to_datetime(xb["date"])
    xb = xb.set_index("date").sort_index()

    m = xb.join(out, how="left", rsuffix="_fr")
    m["dow"] = m.index.dayofweek
    m["is_weekend"] = (m["dow"] >= 5).astype(int)

    # 交叉自检: PS-041 面板已有的 FR 变量与本流程独立算出的 `_fr` 版本必须逐日一致
    # (两条管线都源自 price_FR.csv, 但 PS-041 在 Madrid 当地日流程里算, 这里用 Paris 窗口重算)
    for c in ["fr_negh_noon", "fr_price_noon", "fr_min_noon"]:
        a, b = m[c], m[c + "_fr"]
        ok = ~pd.isna(a) & ~pd.isna(b)
        bad = int((~np.isclose(a[ok], b[ok], atol=1e-9)).sum())
        assert bad == 0, "%s 逐日不一致: %d 天" % (c, bad)
        print("自检 %-14s 一致 (%d 日)" % (c, int(ok.sum())))
    m = m[[c for c in m.columns if not c.endswith("_fr")]]
    m.to_csv(SP / "france_noon_panel.csv")

    print("FR 小时序列: %d 小时 (%s ~ %s, %s)" % (len(pw), pw.index.min(), pw.index.max(), TZ))
    print("FR 正午聚合: %d 日 (%s ~ %s)" % (len(out), out.index.min().date(), out.index.max().date()))
    print("合并面板:   %d 日 × %d 列 → %s" % (len(m), m.shape[1], SP / "france_noon_panel.csv"))
    print("缺 FR 特征的日: %d" % int(m["fr_noon_ratio"].isna().sum()))

    print("\n逐年 FR 特征(正午窗口均值):")
    y = m.groupby(m.index.year).agg(
        n=("fr_negh_noon", "size"),
        fr_negh_noon=("fr_negh_noon", "mean"),
        fr_noon_ratio=("fr_noon_ratio", "mean"),
        fr_nuclear_ratio=("fr_nuclear_ratio", "mean"),
        fr_vre_ratio=("fr_vre_ratio", "mean"),
        es_noon_ratio=("noon_ratio", "mean"),
        es_negh=("negh", "mean"),
    )
    print(y.round(4).to_string())

    print("\nFR / ES 正午负价小时分位:")
    print(m[["fr_negh_noon", "negh_noon", "negh"]].describe().round(2).to_string())

    # 自检: FR 窗口负价小时(日) 与 PS-041 面板里的 fr_negh_noon 是否一致
    both = m[["fr_negh_noon", "fr_price_noon"]].dropna()
    print("\n自检: 面板 fr_negh_noon 覆盖 %d 日, 与 price_FR 口径一致(见上分位)" % len(both))


if __name__ == "__main__":
    main()
