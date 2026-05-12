---
fix: B-P4-cluster-1-M06-competitor
cluster: P4 cluster-1（双修合并 / 同模块 M06 / 同 commit）
bug_ids:
  - B-P2-M06-competitor-not-found-returns-422
  - B-P2-M06-competitor-ref-response-no-display-name
risk_path: A 路径（单模块 / 单 service + dao + schema / 单文件改动 ≤30 行 / 不动 design / 不涉 migration）
created: 2026-05-13
status: 已修 / pytest M06 65/65 PASS / playwright M06 23/24 PASS（残留 test 14 = 已立 B-P2-M10 跨切 / 非本 cluster 范围）/ regression M01/M02/M07 48/48 PASS / tsc 0 错
---

# RCA — P4 cluster-1 M06 双修

## §1 Bug 1：competitor 不存在创建 ref 返 422 而非 404

### §1.1 现象

- 入口：`POST /api/projects/{pid}/nodes/{nid}/competitor-refs` with `{ competitor_id: "00000000-0000-0000-0000-000000000000" }`（全零 UUID / 不存在的 competitor）
- 实测响应：`422 Unprocessable Entity` + `{"code":"competitor_cross_project", ...}`
- 期望响应（design §13 + tests.md + M06-competitor.spec.ts test 12）：`404 Not Found` + `{"code":"competitor_not_found", ...}`
- 受影响 spec：
  - test 12 line 472 `[P0] API 旁路: competitor_id 不存在创建 ref 返 404 COMPETITOR_NOT_FOUND` — 状态码断言 FAIL
  - test 14 line 535 `[P0] API 旁路: 错误响应格式符合规约` — 状态码断言 `res.status()).toBe(404)` FAIL（残留 wrapper 格式问题是 B-P2-M10 跨切 / 见 §5）

### §1.2 根因

`api/services/competitor_service.py` `create_ref` L261-265（fix 前）只走单一查询：

```python
c = await self.dao.get_competitor_by_id(db, competitor_id, project_id)
if c is None:
    raise CompetitorCrossProjectError(...)  # ← 不区分"不存在" vs "跨项目"
```

`get_competitor_by_id` 强制 `WHERE id=? AND project_id=?` tenant 过滤（design §9 DAO tenant 过滤策略 / 豁免清单：无）。所以两种 case 都返 None：
1. competitor 全局不存在
2. competitor 存在但属于其他 project

旧实装一刀切走 `CompetitorCrossProjectError(http_status=422)`，违反 design §13 要求的"竞品不存在 → COMPETITOR_NOT_FOUND/404"契约。

### §1.3 类似问题 grep

```bash
grep -rn "get_.*_by_id.*project_id\|raise.*CrossProject" api/services/ | grep -v test
```

同款"不区分不存在 vs 跨项目"风险点排查：
- `issue_service.py` create_issue 调 `_check_node_belongs_to_project` 时已先 `node_dao.get_by_id(node_id, project_id)`，未存在和跨项目都走 422 `ISSUE_NODE_CROSS_PROJECT` — 同款 issue 但 design §13 M07 只声明 `ISSUE_NODE_CROSS_PROJECT`，未要求 `NODE_NOT_FOUND` 分离 → 不构成 bug / **登记为 follow-up audit** 候选
- `dimension_service.py` / `version_service.py` 等其他 service 跨模块引用查询均单查带 project_id 过滤，但 design §13 各模块表均未明确"不存在 vs 跨项目"分离 → 同款风险 / 沉淀候选

### §1.4 design 哪步漏

- M06 `design/02-modules/M06-competitor/00-design.md` §13 ErrorCode 表 L466-491 字面声明：
  - `COMPETITOR_NOT_FOUND = "competitor_not_found"` http_status=404
  - `COMPETITOR_CROSS_PROJECT = "competitor_cross_project"` http_status=422
- 但 §6 service 接口签名 + §8 三层防御均未明确"create_ref 时 NOT_FOUND vs CROSS_PROJECT 区分时机"
- Phase 1 设计前置时只列了错误码 / 未列错误路径决策树
- Phase 2.1 实装时按"单 DAO 查询带 tenant 过滤" Phase 2.0 工程默认范式 → 走 CrossProject 一条路 → 漏 NotFound

### §1.5 修复

`api/services/competitor_service.py` `create_ref` L261-265 → 改成两步：

