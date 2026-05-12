# P1 testpoint subagent prompt

> 启动方式：主 agent 在 prism-0420 根目录派 Opus subagent / 跑 1 个模块。

---

## Role
P1-testpoint / Opus / 单模块测试点生成

## Cost cap
$3（超即 commit 当前进度 + 退出 / 不无限跑）

## Input contract（必读 / 缺任一中止）

1. `_handoff/dogfooding/00-plan.md` 段 2 + 段 5（验收）
2. `design/02-modules/M<NN>/00-design.md`（当前模块完整 design / 重点：§1 业务说明 / §4 状态机 / §7 API 契约 / §8 权限 / §10 activity_log / §11 idempotency / §14 测试场景）
3. `design/00-architecture/01-PRD.md`（PRD F<NN> 验收条件 AC）
4. `design/00-architecture/06-design-principles.md`（5 核心 + 5 约束 / 推导风险点）
5. `/root/.claude/projects/-root/memory/feedback_testpoint_style.md`（**风格红线 2 条 / 不许违反**）
6. `/root/.claude/skills/requirements-to-testpoints/SKILL.md` §"15 角度框架" 段（用作视角清单）
7. **参考**：`design/02-modules/M<NN>/tests.md`（如有 / 已有测试场景 / 不重复但要覆盖）

## Output contract

写入 `_handoff/dogfooding/01-testpoints/M<NN>-<short-name>.md`：

```markdown
---
module: M<NN>
name: <short-name>
created: <iso>
generator: P1-testpoint subagent
references: design/02-modules/M<NN>/00-design.md
---

# M<NN> <模块中文名> 测试点

## 业务流程（H1 / 1 行概述）

## 测试点（H2 / 按 15 角度）

### 1. 功能性
- [P0] 创建项目 happy path 跳转项目详情页
- [P0] 创建项目失败 422 返业务码 + 错误展示
- [P1] 创建项目名称超长 200 字符边界

### 2. 边界 / 状态机
- [P0] active → archived 状态转换允许
- [P1] archived → active 状态转换禁止
- ...

### 3. 异常 / 错误
- [P0] 网络断连 retry 友好
- ...

### 4. 权限 / Auth
- ...

### 5. Tenant 隔离
- ...

### 6. 并发 / 乐观锁
- ...

### 7. 数据完整性
- ...

### 8. UI / UX
- ...

### 9. 性能（如适用）
- ...

### 10. 兼容性（如适用）
- ...

（11-15 按 15 角度框架，每模块按需挑用，不强求全 15 个）
```

## Self-check（缺任一 → 重做）

1. 行数 ≥10 testpoint（不含 H1 / H2 标题）
2. 每 testpoint **单行**：`- [P<0/1/2>] <testpoint 内容>` 不许换行 / 不许子项 / 不许"步骤"/ 不许"断言"/ 不许"业务影响"
3. 每模块至少含 §1 功能性 / §3 异常 / §4 权限（auth 模块特别覆盖）/ §5 tenant（任何带 project_id 的）
4. P0 测试点 ≥3（核心 happy path + 关键边界）
5. 引用 design 文档时显式引 §N 节号（如 "见 design §7 API 契约"）

## Forbidden（违反 → 重做）

- ❌ 子项 / 步骤 / 断言 / 业务影响（[[feedback_testpoint_style]] 红线）
- ❌ 凭印象写 testpoint / 必须基于 design 文档具体内容
- ❌ 跳过权限 / tenant 隔离视角（除非该模块明文 N/A）
- ❌ 跨模块测试点写在本模块（属于 `_cross-cutting.md`）

## Cross-cutting 视角（M01-M20 共用 / 单独 subagent 跑）

特殊：1 个跨模块 subagent 跑 `_cross-cutting.md`，按视角而非模块组织：
- auth flow（login / logout / cookie / refresh / session timeout）
- 跨 tab/window cookie sync
- 网络断连 / API 超时
- 权限三层防御（router / service / dao）
- 跨 module navigation（项目 → 节点 → 维度 → 问题 → 竞品）
- mobile / 响应式
- 国际化（如适用）
- 性能（首屏 / 大数据 / 长列表 / 翻页）

## Escalation

- 缺 design 文档 / 找不到 M<NN>/00-design.md → 中止上报主 agent
- design 内部矛盾（§3 SQLAlchemy 跟 §7 API 不一致）→ 在 testpoint 文件顶部写 "⚠️ design 内部不一致 / 已记 design-audit candidates" 段，继续跑
- testpoint 数 ≥100（auth pilot 级 / 真的异常多）→ commit 当前进度 + 拆 P0/P1 优先级 + 报告（不阻塞主 agent / 仅 surface）
- testpoint 数 <10（覆盖不足）→ 重做 / self-check 第 1 项

## 完成后

不 commit（主 agent 收集全 21 个 module testpoint 后一次性 commit `dogfooding P1 testpoints`）。

更新主 agent 跟踪表：
```
M<NN>: ✅ DONE / N testpoints / cost $X
```

---

## 启动 prompt（拷给 subagent）

```
你是 P1-testpoint subagent / 任务：为 prism-0420 模块 M<NN> 生成测试点。

cost cap $3。

按 _handoff/dogfooding/prompts/phase1-testpoint.md 跑：
1. 读 7 项 input contract
2. 按 15 角度框架挑用
3. 写 _handoff/dogfooding/01-testpoints/M<NN>-<short>.md
4. self-check 5 项
5. 不许子项 / 步骤 / 断言（[[feedback_testpoint_style]] 红线）
6. 完成不 commit / 返主 agent

当前模块：M<NN>=<填> / short-name=<填>
```
