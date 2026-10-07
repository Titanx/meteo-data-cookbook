# -*- coding: utf-8 -*-
"""方向4报告图表数据生成 (DCAPE × 电价)

输入: data/ercot/dcape_daily_panel.csv, dcape_price_results.csv
输出: output/dcape_price/assets/charts_data.js (window.DCAPE_DATA)
用法: python skills/shortfall-price/references/make_dcape_charts_data.py
"""
import json
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\ercot"
OUT = r"c:\work\meteo\output\dcape_price\assets\charts_data.js"


def r3(v):
    return round(float(v), 3) if np.isfinite(v) else None


def main():
    df = pd.read_csv(os.path.join(D, "dcape_daily_panel.csv"), index_col=0, parse_dates=True)
    res = pd.read_csv(os.path.join(D, "dcape_price_results.csv"))

    # 1. 9月窗口时间线: dcape_m vs rtm_eve_max
    sep = df[(df.index >= "2026-09-07") & (df.index <= "2026-09-30")]
    timeline = {
        "day": [d.strftime("%m-%d") for d in sep.index],
        "dcape": [r3(v) for v in sep["dcape_m"]],
        "rtm_max": [r3(v) for v in sep["rtm_eve_max"]],
        "n200": [int(v) for v in sep["n200"]],
        "dcape_med_all": r3(df["dcape_m"].median()),
    }

    # 2. 散点: dcape_m vs ln(rtm_eve_max), 按年着色
    sc = df.dropna(subset=["dcape_m"])
    scatter = {
        "dcape": [r3(v) for v in sc["dcape_m"]],
        "ln_rtm": [r3(np.log(max(v, 1.0))) for v in sc["rtm_eve_max"]],
        "year": [int(y) for y in sc["year"]],
        "spike": [int(v) for v in sc["spike200"]],
    }

    # 3. 条件概率表 (年内三分位) — 从 results 提取
    cond = []
    for _, r in res[res["tag"].str.startswith("A4-")].iterrows():
        if str(r["tag"]).startswith("A4-P"):
            yr = 0
        else:
            try:
                yr = int(str(r["tag"]).split("-")[1])
            except ValueError:
                continue
        cond.append({"year": yr, "metric": r["metric"],
                     "p": float(r["value"]), "note": r["note"]})

    # 4. 机制: B1 相关系数 + B2 中介路径
    mech_corr = []
    for _, r in res[res["tag"] == "B1"].iterrows():
        mech_corr.append({"name": r["metric"].replace("ρ(dcape_m, ", "").replace(")", ""),
                          "rho": float(r["value"]), "note": r["note"]})
    mediation = []
    for _, r in res[res["tag"] == "B2"].iterrows():
        try:
            mediation.append({"model": r["metric"], "coef": float(r["value"]),
                              "se": float(str(r["note"]).split("SE ")[1].split(";")[0])})
        except (ValueError, IndexError):
            mediation.append({"model": r["metric"], "coef": float(r["value"]), "se": None})

    # 5. 站点 × hub 系数 (C2)
    station_hub = []
    for _, r in res[res["tag"] == "C2"].iterrows():
        cells = []
        for part in str(r["value"]).split():
            if ":" in part:
                hb, b = part.split(":")
                se = b.split("(")[1].rstrip(")") if "(" in b else ""
                cells.append({"hub": hb, "b": float(b.split("(")[0]), "se": float(se) if se else None})
        station_hub.append({"station": str(r["metric"]).split(" ")[0], "cells": cells,
                            "note": r["note"]})

    # 6. DAM 吸收 (A6)
    dam = []
    for _, r in res[res["tag"] == "A6"].iterrows():
        try:
            se = float(str(r["note"]).split("SE ")[1].split(";")[0])
        except (ValueError, IndexError):
            se = None
        dam.append({"model": r["metric"], "coef": float(r["value"]), "se": se})

    # 7. 事前 vs 同期 (A2 + A 头条 12Z 系数) — 主口径取池化 "A"，回退单年 "A2026"
    exante = []
    a_head = res[(res["tag"] == "A") & res["metric"].str.startswith("OLS ln(rtm_eve_max)")]
    if len(a_head) == 0:
        a_head = res[(res["tag"] == "A2026") & res["metric"].str.startswith("OLS ln(rtm_eve_max)")]
    if len(a_head):
        r = a_head.iloc[0]
        try:
            se = float(str(r["note"]).split("SE ")[1].split(";")[0])
        except (ValueError, IndexError):
            se = None
        exante.append({"model": "12Z 事前 (dcape_m 中位, 池化)", "coef": float(r["value"]), "se": se})
    for _, r in res[res["tag"] == "A2"].iterrows():
        try:
            se = float(str(r["note"]).split("SE ")[1].split(";")[0])
        except (ValueError, IndexError):
            se = None
        exante.append({"model": r["metric"], "coef": float(r["value"]), "se": se})

    # 8. 分小时弹性剖面 (A5h)
    hourly = []
    for _, r in res[res["tag"] == "A5h"].iterrows():
        try:
            se = float(str(r["note"]).split("SE ")[1].split(";")[0])
        except (ValueError, IndexError):
            se = None
        hourly.append({"hour": int(str(r["metric"]).split()[1]), "coef": float(r["value"]), "se": se})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    apx_rows = [{"tag": r["tag"], "metric": r["metric"],
                 "value": (float(r["value"]) if str(r["value"]).replace(".", "").replace("-", "").isdigit()
                           else r["value"]),
                 "note": r["note"]} for _, r in res.iterrows()]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.DCAPE_DATA = ")
        json.dump({"timeline": timeline, "scatter": scatter, "cond": cond,
                   "mech_corr": mech_corr, "mediation": mediation,
                   "station_hub": station_hub, "dam": dam,
                   "exante": exante, "hourly": hourly,
                   "apx_rows": apx_rows}, f, ensure_ascii=False)
    print(f"-> {OUT}")
    print(f"   timeline n={len(timeline['day'])}, scatter n={len(scatter['dcape'])}, "
          f"cond rows={len(cond)}, dam rows={len(dam)}")


if __name__ == "__main__":
    main()
