---
module: M05
name: version-timeline
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M05-version-timeline/00-design.md
  - design/02-modules/M05-version-timeline/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F5 版本演进时间线（US-B1.5 / US-C1.4）
---

# M05 版本演进时间线 测试点

## 业务流程（H1 / 1 行概述）

M05 围绕 `version_records` 表（冗余 project_id）做 CRUD + set_current 互斥切换，6 个 endpoint（GET 列表 / GET 单条 / POST 创建 / PUT 元数据 / DELETE / POST set-current），三层权限防御（Server Action / Router viewer-or-editor / Service `_check_node_belongs_to_project`），DB 部分唯一索引 `uq_version_node_is_current` 在 commit 时兜底"同 node 至多 1 个 is_current=true"。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /versions 编辑者 happy path 返 201 + is_current=false + activity_log 写 version_record_created（design §7 + §10 + tests.md G1）
- [P0] GET /versions 返 items 按 created_at DESC 排序 + total 字段正确（design §6 对外契约 + §9 DAO + tests.md G2）
- [P0] GET /versions/{version_id} 返单条版本详情含所有 schema 字段（design §7 VersionResponse + tests.md G3）
- [P0] PUT /versions/{version_id} 改 summary 返 200 + updated_at 推进 + activity_log 写 version_record_updated metadata.changed_fields（design §10 + tests.md G4）
- [P0] POST /versions/{version_id}/set-current 返 200 + 该 version is_current=true + 同 node 其余 is_current 全 false + activity_log 写 version_record_set_current（design §9 set_current 范式 + §10 + tests.md G5）
- [P0] DELETE /versions/{version_id} 返 204 + activity_log 写 version_record_deleted metadata.was_current 反映删除前状态（design §10 + tests.md G6）
- [P1] POST /versions 携带 is_current=true 先 clear 旧 current 再 INSERT 新行为 current（design §9 set_current 范式 + service.create line 154-155）
- [P1] POST /versions 携带 snapshot_data dict 持久化 JSONB 字段（design §1 边界灰区 + §3 snapshot_data）
- [P1] GET /versions limit 参数控制返回条数（service.list_by_node limit 参数 + design §6 R-X3）
- [P1] PUT /versions/{version_id} fields 全空 dict 返 200 + 不写 activity_log（service.update_metadata line 215-217 no-op 语义）
- [P1] PUT /versions/{version_id} 同时改 summary + details + change_type + release_mode 一次写入 activity_log（design §10 单条 update 事件）
- [P1] DELETE 当前 is_current=true 版本 metadata.was_current=true（service.delete line 255 + design §10）
- [P1] DELETE 非当前 is_current=false 版本 metadata.was_current=false（design §10）

### 2. 边界 / 状态机

- [P0] 同一 node 任意时刻最多 1 条 is_current=true（design §4 业务约束 + §3 uq_version_node_is_current 部分唯一索引兜底）
- [P0] POST 带 is_current=true 时事务原子先 clear 旧 current 再 INSERT 新（design §3 Alembic 要点 + service.create line 154）
- [P1] version_label 长度 1 字符通过（schema min_length=1 + tests.md E1 反向边界）
- [P1] version_label 长度 64 字符通过（schema max_length=64 + tests.md E2 边界）
- [P1] version_label 长度 65 字符返 422（schema max_length=64 + tests.md E2）
- [P1] summary 长度 1 字符通过（schema min_length=1）
- [P1] summary 长度 500 字符通过 / 501 字符返 422（schema max_length=500）
- [P1] change_type 枚举 6 值（added/modified/deprecated/split/merged/migrated）均接受（design §3 CheckConstraint + schema Literal + tests.md E4）
- [P1] release_mode 枚举 release/continuous 均接受（design §3 CheckConstraint + schema Literal）
- [P1] M05 显式声明无状态机仅 is_current 布尔标记（design §4 R4-1 显式声明）
- [P2] count_by_node 对节点 0 条版本返 0（design §6 R-X3 + service.count_by_node）

### 3. 异常 / 错误

