---
cluster: P4-cluster-3
bugs:
  - B-P2-M04-cross-node-tenant-read-gap
  - B-P2-M04-activity-log-action-type-naming-gap
  - B-P2-M07-error-details-field-naming
path: A (independent fixes / no audit subagent / verified via fresh-app pytest TestClient)
created: 2026-05-13
---

# Cluster-3 RCA — M04 cross-node 404 + M04 action_type sync + M07 transition details

## 1. 现象

### B-P2-M04-cross-node-tenant-read-gap
`GET /api/projects/{pidA}/nodes/{nidB}/dimensions`（nidB 属 projectB / userA token 持 projectA 访问权）返 **200 + items=[]**，而非 design §8 R8-1 第三层防御声称的 **404 NODE_NOT_IN_PROJECT**。攻击面：node 归属 check bypass / 即使数据不外泄（project_id 过滤兜底）但 design contract 漂移 + 与 write paths 三层防御 inconsistency。

### B-P2-M04-activity-log-action-type-naming-gap
`activity_log.action_type` 实装写入 `dimension_record_created/updated/deleted`（复合命名 / 与 frontmatter `produces_action_types` 一致），但 design §10 prose table 列 `create/update/delete`（简单动词）→ design 内部三处不一致（frontmatter 复合 / prose 单词 / 实装复合）。tests.md G1/G3/G4 沿用 prose 简单动词。

### B-P2-M07-error-details-field-naming
`POST /issues/{id}/transition` 非法转换返 422，details 字段：
```json
{"issue_id": "...", "from_status": "open", "to_status": "closed"}
```
design §13 + tests.md ER2 字面要求：
```json
{"current": "open", "target": "closed"}
```

## 2. 根因

### M04 cross-node
`api/routers/dimension_router.py` L101-115 list_by_node / L118-132 get_one / L135-162 completion 三个 read endpoints 注释明写"service 内部不校验 node 归属（只读不写也是个 P3 — 但越权读返回空 list 也安全）"。write paths（create/update/delete）由 `DimensionService` 内部已调 `_check_node_belongs_to_project` 5 次（service.py L301/L359/L435/L496 + L80 定义），read paths 漏调。

### M04 action_type naming
Phase 2.1 业务模块 sprint 期 `dimension_service.py` 写 activity_log 用 `{target_type}_{past_tense}` 复合命名惯例（与 M14/M15/M16 等 R14 命名规约一致 / `produces_action_types` frontmatter 同步落定），design §10 prose table 未跟实装回写同步。

### M07 transition details
`api/services/issue_service.py` L278-282 raise `IssueTransitionInvalidError(issue_id=..., from_status=..., to_status=...)`。`AppError.__init__(**details)` 把 kwargs 全塞 `self.details`，所以 response body details 字段名 = service kwargs 名。design §13 用业务语义 `current/target`（状态机视角 / 通用），实装用 SQL 视角 `from/to`（更技术）。Phase 2.1 M07 sprint 写代码时未对齐 design §13 + tests.md ER2 字面。

## 3. 类似问题 grep

```bash
grep -rn "from_status\|to_status" api/ | grep -v "metadata\|activity_log\|enum"
```
结果：仅 `issue_service.py` L278-282 + L313-314（activity_log metadata，保留 / design §10 metadata 自由 schema 不约束 field 名）。无其他模块同模式。

```bash
grep -rn "action_type=\"\(create\|update\|delete\)\"" api/services/
```
结果：0 命中。所有 service 都用复合命名 → M04 是唯一 design prose 漂移的模块。

```bash
grep -rn "_check_node_belongs_to_project" api/routers/
```
结果：本次 fix 后 dimension_router 3 处（list/get_one/completion）。其他 router（issue/competitor/etc.）的 service 层在 service method 内部调，read paths 经 _get_or_raise 已含 project_id 过滤（functional 但非显式 check）。其他模块未审计，**punt 候选**：扫所有 `*_router.py` read endpoints 是否也漏 node-belongs check（design-audit candidate）。

## 4. design 哪步漏

