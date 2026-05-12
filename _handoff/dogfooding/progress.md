---
last_session: 2026-05-12 (P2 spike + trigger_bug 抓到 / fix in progress)
phase: P1 ✅ DONE / P2 🟡 SPIKE DONE / 待 trigger_bug fix 后启 batch
sub_task: P1 21/21 ✅ / P2 spike Opus（M01+M02 pilot / 7 PASS + 3 真 FAIL）✅ / P4-prelim trigger_bug fix Opus 跑中
cost_cumulative: P1 ~$21.0 + P1→P2 audit $3 + P2 spike $1.5 + P4-prelim fix (in-progress) = ~$25.5 + 待算
status: NORMAL / P2 spike verdict=B-范式可行 / trigger_bug 真复现入 03-bug-queue.md / 等 fix subagent 完成后改 phase2-case.md 已就绪 → 启 batch 2-5
---

# Dogfooding Sprint Progress

> single source of truth。每 session 起点必 cat 本文件。每 session 结束必更新 + commit。

---

## Phase 完成状态

- **P0 preflight** ✅ DONE
  - ✅ 00-plan.md 落地（commit 256ae8e）
  - ✅ progress.md 初始化
  - ✅ 目录结构创建
  - ✅ 3 核心 prompt 落地（phase1-testpoint / phase4-fix / phase4-audit）
  - ✅ CY review 00-plan + 3 prompt → 拍 A 路径接受现状全跑

