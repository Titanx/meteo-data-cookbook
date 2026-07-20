# 气象数据下载实战指南

> 基于 2026-07-18 ~ 2026-07-20 的一手实测验证，覆盖卫星数据（葵花 8/9、GOES-19）和地面观测（Meteostat 246 机场）两大领域。

现有气象开源项目要么是工具库（satpy / meteostat），要么是数据源索引（awesome-meteorology），本项目的定位是**第三层：实战经验沉淀**——怎么下、踩过什么坑、实测数据是多少。

## 为什么需要这个项目

| 已有项目类型 | 代表 | 覆盖了什么 | 没覆盖什么 |
|------------|------|-----------|-----------|
| 工具库 | satpy / meteostat / MetPy | API 和代码 | 使用陷阱、实测数据 |
| 数据源索引 | awesome-meteorology / open-earth-data-guide | "在哪下" | "怎么下、踩过什么坑" |
| **本项目** | — | — | **下载流程 + 陷阱 + 实测验证** |

## 知识库结构

```
meteo-data-cookbook/
├── README.md                   # 本文件
├── LICENSE                     # MIT
├── .gitignore
├── .knowledge/                 # 知识库主体
│   ├── catalog.md              # 全景目录
│   ├── log.md                  # 变更日志
│   └── tech/
│       ├── catalog.md          # 技术条目索引
│       ├── guidelines/         # 最佳实践
│       │   ├── GL-004.md       # Open-Meteo API 使用指南
│       │   └── GL-005.md       # Meteostat 地面观测数据使用指南
│       ├── pitfalls/           # 已知陷阱
│       │   └── PF-004.md       # Meteostat 区域数据下载陷阱
│       └── processes/          # 技术流程
│           ├── PS-003.md       # 葵花 8/9 卫星数据下载流程
│           ├── PS-004.md       # GOES-16/18/19 卫星数据下载流程
│           └── PS-005.md       # SURFRAD 地表辐射实测数据下载流程
└── scripts/
    └── data_download/          # 19 个实测验证脚本
```

> `data/` 目录不纳入 git（可通过脚本重新下载），运行脚本后会自动创建。

## 条目清单（全部 verified）

| ID | 标题 | 核心内容 |
|----|------|---------|
| GL-004 | Open-Meteo API 使用指南 | 免 API key、ERA5 历史 17 天、预报 168h、批量请求 |
| GL-005 | Meteostat 地面观测数据使用指南 | 246 机场 847 CSV 180.4MB、站点 ID 复用 3-5x 提速、**小时数据延迟仅 12 分钟** |
| PF-004 | Meteostat 区域数据下载陷阱 | 中国站点稀疏需 200km 半径、缅甸日数据缺失、越南 3 机场无数据 |
| PS-003 | 葵花 8/9 卫星数据下载流程 | AWS S3 匿名访问、FLDK 分段下载省 80%、白天时次选择、HSD→AHI-L1b-FLDK 目录迁移 |
| PS-004 | GOES-16/18/19 卫星数据下载流程 | AWS S3 匿名访问、ABI L1b RadF、真彩色合成（手动 RGB + gamma）、与 Himawari 对比 |
| PS-005 | SURFRAD 地表辐射实测数据下载流程 | 匿名 HTTPS、7 站美国辐射网、1 分钟 GHI/DNI/DHI、当天实时追加、1.14GB 覆盖 2025-2026 |

## 数据源覆盖

### 卫星数据

| 卫星 | 数据源 | 访问方式 | 实时性 | 实测验证 |
|------|--------|---------|--------|---------|
| 葵花 9（Himawari-9） | AWS S3 `noaa-himawari9` | 匿名 UNSIGNED | 实时（10 分钟间隔） | 2026-07-20 02:02 UTC 最新 |
| GOES-19 | AWS S3 `noaa-goes19` | 匿名 UNSIGNED | 实时 | 2026-07-20 01:30 UTC 全圆盘 + 真彩色图 |

### 地表辐射实测

| 数据源 | 分辨率 | 覆盖 | 访问方式 | 实测验证 |
|--------|--------|------|---------|---------|
| SURFRAD | 1 分钟 | 美国 7 站 | 匿名 HTTPS | 2026-07-20 7 站×7 天，GHI 峰值 1058-1382 W/m² |

### 地面观测

| 区域 | 机场数 | 文件数 | 数据量 | 成功率 |
|------|--------|--------|--------|--------|
| 中国 | 46 | 187 | 37.8 MB | 100% |
| 东亚东南亚 | 115 | 318 | 71.1 MB | 94%（108/115） |
| 南北美洲 | 85 | 342 | 71.5 MB | 100% |
| **合计** | **246** | **847** | **180.4 MB** | — |

