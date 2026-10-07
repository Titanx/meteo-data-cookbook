"""定向核验 ERCOT 关键区候选站 (带重试, 避开服务器抖动)
用法: python skills/data-fetch-ground/references/verify_sounding_stations.py
"""
import re
import ssl
import time
import urllib.parse
import urllib.request

BASE_URL = "http://weather.uwyo.edu/wsgi/sounding"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

CANDIDATES = [
    "72243", "72244", "72254", "72261", "72266", "72353", "72363", "72251",
]
DT = "2026-08-01 12:00:00"


def fetch(sid, dt, retries=4):
    params = urllib.parse.urlencode({
        "datetime": dt, "id": sid, "src": "UNKNOWN", "type": "TEXT:LIST"})
    for k in range(retries):
        try:
            req = urllib.request.Request(
                f"{BASE_URL}?{params}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            html = urllib.request.urlopen(req, timeout=60, context=SSL_CTX)
            html = html.read().decode("utf-8", errors="replace")
        except Exception as e:
            err = type(e).__name__
            time.sleep(3 * (k + 1))
            continue
        if len(html) < 500 or "<PRE>" not in html:
            time.sleep(3 * (k + 1))
            continue
        m_lat = re.search(r"Latitude:\s*(-?[\d.]+)", html)
        m_lon = re.search(r"Longitude:\s*(-?[\d.]+)", html)
        m_dcape = re.search(r"(?:^|\n)\s*DCAPE\s*\n\s*(-?[\d.]+)", html)
        return (f"lat={m_lat.group(1)} lon={m_lon.group(1)} "
                f"DCAPE={m_dcape.group(1) if m_dcape else 'n/a'}")
    return f"FAIL ({err})"


for sid in CANDIDATES:
    print(f"{sid}: {fetch(sid, DT)}", flush=True)
    time.sleep(2.0)
