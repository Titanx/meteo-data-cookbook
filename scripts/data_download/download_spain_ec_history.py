# -*- coding: utf-8 -*-
"""Energy-Charts 西班牙分技术发电 12 年历史下载 (2015-2026, 免注册)

用途: PS-039 —— 用 12 年历史建"负价爆发阈值"模型(需要 2015-2022 的光伏出力)。

要点:
  · 端点 `public_power?country=es` 一次可取整年; PS-037 已证 Energy-Charts ≡ ENTSO-E (r=1.000000)
  · 🔴 **分辨率随年份变化**: 2015-2022 返回**逐小时**, 2023 起返回 **15 分钟**
    ⇒ 必须先重采样到小时再求和, 否则 2023+ 的能量虚增 4 倍
    (自检: 2023 光伏按行求和 = 161.7 TWh, 重采样后 = 40.4 TWh, 与 PS-031 实测的 40.4 TWh 一致)
  · ⚠ 该端点**无独立负荷字段**(`/load` 端点 404), 且 Σproduction_types **不等于负荷**
    (含"跨境交易""抽蓄耗电"等, 2015 求和 686.9 TWh ≫ 西班牙年需求 ~250 TWh)
    ⇒ **负荷一律用 ENTSO-E A65 官方值**, 不用本文件反推

输出: data/energy_charts/es_public_power_{年}.json (+ 汇总 CSV)
用法: python scripts/data_download/download_spain_ec_history.py
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
YEARS = list(range(2015, 2027))
GEN_EXCLUDE = ("Cross border electricity trading", "Hydro pumped storage consumption")
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


def hourly(json_obj, name):
    """从 Energy-Charts 响应中取指定技术序列, 并重采样到小时"""
    d = json_obj
    data = None
    for p in d.get("production_types", []):
        if p.get("name") == name:
            data = p.get("data")
            break
    if data is None:
        return None
    s = pd.Series([float("nan") if x is None else float(x) for x in data],
                  index=pd.to_datetime(d["unix_seconds"], unit="s", utc=True), name=name)
    s = s[~s.index.duplicated()]
    return s.resample("1h").mean()


def main():
    rows = []
    for y in YEARS:
        end = "%d-12-31" % y if y < 2026 else "2026-09-30"
        f = OUT / ("es_public_power_%d.json" % y)
        if f.exists():
            j = json.loads(f.read_text(encoding="utf-8"))
            tag = "缓存"
        else:
            j = get("/public_power", country="es", start="%d-01-01" % y, end=end)
            f.write_text(json.dumps(j), encoding="utf-8")
            tag = "下载"
            time.sleep(3)

        types = {p["name"]: p["data"] for p in j.get("production_types", [])}
        raw_n = len(j.get("unix_seconds", []))
        sol = hourly(j, "Solar")
        gen_twh = 0.0
        for k in types:
            if k in GEN_EXCLUDE:
                continue
            hs = hourly(j, k)
            if hs is not None:
                gen_twh += hs.sum() / 1e6
        s_twh = sol.sum() / 1e6 if sol is not None else float("nan")
        s_max = sol.max() if sol is not None else float("nan")
        res = "15min" if raw_n > 9000 else "hourly"
        rows.append({"year": y, "n_raw": raw_n, "resolution": res, "n_hours": len(sol) if sol is not None else 0,
                     "solar_TWh": round(s_twh, 1), "solar_max_MW": round(s_max, 0),
                     "gen_TWh": round(gen_twh, 1)})
        print("[%d] %s %d 点(%s) → %d 小时 | 光伏 %.1f TWh 峰值 %.0f MW | 本地发电 %.1f TWh"
              % (y, tag, raw_n, res, rows[-1]["n_hours"], s_twh, s_max, gen_twh))

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "es_public_power_summary.csv", index=False)
    print("\n" + df.to_string(index=False))
    print("\n→ %s" % OUT)


if __name__ == "__main__":
    main()
