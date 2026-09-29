# -*- coding: utf-8 -*-
"""Energy-Charts 法国分技术发电/负荷下载 (2023-2026, 免注册) —— PS-042

用途: PS-041 发现"法国同窗口负价小时数"是西班牙负价的**支配性预测量**(r=+0.620,
泊松强度 AUC 0.808→0.903), 但该变量是**同期观测**。PS-042 要把它建成**可预报量**,
第一步是取到法国的**光伏 / 负荷 / 核电 / 剩余负荷**逐小时序列。

要点:
  · 端点 `public_power?country=fr` 支持整年区间, 免注册
  · 🔴 **分辨率随年份变化** (实测: 2023 为 30min, 2026 为 10min) ⇒ **必须先重采样到小时**
    再求和/取均值, 否则能量与负荷会按行数虚增
  · 该国字段含 `Nuclear`(核电)、`Residual load`(剩余负荷 = 负荷 − 风光)、
    `Renewable share of load` 等, 与西班牙字段集不同 ⇒ 按名取值, 缺失即跳过
  · ⚠ `Cross border electricity trading` 是**泛边界合计**且符号未文档化, 本流程不使用

输出: data/energy_charts/fr_public_power_{年}.json (缓存) + fr_power_hourly.csv (小时化)
用法: python skills/data-fetch-power/references/download_france_ec_power.py
"""
import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(r"c:\work\meteo\data\energy_charts")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://api.energy-charts.info"
YEARS = [2023, 2024, 2025, 2026]
# 本流程需要的技术序列(其余如 Fossil/Biomass 不取, 保持产出精简)
KEEP = ["Solar", "Load", "Nuclear", "Residual load", "Wind onshore", "Wind offshore",
        "Hydro Run-of-River", "Hydro water reservoir"]
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(path, tries=5, **params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    delay = 4
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "meteo-research/1.0"})
            with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and k < tries - 1:
                print("      %d → 等待 %ds 重试" % (e.code, delay))
                time.sleep(delay)
                delay *= 2
                continue
            raise


def series_hourly(json_obj, name):
    """取指定技术序列并重采样到小时(先重采样再使用, 避免多分辨率下按行计数虚增)"""
    data = None
    for p in json_obj.get("production_types", []):
        if p.get("name") == name:
            data = p.get("data")
            break
    if data is None:
        return None
    s = pd.Series([float("nan") if x is None else float(x) for x in data],
                  index=pd.to_datetime(json_obj["unix_seconds"], unit="s", utc=True), name=name)
    s = s[~s.index.duplicated()]
    return s.resample("1h").mean()


def main():
    frames, rows = [], []
    for y in YEARS:
        end = "%d-12-31" % y if y < 2026 else "2026-09-30"
        f = OUT / ("fr_public_power_%d.json" % y)
        if f.exists():
            j = json.loads(f.read_text(encoding="utf-8"))
            tag = "缓存"
        else:
            j = get("/public_power", country="fr", start="%d-01-01" % y, end=end)
            f.write_text(json.dumps(j), encoding="utf-8")
            tag = "下载"
            time.sleep(3)

        raw_n = len(j.get("unix_seconds", []))
        cols = {}
        for k in KEEP:
            s = series_hourly(j, k)
            if s is not None:
                cols[k] = s
        if not cols:
            print("[%d] 无可用序列" % y)
            continue
        dfy = pd.DataFrame(cols)
        frames.append(dfy)
        # 分辨率由"原始点数 ÷ 小时数"反推 (逐年不同: 2023-2025 逐小时, 2026 15min)
        ratio = raw_n / max(len(dfy), 1)
        res = "hourly" if ratio < 1.5 else ("30min" if ratio < 3 else ("15min" if ratio < 5 else "10min"))
        rows.append({"year": y, "n_raw": raw_n, "resolution": res, "n_hours": len(dfy),
                     "solar_TWh": round(dfy["Solar"].sum() / 1e6, 1) if "Solar" in dfy else float("nan"),
                     "load_TWh": round(dfy["Load"].sum() / 1e6, 1) if "Load" in dfy else float("nan"),
                     "nuclear_TWh": round(dfy["Nuclear"].sum() / 1e6, 1) if "Nuclear" in dfy else float("nan"),
                     "solar_max_GW": round(dfy["Solar"].max() / 1e3, 1) if "Solar" in dfy else float("nan"),
                     "nuclear_max_GW": round(dfy["Nuclear"].max() / 1e3, 1) if "Nuclear" in dfy else float("nan")})
        print("[%d] %s %d 点(%s) → %d 小时 | 光伏 %.1f / 核电 %.1f / 负荷 %.1f TWh"
              % (y, tag, raw_n, res, len(dfy), rows[-1]["solar_TWh"], rows[-1]["nuclear_TWh"], rows[-1]["load_TWh"]))

    all_df = pd.concat(frames)
    all_df = all_df[~all_df.index.duplicated()].sort_index()
    all_df.index.name = "datetime_utc"
    all_df.to_csv(OUT / "fr_power_hourly.csv")
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "fr_power_summary.csv", index=False)
    print("\n" + summ.to_string(index=False))
    print("\n小时化序列: %s (%d 小时, %s ~ %s)"
          % (OUT / "fr_power_hourly.csv", len(all_df), all_df.index.min(), all_df.index.max()))


if __name__ == "__main__":
    main()
