---
module: M02
name: project
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M02-project/00-design.md
  - design/02-modules/M02-project/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
  - design/adr/ADR-001-shadow-prism.md
prd_ref: F2 项目管理（US-A1.1/A1.2/A1.3/A1.4/A2.1/A2.3/C2.1）
---

# M02 项目管理 测试点

## 业务流程（H1 / 1 行概述）

M02 是系统 tenant 锚点：owner 创建项目（多表事务：projects + project_members[owner] + project_dimension_configs + activity_log）/ 邀请成员（依赖 DB UNIQUE 防重）/ 配置维度 / 配置 AI Provider（AES-256-GCM 加密 API Key）/ 归档（active→archived 不可逆终态，不级联子模块）；下游 M03-M20 全通过 project_id 引用。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects owner 创建项目 201 返 projects+project_members(owner)+project_dimension_configs+activity_log[create] 全部落库（design §5 多表事务 + tests.md G1）
- [P0] GET /api/projects 列表仅返当前用户是 project_members 的 active 项目（design §9 list_by_user + tests.md G2）
- [P0] GET /api/projects/{pid} 项目详情 200 含 hierarchy_labels / template_type / version_mode 字段且不含 ai_api_key_enc（design §7 ProjectResponse + tests.md T1）
- [P0] PUT /api/projects/{pid} owner 更新 name/description 200 + activity_log[update] 含 changed_fields（design §10 + tests.md G6 派生）
- [P0] POST /api/projects/{pid}/archive owner 归档 200 status=archived + activity_log[archive] previous_status=active（design §4 状态机 + tests.md G5）
- [P0] POST /api/projects/{pid}/members owner 邀请成员 201 写 project_members 行 + activity_log[invite_member]（design §10 + tests.md G3）
- [P0] PUT /api/projects/{pid}/members/{uid} owner 变更角色 editor→viewer 200 + activity_log[update_member_role] 含 old_role/new_role（design §10 + tests.md G4）
- [P0] DELETE /api/projects/{pid}/members/{uid} owner 移除非 owner 成员 204 + activity_log[remove_member]（design §10 + tests.md G7）
- [P0] PUT /api/projects/{pid}/dimension-configs 批量更新 200 每条变更 config 写独立 activity_log[update_dimension_config]（design §10 R10-1 + tests.md G6）
- [P0] PUT /api/projects/{pid} 含 ai_api_key 明文写入 200 + DB ai_api_key_enc AES-256-GCM 密文 + 响应体不含明文（design §3.Z + tests.md E4）
- [P1] PUT /api/projects/{pid} 含 ai_provider="claude" 写入 200 + activity_log[update_ai_provider] new_provider 含值不含 api_key（design §10）
- [P1] GET /api/projects/{pid}/members 列表 200 含每条 user_name/user_email join 字段（design §7 MemberResponse）
- [P1] GET /api/projects/{pid}/dimension-configs 列表 200 每条含 dimension_type_key/dimension_type_name join 字段（design §7 DimensionConfigResponse）
- [P1] POST /api/projects template_type="custom" 默认 hierarchy_labels=["层级1","层级2","层级3"]（design §3 model default）
- [P1] ProjectService.get_search_config 返 SearchConfig(rrf_k=60, similarity_threshold=0.3) 默认值（design §3.X A2 + §6）

### 2. 边界 / 状态机

