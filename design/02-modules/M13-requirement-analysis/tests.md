---
title: M13 需求分析 - 测试场景
status: draft
owner: CY
created: 2026-04-25
module_id: M13
pilot: true
---

# M13 需求分析 - 测试场景

> 覆盖 6 类必答（Golden / 边界 / 并发 / Tenant / 权限 / 错误）+ **流式特化**（pilot §12A 子模板专属验证）。
>
> **测试执行形态**：
> - 大多数场景 = pytest 集成测试（FastAPI TestClient + SSE 客户端 mock）
> - 个别"用户感知"场景 = E2E（Playwright 对抗流式抽屉 UI）——标 `[E2E]`
> - mock AI Provider：使用 `MockProvider`（固定 chunks 序列 + 可配置延迟 / 错误注入）

---

## G. Golden Path（核心快乐路径）

### G1. L2 分析 → 保存 → 关系图高亮（主流程）

**步骤**：
1. editor 用户 A 登录，打开项目 P1 下 node N1（"订单取消"）的档案页
2. 输入 requirement_text（100 字），analysis_level=L2，点"AI 分析"
3. 前端 POST `/analyze/requirement`，MockProvider 分 5 chunks 返回（总耗时 1s）
4. 前端每收到 chunk event 追加展示
5. 收到 complete event 后，点"保存"按钮，前端 POST `/analyze/save`（含 full_result + affected_node_ids=[N2, N3]）
6. 跳转到关系图，GET `/analyze/affected-nodes?node_id=N1`

**断言**：
- SSE 收到 5 个 `chunk` + 1 个 `complete` event，顺序正确
- `complete.full_result = "".join(chunks)`
- `complete.metadata` 含 `ai_provider / ai_model / analysis_level="L2" / analysis_time_ms / matched_template_id`
- `/analyze/save` 返回 200 + `dimension_record_id`（UUID） + `analysis_saved_at`（ISO 8601 字符串）
- M04 `dimension_records` 表新增 1 行：`dimension_type_key="requirement_analysis"`, `node_id=N1`, `content.analysis_result=full_result`, `content.metadata.affected_node_ids=[N2,N3]`
- M15 `activity_log` 新增 1 行（**由 M04 Service 代写**）：`action_type="create"`, `target_type="dimension_record"`, `target_id=<新建 dim_record_id>`, `user_id=A`, `metadata` 合并 M04 默认（`node_id, type_id, content_size`）+ M13 注入（`dimension_type_key="requirement_analysis", analysis_level, affected_node_count=2, ai_provider, ai_model, analysis_time_ms, requirement_text_hash`）
- `/analyze/affected-nodes?node_id=N1` 返回 `affected_node_ids=[N2, N3]`, `analysis_record_id=<上一步返回的 id>`, `analysis_saved_at=<response 的同一时间戳>`

### G2. L1 快速分析（更短 chunks）

同 G1，但 `analysis_level=L1` + MockProvider 2 chunks（总耗时 200ms）。断言：`complete.metadata.analysis_level="L1"`。

### G3. L3 深度分析（更长 chunks）

同 G1，但 L3 + 20 chunks + 总耗时 30s。断言：耗时 < 5min 超时，正常 complete。

### G4. 无 affected_nodes 的保存

`save` 请求 `affected_node_ids=[]`。断言：
- 成功写入 dimension_record
- `content.metadata.affected_node_ids=[]`
- `/analyze/affected-nodes` 返回 `affected_node_ids=[]`

### G5. 初次访问无历史分析

N1 从未分析过，直接 GET `/analyze/affected-nodes?node_id=N1`。断言：
- 200 OK
- `{node_id: N1, affected_node_ids: [], analysis_record_id: null, analysis_saved_at: null}`

---

## B. 边界（Boundary）

### B1. requirement_text = 0 字符

POST `/analyze/requirement` with `requirement_text=""`。断言：
- 422 Pydantic validation error（`min_length=1`）
- 无 activity_log 写入

### B2. requirement_text = 5000 字符

`requirement_text` 恰好 5000 字。断言：通过 Pydantic；流式正常启动。

### B3. requirement_text = 5001 字符

断言：422 Pydantic error（`max_length=5000`）。

