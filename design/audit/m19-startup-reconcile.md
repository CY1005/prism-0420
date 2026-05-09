---
title: M19 sprint 启动期 reconcile pass — 三栏分类 + 配套验收
status: accepted
owner: CY
created: 2026-05-09
sprint: M19 导入/导出 / complexity=low / pilot=false / Phase 2.1 90%→95%
trigger: M18 sprint 完成（commit 249bc12 / 1480 PASS）后启动 M19
related:
  - design/02-modules/M19-import-export/00-design.md（status=accepted 2026-04-21）
  - design/00-phase-gate.md（闸门 2.5 reconcile pass + 闸门 3.4 L1 总则）
  - _handoff/cross-sprint-punt-pool.md（M18 新增 #20-#24 + 触发点 A）
  - design/99-comparison/phase-gate-bypass-log.md（#2 配套验收：M18 真跑 ✅ / M19 必继续）
---

# M19 sprint 启动期 reconcile pass

> 闸门 2.5 三栏强制分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）。
> B 栏前先穷举 L1 锁规候选（feedback_problem_layered_analysis 失效信号 /
> M17 启动期 R1-A P1-1 立规：B 栏 = 0 时禁列 B 栏）。

## 0. 执行摘要

| 栏目 | 项数 | 状态 |
|------|------|------|
| **A 机械可做** | **6** | 全 ✅（本 commit 内修完 / 部分留子片 1+3 落地） |
| **B 待 CY 决策** | **0** | M19 design accepted 2026-04-21 / 6 项 CY 决策 Q1-Q6 全锁 / 三轮 reviewer audit 已过 |
| **C 已自我消解** | **8** | 横切 helper 已稳定 / 复用 M02-M18 范式 / pilot=false 不需新模板 |

**B 栏 = 0 第十四次实证**（M05-M18 十三连 + M19 第十四）。

---

## 1. A 栏：机械可做（6 项）

### A1 [本启动期] §14.5 Sprint Review 拆分计划补完

闸门 3.4 L1 总则强制段。已 append 到 design/02-modules/M19-import-export/00-design.md（节 14.5 / 5 子片拆分 + R1=3 + R2=1 + 范式复用清单 19 项 + L3 留空 3 项）。

### A2 [本启动期] bypass log #2 配套验收最终 ✅

M16 bypass + M17 恢复 + M18 继续 = 累计 2 次 bypass 不复位 / 第 3 次触发闸门 3.4 L1 review。M19 必继续 R1=3 subagent 并行 + R2=1 合并 Opus 真跑（不再降级 / 不复位累计触发线）。spawn prompt 必含 ls/find 穷举要求；spawn 后 >5min 无通知必主动 ping。

### A3 [本启动期] cross-sprint punt 池本 sprint 命中检查

| # | punt | 本 sprint 命中？ | 处置 |
|---|------|-----------------|------|
| #3 | IssueResponse 漏 join 字段 | M19 不触 IssueResponse / N/A | STILL_PUNT |
| #6 | M07 update detach（None→NULL） | M19 全只读 / N/A | STILL_PUNT |
| #11 | IntegrityError 转换缺口 M04 dimension B3+C7.1 | M19 全只读 无 INSERT / N/A 显式声明 | STILL_PUNT |
| #12 | M04-9 target_type hard-code | M19 不触 dimension_service / N/A | STILL_PUNT |
| #13 | M04-1 (updated_by, updated_at) 联合索引 | M19 不写 dimension_records / N/A | STILL_PUNT |
| #14 | M04-8 db.get(DimensionType) 三处 | M19 不触 dimension_service / N/A | STILL_PUNT |
| #15 | M04-R2 A1 DimensionResponse 缺 join | M19 不返回 DimensionResponse（Markdown bytes） / N/A | STILL_PUNT |
| #17 | _sanitize_filename horizontal | **第三实例触发评估**：M11 输入端 + M17 输入端 + **M19 输出端 Content-Disposition filename**——根源不同（输入：用户上传 / 输出：服务端生成），**留 sprint 子片 4 评估**是否合并到 api/utils/upload_helpers.py 还是新建 api/utils/download_helpers.py。当前倾向：M19 输出端 filename 是服务端构造 `prism-export-{timestamp}.md` + project_name 拼接，需要 strip 控制字符 + UTF-8 兼容 + RFC 5987 编码（与 M11/M17 input sanitize 不同形态） / 子片 4 立修后回写本表 |
| #20 | require_platform_admin 去重 | **不触发**：M19 design §8 字面 viewer 即可导出 / 无 admin endpoint / 不引入 require_platform_admin | STILL_PUNT |
| #21 | M18 worker source_text 真接 | M19 不触 embedding worker / N/A | STILL_PUNT |
| #22 | M18 noop 转 succeeded | 同上 | STILL_PUNT |
| #23 | M18 cron PCT 维度 | 同上 | STILL_PUNT |
| #24 | M18 batch_backfill | 同上 | STILL_PUNT |

