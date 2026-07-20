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
.knowledge/
├── README.md               # 本文件
├── tech/
│   ├── catalog.md          # 条目索引
│   ├── guidelines/         # 最佳实践
│   │   ├── GL-004.md       # Open-Meteo API 使用指南
│   │   └── GL-005.md       # Meteostat 地面观测数据使用指南
│   ├── pitfalls/           # 已知陷阱
│   │   └── PF-004.md       # Meteostat 区域数据下载陷阱
│   └── processes/          # 技术流程
│       ├── PS-003.md       # 葵花 8/9 卫星数据下载流程
│       └── PS-004.md       # GOES-16/18/19 卫星数据下载流程
└── log.md                  # 变更日志

scripts/
└── data_download/          # 实测验证脚本

data/                       # 下载数据（不纳入 git，可重新生成）
├── himawari/               # 葵花 8/9 卫星数据
├── himawari9/              # 葵花 9 实时分段数据
├── goes19/                 # GOES-19 卫星数据
└── meteostat/              # 地面观测数据（246 机场 847 CSV）
```

## 条目清单（全部 verified）

| ID | 标题 | 核心内容 |
|----|------|---------|
| GL-004 | Open-Meteo API 使用指南 | 免 API key、ERA5 历史 17 天、预报 168h、批量请求 |
| GL-005 | Meteostat 地面观测数据使用指南 | 246 机场 847 CSV 180.4MB、站点 ID 复用 3-5x 提速、**小时数据延迟仅 12 分钟** |
| PF-004 | Meteostat 区域数据下载陷阱 | 中国站点稀疏需 200km 半径、缅甸日数据缺失、越南 3 机场无数据 |
| PS-003 | 葵花 8/9 卫星数据下载流程 | AWS S3 匿名访问、FLDK 分段下载省 80%、白天时次选择、HSD→AHI-L1b-FLDK 目录迁移 |
| PS-004 | GOES-16/18/19 卫星数据下载流程 | AWS S3 匿名访问、ABI L1b RadF、真彩色合成（手动 RGB + gamma）、与 Himawari 对比 |

## 数据源覆盖

### 卫星数据

| 卫星 | 数据源 | 访问方式 | 实时性 | 实测验证 |
|------|--------|---------|--------|---------|
| 葵花 9（Himawari-9） | AWS S3 `noaa-himawari9` | 匿名 UNSIGNED | 实时（10 分钟间隔） | 2026-07-20 02:02 UTC 最新 |
| GOES-19 | AWS S3 `noaa-goes19` | 匿名 UNSIGNED | 实时 | 2026-07-20 01:30 UTC 全圆盘 + 真彩色图 |

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

## 使用方式

每篇文档自成体系，可独立阅读。推荐阅读顺序：

1. 先看 `.knowledge/tech/catalog.md` 了解全貌
2. 按需阅读具体条目（卫星数据看 PS-003/PS-004，地面观测看 GL-005 + PF-004）
3. 脚本位于 `scripts/data_download/`，数据路径以 `data/` 开头（相对路径，按需调整）
4. `data/` 目录不纳入 git，运行脚本可重新生成

## 相关项目

- [satpy](https://github.com/pytroll/satpy) — 卫星数据处理库（本项目使用的核心工具）
- [meteostat](https://github.com/meteostat/meteostat) — 地面观测数据 Python 库
- [open-earth-data-guide](https://github.com/wait4xx/open-earth-data-guide) — 中文地球系统数据源索引（互补关系）
- [awesome-meteorology](https://github.com/jeffreyspringer/awesome-meteorology) — 气象领域 awesome list

## 许可证

[MIT License](LICENSE) — 内容可自由引用，脚本可自由使用。

## 来源

所有条目基于 2026-07-18 ~ 2026-07-20 的实际下载测试，非文档摘抄。测试脚本归档于 `scripts/data_download/` 目录。
