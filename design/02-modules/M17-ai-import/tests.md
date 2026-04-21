---
title: M17 AI 智能导入 - 测试场景
status: accepted
owner: CY
created: 2026-04-21
accepted: 2026-04-21
last_reviewed_at: 2026-04-21
module_id: M17
prism_ref: F17
pilot: true
complexity: high
---

# M17 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> M17 是异步 pilot——测试场景重点覆盖 Queue / 重试 / WebSocket / 批量事务回滚 / tenant 隔离

---

## 1. Golden Path（3 输入形态各跑通）

| ID | 场景 | 输入 | 期望 |
|----|------|------|------|
| G1 | zip 完整 4 步流程 | 用户传 1MB zip（10 文件） | 提交 200 → Queue 拉起 extract → ai_step1 → ai_step2 → awaiting_review（WebSocket 推 review_ready）→ 用户确认 → ai_step3 → importing → completed；activity_log 8 条 |
| G2 | git URL clone 流程 | 用户传 https://github.com/foo/bar.git | 同 G1 但 extract 阶段走 git clone；clone 成功后流程一致 |
| G3 | .git 包流程 | 用户传 5MB .git 包 | 同 G1 但 extract 解压 .git 包；流程一致 |
| G4 | 用户调整 review 后入库 | 在 awaiting_review 阶段用户改 node 名 + 跳过 2 个 item | confirm 入库后 nodes/dimensions 含用户调整的命名；skip_items 不写入 |
| G5 | idempotency 命中 | 用户 1 小时内重复传同 zip | 第二次提交返回 200 + 上次 task_id（不重新跑 AI）|

---

## 2. 边界场景

| ID | 场景 | 期望错误 / 行为 |
|----|------|----------------|
| E1 | 上传超大 zip（>500MB）| 422 + 提示"单 zip 上限 500MB" |
| E2 | 损坏 zip | extract 阶段 status=failed + ErrorCode `IMPORT_INVALID_SOURCE` |
| E3 | git URL 不可达 | extract 失败重试 3 次 → status=failed + ErrorCode `IMPORT_INVALID_SOURCE` |
| E4 | git URL 私有 repo（无 token） | 同 E3 行为，error_message 含"authentication failed" |
| E5 | .git 包格式错（非 git bare repo） | 422 + ErrorCode `IMPORT_INVALID_SOURCE` |
| E6 | zip 内全是无关文件（图片/二进制） | step1 拆分识别 0 个模块 → status=completed + 空 review_data + activity_log "0 modules detected" |
| E7 | AI 输出格式错（非 JSON） | step1 重试 3 次都格式错 → status=failed + ErrorCode `IMPORT_AI_PROVIDER_ERROR` |
| E8 | review_data 超大（>50MB JSON） | 写入 PG TOAST 自动压缩，可读出；性能下降但可用 |
| E9 | 用户提交后立即调用 confirm（不等 awaiting_review） | 409 + ErrorCode `IMPORT_INVALID_STATE_TRANSITION` |

---

## 3. 并发场景

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 同 user 重复提交同 zip | 1 秒内连续提交两次相同 source_hash | 两次都返回 200 + 同一 task_id（idempotency 命中）；只跑一次 AI |
| C2 | 同 user 不同 zip 并发提交 | 提交 zip-A + zip-B | 两个独立任务，独立 Queue 处理；互不阻塞 |
| C3 | 多 user 同 project 同时提交 | userA + userB 各传 zip 到同 project | 两个独立任务（user_id 不同 idempotency 不命中）；Queue 隔离正确 |
| C4 | 用户 cancel 同时 Queue worker 在跑 | 提交后立即 cancel | worker 检测 status=cancelled 中断处理；已写入数据回滚；活跃 WebSocket 推 cancelled 事件 |
| C5 | review 阶段 user-A 改 mapping，user-B（同项目 editor）也改 | 同 task_id 双 user PUT review | 第二个写覆盖第一个（无乐观锁）；可考虑加 last_modified_by 提示——⚠️ 暂不实现 |

---

## 4. Tenant 隔离（异步 pilot 重点）

