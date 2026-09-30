"""BSRN 地表辐照基准实测数据取数流程（PANGAEA 匿名通道）

与 SURFRAD 的区别：BSRN 是**全球**基准网络，但发布走 PANGAEA 数据出版平台，
月度数据被拆成"逻辑记录（LR）"，一年 = 12 个独立数据集，各带一个 DOI。

本脚本验证结论（2026-09-30，中国大陆办公网络，全程无账号、无 cookie）：
  - 列表 / 检索：`advanced/search.php` 匿名返回 JSON，带 totalCount
  - 单个数据集取值：`https://doi.pangaea.de/{DOI}?format=textfile` 匿名 200
  - 匿名可用格式：**只有 `textfile`**（tab 分隔 + 注释头）；`csv`/`zip`/`tab` 均返回 400
  - 站点覆盖矩阵：`https://dataportals.pangaea.de/bsrn/` 匿名 200（站点 × 年份）

⚠️ 两个必须注意的点：
  1. **列结构逐站、逐年代都不同**（有的站只有下行辐射，有的带 std/min/max，
     有的是 SWU/LWU 全量）。所以**不能硬编码列名**，必须读文件头。
  2. 官方页面写"登录后可获多种格式"，实测 `textfile` 免登录即可拿到完整数据；
     真正需要申请账号的是 **ftp 通道**（`ftp.bsrn.awi.de`，read account 向 WRMC 申请）。

用法：
  python bsrn_pangaea_pipeline.py --coverage                 # 站点 × 年份覆盖矩阵
  python bsrn_pangaea_pipeline.py --list TAT 2026            # 列某站某年的月度数据集
  python bsrn_pangaea_pipeline.py --get TAT 2026-08          # 下载并解析一个月
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SEARCH_URL = "https://www.pangaea.de/advanced/search.php"
PORTAL_URL = "https://dataportals.pangaea.de/bsrn/"
DOIDX_URL = "https://doi.pangaea.de/{doi}"
UA = {"User-Agent": "Mozilla/5.0 (research; meteo-power-analyst)"}
OUT_DIR = r"c:\work\meteo\data\bsrn"

DOI_RE = re.compile(r"doi:10\.1594/PANGAEA\.(\d+)")
YM_RE = re.compile(r"\((20\d{2})-(\d{2})\)")


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def coverage_matrix() -> None:
    """打印站点 × 年份覆盖矩阵的关键统计（匿名）。"""
    html = _fetch(PORTAL_URL).decode("utf-8", "ignore")
    rows = re.findall(
        r"<tr><td[^>]*>([^<]+)</td><td[^>]*>([^<]*)</td><td[^>]*>(.*?)</td>(.*?)</tr>",
        html, re.S,
    )
    years = list(range(1992, 2027))
    stats = []
    for name, short, sci, rest in rows:
        cells = re.findall(r"<td([^>]*)>", rest)
        have = [years[i] for i, c in enumerate(cells[: len(years)]) if 'class="X"' in c]
        stats.append((short.strip(), name.strip(), max(have) if have else None,
                      "**" in sci))
    print(f"站点行数: {len(stats)}")
    for y in (2026, 2025, 2024):
        n = sum(1 for s in stats if s[2] == y)
        print(f"  最新年份 == {y}: {n} 站")
    print("\n-- 有 2026 年数据的站 --")
    for short, name, last, closed in sorted(stats, key=lambda s: s[1]):
        if last == 2026:
            print(f"  {short:5s} {name}")


def list_monthly(short: str, year: int) -> list[tuple[str, str]]:
    """列出某站某年的月度数据集，返回 [(YYYY-MM, DOI), ...]（匿名）。"""
    q = f'project:label:BSRN +event:label:{short} +citation:"radiation"'
    params = {
        "q": q,
        "count": 30,
        "mindate": f"{year}-01-01",
        "maxdate": f"{year}-12-31",
    }
    data = json.loads(_fetch(SEARCH_URL + "?" + urllib.parse.urlencode(params)))
    out: dict[str, str] = {}
    for r in data.get("results", []):
        m_doi = DOI_RE.search(r.get("URI", ""))
        m_ym = YM_RE.search(r.get("html", ""))
        if m_doi and m_ym and int(m_ym.group(1)) == year:
            out[m_ym.group(0).strip("()")] = "10.1594/PANGAEA." + m_doi.group(1)
    return sorted(out.items())


def download_textfile(doi: str, out_dir: str = OUT_DIR) -> str:
    """匿名下载单个数据集的 textfile（唯一可匿名拿到的数据格式）。"""
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, doi.replace("/", "_") + ".txt")
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        print(f"  已存在: {dst}")
        return dst
    raw = _fetch(DOIDX_URL.format(doi=doi) + "?format=textfile")
    if b"/* DATA DESCRIPTION" not in raw[:200]:
        raise RuntimeError(f"非预期返回（可能不是数据体）: {doi} 前 200B={raw[:200]!r}")
    with open(dst, "wb") as f:
        f.write(raw)
    print(f"  下载 {doi} -> {dst} ({len(raw) / 1e6:.2f} MB)")
    return dst


def parse_bsrn(path: str):
    """按**文件自带表头**解析（列结构逐站不同，禁止硬编码列名）。"""
    import pandas as pd

    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    i_end = next(i for i, ln in enumerate(lines) if ln.strip() == "*/")
    header = lines[i_end + 1].split("\t")
    body = [ln.split("\t") for ln in lines[i_end + 2:] if ln.strip()]
    df = pd.DataFrame(body, columns=header)
    for c in df.columns:
        if c.lower().startswith("date/time"):
            continue
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description="BSRN / PANGAEA 匿名取数")
    ap.add_argument("--coverage", action="store_true", help="打印站点覆盖矩阵统计")
    ap.add_argument("--list", nargs=2, metavar=("SHORT", "YEAR"), help="列某站某年月度数据集")
    ap.add_argument("--get", nargs="+", metavar=("SHORT", "YYYY-MM"), help="下载并解析一个月")
    args = ap.parse_args()

    if args.coverage:
        coverage_matrix()
        return 0
    if args.list:
        short, year = args.list[0], int(args.list[1])
        for ym, doi in list_monthly(short, year):
            print(f"{ym}  {doi}")
        return 0
    if args.get:
        short, ym = args.get[0], args.get[1]
        year = int(ym[:4])
        found = dict(list_monthly(short, year))
        if ym not in found:
            print(f"未找到 {short} {ym}；该年可用: {sorted(found)}")
            return 1
        path = download_textfile(found[ym])
        df = parse_bsrn(path)
        print(f"记录数 {len(df)}，列数 {len(df.columns)}")
        print("列名:", list(df.columns))
        print(df.head(3).to_string())
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
