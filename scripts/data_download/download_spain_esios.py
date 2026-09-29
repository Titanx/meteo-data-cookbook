# -*- coding: utf-8 -*-
"""
西班牙 ESIOS API 下载：分技术实际出力 / 需求 / 电价（PS-029 §5 的落地）
=====================================================================
用途：把 PS-031/032/033/035 里用 Energy-Charts 代理的"实际分技术出力"，换成
      REE 官方 ESIOS 口径（更高频、含实时需求），用于校核与细化。

⚠ 先决条件
  1) .env 中需有 ESIOS_API_TOKEN（已申请）；本机网络被 REE 的 Imperva/Incapsula
     WAF 域名级拦截（见 PF-013），需在可访问 ree.es 的网络运行，或设代理：
        .env 加一行  ESIOS_PROXY=http://user:pass@host:port
  2) 指标 ID 与 geo_id 须**逐指标核验**：先跑 `--list indicators`（元数据）确认。

用法
  python download_spain_esios.py --check                      # 只做连通性+元数据核验
  python download_spain_esios.py --list                       # 打印线上指标清单(名称->id)
  python download_spain_esios.py --start 2024-01 --end 2026-09 # 逐月下载(可断点续传)

遵守 REE 的 responsible-use：按"月"缓存，已下载的月份默认跳过，不做重复/冗余请求。
"""
import ssl
import sys
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

import pandas as pd

ROOT = Path(r"c:\work\meteo")
OUT_DIR = ROOT / "data" / "esios"
RAW_DIR = OUT_DIR / "raw"
BASE = "https://api.esios.ree.es"

# ---- 指标表（用前务必以 --list / --check 复核；geo_id 逐指标核验）----
INDICATORS = {
    "price_da":  dict(id=600,  geo="3",    unit="EUR/MWh", label="日前/现货价(OMIE)"),
    "demand":    dict(id=1293, geo="8741", unit="MW",      label="实时需求(半岛)"),
    "solar_pv":  dict(id=1295, geo="8741", unit="MW",      label="实时光伏"),
    "wind":      dict(id=551,  geo="8741", unit="MW",      label="实时风电"),
    "hydro":     dict(id=546,  geo="8741", unit="MW",      label="实时水电"),
    "nuclear":   dict(id=549,  geo="8741", unit="MW",      label="实时核电"),
    "ccgt":      dict(id=550,  geo="8741", unit="MW",      label="实时联合循环"),
    "coal":      dict(id=547,  geo="8741", unit="MW",      label="实时煤电"),
}


def load_env(p):
    env = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


ENV = load_env(ROOT / ".env")
TOKEN = ENV.get("ESIOS_API_TOKEN")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PROXY = ENV.get("ESIOS_PROXY") or ENV.get("HTTPS_PROXY") or ENV.get("https_proxy")
if PROXY:
    OPENER = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
        urllib.request.HTTPSHandler(context=CTX))
else:
    OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))


class WafBlocked(RuntimeError):
    pass