**触发点 A 4 项**（M04-1 / M04-8 / M04-9 / M04-10）：M19 不触 dimension_service / N/A 显式声明 / 全部 STILL_PUNT。

### A4 [子片 1 责任] ActionType+1（"export"）4 处同步

design §10 + frontmatter line 51-53 字面：M19 写 export 事件到 activity_log，但 export action_type 不在当前枚举中；待 Phase 2 Alembic 迁移添加。

实施位置（M15 横切表 owner enum 4 处同步范式）：
1. `api/models/activity_log.py:_ACTION_TYPES` tuple 末尾追加 `"export"`（含 M19 段注释）
2. `api/schemas/activity_stream_schema.py:ActionType` StrEnum 末尾追加 `export = "export"`
3. CheckConstraint 自动同步（已基于 _ACTION_TYPES tuple 构造）
4. Alembic m19_export.py: `op.execute("ALTER TABLE activity_logs DROP CONSTRAINT ck_activity_log_action_type")` + 新 CHECK with "export" included

TargetType："node" 已存在（_TARGET_TYPES line 139）→ 无新增。

### A5 [子片 1 责任] ci-lint R14 验证

M16 sprint 立的 R14（write_event 调用 action_type 必须 _ACTION_TYPES 枚举字面 / ci-lint grep 守护）：M19 service write_event(action_type="export") 必字面命中枚举 / 不漂移。子片 1 + 3 实施时同步验证。

### A6 [子片 3 责任] 3 ErrorCode + 3 AppError 子类

design §13 字面已锁：
- EXPORT_NODE_LIMIT_EXCEEDED (422)
- EXPORT_NODE_NOT_IN_PROJECT (404 / 继承 NotFoundError)
- EXPORT_EMPTY_CONTENT (422)

留子片 3 落地（service 层 INSERT N/A / IntegrityError 清单 6 N/A 显式 / 全只读）。

---

## 2. B 栏：待 CY 决策（0 项 / 第十四次实证）

### B 栏 = 0 穷举 L1 锁规候选清单（防"反正都锁了 / 没看见决策点 = 没锁规"认知漂移）