### B4. requirement_text 含特殊字符（SQL 注入尝试 / Markdown / emoji）

输入 `"'; DROP TABLE users; --\n# Header\n🎉"`。断言：
- 正常处理（prompt 拼装用参数化字符串）
- DB 无异常 / 无任务表被删
- 分析结果能正常 save

### B5. affected_node_ids = 空数组 / 50 个 / 500 个

- 空：G4 已覆盖
- 50：正常 save + `/affected-nodes` 返回 50 个 UUID
- 500：save 成功但 metadata JSONB 变大（< 1MB 接受）——断言 PG TOAST 自动压缩不报错

### B6. analysis_result 超长（100 KB Markdown）

save 请求 `analysis_result` = 100 KB 文本。断言：
- dimension_records.content 写入成功（JSONB 支持大字段）
- `/affected-nodes` 查询性能仍 < 100ms（只读 metadata 不读 analysis_result）

### B7. MockProvider 0 chunks 直接 complete

provider.analyze 立即 StopAsyncIteration，无 chunk。断言：
- SSE 只发 1 个 `complete` event，`full_result=""`
- 用户可点保存（save 接受空文本）——但前端 UX 应提示"无结果"（UI 层行为，不在 server 测试断言里）

---

## C. 并发（Concurrency）

### C1. 同一 user 同 node 并发 3 个流式请求

用户 A 对 N1 同时发 3 个 `/analyze/requirement`。断言：
- 3 个 HTTP 连接都建立成功
- 3 个流独立 yield chunks（无互斥锁错误）
- 3 个 complete event 分别返回（结果可能相同或不同，不断言内容）
- 无"taskid 冲突" / 无 DB 唯一键冲突（M13 无自有表无 key）

### C2. 同一 user 不同 node 并发（N1/N2/N3）

3 个 node 同时分析。断言：每个流互不影响 + context 拼装严格按各自 node_id 独立。

### C3. 同 user 对同分析结果 save 3 次（**后端允许 + 前端防抖兜底**）

**后端**：直接用 HTTP client 快速调 `/analyze/save` 3 次（绕过前端）。断言：
- 3 个 POST 全部成功
- M04 `dimension_records` 新增 3 行（允许重复，Q6 ack）
- M15 `activity_log` 写 3 条 `action_type="create"` / `target_type="dimension_record"`（M04 代写）
- `/analyze/affected-nodes` 返回 **最新一条**（M04 `get_latest(db, ..., dimension_type_key="requirement_analysis")` 按 `created_at DESC`）

### C3b. `[E2E]` 前端保存按钮防抖（R2-04 修复验证）

Playwright 启动，editor 登录，完成流式分析。断言：
- 点击"保存"第 1 次：按钮立即变 disabled + loading 态
- save response 返回前，用户疯点 10 次：network 面板只能看到 1 个 `/analyze/save` 请求
- save response 返回后：按钮变"已保存"不可再点；若用户手动清空并重输相同 full_result，同一抽屉生命周期内仍拒绝第 2 次（基于 SHA256 hash 判重，见 §6 Component 层职责）
- DB 验证：`dimension_records` 仅 1 新行

### C4. 不同 user 并发 save 到同一 node

用户 A、B 都是 P1 的 editor，同时对 N1 做分析 + save。断言：
- 两条 dimension_record 都写入（各自 created_by = A / B）
- M15 各 1 条 activity_log（user_id 区分）
- `/analyze/affected-nodes` 返回最新（按 timestamp）

---

## T. Tenant（跨租户隔离）

### T1. 跨项目读取 node 拒绝

用户 A 是 P1 editor，不是 P2 成员。A POST `/api/projects/P2/nodes/<P2 的 node>/analyze/requirement`。断言：
- 403（project access check 失败）
- 无 SSE 流建立
- 无 activity_log

### T2. URL 路径 project_id 与 body node_id 跨项目混淆

A 是 P1 editor。POST `/api/projects/P1/nodes/<P2 的 node N2>/analyze/requirement`。断言：
- 404（`node_service.get_node_with_path(P1, N2)` 返回 None，wrap 为 `AnalysisNodeNotFoundError`）
- 不泄露"N2 存在于 P2"信息（统一 404 而非 403）

