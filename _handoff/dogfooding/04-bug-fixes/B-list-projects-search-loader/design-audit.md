---
fix: B-list-projects-search-loader
audit_path: A
conflicts: 0
created: 2026-05-12
---

# design-audit — B-list-projects-search-loader

## 结论

**A 路径 / 0 冲突**。

dogfooding 6 项自评（rca.md §5.1）预判 1-2 项中 / 0 项高 → A 路径直推。同模式扫描（rca.md §3）src/ 全 codebase 仅 1 处命中 `'use server'` 文件中的危险 `export type { X }` 模式 / 已 1 行删除修复 / 无其他文件改动 / 不需要 audit subagent。

## 不需 audit 的依据

| 维度 | 实证 |
|------|------|
| design ADR 冲突 | 0 — fix 不改 ADR-001/004/005/006 任一决策 / 不动 auth / 不动 cookie path / 不动权限三层 |
| 业务逻辑冲突 | 0 — globalSearch 函数签名 `(query, options?) => Promise<ActionResult<SearchResponse>>` 完全不变 / 仅删除 dead type re-export |
| 消费方契约 | 0 — `src/components/global-search-bar.tsx` + `src/app/projects/[projectId]/search/page.tsx` 均通过 await 推断返回类型 / 不依赖显式 `import type { SearchResponse }` / tsc 0 错验证 |
| 框架兼容 | 0 — Next.js 16.2.4 server actions 官方契约（action-validate.js）即 "`'use server'` 文件只能 export async function" / 删除类型再导出**反而**让代码更贴近官方契约 |
| 同模式扩散 | 0 — rca.md §3.1 全 codebase grep 仅 search.ts 命中 `'use server'` + `export type { X }` 组合 / 另 2 处 `'use client'` 文件不走 server-actions 转换 / 安全 |
| Phase 2.3 cleanup C 翻车镜像（[[feedback_decision_codefirst_validation]]）| 0 — 本 fix 推荐前已做 fact-finding 3 步：(a) 读 search.ts 真实代码 + next-dev log + Next.js docs / (b) grep 全 codebase 同模式 / (c) hypothesis 反验 — 验证 SearchResponse 在 codebase 无外部消费者 / 删除安全 |

## A 路径合理性最终验证

`_handoff/dogfooding/00-plan.md` §3 risk matrix A 路径条件：
- 改动范围 低-中 ✅（单文件单行）
- 代码位置 低-中 ✅（actions/ 业务文件 / 不动 auth/middleware）
- 可逆性 低（git revert 安全）✅
- 业务断言 低-中 ✅（仅类型再导出 / 函数签名不变）
- 测试覆盖 中 ✅（M02 list projects DOM 已转 PASS）
- bug 类型 低-中 ✅（tooling bug + 类型漂移 / 非 auth bypass / 非数据丢）

**6/6 维度全在 A 路径阈值内 → 直推 / 不需 audit**。

## 与第一条 fix（B-trigger-bug-server-action-cookie）的关系

第一条 fix（cookie path）B 路径 audit medium 已 CY 拍批（见 `04-bug-fixes/B-trigger-bug-server-action-cookie/design-audit.md`）。本 fix（search loader）独立 A 路径 / 无需 CY 拍 / 但因双修包合并 commit（CY 已拍）/ 本 design-audit 走 A 路径报备即可。

两 fix 协同点：
- 第一条修完 → M02 trigger_bug + create-project happy + tenant + archived 4 个 test PASS
- 第二条修完 → M02 list projects DOM 转 PASS
- 联合验证：M01 5/5 + M02 5/5 + tsc 0 错 + next build PASS（rca.md §6）
