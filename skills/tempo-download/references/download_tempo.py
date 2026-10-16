#!/usr/bin/env python3
"""TEMPO (Earthdata) 下载脚本。

用法 (PowerShell):
    python skills/tempo-download/references/download_tempo.py \
        --short-name TEMPO_NO2_L2 --start 2026-01-01 --end 2026-01-01 \
        --out data/asdc/tempo --limit 2

凭证: data/asdc/earthdata_token.txt (存 NASA Earthdata Bearer token, 已被 git 忽略)
"""
import argparse
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TOKEN_FILE = os.path.join(ROOT, "data", "asdc", "earthdata_token.txt")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def load_token():
    if not os.path.exists(TOKEN_FILE):
        sys.exit(f"[错误] 未找到令牌文件 {TOKEN_FILE}; 先去 urs.earthdata.nasa.gov 生成 Personal Access Token")
    return open(TOKEN_FILE, "r", encoding="utf-8-sig").read().strip()


def hered(url, token, method="GET"):
    """带 token 鉴权的请求; 返回 (status, 字节内容)。"""
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    for k, v in UA.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()


def cmr_search(short_name, start, end, page_size=10, token=None):
    """CMR 目录查询, 返回真实数据文件(list与绑定数据盘)。"""
    params = {
        "short_name": short_name,
        "page_size": page_size,
        "temporal[]": f"{start}T00:00:00Z,{end}T23:59:59Z",
    }
    url = "https://cmr.earthdata.nasa.gov/search/granules.json?" + urllib.parse.urlencode(params)
    if token:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        for k, v in UA.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=60) as r:
            blob = r.read()
    else:
        _, blob = hered(url, token) if token else (urllib.request.urlopen(url, timeout=60).status,
                                                   urllib.request.urlopen(url, timeout=60).read())
    import json
    j = json.loads(blob.decode("utf-8", "replace"))
    files = []
    for e in j.get("feed", {}).get("entry", []):
        for link in e.get("links", []):
            href = link.get("href", "")
            if re.search(r"\.nc[34]?$", href):
                files.append(href)
    return files


def download(url, token, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    for k, v in UA.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=300) as r, open(out, "wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return os.path.getsize(out)


def main():
    ap = argparse.ArgumentParser(description="TEMPO Earthdata 下载")
    ap.add_argument("--short-name", default="TEMPO_NO2_L2", help="集合短名, 如 TEMPO_NO2_L2 / TEMPO-ABI_PM25_L3")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD, 缺省=start")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "asdc", "tempo"))
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()
    args.end = args.end or args.start

    token = load_token()
    print(f"[1] CMR 查询 {args.short_name} {args.start}~{args.end} ...")
    files = cmr_search(args.short_name, args.start, args.end, page_size=args.limit, token=token)
    print(f"    命中 {len(files)} 个数据文件")
    for i, fn in enumerate(files[: args.limit]):
        leaf = os.path.basename(fn)
        out = os.path.join(args.out, leaf)
        if os.path.exists(out) and os.path.getsize(out) > 1_000_000:
            print(f"[{i+1}] 已存在, 跳过: {leaf} ({os.path.getsize(out)} B)")
            continue
        for attempt in range(3):
            try:
                sz = download(fn, token, out)
                print(f"[{i+1}] OK {leaf} -> {sz:,} B")
                break
            except Exception as e:
                print(f"[{i+1}] 第{attempt+1}次失败: {e}")
                time.sleep(2 ** attempt)
    print("完成")


if __name__ == "__main__":
    main()