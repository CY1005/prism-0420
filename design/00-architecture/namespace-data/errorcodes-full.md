# ErrorCode 全集（125 条）

> 自动提取自 design/02-modules/M*/00-design.md（2026-05-06）。owner = 模块 ID。
> 命名规范遵守度待 N1-N5 定稿后批量审计。

## 通用码（10 条，横向 owner）

见 [](../08-namespaces.md) § 1.2

## 模块特化码（115 条）

**M01**:

| code | http/note |
|------|-----------|
| UNAUTHENTICATED | 401 |
| INVALID_CREDENTIALS | 401 登录邮箱/密码错误（不暴露具体原因） |
| ACCOUNT_DISABLED | 403 |
| ACCOUNT_LOCKED | 423 |
| ACCOUNT_PENDING | 403（Q1 预留） |
| INVALID_REFRESH_TOKEN | 401 |
| REFRESH_TOKEN_EXPIRED | 401 |
| OLD_PASSWORD_MISMATCH | 400 改密码时旧密码错 |
| PASSWORD_TOO_WEAK | 422 |
| EMAIL_ALREADY_EXISTS | 409 |
| USER_NOT_FOUND | 404 |
| PERMISSION_DENIED | 403（require_admin 失败） |
| SELF_DOWNGRADE_FORBIDDEN | 400 admin 改自己 role |
| LAST_ADMIN_PROTECTED | 400 禁用最后一个 admin |
| INVALID_STATUS_TRANSITION | 400 |
| VERSION_CONFLICT | 409 Concern 1：乐观锁失败 |
| REGISTRATION_DISABLED | 403 Q1 预留（本期开放注册未启用时的稳定错误码） |

**M02**:

| code | http/note |
|------|-----------|
| PROJECT_NOT_FOUND |  |
| PROJECT_ALREADY_ARCHIVED |  |
| PROJECT_ALREADY_ACTIVE |  |
| PROJECT_DELETE_NOT_SUPPORTED |  |
| PROJECT_NAME_DUPLICATE | G3=B：同 owner 下 active 项目名唯一（部分唯一索引） |
| MEMBER_NOT_FOUND |  |
| MEMBER_ALREADY_EXISTS |  |
| MEMBER_CANNOT_REMOVE_OWNER |  |
| MEMBER_ROLE_INVALID |  |
| DIMENSION_CONFIG_INVALID | 维度配置批量更新校验失败 |
| AI_KEY_ENCRYPT_FAILED | API Key 加密失败 |
| PROJECT_ARCHIVED | 422，archived project 拒加入 team |

**M03**:

| code | http/note |
|------|-----------|
| NODE_NOT_FOUND |  |
| NODE_NAME_EMPTY |  |
| NODE_PARENT_NOT_FOUND | 指定的 parent_id 不存在 |
| NODE_TYPE_IMMUTABLE | 节点类型创建后不可变 |
| NODE_REORDER_INVALID | 重排节点不属于同一父节点 |
| NODE_DELETE_HAS_CHILDREN | 删除有子节点时的级联确认（G2：直接级联，此码不触发，保留备用） |
| NODE_MOVE_CYCLE_DETECTED | G5：跨父移动检测到循环引用（移到子孙节点） |

**M04**:

| code | http/note |
|------|-----------|
| DIMENSION_NOT_FOUND |  |
| DIMENSION_TYPE_DISABLED | 项目级配置禁用 |
| DIMENSION_TYPE_NOT_FOUND |  |
| DIMENSION_CONTENT_INVALID | field_schema 校验失败 |
| DIMENSION_DUPLICATE | (node_id, type_id) 唯一约束 |

**M05**:

| code | http/note |
|------|-----------|
| VERSION_NOT_FOUND |  |
| VERSION_LABEL_DUPLICATE | (node_id, version_label) 唯一约束 |
| VERSION_SNAPSHOT_INVALID | snapshot_data 格式校验失败 |

**M06**:

