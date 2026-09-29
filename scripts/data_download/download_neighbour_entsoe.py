# -*- coding: utf-8 -*-
"""西班牙邻国价格与跨境物理流下载 (PS-041)

内容:
  · A44 法国日前价                     EIC 10YFR-RTE------C
  · A11 跨境物理流 ES→FR 与 FR→ES      (净出口 = ES→FR − FR→ES)

为什么要 A11 而不是 Energy-Charts 的 `Cross border electricity trading`:
  实测该 EC 序列是**泛边界合计净交易**(2016 +13.2 TWh 出口 / 2025 −9.3 TWh 进口),
  与 A11 的"净 ES→FR" 相关 r=0.80 但**水平不同号**(2026-08: EC 均值 −1655 MW vs A11 净 +589 MW)
  —— 因为西班牙还有 PT/MA/AD 等边界。要么看**逐边界**, 要么用它做总量代理, 不可混用。

设计要点(吸取 PS-039 的教训):
  · 按月缓存原始 XML + 解析 CSV
  · 🔴 合并表**始终按"全部已缓存月份"重建**(glob 全量), 而不是本次请求区间
    —— 否则补数批会把合并表截断(PS-039 §8-6)
  · A11 的 in_Domain/out_Domain 表示**方向**; 每方向一次请求

输出: data/entsoe/fr_price_da.csv, flow_es_fr.csv, flow_fr_es.csv (+ raw/ 月缓存)
用法: python scripts/data_download/download_neighbour_entsoe.py [--start 2023-01] [--end 2026-09]
"""
import argparse
import glob
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(r"c:\work\meteo")
sys.path.insert(0, str(ROOT / "scripts" / "data_download"))
import download_spain_entsoe as D  # noqa: E402

OUT = ROOT / "data" / "entsoe"
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

ES = "10YES-REE------0"
FR = "10YFR-RTE------C"
SLEEP = 2.5


def fetch_month_price(eic, ym):
    st, en = D.ym_bounds(ym)
    raw = D.api_get(dict(documentType="A44", in_Domain=eic, out_Domain=eic,
                         periodStart=st, periodEnd=en))
    df = D.parse_iec(raw)
    if df.empty:
        return df, raw
    if df["contract"].notna().any():
        df = df[df["contract"] == "A01"]
    df = (df.drop_duplicates("datetime_utc", keep="first")
            .rename(columns={"value": "price_eur_mwh"})[["datetime_utc", "price_eur_mwh"]])
    return df, raw


def fetch_month_flow(a, b, ym):
    st, en = D.ym_bounds(ym)
    raw = D.api_get(dict(documentType="A11", in_Domain=a, out_Domain=b,
                         periodStart=st, periodEnd=en))
    df = D.parse_iec(raw)
    if df.empty:
        return df, raw
    df = df[df["value_tag"] == "quantity"]
    df = (df.drop_duplicates("datetime_utc", keep="first")
            .rename(columns={"value": "flow_mw"})[["datetime_utc", "flow_mw"]])
    return df, raw


JOBS = {
    "fr_price_da": dict(kind="price", args=(FR,), label="A44 法国日前价"),
    "flow_es_fr": dict(kind="flow", args=(ES, FR), label="A11 ES→FR"),
    "flow_fr_es": dict(kind="flow", args=(FR, ES), label="A11 FR→ES"),
}


def cached_span(key):
    """按**全部已缓存月份**重建合并表(而非本次请求区间)"""
    fs = sorted(glob.glob(str(RAW / ("%s_*.csv" % key))))
    fr = []
    for f in fs:
        d = pd.read_csv(f)
        if d.empty:
            continue
        fr.append(d)
    if not fr:
        return None
    a = pd.concat(fr, ignore_index=True)
    a["datetime_utc"] = pd.to_datetime(a["datetime_utc"], utc=True).astype(str)
    a = a.drop_duplicates("datetime_utc").sort_values("datetime_utc").reset_index(drop=True)
    a.to_csv(OUT / ("%s.csv" % key), index=False)
    ms = sorted({"%s" % re.search(r"_(\d{4}-\d{2})", os.path.basename(f)).group(1) for f in fs})
    return ms, len(a), a["datetime_utc"].iloc[0], a["datetime_utc"].iloc[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01")
    ap.add_argument("--end", default="2026-09")
    a = ap.parse_args()
    months = [str(p) for p in pd.period_range(a.start, a.end, freq="M")]
    print("月份范围 %s ~ %s (%d 个月)" % (months[0], months[-1], len(months)))

    for key, spec in JOBS.items():
        got, reused, empty = 0, 0, 0
        for ym in months:
            xmlp = RAW / ("%s_%s.xml" % (key, ym))
            csvp = RAW / ("%s_%s.csv" % (key, ym))
            if csvp.exists():
                reused += 1
                continue
            try:
                df, raw = None, None
                for attempt in range(4):
                    try:
                        if spec["kind"] == "price":
                            df, raw = fetch_month_price(spec["args"][0], ym)
                        else:
                            df, raw = fetch_month_flow(spec["args"][0], spec["args"][1], ym)
                        break
                    except D.AuthError:
                        raise
                    except Exception as e:
                        # 599/5xx/网关超时 等瞬时错误 → 指数退避重试
                        wait = 5 * (2 ** attempt)
                        print("  [%s] %s 第%d次失败(%s) → 等 %ds 重试"
                              % (key, ym, attempt + 1, str(e)[:70], wait), flush=True)
                        if attempt == 3:
                            print("  [%s] %s 放弃" % (key, ym), flush=True)
                        time.sleep(wait)
            except D.AuthError as e:
                print("!! %s" % e, flush=True)
                return
            if df is None:
                continue
            xmlp.write_bytes(raw)
            if df.empty:
                empty += 1
                print("  [%s] %s -> 空" % (key, ym), flush=True)
            else:
                df.to_csv(csvp, index=False)
                got += 1
                print("  [%s] %s -> %d 行" % (key, ym, len(df)), flush=True)
            time.sleep(SLEEP)
        r = cached_span(key)
        print("  => %s : 新取 %d 月 / 复用 %d / 空 %d | 合并表 %s\n"
              % (key, got, reused, empty, ("%d 月 %d 行 (%s ~ %s)" % r) if r else "无"), flush=True)

    print("完成。")
    print("提示: A11 与 A44 在 2026 年为 15 分钟粒度, 聚合前须先重采样到小时。")


if __name__ == "__main__":
    main()
