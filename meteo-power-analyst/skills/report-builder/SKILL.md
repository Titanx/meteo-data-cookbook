# 单文件 HTML 报告

**状态**: ✅ 可用 — 本包所有主题报告均用此批脚本产出（单文件 HTML，内嵌图表库与字体，零外部依赖）。

**用途**: 把已有结论与数据表组装成可直接交付的单文件 HTML 报告，落到 `output/<slug>/index.html`。

**入口检查**:
1. **先确认结论齐了没有**：按引用知识里的报告骨架逐节对照，缺节先别生成
2. 手上有数据表但没结论 → 回上游 skill（缺口 / 负价 / 出力）先把结论做出来
3. 结论齐 → 选下方对应主题的组装脚本

## 选脚本

| 报告主题 | 脚本 |
|----------|------|
| 负价概率 / 展望（西班牙） | `references/build_spain_negprice_report.py`、`references/build_spain_negprice_v3_report.py`、`references/build_spain_threshold_report.py`、`references/build_spain_noon_report.py` |
| 负价跨境 / 法国侧 / 法国 NWP | `references/build_spain_xborder_report.py`、`references/build_france_noon_report.py`、`references/build_france_nwp_report.py` |
| ES 侧 D-1 预警 | `references/build_spain_nwp_report.py` |
| 光伏缺口（口径统一 / 事件 / 尾部） | `references/build_shortfall_unification_report.py`、`references/build_pv_event_price_report.py`、`references/build_price_tail_report.py` |
| 季节风险 / 转移函数桥 | `references/build_seasonal_risk_report.py`、`references/build_forecast_bridge_report.py` |
| 可逆性 / 工况指纹 | `references/build_reversibility_report.py`、`references/build_fingerprint_report.py` |
| 风电缺口 | `references/build_wind_shortfall_report.py` |
| 西班牙区域工况 / 最小链路 | `references/build_spain_regime_report.py`、`references/build_spain_minchain_report.py` |
| NSRDB × pvlib 验证 | `references/build_nsrdb_pvlib_report.py` |
| 季节预报精度 / 官方口径复核 / 数据源调研 | `references/build_forecast_accuracy_summary.py`、`references/build_spain_entsoe_verification_report.py`、`references/build_spain_market_survey_report.py` |
| 图表数组重建（改图后） | `references/rebuild_full_chart_arrays.py` |

## 使用

```powershell
# 依赖（首次）
pip install pandas numpy

# 生成报告（示例）
python skills/report-builder/references/build_spain_nwp_report.py
# 产出 output/spain_negprice_d1warning/index.html
```

## 交付校验（生成后必做）

- 正文不得残留未替换的 `**` 占位符，不得出现 NaN / inf 字样
- 同一指标在同一区间内的数值，表格与图必须一致
- 图表字体显式指定中文字体，避免显示成方框
- 概率类报告必须带"原始强度 / 校准后 / 实际"三者对照
- 报告里写清数据截止日与口径一句话

## 已知局限

- 报告脚本只做组装，不做计算；数字错了要回上游改，不要在报告脚本里打补丁
- 各报告脚本是**分别演进**的，样式约定不完全一致；新增报告请以最新一个为模板
- `output/` 是生成目录，可随时重建，不进版本库

## 失败处理

- 图表空白 → 先查图表数组 json 是否生成（必要时跑 `references/rebuild_full_chart_arrays.py`）
- 中文变方框 → 字体未内嵌或未指定，改样式后重生成
- 数字与上游对不上 → 停下，回上游核对，禁止在报告里手改数字

> 引用知识（kb/）:
> - `[DEC-20260930-003]` 评预报量效益必须先建持续性基线，且基线不塞冗余日历变量
> - `[MTD-20260907-001]` 气象数据 API 凭证安全管理实践