- **P1 testpoint** ✅ DONE（21/21 完成 / 批 1+2+3+4+5 全完 / 2327 testpoint 累计）
  - ✅ M01 user-account / 127 testpoint（P0=45 / P1=69 / P2=13）/ 14 视角 / cost ~$2
    - 文件：`01-testpoints/M01-user-account.md`
    - 质量验证：每条引 design §N + tests.md GN / 单行 / 无 forbidden / 全 self-check 通过
  - ✅ M11 cold-start / 91 testpoint（P0=30 / P1=52 / P2=8 / 实 grep 90）/ 14 视角 / cost ~$1.5
    - 文件：`01-testpoints/M11-cold-start.md`（152 行）
    - 风险点：R-X1 orchestrator 首例 / 共享 db.begin() 跨 service 回滚 / G2/G6 无 idempotency / completed/failed 终态 409 / 10MB+1000 行同步阈值
    - PRD F11 章节未显式存在 → 改引 US-A1.5 + PRD Q3.1（frontmatter 已注）
  - ✅ M14 industry-news / 89 testpoint（P0=27 / P1=46 / P2=16）/ 14 视角 / cost ~$0.6
    - 文件：`01-testpoints/M14-industry-news.md`（151 行）
    - 风险点：首个全局豁免业务模块（GLOBAL DATA NO TENANT FILTER）/ link/unlink 权限裁决 / source_type='manual' 双重防护 / IntegrityError 区分约束名 / 过去式 action_type / activity_log 非事务
  - ✅ M19 import-export / 86 testpoint（P0=25 / P1=46 / P2=15）/ 14 视角 / cost ~$0.6
    - 文件：`01-testpoints/M19-import-export.md`（148 行）
    - 风险点：action_type "exported" 4 处同步漂移 / Content-Disposition filename sanitize 输出端首发 / 跨 project node 走 422 而非 404 / viewer 写 activity_log / EXPORT_EMPTY_CONTENT 422 优先空报告
  - ✅ M20 team / 128 testpoint（P0=61 / P1=62 / P2=5）/ 12 视角 / cost ~$1.2 / **escalation surface ≥100 → 已按 P0/P1/P2 拆好**
    - 文件：`01-testpoints/M20-team.md`（186 行）
    - 风险点：R-X3 跨事务签名首发 / L3 SQL 注入横切 M03-M19 / correlation_id F2.9 + R10-1 批量独立 N+1 / 嵌套 max(team_role, project_role) 10 组合 / archived × team 双路径互锁 F2.3
    - 复杂度最高单 sprint（design §14.5 R-X5 实证）/ P0 占比 47.7% 偏高合理
  - ✅ M02 project / 130 testpoint（P0=52 / P1=66 / P2=12）/ 15 视角全用 / cost ~$0.7
    - 文件：`01-testpoints/M02-project.md`（196 行）
    - 风险点：AES 加密路径横切归属 / 多表事务回滚（4 步：projects + members + dimension_configs + activity_log）/ PG 部分唯一索引归档语义边界 / archive 不级联（design §4 P5 audit F-2）/ baseline-patch 时序契约（M20/M18 反向引用）/ last-write-wins（AI Key + project name 无乐观锁）/ 三层权限矩阵
  - ✅ M03 module-tree / 84 testpoint（P0=32 / P1=43 / P2=9）/ 11 视角 / cost ~$0.6
    - 文件：`01-testpoints/M03-module-tree.md`（137 行）
    - 风险点：R-X2 R10-1 删除调下游 + 子树 N 条 activity_log（CASCADE 不触发下游）/ path 物化路径 move_subtree 循环引用防御 / last-write-wins 不加锁（与 M01/M02 对照）/ type 不可变三重防护 / M18 baseline-patch get_for_embedding 推迟 / 拓扑排序责任 punt（A5 caller-must）
  - ✅ M04 feature-archive / 106 testpoint（P0=39 / P1=58 / P2=9）/ 15 视角全用 / cost ~$1.1 / **escalation surface ≥100**
    - 文件：`01-testpoints/M04-feature-archive.md`（173 行）
    - 风险点：乐观锁 + DB UNIQUE 双防御（dimension_records）/ R-X3 对外契约 5 方法（M03/M11/M12/M13/M17/M18 调用入口 / 事务边界 caller 控制）/ project_id 冗余 tenant 字段（CHECK + generated column 兜底 + DAO 双过滤）/ content JSONB 运行期 jsonschema 校验（依赖 M02 dimension_types）/ M18 baseline-patch B 路径 enqueue 推迟
  - ✅ M05 version-timeline / 111 testpoint（P0=42 / P1=57 / P2=12）/ 13 视角 / cost ~$1.0 / **escalation surface ≥100**
    - 文件：`01-testpoints/M05-version-timeline.md`（170 行）
    - 风险点：DB 部分唯一索引 uq_version_node_is_current race（两并发 set-current）/ 冗余 project_id 一致性（service 强制 record.project_id = node.project_id）/ cross-tenant node_id 攻击（service 第三层防御 _check_node_belongs_to_project）/ PUT snapshot_data 拒绝（Pydantic schema 无该字段自动拒）/ L1-α detach 语义（exclude_unset） / IntegrityError catch 横切硬规则
  - ✅ M06 competitor / 90 testpoint（P0=36 / P1=43 / P2=11）/ 11 视角 / cost ~$1.0
    - 文件：`01-testpoints/M06-competitor.md`（144 行）
    - 风险点：R-X3 第三真注入 4 参签名（delete_by_node_id 给 M03 / batch_create_in_transaction 给 M11/M17）/ Q4 R1-A 立修档案页内联多表事务 / 级联删除 activity_log 顺序敏感（CASCADE 前显式批量写 delete）/ 跨项目竞品引用 422 非 403 / DB UNIQUE(node_id, competitor_id) 但无 display_name UNIQUE
  - ✅ M07 issue / 110 testpoint（P0=42 / P1=56 / P2=12）/ 15 视角全用 / cost ~$1.0 / **escalation surface ≥100**
    - 文件：`01-testpoints/M07-issue.md`（176 行）
    - 风险点：状态机 4 态（open/in_progress/resolved/closed）+ 5 禁止转换（专列 16 条）/ R-X3 `orphan_by_node_id` SET NULL 语义（与 M04/M06 同签名不同行为）/ node_id NULL 合法（US-B1.6 项目级问题）/ 取消认领权限灰区（in_progress→open 仅 assignee 或 admin）/ M18 baseline-patch A7 退化路径
  - ✅ M08 module-relation / 88 testpoint（P0=37 / P1=43 / P2=8）/ 11 视角 / cost ~$1.0
    - 文件：`01-testpoints/M08-module-relation.md`（141 行）
    - 风险点：三元组 UNIQUE(src, tgt, type) + IntegrityError 按 constraint name 区分 / R-X3 第四真注入实证（接受外部 db session 不自开事务）/ R-X2 vs DB CASCADE（M03 必须显式调 delete_by_node_id 不能依赖 CASCADE）/ R10-1 N 条独立 activity_log / *_node_name + created_by_name 三连 punt（前端 N+1 lookup）
  - ✅ M10 overview / 79 testpoint（P0=32 / P1=39 / P2=8）/ 12 视角 / cost ~$1.5
    - 文件：`01-testpoints/M10-overview.md`（135 行）
    - 风险点：ADR-003 规则 2 OverviewDAO 只读豁免边界（任何 INSERT/UPDATE/DELETE 违反）/ 分母=0 早返回 OverviewNoDimensionsError(422) / folder 均值迭代后序遍历防深层树栈溢出（_build_tree 排序仍递归）/ /completion endpoint M04 唯一注册防双注册 / Pydantic 自引用模型 model_rebuild() 必调 / CY ack 红黄绿阈值常量 0.3/0.7
  - ✅ M12 comparison / 99 testpoint（P0=35 / P1=56 / P2=8）/ 14 视角 / cost ~$1.2
    - 文件：`01-testpoints/M12-comparison.md`（161 行）
    - 风险点：G4=B 值快照不降级（保存后改 M04 dim_record / 删 M03 node 都不影响 snapshot.items.content）/ 多表事务 snapshots+items+activity_log 三表 with db.begin() 全量回滚 / 跨模块只读纪律（comparison_service 调 M04 batch_get_by_nodes 不直查 dimension_records / R-X1 合规）/ 乐观锁 expected_version 不匹配 409 不写 activity_log / nodes_ref JSONB list[str(UUID)] 类型转换边界 / viewer 写 3 端点 403 主动复制 M07/M08 元教训
  - ✅ M13 requirement-analysis / 142 testpoint（P0=53 / P1=72 / P2=17）/ 15 视角全用 / cost ~$1.2 / **escalation surface ≥100**
    - 文件：`01-testpoints/M13-requirement-analysis.md`（211 行）
    - 风险点：SSE 流式 pilot（5min 长连接打满 PG pool / chunk 顺序 / aclose 协议 / AbortController 真停）/ R-X3 共享 session 第六真注入实证（M04.create_dimension_record 接受外部 db）/ P2 Server Action HMAC 凭据路径（audit B2）/ 上游 Service 签名对不上（audit B1 / M02/M03/M04/M07 baseline-patch 前置）/ JWT 主动作废中途流不中断 ≤5min 暴露窗口 / 重复 save 多条 dimension_record + 前端防抖（audit R2-04）/ LLM 集成首发 MockProvider aclose_called 可断言（design §14.5 LLM 红线）
  - ✅ M15 activity-stream / 102 testpoint（P0=38 / P1=51 / P2=13）/ 15 视角全用 / cost ~$1.3 / **escalation surface ≥100**
    - 文件：`01-testpoints/M15-activity-stream.md`（167 行）
    - 风险点：R10-2 activity_logs 横切表唯一 owner（ActionType+TargetType enum + CheckConstraint + Alembic 4 处同步）/ C-5 权限非默认（viewer 不可读 / 与多数只读模块相反）/ design §3 三处 disambiguation（Mapped[ActionType] vs str+CheckConstraint / event_metadata 重映射 / list_for_team 签名）/ D-2 分页 total 分支（page=1 精确 / page>1 null + has_more）/ M14 baseline-patch project_id NULLABLE（全局事件跨模块 patch 风险）/ 僵尸 target_id 展示（无 FK / summary 字段冻结目标名）/ R14 守护（业务模块写 activity_log 必须用枚举字面 / M16 sprint 实证 31 处机械批量改）
  - ✅ M16 ai-snapshot / 141 testpoint（P0=59 / P1=68 / P2=14）/ 15 视角全用 + 3 模块专属 / cost ~$1.2 / **escalation surface ≥100**
    - 文件：`01-testpoints/M16-ai-snapshot.md`（207 行）
    - 风险点：BackgroundTasks vs zombie cron CAS race（runner 失败分支必须 cas_complete 不直 UPDATE / audit B3）/ advisory_xact_lock 幂等 get-or-create 替代 DB UniqueConstraint（audit B1+M6）/ GET endpoint 双层鉴权 + 错误码打码统一 404（audit B4）/ save path/task 一致性（SnapshotTaskPathMismatchError 422 防跨 node 攻击 / audit M5）/ content dict 形态契约（audit B2 / M04 JSONB 对齐）/ cron 写 activity_log 落 SYSTEM_USER_UUID（ADR-002 §1.1）/ zombie 阈值 11min + pending 兜底 2min / cron 频率 5min ≤ 阈值/2 / dot-notation action_type 待 Alembic 迁移回写 M15
  - ✅ M17 ai-import / 143 testpoint（P0=62 / P1=66 / P2=15）/ 15 视角全用 + 2 异步专项 / cost ~$1.0-1.5 / **escalation surface ≥100**
    - 文件：`01-testpoints/M17-ai-import.md`（212 行）
    - 风险点：idempotency 跨项目污染（audit B1+R2-01 已修复 / 三元组 key + 7 天过期）/ M17 越权直写跨模块表（audit B2 / 改 orchestrator 调 Service / R-X1 第二实例守护）/ 状态机 11 状态 + 5 禁止转换补全（partial_failed → completed / failed → any / awaiting_review → importing / audit B4）/ WebSocket 每命令鉴权（audit B6 / 防同连接 cancel 任意 task）/ R-X1 importing single transaction 取消 ROLLBACK 路径 / AI Provider 配额超限 IMPORT_QUOTA_EXCEEDED / TOAST 超大 JSONB / chunk_id index / 死信通知 email TBD / mypy strict TaskPayload 基类（audit B5）
  - ✅ M18 semantic-search / 143 testpoint（P0=68 / P1=56 / P2=19）/ 13 视角（国际化 N/A）/ cost ~$1.5 / **escalation surface ≥100**
    - 文件：`01-testpoints/M18-semantic-search.md`（208 行）
    - 风险点：embeddings 表 7 字段 PK + 异维列拆分（embedding_512/1536/3072 + dim 路由 / audit B4 schema 性死债务）/ 删除一致性（audit B1+C2 / except SilentFailure 不能 except Exception 否则崩溃 / orphan cleanup cron 兜底）/ 三段式回填语义（PROVIDER+MODEL_NAME+MODEL_VERSION 三 env 全改 / 漏一个 fallback 全表 / fix v4.1 R5'=B）/ 失败容忍 vs §12C 反向（embedding 失败不通知用户 / 三维 monitor 阈值告警 CY）/ 跨模读双路豁免（ADR-003 规则 4 / 增量 R-X3 调上游 / backfill 只读 import + LEFT JOIN / DAO 必须分文件）/ Race 与幂等三层（Redis SET 60s debounce + pg_advisory_xact_lock 双 namespace 防 hashtext 32-bit 跨 project 鸽笼碰撞 + content_hash 7 字段 PK）/ pgvector 降级 SEARCH_MODE kill switch（audit B5 / env 一键切 hybrid/keyword_only/semantic_only）/ backfill 中断恢复（fix v3 决策 2=A / async def + arq_pool 形参 + _job_id 1h 幂等去重）
  - ✅ _cross-cutting / 238 testpoint（P0=153 / P1=69 / P2=16）/ 18 视角 / cost ~$1.8 / **远超 ≥80 testpoint + ≥12 视角要求**
    - 文件：`01-testpoints/_cross-cutting.md`（314 行）
    - 视角清单：Auth flow(25) / 跨 tab cookie sync(6) / 网络断连+API 超时(12) / 权限三层防御(13) / R-X 横切纪律(12) / 异步路径范式(19) / 幂等三层(9) / 状态机非法转换(14) / AI Provider 集成边界(13) / baseline-patch 时序契约(10) / DB 部分唯一索引 race+多表事务回滚(15) / cross-tenant 三层防御(11) / tenant 豁免 2 类+ADR-003 只读豁免(13) / activity_log 失败传播+SYSTEM_USER_UUID(14) / action_type 同步漂移+R14 守护(11) / filename sanitize+跨项目 422+viewer 403+disambiguation(14) / i18n+mobile+性能(14) / schema 性死债务+cross-tenant(13)
    - 风险点 Top 5：Auth INTERNAL_TOKEN 泄露 + P2 信任链断裂（ADR-004 §3.5）/ baseline-patch 时序契约 punt 池堆积 6 处（升级 cross-sprint punt 池）/ JWT 主动作废中途 SSE 流不中断 ≤5min 暴露窗口（M13）/ M18 三 env 同步漂移 + schema 性死债务（漏一个 fallback 全表回填 5 万行 1+小时）/ R-X3 共享 session 真注入 5 处 + R-X1 orchestrator + DAO 必须分文件
    - 22 个元发现转化全打勾（批 1-4 沉淀的所有元发现 → cross-cutting testpoint）

  ### 批 1 汇总（M11/M14/M19/M20 / 4 模块）
  - **testpoint 总数**：394（P0=143 / P1=206 / P2=44）
  - **cost**：~$3.9（4 subagent 4 并发）
  - **跨模块元发现**（design 推导的 surface 候选）：
    - R-X1 orchestrator 首例（M11）+ R-X3 跨事务签名首发（M20）→ design 中 R-X 系列横切纪律集中爆发 / 建议 cross-cutting 视角单立测试集
    - 全局豁免业务模块（M14 首发）+ 跨 project 只读消费（M19）→ tenant 隔离边界 2 类例外，需要 cross-cutting 集中规约
    - activity_log 失败传播 4 模块全覆盖（M16 范式 / M11/M14/M19/M20 复用）→ 已成横切纪律
    - action_type 同步漂移 M14（5 个过去式）+ M19（4 处同步）→ CI 守护 / 设计漂移防御视角必须有专项
    - filename sanitize 输出端首发（M19）→ 后续 M17/M18 导出场景复用范式

  ### 批 2 汇总（M02/M03/M04/M05 / 4 主流业务模块）
  - **testpoint 总数**：431（P0=165 / P1=224 / P2=42）
  - **cost**：~$3.4（4 subagent 4 并发 / 略低于批 1）
  - **escalation surface ≥100**：M02 130 / M04 106 / M05 111（3/4 命中 / 主流业务模块全 escalation 是常态）
  - **新增跨模块元发现**：
    - R-X3 对外契约范式（M04 5 方法集中 / M05 跨模块契约 / 与 M11 R-X1 + M20 R-X3 跨事务呼应）→ R-X 系列横切纪律已成 design 主轴 / 必有 cross-cutting 集中测试集
    - last-write-wins 不加锁（M02 AI Key / M03 reorder/move 子树）vs 乐观锁（M01 + M04 dimension_records version）→ 并发策略 design 内部已分化 / cross-cutting 必专项
    - DB 部分唯一索引 race 跨模块（M02 uq_project_owner_name_active 归档释放 / M05 uq_version_node_is_current set-current race / M03 也有 path UNIQUE）→ "部分唯一索引 race" 成横切模式
    - 多表事务回滚（M02 4 步 / M11 共享 db.begin() / M20 R-X3 跨事务）→ 事务边界 design 主纪律 / cross-cutting 必专项
    - baseline-patch 时序契约（M02 反向引用 M20/M18 / M03 enqueue B 推迟 / M04 enqueue B 推迟）→ M18 sprint 期回写责任已堆积 3 处 / 需 punt pool 追踪
    - cross-tenant 攻击防御（M05 service 第三层 _check_node_belongs_to_project / R1-C P1-02 立修）→ 三层防御红线
    - 实战观察：4 个"主流业务"模块的 testpoint 数 84-130，比估 50-80 偏高（M03 84 是唯一例外，原因是 path 物化路径压缩了视角数）

  ### 批 1+2 累计（M01 + 批 1 + 批 2 / 9 模块 / 21 模块进度 43%）
  - **testpoint 累计**：127 (M01) + 394 (批 1) + 431 (批 2) = **952 testpoint**
  - **cost 累计**：~$2 (M01) + ~$3.9 (批 1) + ~$3.4 (批 2) = **~$9.3 dogfooding 自身**
  - **批次实战修正后估算**（剩 12 模块）：
    - 批 3 (M06/M07/M08/M10/M12)：5 模块 × ~$1 = ~$5
    - 批 4 (M13/M15/M16/M17/M18)：5 模块 × ~$1.5 (复杂业务 + AI 类) = ~$7.5
    - 批 5 (_cross-cutting)：1 × ~$2 = ~$2
    - **P1 剩余 ~$14.5 / 跨 3-4 个新 session**

  ### 批 3 汇总（M06/M07/M08/M10/M12 / 5 模块 / 4+1 并发）
  - **testpoint 总数**：466（P0=182 / P1=237 / P2=47）
  - **cost**：~$5.7（4 并发 ~$4.5 + M12 单派 ~$1.2 / 略高于 $5 估）
  - **escalation surface ≥100**：M07 110（状态机 4 态 + 5 禁转 + R-X3 第三真注入 + 6 错误码复杂度天然高）
  - **新增跨模块元发现**：
    - R-X3 第三/第四真注入实证（M06 `delete_by_node_id` + `batch_create_in_transaction` / M07 `orphan_by_node_id` SET NULL / M08 `delete_by_node_id` / 与 M04 R-X3 范式 / M11 R-X1 / M20 R-X3 跨事务呼应）→ R-X 系列横切纪律已 4 模块连续命中 / **cross-cutting 视角集中测试集必有 R-X 专项**
    - 状态机禁转 5 条专列范式（M07）→ 后续 M13 等含状态机模块复用 / 跨 tab + cross-cutting 必有"非法转换"专项
    - ADR-003 只读豁免边界（M10 OverviewDAO 任何 INSERT/UPDATE/DELETE 违反）→ design 原则跟实施真对齐的 audit 命中点 / phase3 v0.4 D4 维度数据点
    - 跨项目实体 422 非 403 范式（M06 竞品 + M08 module-relation）→ 与 M19 import-export "跨 project node 422" 同模式连续 3 模块命中 / cross-cutting 集中规约
    - viewer 写端点 403 全覆盖元教训（M07 主动立 / M08 主动复制 / M12 主动复制）→ design §14.5 防御性测试范式跨模块自传播
    - G4=B 值快照不降级范式（M12 snapshot.items.content 副本 / 与 M05 version-timeline G-? 范式对应）→ snapshot 类语义 cross-cutting 专项
    - 多表事务 with db.begin() 主纪律 4 模块连续命中（M06 内联档案页 / M07 / M08 / M12 三表 + activity_log）→ 已成 design 主轴 / cross-cutting 必专项
    - M18 baseline-patch 时序契约堆积 +1 处（M07 A7 退化路径）→ punt pool 累计 4 处（M02 + M03 + M04 + M07）
    - 实战观察：批 3 单批 testpoint 数 79-110 与批 2 (84-130) 趋同 / 主流业务模块稳定在 ~90 / M07 escalation surface ≥100 是状态机复杂度天然 / M10 79 偏低因只读 + 强豁免

  ### 批 1+2+3 累计（M01 + 批 1 + 批 2 + 批 3 / 14 模块 / 21 模块进度 67%）
  - **testpoint 累计**：127 + 394 + 431 + 466 = **1418 testpoint**
  - **cost 累计**：~$9.3 + ~$5.7 = **~$15.0 dogfooding 自身**（含 M01 pilot $2）
  - **触及 $10 sprint 单 session 硬上限**：本 session 强制关闸 + 新 session 跑批 4

  ### 批 4 汇总（M13/M15/M16/M17/M18 / 5 模块 AI+复杂业务 / 拆 4+1 并发）
  - **testpoint 总数**：671（P0=280 / P1=313 / P2=78）
  - **cost**：~$6.2（4 并发 ~$4.7 + M18 单派 ~$1.5 / 接近批 4 估 $7.5 / 略低于估）
  - **escalation surface ≥100**：M13 142 / M15 102 / M16 141 / M17 143 / M18 143（**5/5 命中 / AI+复杂业务模块全 escalation 是常态**）
  - **新增跨模块元发现**：
    - **R-X 横切纪律继续爆发**：M13 R-X3 共享 session 第六真注入（写 M04 dimension_record）/ M16 cron 写多模块 / M17 越权直写需 audit / M18 增量走 R-X3 + backfill 走 ADR-003 规则 4 双路豁免 → **R-X 系列已 8 模块连续命中 / cross-cutting 必有 R-X 专项 + DAO 必须分文件子项**
    - **AI 异步路径 4 范式集中爆发**：M13 SSE 流式 + M16 BackgroundTasks/cron 双路 + M17 Queue + WebSocket + M18 enqueue_delete + Redis debounce + advisory_xact_lock → 异步纪律 cross-cutting 必须单独立"异步路径范式"专项
    - **幂等三层堆积**：M16 advisory_xact_lock 替代 UniqueConstraint / M17 idempotency key 三元组 + 7 天过期 / M18 Redis SET 60s + pg_advisory_xact_lock 双 namespace + content_hash 7 字段 PK → 幂等设计已成 design 主纪律 / cross-cutting "幂等模式对照表"专项
    - **状态机复杂度天花板**：M17 11 状态 + 5 禁止转换（与 M07 4 态 + 5 禁转范式呼应）/ M16 zombie cron CAS race 状态机 / M18 5 cron + 3 层幂等 → 状态机非法转换 cross-cutting 已 3 模块命中
    - **AI Provider 集成首发**（M13 LLM red line / M17 多 provider + 配额 / M18 PROVIDER+MODEL_NAME+MODEL_VERSION 三 env 同步）→ AI 边界 cross-cutting 专项
    - **WebSocket 协议视角首发**（M17）→ 新视角加入 cross-cutting 测试集（握手 / 每命令鉴权 / ping-pong）
    - **JWT 主动作废中途流不中断 ≤5min 暴露窗口**（M13）→ auth 时间窗 cross-cutting 待覆盖
    - **新增 disambiguation 模式**（M15 design §3 三处）→ Pydantic schema vs SQLAlchemy 模型字段映射 cross-cutting 专项
    - **baseline-patch 时序契约堆积 +2**：M13 audit B1（M02/M03/M04/M07 baseline-patch 前置）+ M15 baseline-patch project_id NULLABLE → punt pool 累计 6 处（M02 + M03 + M04 + M07 + M13 + M15）
    - **schema 性死债务首发**（M18 audit B4 / embeddings 表 7 字段 PK + 异维列拆分）→ "schema 一次错全表回填"专项 / 跟 M04 乐观锁 + DB UNIQUE 双防御对照 / 设计前置价值实证点
    - 实战观察：批 4 单批 testpoint 数 102-143 / 5/5 全 ≥100 / 与 批 1-3 主流业务 79-130 对比 / **AI+复杂业务模块密度显著高（design 业务面宽 + 异步 + 幂等 + 状态机 + provider + 跨模读豁免叠加）**

  ### 批 1+2+3+4 累计（M01 + 批 1 + 批 2 + 批 3 + 批 4 / 19 模块 / 21 模块进度 90%）
  - **testpoint 累计**：127 + 394 + 431 + 466 + 671 = **2089 testpoint**
  - **cost 累计**：~$15.0 + ~$6.2 = **~$21.2 dogfooding 自身**（含 M01 pilot $2）
  - **本 session**：批 4 全 5 模块单 session 完成 / cost ~$6.2 自身（含主 agent ~$0.5）/ **未触 $10 单 session 硬上限**（5 subagent ≤4 并发 / context 不堆叠 / 节流策略起作用）

