# Performance Baseline (Sprint 2 Task 2.4 简化版)

## 范围

- **简化规模**：100 project / 500 node / 1000 issue（cleanup-plan §492 完整 1000x 推下次会话）
- **测量对象**：DAO 层 5 个核心 read endpoint（不绕 router）
- **基础设施**：pytest-benchmark + 自定义 samples_ms P95（pytest-benchmark fixture 占位 lambda no-op，真测量在 `extra_info.p95_ms`）

## 跑法

```bash
uv run pytest tests/perf/test_baseline_p95.py \
    --benchmark-only \
    --benchmark-json=tests/perf/baseline.json
```

## 当前阈值（CI runner 抖动 / 简化规模）

| Endpoint | 数据规模 | P95 阈值 |
|---|---|---|
| `dao.list_by_user` | 100 project | < 200ms |
| `dao.get_by_id_for_user` | 单 project | < 50ms |
| `dao.list_by_project` (issue) | 10 issue/proj | < 100ms |
| `dao.list_by_project` (node) | 5 node/proj | < 50ms |
| seed health aggregate | 100/500/1000 | (验真落库) |

## 已知限制

1. **pytest-benchmark fixture 用法是占位**：真测量逻辑在 `samples_ms` 列表，pytest-benchmark 输出的 ns 数据是 `lambda: None`（不准）。下次会话升 1000 seed 时改成 sync wrapper 让 pytest-benchmark 直接测 endpoint。
2. **fixture scope=function**：每 test 重新 seed 100 project（含 setup ~3s）；下次升 1000 时改 session+truncate-between。
3. **不验 router HTTP 中间件层**：当前直测 DAO；router auth/CORS 层加多少耗时未量化（下次会话补 client.get 路径）。
4. **CI 集成 punt**：`.github/workflows/ci.yml` 的 perf-baseline job 推上线 sprint 接通；本地跑 OK 即可建 baseline。

## 下次会话升级路径

1. 升 PERF_PROJECTS=1000 / NODES_PER_PROJECT=10 / ISSUES_PER_PROJECT=5（10000 + 5000）
2. fixture scope=session + autouse truncate
3. 改用 `await client.get(...)` 真测 router 层
4. pytest-benchmark `pedantic(rounds=10)` sync wrapper（asyncio.run 单测内）
5. 接通 `.github/workflows/ci.yml` perf-baseline job
6. baseline.json 设为 CI artifact + 跨 commit 对比

## 触发回归告警条件（推上线后）

- 任一 P95 > 当前阈值 2x
- baseline.json mean 跨 commit 漂移 > 30%
- 真负载 P95 > 500ms（cross-sprint pool §"性能黑洞" DEFER_TO_POST_LAUNCH 触发条件）