- [P0] POST /versions 重复 (node_id, version_label) 返 409 VERSION_LABEL_DUPLICATE（design §13 + tests.md E3 + service.create IntegrityError catch line 158-173）
- [P0] GET /versions/{不存在 version_id} 返 404 VERSION_NOT_FOUND（design §13 + tests.md E6）
- [P0] DELETE /versions/{不存在 version_id} 返 404 VERSION_NOT_FOUND（design §13 + tests.md E6 + service.delete line 252）
- [P0] PUT /versions/{不存在 version_id} 返 404 VERSION_NOT_FOUND（service.update_metadata line 211 / get_by_id 前置）
- [P0] POST /versions/{不存在 version_id}/set-current 返 404 VERSION_NOT_FOUND（service.set_current line 292）
- [P0] POST /versions summary="" 返 422 Pydantic min_length 校验失败（design §7 + tests.md E1）
- [P0] POST /versions version_label 超 64 字符返 422（schema max_length + tests.md E2）
- [P0] POST /versions change_type="unknown" 返 422 Pydantic Literal 枚举校验（schema ChangeType + tests.md E4）
- [P1] POST /versions snapshot_data 传字符串非 dict 返 422 Pydantic dict 校验（design §7 + tests.md E5）
- [P1] PUT /versions/{version_id} 试图传 snapshot_data 字段被 Pydantic 自动拒绝（design §7 决策 Q3 + schema VersionUpdate 无此字段 + extra 默认 ignore 或 forbid 二者均不写库）
- [P1] PUT /versions/{version_id} summary="" 返 422 Pydantic min_length=1 校验（design §7 R2 P1-03 + schema VersionUpdate.summary min_length=1）
- [P1] POST /versions node_id 路径 UUID 在 nodes 表不存在返 404 VersionNotFoundError reason=node_not_in_project（service._check_node_belongs_to_project line 70）
- [P1] POST /versions/{version_id}/set-current 节点已 soft-delete 后调用返 404（service get_by_id 前置 + design §6 tenant 链条）
- [P2] DB 临时不可用调 POST /versions 返 500 + 不暴露 stacktrace（design §13 ErrorCode + framework 中间件）
- [P2] node_id 路径非 UUID 格式返 422（FastAPI path param 自动校验）
- [P2] project_id 路径非 UUID 格式返 422（FastAPI path param 自动校验）

### 4. 权限 / Auth

- [P0] 未登录调 GET /versions 返 401 UNAUTHENTICATED（design §8 Server Action 层 + tests.md P1）
- [P0] viewer 角色调 GET /versions 返 200（design §8 + tests.md P3 + router line 51 role="viewer"）
- [P0] viewer 角色调 POST /versions 返 403 PERMISSION_DENIED（design §8 + tests.md P2 + router line 88 role="editor"）
- [P0] viewer 角色调 PUT /versions/{version_id} 返 403 PERMISSION_DENIED（design §8 + router line 114 role="editor"）
- [P0] viewer 角色调 DELETE /versions/{version_id} 返 403 PERMISSION_DENIED（design §8 + router line 136 role="editor"）
- [P0] viewer 角色调 POST /versions/{version_id}/set-current 返 403 PERMISSION_DENIED（design §8 + router line 155 role="editor"）
- [P0] editor 角色调 POST /versions/{version_id}/set-current 返 200（tests.md P4）
- [P1] check_project_access 用户对该 project 无任何角色返 403（design §8 Router 层）
- [P1] 过期 JWT 调任一 endpoint 返 401（M01 ADR-004 #5 + design §8 Server Action 层）
- [P2] platform_admin 跨项目访问该模块 endpoint 行为（M01 admin role 横切 / 本模块未显式标注）

### 5. Tenant 隔离

- [P0] userA projectA token 访问 projectB 的 /versions 返 403 PERMISSION_DENIED Router 拦截（design §8 + tests.md T1）
- [P0] userA projectA 路径调 GET /versions/{属于 projectB 的 version_id} 返 404 不暴露 forbidden（DAO tenant 过滤 design §9 + tests.md T2）
- [P0] userA projectA 路径调 DELETE /versions/{属于 projectB 的 version_id} 返 404（service.get_by_id project_id 过滤 + tests.md T4）
- [P0] userA projectA 路径调 PUT /versions/{属于 projectB 的 version_id} 返 404（service.get_by_id project_id 过滤）
- [P0] cross-tenant node_id 攻击：path project_id=A node_id=B（B 属于 projectC）调任一写 endpoint 返 404 reason=node_not_in_project（service._check_node_belongs_to_project line 69-70）
- [P1] count_by_node 对 cross-tenant node_id 返 404 而非静默 0（design §6 R1-C P1-02 立修 + service.count_by_node line 95）
- [P1] DAO 单元测 version_dao.list_by_node(other_project_id) 返空 list（tests.md T3 + design §9）
- [P1] DAO 单元测 version_dao.get_one(version_id, wrong_project_id) 返 None（design §9 get_one 范式）
- [P1] DAO clear_current_flag 仅清当前 (node_id, project_id) 范围 / 不影响其他 project 的 is_current 标记（design §9）
- [P1] M05 所有 DAO 方法签名强制 project_id 参数无豁免（design §9 豁免清单空）

