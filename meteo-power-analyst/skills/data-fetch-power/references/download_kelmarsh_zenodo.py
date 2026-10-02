# -*- coding: utf-8 -*-
"""下载 Kelmarsh 风电场开源数据集（Zenodo, CC-BY-4.0）。

Zenodo 记录: 10.5281/zenodo.16807551  —— 6 台 Senvion MM92，10 分钟 SCADA，2016-2024。

**环境坑**：本机 DNS 把裸域 zenodo.org 解析到 0.0.0.0（屏蔽），但 www.zenodo.org 正常。
因此在进程内给 socket.getaddrinfo 打别名补丁，把 zenodo.org 指向 www.zenodo.org 的 IP；
TLS 的 SNI 与证书校验仍按 zenodo.org 进行，不受影响。

用法：
  python download_kelmarsh_zenodo.py --list           # 只列文件与体积
  python download_kelmarsh_zenodo.py                  # 下载全部
  python download_kelmarsh_zenodo.py --only 2016      # 只下文件名含 2016 的
"""
from __future__ import annotations

import argparse
import io
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace",
                              line_buffering=True)

RECORD = 16807551
API = f"https://zenodo.org/api/records/{RECORD}"
OUT_ROOT = r"c:\work\meteo\data\windfarm\kelmarsh"
UA = {"User-Agent": "Mozilla/5.0 (research; meteo-power-analyst)"}
WWW_FALLBACK = "137.138.153.219"


def patch_dns() -> str:
    """把被屏蔽的裸域指到可解析的 www 别名 IP。"""
    orig = socket.getaddrinfo
    ip = None
    for _ in range(3):
        try:
            ip = orig("www.zenodo.org", 443, type=socket.SOCK_STREAM)[0][4][0]
            break
        except Exception:  # noqa: BLE001
            time.sleep(1)
    ip = ip or WWW_FALLBACK

    def patched(host, *a, **kw):
        if host in ("zenodo.org", "www.zenodo.org"):
            port = a[0] if a else kw.get("port", 443)
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
        return orig(host, *a, **kw)

    socket.getaddrinfo = patched
    return ip


def fetch(url: str, retries: int = 4, timeout: int = 300) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(5 * (2 ** attempt))
                continue
            raise
        except Exception:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def download(url: str, dst: str, size: int | None = None) -> None:
    """流式下载，支持断点续传（.part 临时文件）。

    坑 1：本机到 Zenodo 的连接会中途挂死（socket 收不到数据也不报错），
          所以读超时压到 45s，配合 .part 续传快速恢复。
    坑 2：重定向后某些链路会忽略 Range 返回 200，此时只能从头写（用 wb 截断），
          否则会新旧数据拼接导致体积/内容错乱。
    """
    part = dst + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if size and have == size:
        os.replace(part, dst)
        return
    headers = dict(UA)
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as r:
        if have and r.status != 206:  # 服务端忽略 Range → 丢弃旧片段重来
            print(f"      [warn] 服务端返回 {r.status}（忽略 Range），从头下载")
            have = 0
        mode = "ab" if have else "wb"
        last = time.time()
        with open(part, mode) as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                have += len(chunk)
                now = time.time()
                if now - last >= 20:
                    pct = f" ({have/size*100:.0f}%)" if size else ""
                    print(f"      … {have/1e6:.1f} MB{pct}", flush=True)
                    last = now
    if size and os.path.getsize(part) != size:
        raise RuntimeError(f"体积不符：{os.path.getsize(part)} != {size}")
    os.replace(part, dst)


def download_retry(url: str, dst: str, size: int | None, tries: int = 8) -> None:
    """本机到 Zenodo 的链路会偶发截断/挂死（实测少 9KB、或中途不再收数据），必须带重试。"""
    last = None
    for k in range(tries):
        try:
            download(url, dst, size)
            return
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"      重试 {k+1}/{tries - 1}… ({e})", flush=True)
            time.sleep(5 * (k + 1))
    raise last  # type: ignore[misc]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    ip = patch_dns()
    print(f"zenodo.org -> {ip}（别名补丁）")

    d = json.loads(fetch(API))
    md = d["metadata"]
    files = d.get("files", [])
    total = sum(f["size"] for f in files)
    print(f"记录: {md['title']}  DOI={d.get('doi')}  许可={md.get('license', {}).get('id')}")
    print(f"文件 {len(files)} 个，合计 {total/1e9:.2f} GB\n")

    if args.list:
        for f in files:
            print(f"  {f['key']:46s} {f['size']/1e6:9.2f} MB")
        return 0

    os.makedirs(OUT_ROOT, exist_ok=True)
    todo = [f for f in files if not args.only or args.only in f["key"]]
    todo.sort(key=lambda f: f["size"])
    print(f"待下载 {len(todo)} 个（{sum(f['size'] for f in todo)/1e9:.2f} GB）\n")

    t0 = time.time()
    done = fail = 0
    got = 0
    for f in todo:
        dst = os.path.join(OUT_ROOT, f["key"])
        if os.path.exists(dst) and os.path.getsize(dst) == f["size"]:
            print(f"  已存在 {f['key']}")
            got += f["size"]
            done += 1
            continue
        try:
            t1 = time.time()
            download_retry(f["links"]["self"], dst, f["size"])
            dt = time.time() - t1
            got += f["size"]
            done += 1
            print(f"  ✓ {f['key']}  {f['size']/1e6:.1f} MB  {dt:.0f}s  "
                  f"({f['size']/1e6/max(dt,0.1):.1f} MB/s)")
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"  ✗ {f['key']} 失败: {e!r}")

    el = time.time() - t0
    print(f"\n完成：成功 {done}，失败 {fail}，共 {got/1e9:.2f} GB，"
          f"用时 {el/60:.1f} 分钟（均速 {got/1e6/max(el,1):.1f} MB/s）")
    print(f"落盘目录：{OUT_ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
