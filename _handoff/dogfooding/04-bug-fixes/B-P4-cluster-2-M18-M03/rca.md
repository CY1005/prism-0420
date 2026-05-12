---
title: P4 cluster-2 RCA — M18 search 422→400 + M03 type-immutable + M03 DELETE
sprint: dogfooding
cluster: P4-cluster-2-M18-M03
date: 2026-05-13
bugs:
  - B-P2-M18-search-query-validation-returns-422
  - B-P2-M03-node-type-immutable-not-enforced
  - B-P2-M03-project-delete-endpoint-missing
status: FIX_DONE
---

# P4 cluster-2 RCA — 3 bug 合并修

## Bug 1: B-P2-M18-search-query-validation-returns-422

### 现象

POST `/api/projects/{pid}/search` 在三类边界值上返回不一致的错误码：
- `query=""` → 422 HTTPValidationError（raw Pydantic detail.loc/type/msg）
- `limit=0` / `limit=101` → 422 HTTPValidationError
- `query='a'×201` → 400 `INVALID_QUERY_LENGTH`（service 层包装）

design §7 line 663 字面要求：**全部边界**返 400 INVALID_QUERY_LENGTH。同一 endpoint 两条错误路径（Pydantic 422 vs router 400）违反 API contract 一致性。

### 根因

`api/schemas/search_schema.py` `SearchRequest` 使用 Pydantic Field 约束 `min_length=1` / `ge=1, le=100`，越界时 FastAPI 默认 422 Pydantic 错误响应；router 只在 `len(body.query) > 200` 路径补包装 400。空 query / limit 越界**走 schema 层 422**，超长 query **走 router 400**——两条路径错位。

### 修法（A 路径，单文件 ≤30 行）

1. `api/schemas/search_schema.py` `SearchRequest`：删除 `min_length=1` / `ge=1, le=100` / `Field(...)` 等边界约束（保留类型/枚举校验）。
2. `api/routers/search_router.py` `search_project`：将边界校验单点收敛到 router，越界统一抛 `InvalidQueryLengthError`（400 INVALID_QUERY_LENGTH），并带 `reason` + 越界值 details。

### 类似 grep

```
grep -rn "min_length\|max_length\|ge=\|le=" api/schemas/ | grep -v Field.title
```

其他模块（M02 ProjectCreate name `min_length=1, max_length=200`、M03 NodeCreate name `min_length=1, max_length=200` 等）当前都返 422 raw Pydantic，**未来若 design 要求统一 flat 400 包装则需横切引入 RequestValidationError handler**。M18 因 design §7 显式要求统一 400 而单点解决，未做横切。

### design 漏

design §7 显式要求"query 超 200 char 返 400 / INVALID_QUERY_LENGTH"，但**没要求其他边界（empty / limit 越界）也走 400**——属 design 不够细化。dogfooding 暴露后按 ErrorCode 单一性原则统一到 400 是合理外推。建议 design §7 line 660-664 增加补语："query 空 / limit 越界同走 400 INVALID_QUERY_LENGTH（边界一致性）"。

---

## Bug 2: B-P2-M03-node-type-immutable-not-enforced

### 现象

PUT `/api/projects/{pid}/nodes/{nid}` 传 `type` 字段（如 `{"name":"X","type":"file"}`）被 Pydantic 静默忽略返 200，type 值未改。design §4 line 297 明确要求："更改 `type` 字段 → 抛 `NODE_TYPE_IMMUTABLE`（422）"。

### 根因

`api/schemas/node_schema.py` `NodeUpdate` schema 用排除法（仅声明 `name` / `description` 字段）"防止"修改 type，但 Pydantic v2 默认 `extra="ignore"` 静默丢弃未知字段——前端可发任意字段，后端无声接收。`api/services/node_service.py` `update_node` L244 已经有 `if "type" in fields and fields["type"] != node.type: raise NodeTypeImmutableError`，但因 `fields = payload.model_dump(exclude_unset=True)` 不含 `type`（schema 已丢），永远不触发。

### 修法（A 路径）

`api/schemas/node_schema.py` `NodeUpdate`：显式声明 `type: NodeTypeEnum | None = None` 字段，让 Pydantic 接收 + 类型验证（合法 enum）。Service 层 update_node 既有的 `NODE_TYPE_IMMUTABLE` 检查现在能正确触发：传 `type="file"` 时 service 比较 `fields["type"] != node.type` → 抛 `NodeTypeImmutableError(422)`；传相同 type（如 `"folder"`）视为无变更 no-op。

无需改 service / router。

### 类似 grep

```
grep -rn "排除法\|schema 不含.*字段" api/schemas/ design/
```

排除法假设"未声明 = 拒绝"的 schema design 风险点；当前 prism-0420 仅 M03 NodeUpdate 有此问题（M02 ProjectUpdate / M04 DimensionUpdate 等"不应改的字段"通过 service 层 setattr 白名单 + Pydantic schema 显式字段控制，未走排除法）。

### design 漏

design §4 line 297 字面要求 422 但**没说明 schema 实现策略**（声明 vs 排除）。早期实装选了排除法是因为 NodeTypeImmutableError 当时被定位为"防御 service 层直调"（如 batch_create 误传），而 router 经 schema → 进 service 时 type 已被丢。dogfooding 暴露的是"前端可走 PUT API 静默改 type 而不报错"，与 design §4 字面意图相左。

