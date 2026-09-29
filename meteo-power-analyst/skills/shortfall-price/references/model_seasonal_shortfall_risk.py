"""季节预报 → 光伏缺口风险概率化 (ERCOT, 未来45天, 50成员)

动机 (PS-024/025/026 遗留): 缺口×电价链路已量化"相对全机型云"的缺口量级与
持续期, 但都是【事后/past】口径。本脚本用 Open-Meteo Seasonal (EC46/SEAS5,
PS-017 已验证精度) 的 50 成员逐日短波辐射聚合预报, 给**未来 45 天**逐日/逐周
"光伏缺日"风险一个客观概率分布, 并把"缺日×高温"(危险云系, PS-026) 与
"连阴 streak"(PS-025/026 最长25-26天) 的天气先验做出来。

口径与链路:
  1. 晴空基准: pvlib clearsky.haurwitz 逐日 GHI 总量 (MJ/m2) —— 与 seasonal
     shortwave_radiation_sum 同量纲, 相除得纯云量传输率 τ∈[0,1]
  2. fleet 聚合: 141 座光伏电站(30.89GW)按最近站点归属, 太阳容量加权出 fleet 日传输率
  3. 缺口映射: sf_en[d,m] = fleet_clear_daily[doy]×(1-τ_FLEET[d,m])
     ⚠ SHORT: 日聚合口径, 无法分辨日内云的"相位" (全多云半天 vs 全天50%云
     同日总短波, 但小时尖峰不同) → 本输出是**日能源下限**口径
  4. 风险事件: 缺日=τ<0.5; 热日=1d max 温度≥阈值; 危险=缺∧热; 连阴=成员序列max run
  5. 诚实声明: seasonal 集合欠扩散(underdispersion), 无多年回算recalibration → 
     概率是"原始集合频率", 非校准后概率; 可信信号在周/月聚合量与相对异常

用法: python skills/shortfall-price/references/model_seasonal_shortfall_risk.py
输出: data/openmeteo_seasonal/seasonal_shortfall_risk_{运行日}.csv
      data/openmeteo_seasonal/seasonal_streak_risk_{运行日}.csv
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import pvlib
from pvlib import clearsky, solarposition

D = r"c:\work\meteo\data\openmeteo_seasonal"
PLANT_FILE = r"c:\work\meteo\data\nsrdb\ercot_solar_plants_pixels_2025.csv"
CLEARSKY_FLT = r"c:\work\meteo\data\nsrdb\pv_clearsky_hourly_2025_2026.csv"
SUNPOOR_TAU = 0.50          # fleet 日传输率 < 0.5 → 缺日
HEAT_DEGC = 32.0            # 1d max 温度 ≥ 32°C → 热日 (ERCOT 空调用电)
OUT_DAILY = os.path.join(D, "seasonal_shortfall_risk.csv")
OUT_STREAK = os.path.join(D, "seasonal_streak_risk.csv")
OUT_WEEK = os.path.join(D, "seasonal_shortfall_risk_weekly.csv")


def load_sites():
    """读取 6 站 seasonal JSON, 返回 {站点: {date_index, sw_members, tmax_members}}"""
    sites = {}
    for f in glob.glob(os.path.join(D, "*_seasonal_45d.json")):
        name = os.path.basename(f).replace("_seasonal_45d.json", "")
        d = json.load(open(f, encoding="utf-8"))
        day = d["daily"]
        dates = pd.to_datetime(day["time"])
        sw = np.column_stack([day[f"shortwave_radiation_sum_member{k:02d}"]
                              for k in range(1, 51)])
        tm = np.column_stack([day[f"temperature_2m_max_member{k:02d}"]
                              for k in range(1, 51)])
        sites[name] = {"dates": dates, "sw": sw, "tmax": tm,
                       "lat": d["latitude"], "lon": d["longitude"]}
    return sites


def clear_daily_ghi(site, dates):
    """pvlib clearsky.haurwitz 逐站逐日 GHI 总量 (MJ/m2)"""
    lat, lon = site["lat"], site["lon"]
    out = []
    for dt in dates:
        t = pd.date_range(dt, dt + pd.Timedelta(days=1) - pd.Timedelta(minutes=5),
                          freq="1h", tz="UTC")
        zen = solarposition.get_solarposition(t, lat, lon)["apparent_zenith"]
        ghi = clearsky.haurwitz(zen)
        out.append(np.nansum(ghi) * 3600 / 1e6)
    return np.array(out)


def plant_site_weights(sites):
    """141 座光伏电站按最近站点聚类, 返回 {site: 容量} 权重"""
    pl = pd.read_csv(PLANT_FILE)
    names = list(sites.keys())
    coords = np.array([[sites[n]["lat"], sites[n]["lon"]] for n in names])
    w = {n: 0.0 for n in names}
    for _, r in pl.iterrows():
        dx = coords[:, 0] - r["lat"]
        dy = np.cos(np.radians(r["lat"])) * (coords[:, 1] - r["lon"])
        d2 = dx * dx + dy * dy
        w[names[int(np.argmin(d2))]] += r["capacity_mw"]
    tot = sum(w.values())
    return {k: v / tot for k, v in w.items()}, tot


def fleet_clear_energy_doy():
    """从 141 电站晴空小时序列构建逐 doy 的 fleet 晴空日能源气候 (GWh)"""
    cs = pd.read_csv(CLEARSKY_FLT, index_col=0, parse_dates=True)
    cs.index = pd.to_datetime(cs.index, utc=True)
    cday = cs.resample("D").sum()["clearsky_mw"] / 1e3
    cday = cday[~cday.index.duplicated(keep="first")]
    clim = cday.groupby(cday.index.dayofyear).median()
    return clim


def hist_daily_tau():
    """历史(2025-26) fleet 日传输率 τ = 1 - sf_en/clear_daily 的经验分布.
    用于把季节预报的 τ(过度平滑) 转换成相对气候的缺日尾部概率."""
    s = pd.read_csv(r"c:\work\meteo\data\ercot\shortfall_physical_2025_2026.csv",
                    parse_dates=["time_utc"])
    ts = s["time_utc"]
    daily = pd.DataFrame({
        "cle": s["clearsky_mw"].values, "sf": s["shortfall_phys"].values
    }, index=ts).resample("D").sum()
    daily = daily[daily["cle"] > 1e3]
    tau = (daily["cle"] - daily["sf"]) / daily["cle"]
    return tau.dropna()


def main():
    sites = load_sites()

    # 统一日期轴 (任取一站, 各站应一致)
    dates = list(sites.values())[0]["dates"]
    doy = dates.dayofyear.values
    n_day, n_mem = dates.shape[0], 50

    # --- S1 晴空基准 + fleet 权重 ---
    print("== S1 晴空基准 / 站点分离 ==")
    sw_w, tot_mw = plant_site_weights(sites)
    print(f"  141 座电站 {tot_mw/1000:.1f} GW 按最近站归属权重: "
          + ", ".join(f"{k}={v*100:.0f}%" for k, v in sorted(sw_w.items(), key=lambda x: -x[1])))
    clear = {}
    for n, s in sites.items():
        clear[n] = clear_daily_ghi(s, dates)
        tau0 = np.median(s["sw"][:, 0] / clear[n][0])
        print(f"  {n}: clear 首日 {clear[n][0]:.1f} MJ/m2, 成员τ中位 {tau0:.2f}")

    # --- S2 fleet 传输率 (容量加权) ---
    fleet_tau = np.zeros((n_day, n_mem))
    for n, s in sites.items():
        tau = np.clip(s["sw"] / clear[n][:, None], 0, 1)
        fleet_tau += sw_w[n] * tau
    fleet_tau = np.clip(fleet_tau, 0, 1)

    # --- S3 缺口概率化 ---
    print("\n== S3 缺口概率化 (日能源口径下限 + 气候相对缺日概率) ==")
    clim = fleet_clear_energy_doy()
    fc_clear = np.array([clim.get(d, np.nanmedian(clim.values)) for d in doy])
    print(f"  fleet 晴空日能源气候(该季 {doy.min()}-{doy.max()} doy): "
          f"{fc_clear.min():.0f}~{fc_clear.max():.0f} GWh")
    sf_en = (fc_clear[:, None] * (1.0 - fleet_tau)).clip(min=0)   # (day, mem) GWh

    # 气候相对缺日: 用历史 τ 分布把过度平滑的预报 τ 转成"比气候最差X成"的尾部概率
    tau_hist = hist_daily_tau()
    tau_hist = tau_hist[(tau_hist > 0) & (tau_hist < 1)]
    th_mild = float(np.quantile(tau_hist, 0.25))    # 云量最重 25% 的天
    th_sev = float(np.quantile(tau_hist, 0.10))     # 云量最重 10% 的天
    hist_sf_p50 = float(np.quantile((1 - tau_hist), 0.50))   # 日缺能源分数气候中位
    print(f"  历史日传输率 τ: 中位 {np.median(tau_hist):.2f}, Q25(轻缺日阈) {th_mild:.2f}, "
          f"Q10(重缺日阈) {th_sev:.2f}, n={len(tau_hist)}")

    pct = lambda a, q, axis=None: np.percentile(a, q, axis=axis)
    daily = pd.DataFrame({
        "date": dates,
        "doy": doy,
        "tau_p50": pct(fleet_tau, 50, axis=1),
        "tau_p10": pct(fleet_tau, 10, axis=1),
        "tau_p90": pct(fleet_tau, 90, axis=1),
        "sf_p50": pct(sf_en, 50, axis=1),
        "sf_p90": pct(sf_en, 90, axis=1),
        "sf_p99": pct(sf_en, 99, axis=1),
        "P_轻缺日": (fleet_tau <= th_mild).mean(axis=1),
        "P_重缺日": (fleet_tau <= th_sev).mean(axis=1),
    })
    print(f"  历史 2025-26 日缺口能源: P50 {_hist_sf_en():.0f} GWh")
    print(f"  未来45天: 逐日 P50 缺口中位 {pct(sf_en,50):.0f}, P90 缺口中位 {pct(sf_en,90):.0f} GWh")
    print(f"  未来轻缺日日均概率 {daily['P_轻缺日'].mean():.2f}, "
          f"重缺日 {daily['P_重缺日'].mean():.2f}")

    # --- S4 温度 / 危险组合 (轻缺日×热) ---
    tmx = np.stack([sites[n]["tmax"] for n in sites])
    fleet_tmx = np.zeros((n_day, n_mem))
    for i, n in enumerate(sites):
        fleet_tmx += sw_w[n] * tmx[i]
    heat = (fleet_tmx >= HEAT_DEGC)
    mild = fleet_tau <= th_mild
    daily["tmax_p50"] = pct(fleet_tmx, 50, axis=1)
    daily["P_热日"] = heat.mean(axis=1)
    daily["P_危险"] = (mild & heat).mean(axis=1)
    daily["P_缺非热"] = (mild & ~heat).mean(axis=1)

    # --- 连阴 streak (成员为相干序列, 轻缺日二值) ---
    max_run = np.zeros(n_mem)
    for m in range(n_mem):
        run = best = 0
        for d in range(n_day):
            run = run + 1 if mild[d, m] else 0
            best = max(best, run)
        max_run[m] = best
    streak = pd.Series(max_run)
    r = streak.value_counts().sort_index()

    print(f"\n== S4 危险组合 & 连阴 ==")
    print(f"  逐日 P(危险云系=轻缺∧热): 中位 {daily['P_危险'].median():.3f}, "
          f"最大 {daily['P_危险'].max():.3f} (日 {daily.loc[daily['P_危险'].idxmax(),'date'].date()})")
    print(f"  未来45天 轻缺连阴最大长度成员分布: {r.astype(int).to_dict()}")
    print(f"  P(出现≥5天连阴) = {(max_run >= 5).mean():.2f}, P(≥7天) = {(max_run >= 7).mean():.2f}")

    # --- 周聚合 ---
    wk = np.arange(n_day) // 7 + 1
    wks = np.unique(wk)
    weekly = pd.DataFrame({
        "周": wks,
        "周起": dates.values[[np.where(wk == w)[0][0] for w in wks]],
        "P_轻缺日周均": [daily["P_轻缺日"][wk == w].mean() for w in wks],
        "P_重缺日周均": [daily["P_重缺日"][wk == w].mean() for w in wks],
        "P_危险周均": [daily["P_危险"][wk == w].mean() for w in wks],
        "P_热日周均": [daily["P_热日"][wk == w].mean() for w in wks],
        "sf_P50周中位": [pct(sf_en[wk == w], 50) for w in wks],
        "sf_P90周中位": [pct(sf_en[wk == w], 90) for w in wks],
    })

    # 落盘
    daily.set_index("date").to_csv(OUT_DAILY, encoding="utf-8-sig")
    weekly.to_csv(OUT_WEEK, encoding="utf-8-sig")
    streak.rename("n_members").rename_axis("max_streak_day").to_csv(OUT_STREAK,
                                                                    encoding="utf-8-sig")
    print(f"\n→ {OUT_DAILY}\n→ {OUT_WEEK}\n→ {OUT_STREAK}")


def _hist_sf_en():
    s = pd.read_csv(r"c:\work\meteo\data\ercot\shortfall_physical_2025_2026.csv")
    ts = pd.to_datetime(s["time_utc"])
    daily = pd.Series(s["shortfall_phys"].values, index=ts).resample("D").sum() / 1e3
    return float(np.median(daily.dropna()))


if __name__ == "__main__":
    main()