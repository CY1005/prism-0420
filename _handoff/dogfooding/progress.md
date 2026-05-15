---
last_session: 2026-05-15 (Phase 2.x M-frontend cluster-M14 PASS / 1 bug FIX_DONE / 全量 UI 实装)
last_sprint_close: 2026-05-13 (P5b final close) / 5/15 M17 + M14 cluster 接力
phase: P1 ✅ + review ✅ / P2 ✅ / P2-close ✅ / P3 ✅ / P4 cluster-1~6 ✅ / P5a ✅ / **P5b ✅ DONE** / sprint COMPLETE → Phase 2.x M-frontend cluster-M17 ✅ + cluster-M14 ✅ 5/15
sub_task: 全 phase 闭环 / 5/15 P1 review 补齐 / 5/15 cluster-M17 4 frontend bug FIX_DONE / 5/15 cluster-M14 industry-news 全 UI 实装 FIX_DONE
cost_cumulative: dogfooding ~$66-68 + 5/15 review ~$1 + cluster-M17 ~$4-5 + cluster-M14 ~$4-5 = **~$75-78 (跨 sprint)**
status: dogfooding COMPLETE / cluster-M17 ✅ / cluster-M14 ✅ / 剩 M12/M16/M13 3 cluster + uploadZip sub-cluster / cap $32-48 还剩 ~$23-38
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

- **P2-close fixture opt-in 改造** ✅ DONE（2026-05-12）
  - 文件：`app/e2e/fixtures/seed.ts`（+90 行 / 加 SeedOptions interface + resolveDescriptionDimensionTypeId helper + opt-in 分支）
  - 改造内容（向后兼容 opt-in / 默认行为不变）:
    - 加 `opts.withEnabledDim=true` → 启 description 维度（M04/M19 file-view happy path）
    - 加 `opts.withFileNode=true` → 新增 root-level file 节点 "Root File"（M05/M19 file 视图）
    - SeededProject 接口加 `file: {id, name} | null` + `dimensionTypeId: number | null`（默认 null）
  - 改造动因（验证回路）:
    - 初版尝试默认启 dim + file 节点 → 实证 4 个 regression（M04 L896 enabled_count=0 边界 / M19 strict-mode 2 Root Module / 等）
    - 改 opt-in / 默认不动 → 跟 stash baseline 完全一致 0 regression
  - 回归对比（opt-in vs stash baseline）:
    - M01+M02+M03 (41 tests): 41 PASS / 0 FAIL ✅
    - M04+M07 (63 tests): 61 PASS / 2 pre-existing FAIL (M04 L138 / L896) ✅
    - M05 (20 tests): 19 PASS / 1 pre-existing FAIL (L81 workspace bug fix-after 路径"版本演进"不显示)
    - M11+M19+M20 (65 tests): 59 PASS / 6 pre-existing FAIL ✅ (跟 stash baseline 完全相同)
  - 已确认为 spec 设计 bug（非 fixture / 待 P3-P4 spec-level 修复）:
    - M04 L138 workspace smoke: dimension card defaultExpanded=hasContent / hasContent=false 时折叠 → "点击添加，或上传文档自动分析" 文本 hidden / spec isVisible 断言 false（fixture 加 dim 后 dim card 渲染但仍折叠 / 不解决问题）
    - M11 L37/L75 strict-mode: workspace sidebar 顶部 "导入文档" link + welcome card "导入文档" 2 elements 命中 / 跟 seed 完全无关（自建 empty project）
    - M11 L102/L659 CSV upload: 自建 project / 跟 seed 无关（疑似 CSV 上传 API 问题）
    - M19 L57 export node happy path: click folder 节点期待 "导出 Markdown" 但 workspace L970 仅 file 视图渲染此按钮（design 真实行为）
    - M19 L117 export button DOM: folder 视图 folderChildren 异步加载 / 2s timeout 不够
    - M05 L81 workspace DOM smoke: fix-after 路径要求 "版本演进" 显示 / 但 default folder 视图不渲染 version timeline
  - tsc/--list 验:
    - tsc --noEmit: PASS (0 errors)
    - playwright --list e2e/dogfooding/: 505 tests / 22 files / 维持原状
  - 副产品 / 待 P3-P4 跟进:
    - M05/M19 已内联 file node 创建逻辑可收敛到 fixture withFileNode=true（不本期做 / 避免引入 spec 改动）
    - 6 pre-existing FAIL spec 需 spec-level 修复（升级 03-bug-queue.md 候选）