- **P2 case** 🟡 SPIKE 完 / 待 trigger_bug fix 后启 batch
  - 2026-05-12 P1→P2 闸门 audit：`audit/p1-p2-gate-finding.md` / verdict=PASS_WITH_FIX / testpoint 文件 A- 质量不改 / P0 finding=范式错位（API contract 视角 vs 全 DOM 端到端）→ CY 拍两轨范式 B
  - 2026-05-12 P2 spike Opus subagent：`audit/p2-spike-report.md` / verdict=B-范式可行 / 写 M01+M02 pilot spec / cost ~$1.5 / 25 min
    - M01-user-account.spec.ts 146 行 / 5 tests / **5/5 PASS** ✅
    - M02-project.spec.ts 209 行 / 5 tests / 2 PASS + **3 真 FAIL 抓 trigger_bug**
    - **trigger_bug 真复现** → 入 `03-bug-queue.md` B-trigger-bug-server-action-cookie / 同根因 list projects 0 卡片渲染（B-pre-2）
    - Next.js 自定义版 4 坑（server action cookie 透传 / `__next-route-announcer__` 冲突 / server action 303 redirect / AuthProvider mount timeout ≥8s）→ 沉淀进 `prompts/phase2-case.md` Forbidden 范式红线
    - phase2-case.md 8 条改完（两轨范式 / 分类决策树 / 三标签 punt / Self-check +1 真跑 / Forbidden +3 Next.js 坑 / Escalation 真 bug vs spec 错区分 / 启动 prompt 模板）
  - 🟡 阻塞批量：P4-prelim trigger_bug fix Opus subagent 跑中 / B 路径 + audit / fix 完后启 batch 2-5
