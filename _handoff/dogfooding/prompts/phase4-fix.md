# P4 fix subagent prompt

> 启动方式：主 agent 从 `03-bug-queue.md` 取 1 个 OPEN bug / 派 Opus subagent / 修一个。

---

## Role
P4-fix / Opus / 单 bug 修复 + 风险自评

## Cost cap
$5（单 bug / 含修代码 + 验证 / 不含 audit + rca）

## Input contract（必读 / 缺任一中止）

1. `_handoff/dogfooding/00-plan.md` §3（D 风险分级 + 3 路径决策）
2. `_handoff/dogfooding/03-bug-queue.md` 中**当前 OPEN bug** 一条
3. `_handoff/dogfooding/04-bug-fixes/B<id>/case.md`（原始失败 case / playwright spec 引用）
4. 相关 module design `design/02-modules/M<NN>/00-design.md`
5. 相关 ADR（按 bug 类型挑 / 如 auth bug 必读 ADR-004）
6. memory（按 bug 类型挑）：
   - auth/cookie bug → [[feedback_remote_access_audit]]
   - shape/类型 bug → punt pool 元发现 #6
   - design 决策类 bug → [[feedback_decision_codefirst_validation]]
7. 当前代码（按 case.md 提示找受影响文件）

## Task 流程

### Step 1: 复现 bug（必须 / 不许跳）

按 case.md 描述跑 fail 的 spec：
```bash
cd app && pnpm playwright test e2e/dogfooding/M<NN>-<test>.spec.ts:<line> --headed=false
```

确认 fail 信号跟 case.md 一致。如果跑过了 → 报主 agent "bug 不复现 / 可能 flaky / 改进 case 或 skip"。

### Step 2: fact-finding（按 [[feedback_decision_codefirst_validation]] 3 步）

1. 读 design 文档相关段
2. grep 真实代码定位 bug
3. 列 hypothesis + 反验

不许跳步 / 不许凭印象。

### Step 3: 风险自评（6 项）

写到 `04-bug-fixes/B<id>/risk-assessment.md`：

```markdown
# B<id> 风险评估

1. **改动范围**: <预估 N 文件 / M 行> → [低 / 高]
2. **代码位置**: <path> → [低 / 高]（UI 文案/类型=低 / backend service/dao/auth=高）
3. **可逆性**: <分析 git revert 安全度> → [低 / 高]
4. **业务断言**: <yes / no> → [低 / 高]（改状态机/权限/事务=高）
5. **测试覆盖**: <existing test 全绿 / 需新建> → [低 / 高]
6. **bug 类型**: <type / typo / shape / race / auth bypass / ...> → [低 / 高]

判定: <全低 = A 路径直推 main / 任一高 = B 路径 audit / 不确定 = C 路径 escalate>
```

### Step 4: 实际修代码

按 fact-finding 结论写最小修。**禁止扩范围 refactor**（不在 [[feedback_session_focus]] 主任务内）。

### Step 5: 验证修复

```bash
# 跑 fail case 必 PASS
cd app && pnpm playwright test e2e/dogfooding/M<NN>-<test>.spec.ts:<line>

# tsc 必 0 错
pnpm exec tsc --noEmit

# 相关 unit test 必 PASS
cd .. && uv run pytest tests/test_m<NN>_*.py --benchmark-disable -p no:warnings -q
```

任一失败 → 改回去 / 重做 Step 4 / 不许"差不多就提交"。

### Step 6: 决定 commit 路径

按 risk-assessment 判定：

- **A 路径**（全 6 低）：直接 commit + push 到 main（用 §3 commit 模板）
- **B 路径**（任一高 / 改 ≥3 文件 / 改 design）：**不 commit / 派 P4 audit subagent / 等 audit 结果**
- **C 路径**（不确定 / [AMBIGUOUS]）：commit 到新分支 `bug-fix/B<id>` + push + 写 `04-bug-fixes/B<id>/escalation.md` / 主 agent 通知 CY

## Output contract

```
04-bug-fixes/B<id>/
├── case.md                    # 已有 / 不动
├── risk-assessment.md         # 新建（Step 3 输出）
├── fix.patch                  # `git diff main HEAD` 输出（A/B 路径 commit 后 / C 路径暂存）
└── escalation.md              # 仅 C 路径
```

## Self-check（缺任一 → 重做）

1. ✅ bug 复现成功 / 不是 flaky
2. ✅ 3 步 fact-finding 真做了（grep / 读 design / hypothesis 反验）
3. ✅ 修复后 fail case PASS
4. ✅ tsc 0 错
5. ✅ 相关 unit test PASS
6. ✅ 风险自评 6 项全填（不许"差不多"）
7. ✅ commit 路径符合判定（A/B/C）

## Forbidden

- ❌ 扩范围 refactor（"顺手修这个看着不顺眼的"）
- ❌ 跳 fact-finding 直接改（[[feedback_decision_codefirst_validation]] 红线）
- ❌ A 路径但其实改了 backend service 业务逻辑（必须重评 → B）
- ❌ 不跑验证就 commit
- ❌ commit message 不引 RCA / 不引 risk-assessment

## Escalation

- bug 不复现 / flaky → 写到 case.md + 主 agent 决定 skip / 入 punt pool
- 修了 2 次都不行 → C 路径 escalate / 不许第三次硬试
- 修复需要改 design 文档 / migration → B 路径必触发 audit
- 修复跨 ≥3 文件 → 强制 B 路径（不论自评结果）

## 完成后

A 路径：
- commit + push（commit msg 按 §3 模板）
- 主 agent 跑 `gh run watch` 等 CI 全绿
- CI 红 → 立即 revert + 升 C 路径

B 路径：
- 不 commit / 派 P4 audit subagent
- audit 0 冲突 → 同 A 路径 commit + push
- audit ≥1 冲突 → 升 C 路径

C 路径：
- 分支 commit + push / 写 escalation.md / 主 agent 通知 CY

更新 `03-bug-queue.md`：
```
| B<id> | <现象> | OPEN → FIX_IN_PROGRESS → FIX_DONE → REGRESSION_PASS |
```

派 P4 rca subagent（不论路径，rca 都跑）。

---

## 启动 prompt（拷给 subagent）

```
你是 P4-fix subagent / 任务：修 prism-0420 dogfooding sprint 的 1 个 bug。

cost cap $5。

按 _handoff/dogfooding/prompts/phase4-fix.md 跑：
1. 读 7 项 input contract
2. 6 步流程（复现 / fact-finding / 风险自评 / 修代码 / 验证 / 决定路径）
3. 严守 [[feedback_decision_codefirst_validation]] fact-finding 3 步
4. 严守 [[feedback_session_focus]] 不扩范围
5. 路径决策按 00-plan §3

当前 bug：B<id>=<填> / 03-bug-queue.md 第 N 行 / case.md 路径 04-bug-fixes/B<id>/case.md
```
