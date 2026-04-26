---
title: prism-0420 阶段闸门规则
status: accepted
owner: CY
created: 2026-04-26
---

# Phase Gate 阶段闸门

> 防"跳过工程地基直接写业务代码"的硬规则。配合 [`00-roadmap.md`](./00-roadmap.md) 当前位置查询使用。

---

## 闸门 1：Phase 1 → Phase 2.0

**进入 Phase 2.0 工程基线无前置（Phase 1 已完成 = 进入许可证）**。

---

## 闸门 2：Phase 2.0 → Phase 2.1（关键闸门）

写**任何业务模块代码**之前必须**全部 ✅**：

### 2.1 决策类（A 阶段）

- [ ] `02-quality-spec.md` accepted（测试框架 + Lint + Formatter 全决）
- [ ] `engineering-spec.md` §13 accepted（Code review 流程）

### 2.2 代码类（B 阶段）

本地命令必须能跑通：
- [ ] `make dev`（启动 FastAPI + Next.js + PG + Redis）
- [ ] `make test`（pytest + vitest 跑空 test 通过，fixtures 工作）
- [ ] `make migrate`（Alembic upgrade head 不报错）

横切 helper 必须有可调用 + 单元测试：
- [ ] `api/errors/`（AppError + ErrorCode + middleware）
- [ ] `api/auth/`（require_user + JWT + P2 internal token）
- [ ] `api/services/activity_log_service.py`（write_event 单方法）
- [ ] `api/auth/tenant_filter.py`（user_accessible_project_ids_subquery）

---

## 闸门 3：Phase 2.1 启动 → M02-M20

写**第二个业务模块**前必须 ✅：
- [ ] M01 用户系统 PR merge（探针验证整套流程跑得通）
- [ ] M01 tests.md critical path 100% PASS
- [ ] simplify-checklist 三 Agent 流水线在 M01 PR 上实际跑过一次

---

## 闸门 4：后端 → 前端继承

启动 **Phase 2.2 前端继承 Prism** 之前：
- [ ] M01-M05 + M20 后端代码 merge（OpenAPI 契约稳定）
- [ ] `npm run codegen` 能从后端 OpenAPI 生成 TS 类型
- [ ] 前端 api-client 至少 1 个真实 endpoint 调通（不是 mock）

---

## 闸门 5：上线前

启动 **Phase 2.3 集成验证 → 上线** 之前：
- [ ] 后端 20 模块全 PR merge
- [ ] 前端继承 Prism + M20 新增页面 PR merge
- [ ] CI 全跑通（lint + test + build + migrate）

---

## AI 行为约束（防再跳）

**AI 准备做以下任一动作前**，**必须读 `00-roadmap.md` 当前 phase + 检查对应闸门**：
1. 生成「实现提示词」/「Phase N 启动包」
2. 写业务模块代码（M01-M20 任一）
3. 写 PR 计划 / 拆批策略
4. 给 CY 推荐"下一步做什么"

**自检 3 问**（任一 No → 不许出业务内容）：
1. 上一阶段所有 checkbox 都 ✅ 了吗？
2. 闸门所列文件/命令是否都存在/能跑？（用 ls / grep / Bash 验，不凭印象）
3. roadmap.md `last_updated` 是否反映真实进度？

任一 No → 告诉 CY「你在阶段 X，下一步是 Y（具体闸门项），先补完才能 Z」。

---

## CY 自我约束

CY 自己也可绕（这是你的项目你说了算）。但每次想绕时建议：
1. 写一句"为什么这次必须绕闸门 X" 到 `design/99-comparison/phase-gate-bypass-log.md`
2. 累计绕 ≥ 2 次 → 触发对闸门规则本身的 review（是不是闸门定错了）

---

## 维护

- 闸门规则不变 → 不更新本文件
- 闸门项需调整（如新增工程地基要求）→ AI 修订并标注变更原因
- 与 `00-roadmap.md` 不一致时 → 以本文件为准（闸门是真相，roadmap 是状态镜像）
