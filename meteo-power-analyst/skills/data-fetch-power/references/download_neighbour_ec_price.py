# -*- coding: utf-8 -*-
"""西班牙邻国日前价下载 · Energy-Charts 价格端点 (PS-041)

为什么不用 ENTSO-E A44/A11 直取:
  实测该网关在连续请求后进入**限流/超时**(单月 A44 FR 反复 90s read timeout 或 HTTP 599
  "uu-gateway-router/connectTimeout"), 45 个月 × 3 序列 ≈ 135 次请求不可行;
  且 PT 的 EIC(10YPT-REN------*)全部返回空。
  ⇒ 改用 Energy-Charts `/price?bzn=..` (免注册, **支持整年区间**, PS-037 已证 EC ≡ ENTSO-E 逐位一致)。

实测要点:
  · `/price?bzn=ES|FR|PT` 均可用; 2023/2024 为小时, 2025-10 起为 15 分钟
  · **ES 与 PT 是同一个 MIBEL 单一价**(2026-08-01: ES 108.94 / PT 109.10 vs FR 100.74) ⇒ 真正有意义的外部耦合是 **ES–FR**
  · 连发请求会 429 ⇒ 逐年请求之间需 sleep + 退避

输出: data/energy_charts/price_{ES,FR,PT}_{年}.json + data/energy_charts/price_{ES,FR,PT}.csv
用法: python skills/data-fetch-power/references/download_neighbour_ec_price.py
"""
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(r"c:\work\meteo\data\energy_charts")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://api.energy-charts.info"
ZONES = ["ES", "FR", "PT"]
YEARS = [2023, 2024, 2025, 2026]
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(path, tries=5, **params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    delay = 20
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "meteo-research/1.0"})
            with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and k < tries - 1:
                print("      %d → 等 %ds 重试" % (e.code, delay), flush=True)
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except Exception as e:
            if k < tries - 1:
                print("      %s → 等 %ds 重试" % (str(e)[:60], delay), flush=True)
                time.sleep(delay)
                delay *= 2
                continue
            raise


def main():
    for z in ZONES:
        frames = []
        for y in YEARS:
            f = OUT / ("price_%s_%d.json" % (z, y))
            end = "%d-12-31" % y if y < 2026 else "2026-09-30"
            if f.exists():
                j = json.loads(f.read_text(encoding="utf-8"))
                tag = "缓存"
            else:
                j = get("/price", bzn=z, start="%d-01-01" % y, end=end)
                f.write_text(json.dumps(j), encoding="utf-8")
                tag = "下载"
                time.sleep(15)
            s = pd.Series([np.nan if x is None else float(x) for x in j["price"]],
                          index=pd.to_datetime(j["unix_seconds"], unit="s", utc=True))
            s = s[~s.index.duplicated()].sort_index()
            frames.append(s.rename("price_eur_mwh"))
            print("[%s %d] %s n=%d 非空 %d 均值 %.2f 最低 %.2f"
                  % (z, y, tag, len(s), int(s.notna().sum()), s.mean(), s.min()), flush=True)
        a = pd.concat(frames).sort_index()
        a = a[~a.index.duplicated()].resample("1h").mean()   # 15min → 小时
        a.index.name = "datetime_utc"
        a.reset_index().to_csv(OUT / ("price_%s.csv" % z), index=False)
        print("  => price_%s.csv: %d 小时 %s ~ %s\n"
              % (z, len(a), a.index.min(), a.index.max()), flush=True)

    # 一致性自检: EC 的 ES 价 vs ENTSO-E 官方 A44
    import glob
    fr = []
    for f in sorted(glob.glob(r"c:\work\meteo\data\entsoe\raw\price_da_202[3-6]-*.csv")):
        d = pd.read_csv(f)
        if d.empty:
            continue
        fr.append(pd.Series(d["price_eur_mwh"].values,
                            index=pd.to_datetime(d["datetime_utc"], utc=True)))
    off = pd.concat(fr).sort_index()
    off = off[~off.index.duplicated()].resample("1h").mean()
    ec = pd.read_csv(OUT / "price_ES.csv", parse_dates=["datetime_utc"]).set_index("datetime_utc")["price_eur_mwh"]
    m = pd.concat([ec.rename("ec"), off.rename("entsoe")], axis=1).dropna()
    print("[自检] EC ES 价 vs ENTSO-E 官方: 共同 %d 小时 r=%.6f MAE=%.3f 能量比=%.5f"
          % (len(m), m.ec.corr(m.entsoe), (m.ec - m.entsoe).abs().mean(),
             m.ec.abs().sum() / m.entsoe.abs().sum()))


if __name__ == "__main__":
    main()