- **P3 executor** ⬜ NOT_STARTED
- **P4 闭环** 🟡 P4-prelim 进行中（trigger_bug fix）/ 其余待 P3 后
- **P5 final** ⬜ NOT_STARTED

---

## 已发现 bug 池（前置 / dogfooding 触发）

| ID | 现象 | 来源 | status |
|----|------|------|--------|
| B-pre-1 | 创建项目后跳 login（应进项目详情）| CY dogfooding 2026-05-12 / P2 spike 真复现 | **OPEN / P4 修中（B-trigger-bug-server-action-cookie）** / 根因=Next.js 自定义版 server action cookie 透传断裂 |
| B-pre-2 | /projects 列表 0 卡片渲染（getProjects server action 失败）| P2 spike 2026-05-12 顺带抓 | OPEN / 同根因 / fix B-pre-1 自然覆盖 |

---

## 下一 session cold-start 顺序

1. `cat _handoff/dogfooding/progress.md`（本文件 / 起点）
2. `cat _handoff/dogfooding/00-plan.md`（§2 8 类 agent + §5 验收 / 拿总 plan）
3. `cat _handoff/dogfooding/prompts/phase1-testpoint.md`（P1 提示词 / 跟 M01 pilot 用同一份）
4. `cat _handoff/dogfooding/prompts/phase1-testpoint-invocation-template.md`（含 4 并发 invoke 示例 / 6 变量替换清单）
5. `cat _handoff/dogfooding/01-testpoints/M11-cold-start.md` 抽样看批 1 实战输出（128 testpoint 上限 / 14 视角 / 单行 / 引 design §N）

