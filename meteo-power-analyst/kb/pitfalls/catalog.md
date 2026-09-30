# pitfalls/ 目录 — 踩坑条目（PIT）

回答"什么情况下会踩坑、怎么发现、怎么绕"。判据：有排查信号。

| ID | 标题 | 成熟度 | 状态 |
|----|------|--------|------|
| [PIT-20260719-001](PIT-20260719-001.md) | Meteostat 区域数据下载陷阱（中国/亚洲/美洲） | verified | active（原 PF-004） |
| [PIT-20260723-001](PIT-20260723-001.md) | ERCOT 官网反爬虫屏蔽与中国 IP 不可访问陷阱 | verified | active（原 PF-005） |
| [PIT-20260724-001](PIT-20260724-001.md) | Pandas 时区 tz-naive 与 tz-aware 比较错误 | verified | active（原 PF-006） |
| [PIT-20260724-002](PIT-20260724-002.md) | 雷暴检测在高风区绝对阈值失效 | verified | active（原 PF-007） |
| [PIT-20260811-001](PIT-20260811-001.md) | 怀俄明大学探空接口迁移与 SSL 证书问题 | verified | active（原 PF-008） |
| [PIT-20260811-002](PIT-20260811-002.md) | 探空数据区域分辨率差异与标准化比较 | verified | active（原 PF-009） |
| [PIT-20260811-003](PIT-20260811-003.md) | 探空 WSGI 格式中 CAPE 缺失与 HTML 热力指数提取 | verified | active（原 PF-010） |
| [PIT-20260812-001](PIT-20260812-001.md) | NEXRAD 官方 S3 桶匿名访问限制与替代方案 | verified | active（原 PF-011） |
| [PIT-20260907-001](PIT-20260907-001.md) | CMA 气象数据访问陷阱：CMADaaS 需内网、data.cma.cn API 受限、nmc-met-io 不支持 LMI | verified | active（原 PF-012） |
| [PIT-20260929-001](PIT-20260929-001.md) | REE/ESIOS 域名级 WAF 封锁：api.esios.ree.es 全站 403（token 有效也进不去） | verified | active（原 PF-013） |
| [PIT-20260929-002](PIT-20260929-002.md) | ENTSO-E / IEC 62325 报文的两处隐藏结构：curveType=A03 压缩 与 A01/A07 合约混装 | verified | active（原 PF-014） |
| [PIT-20260929-003](PIT-20260929-003.md) | 历史预报归档（previous-runs）的逐 lead 同质性陷阱 | verified | active（原 PF-015） |
| [PIT-20260930-001](PIT-20260930-001.md) | 凭据硬编码与原始材料层外泄：`.gitignore` 挡不住脚本里的明文口令 | verified | active（迁移后新增） |
| [PIT-20260930-002](PIT-20260930-002.md) | NASA POWER 辐照来源被当成 MERRA-2 再分析（三处"查来源"的入口全失效） | verified | active（迁移后新增） |
| [PIT-20260930-003](PIT-20260930-003.md) | 同一段 NASA POWER 辐照会换版本（FLASHFlux 先发布、SYN1deg 后覆盖；hourly 不填） | verified | active（迁移后新增） |
| [PIT-20260930-004](PIT-20260930-004.md) | NASA POWER hourly/daily 默认 LST（当地太阳时），漏传参数会整段错位 | verified | active（迁移后新增） |
| [PIT-20260930-005](PIT-20260930-005.md) | S3 分页静默截断：把"单次列举 1000 条上限"误当成"归档止于某日" | verified | active（迁移后新增） |
| [PIT-20260930-006](PIT-20260930-006.md) | 静止卫星的"延迟"与"体积"都有多个口径（标称/扫描结束/最新时次滞后；昼夜与天气体积差 1.6~26 倍） | verified | active（迁移后新增） |