| ID | 场景 | 期望 |
|----|------|------|
| T1 | 跨项目越权访问任务 | userA 用 projectA 的 token，访问 projectB 的 task | 404 `IMPORT_TASK_NOT_FOUND`（不暴露 forbidden）|
| T2 | **Queue payload 篡改 user_id** | 直接往 Redis Queue 投递 payload（伪造 user_id） | Queue 消费者入口 `TaskPayload.parse()` 校验通过但 `service.check_access` 失败 → 任务标 failed + 安全日志 |
| T3 | **Queue payload 缺 project_id** | 投递不含 project_id 的 raw payload | Pydantic 校验失败 → ValidationError → 任务死信 |
| T4 | DAO 直查另 user 任务 | 单元测试 `ImportTaskDAO.get_by_id(other_user_task_id, projectA, userA)` | 返回 None（user_id 过滤生效） |
| T5 | WebSocket 越权连接 | userA 连接 userB 的 task progress WS | WS 握手 401 + 关闭连接 |

---

## 5. 权限场景

| ID | 场景 | 期望 |
|----|------|------|
| P1 | viewer 提交导入 | 403 + ErrorCode `PERMISSION_DENIED` |
| P2 | 未登录 | 401 + ErrorCode `UNAUTHENTICATED` |
| P3 | role 中途降级（editor → viewer） | 已提交任务继续跑（Queue 不查实时权限）；新提交被拒 |
| P4 | 项目删除时有进行中任务 | 任务级联删（FK CASCADE）+ 已写入数据级联删 + Queue worker 检测到任务不存在中断 |

---

## 6. 错误处理 + 重试

| ID | 场景 | 期望 |
|----|------|------|
| R1 | AI 调用失败 1 次 | 自动重试，1s 后再调；progress 不变；activity_log 一条 retry |
| R2 | AI 调用失败 2 次 | 4s 后再调 |
| R3 | AI 调用失败 3 次 | status=failed + ErrorCode `IMPORT_AI_PROVIDER_ERROR` + dead_letter=true |
| R4 | 死信 30 天后清理 | cron 任务删 task + items + S3 暂存文件；activity_log 一条 cleanup |
| R5 | 批量入库部分失败（10 个 item，3 个 FK 冲突） | 整事务回滚 + status=partial_failed + items 状态保留（用户可重试） |
| R6 | partial_failed 用户点重试 | 重新跑 ai_step3 + importing；只处理 status=failed 的 items；其他 skipped |
| R7 | Queue worker crash 中途 | arq 自动重新拉起任务（持久化保证）；从最后 status 继续 |

---

## 7. 状态机场景

| ID | 场景 | 期望 |
|----|------|------|
| SM1 | pending → ai_step3（跳步） | 拒绝 + ErrorCode `IMPORT_INVALID_STATE_TRANSITION` |
| SM2 | completed → 任意 | 拒绝 + ErrorCode `IMPORT_TASK_FINALIZED` |
| SM3 | cancelled → 任意 | 拒绝 + ErrorCode `IMPORT_TASK_FINALIZED` |
| SM4 | 用户在 pending 状态 cancel | task 直接删（无已写入数据）+ S3 暂存清理 |
| SM5 | 用户在 importing 状态 cancel | 已写入 nodes/dimensions/competitors/issues 全部回滚（事务包裹支持）+ activity_log cancel |
| SM6 | partial_failed → ai_step3 重试 | 允许（节 4 显式标） |

---

## 8. WebSocket 场景

| ID | 场景 | 期望 |
|----|------|------|
| WS1 | 客户端连接活跃任务 WS | 100 ms 内推送当前 status + progress |
| WS2 | 客户端发 cancel 命令 | 服务器调 service.cancel + 推 cancelled 事件 |
| WS3 | 客户端发未知命令 | 推 error 事件，连接保留 |
| WS4 | 长连接 30 分钟无事件 | 服务器推 ping 保活；客户端无回应 → 关闭 |
| WS5 | 任务完成后客户端连接 | 推送当前 final status + completed 事件，关闭 |

---

## 9. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 idempotency 查询每条分支 + tenant 过滤 |
| Service | ≥ 90% | 含状态机所有合法/非法转换 |
| Queue tasks | ≥ 85% | 含 3 次重试 + 死信路径 |
| Router + WebSocket | ≥ 80% | e2e 优先 |
| Component | ≥ 70% | 4 步向导 + 进度条 |

---

## 10. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码：`design/01-engineering/01-engineering-spec.md` 规约 7
- 异步约束：`design/00-architecture/06-design-principles.md` 清单 3