## 下一 session 任务（启 P1 剩余 14 模块 / 批 2-5）

**策略**：并行启动（按 [[feedback_usage_budget]] 信号 A 节流 / 最多 4 并发 Opus subagent）

**批 1 实战观察**（影响后续批次决策）：
- 4 个"边缘模块"实际 testpoint 数 86-128（远超估 30-50）/ 不阻塞但 cost 比估高 / 批 2-4 估算应 +50%
- M20 触发 ≥100 escalation surface 但不阻塞 / 按 P0/P1/P2 已拆好 / 后续大业务模块应预期同等触发
- 4 并发 Opus 单批次实际 cost ~$3.9（接近 $4 估）/ 单 session $10 软上限可装 2 批
- 风格红线全过（0 forbidden 真违反 / 1 false positive 词频）/ prompt 模板鲁棒
- 元发现：R-X 横切纪律 / tenant 豁免 2 类 / activity_log 失败传播 / action_type 同步漂移 / filename sanitize → cross-cutting 视角需专项

**推荐分批顺序**（按模块复杂度从低到高 / 先简单的验证 prompt 鲁棒性）：

### 批 1（边缘模块 / 30-50 testpoint each / 4 并发）✅ DONE 2026-05-12
- M11 cold-start ✅ 91
- M14 industry-news ✅ 89
- M19 import-export ✅ 86
- M20 team ✅ 128 (escalation surface)

