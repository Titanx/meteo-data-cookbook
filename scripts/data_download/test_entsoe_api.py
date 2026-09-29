# -*- coding: utf-8 -*-
"""
ENTSO-E Transparency Platform 连通性 / 鉴权自检
================================================
用途：在拿到 security token 之前/之后，快速判断是不是"token 问题"。
  - 无 token 或 token 无效 → HTTP 401 + Acknowledgement_MarketDocument（reason code 999/…）
  - token 有效            → HTTP 200 + Publication_MarketDocument / GL_MarketDocument
  - 网络被墙 / WAF 拦截    → HTTP 403 + HTML（不是 XML）

读取 c:\\work\\meteo\\.env 的 ENTSOE_API_TOKEN（可含 ESIOS_PROXY 走代理）。

用法:
  python test_entsoe_api.py
"""
import ssl
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT = Path(r"c:\work\meteo")
API = "https://web-api.tp.entsoe.eu/api"
ES = "10YES-REE------0"          # 西班牙（半岛）bidding zone EIC
PORTAL = "https://transparency.entsoe.eu/"


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
    print("使用代理: %s" % PROXY)
else:
    OPENER = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "meteo-research/1.0",
        "Accept": "application/xml,text/xml,*/*",
    })
    try:
        with OPENER.open(req, timeout=45) as r:
            return r.status, r.headers.get("content-type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type", ""), e.read()
    except Exception as e:
        return None, "", repr(e).encode()


def reason(raw):
    """从 Acknowledgement XML 中提取 reason code / text"""
    try:
        t = raw.decode("utf-8", "replace")
        import re
        code = re.search(r"<(?:reason\.)?code>(\d+)</", t)
        text = re.search(r"<text>(.*?)</text>", t, re.S)
        return "reason=%s text=%s" % (code.group(1) if code else "?",
                                      (text.group(1).strip()[:120] if text else "?"))
    except Exception:
        return ""


def probe(label, params):
    q = dict(params)
    if TOKEN:
        q["securityToken"] = TOKEN
    url = API + "?" + urllib.parse.urlencode(q)
    st, ct, raw = get(url)
    if st is None:
        print("  %-28s ERR %s" % (label, raw[:120]))
        return st, ct, raw
    kind = "XML" if b"<?xml" in raw[:200] else ("HTML" if b"<html" in raw[:200].lower() else "?")
    note = ""
    if st == 200:
        note = "OK"
    elif b"Acknowledgement_MarketDocument" in raw:
        note = reason(raw)
    print("  %-28s HTTP %-4s ct=%-24s %s %s" % (label, st, ct[:24], kind, note))
    return st, ct, raw


print("=" * 82)
print("ENTSO-E Transparency API 自检   token=%s" % ("已配置" if TOKEN else "未配置"))
print("=" * 82)

print("\n[1] 门户可达性")
for u, lbl in [(PORTAL, "transparency.entsoe.eu"),
               ("https://keycloak.tp.entsoe.eu/realms/tp/.well-known/openid-configuration", "Keycloak(tp realm)")]:
    st, ct, raw = get(u)
    print("  %-28s HTTP %s" % (lbl, st))

print("\n[2] API 端点 + 鉴权")
COMMON = dict(documentType="A44", in_Domain=ES, out_Domain=ES,
              periodStart="202404290000", periodEnd="202404300000")
st, ct, raw = probe("A44 日前价", COMMON)
probe("A75 分技术实际发电", dict(documentType="A75", processType="A16", in_Domain=ES,
                                periodStart="202404290000", periodEnd="202404300000"))
probe("A65 实际负荷", dict(documentType="A65", processType="A16", outBiddingZone_Domain=ES,
                         periodStart="202404290000", periodEnd="202404300000"))

print("\n[3] 判定")
if st == 200:
    print("  ✅ token 有效，API 可用 → 直接跑 download_spain_entsoe.py")
elif st == 401 and b"Acknowledgement_MarketDocument" in raw:
    print("  ⚠ 端点可达、协议正常，但**缺 token 或 token 无效**。")
    print("    申请流程：注册 transparency.entsoe.eu → 验证邮箱 →")
    print("    发邮件至 transparency@entsoe.eu（主题 'RESTful API access'，正文写注册邮箱）→")
    print("    等待 ≤3 个工作日 → 登录后在 My Account 生成 security token →")
    print("    写入 .env:  ENTSOE_API_TOKEN=<你的token>")
    sys.exit(4)
elif st == 403:
    print("  ❌ HTTP 403（可能是 WAF/网络拦截，非鉴权问题）——参见 PF-013 的排查思路")
    sys.exit(3)
else:
    print("  ❓ 未预期的响应，见上方明细")
    sys.exit(2)

print("\n完成。")
