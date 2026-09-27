import numpy as np
import pandas as pd

df = pd.read_csv(r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels.csv")
ok = df[df["nsrdb_index"] >= 0]
big = ok[ok["capacity_mw"] >= 100]
print(f">=100MW: {len(big)} 站, {big['capacity_mw'].sum()/1000:.1f} GW")
for label, sub in [("all>=10MW", ok), (">=100MW", big)]:
    cb = (sub["nsrdb_index"] // 500).values
    u = np.unique(cb)
    gw = sub["capacity_mw"].sum() / 1000
    print(f"{label}: {len(sub)} 站, {len(u)} 个列块, {gw:.1f} GW")
    nch = len(u) * 5 * 3
    print(f"  -> 7月下载量: {len(u)} 列块 x 5 时间块 x 3 分量 = {nch} chunks x 2MB = {nch*2/1000:.1f} GB")
print("7月时间块:", 52128 // 2000, "~", 60959 // 2000)