### 批 2（主流业务 / 50-80 testpoint each → 实测 84-130 / 4 并发）✅ DONE 2026-05-12
- M02 project ✅ 130 (escalation surface)
- M03 module-tree ✅ 84
- M04 feature-archive ✅ 106 (escalation surface)
- M05 version-timeline ✅ 111 (escalation surface)

### 批 3（主流业务续 / 5 模块 / 拆 4+1 并发）✅ DONE 2026-05-12
- M06 competitor ✅ 90
- M07 issue ✅ 110 (escalation surface)
- M08 module-relation ✅ 88
- M10 overview ✅ 79
- M12 comparison ✅ 99（单派 / 信号 A ≤4 并发硬约束）

### 批 4（AI / 复杂业务 / 5 模块 / 拆 4+1 并发）✅ DONE 2026-05-12
- M13 requirement-analysis ✅ 142 (escalation surface)
- M15 activity-stream ✅ 102 (escalation surface)
- M16 ai-snapshot ✅ 141 (escalation surface)
- M17 ai-import ✅ 143 (escalation surface)
- M18 semantic-search ✅ 143（单派 / 信号 A ≤4 并发硬约束）(escalation surface)

### 批 5（跨模块视角）✅ DONE 2026-05-12
- _cross-cutting ✅ 238 testpoint / 18 视角（单独 subagent / 按视角组织 / 22 个元发现全转化）