- [P0] active → archived 状态转换允许（design §4 mermaid + tests.md G5）
- [P0] archived → active 转换拒绝返 PROJECT_ALREADY_ARCHIVED 409（design §4 禁止转换表 + tests.md E6）
- [P0] archived → archived 重复归档拒绝返 PROJECT_ALREADY_ARCHIVED 409（design §4 + tests.md C1 第二请求）
- [P0] 任何状态 → 物理 DELETE /api/projects/{pid} 端点本期不存在返 404 / 405（design §4 PROJECT_DELETE_NOT_SUPPORTED）
- [P1] name 空字符串返 VALIDATION_ERROR 422（design §7 Pydantic min_length=1 + tests.md E1）
- [P1] name 201 字符返 VALIDATION_ERROR 422（design §7 max_length=200 + tests.md E2）
- [P1] description 2001 字符返 VALIDATION_ERROR 422（design §7 max_length=2000）
- [P1] hierarchy_labels=["a",1,null] 返 VALIDATION_ERROR 422 list[str] 失败（design §7 + tests.md E3）
- [P1] template_type 51 字符返 VALIDATION_ERROR 422（design §7 max_length=50）
- [P1] rrf_k=0 / 201 越界返 DB CHECK 失败 500 或 VALIDATION_ERROR（design §3 ck_project_rrf_k_range CHECK 1-200）
- [P1] similarity_threshold=-0.1 / 1.1 越界返 DB CHECK 失败（design §3 ck_project_similarity_threshold_range CHECK 0.0-1.0）
- [P1] project_id 非 UUID 格式访问 GET /api/projects/{pid} 返 422（FastAPI path param 校验）

### 3. 异常 / 错误

- [P0] 邀请不存在的 user_id 返 USER_NOT_FOUND 404（design §13 + tests.md E5）
- [P0] archive 不存在的 project_id 返 PROJECT_NOT_FOUND 404（design §13）
- [P0] 创建项目 project_members(owner) INSERT 失败事务全回滚 projects/dimension_configs 无残留（design §5 多表事务 + tests.md ER2a）
- [P0] 创建项目 project_dimension_configs INSERT 失败事务全回滚 projects/project_members 无残留（design §5 + tests.md ER2b）
- [P0] 邀请已是成员的 user_id 返 MEMBER_ALREADY_EXISTS 409（DB UNIQUE 约束转业务异常 + tests.md ER1）
- [P0] 同 owner 同名 active 项目第二次创建返 PROJECT_NAME_DUPLICATE 409（design §3 部分唯一索引 + tests.md E8）
- [P1] 同 owner 归档项目 A 后再创建同名 A 201 成功（design §3 部分唯一索引 WHERE status='active' + tests.md E9）
- [P1] 不同 owner 各创建同名项目两者均 201（design §3 + tests.md E10）
- [P1] 批量维度配置含不存在 dimension_type_id 返 DIMENSION_CONFIG_INVALID 422（design §13 + tests.md E7）
- [P1] 移除已不存在的成员 user_id 返 MEMBER_NOT_FOUND 404（design §13）
- [P1] AES 加密 ai_api_key 失败（ENCRYPTION_KEY 缺/损坏）返 AI_KEY_ENCRYPT_FAILED 500（design §13 + tests.md ER4）
- [P1] DB IntegrityError 未识别场景兜底返 CONFLICT 不暴露 SQL 细节（tests.md ER5）
- [P2] update_member_role role 传 enum 外值（如 "super_owner"）返 MEMBER_ROLE_INVALID 422（design §13）

### 4. 权限 / Auth

- [P0] 未登录 GET /api/projects 返 UNAUTHENTICATED 401（design §8 Server Action 层 + tests.md P1）
- [P0] viewer 调 PUT /api/projects/{pid} 返 PERMISSION_DENIED 403（design §8 Router editor 校验 + tests.md P3）
- [P0] viewer 调 PUT /api/projects/{pid}/dimension-configs 返 PERMISSION_DENIED 403（design §8 owner only + tests.md P2）
- [P0] editor 调 POST /api/projects/{pid}/members 邀请返 PERMISSION_DENIED 403（design §8 Service _check_owner + tests.md T4）
- [P0] editor 调 POST /api/projects/{pid}/archive 返 PERMISSION_DENIED 403（design §8 owner only）
- [P0] owner 调 DELETE /api/projects/{pid}/members/{owner_id} 移除自己返 MEMBER_CANNOT_REMOVE_OWNER 422（design §8 Service _check_not_remove_self_owner + tests.md P4）
- [P0] viewer 调 PUT /api/projects/{pid}/members/{uid} 变更角色返 403（design §8 owner only）
- [P1] 角色从 editor 降为 viewer 后老 session 调 PUT 接口返 403（design §8 三层防御 + tests.md P5）
- [P1] platform_admin 跨项目调 GET /api/projects/{pid} 不是该项目成员仍返 403（M02 不豁免 platform_admin / Router check_project_access 走 project_members 表）
- [P1] check_project_access 在 Router 与 _check_owner 在 Service 重复校验（三层防御）owner 单次请求两层都过（design §8 三层）
- [P2] disabled 用户的 JWT 调 /api/projects 返 401（M01 token_invalidated_at 路径，跨模块继承 require_user）