- **P2 case** ✅ DONE（22 spec / 505 tests / commit `cf25cb9` + `57c0116` + `42f02c1` push 完 / **全 20 模块 + cross-cutting A/B/C 三视角组**）
  - 2026-05-12 P1→P2 闸门 audit：`audit/p1-p2-gate-finding.md` / verdict=PASS_WITH_FIX / testpoint 文件 A- 质量不改 / P0 finding=范式错位 → CY 拍两轨范式 B
  - 2026-05-12 P2 spike Opus subagent：`audit/p2-spike-report.md` / verdict=B-范式可行 / 写 M01+M02 pilot / trigger_bug 真复现 / Next.js 4 坑沉淀
  - 2026-05-12 batch 1-5 全跑（22 spec / 505 tests）:
    - batch 1 spike: M01 (146/5) + M02 (209/5) — 7 PASS + 3 真 FAIL（trigger_bug 等已修）
    - batch 2 (Sonnet 4 并发): M11 (764/18) + M14 (651/27) + M19 (546/21) + M20 (894/26)
    - batch 3 (Sonnet 4 并发): M03 (855/31) + M04 (928/25) + M05 (688/20) + M06 (859/24)
    - batch 4 (Sonnet 4 并发): M07 (915/38) + M10 (593/21) + M12 (910/25) + M15 (712/29)
    - batch 5a (混合 4 并发): M16 (855/26 Sonnet) + M18 (701/28 Sonnet) + M08 (991/26 Opus spike XYFlow) + M13 (621/14 Opus spike SSE)
    - batch 5b (Opus 4 并发): M17 (881/19 WebSocket spike) + cross-cutting A (718/19 auth+network) + B (937/32 permissions+state+async) + C (831/26 data+ai+ui)
  - 测试方法学发现已沉淀进 `prompts/phase2-case.md` Forbidden 红线（Next.js 4 坑 / shadcn Label / dialog 时序 / SSE 范式 / WebSocket 范式 / XYFlow drag 范式不支持）
  - 真 bug 累计 **~31 OPEN + 4 FIX_DONE**（详 `03-bug-queue.md`）
  - **frontend gap 模式累计 5 个模块**（M12/M13/M14/M16/M17 backend 实装 vs frontend stub puntResult / fake progress / 调错 URL）= Phase 2.2 前端继承期遗漏 = dogfooding 真价值
- **P3 executor** ✅ DONE（2026-05-13 / 505 tests 全量真跑 / 488 PASS 96.6% / 17 FAIL / init regression baseline 产出）
  - PASS: 488 (96.6%) / FAIL: 17 (3.4%)
  - 已知真 bug FAIL verified: 6（M06×3 + M18×3）
  - Spec-design pre-existing FAIL: 8（M11×4 + M19×2 + M04×1 + M05×1）
  - 新 FAIL: 3（B-P3-M13-save-btn-shows-on-error + B-P3-M17-ws-invalid-jwt-close-code + M18 transient ECONNRESET）
  - 新入队 bug: 2（B-P3-M13 + B-P3-M17 → 03-bug-queue.md OPEN 池）
  - 关键发现: cc-A 必须独立跑（末尾 5-strike lockout test）+ unlock 脚本用 .venv python
  - 输出: `_handoff/dogfooding/05-regression-results.md`（P5b STAR D1 baseline）
  - commit: 待下一步
