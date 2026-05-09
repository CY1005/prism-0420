---
title: 可观测性规划
status: accepted
owner: CY
created: 2026-04-20
v2_revision: 2026-05-07  # §7 加 early adopter 触发条款引用（横切判断前置 + §7.1/§7.2 分支），详见 ../audit/time-dimension-blindspot-2026-05-07.md
v3_revision: 2026-05-09  # §8 Phase 2.3 §8.0 补完决策（指标/告警/traceId/错误聚合）
accepted: 2026-04-26
phase: Phase 2.0 启动决策（A4.2）+ Phase 2.3 §8.0 补完
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

## 6. 完成度判定

- [x] 日志方案（stdout JSON + structlog）
- [x] 日志级别约定（DEBUG/INFO/WARN/ERROR + LOG_LEVEL env）
- [x] X-Request-ID 中间件（Phase 2.0 B4 实现）
- [x] **Phase 2.3 §8.0 补完**（见 §8 / commit Phase 2.3 子 sprint A）：指标 + 告警 + traceId + 错误聚合

---

## 7. accepted-minimal 状态的 early adopter 触发条款（2026-05-07 时间维度盲区沉淀）

本文档为 accepted-minimal 状态——Phase 2.0/2.1/2.2 业务开发够用，详细补完推到 Phase 2.3 §8.0。

