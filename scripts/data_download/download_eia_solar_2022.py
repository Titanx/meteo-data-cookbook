"""EIA API 补拉 2022 年 7 月 ERCOT 小时级燃料数据 (光伏出力验证基准)
输出: data/ercot/ercot_fuel_type_data_2022-07.csv (与现有 fuel_type 系列同构)
用法: python scripts/data_download/download_eia_solar_2022.py
"""
import os
import time

import pandas as pd
import requests

EIA_BASE = "https://api.eia.gov/v2"
OUT = r"c:\work\meteo\data\ercot\ercot_fuel_type_data_2022-07.csv"


def load_api_key():
    for line in open(r"c:\work\meteo\.env"):
        line = line.strip()
        if line.startswith("EIA_API_KEY"):
            return line.split("=", 1)[1].strip()
    raise SystemExit("EIA_API_KEY 未找到于 .env")


def main():
    key = load_api_key()
    path = "electricity/rto/fuel-type-data/data/"
    rows = []
    for month_start, month_end in [("2022-07-01T00", "2022-07-31T23")]:
        offset = 0
        while True:
            params = {
                "api_key": key,
                "frequency": "hourly",
                "data[0]": "value",
                "facets[respondent][0]": "ERCO",
                "start": month_start,
                "end": month_end,
                "offset": offset,
                "length": 5000,
            }
            r = requests.get(f"{EIA_BASE}/{path}", params=params, timeout=60)
            r.raise_for_status()
            d = r.json()["response"]
            for x in d["data"]:
                rows.append({
                    "time": x["period"].replace("T", " "),
                    "respondent": "ERCO",
                    "respondent_name": "Electric Reliability Council of Texas, Inc.",
                    "fuel_code": x["fueltype"],
                    "type_name": x.get("fuel-type", ""),
                    "value": x["value"],
                    "units": x.get("units", "megawatthours"),
                })
            total = int(d.get("total", 0))
            offset += len(d["data"])
            print(f"{month_start[:7]}: {offset}/{total}")
            if not d["data"] or offset >= total:
                break
            time.sleep(1)

    df = pd.DataFrame(rows)
    # 现有系列 time 格形 'YYYY-MM-DD HH:MM:SS'
    df["time"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(OUT, index=False)
    print(f"已保存: {OUT}, {len(df)} 行")
    sun = df[df["fuel_code"] == "SUN"]
    print(f"SUN 行数: {len(sun)}, 峰值出力: {sun['value'].max()} MW")


if __name__ == "__main__":
    main()
