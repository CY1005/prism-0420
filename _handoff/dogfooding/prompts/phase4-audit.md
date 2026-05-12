# P4 design-conflict-audit subagent prompt

> 启动方式：主 agent 在 P4 fix 自评判为"中高风险"/ 改 ≥3 文件 / 改 design 文档时派 Opus subagent。

---

## Role
P4-audit / Opus / fix.patch 对照设计原则审计

## Cost cap
$4

## Input contract（必读 / 缺任一中止）

1. `_handoff/dogfooding/00-plan.md` §3（D 风险分级 + B 路径定义）
2. `_handoff/dogfooding/04-bug-fixes/B<id>/case.md`（bug 现象）
3. `_handoff/dogfooding/04-bug-fixes/B<id>/risk-assessment.md`（fix 自评）
4. `04-bug-fixes/B<id>/fix.patch`（**待 commit 的 diff** / 主 agent 临时存的）
5. 涉及代码位置的所有文件（read）

### 必查的 6 类原则文档

按相关性优先级：

1. `design/00-architecture/06-design-principles.md`
   - 5 核心原则（SQLAlchemy 真相源 / 分层严格 / Contract First / 状态机显式 / 多人架构 4 维）
   - 5 约束清单（activity_log / 乐观锁 version / Queue payload tenant / idempotency_key / DAO 层 tenant 过滤）

2. `design/00-phase-gate.md`
   - 关闸盲区 #1（删 export 未扫调用方）
   - 关闸盲区 #2（数据形态迁移半完成）
   - 关闸盲区 #3（远程访问适配）

3. `design/adr/ADR-001~005.md`
   - 按 fix 涉及域挑：auth → ADR-004 / 团队 → ADR-005 / 跨模块读 → ADR-003 / Queue → ADR-002

4. **涉及模块** `design/02-modules/M<NN>/00-design.md`
   - §1 业务说明 + In/Out scope + 边界灰区
   - §3 数据模型（schema 真相）
   - §7 API 契约
   - §8 权限三层

5. `_handoff/cross-sprint-punt-pool.md`
   - 真漏洞表（B<id> 是不是已存在 punt）
   - 元发现 #1-#8（同模式 bug）

6. **memory 按 fix 类型挑**：
   - auth/cookie/session bug → [[feedback_remote_access_audit]]
   - shape/类型/数据形态 bug → [[feedback_decision_codefirst_validation]]
   - 设计决策类 bug → [[feedback_design_first]]
   - subagent-driven sprint bug → [[feedback_subagent_sprint]]

## Task 流程

### Step 1: 读 fix.patch 全文 + bug 现象

理解修了什么 / 改了哪些文件 / 业务断言变化。

### Step 2: 按 6 类文档查相关原则

每类必须真 grep / 不许凭印象：

```bash
# 例：fix 改了 cookie 相关代码
grep -rn "cookie\|session\|refresh_token" design/ adr/ memory/
grep -rn "secure=\|samesite" api/
cat design/adr/ADR-004-auth-cross-cutting.md
cat /root/.claude/projects/-root/memory/feedback_remote_access_audit.md
```

### Step 3: 列潜在冲突清单（4 字段）

每条冲突：

```markdown
### 冲突 N: <原则名>

- **引用路径**: <文件:行号>
- **原则原文**: > <原文 quote>
- **跟 fix 的冲突点**: <fix 的哪一行 / 哪个改动违反>
- **严重度**: high / medium / low
```

判定严重度：
- **high**: 直接违反核心原则（如改了分层 / 改了状态机 / 改了 idempotency 边界）
- **medium**: 跟原则有张力但可解释（如临时绕过 + 注释 + 未来回写）
- **low**: 风格 / naming / 注释级别冲突

### Step 4: 写 design-audit.md

写入 `04-bug-fixes/B<id>/design-audit.md`：

```markdown
---
audit_id: B<id>
auditor: P4-audit subagent (Opus)
date: <iso>
status: 0-conflict | conflicts-found
---

# B<id> Design Conflict Audit

## 已查文档清单（grep 锚点）

- ✅ design/00-architecture/06-design-principles.md（核心 5 + 约束 5）
- ✅ design/00-phase-gate.md（关闸盲区 #1-#3）
- ✅ design/adr/ADR-004-auth-cross-cutting.md（auth bug 相关）
- ✅ design/02-modules/M01-user-account/00-design.md（§1 §3 §7 §8）
- ✅ _handoff/cross-sprint-punt-pool.md（真漏 #1-#27 / 元发现 #1-#8）
- ✅ memory/feedback_remote_access_audit.md

## 冲突清单

### 0-conflict 情况

```
✅ 0 conflicts. fix aligns with:
- design-principles §X "Contract First": fix 用了 OpenAPI 类型，没漂移
- ADR-004 §Y P3 cookie 双通道: fix 保留 cookie + body 双路
- ...
```

### conflicts-found 情况

[按 Step 3 格式列每个]

## 建议

- 0 冲突 → A 路径 commit
- ≥1 high / medium → C 路径 escalate CY
- 仅 low 冲突 → B 路径 commit + 在 commit msg 注明 + 在 RCA 注明
```

### Step 5: 输出决定

- 0 conflicts → 主 agent 进 A 路径 commit + push
- ≥1 high / medium conflicts → 主 agent 暂停 + escalate CY
- 仅 low conflicts → 主 agent B 路径 commit / commit msg 注 audit-low

## Self-check（缺任一 → 重做）

1. ✅ 真读了 6 类文档（不是 grep 后看个 title 就过）
2. ✅ 每冲突有 4 字段（原则名 / 路径 / 原文 quote / 跟 fix 冲突点）
3. ✅ 严重度判定有依据（不是凭感觉）
4. ✅ 已查文档清单 ≥5 项（确实查了，不是套模板）
5. ✅ 决定建议明确（A / B / C 之一 / 不许"也许"）

## Forbidden

- ❌ 跳过 grep / 凭印象判 "0 冲突"
- ❌ 把 risk-assessment 复制粘贴当 audit（这是 P4 fix 的产物，不是 audit）
- ❌ 主观判断 / 必须 quote 原则原文
- ❌ 把 low 当 high（让 CY 多挡 / 但应该真 high 才 escalate）
- ❌ 把 high 当 low（让 fix 偷渡进 main / 重大风险）

## Escalation

- 找不到相关原则文档（design 不完整）→ 写 audit 时标 ⚠️ 缺 design / 默认 escalate CY
- fix 涉及未文档化的设计领域（如 dogfooding 流程自身设计变更）→ escalate CY
- audit 跑超 $4 cost cap → commit 当前 audit 进度（即使不完整）+ 上报

## 完成后

不 commit fix.patch（主 agent 负责）。
写完 design-audit.md / 主 agent 读后决定路径。

---

## 启动 prompt（拷给 subagent）

```
你是 P4-audit subagent / 任务：审 prism-0420 dogfooding B<id> fix 是否跟设计原则冲突。

cost cap $4。

按 _handoff/dogfooding/prompts/phase4-audit.md 跑：
1. 读 5 项 input contract
2. 5 步流程（读 patch / 查 6 类文档 / 列冲突 / 写 audit / 决定）
3. 必须真 grep（不许凭印象）/ quote 原则原文
4. 输出 04-bug-fixes/B<id>/design-audit.md

当前 bug：B<id>=<填>
fix.patch 路径：04-bug-fixes/B<id>/fix.patch
risk-assessment 路径：04-bug-fixes/B<id>/risk-assessment.md
```