若 M02-M19 任一模块在 §8.0 补完之前需要本文件 minimal 范围**之外**的可观测性能力（如某模块需提前用 OTel traceId / Prometheus metrics / 告警通道 / Sentry 错误聚合），sprint 启动 reconcile pass 期间必须按 [`05-security-baseline.md §7`](./05-security-baseline.md#7-accepted-minimal-状态的-early-adopter-触发条款2026-05-07-时间维度盲区沉淀2026-05-07-后续-d4-推演修订) 流程：

1. **判断前置**：能力是横切（traceId / metrics / 告警通道 / 日志聚合等基础设施）还是模块特定？可观测性能力**绝大多数都是横切**——默认走横切分支
2. **三选一**：横切走 §7.1（A 完整提前 / B' 部分提前 + 横切实装 / C 推迟）；模块特定走 §7.2

**禁止**：把可观测性 helper（如 traceId middleware / metrics 上报 service / 告警通道 client）挂在某业务模块名下——这是横切关注，必须建在横切层（`api/middleware/` 或 `api/services/observability/` 等横切目录）。

> 触发条款完整定义、判断前置、横切 vs 模块特定分支、决策登记格式、清单维护在 05-security-baseline.md §7 主表，本文件仅引用。

---

## 8. Phase 2.3 §8.0 补完决策（2026-05-09 / 子 sprint A）

> **scope**：04-observability minimal → accepted。**自决原则**：shadow 项目 + 单人 + 上线最简，先建管道再调数据。

### 8.1 指标采集方案（B1）

**决定**：✅ **prometheus-fastapi-instrumentator + 自建 arq counter / `/metrics` endpoint 暴露 / 上线 sprint 接 Grafana Cloud 免费档**

| 候选 | 优 | 缺 |
|------|----|----|
| **A Prometheus + Grafana Cloud 免费**（选）| 生态最广 / instrumentator 0 配置 / Grafana Cloud 10k metrics 免费足单人 | 需自建 dashboard（Phase 2.3+ 沉淀）|
| B OTel + collector | 标准前瞻 / 跨指标/trace 统一 | collector 部署运维 / 单人过度 |
| C 云厂商 APM（DataDog/NewRelic）| 0 部署 | $$ / vendor lock |

**关键指标清单**（落 `/metrics`）：
```
# 通用 HTTP
http_requests_total{method, path, status}        # QPS + 错误率
http_request_duration_seconds{method, path}      # P50/P95/P99（histogram）

# 异步 Queue（M16/M17/M18）
arq_queue_pending{queue_name}                    # Queue 堆积
arq_jobs_total{queue_name, status}               # success/failure
arq_job_duration_seconds{queue_name, job_name}

# Embedding（M18）
embedding_tasks_total{status}                    # success/failed/noop
embedding_provider_latency_seconds{provider}

# SSE/WS active connections
sse_active_connections{endpoint}                 # M16
ws_active_connections{endpoint}                  # M17
```

**3-5 月演进**：单实例 → 多实例时切 OTel collector 聚合；上 K8s 时切 Prometheus Operator。

### 8.2 告警阈值 + 通道（B2）

**决定**：✅ **Sentry 错误告警 + Grafana Cloud Alerting 指标告警 / 通道 = TG（reuse OpenClaw push 通道）**

**阈值**（首版保守 / 上线后真负载调整）：
| 信号 | 阈值 | 通道 |
|------|------|------|
| HTTP 5xx 率 | > 1% 持续 5min | TG + Sentry |
| HTTP P95 latency | > 500ms 持续 5min | TG |
| arq queue pending | > 1000 持续 10min | TG |
| arq job failure rate | > 5% 持续 10min | TG |
| embedding noop rate | > 20% 持续 1h | TG（数据质量预警）|
| SSE/WS active connections | > 100（容量上限）| TG |
| 错误聚合（Sentry）| 任何 P0 / 新 issue | TG + email |

**TG 通道实施**：FastAPI 启动加 `api/services/alert_channel.py`（占位本期；上线 sprint 接 OpenClaw `/root/.claude-plugins/openclaw/scripts/notify.py` 或独立 bot）；本期 spec 决策落，实施推上线 sprint。

**3-5 月演进**：增 PagerDuty / 多人 oncall 轮换。

### 8.3 traceId 贯穿（B3）

**决定**：✅ **复用现有 X-Request-ID middleware → structlog bind / arq job kwargs 透传 trace_id**

- FastAPI middleware（已实装）：解析 `X-Request-ID` 入 contextvar → structlog processor bind
- arq job：enqueue 时把 `request.state.trace_id` 塞 job kwargs；worker 启动时再从 kwargs 取出 bind 到 structlog
- WebSocket：accept 时从 query/header 取 trace_id（生成新 uuid 兜底），bind context
- SSE：response stream lifetime 内保持 contextvar

**实施位置**（spec 决策 / 实施推上线 sprint）：
- `api/middleware/trace.py`（已有 X-Request-ID）— 改名/扩展为 trace_id 主键
- `api/queue/base.py` — enqueue 注入 trace_id / dequeue 提取 bind
- `api/services/aio_provider.py` — LLM call 日志带 trace_id（M13/M16）

**字段统一**：与 `tenant_id` 同 payload；ADR-002 Queue 消费者租户权限对照不破。

### 8.4 错误聚合（B4）

**决定**：✅ **Sentry SaaS（免费 5K events/month / 单人 prism-0420 充足）**

| 候选 | 优 | 缺 |
|------|----|----|
| **A Sentry SaaS**（选）| 0 运维 / Python+Next 双 SDK 成熟 / 5K events 免费足单人 | $$ if 增到团队级 / 数据出境（shadow 项目 N/A）|
| B GlitchTip 自建 | 私有 / Sentry API 兼容 | 运维成本 / 单人不值 |
| C 自建（仅 Sentry SDK send to backend）| N/A | 自造轮子 / 不推荐 |

**集成**：
- backend `sentry-sdk[fastapi]` + DSN 走 `settings.sentry_dsn`（env `SENTRY_DSN`，默认 None = 关）
- frontend `@sentry/nextjs`（公司有 SaaS DSN 就启 / 否则不开）
- 错误过滤：忽略 4xx 客户端错误（仅采 5xx / unhandled exceptions）
- traceId 从 structlog 串到 Sentry tag

**3-5 月演进**：team 多人 → 升 Sentry team plan；GDPR/PII 风险 → 加 before_send filter。

### 8.5 决策登记总览

| 决策 | 选 | 理由 |
|------|----|------|
| B1 指标 | Prometheus + Grafana Cloud 免费档 | 生态广 / 免费足单人 |
| B2 告警 | Grafana alerting + Sentry → TG 通道 | reuse OpenClaw push |
| B3 traceId | X-Request-ID middleware → structlog → arq kwargs | 已有基线扩展 |
| B4 错误聚合 | Sentry SaaS 免费档 | 单人最低运维成本 |
