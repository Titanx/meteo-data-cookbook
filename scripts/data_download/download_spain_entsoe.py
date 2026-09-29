# -*- coding: utf-8 -*-
"""
西班牙 ENTSO-E Transparency 数据下载（替代/补充 ESIOS）
======================================================
下载内容（西班牙半岛 bidding zone EIC = 10YES-REE------0）：
  A44  日前电价
  A75  分技术实际发电（processType=A16 实际值）
  A65  实际负荷

认证：.env 中的 ENTSOE_API_TOKEN（securityToken 查询参数）。
      申请流程见 test_entsoe_api.py 的提示，或 .knowledge/tech/processes/PS-036.md。
网络：本机对 web-api.tp.entsoe.eu 可达；如走代理，在 .env 加 ESIOS_PROXY=...

用法
  python download_spain_entsoe.py --check                  # 连通性/鉴权自检
  python download_spain_entsoe.py --start 2024-01 --end 2026-09
  python download_spain_entsoe.py --start 2025-01 --end 2025-12 --docs price_da,load

设计：按月分块 + 原始 XML 落盘缓存（重复运行自动跳过已下载月份），符合平台"避免冗余请求"的要求。
"""
import ssl
import sys
import io
import json
import zipfile
import argparse
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd

ROOT = Path(r"c:\work\meteo")
OUT_DIR = ROOT / "data" / "entsoe"
RAW_DIR = OUT_DIR / "raw"
API = "https://web-api.tp.entsoe.eu/api"
ES = "10YES-REE------0"

DOCS = {
    "price_da": dict(doc="A44", label="日前电价(EUR/MWh)",
                     extra=dict(in_Domain=ES, out_Domain=ES), kind="price"),
    "gen_by_type": dict(doc="A75", label="分技术实际发电(MW)",
                        extra=dict(processType="A16", in_Domain=ES), kind="gen"),
    "load": dict(doc="A65", label="实际负荷(MW)",
                 extra=dict(processType="A16", outBiddingZone_Domain=ES), kind="load"),
}

# 发电技术代码（IEC 62325 PSR type）
PSR = {
    "B01": "Biomass", "B02": "Lignite", "B03": "Coal-derived gas", "B04": "Fossil Gas",
    "B05": "Hard Coal", "B06": "Oil", "B07": "Oil Shale", "B08": "Peat",
    "B09": "Geothermal", "B10": "Pumped Hydro", "B11": "Hydro Run-of-river",
    "B12": "Hydro Reservoir", "B13": "Marine", "B14": "Nuclear", "B15": "Other Renewable",
    "B16": "Solar", "B17": "Waste", "B18": "Wind Offshore", "B19": "Wind Onshore",
    "B20": "Other", "B21": "AC Link", "B22": "DC Link", "B23": "Substation",
}

RES_MIN = {"PT1M": 1, "PT5M": 5, "PT15M": 15, "PT30M": 30, "PT60M": 60, "P1D": 1440}


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
TOKEN = ENV.get("ENTSOE_API_TOKEN")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
PROXY = ENV.get("PROXY") or ENV.get("HTTPS_PROXY") or ENV.get("https_proxy")
if PROXY:
    OPENER = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
        urllib.request.HTTPSHandler(context=CTX))
else:
    OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))


class AuthError(RuntimeError):
    pass


def api_get(params):
    q = dict(params)
    q["securityToken"] = TOKEN
    url = API + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={
        "User-Agent": "meteo-research/1.0", "Accept": "application/xml,text/xml,*/*"})
    try:
        with OPENER.open(req, timeout=90) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        if b"Acknowledgement_MarketDocument" in raw and e.code == 401:
            raise AuthError("HTTP 401：securityToken 缺失或无效。请按 PS-036 申请后写入 .env 的 ENTSOE_API_TOKEN。")
        raise RuntimeError("HTTP %s: %s" % (e.code, raw[:300].decode("utf-8", "replace")))


def maybe_unzip(raw):
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = [n for n in z.namelist() if n.lower().endswith(".xml")]
            if not name:
                raise RuntimeError("ZIP 内容无 XML: %s" % z.namelist()[:5])
            return z.read(name[0])
    return raw


def strip_ns(tag):
    return tag.split("}")[-1]


def parse_iec(raw):
    """把 Publication/GL_MarketDocument 解析成 (datetime_utc, psr_type, kind_value) 行"""
    root = ET.fromstring(maybe_unzip(raw))
    rows = []
    for ts in root:
        if strip_ns(ts.tag) != "TimeSeries":
            continue
        psr = None
        for ch in ts:
            if strip_ns(ch.tag) == "MktPSRType":
                for g in ch:
                    if strip_ns(g.tag) == "psrType":
                        psr = (g.text or "").strip()
        for per in ts:
            if strip_ns(per.tag) != "Period":
                continue
            start, res, points = None, "PT60M", []
            for ch in per:
                n = strip_ns(ch.tag)
                if n == "timeInterval":
                    for g in ch:
                        if strip_ns(g.tag) == "start":
                            start = g.text
                elif n == "resolution":
                    res = (ch.text or "PT60M").strip()
                elif n == "Point":
                    pos, val, vt = None, None, None
                    for g in ch:
                        gn = strip_ns(g.tag)
                        if gn == "position":
                            pos = int(g.text)
                        elif gn in ("quantity", "price.amount", "secondaryQuantity"):
                            val = float(g.text)
                            vt = gn
                    if pos is not None and val is not None:
                        points.append((pos, val, vt))
            if start is None or not points:
                continue
            t0 = pd.Timestamp(start).tz_convert("UTC")
            step = timedelta(minutes=RES_MIN.get(res, 60))
            for pos, val, vt in points:
                rows.append({
                    "datetime_utc": t0 + step * (pos - 1),
                    "psr_type": psr,
                    "value": val,
                    "value_tag": vt,
                })
    return pd.DataFrame(rows)