**实时性实测（2026-07-20 03:09 UTC）**：18 个测试站点的小时数据全部延迟 0.2 小时（12 分钟），可作为准实时观测源。

## 特色内容（别人没有的）

1. **AWS S3 匿名访问完整流程**——无需注册、无需 API key、无需 AWS 凭证，boto3 UNSIGNED 模式直接下载
2. **葵花 FLDK 分段下载策略**——华东区域只需 S0210 + S0310 两个分段，省 80% 下载量
3. **Meteostat 站点密度实测表**——中国 46 机场逐个标注站点距离，西部需 200km 半径
4. **Meteostat 实时性实测**——纠正"1-7 天延迟"的旧认知，小时数据实际延迟仅 12 分钟
5. **GOES 真彩色合成手动方案**——不依赖 pyspectral，手动 RGB + gamma 2.2 + 降采样，避免内存溢出
6. **区域下载陷阱清单**——缅甸日数据缺失、越南 3 机场无数据、巴西 SBGR 日数据延迟 7 天
7. **SURFRAD 地表实测辐照**——1 分钟 GHI/DNI/DHI，匿名 HTTPS，当天实时追加，区别于卫星衍生产品（NSRDB/PVGIS）

## 使用方法

### 方式一：用 Coding Agent 阅读整个项目（推荐）

