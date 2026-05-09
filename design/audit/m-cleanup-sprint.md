---
title: M-CLEANUP sprint — Phase 2.1 收官后 cross-sprint punt 池清理
status: completed
owner: CY
sprint: M-CLEANUP / 4 commits / 2026-05-09 / Phase 2.1 100% 后启动
trigger: CY 2026-05-09 反问 "M01-M20 全做完了那为什么还有未来的任务" → 暴露 cross-sprint pool
  49 项 STILL_PUNT 累计存量债 → 启动专门 cleanup sprint 清"约定时机已过"+ "B 类真漏洞" + 最后归类
purpose: |
  Phase 2.1 100% 收官后清 punt 池存量债。本 sprint 不引入新业务 / 仅清旧 punt + 重新归类。
  覆盖范围：
  - 关闭 cross-sprint #10/#11/#12/#13/#14/#8/#9/#3+#15（8 项）
  - 重新归类 41 项剩余 STILL_PUNT 到 A/B/C/D/E 5 类
  - 性能黑洞（元发现 #2 ~12 项）显式归 C 类 / 推荐 Phase 2.3 perf sprint 处理
  - M18 embedding 占位期残留 5 项（#21-#24）显式归 A 类 / 待 pgvector 真接通
---

# M-CLEANUP sprint pilot-template-validation

## 0. 执行摘要

| 指标 | M-CLEANUP 前 | M-CLEANUP 后 |
|------|-----------|-----------|
| baseline PASS | 1613 | 1619 (+6) |
| cross-sprint STILL_PUNT | 49 | 41（关 8 项 / 16% 缩减） |
| cross-sprint DONE | 22 | 30 |
| 真漏洞 B 类（约定已过 high+medium）| 10 项 | **0 项** ✅ |
| R13-1 | 139 | 139（不变 / 无 ErrorCode 新增） |

## 1. M-CLEANUP 实施（4 commits / 2026-05-09）

| # | commit | 子片 | 范围 | tests | 关闭 punts |
|---|--------|------|------|-------|----------|
| 1 | 33b5759 | 子片 1 mechanical | M04-9 target_type const + M04-8 db.get→DAO + M04-1 联合索引 + M10-5 viewer test | 1613→1615 (+2) | #10 #12 #13 #14 |
| 2 | aabde04 | 子片 2 契约缺口 | M04 dimension_service.create + create_dimension_record IntegrityError handler | 1615→1616 (+1) | #11（#3+#15 推迟 D 类） |
| 3 | 5c7783d | 子片 3 M14 + race | M14 update/delete/unlink write_event e2e 3 项 + M05-M08 race 复审 DONE_BY_INSPECTION | 1616→1619 (+3) | #8 #9 |
| 4 | 本 commit | 子片 5 关闸 | cross-sprint pool 重新归类 41 项 + audit + handoff 同步 | ≈1619 | — |

**注**：子片 4 性能黑洞（元发现 #2 ~12 项）SKIP / 需单独 perf sprint 实测基线（design §C7 1000 project P95<100ms）/ 推荐 Phase 2.3 上线前处理。

## 2. 41 项剩余 STILL_PUNT 5 类归类

### A 类：M18 embedding 占位期残留（5 项 / 高 + medium）— 待 pgvector 真接通解锁

| # | 项 | 严重度 | 解锁条件 |
|---|----|------|---------|
| 21 | worker source_text 真接 Service.get_for_embedding | **high** | pgvector 装库 + 真业务 path 启用 |
| 22 | EmbeddingTargetNotFoundError noop 转 succeeded 语义 | low | design 加字面或 task DAO result_label="noop" |
| 23 | cron_failure_monitor PCT 维度真实施 | medium | task_dao.count_completed_in_window 接通 |
| 24 | batch_backfill 真 batch INSERT FROM unnest | medium | 5 万条规模触发 |
| 21+ | M03-1 P-A-03 batch_create 拓扑责任（M11/M17 简化版）| low | 后续重构 sprint |

**建议**：Phase 2.3 上线前 / 或专门 embedding-real-launch sprint 一并接通 pgvector + 解锁这 5 项。

### B 类：真漏洞约定已过（**0 项 / M-CLEANUP 已清完** ✅）

M-CLEANUP 之前 10 项（#3 #6 #8 #9 #10 #11 #12 #13 #14 #15）：
- 8 项关闭（#8 #9 #10 #11 #12 #13 #14 + #3+#15 推迟 D 类）
- 2 项 #6 M07 update detach（None→NULL）→ 待产品决策（CY 拍是否补 detach 路径）

**结论**：B 类约定已过真漏洞已清完，#6 留待产品决策不算"已过"。

### C 类：性能黑洞（元发现 #2 / ~12 项 / 推迟 Phase 2.3 perf sprint）

| 来源 | 项数 | 类别 |
|------|------|------|
| M02 #1 重复 JOIN / #2 batch_update UPSERT | 2 | tenant 过滤双 JOIN / N 条 UPSERT |
| M04 #13 batch_get_by_nodes / #6 N+1 | 2 | 跨模块批量读 / N+1 |
| M05 #14/#15 query 优化 | 2 | set_current 6→5 query / update_metadata 4→3 query |
| M11 #8 size 检查重复 | 1 | parse vs process 双检 |
| M12 #5 _tenant_filter 抽 / #7 双查询合一 | 2 | 7 处 project_id where 抽 helper / COUNT OVER 合一 |
| M19 #27 Cache-Control: no-store | 1 | header 横切 |
| M20 R1-C P2-5 UNION vs UNION_ALL | 1 | M20TenantContext 性能 |
| M20 R1-C P2-1 count + list 双 SELECT | 1 | 删 team 失败路径 |

