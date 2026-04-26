---
title: 可观测性规划（最小集占位决策）
status: accepted-minimal
owner: CY
created: 2026-04-20
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
