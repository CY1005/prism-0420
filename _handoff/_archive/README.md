---
title: _handoff/_archive/ 归档索引
status: archive
owner: CY
created: 2026-05-12
purpose: |
  本目录存放已完成 sprint 的启动 prompt / 已被取代的 plan / 已过时的交接快照。
  仅作历史快照与对照参考，不再活跃维护。新动作不读本目录。
---

# _handoff/_archive/ 归档清单

> 真活跃文件留在 `_handoff/` 根；本目录全部冻结。

| 文件 | 归档日期 | 归档理由 | 真实状态依据 |
|------|---------|---------|------------|
| [sprint-prompts-M05-M20.md](sprint-prompts-M05-M20.md) | 2026-05-12 | Phase 2.1 M01-M20 全 sprint ✅ | `design/00-roadmap.md` §1：M01-M08+M10-M20 全交付（M09 superseded by M18） |
| [m20-sprint-prompt.md](m20-sprint-prompt.md) | 2026-05-12 | M20 团队模块 sprint ✅ 2026-05-09 | 同上 |
| [p22-sprint-prompt.md](p22-sprint-prompt.md) | 2026-05-12 | Phase 2.2 总 sprint ✅ 2026-05-09 | `design/00-roadmap.md` §1：Phase 2.2 100% / 7-7 子片 |
| [p22-subslice-prompts.md](p22-subslice-prompts.md) | 2026-05-12 | Phase 2.2 子片 1-5 ✅ | 同上 |
| [phase23-prompts.md](phase23-prompts.md) | 2026-05-12 | Phase 2.3 A/B/C/D 4 子 sprint ✅ / 被 `phase23-integration-cleanup-prompts.md` 接续完成 | `design/00-roadmap.md` §1：Phase 2.3 100% |
| [post-phase23-cleanup-plan.md](post-phase23-cleanup-plan.md) | 2026-05-12 | 2026-05-10 cleanup 计划 / 被 `phase23-integration-cleanup-prompts.md` (S1-S10) 取代并完整执行 | 同上 |
| [next-session.md](next-session.md) | 2026-05-12 | 跨 session 交接旧总表 / 状态停在 Sprint 4C.3（5/10）+ Sprint 3.1/3.2（5/12）/ 不含 dogfooding sprint | 当前接力点已迁到 `_handoff/dogfooding/progress.md` |

---

## 如要复用历史 prompt

历史 sprint prompt 仍有方法论价值（设计前置 / 子片拆分 / 关闸 checklist）。如新 sprint 需要复用模板：

1. 从本目录取对应 prompt 作起点
2. 复制到 `_handoff/` 根并改名为新 sprint 名
3. 在 `_handoff/INDEX.md` 加新条目
4. **不要直接在 _archive/ 文件上改**（会破坏归档完整性）

---

## 历史指针

- 当前活跃 sprint：`_handoff/dogfooding/`（dogfooding 全功能测试）
- 当前活跃 living-doc：`_handoff/INDEX.md` + `_handoff/cross-sprint-punt-pool.md`
- 项目真实进度：`design/00-roadmap.md`
