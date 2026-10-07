"""把 pv_node_shock 各 CSV 编译成 report assets/charts_data.js (方向3 图表数据)"""
import json
import os

import numpy as np
import pandas as pd

D = r"c:\work\meteo\data\ercot"
OUT = r"c:\work\meteo\output\pv_node_shock\assets\charts_data.js"

prem = pd.read_csv(os.path.join(D, "pv_node_hourly_premium.csv"),
                   index_col=0, parse_dates=True)
node_cols = [c for c in prem.columns
             if c not in ("HB_HOUSTON", "event", "sf_gw")]
ev = prem["event"].astype(bool)
hub = prem["HB_HOUSTON"]
n_med = prem[node_cols].median(axis=1)
n_p90 = prem[node_cols].quantile(0.9, axis=1)

timeline = {
    "ts": [t.isoformat() for t in prem.index],
    "hub": [round(v, 3) if np.isfinite(v) else None for v in hub],
    "nmed": [round(v, 3) if np.isfinite(v) else None for v in n_med],
    "np90": [round(v, 3) if np.isfinite(v) else None for v in n_p90],
    "event": [bool(v) for v in ev],
    "sf": [round(v, 2) if np.isfinite(v) else None for v in prem["sf_gw"]],
}

disp = pd.read_csv(os.path.join(D, "pv_node_dispersion.csv"),
                   index_col=0, parse_dates=True)
disp = disp[disp["is_daytime"] & disp["p9010"].notna() & disp["sf_gw"].notna()]
dispersion = {
    "ts": [t.isoformat() for t in disp.index],
    "p9010": [round(v, 3) for v in disp["p9010"]],
    "sf": [round(v, 2) for v in disp["sf_gw"]],
    "event": [bool(v) for v in disp["is_event"]],
}

spikes = pd.read_csv(os.path.join(D, "pv_node_spikes.csv"))
spikes = spikes.sort_values("max_ev", ascending=False).head(10)
spike_list = [{"node": r["node"], "max": round(float(r["max_ev"]), 0)}
              for _, r in spikes.iterrows()]

with open(OUT, "w", encoding="utf-8") as f:
    f.write("// 由 make_pv_node_charts_data.py 生成, 数据: pv_node_hourly_premium / dispersion / spikes\n")
    f.write("window.PV_DATA = ")
    json.dump({"timeline": timeline, "dispersion": dispersion,
               "spikes": spike_list}, f, ensure_ascii=False)
    f.write(";\n")
print(f"OK -> {OUT}")
print(f"  timeline {len(timeline['ts'])}h, dispersion {len(dispersion['ts'])}h,"
      f" top spikes {len(spike_list)}")