| code | http/note |
|------|-----------|
| COMPETITOR_NOT_FOUND |  |
| COMPETITOR_REF_NOT_FOUND |  |
| COMPETITOR_REF_DUPLICATE | (node_id, competitor_id) 唯一约束 |
| COMPETITOR_CROSS_PROJECT | 引用了其他项目的竞品 |

**M07**:

| code | http/note |
|------|-----------|
| ISSUE_NOT_FOUND |  |
| ISSUE_TRANSITION_INVALID | 状态机非法转换（如 open→closed） |
| ISSUE_CLOSED_ERROR | closed 状态不可重开 |
| ISSUE_ASSIGNEE_REQUIRED | in_progress 时 assigned_to 必填 |
| ISSUE_CATEGORY_INVALID | category 非枚举值 |
| ISSUE_NODE_CROSS_PROJECT | node_id 属于其他项目 |

**M08**:

| code | http/note |
|------|-----------|
| RELATION_NOT_FOUND |  |
| RELATION_DUPLICATE | 三元组唯一约束冲突 |
| RELATION_SELF_LOOP | source == target |
| RELATION_NODE_NOT_IN_PROJECT | 节点不属于该 project |
| RELATION_TYPE_INVALID | 非法 relation_type 枚举值（理论上 Pydantic 先拦） |

**M09**:

| code | http/note |
|------|-----------|
| SEARCH_QUERY_TOO_SHORT | 关键词长度 < 1（Pydantic 先拦，兜底） |
| SEARCH_QUERY_TOO_LONG | 关键词长度 > 200 |
| SEARCH_PROJECT_ACCESS_DENIED | 指定 project 无权访问 |

**M10**:

| code | http/note |
|------|-----------|
| OVERVIEW_PROJECT_NOT_FOUND | project 不存在或无权限 |

**M11**:

| code | http/note |
|------|-----------|
| COLD_START_TASK_NOT_FOUND |  |
| COLD_START_CSV_INVALID | CSV 格式无效（文件解析失败） |
| COLD_START_ROW_VALIDATION_FAILED | 行级校验失败（含行号） |
| COLD_START_BATCH_INSERT_FAILED | 批量入库事务失败 |
| COLD_START_TASK_FINALIZED | 终态不可重操作 |
| COLD_START_INVALID_STATE_TRANSITION |  |
| COLD_START_FILE_TOO_LARGE | 超过大小阈值 |

**M12**:

| code | http/note |
|------|-----------|
| COMPARISON_SNAPSHOT_NOT_FOUND |  |
| COMPARISON_SNAPSHOT_NAME_EMPTY | 快照名为空 |
| COMPARISON_NODE_NOT_FOUND | 所选 node 不属于该 project |
| COMPARISON_EMPTY_SELECTION | nodes 或 dimensions 选择为空 |
| COMPARISON_SNAPSHOT_CONFLICT | 乐观锁冲突（rename 并发） |

**M13**:

| code | http/note |
|------|-----------|
| ANALYSIS_NODE_NOT_FOUND | node 不存在 / 跨项目越权 |
| ANALYSIS_PROVIDER_NOT_CONFIGURED | 项目未配置 AI provider（引导用户去配置页） |
| ANALYSIS_PROVIDER_ERROR | AI provider 调用失败（瞬时故障，提示重试） |
| ANALYSIS_TIMEOUT | 5 分钟硬超时 |
| ANALYSIS_QUOTA_EXCEEDED | 用户 / 项目 AI 配额超限 |
| ANALYSIS_SAVE_FAILED | save 阶段写 dimension_record 失败 |
| ANALYSIS_INVALID_LEVEL | L1/L2/L3 以外（理论上 Pydantic Enum 拦住，预留） |

**M14**:

| code | http/note |
|------|-----------|
| NEWS_NOT_FOUND |  |
| NEWS_LINK_DUPLICATE | (news_id, node_id) 重复关联 |
| NEWS_LINK_NOT_FOUND |  |
| NEWS_FORBIDDEN | 非本人/非管理员尝试删除/编辑 |

