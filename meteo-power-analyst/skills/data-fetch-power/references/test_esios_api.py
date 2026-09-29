# -*- coding: utf-8 -*-
"""
ESIOS API 连通性验证（PS-029 §5 的落地）
--------------------------------------------------
- 从 c:\\work\\meteo\\.env 读取 ESIOS_API_TOKEN（该文件不入 git）
- 验证认证头格式：Authorization: Token token="<TOKEN>"
- 拉取常用指标，与 PS-029 的一手 OMIE 结果交叉校验（2024-04-29 日均 58.27 €/MWh）
- 遵守 REE 的 responsible-use：仅少量探测性请求，不做批量拉取

⚠ 已知网络问题（PF-013）：本机网络出口被 REE 的 Imperva/Incapsula WAF 在**域名级**拦截，
   对 api/www.esios.ree.es 与 www.ree.es 一律 403（连根路径都拦，带 token 与不带 token 返回
   同一张拦截页；有界面真实浏览器同样 403）⇒ 与 token 无关。
   解决办法：在可访问 ree.es 的网络运行本脚本，或设置代理后重试。
     在 .env 中加一行：ESIOS_PROXY=http://user:pass@host:port
     或设环境变量 HTTPS_PROXY。

用法: python test_esios_api.py
"""
import ssl
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT = Path(r"c:\work\meteo")
BASE = "https://api.esios.ree.es"


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
if not TOKEN:
    print("!! 未找到 ESIOS_API_TOKEN，请先写入 .env")
    sys.exit(1)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 可选代理（本机网络被 WAF 封锁时，经由可访问 ree.es 的代理/VPS 转发）
PROXY = ENV.get("ESIOS_PROXY") or ENV.get("HTTPS_PROXY") or ENV.get("https_proxy")
if PROXY:
    _opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}),
        urllib.request.HTTPSHandler(context=CTX))
    print("使用代理: %s" % PROXY)
else:
    _opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))

FMT = "quoted"  # 认证头格式，探测后决定


def is_waf_block(body):
    return isinstance(body, str) and ("_Incapsula" in body or "Incapsula" in body)


def call(path, token_fmt=None, **params):
    token_fmt = token_fmt or FMT
    url = BASE + path
    q = {k: v for k, v in params.items() if v is not None}
    if q:
        url += "?" + urllib.parse.urlencode(q)
    auth = ('Token token="%s"' % TOKEN) if token_fmt == "quoted" else ("Token token=%s" % TOKEN)
    req = urllib.request.Request(url, headers={
        "Authorization": auth,
        "Accept": "application/json",
        "Accept-Language": "es",
        "User-Agent": "meteo-research/1.0",
    })
    try:
        with _opener.open(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:
        return None, repr(e)


def summarize(values, unit="€/MWh"):
    if not values:
        return "（无数据）"
    vs = [v["value"] for v in values if v.get("value") is not None]
    if not vs:
        return "（无有效值）"
    import statistics
    geos = sorted({v.get("geo_id") for v in values})
    n_days = len({v["datetime"][:10] for v in values})
    return ("n=%d, 天数=%d, geo_ids=%s | 均值 %.2f, 最低 %.2f, 最高 %.2f %s"
            % (len(vs), n_days, geos, statistics.mean(vs), min(vs), max(vs), unit))


print("=" * 78)
print("ESIOS API 连通性验证  |  root = %s" % ROOT)
print("=" * 78)

# ---- 1) 认证格式探测 ----
print("\n[1] 认证头格式探测：GET /indicators/600（仅元数据）")
meta = None
blocked = False
for fmt in ("quoted", "bare"):
    st, body = call("/indicators/600", token_fmt=fmt)
    ok = isinstance(body, dict) and "indicator" in body
    print("    token_fmt=%-7s -> HTTP %s  %s" % (fmt, st, "OK" if ok else "FAIL"))
    if ok:
        FMT = fmt
        meta = body["indicator"]
        break
    if is_waf_block(body):
        blocked = True

if meta is None:
    print()
    if blocked:
        print("!! 判定：网络层被 REE 的 Imperva/Incapsula WAF 拦截（**不是 token 问题**）")
        print("   依据：根路径(无 token)与带 token 请求返回同一张 Incapsula 拦截页；")
        print("        有界面真实浏览器同样 403 ⇒ 域名级封锁，取决于网络出口 IP。")
        print("   处置：在可访问 ree.es 的网络运行本脚本；或设置代理后重试：")
        print("        在 .env 中加一行  ESIOS_PROXY=http://user:pass@host:port")
        sys.exit(3)
    print("!! 认证失败，终止。请检查 token 是否有效/是否已过期。")
    sys.exit(2)

print("    认证格式确认为: %s" % ("Token token=\"...\"" if FMT == "quoted" else "Token token=..."))
print("    指标名   : %s / %s" % (meta.get("name"), meta.get("name_es")))
print("    时间粒度 : %s" % meta.get("time_trunc"))
print("    可查起始 : %s" % meta.get("start_date"))
print("    单位     : %s" % meta.get("magnitude"))

# ---- 2) 日前价 600 交叉校验（2024-04-29） ----
print("\n[2] 指标 600（日前/现货价）— 与 PS-029 一手 OMIE 结果交叉校验")
st, body = call("/indicators/600",
                start_date="2024-04-29T00:00:00+02:00",
                end_date="2024-04-29T23:59:00+02:00",
                geo_ids="3", time_trunc="hour")
if isinstance(body, dict):
    print("    HTTP %s | %s" % (st, summarize(body["indicator"]["values"])))
    print("    PS-029 一手 OMIE（2024-04-29）: 日均 58.27, 最低 35.00(17h), 最高 102.26(08h)")
else:
    print("    HTTP %s | %s" % (st, str(body).replace("\n", " ")[:160]))

# ---- 3) 近实时指标抽样 ----
print("\n[3] 常用指标抽样（近一日 2026-09-28，hour 粒度）")
PROBES = [
    ("1293", "实时需求", "MW", "8741"),
    ("551",  "实时风电", "MW", "8741"),
    ("1295", "实时光伏", "MW", "8741"),
    ("600",  "日前价",   "€/MWh", "3"),
]
for iid, label, unit, geo in PROBES:
    st, body = call("/indicators/%s" % iid,
                    start_date="2026-09-28T00:00:00+02:00",
                    end_date="2026-09-28T23:59:00+02:00",
                    geo_ids=geo, time_trunc="hour")
    if isinstance(body, dict):
        print("    %-4s %-6s | HTTP %s | %s" % (iid, label, st, summarize(body["indicator"]["values"], unit)))
    else:
        print("    %-4s %-6s | HTTP %s | %s" % (iid, label, st, str(body).replace("\n", " ")[:160]))

print("\n完成。")