**推荐用 TRAE、Cursor、Claude Code 等 coding agent 直接打开本项目仓库**，让 AI 帮你按需检索和理解知识库。原因见下方[设计理念：为什么不是 Skill](#设计理念为什么不是-skill)。

**给 coding agent 的提示词示例**：

```
我要下载葵花9卫星的华东区域数据，请阅读 .knowledge/tech/processes/PS-003.md 
和 .knowledge/tech/pitfalls/PF-004.md，给我一个完整的下载方案，包括：
1. 需要下载哪些分段
2. 选什么时次
3. 怎么用 satpy 处理
4. 有什么坑要避开
```

```
我要下载中国50个主要机场的2025年全年气象数据，请阅读 
.knowledge/tech/guidelines/GL-005.md 和 .knowledge/tech/pitfalls/PF-004.md，
告诉我用哪个脚本、怎么运行、预期数据量、哪些机场可能有问题。
```

agent 会自动按需读取相关条目，你不需要手动翻文档。

**纯人工阅读**也可：先看 [.knowledge/tech/catalog.md](.knowledge/tech/catalog.md) 了解全貌，再按需点进具体条目：
- 想下载葵花卫星数据 → [PS-003](.knowledge/tech/processes/PS-003.md)
- 想下载 GOES 卫星数据 → [PS-004](.knowledge/tech/processes/PS-004.md)
- 想用 Meteostat 下载地面观测 → [GL-005](.knowledge/tech/guidelines/GL-005.md)
- 下载遇到问题先看这里 → [PF-004](.knowledge/tech/pitfalls/PF-004.md)
- 想用 Open-Meteo 获取 ERA5 再分析 → [GL-004](.knowledge/tech/guidelines/GL-004.md)

每篇文档自成体系，包含背景、接口说明、Python 代码示例、实测结果、适用/不适用场景。

### 方式二：运行脚本下载数据

#### 环境准备

```bash
# 克隆仓库
git clone https://github.com/Titanx/meteo-data-cookbook.git
cd meteo-data-cookbook

# 安装 Python 依赖（Python 3.9+）
pip install meteostat boto3 satpy pyresample pyproj numpy pandas matplotlib pillow
```

#### 下载地面观测数据（Meteostat）

```bash
# 进入脚本目录
cd scripts/data_download/

# 测试单站（北京）
python test_meteostat.py

# 下载中国 46 个主要机场 2026 年数据
python download_china_airports_2026.py

# 下载中国 46 个机场 2025 年全年数据
python download_china_airports_2025.py

# 下载东亚东南亚 115 个机场
python download_east_southeast_asia_2025_2026.py

# 下载南北美洲 85 个机场
python download_americas_airports_2025_2026.py
```

数据将保存到 `data/meteostat/` 目录，按年份和区域分子目录：
```
data/meteostat/
├── china_2025/          # daily_ZBAA.csv, hourly_ZBAA.csv, ...
├── china_2026/
├── east_southeast_asia/
│   ├── 2025/
│   └── 2026/
└── americas/
    ├── 2025/
    └── 2026/
```

#### 下载卫星数据（葵花 / GOES）

```bash
# 测试 AWS S3 匿名访问（葵花 8）
python test_himawari_s3.py

# 下载葵花 9 华东区域分段数据 + 生成真彩色图
python himawari9_segment_pipeline.py

# 下载 GOES-19 全圆盘 + 生成真彩色图
python goes19_pipeline.py
```

卫星数据将保存到 `data/himawari9/` 或 `data/goes19/` 目录。

#### 数据质量检验

```bash
# 检验中国机场数据完整性
python check_data_integrity.py

# 检验东亚东南亚数据
python check_asia_integrity.py

# 测试 Meteostat 实时性（延迟多久）
python check_meteostat_realtime.py
python check_meteostat_realtime_americas.py
```

### 方式三：复用代码到自己的项目

知识库中的代码示例可直接复制到你的项目。关键依赖：

| 用途 | 依赖库 | 安装 |
|------|--------|------|
| 地面观测下载 | `meteostat` | `pip install meteostat` |
| AWS S3 匿名访问 | `boto3` | `pip install boto3` |
| 卫星数据处理 | `satpy`, `pyresample` | `pip install satpy` |
| 再分析数据 | `requests` 或 `openmeteo-requests` | `pip install openmeteo-requests` |

**核心代码片段**（详见各条目文档）：

```python
# AWS S3 匿名访问（葵花/GOES 通用）
import boto3
from botocore import UNSIGNED
from botocore.config import Config
s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

# Meteostat 批量下载（站点 ID 复用优化）
from meteostat import Daily, Hourly
from datetime import datetime
df = Daily("54511", datetime(2026, 1, 1), datetime(2026, 7, 19)).fetch()
```

## 设计理念：为什么不是 Skill

有人会问：为什么不把这些知识做成一个 coding agent 的 Skill（一次性加载所有上下文），而要维护一个分文件的 Markdown 知识库？

**答案是：气象数据知识太庞杂，必须用渐进式披露（progressive disclosure）结构。**

### Skill 的问题

一个 Skill 的 prompt 在每次对话时都会完整加载到上下文窗口。如果要把目前 5 条 verified 知识（约 1500 行 Markdown）塞进一个 Skill：

| 问题 | 说明 |
|------|------|
| **上下文爆炸** | 5 条已 1500 行，未来扩到 30+ 条会过万行，挤占对话的有效上下文 |
| **信噪比下降** | 用户问"葵花怎么下"时，GOES/Meteostat/Open-Meteo 的内容全是噪声 |
| **维护困难** | 单文件改一处要重新审阅全文，知识库分文件可独立迭代 |
| **验证成本高** | Skill 无法区分 verified 和 draft，知识库可通过成熟度标记分级 |

### 渐进式披露的结构

本知识库采用三层渐进式披露：

```
第 1 层：catalog.md（索引）
  ↓ 用户/agent 按需选择
第 2 层：具体条目（GL-005.md / PS-003.md / ...）
  ↓ 条目内部再分层
第 3 层：背景 → 接口 → 代码示例 → 实测结果 → 陷阱 → 适用场景
```

**coding agent 天然适配这个结构**：
1. agent 先读 `catalog.md`（几十行，低成本）
2. 根据用户问题，只读取相关的 1-2 个条目（几百行，按需）
3. 条目内部的分层结构让 agent 能快速定位到"代码示例"或"陷阱"段落

这样，无论知识库增长到多少条，单次对话的上下文消耗始终可控。这也是为什么**推荐用 coding agent 打开本项目**而不是做成 Skill——agent 的文件检索能力就是天然的渐进式加载机制。

### 知识库 vs Skill 的选择标准

| 场景 | 适合 Skill | 适合知识库 |
|------|-----------|-----------|
| 知识总量 < 200 行，规则性强 | ✅ | ❌ 过度设计 |
| 知识总量 > 500 行，领域庞杂 | ❌ 上下文爆炸 | ✅ |
| 需要区分成熟度（draft/verified） | ❌ | ✅ |
| 需要独立迭代各条目 | ❌ | ✅ |
| 需要 agent 按需检索 | ❌ | ✅ |

气象数据领域属于右列：卫星（葵花/GOES/风云）、地面观测（Meteostat/ISD）、再分析（ERA5）、数值模式（WRF/GFS），每个子领域都有独立的下载流程、陷阱、最佳实践，总量会持续增长到数千行。知识库 + coding agent 是唯一可行的结构。

## 相关项目

- [satpy](https://github.com/pytroll/satpy) — 卫星数据处理库（本项目使用的核心工具）
- [meteostat](https://github.com/meteostat/meteostat) — 地面观测数据 Python 库
- [open-earth-data-guide](https://github.com/wait4xx/open-earth-data-guide) — 中文地球系统数据源索引（互补关系）
- [awesome-meteorology](https://github.com/jeffreyspringer/awesome-meteorology) — 气象领域 awesome list

## 许可证

[MIT License](LICENSE) — 内容可自由引用，脚本可自由使用。

## 来源

所有条目基于 2026-07-18 ~ 2026-07-20 的实际下载测试，非文档摘抄。测试脚本归档于 `scripts/data_download/` 目录。
