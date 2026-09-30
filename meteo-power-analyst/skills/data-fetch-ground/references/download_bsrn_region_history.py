"""按区域批量下载 BSRN 多年数据（重点：中国 / 美国 / 欧洲），用于与其他数据源对照。

与 download_bsrn_typical_years.py 的关系：
  前者 = 每个典型站下 1 个完整年（广覆盖）；
  本脚本 = 在重点区域内按**年份区间**下多年的全部完整年（深覆盖），可反复运行（已下的复用）。

年份规则：每年必须 12 个月齐备才下（"完整年"），不完整的年份跳过。
目录：data/bsrn/<站码>/<年>/<站码>_<YYYY-MM>.txt
清单：data/bsrn/bsrn_catalog.csv（扫全树重建，覆盖所有已下数据）

用法：
  python download_bsrn_region_history.py --plan          # 只打印计划与规模
  python download_bsrn_region_history.py                 # 下载
  python download_bsrn_region_history.py --only 中国      # 只下某个区域
  python download_bsrn_region_history.py --reindex        # 只重建清单，不下
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
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace",
                              line_buffering=True)

SEARCH = "https://www.pangaea.de/advanced/search.php"
DOIDX = "https://doi.pangaea.de/{doi}?format=textfile"
UA = {"User-Agent": "Mozilla/5.0 (research; meteo-power-analyst)"}
OUT_ROOT = r"c:\work\meteo\data\bsrn"
DOI_RE = re.compile(r"doi:10\.1594/PANGAEA\.(\d+)")
YM_RE = re.compile(r"\((\d{4})-(\d{2})\)")

# ---- 站元数据（写清单用） ----
META = {
    "CAB": ("Cabauw", "荷兰 / 西欧"), "PAY": ("Payerne", "瑞士 / 中欧"),
    "TOR": ("Toravere", "爱沙尼亚 / 北欧"), "NYA": ("Ny-Alesund", "挪威 / 北极"),
    "QIQ": ("Qiqihar", "中国 / 东亚"), "XIA": ("Xianghe", "中国 / 华北平原(已停测)"),
    "TAT": ("Tateno", "日本 / 东亚"),
    "BON": ("Bondville", "美国 / 伊利诺伊"), "BOS": ("Boulder", "美国 / 科罗拉多"),
    "DRA": ("Desert Rock", "美国 / 内华达"), "FPE": ("Fort Peck", "美国 / 蒙大拿"),
    "GCR": ("Goodwin Creek", "美国 / 密西西比"), "SXF": ("Sioux Falls", "美国 / 南达科他"),
    "E13": ("Southern Great Plains", "美国 / 俄克拉何马(近ERCOT)"),
    "LRC": ("Langley Research Center", "美国 / 弗吉尼亚"),
    "BAR": ("Barrow", "美国 / 阿拉斯加"),
    "LMP": ("Lampedusa", "意大利 / 南欧"), "SON": ("Sonnblick", "奥地利 / 阿尔卑斯"),
    "LIN": ("Lindenberg", "德国 / 中欧"), "CAM": ("Camborne", "英国 / 西欧"),
    "LER": ("Lerwick", "英国 / 苏格兰北部"), "CNR": ("Cener", "西班牙 / 纳瓦拉"),
    "IZA": ("Izana", "西班牙 / 加那利"), "INO": ("Magurele", "罗马尼亚 / 东南欧"),
    "BUD": ("Budapest", "匈牙利 / 中欧"), "PAL": ("Palaiseau", "法国 / 西欧"),
    "SYO": ("Syowa", "南极 / 东南极"), "SPO": ("South Pole", "南极 / 南极点"),
    "DAA": ("De Aar", "南非 / 南部非洲"), "TAM": ("Tamanrasset", "阿尔及利亚 / 北非"),
    "GIM": ("Granite Island", "澳大利亚 / 大洋洲"), "BRB": ("Brasilia", "巴西 / 南美"),
}

# ---- 各区域计划：(区域, 站码, 起始年, 结束年) ----
PLAN = [
    # 中国（重点，全部可用）
    ("中国", "QIQ", 2023, 2025),
    ("中国", "XIA", 2005, 2015),
    # 美国
    ("美国", "BON", 2016, 2025),
    ("美国", "BOS", 2016, 2025),
    ("美国", "DRA", 2016, 2025),
    ("美国", "FPE", 2016, 2022),
    ("美国", "GCR", 2016, 2019),
    ("美国", "SXF", 2016, 2018),
    ("美国", "E13", 2016, 2018),
    ("美国", "LRC", 2016, 2025),
    ("美国", "BAR", 2016, 2022),
    # 欧洲
    ("欧洲", "CAB", 2016, 2025),
    ("欧洲", "PAY", 2016, 2025),
    ("欧洲", "SON", 2016, 2025),
    ("欧洲", "CNR", 2010, 2025),
    ("欧洲", "IZA", 2016, 2025),
    ("欧洲", "PAL", 2016, 2025),
    ("欧洲", "LIN", 2016, 2022),
    ("欧洲", "TOR", 2016, 2020),
    ("欧洲", "BUD", 2020, 2025),
    ("欧洲", "INO", 2022, 2025),
    ("欧洲", "LMP", 2024, 2025),
    ("欧洲", "CAM", 2016, 2016),
    # LER 2016 只有 86% 完整（少 7.4 万分钟），改用完整度更高的 2015
    ("欧洲", "LER", 2015, 2015),
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def months_by_year(code: str) -> dict[int, dict[str, str]]:
    """{年: {YYYY-MM: DOI}}，剔除合集条目。一次检索拿全站历史。"""
    q = f'project:label:BSRN +event:label:{code} +citation:"radiation"'
    params = {"q": q, "count": 600}
    data = json.loads(fetch(SEARCH + "?" + urllib.parse.urlencode(params)))
    out: dict[int, dict[str, str]] = defaultdict(dict)
    for x in data.get("results", []):
        h = x.get("html", "")
        if "et seq" in h:
            continue
        m_doi = DOI_RE.search(x.get("URI", ""))
        m_ym = YM_RE.search(h)
        if m_doi and m_ym:
            out[int(m_ym.group(1))][m_ym.group(0).strip("()")] = \
                "10.1594/PANGAEA." + m_doi.group(1)
    return dict(out)


def parse_rows(raw: bytes):
    text = raw.decode("utf-8", "replace")
    lines = text.splitlines()
    i_end = next((i for i, ln in enumerate(lines) if ln.strip() == "*/"), None)
    if i_end is None:
        return 0, 0
    return sum(1 for ln in lines[i_end + 2:] if ln.strip()), len(lines[i_end + 1].split("\t"))


def reindex() -> None:
    """扫全树重建 bsrn_catalog.csv。"""
    rows = []
    for dp, _, fns in os.walk(OUT_ROOT):
        for fn in sorted(fns):
            if not fn.endswith(".txt"):
                continue
            fp = os.path.join(dp, fn)
            code = os.path.basename(os.path.dirname(os.path.dirname(fp)))
            ym = fn[:-4].split("_")[-1]
            raw = open(fp, "rb").read()
            n_rows, n_cols = parse_rows(raw)
            doi = ""
            for ln in raw[:4000].decode("utf-8", "replace").splitlines():
                m = DOI_RE.search(ln)
                if m:
                    doi = "10.1594/PANGAEA." + m.group(1)
                    break
            name, region = META.get(code, ("?", "?"))
            rows.append({
                "station": code, "name": name, "region": region,
                "year": ym[:4], "month": ym, "doi": doi,
                "bytes": len(raw), "rows": n_rows, "cols": n_cols,
                "file": os.path.relpath(fp, OUT_ROOT),
            })
    rows.sort(key=lambda r: (r["region"], r["station"], r["month"]))
    cat = os.path.join(OUT_ROOT, "bsrn_catalog.csv")
    with open(cat, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    total = sum(r["bytes"] for r in rows)
    print(f"清单重建：{len(rows)} 个文件，{total/1e9:.2f} GB -> {cat}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--reindex", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--delay", type=float, default=0.4, help="每个请求后的休眠秒数（防限流）")
    args = ap.parse_args()

    if args.reindex:
        reindex()
        return 0

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    plan = [p for p in PLAN if not only or p[0] in only]

    todo = []
    print("规划（只列 12 个月齐备的年份）：")
    for region, code, y0, y1 in plan:
        have = months_by_year(code)
        years = [y for y in range(y0, y1 + 1) if len(have.get(y, {})) == 12]
        name, _ = META.get(code, ("?", "?"))
        if not years:
            print(f"  [{region}] {code:4s} {name:26s} {y0}-{y1}: 无完整年")
            continue
        print(f"  [{region}] {code:4s} {name:26s} {years[0]}-{years[-1]}: {len(years)} 个完整年")
        for y in years:
            todo.append((region, code, name, y, have[y]))

    n_files = sum(len(m) for *_x, m in todo)
    print(f"\n合计 {len(todo)} 个站年 / {n_files} 个文件（估算 {n_files*3.5/1000:.1f} GB，"
          f"按均值 3.5 MB/月）")
    if args.plan:
        return 0

    # 组装任务，跳过已缓存的
    tasks = []
    cached = 0
    for region, code, name, year, months in todo:
        dst_dir = os.path.join(OUT_ROOT, code, str(year))
        os.makedirs(dst_dir, exist_ok=True)
        for ym in sorted(months):
            dst = os.path.join(dst_dir, f"{code}_{ym}.txt")
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                cached += 1
                continue
            tasks.append((code, ym, months[ym], dst))
    print(f"已缓存 {cached} 个；待下载 {len(tasks)} 个\n")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    done, failed = 0, 0
    t0 = time.time()
    last_code = None

    def get_one(task):
        """单文件下载：429/网络错误退避重试，单点失败不影响整体。"""
        code, ym, doi, dst = task
        import urllib.error
        for attempt in range(6):
            try:
                raw = fetch(DOIDX.format(doi=doi))
                if b"/* DATA DESCRIPTION" not in raw[:200]:
                    return task, False, "非数据返回"
                with open(dst, "wb") as f:
                    f.write(raw)
                time.sleep(args.delay)
                return task, True, ""
            except urllib.error.HTTPError as e:
                if e.code in (429, 503):
                    time.sleep(5 * (2 ** attempt))
                    continue
                return task, False, f"HTTP {e.code}"
            except Exception as e:  # noqa: BLE001
                time.sleep(3 * (attempt + 1))
                if attempt == 5:
                    return task, False, repr(e)
        return task, False, "重试耗尽"

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(get_one, t): t for t in tasks}
        for fu in as_completed(futs):
            task, ok, err = fu.result()
            done += 1 if ok else 0
            failed += 0 if ok else 1
            if not ok:
                print(f"  ! {task[0]} {task[1]} 失败: {err}")
            if task[0] != last_code:
                last_code = task[0]
                print(f"  [{META.get(task[0], ('?', '?'))[1]}] {task[0]} 下载中…")
            if (done + failed) % 120 == 0:
                el = time.time() - t0
                print(f"  ... 成功 {done} / 失败 {failed} / 共 {len(tasks)}，"
                      f"{el/60:.1f} 分钟，{(done+failed)/el*60:.0f} 文件/分钟")

    print(f"\n下载结束：成功 {done}，失败 {failed}，用时 {(time.time()-t0)/60:.1f} 分钟")
    reindex()
    return 0


if __name__ == "__main__":
    sys.exit(main())