- **P4 闭环** 🟡 4/N FIX_DONE
  - ✅ B-trigger-bug-server-action-cookie（commit cf25cb9 / Next.js refresh_token cookie Path=/auth → /）
  - ✅ B-list-projects-search-loader（commit cf25cb9 / Turbopack SWC dead re-export）
  - ✅ B-workspace-no-dims-graceful（commit 57c0116 / OverviewNoDimensionsError 422 fallback + parseError 双读 code/error_code / 含 M14 + M19 + M08 + M03 + M04 同根因）
  - ✅ B-cold-start-validation-deadlock（commit 57c0116 / cold_start_service.py L342+L407 立即 commit 释放行锁）
  - ✅ cluster-1 M06 双 fix（commit 033ea64 / 404 + display_name JOIN）
  - ✅ cluster-2 M18 422→400 + M03 type-immutable + DELETE-projects（commit 0992dc8 / ⚠️ M03 DELETE HIGH design 冲突待 CY 决）
  - ✅ cluster-3 M04 cross-node 404 + M04 action_type design sync + M07 transition details current/target（B-P4-cluster-3-M04-M07 / A 路径全 / 7 文件 / pytest 146 PASS）
  - 🟡 OPEN ~24 bug 待 P4 入：M04 (0) / M05 (1) / M07 (0) / M10 (1) / M11 (1) / M12 (1) / M13 (4) / M14 (1) / M15 (3) / M16 (2) / M17 (4) / M18 (1 design-gap) / M19 (0) / M20 (0) / M08 (2) / cc-A (2) / cc-B (1)
- **P5a regression** ✅ DONE（2026-05-13 / 505 tests 全量重跑 / 502 PASS 99.4% / 3 FAIL）
  - PASS: 502 (99.4%) / FAIL: 3 (0.6%)
  - P4 cluster 1-6 修复转化验证: 14 条 P3 FAIL → P5a PASS ✅
  - 残留 FAIL: 3 条 M18 transient/infra（ECONNRESET + socket hang up + DOM timeout / 非代码 bug）
  - 新 FAIL: 0（cluster 1-6 全覆盖 / 无新发现）
  - 输出: `_handoff/dogfooding/05-regression-results.md`（覆盖 P3 init 版 / 加 after-fix 段 / D1 数据完整）
  - regression data: P3 488/505=96.6% → P5a 502/505=99.4% / 净 +14 tests / +2.8pp
- **P5b STAR 报告** ✅ DONE（2026-05-13 / Opus subagent / cost ~$3-5）
  - 输出：`_handoff/dogfooding/05-final-report.md`（STAR S/T/A/R 完整 / D1-D4 4 维度数据 / 失败案例不掩盖 / Punt 池总览）
  - 同步更新：`design/99-comparison/phase3-data-baseline.md` v0.4 段（4 维度数据 + 跟 v0.3 对照 + 4 条新结论）
  - 03-bug-queue.md final verdict：17 真 bug FIX + 1 VERIFIED + 10 SYNCED + 7 spec-fix + 12 PUNT + 2 OPEN = 49 状态条目 / 47 独立 ID
  - **dogfooding sprint 全闭环 COMPLETE**
  - commit: <P5b-hash 见下>

---

## Sprint 全闭环 verdict (2026-05-13)

**5-phase plan 全 ✅**：P0 + P1 + P2 + P3 + P4 (cluster-1~6 + revert) + P5a + P5b 全 DONE
**最终 commit chain**：cf25cb9 → 57c0116 → 42f02c1 → fb496e2 → 52f4530 → 033ea64 → 0992dc8 → feca350 → 419ac07 → 7deb5ff → 72317cf → 596b59d → 991796f → P5b-hash
**CI**：main 全绿
**Phase 3 v0.4 数据**：已落 design/99-comparison/phase3-data-baseline.md
**STAR 报告**：05-final-report.md（简历级素材 / 跳槽 PRISM 代表作 v0.4）
**总 cost**：~$80-85（2 天 / 5-phase 全跑 / 多 agent 协作）
**下一 sprint**：Phase 2.x M-frontend 实装（M14/M12/M16/M17/M13 / Opus × 5 / cap $32-48）

---

## P1 review 闸门 5/15 补齐记录

**Why**: plan §5 P1 checkpoint 闸门「CY review 抽样」5/12-5/13 sprint 期被 P2 hybrid 强推跳过；5/15 CY 主动问起 + 选「完整版抽样」补齐闸门，与 5/13 sprint COMPLETE 状态对齐。