```python
c = await self.dao.get_competitor_by_id(db, competitor_id, project_id)
if c is None:
    global_c = await self.dao.get_competitor_global(db, competitor_id)
    if global_c is None:
        raise CompetitorNotFoundError(competitor_id=str(competitor_id))
    raise CompetitorCrossProjectError(
        competitor_id=str(competitor_id), project_id=str(project_id)
    )
```

`api/dao/competitor_dao.py` 加 `get_competitor_global` 方法（不带 tenant 过滤 / 仅 service 内部 NotFound vs CrossProject 区分用 / 不暴露给 router / docstring 明示）：

```python
async def get_competitor_global(self, db, competitor_id):
    """无 tenant 过滤的 id 全局查；仅供 service 层用来区分
    "竞品不存在 (404)" vs "竞品存在但跨项目 (422)"。"""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    return result.scalar_one_or_none()
```

---

## §2 Bug 2：CompetitorRefResponse 缺 display_name JOIN

### §2.1 现象

- 入口：`GET /api/projects/{pid}/nodes/{nid}/competitor-refs`
- 实测响应：items 仅含 `competitor_id` UUID，无 `display_name`
- 期望响应（design §7 + M06-competitor.spec.ts test 23）：每条 ref 含 `display_name`（JOIN 自 `competitors.display_name`）
- 受影响 spec：test 23 line 778 `[P1] GET /competitor-refs 返回含 display_name join 的 CompetitorRefResponse` — `expect(refItem?.display_name).toBe("JoinTest竞品")` FAIL

### §2.2 根因

三处漏链：
1. `api/schemas/competitor_schema.py` `CompetitorRefResponse` 字段表缺 `display_name`（design §7 字面声明该字段但 Phase 2.1 实装漏）
2. `api/dao/competitor_dao.py` `list_refs_by_node` / `get_ref_by_id` 单表 SELECT 无 JOIN / 无 `selectinload(competitor)`
3. `api/routers/competitor_router.py` `_ref_response` 用 `CompetitorRefResponse.model_validate(ref)` 自动从 ORM 属性映射 / ORM 关系字段未 eager-load 时 async lazy-load 会失败 / 没有显式装配 display_name

### §2.3 类似问题 grep

```bash
grep -n "model_validate.*from_attributes" api/routers/ | head
```

- M07 `IssueResponse` 三个 join 字段（`node_name` / `created_by_name` / `assigned_to_name`）走 `_JOINS = (selectinload(Issue.node), selectinload(Issue.created_by_user), selectinload(Issue.assigned_to_user))` + model 层 `lazy="raise"` 强制 eager-load — **是正确范式**
- M06 model 未用 `lazy="raise"` / DAO 未 selectinload / Phase 2.1 三处漏链同时发生 → 与 M07 范式不一致

### §2.4 design 哪步漏

- M06 design §7 L354-366 字面：
  ```
  class CompetitorRefResponse(BaseModel):
      ...
      display_name: str       # join 自 competitors.display_name
  ```
- §7 字面 contract OK / **没漏**
- §9 DAO 章节未明确"JOIN 装配走 selectinload(关系)"范式约束 → 实装方按"单表 select 带 project_id"通用范式做 → 漏 JOIN
- M07 sprint 后期才显式建立 `_JOINS` + `lazy="raise"` 范式（DAO L23-30 + model L91-92 / Phase 2.2 子片 5 D 类 #3 join 装配 / SR-CLEANUP-3）/ M06 sprint 在前未回流

### §2.5 修复

三处合并：

1. `api/schemas/competitor_schema.py` `CompetitorRefResponse` 加 `display_name: str` 字段。
2. `api/dao/competitor_dao.py`：
   - 引入 `_REF_JOINS = (selectinload(CompetitorRef.competitor),)`
   - `list_refs_by_node` / `get_ref_by_id` 加 `.options(*_REF_JOINS)`
3. `api/services/competitor_service.py` `create_ref` 路径 `db.refresh` 加上 `"competitor"` attribute → 让新建的内存对象也 eager-load relationship（避免 router `_ref_response` 触发 async lazy-load）
4. `api/routers/competitor_router.py` `_ref_response` 改成显式字段装配 + `display_name=ref.competitor.display_name`
5. `app/src/types/api.ts` 重新 codegen（OpenAPI → TS）/ `CompetitorRefResponse` 自动加 `display_name: string`

---

## §3 测试结果

### §3.1 pytest

```bash
cd /root/workspace/projects/prism-0420 && .venv/bin/python -m pytest tests/test_m06_*.py -v
```

