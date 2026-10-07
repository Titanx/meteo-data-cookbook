# -*- coding: utf-8 -*-
"""NCEI Storm Events 全量批量下载（1950-2026，3 产品）

源: https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/  (NOAA NCEI, 匿名)
产品: details(事件明细) / fatalities(伤亡) / locations(逐点路径)
命名: StormEvents_{product}-ftp_v1.0_d{YYYY}_c{SNAPSHOT}.csv.gz

要点:
  · 文件名含快照日 cYYYYMMDD —— 同一年会重发布, 清单里记录快照日, 便于追溯
  · 时间是**当地时**(details 带 CZ_TIMEZONE 列), 与 UTC 链路对齐需另行处理
  · 断点续传: 本地已存在且大小一致即跳过
  · 温和限速(4 并发 + 0.2s), 失败指数退避重试

用法:
  python skills/data-fetch-ground/references/download_storm_events.py
  python skills/data-fetch-ground/references/download_storm_events.py --products details --workers 4
输出:
  data/storm_events/<product>/<file>.csv.gz
  data/storm_events/storm_events_manifest.csv
"""
import argparse
import csv
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

BASE = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
DEFAULT_OUT = r"c:\work\meteo\data\storm_events"
FILE_RE = re.compile(
    r'href="(StormEvents_(details|fatalities|locations)-ftp_v1\.0_d(\d{4})_c(\d{8})\.csv\.gz)"')

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def list_remote():
    """返回 [(filename, product, year, snapshot)]"""
    req = urllib.request.Request(BASE, headers=UA)
    html = urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
    seen, out = set(), []
    for m in FILE_RE.finditer(html):
        name, prod, yr, snap = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        if name in seen:
            continue
        seen.add(name)
        out.append((name, prod, yr, snap))
    out.sort(key=lambda t: (t[1], t[2]))
    return out


def remote_size(name, retries=4):
    """HEAD 取远端字节数; 失败返回 -1"""
    for k in range(retries):
        try:
            req = urllib.request.Request(BASE + name, headers=UA, method="HEAD")
            with urllib.request.urlopen(req, timeout=60) as r:
                return int(r.headers.get("Content-Length", -1))
        except Exception:
            time.sleep(1.5 * (k + 1))
    return -1


def download_one(item, out_root):
    name, prod, yr, snap = item
    dest_dir = os.path.join(out_root, prod)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name)
    size = remote_size(name)
    if os.path.exists(dest) and size > 0 and os.path.getsize(dest) == size:
        return name, "skip", size
    time.sleep(0.2)
    for k in range(4):
        try:
            req = urllib.request.Request(BASE + name, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            got = os.path.getsize(dest)
            if size > 0 and got != size:
                raise IOError(f"size mismatch {got} != {size}")
            return name, "ok", got
        except Exception as e:
            if k == 3:
                return name, f"FAIL:{type(e).__name__}", os.path.getsize(dest) if os.path.exists(dest) else 0
            time.sleep(2.0 * (k + 1))
    return name, "FAIL", 0


def main():
    ap = argparse.ArgumentParser(description="NCEI Storm Events 全量下载")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--products", nargs="+", default=["details", "fatalities", "locations"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--years", nargs="+", type=int, default=None, help="只下指定年份")
    args = ap.parse_args()

    items = list_remote()
    if args.years:
        items = [t for t in items if t[2] in set(args.years)]
    items = [t for t in items if t[1] in args.products]
    if not items:
        print("未匹配到文件"); return 1

    yrs = sorted({t[2] for t in items})
    print("=" * 68)
    print(f"NCEI Storm Events 下载  |  产品: {args.products}")
    print(f"  文件数: {len(items)}  |  年份: {yrs[0]} ~ {yrs[-1]} ({len(yrs)} 年)")
    print(f"  并发: {args.workers}  |  输出: {args.out}")
    print("=" * 68)

    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(download_one, it, args.out): it for it in items}
        done = 0
        for f in as_completed(futs):
            name, status, size = f.result()
            results.append((name, status, size))
            done += 1
            if status.startswith("FAIL") or done % 25 == 0 or done == len(items):
                print(f"  [{done}/{len(items)}] {status:>12}  {name}  ({size/1e6:.2f} MB)")

    # 清单
    meta = {t[0]: t for t in items}
    os.makedirs(args.out, exist_ok=True)
    mf = os.path.join(args.out, "storm_events_manifest.csv")
    total = 0
    with open(mf, "w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(["product", "year", "snapshot", "filename", "bytes", "status", "downloaded_utc"])
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for name, status, size in sorted(results, key=lambda r: r[0]):
            _, prod, yr, snap = meta[name]
            total += size if status in ("ok", "skip") else 0
            w.writerow([prod, yr, snap, name, size, status, now])

    ok = sum(1 for r in results if r[1] in ("ok", "skip"))
    bad = [r for r in results if r[1] not in ("ok", "skip")]
    print("-" * 68)
    print(f"完成: {ok}/{len(items)} 成功, {len(bad)} 失败  |  合计 {total/1e6:.1f} MB  |  用时 {time.time()-t0:.0f}s")
    if bad:
        for n, s, _ in bad[:15]:
            print(f"  失败: {n}  ({s})")
    print(f"清单: {mf}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