### T3. save 时 node_id 跨项目

流式用 `P1/N1` 正常，save 时故意改 URL 到 `P1/<P2 的 N2>`。断言：
- 404 `ANALYSIS_NODE_NOT_FOUND`
- 无 dimension_record 写入
- 无 activity_log

### T4. `/analyze/affected-nodes` 跨项目

A 是 P1 editor，GET `/api/projects/P1/nodes/<P2 的 node>/analyze/affected-nodes`。断言：404。

### T5. context 聚合不泄露跨项目数据

验证 M13 Service 内部聚合 `RequirementAnalysisContext` 时，M03/M04/M07 Service 调用均带 `project_id` 参数。mock M04 Service 返回"跨项目 dimension_record"时，M13 Service 应该拒绝使用（但这是 M04 Service 的防护责任，M13 tests 只验证调用参数正确）。

---

## P. 权限（Permission）

### P1. 未登录请求流式

无 Authorization header POST `/analyze/requirement`。断言：401 `UNAUTHORIZED`（ADR-004 require_user 拦截）。

### P2. viewer 发起流式分析

用户 V 是 P1 viewer。POST `/analyze/requirement`。断言：403 `FORBIDDEN`（role 不足 editor）。

### P3. viewer 保存分析

同 P2，`/analyze/save`：403。

### P4. viewer 读取 affected-nodes

viewer 可读。断言：200 正常返回。

### P5. editor 发起 + 保存

正常通过（G1 已覆盖）。

### P6. project_admin 发起

正常通过（admin 继承 editor 权限）。

### P7. platform_admin 跨项目访问

platform_admin 可访问任意项目。断言：流式 + save 正常通过。

### P8. JWT **自然过期**（`exp` 到期）中途（接受窗口）

JWT 有效期剩 10s，发起 L3 分析（预计 30s）。断言：
- 流式正常跑完（HTTP 长连接内不校验自然过期，与 ADR-004 原语义一致，非脱节）
- 流完后 save 请求用旧 JWT 返回 401；用 refresh token 换新 JWT 后 save 正常
- tests 记录：此行为**不是脱节**，是 ADR-004 预期行为

### P9. token **主动作废**（ADR-004 §5）场景

覆盖 ADR-004 §5 的 4 个触发事件：管理员禁用 / 用户改密 / 管理员强制登出 / 刷新令牌被盗。

**P9a 流开始前被作废**：
- 第一次 `require_user` 校验时 `iat < token_invalidated_at` → 401
- 断言：无流建立，无 dimension_record，无 activity_log

**P9b 流中途被作废**（接受脱节窗口）：
- 流运行时管理员触发 `revoke_all_user_tokens` → 更新 `users.token_invalidated_at`
- 当前已建流**继续跑完**（M13 设计明确接受，见 §8）
- 流完后用户尝试 save：新请求 `require_user` 时 `iat < token_invalidated_at` → 401
- 断言：流的 chunks 返回完整；save 被拦，无 dimension_record 产生
- 此行为**是已知脱节**（M13 设计 §8 声明，≤5min 暴露窗口）

---

## E. 错误处理（Error Handling）

### E1. AI Provider 瞬时失败

MockProvider 第 3 个 chunk 抛异常。断言：
- SSE 发了前 2 个 chunk + 1 个 `error` event
- `error.error_code = "ANALYSIS_PROVIDER_ERROR"`
- 连接正常关闭
- 无 dimension_record 写入（流未 save）
- 无 activity_log

### E2. AI Provider 首次调用就失败

MockProvider 进入 analyze() 立即抛异常。断言：
- SSE 只发 1 个 `error` event，无任何 chunk
- HTTP status 200（SSE 开始后不改 status；错误信号通过 error event）

### E3. 5 分钟 server 硬超时

MockProvider 10 分钟才结束。断言：
- 5 分钟时 `asyncio.TimeoutError` 被捕获
- SSE 发 `error` event, `error_code="ANALYSIS_TIMEOUT"`
- `provider.aclose()` 被调用（断言 mock 收到 aclose 信号）
- HTTP 连接关闭

### E4. provider quota 耗尽