| # | 候选决策点 | 是否已锁规 | 锁规来源 |
|---|-----------|----------|---------|
| 1 | 导出入口设计（A 多 node / B 单 node / AB 共存） | ✅ 锁 | CY ack 2026-04-21 / Q1 = AB 共存 / design §1 + §7 字面 |
| 2 | 报告内容范围（A 仅维度 / B 维度+版本 / C 完整档案） | ✅ 锁 | CY ack 2026-04-21 / Q2 = C 完整档案 / include 选项可控 |
| 3 | 是否记录导出历史（A 不记录 / B 新建 export_records 表） | ✅ 锁 | CY ack 2026-04-21 / Q3 = A 不记录 / activity_log 满足审计 |
| 4 | DAO 复用策略（A 复用各模块 DAO / B 新建 export_dao.py） | ✅ 锁 | CY ack 2026-04-21 / Q4 = A 复用 / ADR-003 规则 1 |
| 5 | node_ids 最大数量（10 / 20 / 50） | ✅ 锁 | CY ack 2026-04-21 / Q5 = 20 |
| 6 | idempotency 范围（无 / 有） | ✅ 锁 | CY ack 2026-04-21 / Q6 = 无幂等 |
| 7 | 同步 vs 异步导出 | ✅ 锁 | design §1 灰区 3 字面 / 本期同步（异步 = M17 链路） |
| 8 | 权限层级（viewer / editor） | ✅ 锁 | design §8 字面 / viewer 即可（只读） |
| 9 | Markdown 报告结构 | ✅ 锁 | design §7 字面 / project_name + node + 维度 + 版本 + 竞品 + 问题 |
| 10 | activity_log target_type（node vs project） | ✅ 锁 | design §10 字面 / target_type=node（M15 数据流转可精确定位） |
| 11 | 输出端 filename sanitize horizontal 化（合并 upload_helpers vs 新建 download_helpers） | ⏸️ punt 子片 4 实证后决定 | 横切技术决策 / 不阻塞业务路径 / 留 sprint 实证（参 cross-sprint #17）|

→ B 栏 = 0 项（第十四次实证 / M05-M19 十四连）。第 11 项是技术 punt 不是 CY 业务决策。

---

## 3. C 栏：已自我消解（8 项）

| # | 项 | 消解原因 |
|---|---|---------|
| C1 | M19 无主表 SQLAlchemy class | design §3 字面 / 只读聚合 / 复用上游模型 |
| C2 | M19 无状态机 | design §4 字面 / 无状态实体 |
| C3 | Queue payload tenant | design §12 字面 / 无 Queue / N/A |
| C4 | 乐观锁 version | design §5 清单 2 字面 / 只读 / N/A |
| C5 | idempotency_key | design §11 字面 / 无幂等 / N/A |
| C6 | R-X1 orchestrator 失败补偿 commit boundary | M19 同步只读 / 无补偿形态 / N/A |
| C7 | 上游 DAO 方法已存在（DimensionDAO.list_by_node / VersionDAO.list_by_node / CompetitorDAO.list_refs_by_node / IssueDAO.list_by_project + node_id / NodeDAO.list_by_ids） | grep 命中所有方法签名 / 无新增 / 子片 2 仅 import + DI |
| C8 | M18 沉淀的 4 项 R1+R2 sink 立规候选（EndpointRequest schema 不继承 TaskPayload / pgvector 三层降级 / 占位 metadata _stub / 测试反模式 assert True） | M19 不触发 embedding/queue 路径 / 全 N/A 显式声明（§14.5 范式复用清单字面） |

---

## 4. 启动期完成 checklist

- [x] §14.5 Sprint Review 拆分计划补完（design 节 14.5）
- [x] bypass log #2 配套验收最终 ✅（M19 必继续 R1=3 + R2=1 不复位）
- [x] cross-sprint punt 池本 sprint 命中检查（13 项 STILL_PUNT 中 1 项触发评估 #17 / 12 项 N/A）
- [x] B 栏 = 0 穷举 L1 锁规候选清单（11 项 / 第十四次实证）
- [x] C 栏 8 项自我消解
- [x] design status accepted 2026-04-21 不需 audit flip
- [x] baseline-patch 检查：M19 design references 仅触发 ActionType+1（不触其他模块改动）

---

## 5. 元贡献候选（sprint 完成后回写 m19-pilot-template-validation.md）

- M19 是 Phase 2.1 倒数第 2 个 own sprint（M20 团队是最后）
- M19 形态特殊性："只读聚合 + 同步 Markdown 二进制响应 + Content-Disposition filename sanitize 输出端首发"——区别于 M11/M17 输入端 multipart sanitize；horizontal 化决策（合并 upload_helpers vs 新建 download_helpers）留实证
- pilot=false / complexity=low → R1+R2 数据点 16 → 17 是否仍稳定（M02-M18 16 数据点稳态验证）
- N/A 元教训显式声明范式应用（§14.5 范式复用清单 19 项 / 7+ N/A 项）

---

last_updated: 2026-05-09
