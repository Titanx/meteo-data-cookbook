# -*- coding: utf-8 -*-
"""站点降水的"日界（报告时间）"对齐检验。

为什么需要这个工具
------------------
站点雨量计记录的是**当地日历日**的日累积，而 AI 预报 / 再分析输出的是 **UTC 日历日**。
把两者直接对比，会把"日累积窗口不同"造成的**时间相位差**算成误差，
系统性地惩罚降水技巧——而且这个偏差**逐站不同、按国家成块聚集**，
在区域比较里会被误读成"某些地区预报更差"。

本工具做的事
------------
用 GHCNh 的小时观测（可以任意重切窗口）在 UTC 上把日累积窗口平移 -N..+N 小时，
与 GHCNd 上报的日值求相关；相关峰的偏移量就是该站真实的日界，
同时给出"未对齐（0 h）"与"最优对齐"的得分落差 = 错位代价。

三个已实测的口径坑（务必先读，否则结果会是垃圾）
------------------------------------------------
1. **GHCNh 的 `precipitation` 是"自上次观测以来的累积"，不是小时增量。**
   直接对全部记录求和会得到年总量的 ≈2.45 倍。
   正确做法：**按小时取 max，再逐小时求和**（实测年量还原到 1.04~1.05 倍）。
   —— 相关性对线性缩放不敏感，所以这个还原度足够支撑 PCC，但对"量级/偏差比"必须谨慎。
2. **GHCNh 的时间戳不是整点**，实测有 `:51`、`:02`、`:22`、`:27` 这种次小时时点。
   按整点去取数会几乎全部落空（表现为偏差比算出 0.01~0.04 这种荒谬值）。
   必须先 floor 到小时再聚合。
3. **GHCNd 与 GHCNh 的站点集合不重合。**
   本工具需要两者都有：GHCNh 提供小时降水、GHCNd 提供上报日值。
   实测东亚站点里同时满足的很少（扫 29 站仅零星可用），北美/欧洲覆盖最好。

读结论时必须看的两件事
----------------------
1. **量级还原比**（`level_ratio`）：应 ≈1.0（实测 1.04~1.06）。偏到 0.0x 或 >2 说明聚合口径错了，
   此时任何相关结论都不成立。
2. **峰位平台宽度**（`plateau_range`）：PCC-偏移曲线在 1 小时步长下常常是**宽平台**，
   与最优之差 ≤0.005 的偏移可能有 ±1~2 h。**平台内取 argmax 不是估计量**，
   只能把日界报成一个区间；分月结论在低降水月（湿日少）尤其不可靠，脚本会打 `?` 标记。

用法
----
    # 单站/多站：扫描日界偏移并给出错位代价
    python precip_window_verify.py --station USW00094728 USW00023183 --year 2024

    # 先找出某国前缀下"两边都有"的候选站
    python precip_window_verify.py --list KSM

产物（默认写到仓库根 data/station_precip/，该目录已被 .gitignore 忽略）
    precip_window_verify.json   逐站结论（最优偏移 / PCC 落差 / 年度量还原比 / 分月结论）
    precip_window_curves.csv    逐站逐偏移的完整曲线（长表）
    precip_window_monthly.csv   逐站逐月的最优偏移（用于拆夏令时的 1 小时季节错配）

数据源
    GHCNd 日值：https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/<SID>.csv.gz
    GHCNh 小时：AWS 公开桶 noaa-ghcnh-pds（匿名，NODD），by-year/psv
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

UA = {"User-Agent": "Mozilla/5.0 (research; meteo-power-analyst)"}
GHCNH_BUCKET = "https://noaa-ghcnh-pds.s3.amazonaws.com"
GHCNH_KEY = "hourly/access/by-year/{year}/psv/GHCNh_{sid}_{year}.psv"
GHCNH_PREFIX = "hourly/access/by-year/{year}/psv/GHCNh_{prefix}"
GHCN_D_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{sid}.csv.gz"
# GHCNd 单站文件名 = 11 位站号；GSOD 则是 11 位**无连字符**，两者别混
TIMEOUT = 90


def repo_root() -> Path:
    p = Path(__file__).resolve()
    for cand in p.parents:
        if (cand / "meteo-power-analyst").is_dir():
            return cand
    return p.parents[4] if len(p.parents) > 4 else Path.cwd()


def fetch(url: str, cache: Path | None = None, tag: str = "") -> bytes:
    """取数（可选本地缓存）。缓存键用 tag，避免把 URL 里的特殊字符写进文件名。"""
    if cache is not None:
        cpath = cache / tag
        if cpath.exists() and cpath.stat().st_size > 0:
            return cpath.read_bytes()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read()
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / tag).write_bytes(data)
    return data


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    sx = sum((a - mx) ** 2 for a in xs)
    sy = sum((b - my) ** 2 for b in ys)
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(sx * sy)


def load_ghcn_daily(sid: str, year: int, cache: Path | None) -> dict[str, float]:
    """GHCNd 上报日值（当地日历日），PRCP 单位 0.1mm -> mm。"""
    raw = fetch(GHCN_D_URL.format(sid=sid), cache, tag=f"ghcnd_{sid}.csv.gz")
    txt = gzip.decompress(raw).decode("utf-8", "replace")
    out: dict[str, float] = {}
    for line in txt.splitlines():
        p = line.split(",")
        if len(p) < 4 or p[2] != "PRCP":
            continue
        if not p[1].startswith(str(year)):
            continue
        try:
            v = int(p[3])
        except ValueError:
            continue
        if v == -9999:
            continue
        out[p[1]] = v / 10.0
    return out


def load_ghcn_hourly(sid: str, year: int, cache: Path | None) -> dict[datetime, float]:
    """GHCNh 小时降水（mm）。

    坑 1：值是"自上次观测累积"，故先按小时取 max 再求和。
    坑 2：时间戳非整点，必须先 floor 到小时。
    """
    try:
        raw = fetch(GHCNH_BUCKET + "/" + GHCNH_KEY.format(year=year, sid=sid),
                    cache, tag=f"ghcnh_{sid}_{year}.psv")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FileNotFoundError(f"GHCNh 无 {sid} 的 {year} 小时文件") from e
        raise
    lines = raw.decode("utf-8", "replace").splitlines()
    if not lines:
        raise FileNotFoundError(f"GHCNh {sid} {year} 文件为空")
    cols = lines[0].split("|")
    di, pi = cols.index("DATE"), cols.index("precipitation")
    by_hour: dict[datetime, list[float]] = {}
    fmts = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M")
    for line in lines[1:]:
        p = line.split("|")
        if len(p) <= max(di, pi) or p[pi] == "":
            continue
        try:
            val = float(p[pi])
        except ValueError:
            continue
        ts = p[di].strip()
        dt = None
        for f in fmts:
            try:
                dt = datetime.strptime(ts[: len(f) + 4].strip(), f)
                break
            except ValueError:
                continue
        if dt is None:
            continue
        # 坑 2：floor 到小时
        key = dt.replace(minute=0, second=0, microsecond=0)
        by_hour.setdefault(key, []).append(val)
    # 坑 1：小时取 max
    return {k: max(v) for k, v in by_hour.items()}


def window_sum(hourly: dict[datetime, float], day, shift_h: int) -> float:
    """把 UTC 窗口 [D 00:00 + shift, D+1 00:00 + shift) 内的降水累加。"""
    start = datetime(day.year, day.month, day.day) + timedelta(hours=shift_h)
    return sum(hourly.get(start + timedelta(hours=k), 0.0) for k in range(24))


def scan_sids(prefix: str, year: int, limit: int = 8) -> list[str]:
    url = (GHCNH_BUCKET + "/?list-type=2&prefix="
           + GHCNH_PREFIX.format(year=year, prefix=prefix) + f"&max-keys={limit}")
    body = fetch(url).decode("utf-8", "replace")
    out = []
    for k in re.findall(r"<Key>([^<]+)</Key>", body):
        out.append(k.split("GHCNh_")[1].split(f"_{year}")[0])
    return out


def verify_one(sid: str, year: int, half: int, cache: Path | None, min_days: int) -> dict | None:
    daily = load_ghcn_daily(sid, year, cache)
    if len(daily) < min_days:
        print(f"  [{sid}] GHCNd 日值仅 {len(daily)} 天（<{min_days}），跳过")
        return None
    hourly = load_ghcn_hourly(sid, year, cache)
    if not hourly:
        print(f"  [{sid}] GHCNh 无有效小时降水，跳过")
        return None

    keys = sorted(daily)
    days = [datetime.strptime(k, "%Y%m%d").date() for k in keys]
    obs = [daily[k] for k in keys]
    obs_total = sum(obs)
    wet_days = sum(1 for v in obs if v >= 0.1)

    # 先把每个偏移下的估计序列算一遍，后面整年相关与分月相关都复用它（避免重复计算）
    est_by_shift = {sh: [window_sum(hourly, d, sh) for d in days]
                    for sh in range(-half, half + 1)}

    curves = [{"shift": sh, "pcc": pearson(obs, est_by_shift[sh]),
               "est_total": sum(est_by_shift[sh])}
              for sh in range(-half, half + 1)]

    valid = [c for c in curves if c["pcc"] == c["pcc"]]
    if not valid:
        print(f"  [{sid}] 相关系数全为 nan（观测或估计无变差），跳过")
        return None
    best = max(valid, key=lambda c: c["pcc"])
    at0 = next((c for c in valid if c["shift"] == 0), None)

    # 峰位平台：与最优之差 <= 0.005 的偏移区间。
    # 平台越宽，说明"最优偏移"的定位越不确定——1 小时步长下常见 ±1~2 h 的平台，
    # 此时把 argmax 当成精确日界是过度解读。
    plateau = sorted(c["shift"] for c in valid if best["pcc"] - c["pcc"] <= 0.005)

    # 分月最优偏移：用来拆夏令时（DST）造成的 1 小时季节错配。
    # 单月样本小，须设门槛：天数 >=20 且湿日 >=3，否则峰位不可信。
    monthly = []
    for m in range(1, 13):
        idx = [i for i, d in enumerate(days) if d.month == m]
        if len(idx) < 20:
            continue
        o = [obs[i] for i in idx]
        wet = sum(1 for v in o if v >= 0.1)
        if wet < 3:
            continue
        cand = [(sh, pearson(o, [est_by_shift[sh][i] for i in idx]))
                for sh in range(-half, half + 1)]
        cand = [c for c in cand if c[1] == c[1]]
        if not cand:
            continue
        b = max(cand, key=lambda t: t[1])
        # 峰宽诊断：最优与次优不同偏移的落差，太小说明该月区分不出来
        gap = b[1] - max((c[1] for c in cand if c[0] != b[0]), default=float("nan"))
        monthly.append({"month": m, "days": len(idx), "wet_days": wet,
                        "best_shift": b[0], "pcc_best": round(b[1], 3),
                        "gap_to_2nd": round(gap, 3) if gap == gap else None,
                        # 平台诊断：与次优偏移落差 <0.005 说明该月峰位是任意的，不可用
                        "reliable": bool(gap == gap and gap >= 0.005)})

    ratio = (best["est_total"] / obs_total) if obs_total > 0 else float("nan")
    return {
        "sid": sid,
        "year": year,
        "days": len(days),
        "wet_days": wet_days,
        "obs_total_mm": round(obs_total, 1),
        "best_shift_h": best["shift"],
        "pcc_best": round(best["pcc"], 3),
        "pcc_at_0h": round(at0["pcc"], 3) if at0 else None,
        "delta_pcc": round(best["pcc"] - at0["pcc"], 3) if at0 else None,
        # 量级还原比：应接近 1.0；明显偏离说明 GHCNh 聚合口径需要复核
        "level_ratio": round(ratio, 3),
        "plateau_range": [plateau[0], plateau[-1]] if plateau else None,
        "curve": {str(c["shift"]): round(c["pcc"], 3) for c in valid},
        "monthly": monthly,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="站点降水日界（报告时间）对齐检验")
    ap.add_argument("--station", nargs="+", default=[], help="GHCN 站号，可多个（或逗号分隔）")
    ap.add_argument("--year", type=int, default=2024, help="年份（默认 2024）")
    ap.add_argument("--half", type=int, default=12, help="偏移扫描半径，小时（默认 ±12）")
    ap.add_argument("--min-days", type=int, default=200, help="GHCNd 日值最少天数（默认 200）")
    ap.add_argument("--list", metavar="PREFIX", default=None,
                    help="列出 GHCNh 某国前缀下的站点（如 KSM / JA / CHM），不跑检验")
    ap.add_argument("--out", default=None, help="产物目录（默认 <repo>/data/station_precip）")
    ap.add_argument("--cache", default=None, help="下载缓存目录（默认 <out>/_cache）")
    ap.add_argument("--no-cache", action="store_true", help="不读写下载缓存")
    args = ap.parse_args()

    root = repo_root()
    out = Path(args.out) if args.out else root / "data" / "station_precip"
    if args.no_cache:
        cache = None
    else:
        cache = Path(args.cache) if args.cache else out / "_cache"

    if args.list:
        sids = scan_sids(args.list, args.year)
        print(f"GHCNh {args.year} 前缀 {args.list} 下站点（前 {len(sids)} 个）：")
        for s in sids:
            print("  " + s)
        return 0

    sids: list[str] = []
    for s in args.station:
        sids.extend(x for x in s.replace(",", " ").split() if x)
    if not sids:
        ap.error("需要 --station（或 --list PREFIX）")

    print("=" * 88)
    print(f"站点降水日界对齐检验  year={args.year}  扫描 ±{args.half} h  "
          f"（GHCNd 上报日值 × GHCNh 小时重切窗口）")
    print("=" * 88)
    print(f"缓存目录: {cache if cache else '（关闭）'}")

    results = []
    for sid in sids:
        print(f"\n### {sid}")
        try:
            r = verify_one(sid, args.year, args.half, cache, args.min_days)
        except FileNotFoundError as e:
            print(f"  跳过：{e}")
            continue
        except urllib.error.HTTPError as e:
            print(f"  跳过：HTTP {e.code}")
            continue
        if r is None:
            continue
        results.append(r)
        print(f"    日值 {r['days']} 天，湿日 {r['wet_days']}，年量 {r['obs_total_mm']:.0f} mm，"
              f"量级还原比 {r['level_ratio']:.2f}")
        print("    PCC 曲线: " + "  ".join(f"{k}:{v}" for k, v in r["curve"].items()))
        pr = r.get("plateau_range")
        ptxt = f"   峰位平台 {pr[0]:+d}~{pr[1]:+d} h（ΔPCC≤0.005）" if pr else ""
        print(f"    ▶ 最优日界偏移 {r['best_shift_h']:+d} h   PCC={r['pcc_best']:.3f}{ptxt}")
        if r["pcc_at_0h"] is not None:
            print(f"    ▶ 未对齐 0 h          PCC={r['pcc_at_0h']:.3f}   Δ={r['delta_pcc']:+.3f}")
        if r["monthly"]:
            print("    分月最优偏移: " + "  ".join(
                f"{m['month']:02d}月:{m['best_shift']:+d}{'' if m['reliable'] else '?'}"
                for m in r["monthly"]))
            bad = [m["month"] for m in r["monthly"] if not m["reliable"]]
            if bad:
                print(f"    ⚠ {len(bad)}/{len(r['monthly'])} 个月峰位落在平台里（落差<0.005），"
                      f"该月 argmax 无意义，已标 ?：{', '.join(f'{m}月' for m in bad)}")
            win = sorted(m["best_shift"] for m in r["monthly"] if m["month"] in (12, 1, 2))
            smr = sorted(m["best_shift"] for m in r["monthly"] if m["month"] in (6, 7, 8))
            if win and smr:
                w_mid = win[len(win) // 2]
                s_mid = smr[len(smr) // 2]
                print(f"    ▶ 冬(12/1/2) 中位 {w_mid:+d} h   夏(6/7/8) 中位 {s_mid:+d} h   "
                      f"季节差 {s_mid - w_mid:+d} h")

    if results:
        print("\n" + "=" * 88)
        print(f"{'站点':<16}{'最优偏移h':>9}{'PCC@0h':>9}{'PCC@最优':>9}{'ΔPCC':>8}{'还原比':>8}")
        print("-" * 88)
        for r in results:
            print(f"{r['sid']:<16}{r['best_shift_h']:>+9d}{r['pcc_at_0h']:>9.3f}"
                  f"{r['pcc_best']:>9.3f}{r['delta_pcc']:>+8.3f}{r['level_ratio']:>8.2f}")
        print("=" * 88)
        print("提示：本测试下『最优偏移 = 该站标准 UTC 偏移的相反数』即为命中，"
              "可用它校验复原是否正确。")

        out.mkdir(parents=True, exist_ok=True)
        (out / "precip_window_verify.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        with (out / "precip_window_curves.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["sid", "year", "shift_h", "pcc"])
            for r in results:
                for sh, pcc in sorted(r["curve"].items(), key=lambda kv: int(kv[0])):
                    w.writerow([r["sid"], r["year"], sh, pcc])
        with (out / "precip_window_monthly.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["sid", "year", "month", "days", "wet_days",
                        "best_shift_h", "pcc_best", "gap_to_2nd", "reliable"])
            for r in results:
                for m in r["monthly"]:
                    w.writerow([r["sid"], r["year"], m["month"], m["days"], m["wet_days"],
                                m["best_shift"], m["pcc_best"], m["gap_to_2nd"],
                                int(m["reliable"])])
        print(f"\n产物：{out / 'precip_window_verify.json'}")
        print(f"      {out / 'precip_window_curves.csv'}")
        print(f"      {out / 'precip_window_monthly.csv'}")
    else:
        print("\n没有可出结论的站点。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