### 6. 并发 / 乐观锁

- [P0] 同一 node 两并发 POST /versions 相同 version_label 一个 201 一个 409 VERSION_LABEL_DUPLICATE（UNIQUE uq_version_node_label + service IntegrityError catch line 158-173）
- [P0] 同一 node 两并发 POST set-current 不同 version_id：DB 部分唯一索引 uq_version_node_is_current 在 commit 时兜底其中一者失败返 ConflictError（design §3 + service.create line 165-168）
- [P0] 同一 node 两并发 POST /versions 都带 is_current=true：先 clear→INSERT 路径 race 下其中一者命中 uq_version_node_is_current 抛 ConflictError 提示"另一并发请求已设当前版本"（service.create line 165-168 R1-C P1-01）
- [P1] M05 无 version 乐观锁字段 / 版本记录非多人并发编辑场景（design §5 4 维必答并发=N/A）
- [P1] 同一 version_id 并发 PUT + DELETE：UPDATE 走 dao.update_metadata rows=0 抛 VersionNotFoundError（service.update_metadata line 219-222 race 处理）
- [P1] 同一 version_id 并发 DELETE + set-current：DELETE 后 set_current 走 get_by_id 抛 VersionNotFoundError（service.set_current line 292）

### 7. 数据完整性

- [P0] version_records.project_id 冗余字段写入时 service 强制 = node.project_id（design §3 一致性兜底）
- [P0] CHECK ck_version_change_type 仅允许 6 枚举值 / INSERT change_type="invalid" DB 层失败（design §3 R3-2 + Alembic 要点）
- [P0] CHECK ck_version_release_mode 仅允许 release/continuous / INSERT release_mode="invalid" DB 层失败（design §3 R3-2）
- [P0] UNIQUE uq_version_node_label (node_id, version_label) 防同 node 重名版本（design §3）
- [P0] uq_version_node_is_current 部分唯一索引 WHERE is_current=true / 同 node 仅 1 条 is_current=true 可存（design §3 + §4）
- [P0] FK nodes.id ON DELETE CASCADE / 删 node 行其 version_records 级联删除（design §3）
- [P0] FK projects.id ON DELETE CASCADE / 删 project 行其 version_records 级联删除（design §3 冗余 tenant FK）
- [P1] version_records.created_at / updated_at 由 TimestampMixin 自动填充（design frontmatter mixins）
- [P1] created_by FK users.id nullable（design §3 / 用户被删除场景 SET NULL 或保留 NULL）
- [P1] ix_version_node_proj_created (node_id, project_id, created_at DESC) 索引存在（design §3 Alembic 要点）
- [P1] ix_version_project (project_id) 索引存在 / 用于 tenant 过滤（design §3）
- [P1] snapshot_data JSONB 字段可存任意 dict / 读出来字段顺序 / 嵌套结构保留（design §3 + §1 边界灰区）

### 8. UI / UX

- [P1] 时间线 UI 按 created_at DESC 渲染最新版本在上（design §6 R1-A P1-1 + tests.md G2）
- [P1] 版本卡片展示 change_type 变更类型标签（added/modified/deprecated/split/merged/migrated 6 种 design §1 + §6 Component）
- [P1] 当前版本 is_current=true 在 UI 上有"当前"高亮标记（design §1 In scope）
- [P1] 创建版本弹窗 version_label 输入框 max-length=64 前端校验（design §7 + schema 长度）
- [P1] 创建版本弹窗 summary 必填 / placeholder 提示（schema min_length=1）
- [P2] 删除当前版本前端确认弹窗（破坏性操作 UX）
- [P2] set-current 操作成功后前端 toast"已标记为当前版本"+ 自动刷新列表（design §7 endpoint）

