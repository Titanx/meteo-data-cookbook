"""ASTER 地形与 GOES GLM 闪电分布联动分析

分析内容:
  1. 闪电闪击位置与地形高程的关联 (按高程分带统计闪击密度)
  2. 闪电闪击位置与水体距离的关联 (内陆/沿海/湖泊区差异)
  3. 地形坡度对闪电分布的影响
  4. 可视化: 散点图、热力图、分带统计图

数据源:
  - GLM L2: GOES-18 闪电闪击 (2026-09-07 00:00~02:00 UTC, ERCOT 区域)
  - ASTER GDEM v3: 30m 数字高程模型
  - ASTWBD: 30m 水体分类 (0=陆地, 1=海洋, 2=湖泊, 3=河流)

输出:
  - c:\\work\\meteo\\data\\analysis\\terrain_lightning_stats.csv  统计表
  - c:\\work\\meteo\\data\\analysis\\terrain_lightning_scatter.png  散点图
  - c:\\work\\meteo\\data\\analysis\\terrain_lightning_density.png  分带密度图
  - c:\\work\\meteo\\data\\analysis\\terrain_lightning_map.png     空间分布图
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import glob
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="rasterio")

# 项目路径
PROJECT_ROOT = Path(r"c:\work\meteo")
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "data_download"))

GDEM_DIR = PROJECT_ROOT / "data" / "aster" / "gdem"
WBD_DIR = PROJECT_ROOT / "data" / "aster" / "wbd"
GLM_DIR = PROJECT_ROOT / "data" / "glm" / "l2"
OUTPUT_DIR = PROJECT_ROOT / "data" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ERCOT_BBOX = (-107.0, 25.0, -93.0, 34.0)


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def extract_glm_flashes():
    """从 GLM L2 文件提取 ERCOT 区域所有闪电闪击"""
    from parse_glm import parse_glm_file

    files = sorted(glob.glob(str(GLM_DIR / "*.nc")))
    log(f"GLM 文件数: {len(files)}")

    all_lats = []
    all_lons = []
    all_times = []

    for i, fpath in enumerate(files):
        data = parse_glm_file(fpath, bbox=ERCOT_BBOX)
        flashes = data["flashes"]
        if len(flashes) > 0:
            all_lats.extend(flashes["lat"])
            all_lons.extend(flashes["lon"])
            all_times.extend(flashes["time"])
        if (i + 1) % 60 == 0:
            log(f"  已处理 {i+1}/{len(files)} 文件, 累计闪击 {len(all_lats)}")

    lats = np.array(all_lats)
    lons = np.array(all_lons)
    times = np.array(all_times)

    log(f"ERCOT 闪击总数: {len(lats)}")
    log(f"  纬度: {lats.min():.2f} ~ {lats.max():.2f}")
    log(f"  经度: {lons.min():.2f} ~ {lons.max():.2f}")

    return lats, lons, times


def build_tile_index(tile_dir, prefix):
    """构建 ASTER tile 索引: (lat, lon) -> 文件路径"""
    index = {}
    pattern = f"{prefix}_N*_W*_dem.tif" if "ASTGTM" in prefix else f"{prefix}_N*_W*_dem.tif"

    for fpath in glob.glob(str(tile_dir / f"{prefix}*dem.tif")):
        fname = os.path.basename(fpath)
        # 解析文件名: ASTGTMV003_N32W097_dem.tif 或 ASTWBDV001_N32W097_dem.tif
        parts = fname.replace(prefix + "_", "").replace("_dem.tif", "")
        if "W" in parts:
            lat_str, lon_str = parts.split("W", 1)
            lat = int(lat_str.replace("N", "").replace("S", ""))
            lon = int(lon_str)
        elif "E" in parts:
            lat_str, lon_str = parts.split("E", 1)
            lat = int(lat_str.replace("N", "").replace("S", ""))
            lon = -int(lon_str)
        else:
            continue

        index[(lat, lon)] = fpath

    log(f"Tile 索引: {prefix} -> {len(index)} tiles")
    return index


def sample_raster(tile_index, prefix, lats, lons, band=1):
    """从 ASTER tile 网格中按经纬度采样栅格值

    tile 覆盖 N{lat}W{lon} 的 1°×1° 区域
    """
    n = len(lats)
    values = np.full(n, np.nan)
    tile_cache = {}

    for i in range(n):
        lat, lon = lats[i], lons[i]

        # 向下取整找到 tile 左下角
        tile_lat = int(np.floor(lat))
        tile_lon = int(np.ceil(abs(lon)))

        key = (tile_lat, tile_lon)
        if key not in tile_index:
            continue

        if key not in tile_cache:
            with rasterio.open(tile_index[key]) as src:
                tile_cache[key] = {
                    "data": src.read(band),
                    "transform": src.transform,
                    "nodata": src.nodata,
                    "shape": (src.height, src.width),
                }

        tile = tile_cache[key]
        col, row = ~tile["transform"] * (lon, lat)
        col = int(np.floor(col))
        row = int(np.floor(row))

        if 0 <= row < tile["shape"][0] and 0 <= col < tile["shape"][1]:
            val = tile["data"][row, col]
            if tile["nodata"] is not None and val == tile["nodata"]:
                continue
            values[i] = val

    return values


def compute_slope(elevations, lats, lons, tile_index):
    """计算每个闪击点的地形坡度 (度)

    使用 3×3 窗口计算最大坡度方向
    """
    n = len(lats)
    slopes = np.full(n, np.nan)
    tile_cache = {}

    for i in range(n):
        lat, lon = lats[i], lons[i]
        tile_lat = int(np.floor(lat))
        tile_lon = int(np.ceil(abs(lon)))
        key = (tile_lat, tile_lon)

        if key not in tile_index:
            continue

        if key not in tile_cache:
            with rasterio.open(tile_index[key]) as src:
                tile_cache[key] = {
                    "data": src.read(1).astype(np.float64),
                    "transform": src.transform,
                    "nodata": src.nodata,
                    "shape": (src.height, src.width),
                    "res_deg": src.res[0],
                }

        tile = tile_cache[key]
        col, row = ~tile["transform"] * (lon, lat)
        col = int(np.floor(col))
        row = int(np.floor(row))

        if row < 1 or row >= tile["shape"][0] - 1 or col < 1 or col >= tile["shape"][1] - 1:
            continue

        # 3×3 窗口
        window = tile["data"][row-1:row+2, col-1:col+2]
        if np.any(window == tile["nodata"]) if tile["nodata"] else False:
            continue

        # Horn 坡度计算
        dz_dx = (window[1, 2] - window[1, 0]) / 2
        dz_dy = (window[2, 1] - window[0, 1]) / 2
        # 转为度: arctan(sqrt(dz_dx^2 + dz_dy^2) / (res * 111000))
        res_m = tile["res_deg"] * 111000 * np.cos(np.radians(lat))
        slope = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2) / res_m))
        slopes[i] = slope

    return slopes


def compute_water_distance(att_values, lats, lons, tile_index_att):
    """计算每个闪击点到最近水体的距离 (粗略, 单位: km)

    简化版: 如果该点是水体则距离=0, 否则在 tile 内搜索最近水体像素
    """
    n = len(lats)
    distances = np.full(n, np.nan)

    for i in range(n):
        if np.isnan(att_values[i]):
            continue
        if att_values[i] > 0:
            distances[i] = 0.0
            continue

        # 对于陆地闪击, 计算到最近水体的粗略距离
        lat, lon = lats[i], lons[i]
        tile_lat = int(np.floor(lat))
        tile_lon = int(np.ceil(abs(lon)))
        key = (tile_lat, tile_lon)

        if key not in tile_index_att:
            continue

        with rasterio.open(tile_index_att[key]) as src:
            att = src.read(1)
            transform = src.transform

            # 闪击在 tile 中的行列
            col, row = ~transform * (lon, lat)
            col = int(np.floor(col))
            row = int(np.floor(row))

            # 搜索半径 (像素数), 30m 分辨率下 100 像素 = 3km
            search_r = 200  # 6km 搜索半径
            r_min = max(0, row - search_r)
            r_max = min(att.shape[0], row + search_r + 1)
            c_min = max(0, col - search_r)
            c_max = min(att.shape[1], col + search_r + 1)

            sub = att[r_min:r_max, c_min:c_max]
            water_pixels = np.argwhere(sub > 0)

            if len(water_pixels) == 0:
                distances[i] = 6.0  # 超过搜索半径
                continue

            # 计算最近水体像素的距离
            center_r = row - r_min
            center_c = col - c_min
            dists = np.sqrt((water_pixels[:, 0] - center_r)**2 +
                            (water_pixels[:, 1] - center_c)**2)
            min_dist_pixels = dists.min()
            # 30m/pixel -> km
            distances[i] = min_dist_pixels * 0.030

    return distances


def main():
    log("=" * 60)
    log("ASTER 地形 × GLM 闪电分布联动分析")
    log("=" * 60)

    # 1. 提取 GLM 闪电闪击
    log("\n[1/5] 提取 GLM 闪电闪击数据...")
    lats, lons, times = extract_glm_flashes()

    if len(lats) == 0:
        log("ERCOT 区域无闪电, 退出")
        return

    # 2. 构建 ASTER tile 索引
    log("\n[2/5] 构建 ASTER tile 索引...")
    gdem_index = build_tile_index(GDEM_DIR, "ASTGTMV003")
    wbd_att_index = {}
    for fpath in glob.glob(str(WBD_DIR / "ASTWBDV001_*_att.tif")):
        fname = os.path.basename(fpath)
        parts = fname.replace("ASTWBDV001_N", "").replace("_att.tif", "")
        if "W" in parts:
            lat_str, lon_str = parts.split("W", 1)
            lat = int(lat_str.replace("N", "").replace("S", ""))
            lon = int(lon_str)
            wbd_att_index[(lat, lon)] = fpath

    log(f"GDEM tiles: {len(gdem_index)}, WBD att tiles: {len(wbd_att_index)}")

    # 3. 采样地形高程
    log("\n[3/5] 采样地形高程和水体属性...")
    log("  采样 GDEM 高程...")
    elevations = sample_raster(gdem_index, "ASTGTMV003", lats, lons, band=1)
    valid_elev = np.count_nonzero(~np.isnan(elevations))
    log(f"  高程采样成功: {valid_elev}/{len(lats)} ({valid_elev/len(lats)*100:.1f}%)")

    if valid_elev > 0:
        log(f"  高程范围: {np.nanmin(elevations):.0f}m ~ {np.nanmax(elevations):.0f}m")
        log(f"  高程均值: {np.nanmean(elevations):.1f}m, 中位数: {np.nanmedian(elevations):.1f}m")

    # 采样水体属性
    log("  采样 WBD 水体属性...")
    att_values = sample_raster(wbd_att_index, "ASTWBDV001", lats, lons, band=1)
    valid_att = np.count_nonzero(~np.isnan(att_values))
    log(f"  水体采样成功: {valid_att}/{len(lats)}")

    wbd_labels = {0: "陆地", 1: "海洋", 2: "湖泊", 3: "河流"}
    for v, label in wbd_labels.items():
        count = np.count_nonzero(att_values == v)
        if count > 0:
            log(f"    {label}: {count} ({count/valid_att*100:.1f}%)")

    # 4. 计算坡度
    log("\n  计算地形坡度...")
    slopes = compute_slope(elevations, lats, lons, gdem_index)
    valid_slope = np.count_nonzero(~np.isnan(slopes))
    log(f"  坡度计算成功: {valid_slope}/{len(lats)}")
    if valid_slope > 0:
        log(f"  坡度范围: {np.nanmin(slopes):.2f}° ~ {np.nanmax(slopes):.2f}°")
        log(f"  坡度均值: {np.nanmean(slopes):.2f}°, 中位数: {np.nanmedian(slopes):.2f}°")

    # 计算水体距离
    log("  计算到最近水体距离...")
    water_dists = compute_water_distance(att_values, lats, lons, wbd_att_index)
    valid_dist = np.count_nonzero(~np.isnan(water_dists))
    log(f"  距离计算成功: {valid_dist}/{len(lats)}")
    if valid_dist > 0:
        log(f"  水体距离: {np.nanmin(water_dists):.2f}km ~ {np.nanmax(water_dists):.2f}km")
        log(f"  距离均值: {np.nanmean(water_dists):.2f}km, 中位数: {np.nanmedian(water_dists):.2f}km")

    # 5. 统计分析
    log("\n[4/5] 统计分析...")

    # 组装 DataFrame
    df = pd.DataFrame({
        "lat": lats,
        "lon": lons,
        "elevation_m": elevations,
        "slope_deg": slopes,
        "water_body_type": att_values,
        "water_body_label": [wbd_labels.get(int(v), "未知") if not np.isnan(v) else "无数据"
                              for v in att_values],
        "water_dist_km": water_dists,
    })

    # 时间
    if len(times) > 0:
        df["time"] = times

    # 高程分带统计
    elev_bins = [-100, 0, 100, 200, 300, 400, 500, 600, 800, 1000, 3000]
    elev_labels = ["<0m", "0-100m", "100-200m", "200-300m", "300-400m",
                   "400-500m", "500-600m", "600-800m", "800-1000m", ">1000m"]
    df["elev_band"] = pd.cut(df["elevation_m"], bins=elev_bins, labels=elev_labels, right=False)

    # 坡度分带统计
    slope_bins = [-1, 0.5, 1, 2, 3, 5, 10, 20, 90]
    slope_labels = ["<0.5°", "0.5-1°", "1-2°", "2-3°", "3-5°", "5-10°", "10-20°", ">20°"]
    df["slope_band"] = pd.cut(df["slope_deg"], bins=slope_bins, labels=slope_labels, right=False)

    # 水体距离分带
    dist_bins = [-0.1, 0.01, 0.5, 1, 2, 3, 5, 10]
    dist_labels = ["0km(水体上)", "0-0.5km", "0.5-1km", "1-2km", "2-3km", "3-5km", ">5km"]
    df["dist_band"] = pd.cut(df["water_dist_km"], bins=dist_bins, labels=dist_labels, right=False)

    # 输出统计表
    log("\n--- 高程分带统计 ---")
    elev_stats = df.groupby("elev_band", observed=False).agg(
        flash_count=("lat", "count"),
        elev_mean=("elevation_m", "mean"),
        slope_mean=("slope_deg", "mean"),
    ).reset_index()
    elev_stats["flash_pct"] = (elev_stats["flash_count"] / elev_stats["flash_count"].sum() * 100).round(1)
    print(elev_stats.to_string(index=False))

    log("\n--- 坡度分带统计 ---")
    slope_stats = df.groupby("slope_band", observed=False).agg(
        flash_count=("lat", "count"),
        slope_mean=("slope_deg", "mean"),
        elev_mean=("elevation_m", "mean"),
    ).reset_index()
    slope_stats["flash_pct"] = (slope_stats["flash_count"] / slope_stats["flash_count"].sum() * 100).round(1)
    print(slope_stats.to_string(index=False))

    log("\n--- 水体类型统计 ---")
    water_stats = df.groupby("water_body_label").agg(
        flash_count=("lat", "count"),
        elev_mean=("elevation_m", "mean"),
        water_dist_mean=("water_dist_km", "mean"),
    ).reset_index()
    water_stats["flash_pct"] = (water_stats["flash_count"] / water_stats["flash_count"].sum() * 100).round(1)
    print(water_stats.to_string(index=False))

    log("\n--- 水体距离分带统计 ---")
    dist_stats = df.groupby("dist_band", observed=False).agg(
        flash_count=("lat", "count"),
        elev_mean=("elevation_m", "mean"),
    ).reset_index()
    dist_stats["flash_pct"] = (dist_stats["flash_count"] / dist_stats["flash_count"].sum() * 100).round(1)
    print(dist_stats.to_string(index=False))

    # 保存数据
    csv_path = OUTPUT_DIR / "terrain_lightning_stats.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    log(f"\n数据保存: {csv_path}")

    # 保存汇总统计
    stats_path = OUTPUT_DIR / "terrain_lightning_summary.csv"
    with open(stats_path, "w", encoding="utf-8-sig") as f:
        f.write("=== 高程分带统计 ===\n")
        elev_stats.to_csv(f, index=False)
        f.write("\n=== 坡度分带统计 ===\n")
        slope_stats.to_csv(f, index=False)
        f.write("\n=== 水体类型统计 ===\n")
        water_stats.to_csv(f, index=False)
        f.write("\n=== 水体距离分带统计 ===\n")
        dist_stats.to_csv(f, index=False)
    log(f"汇总统计保存: {stats_path}")

    # 6. 可视化
    log("\n[5/5] 生成可视化图表...")
    try:
        generate_visualizations(df, elev_stats, slope_stats, water_stats, dist_stats)
    except Exception as e:
        log(f"可视化错误: {e}")
        import traceback
        traceback.print_exc()

    # 总结
    log("\n" + "=" * 60)
    log("分析完成!")
    log(f"  闪击总数: {len(df)}")
    log(f"  高程覆盖: {valid_elev}/{len(lats)} ({valid_elev/len(lats)*100:.1f}%)")
    log(f"  高程范围: {np.nanmin(elevations):.0f}m ~ {np.nanmax(elevations):.0f}m")
    log(f"  坡度范围: {np.nanmin(slopes):.2f}° ~ {np.nanmax(slopes):.2f}°")
    log(f"  输出目录: {OUTPUT_DIR}")
    log("=" * 60)

    # 关键发现
    log("\n关键发现:")
    top_elev = elev_stats.sort_values("flash_count", ascending=False).iloc[0]
    log(f"  闪电最密集高程带: {top_elev['elev_band']} ({top_elev['flash_count']}次, {top_elev['flash_pct']}%)")
    top_slope = slope_stats.sort_values("flash_count", ascending=False).iloc[0]
    log(f"  闪电最密集坡度带: {top_slope['slope_band']} ({top_slope['flash_count']}次, {top_slope['flash_pct']}%)")
    top_water = water_stats.sort_values("flash_count", ascending=False).iloc[0]
    log(f"  闪电最密集水体类型: {top_water['water_body_label']} ({top_water['flash_count']}次, {top_water['flash_pct']}%)")
    top_dist = dist_stats.sort_values("flash_count", ascending=False).iloc[0]
    log(f"  闪电最密集水体距离: {top_dist['dist_band']} ({top_dist['flash_count']}次, {top_dist['flash_pct']}%)")

    # 高程相关性
    corr_elev = np.corrcoef(df["elevation_m"][~np.isnan(df["elevation_m"])],
                            df["slope_deg"][~np.isnan(df["elevation_m"])])[0, 1]
    log(f"  高程-坡度相关系数: {corr_elev:.3f}")


def generate_visualizations(df, elev_stats, slope_stats, water_stats, dist_stats):
    """生成可视化图表"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    import matplotlib.cm as cm

    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    valid = df.dropna(subset=["elevation_m"]).copy()

    # --- 图1: 高程 vs 闪击散点图 ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("ASTER 地形 × GLM 闪电分布联动分析\n(2026-09-07 00:00~02:00 UTC, ERCOT 区域)", fontsize=14)

    # 1a: 高程分带
    ax = axes[0, 0]
    colors = cm.viridis(Normalize(0, len(elev_stats))(np.arange(len(elev_stats))))
    bars = ax.bar(range(len(elev_stats)), elev_stats["flash_count"], color=colors)
    ax.set_xticks(range(len(elev_stats)))
    ax.set_xticklabels(elev_stats["elev_band"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("闪击数")
    ax.set_title("高程分带闪电分布")
    for bar, pct in zip(bars, elev_stats["flash_pct"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"{pct}%", ha="center", va="bottom", fontsize=7)

    # 1b: 坡度分带
    ax = axes[0, 1]
    colors = cm.plasma(Normalize(0, len(slope_stats))(np.arange(len(slope_stats))))
    bars = ax.bar(range(len(slope_stats)), slope_stats["flash_count"], color=colors)
    ax.set_xticks(range(len(slope_stats)))
    ax.set_xticklabels(slope_stats["slope_band"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("闪击数")
    ax.set_title("坡度分带闪电分布")
    for bar, pct in zip(bars, slope_stats["flash_pct"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"{pct}%", ha="center", va="bottom", fontsize=7)

    # 1c: 水体类型
    ax = axes[1, 0]
    w_labels = water_stats["water_body_label"].tolist()
    w_counts = water_stats["flash_count"].tolist()
    colors_w = ["#8B4513", "#1E90FF", "#32CD32", "#FFD700"][:len(w_labels)]
    bars = ax.bar(range(len(w_labels)), w_counts, color=colors_w)
    ax.set_xticks(range(len(w_labels)))
    ax.set_xticklabels(w_labels, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("闪击数")
    ax.set_title("水体类型闪电分布")
    for bar, pct in zip(bars, water_stats["flash_pct"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"{pct}%", ha="center", va="bottom", fontsize=8)

    # 1d: 水体距离
    ax = axes[1, 1]
    colors_d = cm.cool(Normalize(0, len(dist_stats))(np.arange(len(dist_stats))))
    bars = ax.bar(range(len(dist_stats)), dist_stats["flash_count"], color=colors_d)
    ax.set_xticks(range(len(dist_stats)))
    ax.set_xticklabels(dist_stats["dist_band"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("闪击数")
    ax.set_title("水体距离闪电分布")
    for bar, pct in zip(bars, dist_stats["flash_pct"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"{pct}%", ha="center", va="bottom", fontsize=7)

    plt.tight_layout()
    plot_path = OUTPUT_DIR / "terrain_lightning_density.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    log(f"  分带密度图: {plot_path}")

    # --- 图2: 空间散点图 ---
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    scatter = ax.scatter(valid["lon"], valid["lat"],
                        c=valid["elevation_m"], cmap="terrain",
                        s=3, alpha=0.5, edgecolors="none")
    plt.colorbar(scatter, label="高程 (m)", shrink=0.8)
    ax.set_xlabel("经度 (°W)")
    ax.set_ylabel("纬度 (°N)")
    ax.set_title(f"ERCOT 闪电闪击空间分布 (按高程着色)\n共 {len(valid)} 个闪击, 2026-09-07 00:00~02:00 UTC")
    ax.set_xlim(-107, -93)
    ax.set_ylim(25, 34)
    ax.grid(True, alpha=0.3)
    plot_path = OUTPUT_DIR / "terrain_lightning_scatter.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    log(f"  空间散点图: {plot_path}")

    # --- 图3: 高程-闪击密度双轴图 ---
    fig, ax1 = plt.subplots(1, 1, figsize=(12, 6))

    # 高程分布直方图 (所有ERCOT区域采样)
    # 使用有效闪击点的高程做直方图
    ax2 = ax1.twinx()

    bins = np.arange(0, 1200, 50)
    counts, bin_edges = np.histogram(valid["elevation_m"], bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    ax1.bar(bin_centers, counts, width=45, alpha=0.7, color="steelblue", label="闪击数")
    ax1.set_xlabel("高程 (m)")
    ax1.set_ylabel("闪击数", color="steelblue")
    ax1.tick_params(axis="y", labelcolor="steelblue")

    # 叠加闪击密度 (闪击数/高程区间)
    density = counts / 50  # per meter
    ax2.plot(bin_centers, density, "r-o", linewidth=2, markersize=4, label="密度")
    ax2.set_ylabel("闪击密度 (个/50m)", color="red")
    ax2.tick_params(axis="y", labelcolor="red")

    ax1.set_title("高程分带闪电闪击密度分布")
    ax1.grid(True, alpha=0.3)
    fig.legend(loc="upper right", bbox_to_anchor=(0.9, 0.95))

    plt.tight_layout()
    plot_path = OUTPUT_DIR / "terrain_lightning_elev_profile.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    log(f"  高程密度剖面图: {plot_path}")


if __name__ == "__main__":
    main()
