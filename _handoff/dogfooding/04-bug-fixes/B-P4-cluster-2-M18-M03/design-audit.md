---
title: B-P4-cluster-2 design audit (B 路径 / M03 DELETE)
sprint: dogfooding
cluster: P4-cluster-2-M18-M03
date: 2026-05-13
trigger: 第三 bug B-P2-M03-project-delete-endpoint-missing 触发新 endpoint + CASCADE 设计 → B 路径必跑 audit
status: HIGH conflict（需 CY 决策 sync code / sync design）
---

# B 路径 design audit — M03 project DELETE endpoint 实装

## audit 范围

- ADR-001 / ADR-005（团队扩展含 projects.team_id FK 段）
- M02 §1 / §4 / §13 design（项目模块字面规约）
- M03 §7 design（nodes FK CASCADE 段）
- 06-design-principles（5 条核心 + 5 条多人架构约束）

## audit 结果总览

| # | 冲突源 | 冲突描述 | 严重度 | 建议处理 |
|---|--------|---------|--------|---------|
| 1 | M02 §1 line 117 | "本设计采用归档（active → archived）软删除语义，**不物理删除**——归档为不可逆终态（G2 决策：归档=软删除不可逆）。物理删除涉及级联所有子模块数据，风险过高。" | **HIGH** | 上报 CY |
| 2 | M02 §4 line 503 | 禁止转换表："任何状态 → 物理删除 \| 本期不支持物理删除，保留软删除语义；抛 `PROJECT_DELETE_NOT_SUPPORTED`（422）" | **HIGH** | 上报 CY |
| 3 | M02 §4 line 479 / Mermaid 状态机 | `archived --> [*] : 归档为不可逆终态（本期不支持恢复和物理删除）` | **HIGH** | 上报 CY |
| 4 | M02 §13 line 822 / line 852 | ErrorCode `PROJECT_DELETE_NOT_SUPPORTED = "project_delete_not_supported"` 已注册到 ErrorCode 枚举 + `ProjectDeleteNotSupportedError(AppError) http_status=422` exception 类已定义但**全仓 0 引用**（grep 仅出现在 codes.py + exceptions.py 定义本身） | **MEDIUM** | 与 #1-3 一并决策 |
| 5 | ADR-005 全文 | ADR-005 仅决策 teams 表 + projects.team_id FK ondelete=RESTRICT（"删 team 前 project 必须先解绑"），**完全不涉及**"archived → delete project"流程。P4 prompt 写"走 ADR-005 archived → delete + CASCADE 验证"是错误引用——ADR-005 不存在该决策。 | **MEDIUM** | prompt 修订 / ADR 不变 |
| 6 | ADR-001 全文 | 不涉及 project 物理删除 | 无 | — |
| 7 | 06-design-principles | 不涉及 project 物理删除 | 无 | — |
| 8 | M03 §7 line 252 | "`nodes.parent_id` ON DELETE CASCADE：级联删除子树（DB 层面兜底）" + line 333 `_child_services` 注册表跨模块 R-X2 段 → **node CASCADE 已设计**，project→node CASCADE 是 DB FK 副作用而非 design 显式决策 | 无 | — |
| 9 | E2E spec | `M03-module-tree.spec.ts:623-677` `[P0] nodes.project_id ON DELETE CASCADE` test：if (status===405) log bug + 验 node 仍 200；else if ([200,204]) 验 cascade（getNode 返 404/403）；**else expect([200,204,405]).toContain(status)** → 422 路径 spec FAIL | **HIGH** | 与 #1-3 一并决策（若选 sync code 也需同步改 spec） |

## 冲突详情（HIGH）

### 冲突 #1-3: design §1 / §4 line 117 / 503 / 479 字面禁物理删除

```text
M02 design §1 line 117:
- **项目删除 vs 归档**：本设计采用归档（active → archived）软删除语义，不物理删除——
  **归档为不可逆终态**（G2 决策：归档=软删除不可逆）。物理删除涉及级联所有子模块数据，风险过高。

M02 design §4 line 501-503:
| 禁止操作 | 原因 + ErrorCode |
|----------|------------------|
| `archived → active`（归档恢复）| 归档为不可逆终态... `PROJECT_ALREADY_ARCHIVED`（409）|
| `archived → archived`（重复归档）| 已是终态... `PROJECT_ALREADY_ARCHIVED`（409）|
| 任何状态 → 物理删除 | 本期不支持物理删除，保留软删除语义；抛 `PROJECT_DELETE_NOT_SUPPORTED`（422） |

M02 design §4 line 479 (Mermaid):
archived --> [*] : 归档为不可逆终态（本期不支持恢复和物理删除）
```

**与本次 fix 的冲突**：fix 在 `api/routers/project_router.py` 注册 `DELETE /api/projects/{project_id}` 返 204（真物理删除），且 `api/services/project_service.py` 新增 `delete_project` 调 `delete_one` 触发 FK CASCADE 删 17 个子表（详 ADR-005 §3.2 横切表清单）。**此行为字面违反 design §1/§4/§13**。

### 冲突 #4 (MEDIUM): ErrorCode/Exception 已注册但 0 引用

