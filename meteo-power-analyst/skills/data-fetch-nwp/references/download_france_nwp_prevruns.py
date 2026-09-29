# -*- coding: utf-8 -*-
"""法国光伏代表点位的 NWP 预报下载(Open-Meteo previous-runs, D-1~D-7) —— PS-043

用途: PS-042 证明"用气候学代理把法国通道事前化"不带来增量技能。本流程改用**真实 NWP 预报**,
      检验短期(D-1~D-7)能否恢复技能 —— 因此必须取到**带 lead 的历史预报**, 而不是分析场。

关键点:
  · 端点 `previous-runs-api.open-meteo.com/v1/forecast`, 变量后缀 `_previous_dayN` (N=1..7)
  · 🔴 **必须显式指定 `models=`**: 不指定(或 best_match)时 previous-runs 全为 null;
    实测 `ecmwf_ifs025` 的 D1~D7 完整, `icon_seamless`/`meteofrance_seamless` 只有 D1、`gfs_seamless` 部分
  · 🔴 **归档起点 ≈ 2024-07-01**: 2024-01 及以前全部为 null(实测逐模式); D1~D7 覆盖 2024-07~至今
  · `start_date/end_date` 与 `past_days/forecast_days` **不可混用**(混用返回 HTTP 400)
  · 一次请求可取 14 个变量 × 180 天; 分块缓存(断点续传)

输出: data/openmeteo_nwp_france/fr_nwp_prevruns_{chunk}.npz (ghi/t2m 形状 [7 lead, N hub, T hour])
      + 汇总 data/openmeteo_nwp_france/fr_nwp_meta.csv
用法: python skills/data-fetch-nwp/references/download_france_nwp_prevruns.py
"""
import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(r"c:\work\meteo\data\openmeteo_nwp_france")
OUT.mkdir(parents=True, exist_ok=True)
HUBS = Path(r"c:\work\meteo\data\gem\france_solar_hubs_2024.csv")
MODEL = "ecmwf_ifs025"
LEADS = list(range(1, 8))
START, END = "2024-07-01", "2026-09-29"
CHUNK_DAYS = 180
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
VARS = (["shortwave_radiation_previous_day%d" % k for k in LEADS] +
        ["temperature_2m_previous_day%d" % k for k in LEADS])


def get(url, tries=5):
    delay = 8
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "meteo-research/1.0"})
            with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and k < tries - 1:
                print("      %d → 等待 %ds 重试" % (e.code, delay))
                time.sleep(delay)
                delay *= 2
                continue
            raise


def chunks():
    s = pd.Timestamp(START)
    e = pd.Timestamp(END)
    out = []
    while s <= e:
        t = min(s + pd.Timedelta(days=CHUNK_DAYS - 1), e)
        out.append((s.strftime("%Y-%m-%d"), t.strftime("%Y-%m-%d")))
        s = t + pd.Timedelta(days=1)
    return out


def main():
    hubs = pd.read_csv(HUBS)
    print("法国代表点位 %d 个 (覆盖 GEM operating 装机 %.1f%%)"
          % (len(hubs), 100 * hubs["share"].sum()))
    rows, ref_time = [], None
    for a, b in chunks():
        f = OUT / ("fr_nwp_prevruns_%s_%s.npz" % (a, b))
        if f.exists():
            z = np.load(f)
            ghi, t2m, tt = z["ghi"], z["t2m"], z["time"]
            print("[%s ~ %s] 缓存: %s  %d hub × %d 小时" % (a, b, ghi.shape, ghi.shape[1], ghi.shape[2]))
        else:
            ghi = np.full((len(LEADS), len(hubs), 0), np.nan, dtype=np.float32)
            t2m = np.full((len(LEADS), len(hubs), 0), np.nan, dtype=np.float32)
            tt = None
            G, T = [], []
            for i, h in hubs.iterrows():
                q = dict(latitude=h["lat"], longitude=h["lon"], start_date=a, end_date=b,
                         timezone="UTC", hourly=",".join(VARS), models=MODEL)
                j = get("https://previous-runs-api.open-meteo.com/v1/forecast?" +
                        urllib.parse.urlencode(q))
                hh = j["hourly"]
                if tt is None:
                    tt = np.array(pd.to_datetime(hh["time"]).astype("datetime64[ns]"))
                g = np.array([[np.nan if v is None else float(v)
                               for v in hh[vn]] for vn in VARS[:len(LEADS)]], dtype=np.float32)
                t = np.array([[np.nan if v is None else float(v)
                               for v in hh[vn]] for vn in VARS[len(LEADS):]], dtype=np.float32)
                G.append(g)
                T.append(t)
                time.sleep(1.2)
            ghi = np.stack(G, axis=1)   # [lead, hub, hour]
            t2m = np.stack(T, axis=1)
            np.savez_compressed(f, ghi=ghi, t2m=t2m, time=tt)
            print("[%s ~ %s] 下载: %s  %d hub × %d 小时" % (a, b, ghi.shape, ghi.shape[1], ghi.shape[2]))
        cov = float(np.isfinite(ghi).mean())
        rows.append({"chunk": "%s~%s" % (a, b), "hub": ghi.shape[1], "hour": ghi.shape[2],
                     "ghi_cov": round(cov, 5),
                     "d1_cov": round(float(np.isfinite(ghi[0]).mean()), 4),
                     "d7_cov": round(float(np.isfinite(ghi[6]).mean()), 4),
                     "t2m_cov": round(float(np.isfinite(t2m).mean()), 4)})
        if ref_time is None:
            ref_time = tt
        time.sleep(2)

    meta = pd.DataFrame(rows)
    meta.to_csv(OUT / "fr_nwp_meta.csv", index=False)
    print("\n" + meta.to_string(index=False))
    print("\n注意: 覆盖率 <1 的部分是 previous-runs 归档起点(≈2024-07-01)之前的空档")
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
