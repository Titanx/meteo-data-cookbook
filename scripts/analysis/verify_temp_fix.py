"""对比 温度参数化 vs HRRR 实测温度 两版模型在热浪窗口的表现
输入: ercot_pv_power_2022-07_paramtemp.csv (参数化) / ercot_pv_power_2022-07.csv (HRRR)
输出: 分窗口指标表 (stdout)
"""
import numpy as np
import pandas as pd

PARAM = r"c:\work\meteo\data\nsrdb\ercot_pv_power_2022-07_paramtemp.csv"
HRRR = r"c:\work\meteo\data\nsrdb\ercot_pv_power_2022-07.csv"


def load(path):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.columns = ["model", "eia"]
    return df.dropna()


def metrics(j):
    r = j["model"].corr(j["eia"])
    mae = (j["model"] - j["eia"]).abs().mean()
    bias = (j["model"] - j["eia"]).mean()
    return r, mae, bias


def main():
    a, b = load(PARAM), load(HRRR)

    windows = [
        ("全月", lambda x: x),
        ("热浪 07-13~18", lambda x: x["2022-07-13":"2022-07-18"]),
        ("非热浪其余日", lambda x: x[~x.index.normalize().isin(
            pd.date_range("2022-07-13", "2022-07-18"))]),
        ("热浪正午 16-22UTC", lambda x: x["2022-07-13":"2022-07-18"]
            .between_time("16:00", "22:00")),
        ("07-18 (最差日)", lambda x: x.loc["2022-07-18"]),
    ]

    print(f"{'窗口':<18s} {'参数化 r':>9s} {'HRRR r':>9s} | "
          f"{'参数MAE':>8s} {'HRRR MAE':>9s} | "
          f"{'参数偏差':>8s} {'HRRR偏差':>8s}")
    for name, sel in windows:
        ja, jb = sel(a), sel(b)
        ra, ma, ba = metrics(ja)
        rb, mb, bb = metrics(jb)
        print(f"{name:<18s} {ra:>9.4f} {rb:>9.4f} | "
              f"{ma:>7.0f} {mb:>8.0f} | {ba:>+8.0f} {bb:>+8.0f}")

    # 逐日能量偏差对比 (热浪日)
    da = a.resample("1D").sum() / 1000
    db = b.resample("1D").sum() / 1000
    print("\n热浪期逐日能量 (GWh): 日期 | 参数偏差 | HRRR偏差")
    for t in pd.date_range("2022-07-13", "2022-07-18", tz="UTC"):
        ba_ = da.loc[t, "model"] - da.loc[t, "eia"]
        bb_ = db.loc[t, "model"] - db.loc[t, "eia"]
        print(f"  {t.date()} | {ba_:+6.2f} | {bb_:+6.2f}")

    # 温度本身对输出的影响: 5min 尺度 fleet 均值差
    diff = (b["model"] - a["model"]).dropna()
    print(f"\nHRRR版 - 参数版 出力差: 均值 {diff.mean():+.0f} MW, "
          f"最小 {diff.min():+.0f}, 最大 {diff.max():+.0f}")
    print("(负=实测温度比参数化更热→出力更低)")


if __name__ == "__main__":
    main()