def ym_bounds(ym):
    """ENTSO-E 用 yyyymmddHHMM（本地布鲁塞尔时间）；月首 00:00 到次月首 00:00"""
    p = pd.Period(ym, freq="M")
    nxt = p + 1
    return "%s010000" % ym.replace("-", ""), "%s010000" % str(nxt).replace("-", "")


def fetch_month(key, ym):
    spec = DOCS[key]
    st, en = ym_bounds(ym)
    params = dict(documentType=spec["doc"], periodStart=st, periodEnd=en, **spec["extra"])
    raw = api_get(params)
    df = parse_iec(raw)
    if df.empty:
        return df, raw
    if spec["kind"] == "price":
        df = df.rename(columns={"value": "price_eur_mwh"})[["datetime_utc", "price_eur_mwh"]]
    elif spec["kind"] == "load":
        df = df.rename(columns={"value": "load_mw"})[["datetime_utc", "load_mw"]]
    else:
        df = df[(df["value_tag"] == "quantity")][["datetime_utc", "psr_type", "value"]]
        df = df.rename(columns={"value": "gen_mw"})
    return df.sort_values("datetime_utc").reset_index(drop=True), raw


def cmd_check():
    if not TOKEN:
        print("!! .env 未配置 ENTSOE_API_TOKEN")
        print("   申请：注册 transparency.entsoe.eu → 验证邮箱 →")
        print("        发邮件 transparency@entsoe.eu（主题 'RESTful API access'）→ My Account 生成 token")
        sys.exit(4)
    st, en = ym_bounds("2024-04")
    try:
        raw = api_get(dict(documentType="A44", in_Domain=ES, out_Domain=ES,
                           periodStart=st, periodEnd=en))
    except AuthError as e:
        print("!! %s" % e)
        sys.exit(4)
    df = parse_iec(raw)
    print("A44 2024-04 探针: %d 行" % len(df))
    print(df.head(3).to_string(index=False))
    print("✅ token 有效，API 可用")


def cmd_download(start, end, keys):
    if not TOKEN:
        print("!! .env 未配置 ENTSOE_API_TOKEN（申请流程见 --check 提示）")
        sys.exit(4)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    months = [str(p) for p in pd.period_range(start, end, freq="M")]
    print("月份范围: %s ~ %s (%d 个月)" % (months[0], months[-1], len(months)))
    for key in keys:
        if key not in DOCS:
            print("跳过未知文档: %s（可选 %s）" % (key, list(DOCS)))
            continue
        frames, got, skipped = [], 0, 0
        for ym in months:
            cache = RAW_DIR / ("%s_%s.xml" % (key, ym))
            pars = RAW_DIR / ("%s_%s.csv" % (key, ym))
            if pars.exists():
                frames.append(pd.read_csv(pars))
                skipped += 1
                continue
            try:
                df, raw = fetch_month(key, ym)
            except AuthError as e:
                print("!! %s" % e)
                sys.exit(4)
            cache.write_bytes(raw)
            if df.empty:
                print("  [%s] %s -> 空（该月可能无数据）" % (key, ym))
                continue
            df.to_csv(pars, index=False)
            frames.append(df)
            got += 1
            print("  [%s] %s -> %d 行" % (key, ym, len(df)))
        if frames:
            all_df = pd.concat(frames, ignore_index=True).drop_duplicates("datetime_utc")
            all_df = all_df.sort_values("datetime_utc").reset_index(drop=True)
            dst = OUT_DIR / ("%s.csv" % key)
            all_df.to_csv(dst, index=False)
            extra = ""
            if key == "gen_by_type":
                techs = sorted(all_df["psr_type"].dropna().unique())
                extra = " | 技术: %s" % ", ".join("%s(%s)" % (t, PSR.get(t, "?")) for t in techs)
            print("  => %s : %d 行 (新取 %d 月, 复用 %d 月)%s" %
                  (dst.name, len(all_df), got, skipped, extra))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--start", default="2024-01")
    ap.add_argument("--end", default="2026-09")
    ap.add_argument("--docs", default="all", help="逗号分隔: price_da,gen_by_type,load 或 all")
    a = ap.parse_args()
    if a.check:
        cmd_check()
        return
    keys = list(DOCS) if a.docs == "all" else [s.strip() for s in a.docs.split(",")]
    cmd_download(a.start, a.end, keys)


if __name__ == "__main__":
    main()
