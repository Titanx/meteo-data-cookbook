import pandas as pd

f = pd.read_csv(r"c:\work\meteo\data\ercot\ercot_fuel_type_data_2022-07.csv")
sun = f[f["fuel_code"] == "SUN"].set_index("time")["value"]
sun.index = pd.to_datetime(sun.index)
peak = sun.idxmax()
print(f"2022-07 峰值: {sun.max()} MW @ {peak} (UTC)")
print("若为 UTC, 当地 CDT = UTC-5:", peak - pd.Timedelta(hours=5), "(应在正午~14点)")
print(sun.loc["2022-07-01 12:00":"2022-07-01 23:00"].to_string())