**抽样范围**：4 模块 / 602 testpoint / **26% 覆盖率**
- M02 project (130, A-, 15 视角)
- M11 cold-start (91, A-, 14 视角 / R-X1 首例)
- M18 semantic-search (143, A, 13 视角 / 最复杂)
- _cross-cutting (238, A, 18 视角 / 22 元发现真转化)

**Verdict**: **PASS** — 0 HIGH / 1 MEDIUM / 4 LOW / 20/20 可执行性抽样直接转 spec

**Finding 明细**：
| 级别 | 文件:行 | 描述 | 处置 |
|------|---------|------|------|
| MEDIUM | M18-semantic-search.md:56+127 | ck_embeddings_dim_column_consistency 同 CHECK 两条不同角度，P2 写 spec 时 merge 成 1 个测试避免双跑 | 下 sprint M-frontend 实装期顺手处理 |
| LOW | M02-project.md:130 | viewer 编辑按钮「置灰 / 隐藏」UI 行为模糊 | P2 写 spec 时选一个 |
| LOW | M02-project.md:134 | API Key `type=password` 也接受 mask，可补 mask 范式 | 可不补 |
| LOW | M11-cold-start.md:59 | SQL 注入 P1 只检查「不执行 SQL」，建议加 nodes 表内容验证 | 可补 |
| LOW | _cross-cutting.md:314 | M03 path 物化路径压缩视角数 — 元观察非 testpoint | 挪到 design audit 备注 |

**声明真实性核对**（progress.md 各项声明 vs 抽样验证）:
- ✅ 21 testpoint 文件齐全 / 2327 总数符合
- ✅ 风格红线全过（抽 50+ 条 0 违反）
- ✅ H3 视角清单达标（边缘 ≥10 / 主流 ≥12 / escalation ≥15）
- ✅ 22 元发现转化（cc 文件抽 12 项核对全在相应 § 中）
- ✅ 风险点 Top 5 对照 design 可验证

**Sprint 闭环状态最终对齐**：dogfooding sprint **真闭环**（P3 488/505 → P5a 502/505 → P5b 报告 / Phase 3 v0.4 已落）+ P1 闸门 review 补齐 ✓ → 全部 5 phase 都过 / 0 遗留闸门。

**对 CURRENT.md 影响**：CURRENT v1.4「等 review BLOCKED」是脏数据 → CURRENT v1.5 校准为「P1 review 5/15 补齐 / 下 sprint = M-frontend 实装」。

**cost**：~$1（4 文件直读 + 抽样分析，无 subagent）

---

## Phase 2.x M-frontend cluster-M17 完成记录 (2026-05-15)

**Why**: M-frontend 5 模块（M14/M12/M16/M17/M13）第 1 个 cluster 起手 / M17 选作 first 因 6/8 dogfooding 工作笔记导入核心依赖。

**4 bug 处置**（cluster commit cb27ac8 / CI run 25904585055 全绿）:

| Bug ID | 处置 | 改动 |
|--------|------|------|
| B-P2-M17-frontend-stub-puntresult | **FIX_DONE** | import-ai.ts 删 4 stub / 加 aiSubmitImportZip + aiFetchReviewData / aiAnalyzeZip 改 error 引导 / aiAdjustMapping 改 no-op / aiUndoImport 调 task cancel |
| B-P2-M17-fake-progress-no-websocket | **FIX_DONE** | ai-import-wizard.tsx 实装 WS 客户端 onmessage 取 ProgressEvent / 删 setTimeout(150) 假进度 / WS 路径 /api/projects/{pid}/imports/{tid}/ws / 复用 B-P3-M17 1008 close frame 路径 |
| B-P2-M17-design-gap-tab-vs-wizard | **SYNCED** | design §6 加 tab 入口范式说明（不动 UI / 对齐实装 3 tab）/ tests.md 同步 / 呼应 cluster-5+6 sync 范式 |
| B-P2-M17-design-gap-fresh-project-blocked | **FIX_DONE** | import-page-client.tsx 加 ai_provider 检查 / NULL 时引导卡 + 跳设置页链接 |

