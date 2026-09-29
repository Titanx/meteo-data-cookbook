"""ASTER GDEM v3 + ASTWBD 水体数据下载 (ERCOT 区域)

数据源: NASA LP DAAC (Earthdata Cloud)
认证: earthaccess + netrc (urs.earthdata.nasa.gov)
覆盖: ERCOT 区域 (25°N~34°N, 107°W~93°W)
分块: 1°×1° tile, 共 135 个

数据集:
  1. ASTGTM.003 - ASTER Global Digital Elevation Model v3 (30m)
     文件: ASTGTMV003_N{lat}{lon}_dem.tif (高程)
           ASTGTMV003_N{lat}{lon}_num.tif (观测次数/QA)

  2. ASTWBD.001 - ASTER Water Body Dataset (30m)
     文件: ASTWBDV001_N{lat}{lon}_dem.tif (水体高程)
           ASTWBDV001_N{lat}{lon}_att.tif (水体属性: 1=海洋, 2=湖泊, 3=河流)

== 使用方法 ==
  python download_aster_gdem.py              # 下载 GDEM + WBD
  python download_aster_gdem.py --gdem-only  # 仅下载 GDEM
  python download_aster_gdem.py --wbd-only   # 仅下载水体
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
from pathlib import Path
from datetime import datetime

# 自动加载 .env 文件
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

OUTPUT_DIR = Path(r"c:\work\meteo\data\aster")

ERCOT_BBOX = (-107.0, 25.0, -93.0, 34.0)

DATASETS = {
    "gdem": {
        "short_name": "ASTGTM",
        "doi": "10.5067/ASTER/ASTGTM.003",
        "name": "ASTER GDEM v3 (30m 数字高程模型)",
    },
    "wbd": {
        "short_name": "ASTWBD",
        "doi": "10.5067/ASTER/ASTWBD.001",
        "name": "ASTER Water Body Dataset (30m 水体数据)",
    },
}


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def download_dataset(key, ds_info):
    log(f"{'='*60}")
    log(f"下载 {key}: {ds_info['name']}")
    log(f"  DOI: {ds_info['doi']}")
    log(f"  范围: {ERCOT_BBOX}")
    log(f"{'='*60}")

    import earthaccess
    earthaccess.login(strategy="netrc")

    log("  搜索 granules...")
    results = earthaccess.search_data(
        short_name=ds_info["short_name"],
        doi=ds_info["doi"],
        bounding_box=ERCOT_BBOX,
        count=-1,
    )
    log(f"  找到 {len(results)} 个 granule")

    if not results:
        log("  无数据, 跳过")
        return

    out_dir = OUTPUT_DIR / key
    out_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    for i, granule in enumerate(results, 1):
        data_links = granule.data_links()
        if not data_links:
            log(f"  [{i}/{len(results)}] 无下载链接, 跳过")
            failed += 1
            continue

        url = data_links[0]
        fname = url.split("/")[-1]
        fpath = out_dir / fname

        if fpath.exists() and fpath.stat().st_size > 1000:
            log(f"  [{i}/{len(results)}] {fname} 已存在, 跳过")
            skipped += 1
            continue

        log(f"  [{i}/{len(results)}] 下载 {fname}...")
        try:
            earthaccess.download(granule, local_path=str(out_dir))
            if fpath.exists() and fpath.stat().st_size > 1000:
                size_mb = fpath.stat().st_size / 1024 / 1024
                log(f"    完成 ({size_mb:.1f} MB)")
                downloaded += 1
            else:
                log(f"    文件异常")
                failed += 1
        except Exception as e:
            log(f"    错误: {e}")
            failed += 1

    log(f"\n  {key} 完成: 新下载 {downloaded}, 跳过 {skipped}, 失败 {failed}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="下载 ASTER GDEM + WBD 数据")
    parser.add_argument("--gdem-only", action="store_true", help="仅下载 GDEM")
    parser.add_argument("--wbd-only", action="store_true", help="仅下载水体数据")
    args = parser.parse_args()

    keys = []
    if not args.wbd_only:
        keys.append("gdem")
    if not args.gdem_only:
        keys.append("wbd")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log("ASTER 地形/水体数据下载")
    log(f"  区域: ERCOT {ERCOT_BBOX}")
    log(f"  输出: {OUTPUT_DIR}")
    log(f"  数据集: {keys}")

    for key in keys:
        download_dataset(key, DATASETS[key])

    log(f"\n{'='*60}")
    log("全部完成!")
    log(f"  输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