### 9. 性能 / 容量

- [P1] count_by_node 复用 ix_version_node_proj_created 走 PG index-only scan p95 < 5ms（design §6 性能验收 + R-X3）
- [P1] list_by_node ordered scan 命中 ix_version_node_proj_created 索引 + tenant 过滤一索引覆盖（design §3 Alembic 要点 P1-2）
- [P2] node 下版本数 ≥ 100 时 list endpoint 响应时间不退化（design §6 typical node ≤100 versions 假设）
- [P2] activity_log 单月写入量随 version CRUD 频次膨胀 / 监控阈值（design §10 + 横切 M15）

### 10. activity_log 事件完备性

- [P0] create 路径写 1 行 version_record_created metadata 含 node_id/version_label/change_type/is_current（design §10 + service.create line 176-190）
- [P0] update 路径写 1 行 version_record_updated metadata.changed_fields 反映改了哪些字段（design §10 + service.update_metadata line 226-239）
- [P0] delete 路径写 1 行 version_record_deleted metadata.was_current 反映是否删的当前版本（design §10 + service.delete line 263-276）
- [P0] set-current 路径写 1 行 version_record_set_current metadata.previous_current_id 反映原 current id 或 null（design §10 ER4 + service.set_current line 306-319）
- [P1] 创建失败回滚（IntegrityError）不写 activity_log（service.create line 156-173 catch 在 write_event 之前 + autobegin 回滚 design docstring）
- [P1] PUT 无字段更新 fields={} no-op 不写 activity_log（service.update_metadata line 215-217）
- [P1] activity_log target_type="version_record" / target_id=version_id 字段稳定（design §10）
- [P2] activity_log 事件被 M15 数据流转模块消费 / cross-module 契约（design §2 依赖图 -.事件.->M15）

### 11. ErrorCode / 错误响应规范

- [P1] VERSION_NOT_FOUND 错误 http_status=404 / 响应体 {"error":{"code":"version_not_found","message":...}}（design §13 + tests.md ER2）
- [P1] VERSION_LABEL_DUPLICATE 错误 http_status=409 / 响应体含 code=version_label_duplicate（design §13 + tests.md ER1）
- [P1] VERSION_SNAPSHOT_INVALID 错误 http_status=422 / 响应体含 details 子段（design §13 + tests.md ER3）
- [P1] set-current 时原 current 已被删的边缘场景 clear_current_flag 无记录正常 200 + previous_current_id=null（tests.md ER4 + service.set_current line 296-297）
- [P2] ErrorCode 枚举行数 == AppError class 定义行数 CI 守护（design frontmatter R13-1 + M01 CI grep 守护 3）

### 12. 跨模块契约（M05 是被依赖源头）

- [P1] VersionService.list_by_node 对外契约接受外部 db session（design §6 R-X3 + service line 74）
- [P1] VersionService.count_by_node 对外契约接受外部 db session 不开事务不写 activity_log（design §6 R-X3 + service line 89）
- [P1] M16 AI 快照消费 snapshot_data JSONB 字段 / 字段命名稳定（design §1 边界灰区 + §2 依赖图）
- [P1] M15 数据流转模块订阅 version_record_created/updated/deleted 4 个 action_type（design frontmatter produces_action_types）
- [P2] M04 维度内容回滚未实装本期 / set-current 不自动写回维度（design §1 Q5 决策 A 否）

### 13. 设计漂移 / CI 守护

- [P1] service 层 INSERT 路径 except IntegrityError 段存在（design-principles 清单 6 + service.create line 158）
- [P1] DAO 层全部查询带 tenant 过滤 / CI 扫描 version_dao.py 无裸 WHERE id= 缺 project_id（design §9 + design-principles 清单 5）
- [P1] PUT router 用 model_dump(exclude_unset=True) 不用 exclude_none（design-principles partial update 附录 L1-α + router line 119）
- [P1] design §3 sample "with db.begin():" 与实装 "Router 层管 commit / service autobegin" 不一致 / sprint 关闸 audit 立修 docstring 范式（service docstring line 3-12 R1-A P1）
