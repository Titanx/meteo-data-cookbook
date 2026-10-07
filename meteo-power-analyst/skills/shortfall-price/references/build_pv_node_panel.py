"""光伏 Resource Node RTM 面板构建 + 节点->电站匹配 (方向3, PS-046 前置)

输入: data/ercot/ercot_rtm_{node}_*.csv  (89 个光伏节点, 窗口 2026-09-07 ~ 2026-10-01,
      部分节点有更宽窗口; 另含 HB_HOUSTON 15min 全期)
      data/nasa_power/ercot_pv_plants.npz  (136 电站逐时 GHI, 含坐标/容量)
      data/gem/gem_solar_2026-08.csv      (GEM 全量光伏电站, 匹配兜底)
输出: data/ercot/pv_node_panel_15min.csv   节点 x 15min tidy (含 hub)
      data/ercot/pv_node_hourly.csv        节点 x 小时宽表 (PS-045 口径: interval_start 1h 均值)
      data/ercot/pv_node_match.csv         节点 -> NPZ/GEM 电站匹配表
      data/ercot/pv_node_coverage.csv      节点覆盖诊断
用法: python skills/shortfall-price/references/build_pv_node_panel.py
"""
import glob
import os
import re

import numpy as np
import pandas as pd

D_ERCOT = r"c:\work\meteo\data\ercot"
D_NPZ = r"c:\work\meteo\data\nasa_power\ercot_pv_plants.npz"
D_GEM = r"c:\work\meteo\data\gem\gem_solar_2026-08.csv"