### 5. Tenant 隔离

- [P0] userB 非成员调 GET /api/projects/{projectA_id} 返 PERMISSION_DENIED 403（design §8 check_project_access + tests.md T1）
- [P0] userB 非成员调 POST /api/projects/{projectA_id}/members 返 403（tests.md T2）
- [P0] userA 调 GET /api/projects/{projectB_id}/members 非项目成员返 403（design §9 Router 层拦 + tests.md T5）
- [P0] ProjectDAO.list_by_user(userB_id) 单元测试 userB 只看到自己有成员资格的项目不返 projectA（design §9 list_by_user + tests.md T3）
- [P1] ProjectDAO.get_by_id_for_user 同时校验 project_id + user_id JOIN project_members（design §9 主查询模式）
- [P1] MemberDAO.list_by_project / get_member 均按 project_id 过滤（design §9）
- [P1] dimension_types 全表查询不带 tenant 过滤（design §9 豁免清单 / 全局字典数据）
- [P1] 用户被移除成员后调 GET /api/projects/{pid} 返 403（design §9 + 状态传播）
- [P2] 跨项目 PUT /api/projects/{projectA}/members/{userB} body project_id 不可被前端篡改重定向到 projectB（FastAPI path param 优先于 body）

### 6. 并发 / 乐观锁

- [P0] 两 owner 并发 POST /archive 同一项目第一 200 第二 409 PROJECT_ALREADY_ARCHIVED 不报 500 不丢数据（design §5 R5-2 + tests.md C1）
- [P0] 两 owner 并发 POST /members 邀请同一 user_id 第一 201 第二 409 MEMBER_ALREADY_EXISTS 不报 500 / DB UNIQUE(project_id,user_id) 防重（tests.md C3）
- [P1] 两 owner 并发 DELETE 不同 user_id 两者均 204 无冲突（tests.md C2）
- [P1] 两 owner 并发 PUT ai_api_key 不同值两者均 200 last-write-wins 无乐观锁（design §5 4 维必答 / 并发 N/A + tests.md C4）
- [P1] 两 owner 并发 PUT /dimension-configs 不同 config_id 两者均 200（独立行 UPSERT 无冲突）
- [P1] 同一 owner 两 tab 并发 PUT /api/projects/{pid} 改 name 不同值 last-write-wins（M02 无 version 字段 / design §5 清单 2 不触发）
- [P2] 同一 user_id 并发邀请到不同项目两者均 201（project_id 不同 UNIQUE 不冲突）

### 7. 数据完整性