**M15**:

| code | http/note |
|------|-----------|
| ACTIVITY_STREAM_PROJECT_NOT_FOUND | project 不存在或无权限 |

**M16**:

| code | http/note |
|------|-----------|
| SNAPSHOT_NODE_NOT_FOUND | node 不存在 / 跨项目越权 |
| SNAPSHOT_INSUFFICIENT_VERSIONS | 版本数 < 3，AC1 兜底 |
| SNAPSHOT_PROVIDER_NOT_CONFIGURED | 项目未配置 AI provider |
| SNAPSHOT_PROVIDER_ERROR | AI provider 调用失败 |
| SNAPSHOT_TIMEOUT | 10 分钟硬超时 |
| SNAPSHOT_QUOTA_EXCEEDED | 用户 / 项目 AI 配额超限 |
| SNAPSHOT_SAVE_FAILED | save 阶段写 dimension_record 失败 |
| SNAPSHOT_TASK_NOT_FOUND | task_id 不存在 / 越权 |
| SNAPSHOT_NOT_READY | save 时任务还未 succeeded |
| SNAPSHOT_TASK_FINALIZED | 状态机非法转换（终态不可变） |
| SNAPSHOT_INVALID_STATE_TRANSITION |  |
| SNAPSHOT_ZOMBIE | cron 兜底标记的 zombie task |
| SNAPSHOT_PARSE_FAILED | AI 输出 JSON parse 失败 |
| SNAPSHOT_INVALID_DIMENSION_KEY | save 时 selected_dimension_keys 不在 review_data 中 |
| SNAPSHOT_TASK_PATH_MISMATCH | save 时 task.project_id/node_id 与 URL path 不一致（audit M5 修复） |

**M17**:

| code | http/note |
|------|-----------|
| IMPORT_TASK_NOT_FOUND |  |
| IMPORT_TASK_FINALIZED | 终态不可变 |
| IMPORT_INVALID_SOURCE | zip 损坏 / git URL 无效 |
| IMPORT_AI_PROVIDER_ERROR | AI 调用失败（重试用尽） |
| IMPORT_BATCH_INSERT_FAILED | 入库阶段失败 |
| IMPORT_QUOTA_EXCEEDED | 用户 / 项目 AI 配额超限 |
| IMPORT_TASK_DUPLICATE | idempotency 命中（非错误，但需特殊响应） |
| IMPORT_INVALID_STATE_TRANSITION | 状态机非法转换 |

**M18**:

| code | http/note |
|------|-----------|
| INVALID_QUERY_LENGTH |  |
| SEARCH_TIMEOUT |  |
| PGVECTOR_UNAVAILABLE | 降级为 keyword_only 时不抛错，仅写日志/embedding_failures |
| EMBEDDING_PROVIDER_FAILED | OpenAI/bge 调用失败 |
| EMBEDDING_PROVIDER_TIMEOUT |  |
| EMBEDDING_TARGET_NOT_FOUND | 业务表已删（noop 不算失败） |
| EMBEDDING_ZOMBIE | zombie cron 兜底 |
| EMBEDDING_TASK_TERMINAL_VIOLATION |  |
| EMBEDDING_TASK_INVALID_TRANSITION |  |
| EMBEDDING_BACKFILL_ALREADY_RUNNING | 防并发触发 |
| EMBEDDING_MODEL_UPGRADE_INVALID | 切到不存在的 model |
| EMBEDDING_DELETE_FAILED | delete_by_target 失败不阻塞，写 failures |

**M19**:

| code | http/note |
|------|-----------|
| EXPORT_NODE_LIMIT_EXCEEDED | node_ids 数量超上限 |
| EXPORT_NODE_NOT_IN_PROJECT | node 不属于该 project |
| EXPORT_EMPTY_CONTENT | 所有 node 均无内容（422） |
