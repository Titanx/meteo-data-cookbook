"""按"典型国家/地区"批量下载 BSRN 完整年地表辐照（PANGAEA 匿名通道）。

选择规则：
  1. 候选站覆盖 西欧/中欧/北欧/北极/东亚/北美/北非/南部非洲/大洋洲/南美/南欧/南极；
  2. 每个站自动回溯，取**最近一个有 12 个月度数据集齐备的年份**（完整年）；
  3. 逐月下载 textfile 到 data/bsrn/<站码>/<年>/，按文件头解析并校验行数；
  4. 产出 data/bsrn/bsrn_catalog.csv（站、地区、年、月、DOI、字节、行数、列数）。

用法：
  python download_bsrn_typical_years.py --plan     # 只规划，不下
  python download_bsrn_typical_years.py            # 规划 + 下载 + 校验
"""
from __future__ import annotations

import argparse
import calendar
import csv
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SEARCH = "https://www.pangaea.de/advanced/search.php"
DOIDX = "https://doi.pangaea.de/{doi}?format=textfile"
UA = {"User-Agent": "Mozilla/5.0 (research; meteo-power-analyst)"}
OUT_ROOT = r"c:\work\meteo\data\bsrn"

DOI_RE = re.compile(r"doi:10\.1594/PANGAEA\.(\d+)")
YM_RE = re.compile(r"\((20\d{2}|19\d{2})-(\d{2})\)")

# (站码, 站名, 地区/国家, 选定年)
# 选定年 = 复核过的"最近且完整度最高"的年份（None 表示脚本自动回溯）。
# 复核依据：12 个月齐备 + 检索结果 "Size: N data points" 求和最高（见 raw/research-log）。
# 例：BRB 2015 虽 12 个月齐备但有整月缺测（2015-12 仅 7.5 天），2014 更完整；
#     DAA 2019 同理，2018 更完整。
STATIONS = [
    ("CAB", "Cabauw", "荷兰 / 西欧", 2025),
    ("PAY", "Payerne", "瑞士 / 中欧", 2025),
    ("TOR", "Toravere", "爱沙尼亚 / 北欧", 2020),
    ("NYA", "Ny-Alesund", "挪威 / 北极", 2025),
    ("QIQ", "Qiqihar", "中国 / 东亚", 2025),
    ("TAT", "Tateno", "日本 / 东亚", 2025),
    ("BON", "Bondville", "美国 / 北美中部", 2025),
    ("BOS", "Boulder (SURFRAD)", "美国 / 北美西部", 2025),
    ("TAM", "Tamanrasset", "阿尔及利亚 / 北非", 2025),
    ("DAA", "De Aar", "南非 / 南部非洲", 2018),
    ("GIM", "Granite Island", "澳大利亚 / 大洋洲", 2025),
    ("BRB", "Brasilia", "巴西 / 南美", 2014),
    ("LMP", "Lampedusa", "意大利 / 南欧", 2025),
    ("SON", "Sonnblick", "奥地利 / 阿尔卑斯", 2025),
    ("SYO", "Syowa", "南极 / 东南极", 2025),
    ("SPO", "South Pole", "南极 / 南极点", 2021),
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def list_year(code: str, year: int) -> dict[str, str]:
    """返回 {YYYY-MM: DOI}，剔除合集条目（标题含 'et seq'）。"""
    q = f'project:label:BSRN +event:label:{code} +citation:"radiation"'
    params = {"q": q, "count": 30,
              "mindate": f"{year}-01-01", "maxdate": f"{year}-12-31"}
    data = json.loads(fetch(SEARCH + "?" + urllib.parse.urlencode(params)))
    out: dict[str, str] = {}
    for r in data.get("results", []):
        html = r.get("html", "")
        if "et seq" in html:
            continue
        m_doi = DOI_RE.search(r.get("URI", ""))
        m_ym = YM_RE.search(html)
        if m_doi and m_ym and int(m_ym.group(1)) == year:
            out[f"{m_ym.group(1)}-{m_ym.group(2)}"] = "10.1594/PANGAEA." + m_doi.group(1)
    return out


def latest_complete_year(code: str, start: int = 2025, floor: int = 1992):
    """回溯找最近一个有 12 个月的年份。"""
    for year in range(start, floor - 1, -1):
        months = list_year(code, year)
        if len(months) == 12:
            return year, months
    return None, {}


def parse_rows(raw: bytes):
    """返回 (n_rows, n_cols, header)。"""
    text = raw.decode("utf-8", "replace")
    lines = text.splitlines()
    i_end = next((i for i, ln in enumerate(lines) if ln.strip() == "*/"), None)
    if i_end is None:
        return 0, 0, []
    header = lines[i_end + 1].split("\t")
    n = sum(1 for ln in lines[i_end + 2:] if ln.strip())
    return n, len(header), header


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--start-year", type=int, default=2025)
    ap.add_argument("--only", default="", help="只处理这些站码，逗号分隔")
    ap.add_argument("--year-override", default="", help="强制年份，如 BRB=2014,DAA=2018")
    args = ap.parse_args()

    only = {s.strip().upper() for s in args.only.split(",") if s.strip()}
    override = {}
    for part in args.year_override.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            override[k.strip().upper()] = int(v)

    plan = []
    for code, name, region, preset in STATIONS:
        if only and code not in only:
            continue
        year = override.get(code, preset)
        if year is None:
            year, months = latest_complete_year(code, start=args.start_year)
        else:
            months = list_year(code, year)
        if not year or len(months) != 12:
            print(f"  {code:4s} {name:20s} {year} 年只有 {len(months)} 个月，跳过")
            continue
        plan.append((code, name, region, year, months))
        tag = "（指定）" if year in override.values() else ""
        print(f"  {code:4s} {name:20s} {region:22s} 完整年 = {year}（12 个月）{tag}")

    print(f"\n规划：{len(plan)} 站 × 12 月 = {len(plan)*12} 个文件")
    if args.plan:
        return 0

    rows_out = []
    for code, name, region, year, months in plan:
        dst_dir = os.path.join(OUT_ROOT, code, str(year))
        os.makedirs(dst_dir, exist_ok=True)
        print(f"\n=== {code} {name} {year} ===")
        for ym in sorted(months):
            doi = months[ym]
            dst = os.path.join(dst_dir, f"{code}_{ym}.txt")
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                raw = open(dst, "rb").read()
                note = "cached"
            else:
                raw = fetch(DOIDX.format(doi=doi))
                if b"/* DATA DESCRIPTION" not in raw[:200]:
                    print(f"    {ym} 异常返回，跳过")
                    continue
                with open(dst, "wb") as f:
                    f.write(raw)
                note = "ok"
                time.sleep(0.2)
            n_rows, n_cols, _ = parse_rows(raw)
            days = calendar.monthrange(int(ym[:4]), int(ym[5:]))[1]
            flag = "" if n_rows == days * 1440 else f" 行数异常(应 {days*1440})"
            print(f"    {ym}  {len(raw)/1e6:5.2f} MB  {n_rows:6d} 行  {n_cols:2d} 列  {note}{flag}")
            rows_out.append({
                "station": code, "name": name, "region": region, "year": year,
                "month": ym, "doi": doi, "bytes": len(raw),
                "rows": n_rows, "cols": n_cols, "file": os.path.relpath(dst, OUT_ROOT),
            })

    cat = os.path.join(OUT_ROOT, "bsrn_catalog.csv")
    with open(cat, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    print(f"\n总文件 {len(rows_out)} 个；清单 -> {cat}")
    print(f"总体积 {sum(r['bytes'] for r in rows_out)/1e9:.2f} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
