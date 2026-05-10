# Performance Baseline (Sprint 2 Task 2.4 完整版)

## 范围

- **完整版规模**：1000 project / 10000 node / 5000 issue
- **测量对象**：DAO 层 5 个核心 read endpoint
- **基础设施**：pytest-benchmark + bulk_insert_mappings 单 SQL 批量 + 自定义 samples_ms P95（pytest-benchmark fixture 占位 lambda no-op，真测量在 `extra_info`）

## 跑法

```bash
uv run pytest tests/perf/test_baseline_p95.py \
    --benchmark-only \
    --benchmark-json=tests/perf/baseline.json
```

setup ~6s × 5 test = 总 30s 左右（function scope / 每 test 重 seed）。

## 当前阈值

| Endpoint | 数据规模 | P95 阈值 | 实测 (示例) |
|---|---|---|---|
| `dao.list_by_user` | 1000 project | < 1500ms | 看 baseline.json `extra_info.p95_ms` |
| `dao.get_by_id_for_user` | 单 project / 1000 in DB | < 50ms | 同上 |
| `dao.list_by_project` (issue) | 5 issue/proj / 5000 in DB | < 100ms | 同上 |
| `dao.list_by_project` (node) | 10 node/proj / 10000 in DB | < 50ms | 同上 |
| seed health aggregate | 1000/10000/5000 | (验真落库) | — |

## 已知限制（剩余项 / 推下次会话或独立 sprint）

1. **pytest-benchmark fixture 用法是占位**：真测量逻辑在 `samples_ms` 列表 + `extra_info`，pytest-benchmark 输出的 ns 数据是 `lambda: None`（不准）。  
   **未完成原因**：pytest-asyncio loop_scope=session 与 `asyncio.run` 在已运行 loop 内 raise 冲突；pedantic sync wrapper 不可用。  
   **替代**：解析 baseline.json 的 `extra_info.p95_ms` / `samples` 而非 `mean`。
2. **Router 层未真测**：当前 DAO 层基线足够稳定。Router + middleware（auth / CORS / log）overhead 估 +2-5ms 推下次专 sprint（涉及 dep override + session sharing 复杂 wiring）。
3. **fixture function scope**：每 test 重 seed 6s × 5 = 30s（接受）。session scope 受 db_session 是 function scope 限制。下次升 10000 project 时考虑用独立 db connection 绕过 conftest.db_session。
4. **CI 接通推上线 sprint**：`.github/workflows/ci.yml` 的 perf-baseline job 当前未挂；本地跑建立 baseline 即可。CI 接通依赖 GH PAT workflow scope。

## 升级路径（下次会话或独立 perf sprint）

| # | 内容 | cost |
|---|---|---|
| 1 | router 层真测（auth_client + dep override + perf_seeded_db.user 注入 current_user）| $1-2 |
| 2 | pedantic sync wrapper（绕开 pytest-asyncio loop conflict / 用 anyio.run / 或单独 process pool）| $1-2 |
| 3 | session scope fixture（独立 db connection / 跨 test 共享 seed）| $1 |
| 4 | 接通 ci.yml perf-baseline job（依赖 PAT scope）| $1 |
| 5 | baseline.json 设为 CI artifact + 跨 commit 对比 + 自动告警 | $1 |

## 触发回归告警条件（推上线后）

- 任一 P95 > 当前阈值 2x（list_projects > 3000ms / get_by_id > 100ms 等）
- baseline.json `extra_info.median_ms` 跨 commit 漂移 > 30%
- 真负载 P95 > 500ms（cross-sprint pool §"性能黑洞" DEFER_TO_POST_LAUNCH 触发条件）
