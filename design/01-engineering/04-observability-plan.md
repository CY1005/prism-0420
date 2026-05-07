---
title: 可观测性规划（最小集占位决策）
status: accepted-minimal
owner: CY
created: 2026-04-20
v2_revision: 2026-05-07  # §7 加 early adopter 触发条款引用（横切判断前置 + §7.1/§7.2 分支），详见 ../audit/time-dimension-blindspot-2026-05-07.md
accepted: 2026-04-26
phase: Phase 2.0 启动决策（A4.2）+ Phase 2.3 上线前补完
parent: ../00-roadmap.md
---

# 04 - 可观测性规划

> Phase 2.0 阶段只决最小集（日志方案），不阻塞 Phase 2.1。监控 / 告警推到 Phase 2.3 上线前。

---

## 1. 日志方案

| 候选 | 优 | 缺 |
|------|----|----|
| **A stdout 结构化 JSON**（loguru / structlog）+ Phase 2.3 后接 Loki | 0 基础设施依赖 / Docker logs 即可 / 后期可解析接 Loki | 单机，跨实例聚合靠后期 |
| B 直接接 Loki / ELK | 完整方案 | Phase 2.0/2.1 阶段过度 |
| C plain text | 0 配置 | 不可机器解析 / Phase 3 数据对照困难 |

**决定**：✅ **A stdout JSON**（用 `structlog` 库）

**理由**：
1. Phase 2.0/2.1 单机开发，stdout 即可
2. JSON 格式 Phase 3 数据对照能直接 jq 解析
3. 后期接 Loki 几乎零迁移成本

**字段约定**（structlog processors）：
```python
{
    "timestamp": "2026-04-26T10:00:00Z",
    "level": "INFO",
    "logger": "api.services.team_service",
    "event": "team_created",
    "request_id": "<uuid>",        # 来自 X-Request-ID 中间件
    "user_id": "<uuid>",            # 从 require_user 注入
    "extra": { ... }                # 业务字段
}
```

**替代触发**：单机 → 多实例部署时 → 接 Loki

---

## 2. 日志级别约定

| 级别 | 场景 | 示例 |
|------|------|------|
| **DEBUG** | 详细执行轨迹（开发用，生产关）| SQL query / fixture setup |
| **INFO** | 业务事件 / 正常流程 | team_created / login_success |
| **WARN** | 可恢复的异常 / 边界场景 | retry / fallback / archived project 加入 team 拒 |
| **ERROR** | 不可恢复异常 / 5xx | DB 连接失败 / Auth 解析失败 / unhandled exception |

`api/config.py` 通过 `LOG_LEVEL` env var 控制（dev=DEBUG / prod=INFO）

---

## 3. 监控方案

> Phase 2.3 上线前决，本期占位

候选：Prometheus + Grafana / 云厂商 APM / 暂不做

**Phase 2.0/2.1 决策**：✅ **暂不做**（依赖 stdout 日志 + Phase 3 离线分析）

---

## 4. 链路追踪

> Phase 2.3 上线前决，本期占位

候选：OpenTelemetry / Jaeger / 暂不做

**Phase 2.0/2.1 决策**：✅ **仅 X-Request-ID 中间件 + 日志带 request_id**（最小相关性追踪）

---

## 5. 告警

> Phase 2.3 上线前决，本期不做

---

## 6. 完成度判定（Phase 2.0 范围）

- [x] 日志方案（stdout JSON + structlog）
- [x] 日志级别约定（DEBUG/INFO/WARN/ERROR + LOG_LEVEL env）
- [x] X-Request-ID 中间件（Phase 2.0 B4 实现）
- [ ] **Phase 2.3 上线前补**：监控 + 链路追踪 + 告警决策

---

## 7. accepted-minimal 状态的 early adopter 触发条款（2026-05-07 时间维度盲区沉淀）

本文档为 accepted-minimal 状态——Phase 2.0/2.1/2.2 业务开发够用，详细补完推到 Phase 2.3 §8.0。

若 M02-M19 任一模块在 §8.0 补完之前需要本文件 minimal 范围**之外**的可观测性能力（如某模块需提前用 OTel traceId / Prometheus metrics / 告警通道 / Sentry 错误聚合），sprint 启动 reconcile pass 期间必须按 [`05-security-baseline.md §7`](./05-security-baseline.md#7-accepted-minimal-状态的-early-adopter-触发条款2026-05-07-时间维度盲区沉淀2026-05-07-后续-d4-推演修订) 流程：

1. **判断前置**：能力是横切（traceId / metrics / 告警通道 / 日志聚合等基础设施）还是模块特定？可观测性能力**绝大多数都是横切**——默认走横切分支
2. **三选一**：横切走 §7.1（A 完整提前 / B' 部分提前 + 横切实装 / C 推迟）；模块特定走 §7.2

**禁止**：把可观测性 helper（如 traceId middleware / metrics 上报 service / 告警通道 client）挂在某业务模块名下——这是横切关注，必须建在横切层（`api/middleware/` 或 `api/services/observability/` 等横切目录）。

> 触发条款完整定义、判断前置、横切 vs 模块特定分支、决策登记格式、清单维护在 05-security-baseline.md §7 主表，本文件仅引用。