- [P0] projects.name CHECK 约束 != '' 直接 INSERT 空串失败（design §3 ck_project_name_not_empty）
- [P0] projects.status CHECK 约束仅 active/archived（design §3 R3-2 三重防护 + ck_project_status）
- [P0] project_members.role CHECK 约束仅 owner/editor/viewer（design §3 R3-2 + ck_member_role）
- [P0] project_members UNIQUE(project_id, user_id) 直接 INSERT 重复失败（design §3 uq_project_member）
- [P0] project_dimension_configs UNIQUE(project_id, dimension_type_id) 防重（design §3 uq_proj_dim_config）
- [P1] projects 部分唯一索引 uq_project_owner_name_active 仅对 status='active' 生效（design §3 PG partial index）
- [P1] projects.rrf_k CHECK 范围 1-200（design §3 ck_project_rrf_k_range）
- [P1] projects.similarity_threshold CHECK 范围 0.0-1.0（design §3 ck_project_similarity_threshold_range）
- [P1] projects.team_id FK to teams.id ondelete=RESTRICT（M20 baseline-patch / design §3 + §3.X A1）
- [P1] projects.team_id nullable 个人项目允许 NULL（design §3.X A1 / ADR-005）
- [P1] project_members FK projects.id ondelete=CASCADE 删项目级联删成员（design §3）
- [P1] project_dimension_configs FK projects.id ondelete=CASCADE 删项目级联删 config（design §3）
- [P1] ai_api_key_enc String(1000) 长度上限 AES base64 1000 bytes（design §3）
- [P1] hierarchy_labels JSONB 字段类型直接 SELECT 返 list[str]（design §3）
- [P2] dimension_types.key UNIQUE 全局字典防重（design §3）

### 8. UI / UX

- [P1] 项目列表卡片显示 name / description / template_type（design §6 project-card.tsx）
- [P1] viewer 角色项目设置页编辑按钮置灰 / 隐藏（PRD US-C2.1 + design §6）
- [P1] 归档项目操作前端弹二次确认对话框（PRD US-A2.3 防误删 + design §6 dialog-flow）
- [P1] 邀请成员前端按 email 查询 user_id 后端再 POST（design §1 US-A2.1）
- [P1] 维度配置页拖拽排序更新 sort_order（design §6 dimension-config.tsx + US-A1.2）
- [P1] AI Provider 配置页 API Key 输入框 type=password 不明文显示（design §3 安全考虑）
- [P2] PROJECT_NAME_DUPLICATE 前端 toast "项目名已存在"（design §13 message）
- [P2] PROJECT_ALREADY_ARCHIVED 前端 toast "项目已归档" / 隐藏归档按钮（design §13）

### 9. 性能 / 容量

- [P1] GET /api/projects 大量项目分页（design §7 ProjectListResponse.total 提示需分页）
- [P1] GET /api/projects/{pid}/members JOIN users 表 N 成员单次查询不 N+1（design §6 DAO 层 JOIN）
- [P1] PUT /dimension-configs batch 50 条 UPSERT 单次事务（R2 punt follow-up：PostgreSQL ON CONFLICT DO UPDATE 一次完成）
- [P2] projects 索引 (owner_id) / (team_id) 加速 list_by_user JOIN（design §3 Alembic 索引清单）

### 10. activity_log 事件完备性

- [P0] create 事件 target_type=project target_id=project_id metadata={template_type,name}（design §10）
- [P0] update 事件 metadata.changed_fields 反映实际改动字段（design §10）
- [P0] archive 事件 metadata.previous_status='active'（design §10）
- [P0] invite_member 事件 target_type=project_member target_id=member_id metadata 含 project_id/invited_user_id/role（design §10）
- [P1] update_member_role 事件 metadata 含 old_role / new_role（design §10）
- [P1] update_ai_provider 事件 metadata 仅 new_provider 不含 api_key（design §10 安全）
- [P1] batch dimension-configs 更新 N 条变更写 N 条独立 update_dimension_config 事件（design §10 R10-1 batch3 基线补丁）
- [P1] dimension-configs 批量更新中未变更的 config 不写事件（R10-1 仅"被修改的"）

### 11. AES 加密 helper（M02 触发 horizontal）

- [P0] encrypt(plaintext) 同输入两次密文不同（GCM nonce 随机）但 decrypt 都还原（design §3.Z + 单元测试覆盖）
- [P0] decrypt 错密钥（ENCRYPTION_KEY 不匹配）raise 异常 → Service 转 AI_KEY_ENCRYPT_FAILED 500（design §3.Z）
- [P0] decrypt 错 ciphertext（被篡改 base64）raise 异常（design §3.Z）
- [P1] encrypt/decrypt helper 在 api/auth/crypto.py 横切层 而非 services/project_service.py（design §3.Z + 原则 6）
- [P1] ENCRYPTION_KEY env 缺失启动期 settings 校验失败（design §3.Z + 05-security-baseline）
- [P2] ai_api_key_enc 字段 SELECT 不直接暴露给前端 ProjectResponse（design §7 注释 "不返回给前端"）