provider.analyze 抛 `RateLimitError`。断言：
- `error_code="ANALYSIS_QUOTA_EXCEEDED"`, http_status 仍 200（SSE 已开始）
- M15 无 activity_log（流失败不记录）

### E5. save 时 M04 写入失败

模拟 M04 `create_dimension_record` 抛异常。断言：
- `/analyze/save` 返回 500 + `error_code="ANALYSIS_SAVE_FAILED"`
- 事务回滚：dimension_records 无残留 + activity_log 无残留（R-X3 共享 session）

### E6. save 时 affected_node_ids 包含不存在的 node

affected_node_ids = [非法 UUID / 跨项目的 node / 软删 node]。断言：
- **接受保存**（不做存在性校验）——M13 把 affected_node_ids 当作 AI 输出的"参考"，不承诺这些 ID 当前仍有效
- `/analyze/affected-nodes` 返回这些 ID 原样
- 关系图渲染时 M08 自行过滤已删节点（M08 职责）

### E7. 项目未配置 AI provider（配置错误 vs 瞬时故障区分）

Mock M02 `get_by_id_for_user` 返回 Project 对象但 `.ai_provider = None` / `.ai_api_key_enc = None`（项目未配 AI）。断言：
- 流式请求立即返回 SSE `error` event：`error="AI provider is not configured for this project; go to project settings to configure"`, `error_code="ANALYSIS_PROVIDER_NOT_CONFIGURED"`（http 422 语义，但 SSE 已开则 status 仍 200——前端按 error_code 路由"去配置页"UX）
- 无 chunk 发出
- **对比 E1**（provider 瞬时失败）：E1 的 `error_code="ANALYSIS_PROVIDER_ERROR"` 语义是"重试可能恢复"；E7 的 `_NOT_CONFIGURED` 语义是"重试也没用，去配置"。前端据此差异化 UX（E1 展示"重试"按钮，E7 展示"去配置"链接）

---

## S. 流式特化（SSE-specific，pilot 新增覆盖）

### S1. chunk 顺序保证

MockProvider 以指定顺序 yield 10 个 chunks。断言：SSE 客户端收到的 chunk text 拼起来 = 原始 order 拼接（无乱序 / 无丢失 / 无重复）。

### S2. complete event 只发 1 次

正常结束的流断言 `complete` 出现恰好 1 次，`error` 出现 0 次（互斥性）。

### S3. error 后用户可保存已累积 chunks

E1 场景完整链路：
- 前端收到 2 个 chunk + 1 个 error
- 用户点"保存已收到部分"按钮（UI 行为）
- 前端调 `/analyze/save`，`analysis_result = ""join(收到的 chunks)`
- 断言：save 成功，dimension_records 里存的是部分结果 + metadata 标记 `{partial: true}`（可选扩展 metadata 字段，tests 里可选断言）

### S4. AbortController 取消真停 provider

- 用户发起分析，MockProvider 预计 yield 20 个 chunk，每个间隔 100ms
- 收到 3 个 chunk 后前端 `abortController.abort()`
- 断言：
  - server 检测到 `is_disconnected()` = True（在第 4 次 yield 循环开头）
  - `provider.aclose()` 被调用 1 次（mock 收到信号）
  - 4-20 号 chunks 不再生成
  - 无 SSE error event（连接已断，发不出来）
  - 无 activity_log

### S5. 服务器重启期间的流

服务器收到请求后 `uvicorn` 被 kill（模拟重启）。断言：
- 前端 fetch promise reject（HTTP 连接断开）
- 用户看到"连接中断"（UI 行为）
- 服务器重启后用户点"再分析"正常工作
- 无 DB 残留（流无状态）

### S6. chunk 大小极端

- MockProvider 发 1 个 1MB chunk：断言 SSE 协议能承载（无报错）+ 前端能解析
- MockProvider 发 10000 个 1 字节 chunk：断言服务器顺序发出 + 前端顺序接收（性能不在本断言范围）

### S7. complete.metadata 完整性

每个流结束的 complete event 必有 metadata 6 字段：`ai_provider / ai_model / analysis_level / analysis_time_ms / matched_template_id`（可 null）/ （未来扩展：total_tokens）。

### S8. Content-Type 正确

