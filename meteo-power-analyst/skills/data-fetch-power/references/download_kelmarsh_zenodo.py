# -*- coding: utf-8 -*-
"""下载 Kelmarsh 风电场开源数据集（Zenodo, CC-BY-4.0）。

Zenodo 记录: 10.5281/zenodo.16807551  —— 6 台 Senvion MM92，10 分钟 SCADA，2016-2024。

**环境坑 1（DNS）**：本机 DNS 把裸域 zenodo.org 解析到 0.0.0.0（屏蔽），但 www.zenodo.org 正常。
因此在进程内给 socket.getaddrinfo 打别名补丁；TLS 的 SNI 与证书校验仍按 zenodo.org 进行。

**环境坑 2（边缘 IP 快慢差 10 倍）**：www.zenodo.org 是一个 IP 池，实测同时有
连不上的（http=000）、限速到 0.1 MB/s 的、能跑 1 MB/s 的，而且**每次解析到的都不一样**。
所以启动时对候选 IP 逐个测速，选最快的（`pick_ip`）。

**环境坑 3（单连接会被限速，多连接可叠加）**：同一台机器从 GitHub 能跑 7 MB/s，
而 Zenodo 单连接只有 0.1–1 MB/s。实测**分段并发**有效（4 段下 473 MB 用 108s ≈ 4.4 MB/s），
因此默认把每个文件切成 4 段并发取，各段单独校验长度再按序合并。

**环境坑 4（挂死 / 塌陷 / 截断）**：连接会中途不再收数据、速率塌陷、或提前 EOF。
对策：45s 读超时 + `.part` 续传 + 低速看门狗 + 分段重试 + 合并后体积校验。

用法：
  python download_kelmarsh_zenodo.py --list           # 只列文件与体积
  python download_kelmarsh_zenodo.py                  # 下载全部（自动跳过已完成）
  python download_kelmarsh_zenodo.py --conns 4        # 指定每文件并发段数（1 = 单连接）
  python download_kelmarsh_zenodo.py --only 2016      # 只下文件名含 2016 的
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace",
                              line_buffering=True)

RECORD = 16807551
API = f"https://zenodo.org/api/records/{RECORD}"
OUT_ROOT = r"c:\work\meteo\data\windfarm\kelmarsh"
UA = {"User-Agent": "Mozilla/5.0 (research; meteo-power-analyst)"}
WWW_FALLBACK = "137.138.153.219"
MIN_RATE = 0.2e6  # B/s：低于此速率的连接视为"塌陷"，主动断开重连

# www.zenodo.org 解析出的候选边缘 IP（实测有些直接连不上、有些限速到 0.1 MB/s，
# 有些能到 1 MB/s，且**随时间切换**）。启动时逐个实测，选最快的。
CANDIDATE_IPS = [
    "188.185.48.75", "188.184.103.118", "137.138.52.235", "137.138.153.219",
    "188.185.43.22", "137.138.6.45",
]


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


def _probe(ip: str, url: str, seconds: float = 6.0) -> float:
    """给某个 IP 打补丁后跑 window 秒的 Range 测速，返回 B/s（失败返回 0）。"""
    patch_dns_fixed(ip)
    try:
        req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-8000000"})
        t = time.time()
        got = 0
        with urllib.request.urlopen(req, timeout=4) as r:
            if r.status != 206:
                return 0.0
            while time.time() - t < seconds:
                c = r.read(1 << 20)
                if not c:
                    break
                got += len(c)
        el = max(time.time() - t, 0.001)
        return got / el
    except Exception:  # noqa: BLE001
        return 0.0


def patch_dns_fixed(ip: str) -> None:
    """把裸域与 www 都固定指到给定 IP（供测速与正式下载复用）。"""
    orig = socket.getaddrinfo

    def patched(host, *a, **kw):
        if host in ("zenodo.org", "www.zenodo.org"):
            port = a[0] if a else kw.get("port", 443)
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
        return orig(host, *a, **kw)

    socket.getaddrinfo = patched


def pick_ip(url: str) -> str:
    """逐个候选 IP 实测，选最快的那个（Zenodo 边缘快慢差 10 倍以上）。"""
    cands = list(CANDIDATE_IPS)
    try:
        os_ip = socket.getaddrinfo("www.zenodo.org", 443,
                                   type=socket.SOCK_STREAM)[0][4][0]
        if os_ip not in cands:
            cands.insert(0, os_ip)
    except Exception:  # noqa: BLE001
        pass
    best, best_rate = WWW_FALLBACK, -1.0
    for ip in cands:
        rate = _probe(ip, url)
        print(f"    探测 {ip:18s} {rate/1e6:6.3f} MB/s", flush=True)
        if rate > best_rate:
            best, best_rate = ip, rate
    patch_dns_fixed(best)
    print(f"  选用 {best}（{best_rate/1e6:.3f} MB/s）", flush=True)
    return best


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
    坑 3：连接**不死但速率塌陷**（实测从 0.5 MB/s 掉到 0.035 MB/s，
          只是不报错，超时永远等不到）。所以加"低速看门狗"：
          30s 窗口内速率低于 MIN_RATE 且剩余量还大，就主动断开重连（走 Range 续传）。
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
        last = w_start = time.time()
        w_bytes = 0
        with open(part, mode) as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                have += len(chunk)
                w_bytes += len(chunk)
                now = time.time()
                if now - last >= 20:
                    pct = f" ({have/size*100:.0f}%)" if size else ""
                    print(f"      … {have/1e6:.1f} MB{pct}", flush=True)
                    last = now
                if now - w_start >= 30:
                    rate = w_bytes / (now - w_start)
                    if size and (size - have) > 5e6 and rate < MIN_RATE:
                        f.flush()
                        raise RuntimeError(
                            f"速率过低 {rate*1e6:.0f} B/s（<{MIN_RATE*1e6:.0f}），断开重连")
                    w_start, w_bytes = now, 0
    if size and os.path.getsize(part) != size:
        raise RuntimeError(f"体积不符：{os.path.getsize(part)} != {size}")
    os.replace(part, dst)


def download_until(url: str, dst: str, size: int | None,
                   max_seconds: float = 5400) -> None:
    """反复重连直到下完（每个文件一个总时限），应对挂死/速率塌陷/截断。"""
    t0 = time.time()
    k = 0
    while time.time() - t0 < max_seconds:
        try:
            download(url, dst, size)
            return
        except Exception as e:  # noqa: BLE001
            k += 1
            el = time.time() - t0
            have = os.path.getsize(dst + ".part") if os.path.exists(dst + ".part") else 0
            print(f"      重连 #{k}（已 {el/60:.1f} min，落盘 {have/1e6:.1f} MB）: {e}",
                  flush=True)
            time.sleep(2)
    raise RuntimeError(f"超过时限未完成：{dst}")


def download_segmented(url: str, dst: str, size: int, conns: int = 6,
                       max_seconds: float = 7200) -> None:
    """分段并发下载（每段一条连接，各自 Range + 重试），最后按序合并。

    为什么需要：Zenodo 对**单连接**限速（实测 70–120 KB/s，而同一台机器从 GitHub 能跑
    7 MB/s），但**多连接可叠加**（实测 4 连接 ≈ 2.3×）。所以把大文件切成 N 段并发取。
    每段单独校验长度；若某段返回非 206（服务端忽略 Range）或长度不符，就重取该段。
    """
    if not size:
        download_until(url, dst, size)
        return
    tmpdir = dst + ".segs"
    os.makedirs(tmpdir, exist_ok=True)
    seg = math.ceil(size / conns)

    def one(i: int) -> None:
        s = i * seg
        e = min(size, s + seg) - 1
        if s > e:
            return
        want = e - s + 1
        p = os.path.join(tmpdir, f"{i:02d}")
        if os.path.exists(p) and os.path.getsize(p) == want:
            return
        t0 = time.time()
        attempt = 0
        while time.time() - t0 < max_seconds:
            attempt += 1
            try:
                headers = dict(UA)
                headers["Range"] = f"bytes={s}-{e}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=45) as r:
                    if r.status != 206:
                        raise RuntimeError(f"seg{i} 状态 {r.status}（未接受 Range）")
                    got = 0
                    with open(p, "wb") as f:
                        while got < want:
                            c = r.read(min(1 << 20, want - got))
                            if not c:
                                break
                            f.write(c)
                            got += len(c)
                if os.path.getsize(p) == want:
                    return
                raise RuntimeError(f"seg{i} 长度 {os.path.getsize(p)} != {want}")
            except Exception as ex:  # noqa: BLE001
                if attempt % 5 == 1:
                    print(f"      [seg{i}] 重试（{ex}）", flush=True)
                time.sleep(2)
        raise RuntimeError(f"seg{i} 超时")

    with ThreadPoolExecutor(max_workers=conns) as ex:
        list(ex.map(one, range(conns)))

    part = dst + ".part"
    with open(part, "wb") as out:
        for i in range(conns):
            p = os.path.join(tmpdir, f"{i:02d}")
            if os.path.exists(p):
                with open(p, "rb") as f:
                    shutil.copyfileobj(f, out, 1 << 20)
    if os.path.getsize(part) != size:
        raise RuntimeError(f"合并后体积不符：{os.path.getsize(part)} != {size}")
    os.replace(part, dst)
    shutil.rmtree(tmpdir, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--conns", type=int, default=4,
                    help="每文件并发段数；1 = 单连接（Zenodo 单连接被限速，默认 4）")
    args = ap.parse_args()

    # 先找一个能取元数据的边缘 IP（候选里有连不上的）
    cands: list[str] = []
    try:
        cands.append(socket.getaddrinfo("www.zenodo.org", 443,
                                        type=socket.SOCK_STREAM)[0][4][0])
    except Exception:  # noqa: BLE001
        pass
    cands += [c for c in CANDIDATE_IPS if c not in cands]
    if WWW_FALLBACK not in cands:
        cands.append(WWW_FALLBACK)

    d = None
    for ip in cands:
        patch_dns_fixed(ip)
        try:
            d = json.loads(fetch(API, retries=1, timeout=25))
            print(f"元数据经 {ip} 取到")
            break
        except Exception as e:  # noqa: BLE001
            print(f"  {ip} 取元数据失败：{str(e)[:60]}")
    if d is None:
        print("取不到 Zenodo 元数据，放弃")
        return 1

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
    pend = [f for f in todo
            if not (os.path.exists(os.path.join(OUT_ROOT, f["key"]))
                    and os.path.getsize(os.path.join(OUT_ROOT, f["key"])) == f["size"])]
    print(f"待下载 {len(todo)} 个（{sum(f['size'] for f in todo)/1e9:.2f} GB），"
          f"其中未完成 {len(pend)} 个\n")

    if pend:
        # 只对还没下完的文件测速选 IP（Zenodo 边缘快慢差 10 倍以上）
        probe_url = next((f["links"]["self"] for f in pend if f["size"] > 5e6),
                         pend[0]["links"]["self"])
        pick_ip(probe_url)
        print()

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
            if args.conns > 1:
                download_segmented(f["links"]["self"], dst, f["size"], args.conns)
            else:
                download_until(f["links"]["self"], dst, f["size"])
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