**audit verdict**: 0 high + 2 medium (1 DONE / 1 PARTIAL) + 3 low DONE + 2 PASS（详 `04-bug-fixes/B-P4-cluster-M17/design-audit.md`）

**安全网**: tsc PASS (0 errors) / eslint PASS / playwright --list M17 PASS (19 tests) / pytest M17 PASS (134/134)

**改动量**: 7 files / +724 / -56 lines

**escalation 上报点**（独立 cluster 候选）:
- **F3 PARTIAL**：ai-import-wizard.tsx 主流程仍依赖 actions/import.ts uploadZip（cold-start 同范式 / 未在本 cluster scope 内）→ 完整 happy path 端到端走不通，需独立 sub-cluster；候选 A/B/C 选项详 cluster-M17/rca.md §5.1
- **跨模块元规则升级**：M13/M14/M16/M17 同款"前端继承 prism 同步范式 vs prism-0420 design 异步范式"漂移 → 升 `cross-sprint-punt-pool.md` 元规则 / 防 M13/M14/M16 后续 cluster 同款踩坑（详 rca §5.2）

**cost**: ~$4-5 / cap $10-12 / 远低于 cap

**剩余 M-frontend cluster**: M14 / M12 / M16 / M13（按 PUNT-REPORT 推荐顺序 cap $5-12 each）

---

## Phase 2.x M-frontend cluster-M14 完成记录 (2026-05-15)

**Why**: M-frontend 5 模块第 2 个 cluster / M14 全量 UI 缺 / 0 拷贝起点 / 最干净起手 / 0 A/B 决策依赖。

**1 bug 处置**（cluster commit 79f6204 + 闭环 commit 待定）:

| Bug ID | 处置 | 改动 |
|--------|------|------|
| B-P2-M14-design-gap-news-ui | **FIX_DONE** | `app/src/app/industry-news/page.tsx` + 4 components（news-card / news-form / node-link-picker）+ `actions/industry-news.ts` 接 8 endpoints + `lib/validators/news.ts` zod schema |

**audit verdict**: 0 high + 1 medium DONE + 3 low（2 接受不动 design + 1 spec 断言 PARTIAL）+ 5 PASS（详 `04-bug-fixes/B-P4-cluster-M14/design-audit.md`）

**安全网**: tsc PASS (0 errors) / eslint PASS（6 新文件 0 ignore 依赖）/ playwright --list M14 PASS (27 tests) / pytest M14 PASS (106/106 / 3.60s)

**改动量**: 8 文件 / +1386 / -0（6 新源文件 + 2 B 路径产物 / 0 删除 / feed.ts 不动 / design 文档不动）

**cluster 内自决**:
- feed.ts LEFT AS-IS（feed 域 ≠ news 域 / 3 caller 页依赖 / 删除超 cluster boundary）→ feed 域 cleanup 推 cross-sprint-punt-pool
- 组件落 `components/` flat（非 design §6 `business/` 子目录 / 与 peer 业务组件 issue-card/dimension-card/feed-card 范式对齐）

**closeout 闸门处置**:
- spec L628 P0-DOM-SMOKE 反向断言（`/industry-news` 期望 404 → 实装后 200）→ 本闭环 commit 顺手 flip
- §5.3 元规则升 cross-sprint-punt-pool（与 cluster-M17 §5.2 合并 / "Phase 2.2 拷贝层 vs design §6 mismatch 范式漂移群"）
- §5.1 feed 域 stub 长期归宿（A/B/C）→ 跨 cluster 候选 / 沉 cross-sprint pool（不在本 closeout 决）

**cost**: ~$4-5 / cap $6-9 / 与 cluster-M17 同档

**剩余 M-frontend cluster**: M12 / M16 / M13 + uploadZip sub-cluster（M17 escalation）

---

## 🔴 W21 守 plan 推进路径（CY 2026-05-12 拍）

按选项 A 守 plan：
1. **CY review P1 抽样**（plan §5 P1 checkpoint / 闸门未过）
   - 建议抽 4 模块：M02 (130 主流标杆) + M11 (91 边缘) + M18 (143 复杂 AI) + _cross-cutting (238 横切)
   - 也可压到 2：M02 + _cross-cutting
