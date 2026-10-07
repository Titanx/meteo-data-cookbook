"""节点 -> 电站 匹配候选表 (元音骨架法, 供人工复核)"""
import re

import numpy as np
import pandas as pd


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def skel(s):
    s = norm(s)
    s = re.sub(r"[AEIOU]", "", s)
    return s if len(s) >= 3 else norm(s)


DROP = {"SLR", "RN", "ALL", "UN1", "G", "PV1", "SOLAR", "SOLAR1", "UNIT1", "1", "WR1"}


def node_prefix(code):
    toks = code.split("_")
    while toks and toks[-1] in DROP:
        toks.pop()
    while toks and toks[0] == "RN":
        toks.pop(0)
    toks = [re.sub(r"SLR$", "", t) if len(t) > 4 else t for t in toks]
    return "".join(toks)


def main():
    gem = pd.read_csv(r"c:\work\meteo\data\gem\gem_solar_2026-08.csv", low_memory=False)
    tx = gem[gem["subnational"].astype(str).str.contains("Texas", na=False)].copy()
    tx["cap"] = pd.to_numeric(tx["capacity"], errors="coerce")
    d = np.load(r"c:\work\meteo\data\nasa_power\ercot_pv_plants.npz", allow_pickle=True)
    npz = pd.DataFrame({"name": [str(x) for x in d["name"]],
                        "cap": d["capacity_mw"], "src": "NPZ",
                        "lat": d["lat"], "lon": d["lon"]})
    gem_tx = tx[["name", "cap", "Latitude", "Longitude"]].assign(src="GEM").rename(
        columns={"Latitude": "lat", "Longitude": "lon"})
    pool = pd.concat([npz, gem_tx], ignore_index=True).dropna(subset=["name"])
    pool["nn"] = pool["name"].map(norm)
    pool["sk"] = pool["name"].map(skel)

    mt = pd.read_csv(r"c:\work\meteo\data\ercot\pv_node_match.csv")
    todo = mt[mt["match_source"].isna()]["node"].tolist()
    rows = []
    for node in todo:
        pre = node_prefix(node)
        psk = skel(pre)
        hits = pool[(pool["nn"].str.startswith(pre)) |
                    (pool["sk"].str.startswith(psk))]
        hits = hits.sort_values("cap", ascending=False).head(4)
        rows.append({
            "node": node, "prefix": pre, "skel": psk,
            "cands": " | ".join(f"{r['name']} [{r['src']} {r['cap']:.0f}MW]"
                                f"({r['lat']:.2f},{r['lon']:.2f})"
                                for _, r in hits.iterrows())})
    out = pd.DataFrame(rows)
    out.to_csv(r"c:\work\meteo\data\ercot\pv_node_match_candidates.csv", index=False)
    for _, r in out.iterrows():
        print(f"{r['node']:16s} {r['prefix']:8s} -> {r['cands']}")


if __name__ == "__main__":
    main()
