---
title: dogfooding sprint bug queue
status: living-doc
owner: CY
created: 2026-05-12
sources:
  - P2 spike subagent 真复现（audit/p2-spike-report.md）
  - P3 executor subagent（待启）
  - P4 fix subagent 完成回写
---

# Dogfooding Bug Queue

> P2/P3 subagent 抓到的真 bug 入队 / 等 P4 fix subagent 入。**不修 spec / 不修 testpoint**。

## 表头说明

| 列 | 含义 |
|---|---|
| ID | `B-<phase>-<module>-<short>` / 全 sprint 唯一 |
| 现象 | 一句话 / 用户视角 |
| 来源 | phase + subagent + 日期 + spec/test 名 |
| status | OPEN / IN_PROGRESS / FIX_DONE / VERIFIED / PUNT |
| 根因（如已抓） | 一行 / 详见 04-bug-fixes/<B-id>/rca.md |
| fix 路径 | 04-bug-fixes/<B-id>/ (A/B/C 路径) |

---

## OPEN 池

| ID | 现象 | 来源 | status | 根因 | fix 路径 |
|----|------|------|--------|------|----------|
| B-trigger-bug-server-action-cookie | 创建项目 submit 后跳 `/login`（应进项目详情 + 列表 0 卡片渲染同根因）| P2 spike Opus subagent 2026-05-12 / M02-project.spec.ts `[P0-CRITICAL] trigger_bug` + `[P0] list projects DOM` | **IN_PROGRESS** | Next.js 自定义版 server action 不能透传浏览器 refresh cookie 给 backend → `serverApiPost` 401 → `withAuthRedirect` 跳 login | 04-bug-fixes/B-trigger-bug-server-action-cookie/（fix subagent 跑中 / B 路径必走 audit） |

## FIX_DONE 池（待 P5 回归）

（空）

## VERIFIED 池（P5 回归 PASS）

（空）

## PUNT 池（推下 sprint）

（空）

---

## 关联 audit / spec / RCA

- P1→P2 闸门 audit：`audit/p1-p2-gate-finding.md`（testpoint 文件 A- 质量 / 不改）
- P2 spike 报告：`audit/p2-spike-report.md`（trigger_bug 真复现 + Next.js 4 坑清单 + 分类决策树）
- M01 spec：`app/e2e/dogfooding/M01-user-account.spec.ts`（5/5 PASS）
- M02 spec：`app/e2e/dogfooding/M02-project.spec.ts`（2 PASS + 3 真 FAIL 抓 bug）

## 元发现候选（P3/P4 期回写 / 不阻塞）

- M07 §8 UI testpoint vs page.tsx 漂移（design 声称 status badge / filter / 转换按钮 / 详情页 / 节点关联 UI 但实现缺）→ design-gap candidate / 不入 bug queue（功能缺失非 bug）
- AddIssueDialog title 字段是否真在 dialog 表单（page.tsx L322 引用 / 未读细节）→ M07 P2 期自查
- Next.js 自定义版坑清单（4 坑 / spike-report §"坑清单"）→ 沉淀候选 / 简历级 STAR 素材