- `tests/test_m06_routers.py`: 15/15 PASS
- `tests/test_m06_service.py`: 24/24 PASS
- `tests/test_m06_dao.py`: 18/18 PASS
- `tests/test_m06_models.py`: 8/8 PASS
- **合计：65/65 PASS**

注：`test_create_ref_cross_project_competitor_returns_422` 仍 PASS — 因为 fixture 在 projectA 建了真 competitor 再到 projectB 用 → competitor 全局存在但跨项目 → 走 CROSS_PROJECT 路径 正确。

### §3.2 playwright M06

```bash
pnpm exec playwright test e2e/dogfooding/M06-competitor.spec.ts
```

- 修前：21/24 PASS / 3 FAIL（test 12 + test 14 + test 23）
- 修后：23/24 PASS / 1 FAIL：
  - ✅ test 12 PASS（status 404 / code competitor_not_found）
  - ✅ test 23 PASS（refItem.display_name = "JoinTest竞品"）
  - ❌ test 14 残留 FAIL（`expect(body).toHaveProperty("error")` 失败 / 实测 flat `{code, message, details}`）
  
**残留 test 14 失败属于已立 OPEN bug `B-P2-M10-error-response-format-design-gap`**（design §13 模板字面 `{error:{code, message}}` 嵌套 vs middleware.py L18 实装 flat 全局错误响应格式 / 影响所有模块）。
该 bug 是横切 middleware 层改动 + 影响所有 pytest 断言 + 前端 parseError 已适配 flat 格式 → 任何修复都是跨模块大爆破 → 显然超 A 路径 单模块 范围 / 升 B 路径单独处理。本 cluster-1 不动。

### §3.3 regression M01/M02/M07

```bash
pnpm exec playwright test e2e/dogfooding/M01-user-account.spec.ts e2e/dogfooding/M02-project.spec.ts e2e/dogfooding/M07-issue.spec.ts
```

- **48/48 PASS** — 无回归。

### §3.4 tsc

```bash
cd app && pnpm exec tsc --noEmit
```

- 0 错（`display_name: string` 添加到 CompetitorRefResponse 是 additive / 不破坏现有 toCompetitorReference adapter）

---

## §4 改动清单

| 文件 | +/- | 说明 |
|------|------|------|
| `api/schemas/competitor_schema.py` | +1 | `CompetitorRefResponse` 加 `display_name: str` |
| `api/dao/competitor_dao.py` | +29/-2 | 加 `_REF_JOINS` selectinload tuple + 改 `list_refs_by_node` / `get_ref_by_id` 加 `.options(*_REF_JOINS)` + 加 `get_competitor_global` 新方法 |
| `api/services/competitor_service.py` | +9/-2 | `create_ref` 两步区分 NOT_FOUND vs CROSS_PROJECT + `db.refresh` 加 "competitor" attribute |
| `api/routers/competitor_router.py` | +15/-1 | `_ref_response` 改显式字段装配 / 含 `display_name=ref.competitor.display_name` |
| `app/src/types/api.ts` | +2 | OpenAPI → TS codegen 自动追加 display_name |
| **合计** | **+56/-7** | 净增 49 行 / 单模块（M06）/ 单 commit / 跨 4 个 backend 文件 + 1 个 frontend codegen 文件 |

---

## §5 已识别 follow-up（不阻塞 commit / 记录）

1. **B-P2-M10-error-response-format-design-gap 横切 audit**：design 模板 `{error:{code,message}}` 嵌套 vs middleware 实装 flat — 前端已适配 flat / 跨模块所有 pytest 断言 `body["code"]` — 修需大爆破 / 升 B 路径单独 sprint。test 14 残留 FAIL 归属此 bug。
2. **JOIN selectinload 范式统一**：M07 sprint 后期建立 `_JOINS` + `lazy="raise"` 范式 / M06 sprint 在前未回流。M01-M05 / M08+ 模块均需 audit 自身 read 路径是否依赖 ORM 关系 lazy-load — sweep 候选 → cross-sprint pool。
3. **NOT_FOUND vs CROSS_PROJECT 错误码分离 audit**：M07 ISSUE_NODE_CROSS_PROJECT 同款风险 / design §13 未明确分离 → 候选 design-audit。
4. **`get_competitor_global` 滥用风险防御**：DAO 引入"无 tenant 过滤"方法 / docstring 已明示"仅 service 层错误码区分用 / 不暴露 router"。任何 router 调该方法应视为 lint 红线 — 沉淀候选。