### 12. baseline-patch 时序契约（M02 own 3 处反向引用）

- [P0] team_id 字段在 M02 schema 已落 UUID nullable 含 FK（design §3.X A1 实证 commit a42dc81 / 10f2f54）
- [P0] PROJECT_ARCHIVED ErrorCode + ProjectArchivedError 子类已落 但 raise caller 待 M20（design §3.X A3.1 实证 commit 10f2f54）
- [P0] POST /api/projects/{pid}/move-team endpoint 当前不实装 FastAPI 返 404（design §3.X A3.2 实证 commit c9b0618 + test_b_path_move_team_endpoint_not_registered）
- [P1] ProjectService.get_search_config 默认路径 rrf_k=60 / similarity_threshold=0.3 已实装 待 M18 接入（design §3.X A2 实证 commit 10f2f54）
- [P1] dimension_types 表 alembic data migration 必种 1 条 default 类型作测试 fixture 兜底（design §3.Y R3-6-B）
- [P2] R-X5 子选项实证 team_id 写入策略 = DAO 完全允许（design §3.X A1 实证）

### 13. 跨模块边界 / 归档不级联

- [P0] M02 archive 不调任何 M03/M04/M05/M07 子模块状态变更方法（design §4 P5 audit F-2）
- [P0] 归档项目下 M03 NodeService.create 拒绝写入返 PROJECT_ARCHIVED（design §4 实施约束 / 子模块防御）
- [P1] 归档项目 M07 issues.status 保持原值 open 不被强制 closed（design §4 不级联）
- [P1] 归档项目 M05 version_records.is_current 保持原值不重置（design §4 不级联）
- [P1] 归档项目 M03 nodes / M04 dimension_records 等无状态机子表保持原数据（design §4）
- [P1] 跨模块读 archived project 的 nodes/dimension_records 仍合法返数据（design §4 归档=只读历史快照）
- [P2] team_id 非空的 project 上下游 M03-M19 测试盲区 待 M20 sprint 补回归（design §3.X A1 C 路径登记）

### 14. ErrorCode parity / R13-1 守护

- [P0] PROJECT_NOT_FOUND / PROJECT_ALREADY_ARCHIVED / PROJECT_NAME_DUPLICATE / MEMBER_ALREADY_EXISTS / MEMBER_CANNOT_REMOVE_OWNER 各对应一个 AppError 子类（design §13 + R13-1）
- [P0] AppError 子类 http_status 与 design §13 表一致（409/422/500）
- [P1] MemberRoleInvalidError / DimensionConfigInvalidError extends ValidationError（sprint 实施回写 R1#1 / 与 M01 OldPasswordMismatchError 一致语义）
- [P1] CI grep 守护 ErrorCode enum 行数 == AppError class 行数 22+12=34 parity（M01 同款守护）

### 15. 反向漂移防御 / CI

- [P1] Router /api/projects 禁直接 db.query(Project) 必走 ProjectService → ProjectDAO（design §6 禁止清单 + 原则 2）
- [P1] Service 禁直接 INSERT users（design §6 禁止清单 / 走 M01 UserService）
- [P1] DAO 禁判断 if role == 'owner' 业务逻辑（design §6 禁止清单 / 原则 2）
- [P1] DAO 方法签名 list_by_user / get_by_id_for_user 必含 user_id 参数（design §9 tenant 过滤 + CI 守护）
- [P2] frontmatter produces_action_types 与 §10 表 verb 单词派一致（sprint 实施回写 R1#4 / 待 M15 ActionType enum 实装时全局对齐）