### 批 5 汇总（_cross-cutting / 单 subagent / 按视角组织）
- **testpoint 总数**：238（P0=153 / P1=69 / P2=16）/ P0 占比 64% 偏高合理（cross-cutting 是系统级风险密集区 / 元发现专项全 P0）
- **视角数**：18（远超 ≥12 / 8 通用 + 10 元发现专项）
- **cost**：~$1.8（单 subagent / 12 项 input contract + 4 testpoint 抽样 + 单文件 238 testpoint / 远低于 $3 cap）
- **元发现转化对照**（批 1-4 沉淀 22 项全打勾）：
  - R-X 横切纪律 3 子项（R-X1/R-X2/R-X3）✓
  - 异步 7 范式（SSE/BackgroundTasks/cron/arq/WebSocket/Redis/advisory_lock）✓
  - 幂等三层（idempotency_key / advisory_xact_lock / Redis SET + PK）✓
  - 状态机非法转换跨 6 模块统一返码 ✓
  - AI Provider 三 env 同步 ✓ / JWT ≤5min 暴露窗口 ✓
  - baseline-patch punt 池 6 处 ✓
  - DB 部分唯一索引 race（M02/M03/M05）✓
  - last-write-wins vs 乐观锁分化 ✓
  - cross-tenant 三层防御 + tenant 豁免 2 类 + ADR-003 只读豁免 ✓
  - activity_log 失败传播 + SYSTEM_USER_UUID ✓
  - action_type 同步漂移 + R14 守护 ✓
  - filename sanitize / 跨项目 422 / viewer 403 全覆盖 / disambiguation 模式 ✓
  - schema 性死债务 / G4=B 值快照不降级 ✓

### 批 1+2+3+4+5 累计（M01 + 批 1+2+3+4 + _cross-cutting / 21 文件 / 21 模块进度 100%）
- **testpoint 累计**：127 + 394 + 431 + 466 + 671 + 238 = **2327 testpoint**
- **cost 累计**：~$21.0 dogfooding 自身（含 M01 pilot $2）
- **本 session（批 5）**：单 subagent cross-cutting / cost ~$1.8（主 agent + Opus subagent）/ 远低于 $8 单 session 软上限 / 节流红线全过
- **P1 闸门**：21 testpoint 文件齐 / 2327 testpoint 总 / 风格红线全过 / 元发现 22 项全转化 / **待 CY review 抽样 3-4 模块 → 进 P2 case**

### 单次 subagent prompt 模板

**直接读** `_handoff/dogfooding/prompts/phase1-testpoint-invocation-template.md`：
- 含完整 prompt 模板（基于 M01 pilot 实际派的 / 含 briefing + 8 项 input contract + Forbidden + Self-check + Cost cap）
- 含 6 个变量替换清单（MODULE_ID / MODULE_NAME / SHORT_NAME / COMPLEXITY / DESIGN_PATH / TESTS_PATH / OUTPUT_PATH）
- 含 18 模块 → name 映射
- 含 4 并发 Agent tool invoke 示例

主 agent cold-start 流程：
1. `cat _handoff/dogfooding/prompts/phase1-testpoint-invocation-template.md`
2. 拿到当前批次 4 个模块的变量值（如批 1: M11/M14/M19/M20）
3. 在单 user message 里发 4 个 Agent tool call 并行
4. 等 4 个 subagent 都返回（约 3-5 min）
5. 抽样验证输出格式（grep H2 视角清单 / grep Forbidden 内容 / wc -l）
6. 一次性 commit `dogfooding P1 batch<N> — N modules / <total> testpoints`
7. 更新本 progress.md（对应模块行加 ✅ + testpoint 数 + cost + 风险点 + 文件链接）
8. cost 节流：若本 session 已用 >$8 / 退出 / 下一 session 跑下一批

---

## 新 session 启动提示词（CY 直接复制 / 跨批次复用）

**通用模板**（替换 N 即可）：

```
cold-start dogfooding P1 批 N
```

**具体批次**：

- 批 3：`cold-start dogfooding P1 批 3`（M06/M07/M08/M10/M12 / 5 模块 / 拆 4+1）
- 批 4：`cold-start dogfooding P1 批 4`（M13/M15/M16/M17/M18 / AI+复杂业务 / 4+1）
- 批 5：`cold-start dogfooding P1 批 5`（_cross-cutting / 单 subagent 按视角组织）

