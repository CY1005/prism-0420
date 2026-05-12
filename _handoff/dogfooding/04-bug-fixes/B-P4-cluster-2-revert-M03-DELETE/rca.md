---
title: B-P4-cluster-2-revert RCA — M03 DELETE 改 422 跟 design G2 一致
sprint: dogfooding
cluster: P4-cluster-2-revert
date: 2026-05-13
parent_commit: 0992dc8 (P4-cluster-2 错装物理删除)
revert_commit: <TBD>
status: VERIFIED
risk: low (A 路径 / 修法跟 design 真相一致 / 用 design 已留位 ErrorCode + Exception)
---

## 1. 现象

`cluster-2` commit `0992dc8` 错误实装了 `DELETE /api/projects/{pid}` 物理删除 endpoint：

- `api/dao/project_dao.py` 新增 `ProjectDAO.delete_one()` 调 SQL `DELETE FROM projects WHERE id=...`
- `api/services/project_service.py` `delete_project()` 写 `project_deleted` activity_log + 调 `dao.delete_one` 物理删
- `api/routers/project_router.py` `@router.delete("/{project_id}", status_code=204)` endpoint

但 design M02 §1 / §4 / §13 字面声明：归档=软删除不可逆 / **不物理删除** / 任何状态 → 物理删除应抛 `PROJECT_DELETE_NOT_SUPPORTED`(422)，且 ErrorCode `PROJECT_DELETE_NOT_SUPPORTED` + `ProjectDeleteNotSupportedError(http_status=422)` **已在 design §13 注册等实装** 30+ commit 无 caller。

cluster-2 引入物理删除路径 = G2 业务决策违反 / 生产风险窗口（main 上有 endpoint 能真把项目+17 子表 CASCADE 一并物理删除）。

## 2. 根因

### 2.1 prompt 凭印象引 ADR-005（虚假来源）

P4-cluster-2 prompt 写「走 ADR-005 archived → delete + CASCADE 验证」—— 但 **ADR-005 全文不涉及 project 物理删除**（ADR-005 只决策 teams 表 + projects.team_id FK ondelete=RESTRICT）。这是 prompt 作者凭印象引虚假来源 / subagent 没 fact-finding 就照做。

### 2.2 bug-queue 描述「未实现」误导

`03-bug-queue.md` `B-P2-M03-project-delete-endpoint-missing` 描述为「DELETE endpoint 返 405 / 未实现」—— 但**真相是「endpoint 是按 design G2 故意不实装 / ErrorCode 已留位等实装为 422 endpoint」**。「未实现」语义模糊：是「漏写 endpoint」还是「design 故意不实装」？bug-queue 没标注，subagent 走「漏写 = 补实装真物理删除」错路。

### 2.3 design-audit 流程跑过但选错路径

cluster-2 的 `design-audit.md` **实际识别出**了 4 个 HIGH 冲突（§1 L117 / §4 L503 / §4 L479 Mermaid / E2E spec 三分支）+ 1 个 MEDIUM（ErrorCode 已留位 0 引用）—— audit 流程并未失效，但 cluster-2 选择「sync design」反向：保留物理删除代码 / 上报 CY 决策。这违反了 design G2 是 **CY 已落锤业务决策**（G2 = CY 的归档不可逆设计 / 不是工程实施细节）的边界 —— subagent 不应"上报 CY 决策 sync code 还是 sync design"，而应该**立即停止 + BLOCK 上报 prompt 引导错误**。

### 2.4 没 fact-finding design 真相 & ErrorCode 留位

按 `feedback_decision_codefirst_validation` §2 (2026-05-12 新规约)：决策类推荐前必先 fact-finding 3 步（读 design 文档 + grep 真实代码 + hypothesis 反验）。cluster-2 subagent 没在 implementation 前跑 Step 0 grep `PROJECT_DELETE_NOT_SUPPORTED` —— 若跑了 / 就会立即发现 ErrorCode + Exception 已留位 / 真相是「补齐留位 422 endpoint」而非「实装物理删除」。

## 3. 类似问题 grep（同款翻车）

dogfooding sprint 同期 3 次相同根因（详 `feedback_decision_codefirst_validation` §2 2026-05-12 实证段）：

1. **2026-05-12 翻车 #1**：Phase 2.3 cleanup C sprint 决策类推荐跳 design + 真实代码 fact-finding → 工作量偏差 5-10 倍 / 推荐反向
2. **2026-05-13 翻车 #2**：本 cluster-2 commit 0992dc8 凭印象 ADR-005 + bug-queue 「未实现」误导 → 实装违反 G2 物理删除
3. **2026-05-13 翻车 #3**：（如未来发现 cluster-3+ 同款再补）

模式：subagent prompt 凭印象引文档（ADR / design / bug-queue 描述）作为「依据」/ subagent 不交叉验证 / 直接按 prompt 字面做。

## 4. design 哪步漏 / 流程缺口

### 4.1 design 已留位 ErrorCode 长期未实装无追踪

`ProjectDeleteNotSupportedError` + `PROJECT_DELETE_NOT_SUPPORTED` 在 `api/errors/codes.py:44` + `api/errors/exceptions.py:180-181` 已注册等实装 / 30+ commit 没 caller / 没 punt-pool 登记 → 后来 subagent 看「DELETE 返 405」就以为是漏 endpoint / 而非「漏 caller / endpoint 应返 422」。