def call(path, **params):
    if not TOKEN:
        raise RuntimeError("缺少 ESIOS_API_TOKEN（写入 .env）")
    url = BASE + path
    q = {k: v for k, v in params.items() if v is not None}
    if q:
        url += "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={
        "Authorization": 'Token token="%s"' % TOKEN,
        "Accept": "application/json",
        "Accept-Language": "es",
        "User-Agent": "meteo-research/1.0",
    })
    try:
        with OPENER.open(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if "_Incapsula" in body or "Incapsula" in body:
            raise WafBlocked(
                "HTTP %s 被 Imperva/Incapsula WAF 拦截（与 token 无关）。"
                "请在可访问 ree.es 的网络运行，或设置 ESIOS_PROXY 后重试。" % e.code)
        raise RuntimeError("HTTP %s: %s" % (e.code, body[:300]))


def fetch_indicator(iid, start, end, geo, time_trunc="hour"):
    st, body = call("/indicators/%s" % iid, start_date=start, end_date=end,
                    geo_ids=geo, time_trunc=time_trunc)
    vals = body.get("indicator", {}).get("values", [])
    if not vals:
        return pd.DataFrame(columns=["datetime_utc", "geo_id", "value"])
    df = pd.DataFrame([{
        "datetime_utc": v.get("datetime_utc"),
        "geo_id": v.get("geo_id"),
        "value": v.get("value"),
    } for v in vals])
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce", utc=True)
    return df.dropna(subset=["datetime_utc"]).sort_values("datetime_utc").reset_index(drop=True)


def months_between(start, end):
    """生成 (YYYY-MM) 列表"""
    s = pd.Period(start, freq="M")
    e = pd.Period(end, freq="M")
    return [str(p) for p in pd.period_range(s, e, freq="M")]


def iso_bounds(ym):
    """某月的 ISO8601 起止（欧洲马德里时区，含 DST 由本地时间表达）"""
    p = pd.Period(ym, freq="M")
    st = "%s-01T00:00:00+01:00" % ym
    last = p.days_in_month
    en = "%s-%02dT23:59:00+01:00" % (ym, last)
    return st, en


def cmd_list():
    st, body = call("/indicators")
    inds = body.get("indicators", body) if isinstance(body, dict) else body
    print("线上指标 %d 个（节选含关键词者）:" % len(inds))
    kw = ["demanda", "generaci", "eólica", "solar", "fotovolt", "precio", "mercado",
          "restricci", "vertido"]
    n = 0
    for it in inds:
        nm = (it.get("name") or "") + " " + (it.get("name_es") or "")
        if any(k.lower() in nm.lower() for k in kw):
            print("  %-7s %s" % (it.get("id"), nm.strip()[:100]))
            n += 1
    print("（命中 %d 个）" % n)


def cmd_check():
    print("连通性 + 指标元数据核验")
    for key, spec in INDICATORS.items():
        try:
            st, body = call("/indicators/%s" % spec["id"])
            ind = body.get("indicator", {})
            print("  %-9s id=%-5s geo=%-5s | %s / %s | trunc=%s | start=%s" % (
                key, spec["id"], spec["geo"], ind.get("name"), ind.get("name_es"),
                ind.get("time_trunc"), ind.get("start_date")))
        except WafBlocked as e:
            print("!! %s" % e)
            print("   在可访问 ree.es 的网络运行本脚本，或设置 ESIOS_PROXY 后重试。")
            sys.exit(3)
        except Exception as e:
            print("  %-9s id=%-5s -> 失败: %r" % (key, spec["id"], e))


def cmd_download(start, end, keys):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    months = months_between(start, end)
    print("目标月份: %s ~ %s (%d 个月)" % (months[0], months[-1], len(months)))
    for key in keys:
        if key not in INDICATORS:
            print("跳过未知指标: %s" % key)
            continue
        spec = INDICATORS[key]
        frames = []
        got, skipped = 0, 0
        for ym in months:
            cache = RAW_DIR / ("%s_%s.csv" % (key, ym))
            if cache.exists():
                skipped += 1
                frames.append(pd.read_csv(cache))
                continue
            st, en = iso_bounds(ym)
            try:
                df = fetch_indicator(spec["id"], st, en, spec["geo"])
            except WafBlocked as e:
                print("!! %s" % e)
                sys.exit(3)
            if df.empty:
                print("  [%s] %s -> 空" % (key, ym))
                continue
            df.to_csv(cache, index=False)
            frames.append(df)
            got += 1
            print("  [%s] %s -> %d 行" % (key, ym, len(df)))
        if frames:
            all_df = pd.concat(frames, ignore_index=True).drop_duplicates("datetime_utc")
            all_df = all_df.sort_values("datetime_utc").reset_index(drop=True)
            dst = OUT_DIR / ("%s.csv" % key)
            all_df.to_csv(dst, index=False)
            print("  => %s : %d 行 (新取 %d 月, 复用 %d 月)  %s" %
                  (dst.name, len(all_df), got, skipped, spec["unit"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只做连通性+元数据核验")
    ap.add_argument("--list", action="store_true", help="列出线上指标")
    ap.add_argument("--start", default="2024-01", help="起始月 YYYY-MM")
    ap.add_argument("--end", default="2026-09", help="结束月 YYYY-MM")
    ap.add_argument("--indicators", default="all", help="逗号分隔的键名，或 all")
    a = ap.parse_args()

    if a.list:
        cmd_list()
        return
    if a.check:
        cmd_check()
        return

    keys = list(INDICATORS) if a.indicators == "all" else [s.strip() for s in a.indicators.split(",")]
    cmd_download(a.start, a.end, keys)


if __name__ == "__main__":
    main()