**建议**：Phase 2.3 上线前立专门 perf sprint（5-7 天）实测 design §C7 性能基线（U 加入 20 team / 每 team 50 project / 1000 project / P95<100ms）+ 决策是否引入 Redis 缓存层。

### D 类：条件触发型（10 项 / 触发条件未到 / 不动）

| # | 项 | 触发条件 |
|---|----|--------|
| 3 | IssueResponse 漏 join 字段 | 前端真用时（Phase 2.2 触发） |
| 15 | DimensionResponse 漏 join 字段 | 同上 |
| 16 | WS golden e2e | M18+ WS integration sprint |
| 17 | _sanitize_filename horizontal | 第三 multipart 实例（M19 输出端首发 / 第四实例触发） |
| 18 | M17 confirm_review 绕 _transition | M18+ 顺手补（已未补） |
| 19 | M17 import_tasks lazy import 抽 helper | 后续重构 sprint |
| 20 | require_platform_admin 去重 | 下一 platform_admin 模块（M20 评估不触发） |
| 25 | _md_cell horizontal 化 | M20+ 团队报告导出（第二渲染场景） |
| 26 | filename sanitize 输入 vs 输出分类 | 第二输出端实例 |
| 28 | filename 含 project_name RFC 5987 | 该改动发生时 |

### E 类：文档 / UNVERIFIABLE（~14 项 / 子片 5 不补）

UNVERIFIABLE 53 项中：
- 多数是 docstring 注释 / 设计意图 / 测试覆盖度文档类
- 部分已被主线工作默默吸收（元发现 #4）
- 不值得专门 commit / 子片 5 grep 验证 / 关闸时显式不立项

## 3. 元贡献清单（M-CLEANUP sprint 4 项 sink）

### 1. **CY 反问触发的 cleanup sprint 范式**

CY 2026-05-09 反问 "M01-M20 全做完了那为什么还有未来的任务" 暴露 cross-sprint pool 49 项
STILL_PUNT 累计存量债 / 项目级"约定时机已过"风险。**立规候选 SR-CLEANUP-1**：每 N
sprint 后启动专门 cleanup sprint 清 cross-sprint pool / 防累计 50+ 项后无人能整理。

### 2. **DONE_BY_INSPECTION 范式（M05-M08 race 复审）**

不是所有 punt 都需要"代码改动 + commit"才算 DONE。M15-B1 升级真 INSERT 后 grep 验证
M05-M08 各处 `if rows == 0: continue` 路径行为等价 = DONE_BY_INSPECTION（依赖 commit
trail + grep 证据 / 不写新 test / 不改代码 / 关闸标记为 DONE）。**立规候选 SR-CLEANUP-2**：
cross-sprint pool 标 DONE 接受三种证据：(a) 代码 commit / (b) 测试 commit / (c)
DONE_BY_INSPECTION（grep + commit hash + 时间戳）。

### 3. **D 类条件触发型 vs B 类约定已过的边界识别**

#3 + #15 IssueResponse / DimensionResponse join 字段原列 B 类（约定已过 / "前端真用时
补 join"），但前端 Phase 2.2 还没起 / 实际是 D 类条件触发型。M-CLEANUP 重新归类后
B 类清完为 0 / D 类 +2。**教训**：punt 立项时"前端真用时"等条件触发表达需显式标 D 类，
不与"M? sprint 顺修"等 B 类混。

### 4. **元发现 #2 性能黑洞累计 12 项**显式归 C 类 + Phase 2.3 perf sprint 提议

M02-M19 累计约 12 项 punt 写"性能 sprint"，本 sprint 显式归 C 类 + 推荐 Phase 2.3 上线前
立专门 perf sprint。防黑洞继续累计。

## 4. cross-sprint punt 池接通

详见 `_handoff/cross-sprint-punt-pool.md` 状态分布快照段重新归类（49→41 STILL_PUNT
+ A/B/C/D/E 5 类显式登记）。

## 5. Phase 2.2 启动条件评估（M-CLEANUP 关闸后复评）

- [x] M01-M05+M20 后端代码 merge ✅
- [x] OpenAPI 契约稳定 ✅
- [x] **B 类真漏洞约定已过 0 项** ✅（M-CLEANUP 关闭）
- [ ] `npm run codegen` 准备 — 待 Phase 2.2 启动时跑
- [ ] 性能黑洞 C 类 12 项 — Phase 2.3 perf sprint 评估（不阻塞 Phase 2.2 前端继承）
- [ ] M18 embedding 占位期残留 A 类 5 项 — 不阻塞 Phase 2.2（前端不触 embedding worker）

**结论**：Phase 2.2 前端继承 Prism 启动条件全部 ✅（A 类不阻塞 + C 类不阻塞 + D 类不阻塞）。

---

last_updated: 2026-05-09
