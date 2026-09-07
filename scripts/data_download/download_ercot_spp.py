"""ERCOT 结算点电价 (SPP) 下载（2025 至今）

数据来源: GridStatus.io 托管 API (免费方案)
覆盖范围: ERCOT 交易枢纽 + 负荷区 + 代表性 Resource Node
时间范围: 2025-01-01 ~ 今天
输出目录: c:\\work\\meteo\\data\\ercot\\

== 数据说明 ==

ERCOT 官网 (www.ercot.com) 部署了 Imperva 反爬虫且对中国 IP 完全屏蔽，
EIA API 也不提供电价数据。GridStatus.io 托管 API 从中国可正常访问
（返回 401 需要 key，而非 403 封锁），免费方案每月 250 次请求 / 50 万行，
足够下载 ERCOT 全部枢纽的 2025 至今 DAM + RTM 电价。

数据集:
  1. ercot_spp_day_ahead_hourly    日前市场 SPP (小时级)
  2. ercot_spp_real_time_15_min    实时市场 SPP (15分钟级)

ERCOT 交易枢纽 (Trading Hubs):
  - HB_NORTH      北部枢纽
  - HB_SOUTH      南部枢纽
  - HB_HOUSTON    休斯顿枢纽
  - HB_PANHANDLE   锅柄枢纽（已弃用，返回空数据）
  - HB_WEST       西部枢纽

ERCOT 负荷区 (Load Zones):
  - LZ_WEST       西部负荷区 (风电密集区)
  - LZ_NORTH      北部负荷区 (含 Panhandle 风电带)
  - LZ_SOUTH      南部负荷区
  - LZ_HOUSTON    休斯顿负荷区

ERCOT 代表性 Resource Node (基于 EIA API 查询):
  风电 (5个): Horse Hollow, Capricorn Ridge, Aviator, White Mesa, Foard City
  光伏 (5个): Longhorn Solar, Hornet Solar, Aktina, Samson Solar, Red Tailed Hawk
  注意: Resource Node 名称可能与 GridStatus.io 的 location 值不完全一致，
  建议先用 --list-locations 查询实际可用的 location 列表进行匹配。

== 使用方法 ==
  1. 免费注册 GridStatus.io 账号 (1 分钟):
     https://www.gridstatus.io/sign-up

  2. 获取 API key:
     登录后访问 https://www.gridstatus.io/settings/api
     复制你的 API key

  3. 设置环境变量:
     PowerShell: $env:GRIDSTATUS_API_KEY = "你的key"

  4. 运行:
     python download_ercot_spp.py

  5. 可选参数:
     --start 2025-01-01   起始日期 (默认 2025-01-01)
     --end 2026-07-22     截止日期 (默认今天)
     --markets DAM RTM    下载类型 (默认 DAM+RTM)
     --hubs HB_NORTH      指定枢纽 (默认全部 5 个)
     --location-type      hubs/loadzones/resources/recommended/all
     --list-locations     查询所有 location 列表 (消耗约1K行)
     --dry-run            只列出可用数据集, 不下载

  6. 下载推荐的10个代表性 Resource Node (仅RTM, 约545K行):
     python download_ercot_spp.py --location-type recommended --markets RTM

  7. 查询所有可用 location (用于匹配 Resource Node 名称):
     python download_ercot_spp.py --list-locations
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import argparse
import time
import json
from datetime import datetime
from pathlib import Path

# 自动加载 .env 文件 (API key 不入 git)
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import pandas as pd

# ── 常量 ──────────────────────────────────────────────
OUTPUT_DIR = Path(r"c:\work\meteo\data\ercot")

DATASETS = {
    "DAM": {
        "id": "ercot_spp_day_ahead_hourly",
        "name": "日前市场 SPP (小时级)",
        "freq": "hourly",
    },
    "RTM": {
        "id": "ercot_spp_real_time_15_min",
        "name": "实时市场 SPP (15分钟级)",
        "freq": "15min",
    },
}

# HB_PANHANDLE 已弃用，下载时返回空数据，保留在列表中以便跳过时记录
ALL_HUBS = ["HB_NORTH", "HB_SOUTH", "HB_HOUSTON", "HB_PANHANDLE", "HB_WEST"]

# ERCOT 负荷区 (Load Zones) - 比 Hub 更贴近终端用户区域电价
ALL_LOAD_ZONES = ["LZ_WEST", "LZ_NORTH", "LZ_SOUTH", "LZ_HOUSTON"]

# 代表性 Resource Node (大型风电/光伏电厂)
# 基于 EIA API 查询 ERCOT 区域 top 风电/光伏发电厂 (2026-07)
# 2026-08-06 通过 --list-locations 获取 1099 个 Resource Node 代码并完成匹配
# 电厂名称 -> GridStatus.io location 代码

# 风电 Resource Node (31 个 location 代码, 2026-09-07 从 --list-locations 获取)
WIND_RESOURCE_NODES = [
    "AJAXWIND_RN", "AQLA_WND_RN", "BAIRDWND_ALL", "BRAZ_WND_ALL", "BRISCOE_WIND",
    "CALLAHA_WND1", "CAMWIND_RN", "FTWIND_UNIT1", "GOA_GOATWIND", "H_HOLLO_WND1",
    "HART_WND_RN", "HHOLLW2_WND1", "HHOLLW3_WND1", "HHOLLW4_WND1", "HRFDWIND_ALL",
    "MONT_WND_RN", "MOZART_WIND1", "PHILLWND_ALL", "RN_SR_WIND1", "RRC_WIND_ALL",
    "SSPURT_WIND1", "SWEETWND_1", "SWTWN4_WND45", "TYLRWIND_RN", "VERAWIND_ALL",
    "WH_WIND_ALL", "WILDWIND_ALL", "WND_WHITNEY", "WNDTS2_UNIT1", "YCAT_WND_RN",
    "YNG_WND_ALL",
]

# 光伏 Resource Node (89 个 location 代码, 2026-09-07 从 --list-locations 获取)
SOLAR_RESOURCE_NODES = [
    "7RNCHSLR_ALL", "ANDMDSLR_ALL", "ARMD_SLR_RN", "ASCK_SLR_RN", "AURO_SLR_RN",
    "AZSP_SLR_RN", "BART_SLR_RN", "BELM_SLR_RN", "BUZI_SLR_RN", "BYNM_SLR_RN",
    "CHAL_SLR_RN", "CHAR_SLR_RN", "CHIL_SLR", "CMPD_SLR_RN", "CORALSLR_ALL",
    "CRWN_SLR_UN1", "CST1_SLR_RN", "CST2_SLR_RN", "DIVR_SLR_RN", "DORA_SLR_RN",
    "DRCK_SLR_RN", "EIFSLR_UNIT1", "ELZA_SLR_RN", "ERKA_SLR_RN", "FAGUSSLR_RN",
    "FENCESLR_ALL", "FILESSLR_PV1", "FIVEWSLR_ALL", "FRYE_SLR_ALL", "FWLR_SLR_1",
    "GAIA_SLR_RN", "GODY_SLR_RN", "GRAN_SLR_RN", "GRIM_SLR_RN", "GRND_SLR_RN",
    "GRYH_SLR_RN", "HKSN_SLR_ALL", "HOLZ_SLR_RN", "HOPKNSLR_ALL", "HRMS_SLR_RN",
    "HRNT_SLR_RN", "HRZN_SLR_UN1", "JADE_SLR_ALL", "JAG_SLR_RN", "JKLP_SLR_RN",
    "JUNG_SLR_RN", "LAMESASLR_G", "LEON_SLR_RN", "LMWD_SLR_RN", "MAND_SLR_RN",
    "MCLNSLR_RN", "MIDP_SLR_RN", "MLB_SLR_RN", "MRKM_SLR_RN", "MROW_SLR_RN",
    "NHKY_SLR_RN", "NOBLESLR_ALL", "NOVA1SLR_ALL", "NRTN_SLR_RN", "OGS_SLR_RN",
    "OUTP_SLR_RN", "OYST_SLR_RN", "PDRA_SLR_RN", "PERE_SLR_RN", "PINN_SLR_RN",
    "RADN_SLR_ALL", "RN_LNP_SLR", "RN_QTUM_SLR", "RN_SOLC_SLR", "SEQ2_SLR_RN",
    "SHAW_SLR_RN", "SIG_SLR_RN", "SOLARA_UNIT1", "STAM_SLR_ALL", "STAR_SLR_RN",
    "STRG_SLR_ALL", "SUNVASLR_ALL", "SWFT_SLR_RN", "SYBR_SLR_RN", "TI_SOLAR_ALL",
    "TNS_SLR_ALL", "TRBT_SLR_RN", "TREB_SOLAR1", "TROJ_SLR_RN", "TUL_SLR_ALL",
    "TYSN_SLR_RN", "ULYS_SLR_RN", "YAPN_SLR_RN", "ZIER_SLR_ALL",
]

# 已有的非 WND/SLR 命名的风电/光伏节点
EXTRA_RESOURCE_NODES = [
    "CAPRIDGE_ALL",   # Capricorn Ridge Wind
    "AVIAT_ALL",      # Aviator Wind
    "WHMESA_U1",      # White Mesa Wind
    "FOARDCTY_ALL",   # Foard City Wind
    "LHORN_N_U1_2",   # Longhorn Solar
    "SAMSON_ALL",     # Samson Solar
]

RECOMMENDED_RESOURCE_NODES = WIND_RESOURCE_NODES + SOLAR_RESOURCE_NODES + EXTRA_RESOURCE_NODES


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def get_api_key():
    key = os.environ.get("GRIDSTATUS_API_KEY", "").strip()
    if not key:
        log("=" * 60)
        log("错误: 未找到 GridStatus.io API key!")
        log("请按以下步骤获取 (免费, 1 分钟):")
        log("  1. 访问 https://www.gridstatus.io/sign-up")
        log("  2. 注册免费账号")
        log("  3. 登录后访问 https://www.gridstatus.io/settings/api")
        log("  4. 复制你的 API key")
        log("  5. 设置环境变量:")
        log('     PowerShell: $env:GRIDSTATUS_API_KEY = "你的key"')
        log("=" * 60)
        sys.exit(1)
    return key


def main():
    parser = argparse.ArgumentParser(description="下载 ERCOT 结算点电价 (GridStatus.io API)")
    parser.add_argument("--start", default="2025-01-01", help="起始日期 (默认 2025-01-01)")
    parser.add_argument("--end", default=None, help="截止日期 (默认今天)")
    parser.add_argument("--markets", nargs="+", default=None, help="市场类型 (默认 DAM+RTM)")
    parser.add_argument("--hubs", nargs="+", default=None, help="交易枢纽 (默认全部, --location-type=hubs 时生效)")
    parser.add_argument("--location-type", default="all",
                        choices=["hubs", "loadzones", "resources", "wind", "solar", "all", "recommended"],
                        help="结算点类型: hubs, loadzones, resources(全部RN), wind(风电RN), solar(光伏RN), recommended(推荐12个), all(Hub+LZ)")
    parser.add_argument("--dry-run", action="store_true", help="只列出可用数据集, 不下载")
    parser.add_argument("--list-locations", action="store_true",
                        help="查询一个时间点列出所有 location (消耗约1K行, 用于匹配 Resource Node 名称)")
    args = parser.parse_args()

    api_key = get_api_key()

    import gridstatusio
    client = gridstatusio.GridStatusClient(api_key=api_key)

    start_date = args.start
    end_date = args.end or datetime.now().strftime("%Y-%m-%d")

    # 确定要下载的市场
    markets = args.markets if args.markets else ["DAM", "RTM"]

    # --list-locations: 查询一个时间点列出所有 location (消耗约1K行)
    if args.list_locations:
        log("查询所有 location 列表 (消耗约1K行)...")
        from datetime import datetime as dt
        today = dt.utcnow().strftime("%Y-%m-%d")
        df = client.get_dataset(
            "ercot_spp_real_time_15_min",
            start=today + " 00:00",
            end=today + " 00:15",
            verbose=False,
        )
        if df is not None and len(df) > 0:
            log(f"  总行数: {len(df)}")
            if "location_type" in df.columns:
                log("\n  location_type 分布:")
                for lt, count in df["location_type"].value_counts().items():
                    log(f"    {lt}: {count}")
            # 保存 Resource Node 列表
            if "location_type" in df.columns:
                rn = df[df["location_type"] == "Resource Node"]["location"].tolist()
                log(f"\n  Resource Node 数量: {len(rn)}")
                out_file = OUTPUT_DIR / "_resource_nodes_list.csv"
                df[df["location_type"] == "Resource Node"][["location", "location_type"]].to_csv(
                    out_file, index=False
                )
                log(f"  保存到: {out_file}")
                log("\n  前20个 Resource Node:")
                for name in rn[:20]:
                    log(f"    {name}")
            # 全部保存
            all_file = OUTPUT_DIR / "_all_locations_snapshot.csv"
            df.to_csv(all_file, index=False)
            log(f"\n  全部 location 快照: {all_file}")
        return

    # 确定要下载的结算点
    if args.hubs:
        locations = args.hubs
    elif args.location_type == "hubs":
        locations = ALL_HUBS
    elif args.location_type == "loadzones":
        locations = ALL_LOAD_ZONES
    elif args.location_type == "resources":
        locations = RECOMMENDED_RESOURCE_NODES
        log("注意: Resource Node 名称可能与 GridStatus.io 的 location 值不完全一致!")
        log("  建议先用 --list-locations 查询实际可用的 location 列表进行匹配")
    elif args.location_type == "wind":
        locations = WIND_RESOURCE_NODES
        log(f"下载风电 Resource Node ({len(locations)}个 location)")
    elif args.location_type == "solar":
        locations = SOLAR_RESOURCE_NODES
        log(f"下载光伏 Resource Node ({len(locations)}个 location)")
    elif args.location_type == "recommended":
        locations = RECOMMENDED_RESOURCE_NODES
        log(f"下载全部风电+光伏 Resource Node ({len(locations)}个 location)")
    else:  # all = Hub + LZ
        locations = ALL_HUBS + ALL_LOAD_ZONES

    log("ERCOT 结算点电价下载")
    log(f"  数据源: GridStatus.io 托管 API (免费方案)")
    log(f"  时间范围: {start_date} ~ {end_date}")
    log(f"  市场: {markets}")
    log(f"  结算点类型: {args.location_type}")
    log(f"  结算点: {locations}")
    log(f"  输出目录: {OUTPUT_DIR}")

    # 检查 API 使用量
    try:
        usage = client.get_api_usage()
        log(f"  API 使用量: {usage}")
    except Exception as e:
        log(f"  API 使用量查询失败: {e}")

    if args.dry_run:
        log("\n列出 ERCOT 相关数据集...")
        try:
            datasets = client.list_datasets(filter_term="ercot", return_list=True)
            for ds in datasets:
                log(f"  {ds}")
        except Exception as e:
            log(f"  列出数据集失败: {e}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    total_rows = 0

    for market_key in markets:
        if market_key not in DATASETS:
            log(f"  未知市场类型: {market_key}, 跳过")
            continue

        ds = DATASETS[market_key]
        log(f"\n{'='*60}")
        log(f"下载 {market_key}: {ds['name']}")
        log(f"  数据集 ID: {ds['id']}")
        log(f"{'='*60}")

        # 获取数据集元数据
        try:
            meta = client.get_dataset_metadata(ds["id"])
            earliest = meta.get("earliest_available_time_utc", "N/A")
            log(f"  最早可用数据: {earliest}")
        except Exception as e:
            log(f"  元数据查询失败: {e}")

        for hub in locations:
            fname = f"ercot_{market_key.lower()}_{hub}_{start_date}_{end_date}.csv"
            fpath = OUTPUT_DIR / fname

            # 断点续传
            if fpath.exists() and fpath.stat().st_size > 100:
                log(f"  {hub} 已存在, 跳过")
                total_skipped += 1
                continue

            log(f"  下载 {market_key} {hub}...")
            try:
                df = client.get_dataset(
                    ds["id"],
                    start=start_date,
                    end=end_date,
                    filter_column="location",
                    filter_value=hub,
                    verbose=False,
                )

                if df is not None and len(df) > 0:
                    df.to_csv(fpath, index=False)
                    total_rows += len(df)

                    # 统计
                    if "spp" in df.columns:
                        spp = pd.to_numeric(df["spp"], errors="coerce").dropna()
                        if len(spp) > 0:
                            log(f"    {len(df)} 行 → {fname}")
                            log(f"    价格: 均值 ${spp.mean():.2f}, 最大 ${spp.max():.2f}, 最小 ${spp.min():.2f}/MWh")
                        else:
                            log(f"    {len(df)} 行 → {fname} (价格全为空)")
                    else:
                        log(f"    {len(df)} 行 → {fname}")
                        log(f"    列: {list(df.columns)}")

                    total_downloaded += 1
                else:
                    log(f"    无数据")
                    total_failed += 1
            except Exception as e:
                log(f"    错误: {e}")
                total_failed += 1

            time.sleep(1)  # 请求间隔

    # 汇总
    log(f"\n{'='*60}")
    log("下载完成!")
    log(f"  新下载: {total_downloaded} 个文件 ({total_rows:,} 行)")
    log(f"  已跳过: {total_skipped} 个文件")
    log(f"  失败:   {total_failed} 个文件")
    log(f"  输出目录: {OUTPUT_DIR}")

    # 检查剩余 API 额度
    try:
        usage = client.get_api_usage()
        log(f"  API 使用量: {usage}")
    except Exception:
        pass

    # 生成汇总文件
    summary_path = OUTPUT_DIR / "_spp_download_summary.json"
    summary = {
        "download_time": datetime.now().isoformat(),
        "source": "GridStatus.io API (免费方案)",
        "date_range": f"{start_date} ~ {end_date}",
        "markets": markets,
        "location_type": args.location_type,
        "locations": locations,
        "downloaded": total_downloaded,
        "skipped": total_skipped,
        "failed": total_failed,
        "total_rows": total_rows,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log(f"  汇总: {summary_path}")


if __name__ == "__main__":
    main()
