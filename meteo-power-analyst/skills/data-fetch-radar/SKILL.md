# 数据获取 · 雷达

**状态**: 🟡 部分可用 — 匿名访问路径探活完成（`references/test_radar_all_anonymous.py`），
MRMS QPE 与 NEXRAD 分块的可用性以探活结果为准；正式取数流程见引用知识中的两条 recipe。
扫描时请注意：本 skill 只含**探活与单点验证**脚本，批量取数脚本在 `data-fetch-satellite` / 引用流程里。

**用途**: 判断雷达数据源在当前环境是否可达，选择可用的匿名路径，并验证单点下载与解析。

**入口检查**:
1. **先跑探活脚本**，别直接上批量：雷达桶的策略会变，先确认今天能不能匿名读
2. 探活通过 → 按引用知识里的流程走正式取数
3. 探活失败 → 显式记录"该源不可用"，改用卫星/再分析替代口径，不要硬试

## 脚本

| 目标 | 脚本 | 说明 |
|------|------|------|
| 全源匿名可达性探活 | `references/test_radar_all_anonymous.py` | **第一条要跑的**：逐桶/逐入口试探 |
| MRMS 单点下载验证 | `references/test_mrms_download.py` | 定量降水产品，验证目录拼接与单文件可读 |
| 第三方影像服务探测 | `references/test_rainviewer_detail.py` | 只做可达性探测，不作正式数据源 |

## 使用

```powershell
# 依赖（首次）
pip install requests pandas numpy

# 第一步：探活
python skills/data-fetch-radar/references/test_radar_all_anonymous.py

# 第二步：单点验证（确认目录规则与解析都通）
python skills/data-fetch-radar/references/test_mrms_download.py
```

## 产出

- 探活结果（终端打印：逐源 可达 / 403 / 404 及原因）
- 单点验证落盘的小样本文件（供解析器联调）

## 数据源与已知局限

| 数据 | 状态 | 已知限制 |
|------|------|----------|
| MRMS 定量降水 | 🟡 单点已验证 | 需按研究区域边界裁剪；目录按小时分片 |
| NEXRAD Level-2 | 🟡 探活为准 | 官方桶匿名访问受限，需走替代路径 |
| 第三方影像服务 | 🟡 仅探测 | 许可与稳定性不确定，不作正式源 |

## 失败处理

- 桶返回 403 → 换替代路径（见引用知识）；**不要**尝试伪造请求头绕过
- 目录 404 → 优先怀疑时间戳格式（UTC 还是本地、小时是否有前导零）
- 批量前一定要先单点验证，否则容易把"目录规则错了"误判成"数据不存在"

> 引用知识（kb/）:
> - `[MTD-20260812-001]` 气象雷达数据匿名获取综合指南
> - `[PIT-20260812-001]` NEXRAD 官方 S3 桶匿名访问限制与替代方案
> - `[RCP-20260812-001]` NEXRAD 雷达实时分块数据下载流程（unidata chunks）
> - `[RCP-20260927-001]` MRMS 雷达定量降水 (QPE) 下载与 ERCOT 裁剪流程