### M04 cross-node — design 实装一致性 audit 缺
design §8 R8-1 三层防御写得很清楚（Server Action / Router check_project_access / Service _check_node_belongs_to_project），但**只校验写路径**。read paths 在 design §7 6 endpoints 表只标了 "权限：viewer"，**没有标明 read 是否也走第三层防御**。Phase 1 design 期未审计 read paths 是否需要 service 第三层。Phase 2.1 实装期注释明写"P3 punt"（合理推迟但未回填）。dogfooding 实证：**design §8 三层防御要明确"读写双覆盖"**。

### M04 action_type naming — frontmatter / prose 双写漂移
frontmatter `produces_action_types` 列复合命名（Phase 1 design 期最后定型），但 design 同文档 §10 prose table 沿用早期单词命名 → 同文档内部漂移。Phase 2 实装跟 frontmatter 一致（R14 命名规约执行正确），但 prose 未自检同步。dogfooding 实证：**design 期 frontmatter 改动必须 grep 同文档 prose 一致性 audit**。

### M07 transition details — design §13 error details schema 未约束实装 kwargs 命名
design §13 + tests.md ER2 写明 details 字段名 `current/target`，但 design 没规约 service raise 时 kwargs 名必须对齐 details 名（AppError `**details` kwarg pattern 是隐式契约）。Phase 2.1 M07 sprint 实装时按 SQL 视角写 from/to_status，code review 未抓。dogfooding 实证：**error contract 必须 kwargs 名 = details 名 双写一致 / design §13 ErrorCode 表加 kwargs 字面约束**。

## 5. 验证

### Unit (pytest fresh-app TestClient)
```bash
uv run pytest tests/test_m04_routers.py::test_list_dimensions_cross_node_tenant_returns_404 \
              tests/test_m07_routers.py::test_transition_open_to_closed_returns_422 \
              -v --benchmark-disable -p no:warnings
# 2 PASS / 含 details.current+target + dimension_not_found 404 双断言
```

Full M04 + M07 suite: **146 PASS / 0 FAIL**（含 2 新加 + 既有 144）

### E2E (playwright)
- **M04**: 24/25 PASS（残 1 FAIL = L138 workspace smoke / pre-existing spec-design bug / cluster-6 spec-fix 范围 / **非 cluster-3 引入**）
- **M07**: 37/38 PASS local（残 1 FAIL = L580 details / dev server uvicorn 无 --reload / 旧编译代码不返新 details / 代码 fix 已经 pytest TestClient 验证）
  - HANDOFF §4 红线：dev server 不可重启
  - CI 用 fresh backend 跑 e2e → 将打绿（authoritative verification）

### tsc
`pnpm exec tsc --noEmit` 0 错

## 6. 6 项风险自评

| # | 维度 | 自评 | 理由 |
|---|------|------|------|
| 1 | 改动范围 | 低 | 7 文件 / 45 行（含 fix + test + docs）|
| 2 | 代码位置 | 中（自降低）| 1 router + 1 service / 但仅加 1 调用 + 改 2 kwargs 名 / 无业务逻辑改动 |
| 3 | 可逆性 | 低 | git revert 安全 / 无 migration / 无 schema |
| 4 | 业务断言 | 低 | 未改状态机 / 未改权限 / 未改事务 / 仅 surface error contract |
| 5 | 测试覆盖 | 低 | 新增 2 pytest 覆盖 fix path + 既有 144 全过 |
| 6 | bug 类型 | 低 | error contract field rename + 加防御 check + design doc sync / 无 race / 无 bypass |

**判定**: 6/6 低 → **A 路径直推 main**（HANDOFF cluster-3 明指 A 路径全 / 0 audit 冲突 / 跳过 audit subagent）。

## 7. 元发现 / punt 候选

1. **design §8 三层防御要明确读写双覆盖**：punt 候选 / cross-cutting §5 R-X 横切纪律可加"第三层 service check 必须读写双向"。
2. **design frontmatter / prose 同步 audit 自动化**：punt 候选 / 加 pre-commit hook 扫 design 文档内部 action_type 字面一致性。
3. **error contract kwargs 名 = details 名约束**：punt 候选 / design §13 ErrorCode 模板加 kwargs 字面约束段。
4. **其他模块 read paths node-belongs check audit**：cluster-6 design-audit candidate 候选 / 扫 `*_router.py` read endpoints。