SOLAR_NODES = [
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

DROP_TOKENS = {"SLR", "RN", "ALL", "UN1", "G", "PV1", "SOLAR", "SOLAR1",
               "UNIT1", "1", "WR1"}


EXTRA_NODES = [
    "ROSELAND_ALL", "PROSPERO_ALL", "JUNO_ALL", "JUNORTH_RN", "LHORN_N_U1_2",
    "COTTON_PAP2", "BRIGHTSD_U1", "CATARINA_B1", "KINGW_ALL", "LANTANA_RN",
    "BAFFIN_ALL", "SAMSON_ALL",
]

# 人工复核匹配 (元音骨架法 review_node_match.py 逐条核对, 2026-10-04):
#   node -> (source, plant); source 取 "NPZ"/"GEM"; plant 为空表示撤销自动误配
MANUAL_MATCH = {
    "ARMD_SLR_RN": ("GEM", "Armadillo Solar Center"),
    "CMPD_SLR_RN": ("GEM", "Compadre solar farm"),
    "DIVR_SLR_RN": ("NPZ", "Diver solar farm"),
    "HOPKNSLR_ALL": ("NPZ", "Hopkins solar farm"),
    "HRMS_SLR_RN": ("GEM", "Hermes Solar PV solar farm"),
    "HRNT_SLR_RN": ("GEM", "Hornet Swisher solar farm"),
    "HRZN_SLR_UN1": ("NPZ", "Horizon Solar"),
    "LMWD_SLR_RN": ("GEM", "Limewood Bell Solar"),
    "MRKM_SLR_RN": ("NPZ", "Markum solar farm"),
    "NRTN_SLR_RN": ("NPZ", "Norton solar farm (United States)"),
    "RADN_SLR_ALL": ("NPZ", "Radian solar farm"),
    "SWFT_SLR_RN": ("NPZ", "Swift Air solar farm"),
    "TYSN_SLR_RN": ("GEM", "Tyson Nick solar farm"),
    "YAPN_SLR_RN": ("GEM", "Yaupon Solar Project"),
    "GRAN_SLR_RN": ("GEM", "Gransolar Texas One solar farm"),
    "SOLARA_UNIT1": ("", ""),  # 自动匹配 Myers Solar 系误配 (contains 假阳性)
    "ROSELAND_ALL": ("NPZ", "Roseland solar farm"),
    "PROSPERO_ALL": ("NPZ", "Prospero Solar"),
    "JUNO_ALL": ("NPZ", "Juno Solar Project (United States)"),
    "JUNORTH_RN": ("NPZ", "Juno Solar Project (United States)"),
    "LHORN_N_U1_2": ("GEM", "Hecate Energy Longhorn solar farm"),
    "COTTON_PAP2": ("NPZ", "Cottonwood Bayou Solar"),
    "SAMSON_ALL": ("NPZ", "Samson Solar Energy"),
}


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def node_prefix(code):
    """从节点代码提取电站名前缀: 去 SLR/RN 等行业后缀 token, token 内部再剥尾部 SLR"""
    toks = [t for t in code.split("_")]
    while toks and toks[-1] in DROP_TOKENS:
        toks.pop()
    while toks and toks[0] == "RN":
        toks.pop(0)
    toks = [re.sub(r"SLR$", "", t) if len(t) > 4 else t for t in toks]
    return "".join(toks)


def match_node(prefix, npz_names, gem_names):
    """前缀匹配: 优先 NPZ (有 GHI), 兜底 GEM; 返回 (source, name)"""
    for src, names in (("NPZ", npz_names), ("GEM", gem_names)):
        cand = [n for n in names if norm(n).startswith(prefix)]
        if not cand:
            cand = [n for n in names if prefix in norm(n) and len(prefix) >= 4]
        if cand:
            return src, sorted(cand, key=len)[0]
    return "", ""


def main():
    # ---- 1. 读节点 CSV (多文件取窗口最宽者) ----
    rows, cov = [], []
    for node in SOLAR_NODES + EXTRA_NODES:
        hits = sorted(glob.glob(os.path.join(D_ERCOT, f"ercot_rtm_{node}_2*.csv")))
        if not hits:
            cov.append({"node": node, "files": 0})
            continue
        best, span = None, -1
        for f in hits:
            m = re.search(r"_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv$", f)
            if not m:
                continue
            sp = (pd.Timestamp(m.group(2)) - pd.Timestamp(m.group(1))).days
            if sp > span:
                best, span = f, sp
        df = pd.read_csv(best)
        t = pd.to_datetime(df["interval_start_utc"]).dt.tz_localize(None)
        rows.append(pd.DataFrame({"ts": t, "node": node, "spp": df["spp"].astype(float)}))
        cov.append({"node": node, "file": os.path.basename(best), "rows": len(df),
                    "first": t.min(), "last": t.max(),
                    "spp_med": df["spp"].median(), "spp_max": df["spp"].max()})
    panel = pd.concat(rows)
    cov = pd.DataFrame(cov)
    print(f"节点文件: {cov['files'].notna().sum() if 'files' in cov else cov['file'].notna().sum()}"
          f" / {len(SOLAR_NODES)}  总行 {len(panel):,}")

    # ---- 2. 加入 Hub (HB_HOUSTON) 15min 作对照行 ----
    hub = pd.read_csv(glob.glob(os.path.join(D_ERCOT, "ercot_rtm_HB_HOUSTON_*.csv"))[0])
    th = pd.to_datetime(hub["interval_start_utc"]).dt.tz_localize(None)
    panel = pd.concat([panel, pd.DataFrame(
        {"ts": th, "node": "HB_HOUSTON", "spp": hub["spp"].astype(float)})])

    # ---- 3. 落盘 15min tidy ----
    panel = panel.sort_values(["node", "ts"])
    panel.to_csv(os.path.join(D_ERCOT, "pv_node_panel_15min.csv"), index=False)

    # ---- 4. 小时宽表 (PS-045 口径: interval_start resample 1h mean) ----
    hourly = (panel.set_index("ts").groupby("node")["spp"]
              .resample("1h").mean().unstack(0).sort_index())
    hourly.index.name = "ts_utc"
    hourly.to_csv(os.path.join(D_ERCOT, "pv_node_hourly.csv"))

    # ---- 5. 节点 -> 电站匹配 ----
    d = np.load(D_NPZ, allow_pickle=True)
    npz_names = [str(x) for x in d["name"]]
    npz_lat, npz_lon, npz_cap = d["lat"], d["lon"], d["capacity_mw"]
    gem = pd.read_csv(D_GEM, low_memory=False)
    gem_tx = gem[gem["subnational"].astype(str).str.contains(
        "Texas", case=False, na=False)].copy()
    gem_names = gem_tx["name"].dropna().unique().tolist()
    print(f"匹配池: NPZ {len(npz_names)} 电站 / GEM TX {len(gem_names)} 电站")

    recs = []
    for node in SOLAR_NODES + EXTRA_NODES:
        pre = node_prefix(node)
        src, name = match_node(pre, npz_names, gem_names)
        if node in MANUAL_MATCH:
            src, name = MANUAL_MATCH[node]
            pre = pre + "*"  # 标记人工复核
        rec = {"node": node, "prefix": pre, "match_source": src, "plant": name}
        if src == "NPZ":
            if name not in npz_names:
                raise KeyError(f"NPZ 中未找到 {name} ({node})")
            i = npz_names.index(name)
            rec.update({"lat": npz_lat[i], "lon": npz_lon[i], "cap_mw": float(npz_cap[i])})
        elif src == "GEM":
            g = gem_tx[gem_tx["name"] == name]
            if len(g):
                rec.update({"lat": float(g["Latitude"].iloc[0]),
                            "lon": float(g["Longitude"].iloc[0]),
                            "cap_mw": float(g["capacity"].max())})
        recs.append(rec)
    mt = pd.DataFrame(recs)
    mt.to_csv(os.path.join(D_ERCOT, "pv_node_match.csv"), index=False)
    cov.to_csv(os.path.join(D_ERCOT, "pv_node_coverage.csv"), index=False)

    n_npz = (mt["match_source"] == "NPZ").sum()
    n_gem = (mt["match_source"] == "GEM").sum()
    cap_all = mt["cap_mw"].sum() / 1000
    cap_npz = mt.loc[mt["match_source"] == "NPZ", "cap_mw"].sum() / 1000
    print(f"匹配: NPZ {n_npz} ({cap_npz:.1f} GW) / GEM {n_gem} / "
          f"未匹配 {(mt['match_source'] == '').sum()}; 匹配容量合计 {cap_all:.1f} GW")
    print("未匹配节点:", ", ".join(mt.loc[mt["match_source"] == "", "node"]))
    print(f"面板: {hourly.shape[0]} 小时 x {hourly.shape[1]} 节点  "
          f"{hourly.index.min()} ~ {hourly.index.max()}")
    print("已保存: pv_node_panel_15min.csv / pv_node_hourly.csv / "
          "pv_node_match.csv / pv_node_coverage.csv")


if __name__ == "__main__":
    main()