**沉淀动作**：本 fix 已补 endpoint + caller。其他可能存在的"已留位但 0 引用"ErrorCode 需扫一遍 punt pool。

### 4.2 cluster-2 prompt 没引导 subagent 用留位 ErrorCode

cluster-2 prompt 描述「补 endpoint + cascade」时没说「先 grep 已留位 ErrorCode」/ subagent 默认理解「补实装真功能」/ 而非「补齐 422 拒绝 endpoint」。

**沉淀动作**：subagent prompt 写作规约更新（feedback_decision_codefirst_validation §2）：
- 涉及「补 endpoint / 实装新功能」类 prompt 必须先 Step 0 强制 grep 已留位 ErrorCode/Exception
- bug-queue 「未实现」描述必须明确「漏写 endpoint」vs「design 故意不实装」语义边界

### 4.3 bug-queue 「未实现」描述歧义

`03-bug-queue.md` `B-P2-M03-project-delete-endpoint-missing` 描述「DELETE /api/projects/{id} 返 405 / 端点未实现」—— 没标注「design G2 故意不实装 / ErrorCode `PROJECT_DELETE_NOT_SUPPORTED` 已等实装 422 endpoint」。

**沉淀动作**：bug-queue 描述规约：未实现/缺失类 bug 必须标注「期望行为来源」+「相关 ErrorCode/Exception 是否已留位」。

## 5. 修法

A 路径修法 6 项自评全低：
- 改动范围：低（删 dao 1 段 / service 改 1 段 / router 改 1 段）
- 代码位置：中（service / router 改契约）
- 可逆性：低（git revert 安全 / 不动 schema / 不动 design / 不动 ErrorCode）
- 业务断言：低（修法是跟 design 真相一致 / 不动 G2 决策）
- 测试覆盖：高（pytest 2 test + E2E spec 1 test 已写 / 全 PASS）
- bug 类型：低（修法是补齐留位 ErrorCode 实装 / 不是新功能）

### 5.1 dao 层 — 删 `ProjectDAO.delete_one()`

cluster-2 加的 `ProjectDAO.delete_one()` 整段移除。`sqlalchemy.delete` import 保留（`ProjectMemberDAO.delete` + `ProjectDimensionConfigDAO.delete_one` 仍在用）。

### 5.2 service 层 — `delete_project()` raise 422

```python
async def delete_project(
    self, db: AsyncSession, *, project_id: UUID, actor_user_id: UUID
) -> None:
    """物理删除拒绝 (design M02 §1 L117 + §4 L503 + §13 G2 决策)."""
    await self.require_owner(db, project_id, actor_user_id)
    raise ProjectDeleteNotSupportedError(project_id=str(project_id))
```

权限顺序：先 `require_owner`（与 archive/update 对齐）/ 非 owner 由 router 层 `check_project_access(role=owner)` 已拦 403 / service raise 仅 owner 路径触发。

新增 import：`api.errors.exceptions.ProjectDeleteNotSupportedError`（design §13 已注册）。

### 5.3 router 层 — endpoint 保留但去 204

```python
@router.delete("/{project_id}")
async def delete_project(
    access: ProjectAccess = Depends(check_project_access(role="owner")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = ProjectService()
    await svc.delete_project(db, project_id=access.project.id, actor_user_id=access.user.id)
    return Response()  # unreachable / middleware 422
```

endpoint 保留是为了 OpenAPI 显式声明 422 契约（而非 405）/ 前端 codegen 能看到拒绝语义。去掉 `status_code=204` 让 ProjectDeleteNotSupportedError raise 时走 middleware 渲染 422 `{"code": "project_delete_not_supported"}`。

### 5.4 测试

**pytest** `tests/test_m02_routers.py` 加 2 个 test：
- `test_delete_project_returns_422_project_delete_not_supported` — owner 调 DELETE 返 422 + 项目仍 active
- `test_delete_project_non_owner_returns_403` — viewer 调 DELETE 返 403（防御深度）

**E2E spec** `app/e2e/dogfooding/M03-module-tree.spec.ts:623` —— 改前三分支 (if-405 / if-200-204 / else expect[200,204,405]) → 改后单分支期望 422 PROJECT_DELETE_NOT_SUPPORTED + 验项目仍存在 + 子节点仍存在。

## 6. 验证结果

- pytest M02+M03 routers/service/dao：78 PASS / 0 FAIL
- TypeScript tsc --noEmit：0 错
- Playwright M03 spec 31 PASS（原 32 / 改后单分支收成 31）
- Playwright M01 regression 5 PASS / M02 regression 5 PASS
- Backend 重启验证：uvicorn pid 42185 / health OK

## 7. 沉淀清单

1. `feedback_decision_codefirst_validation` §2 加 2026-05-13 新条目：subagent prompt 写作场景规约 + Step 0 fact-finding 强制段 + bug-queue 描述规约
2. `03-bug-queue.md` `B-P2-M03-project-delete-endpoint-missing` 状态从 FIX_DONE → VERIFIED（cluster-2 错实装 / cluster-2-revert 改回 422 跟 design G2 一致）
3. `_handoff/dogfooding/04-bug-fixes/B-P4-cluster-2-M18-M03/design-audit.md` 已不重写（历史留痕 cluster-2 错决策）/ 本 fix 三件套并列 / 标 superseded