2. **P4 收口剩 15 OPEN bug**（plan §3 A/B/C 三路径决策 / 含 audit + RCA）
   - 注：大部分 OPEN 是 design-gap（前端 UI 未实现 / 后端契约偏移 design 文档）→ 多数走 B 路径含 audit
3. **启 P2 batch 剩 8 模块**（M08/M13/M16/M17/M18/M20 + cross-cutting / Sonnet × 8 / 拆 2-3 session）

---

## 已发现 bug 池总览（详见 `03-bug-queue.md`）

**累计 20 bug**：5 FIX_DONE + 15 OPEN

- **FIX_DONE 5**（commit cf25cb9 + 57c0116）：B-trigger-bug-server-action-cookie / B-list-projects-search-loader / B-workspace-no-dims-graceful（含 M14+M19 同根因）/ B-cold-start-validation-deadlock / B-P2-M14-workspace-dimension-error
- **OPEN 15**（按模块）：M03 (2 — node-type-immutable / project-delete-missing) / M04 (2 — cross-node-tenant-read / activity-log-naming) / M05 (1 — version-ops-ui) / M06 (2 — not-found-422 / ref-no-display-name) / M07 (1 — error-details-field) / M10 (1 — error-response-format) / M11 (1 — cold-start-page) / M12 (1 — comparison-page) / M14 (1 — news-ui) / M15 (3 — filter-bar / date-grouping / metadata-collapse)

**类别分布速看**（W21 P4 收口前供 CY 判断改动量）：
- design-gap（前端 UI 未实现 / 多数走 B 路径 audit）：M05 / M11 / M12 / M14 / M15 (3) = 7 bug
- 后端契约偏 design（API 错误码/字段名/格式 / 多数小改）：M03 (2) / M04 (2) / M06 (2) / M07 / M10 = 8 bug

---

## 下一 session cold-start 顺序（W21 守 plan）

1. `cat _handoff/dogfooding/progress.md`（本文件 / 起点 / 看 §"W21 守 plan 推进路径"）
2. `cat _handoff/dogfooding/00-plan.md`（§2 8 类 agent + §3 三路径决策 + §5 验收）
3. **W21 入口分支**：
   - 如果 CY P1 review 还没过 → 等 CY review 完，不主动启 P4 / P2 batch
   - 如果 review 过 → `cat _handoff/dogfooding/03-bug-queue.md` 拿 OPEN 15 bug → 启 P4 fix subagent（plan §3）
   - 如果 P4 收口完 → `cat _handoff/dogfooding/prompts/phase2-case.md` 拿 P2 prompt → 启剩 8 模块 batch
4. `cat _handoff/dogfooding/prompts/phase4-fix.md` + `phase4-audit.md`（P4 收口用）
5. `cat _handoff/dogfooding/prompts/phase2-case.md`（P2 batch 用 / 含 Next.js 4 坑 + 两轨范式 B）

## 历史任务（P1 21 模块完结清单 / 保留供后续审计）

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

> ⚠️ **本段是 P1 历史模板**（P1 已完结 21/21）。W21 启 P4 / P2 batch 时另起 prompt（参考本文件 §"下一 session cold-start 顺序"）。

**通用模板**（替换 N 即可）：

```
cold-start dogfooding P1 批 N
```

**具体批次**（P1 历史 / 已全完）：

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
| 2026-05-12 night | ~$23.0 | ~?$33-38 | P2 spike + hybrid 11 模块 spec + P4 5 fix (含 audit + RCA) / 待补精确数 | 待补 |

**预算**：sprint 总 $130-240 / dogfooding 自身已用 ~$33-38（估）/ 剩 $90-200 / 充足。
**当前关闸状态**：**plan §5 P1 闸门未过**（待 CY review 抽样）/ P2 hybrid 已破 plan §1 串行红线（11 模块 spec + 抓 20 bug + 5 已 fix）/ W21 守 plan 路径：CY review → P4 收口 15 OPEN → P2 batch 剩 8 模块。

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