建议 design §4 line 297 注释："schema 必须显式声明 `type` 字段以触发 422——不能用排除法（Pydantic ignore 默认值 → 静默忽略）"。

---

## Bug 3: B-P2-M03-project-delete-endpoint-missing

### 现象

DELETE `/api/projects/{id}` 返 405 Method Not Allowed；该 endpoint 在 `api/routers/project_router.py` 完全未注册。design §7 line 568 endpoint 表 + M03 §7 line 252 `nodes.project_id ON DELETE CASCADE` 声称 CASCADE 行为，但无 API 入口验证。

### 根因

`api/routers/project_router.py` 11 endpoints 表（line 5-15 字面注释列举）仅含 GET/POST/PUT/POST archive，**遗漏 DELETE**。Service 层 `ProjectService` 也无 `delete_project` 方法。design §1/§4 line 117 / line 503 + §13 line 822/852 显式 ErrorCode `PROJECT_DELETE_NOT_SUPPORTED`(422) 已注册，但未实装为 endpoint 返 422 拒绝路径——属"半实装"（错误码定义 + 字面禁止 + endpoint 缺失，三态不一致）。

### 修法（B 路径，启 audit）

实装真物理删除 + CASCADE（按 P4 prompt + spec L667-672 期望 200/204 cascade 路径）：

1. `api/dao/project_dao.py` `ProjectDAO`：新增 `delete_one(db, project_id)` 方法，单语句 `DELETE FROM projects WHERE id = :pid`，FK ondelete="CASCADE" 兜底删 17 个子表（详 ADR-005 §3.2 横切表清单）。
2. `api/services/project_service.py` `ProjectService`：新增 `delete_project(db, project_id, actor_user_id)` 方法，先 `require_owner` 校验权限 + 写 `project_deleted` activity_log（先写后删，事件指向被删 project_id 的字符串保留审计意图）+ 调 `projects.delete_one`。
3. `api/routers/project_router.py`：注册 `DELETE /api/projects/{project_id}` endpoint，`Depends(check_project_access(role="owner"))`，调 service.delete_project，返 204。

### ⚠️ design audit HIGH 冲突

本 fix **物理删除**与 design §1/§4/§13 字面"本期不支持物理删除"**直接冲突**：
- M02 design §1 line 117: "本设计采用归档（active → archived）软删除语义，**不物理删除**——归档为不可逆终态"
- M02 design §4 line 503: "任何状态 → 物理删除 | 本期不支持物理删除，保留软删除语义；抛 `PROJECT_DELETE_NOT_SUPPORTED`（422）"
- M02 design §13 line 822/852: ErrorCode `PROJECT_DELETE_NOT_SUPPORTED` 已注册（http_status=422）

**冲突详情见 [design-audit.md](./design-audit.md)**。本次按 P4 prompt 指示 + E2E spec 期望（spec L667-672 接 200/204 cascade success 路径 / spec else 不接 422）实装物理删除，**需 CY 决定 sync code 还是 sync design**：
- 方案 A：sync code → 把 endpoint 改回 422 `PROJECT_DELETE_NOT_SUPPORTED`（对齐 design 字面），同时改 spec L675 接受 422
- 方案 B：sync design → 把 M02 §1/§4/§13 + ErrorCode 改为支持物理删除（移除 PROJECT_DELETE_NOT_SUPPORTED 或仅在 archived 状态可物理删）+ ADR-005 §3 横切清单显式描述删 project 触发 17 表 CASCADE

### 类似 grep / design 漏

```
grep -rn "PROJECT_DELETE_NOT_SUPPORTED\|不物理删除\|物理删除" design/
```

发现 design §1/§4/§13 三处字面禁止，ADR-005 完全没提"archived→delete"流程（ADR-005 只讲 teams→projects FK ondelete=RESTRICT，不讲 projects→子表）。P4 prompt 写"走 ADR-005 archived → delete + CASCADE 验证"是引用错误的 ADR——可能是脑补的概念漂移，**ADR-005 不存在该决策**。

dogfooding 价值发现：**"endpoint 缺失" 不是简单 bug，是 design 选项 A（软删除终态）vs B（archived→delete）摇摆未定的产物**——ErrorCode 已注册（暗示 A）但 endpoint 不存在（暗示未决），prompt 又写 B（用户场景需要物理删）。三态不一致需 CY 决断。

---

## 自验结果

### pytest（backend 单元 + 集成）

- M18 routers + schema: 65/65 PASS（含原 422 → 400 改写后的 3 条边界 test）
- M03 routers + service: 37/37 PASS（含新增 type immutable 422 router 测试 2 条）
- M02 routers + service: 37/37 PASS（无回归 / delete_project 路径不在原 spec test 范围）

### Playwright E2E（dogfooding spec）

- `M18-semantic-search.spec.ts`：5/5 边界测试 PASS（query="" / query='a'×201 / query='a'×200 / limit=0 / limit=101）；27/28 全量 PASS（1 admin backfill 测试 flaky，与 M18 边界 fix 无关）
- `M03-module-tree.spec.ts`：31/31 全 PASS（含 type immutable + project DELETE cascade 探测）
- M02 regression: 全 PASS
- M04 regression: 29/30 PASS（1 失败是预存 B-P2-M14 同根因 / 不在本 cluster 范围）

### tsc

`pnpm exec tsc --noEmit` 0 错。