```text
api/errors/codes.py:44      PROJECT_DELETE_NOT_SUPPORTED = "project_delete_not_supported"
api/errors/exceptions.py:180-183:
    class ProjectDeleteNotSupportedError(AppError):
        code = ErrorCode.PROJECT_DELETE_NOT_SUPPORTED
        http_status = 422
        message = "Physical project deletion is not supported; use archive instead"
```

全仓 grep：除定义本身外 0 引用——是 design 已注册"拒绝路径"但实装从未触发的"半实装"。R13-1 parity check 应该会捕获（"design ErrorCode vs 实装引用是否对齐"）。

## P4 prompt 与 ADR-005 不一致（MEDIUM）

P4 prompt 字面：
> 修法：注册 DELETE / 调 service.delete_project / **走 ADR-005 archived → delete + CASCADE 验证**

ADR-005 全文 grep `archived` / `delete project` / `物理删除` 均**无匹配**。ADR-005 §3.1 M02 baseline-patch 段仅讲 `projects.team_id` 字段重命名 + FK ondelete=RESTRICT（teams→projects 方向，不是 projects→子表方向）。

**结论**：P4 prompt 的 "ADR-005 archived → delete" 是错误引用——该决策不存在。这是 dogfooding 价值发现的 **prompt 层概念漂移**（CY/Claude 在写 P4 prompt 时把"软删除终态"和"硬删除 cascade"两种语义混淆，误以为 ADR-005 涵盖后者）。

## 决策选项（上报 CY）

### 方案 A: sync code（保 design 字面）

1. 修 `api/services/project_service.py` `delete_project` → 改为 `raise ProjectDeleteNotSupportedError()`（不真删，返 422）
2. 修 `api/routers/project_router.py` DELETE endpoint 返 422 `PROJECT_DELETE_NOT_SUPPORTED`
3. 删 `api/dao/project_dao.py` `delete_one`（或保留 noop / 改为内部归档辅助）
4. **修 E2E spec `M03-module-tree.spec.ts:673-676`** else 分支 `expect([200, 204, 405, 422]).toContain(status)` 加 422，CASCADE 验证调整为"archive 后再验"
5. 更新 03-bug-queue.md 标 FIX_DONE_AS_REJECTED 而非真删

**得失**：保持 design 一致性（G2 决策不破），但 fix 价值降低（用户仍无法物理删除项目，需走 archive 终态）；spec 必须修一行（破 prompt "❌ 不修 spec" 红线）。

### 方案 B: sync design（保 code 真删 cascade）

1. 修 M02 §1 line 117 删"不物理删除"段，改为"支持物理删除 + 归档（archive 是软删除可选过渡态）"
2. 修 M02 §4 line 503 删"任何状态 → 物理删除" 禁止转换条目
3. 修 M02 §4 line 479 Mermaid `archived --> [*]` 改为"archived → deleted 或保留"
4. 修 M02 §13 + codes.py + exceptions.py 删 `PROJECT_DELETE_NOT_SUPPORTED`
5. 新增 ADR 或扩 ADR-005 §3 / 写 ADR-007"项目物理删除 + 17 表 CASCADE"决策
6. M03 §7 / M15 §10 加 `project_deleted` ActionType + activity_log 字面记录
7. cross-module review M03/M04/M06/M07/M08/M10/M12/M13/M14/M15/M16/M17/M19 的 CASCADE / FK / 兜底验证（M20 排除 / team 路径不变）

**得失**：fix 立刻生效不再有 design 漂移，但 design 修订涉及 7-13 个文件 + 1 ADR 新决策 + 跨模块 cascade 复查，工作量重；G2 决策（归档=软删除不可逆）需要正式 supersede。

### 方案 C: 双路径并存

1. 保 archive 终态（design §4 不动）
2. 新增 ADR-007 "project 物理删除（已 archived 项目可二次删除）"
3. 修 service.delete_project：只允许 `status == 'archived'` 的 project 物理删，否则 422 `PROJECT_DELETE_NOT_SUPPORTED_FROM_ACTIVE` 引导先 archive
4. 修 spec 走"archive → delete → 验 cascade"两步路径

**得失**：保留软删除语义 + 提供物理清理路径，符合"先 archive 后定期清理"工业惯例；需新 ErrorCode + ADR-007 + spec 改一行；与现有 design G2 不冲突（archived 是中间态而非终态，G2 决策"终态"语义弱化）。

## 推荐

倾向 **方案 C**（archived → delete 两步路径）——符合 P4 prompt 隐含意图（"走 archived → delete + CASCADE"字面虽错引 ADR-005 但思路对），生产环境常见（GitLab/Linear/Notion 等都是软删除 → 30 天后物理清理），同时保留 design G2 "archived = 中间不可逆态"精神（弱化"终态"为"待清理终态"）。

## 自验本 audit 范围足够

- ✅ ADR-001 + ADR-005（全部 ADR / 不含 002/003/004/006，因后者均与"删除"无关）
- ✅ M02 §1 §4 §13（design 三处字面声明）
- ✅ M03 §7 nodes FK CASCADE 段（确认子表级 CASCADE 已设计 / project→子表是 DB 副作用）
- ✅ 06-design-principles 全文（多人架构 4 维 / 5 条核心 / 无关物理删除）
- ✅ E2E spec dogfooding 行为期望
- ✅ ErrorCode / Exception 注册表 vs 实装引用 grep
- ✅ 全仓 grep "archived.*delete" / "物理删除" / "hard delete"