**新 session 主 agent 拿到提示词后的标准动作**：

1. `cat _handoff/dogfooding/progress.md`（本文件起点 / 拿当前批次状态 + 批 1+2 实战观察）
2. `cat _handoff/dogfooding/00-plan.md`（§2 8 类 agent / §5 验收）
3. `cat _handoff/dogfooding/prompts/phase1-testpoint-invocation-template.md`（4 并发 invoke 模板 + 6 变量替换 + 18 模块 name 映射）
4. 抽样 1 个已完成的 testpoint 文件验证格式（建议 M02 130 testpoint 或 M01 127 testpoint / 看 H3 视角清单 + 单行格式）
5. `ls design/02-modules/M<NN>*/` 确认本批 design dir 齐全
6. 单 message 并发派 N 个 Opus Agent（按 invocation template 替换变量）
7. 等全部返回 → 抽样 grep H3/forbidden → 更新 progress.md → 一次性 commit
8. cost 节流：dogfooding 自身 >$8 → 关闸退出 → 让 CY 决定续

**节流红线**（[[feedback_usage_budget]] 信号 A）：
- ≥4 并发 Opus subagent 前问"能合成一个吗"（这里因独立模块明确不能 / 一致已批准）
- 单 session dogfooding 自身累计 >$8 强制关闸
- 长 context >150k 不再叠 subagent / 必新 session

### Cost 估算（P1 剩余）

- 批 1（4 module）：4 × $1 = $4
- 批 2（4 module）：4 × $2 = $8
- 批 3（5 module）：5 × $2 = $10
- 批 4（5 module）：5 × $2.5 = $12.5
- 批 5（cross-cutting）：1 × $2 = $2
- **P1 总剩余: ~$36-40**
- 跨 5-6 session（每 session 4 模块 / cap $10）

### Checkpoint

P1 全完成（21 个 testpoints 文件齐全）后：
1. CY review 抽样 3-4 模块
2. 主 agent 一次性 commit `dogfooding P1 done — 21 testpoints / N total`
3. 跑 phase3 数据脚本看 testpoint 数维度 baseline（D1）
4. 进 P2 case

---

## Cost 跟踪

| Session | 起 | 终 | 内容 | 累计 |
|---------|-----|-----|------|------|
| 2026-05-12 init | — | — | 00-plan + progress init | $0 |
| 2026-05-12 evening | $50（前置 sprint）| ~$52 | P0 prompts + M01 pilot | $52 |
| 2026-05-12 night | $0（新 session）| ~$3.9 | P1 批 1 (M11/M14/M19/M20) 4 并发 / 394 testpoint | $3.9 dogfooding 累计 ~$5.9 |
| 2026-05-12 night | ~$3.9 | ~$7.3 | P1 批 2 (M02/M03/M04/M05) 4 并发 / 431 testpoint | $7.3 dogfooding 累计 ~$9.3 |
| 2026-05-12 night | $0（新 session）| ~$5.7 | P1 批 3 (M06/M07/M08/M10 4 并发 + M12 单派) / 466 testpoint / 含冷启动绕路探索 ~$0.5 | $5.7 dogfooding 累计 ~$15.0 |
| 2026-05-12 night | $0（新 session）| ~$6.2 | P1 批 4 (M13/M15/M16/M17 4 并发 + M18 单派) / 671 testpoint / 5/5 escalation surface ≥100 | $6.2 dogfooding 累计 ~$21.2 |
| 2026-05-12 night | $0（新 session）| ~$1.8 | P1 批 5 _cross-cutting 单 subagent / 238 testpoint / 18 视角 / 22 元发现全转化 | $1.8 dogfooding 累计 ~$23.0 |

**预算**：sprint 总 $130-240 / dogfooding 自身已用 ~$23.0 / 剩 $107-217 / 充足。
**本 session 节流**：批 5 单 subagent / cost ~$1.8 / **远低于 $8 单 session 软上限** / context 不堆叠 / 节流红线全过。
**P1 闸门到**：21 个 testpoint 文件齐 / 2327 testpoint 总 / 风格红线全过 / 元发现 22 项全转化 / 待 CY review 抽样 3-4 模块 → 进 P2 case。

**冷启动 dogfooding 观察点（批 3 实证）**：
- ❌ 主 agent 起手把 "P1 批 3" 误解为 MEMORY.md P1 分组而非 Phase 1 批次 → 走 KB 专题 + memory 索引绕路 ~5 工具调用浪费 / 后被 CY 显式纠正"上 session 给你的提示词说 我给你发这个 你就会做"
- ✅ 但没自己脑补设计批次范围 / 用 AskUserQuestion 让 CY 显式回答 → 反 sink 元规则起作用
- 📌 **改进建议**：cold-start 主 agent 看到"cold-start" + 协议关键词（dogfooding / sprint / 批 N）应先 `find ./_handoff` 而非 grep MEMORY.md → 沉淀到 cross-session handoff 协议

---

## 阻塞 / 待 CY 拍

- 无（CY 已拍 A 路径 / P1 并行启 20 module 在新 session 跑）

## 注意事项

- 每 P1 subagent prompt 必含 cost cap $3 + 完整 8 项 input contract + Forbidden 清单
- subagent 完成后**不许 commit** / 主 agent 收齐 21 个 module 后一次性 commit
- 长 module（M17/M18/M13）testpoint 数可能 >100 / 不重做 / 接受
- 边缘 module（M11/M14/M20）若 <30 testpoint / 检查是否漏覆盖视角 / 不许凑数
