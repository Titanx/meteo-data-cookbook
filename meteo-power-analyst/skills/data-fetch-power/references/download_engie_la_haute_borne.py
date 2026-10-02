# -*- coding: utf-8 -*-
"""下载 ENGIE La Haute Borne 风电场开源数据（NREL OpenOA 打包版）。

**重要背景**：原始发布方 ENGIE 的门户 opendata-renewables.engie.com 已下线
（DNS 不再解析，2026-10 实测 NXDOMAIN），全量版（原站 2013–2016 与 2017–2020 两份）
当前不可获取。NREL OpenOA 仓库打包了基于 ENGIE 原始发布（Etalab 开放许可 v2.0，
2019-10-09 快照）的 2014–2015 版，是目前可稳定获取的权威分发点。

数据内容（la_haute_borne.zip）：
  la-haute-borne-data-2014-2015.csv   4 台机组 10 分钟 SCADA（2014–2015 两个完整年）
  plant_data.csv                      场站级 10 分钟净发电量/可发电量/限电量
  era5_wind_la_haute_borne.csv        同址 ERA5 逐时再分析（1999 起）
  merra2_la_haute_borne.csv           同址 MERRA-2 逐时再分析（1997 起）
  la-haute-borne_asset_table.csv      机组台账（坐标/机型/轮毂高/叶轮直径）
  SCADA_data_description.csv          变量说明

用法：
  python download_engie_la_haute_borne.py            # 下载并解压
  python download_engie_la_haute_borne.py --check    # 只检查已有文件
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace",
                              line_buffering=True)

URL = ("https://raw.githubusercontent.com/NREL/OpenOA/main/examples/data/"
       "la_haute_borne.zip")
SIZE = 36762939
OUT_ROOT = r"c:\work\meteo\data\windfarm\la_haute_borne"
UA = {"User-Agent": "Mozilla/5.0 (research; meteo-power-analyst)"}


def fetch_to(url: str, dst: str, size: int | None, tries: int = 5) -> None:
    part = dst + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    if size and have == size:
        os.replace(part, dst)
        return
    for k in range(tries):
        try:
            headers = dict(UA)
            if have:
                headers["Range"] = f"bytes={have}-"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=300) as r:
                if have and r.status != 206:
                    have = 0
                with open(part, "ab" if have else "wb") as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
            if size and os.path.getsize(part) != size:
                raise RuntimeError(f"体积不符：{os.path.getsize(part)} != {size}")
            os.replace(part, dst)
            return
        except Exception as e:  # noqa: BLE001
            print(f"  重试 {k+1}/{tries}… ({e})")
            have = os.path.getsize(part) if os.path.exists(part) else 0
            time.sleep(3 * (k + 1))
    raise RuntimeError("下载失败：重试耗尽")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    os.makedirs(OUT_ROOT, exist_ok=True)
    zip_path = os.path.join(OUT_ROOT, "la_haute_borne.zip")

    if not args.check:
        if os.path.exists(zip_path) and os.path.getsize(zip_path) == SIZE:
            print(f"已存在压缩包（{SIZE/1e6:.1f} MB），跳过下载")
        else:
            print(f"下载 {URL}")
            fetch_to(URL, zip_path, SIZE)

    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.startswith("__MACOSX")]
        print(f"压缩包内 {len(names)} 个文件：")
        for n in names:
            info = z.getinfo(n)
            print(f"  {n:38s} {info.file_size/1e6:9.2f} MB")
        if not args.check:
            for n in names:
                dst = os.path.join(OUT_ROOT, os.path.basename(n))
                if os.path.exists(dst) and os.path.getsize(dst) == z.getinfo(n).file_size:
                    continue
                with z.open(n) as src, open(dst, "wb") as out:
                    out.write(src.read())
            print(f"\n解压完成 -> {OUT_ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