所有流式 response 的 header：
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`（可选，HTTP/1.1 默认）
- `X-Accel-Buffering: no`（若过 Nginx 反代，建议加；本测试验证 FastAPI 默认行为）

### S9. `[E2E]` 前端流式 UI 交互

- Playwright 启动浏览器
- 登录 editor 用户
- 打开 node 档案页
- 点"AI 分析"，验证抽屉打开
- 等待第 1 个 chunk 显示（SSE 正确解析）
- 点"取消"，验证抽屉状态转"已取消"+ fetch 确实断开（network 面板无继续数据）
- 重新点"再分析"，完整流 + 点保存 + 验证抽屉关闭 + 历史列表出现新记录

---

## R. 流式 + 关系图联动（F13 AC4 对照）

### R1. save 后立即 affected-nodes 可读

save 返回 200 后立即 GET affected-nodes。断言：无缓存延迟，立即返回最新数据。

### R2. 多次 save 后 affected-nodes 返回最新

C3 场景后 GET affected-nodes，断言返回**最后一次 save** 的 affected_node_ids。

### R3. 无历史分析的 node

全新 node，GET affected-nodes。断言返回空数组 + `analysis_record_id=null`。

### R4. 历史分析后 node 被删

save 后删掉 node（M03 软删 / 硬删）。断言：
- GET affected-nodes 行为由 M04 `get_latest_dimension_record` 定义（若 node 级联删 dimension_records，返回空；若保留，返回历史）
- 本断言**不在 M13 tests 里**，属于 M03 级联删测试（M13 tests 只验证"存在的 node → 正确返回"）

---

## 测试基础设施要求

### MockProvider 要求

```python
# tests/fixtures/mock_provider.py
class MockProvider:
    def __init__(
        self,
        chunks: list[str],                    # 按顺序 yield 的 chunks
        delay_per_chunk: float = 0.0,         # 每个 chunk 之间 delay（模拟流速）
        error_at_chunk: int | None = None,    # 指定 chunk index 抛异常
        error_type: type[Exception] = Exception,
    ):
        self.chunks = chunks
        self.delay_per_chunk = delay_per_chunk
        self.error_at_chunk = error_at_chunk
        self.error_type = error_type
        self.aclose_called = False

    async def analyze(self, prompt: str, context: str) -> AsyncIterator[str]:
        for i, chunk in enumerate(self.chunks):
            if self.error_at_chunk == i:
                raise self.error_type("Mock provider error")
            yield chunk
            if self.delay_per_chunk:
                await asyncio.sleep(self.delay_per_chunk)

    async def aclose(self):
        self.aclose_called = True
```

### SSE 客户端 mock（pytest）

```python
# tests/fixtures/sse_client.py
async def collect_sse_events(response) -> list[tuple[str, dict]]:
    """解析 SSE response，返回 [(event_type, data), ...]"""
    events = []
    event_type = None
    async for line in response.aiter_lines():
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            events.append((event_type, json.loads(line[6:])))
            event_type = None
    return events
```

### 数据库 fixture

- `db_with_project_p1_editor_a`：P1 + user A 是 editor 的 baseline
- `db_with_cross_project_p1_p2`：P1 + P2 + user A 仅 P1 editor（用于 T 类）
- `db_with_node_n1_p1`：P1 下创建 node N1（"订单取消"）
- `db_with_analysis_history_n1`：N1 已有 1 条 requirement_analysis dimension_record

---

## 完成度判定

- [x] 6 类必答覆盖（Golden 5 / 边界 7 / 并发 4 / Tenant 5 / 权限 9 / 错误 7）
- [x] 流式特化 9 条
- [x] 关系图联动 4 条
- [x] 测试基础设施（MockProvider / SSE 客户端 / DB fixtures）
- [x] 所有决策已定，无 ⚠️ 渗漏（R14-1 合规）
- [ ] reviewer audit 三轮通过

---

## 关联

- [`00-design.md`](./00-design.md) §14 大纲
- [`M17-ai-import/tests.md`](../M17-ai-import/tests.md)（异步 pilot 测试范本）
- Prism 测试参考：`/root/prism/api/tests/test_analyze.py`（若存在）
