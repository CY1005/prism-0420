"""AppError 子类横切 helper（horizontal）。

# horizontal: 是
# owner: engineering-spec §7.2（与 ErrorCode 枚举对齐 R13-1 parity）
# 位置: api/errors/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: 全局异常基类 + 子类（业务模块通过 codes_added 扩展时同步加子类）
"""

from typing import Any

from api.errors.codes import ErrorCode


class AppError(Exception):
    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    http_status: int = 500
    message: str = "Internal error"

    def __init__(self, message: str | None = None, **details: Any) -> None:
        if message is not None:
            self.message = message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    code = ErrorCode.NOT_FOUND
    http_status = 404
    message = "Resource not found"


class ValidationError(AppError):
    code = ErrorCode.VALIDATION_ERROR
    http_status = 422
    message = "Validation failed"


class ConflictError(AppError):
    code = ErrorCode.CONFLICT
    http_status = 409
    message = "Concurrent modification detected"


class UnauthenticatedError(AppError):
    code = ErrorCode.UNAUTHENTICATED
    http_status = 401
    message = "Authentication required"


class RateLimitedError(AppError):
    code = ErrorCode.RATE_LIMITED
    http_status = 429
    message = "Too many requests"


class AccessTokenExpiredError(AppError):
    code = ErrorCode.ACCESS_TOKEN_EXPIRED
    http_status = 401
    message = "Access token expired"


class RefreshTokenExpiredError(AppError):
    code = ErrorCode.REFRESH_TOKEN_EXPIRED
    http_status = 401
    message = "Refresh token expired"


class AccountLockedError(AppError):
    code = ErrorCode.ACCOUNT_LOCKED
    http_status = 423
    message = "Account is locked"


# ─── M01 ─────────────────────────────────────────────


class InvalidCredentialsError(AppError):
    code = ErrorCode.INVALID_CREDENTIALS
    http_status = 401
    message = "Invalid email or password"


class AccountDisabledError(AppError):
    code = ErrorCode.ACCOUNT_DISABLED
    http_status = 403
    message = "Account disabled"


class AccountPendingError(AppError):
    code = ErrorCode.ACCOUNT_PENDING
    http_status = 403
    message = "Account pending approval"


class InvalidRefreshTokenError(AppError):
    code = ErrorCode.INVALID_REFRESH_TOKEN
    http_status = 401
    message = "Invalid refresh token"


class OldPasswordMismatchError(ValidationError):
    code = ErrorCode.OLD_PASSWORD_MISMATCH
    http_status = 400
    message = "Old password mismatch"


class PasswordTooWeakError(ValidationError):
    code = ErrorCode.PASSWORD_TOO_WEAK
    http_status = 422
    message = "Password too weak"


class EmailAlreadyExistsError(AppError):
    code = ErrorCode.EMAIL_ALREADY_EXISTS
    http_status = 409
    message = "Email already exists"


class UserNotFoundError(NotFoundError):
    code = ErrorCode.USER_NOT_FOUND
    message = "User not found"


class PermissionDeniedError(AppError):
    code = ErrorCode.PERMISSION_DENIED
    http_status = 403
    message = "Permission denied"


class SelfDowngradeForbiddenError(AppError):
    code = ErrorCode.SELF_DOWNGRADE_FORBIDDEN
    http_status = 400
    message = "Cannot change your own role"


class LastAdminProtectedError(AppError):
    code = ErrorCode.LAST_ADMIN_PROTECTED
    http_status = 400
    message = "Cannot disable the last platform admin"


class InvalidStatusTransitionError(AppError):
    code = ErrorCode.INVALID_STATUS_TRANSITION
    http_status = 400
    message = "Invalid status transition"


class VersionConflictError(AppError):
    code = ErrorCode.VERSION_CONFLICT
    http_status = 409
    message = "Version conflict — refresh and retry"


class RegistrationDisabledError(AppError):
    code = ErrorCode.REGISTRATION_DISABLED
    http_status = 403
    message = "Registration disabled"


# ─── M02 项目管理 ───────────────────────────────────


class ProjectNotFoundError(NotFoundError):
    code = ErrorCode.PROJECT_NOT_FOUND
    message = "Project not found"


class ProjectAlreadyArchivedError(AppError):
    code = ErrorCode.PROJECT_ALREADY_ARCHIVED
    http_status = 409
    message = "Project is already archived"


class ProjectAlreadyActiveError(AppError):
    code = ErrorCode.PROJECT_ALREADY_ACTIVE
    http_status = 409
    message = "Project is already active"


class ProjectDeleteNotSupportedError(AppError):
    code = ErrorCode.PROJECT_DELETE_NOT_SUPPORTED
    http_status = 422
    message = "Physical project deletion is not supported; use archive instead"


class ProjectNameDuplicateError(AppError):
    code = ErrorCode.PROJECT_NAME_DUPLICATE
    http_status = 409
    message = "Project with this name already exists"


class MemberNotFoundError(NotFoundError):
    code = ErrorCode.MEMBER_NOT_FOUND
    message = "Project member not found"


class MemberAlreadyExistsError(AppError):
    code = ErrorCode.MEMBER_ALREADY_EXISTS
    http_status = 409
    message = "User is already a member of this project"


class MemberCannotRemoveOwnerError(AppError):
    """R1 P1-A: message 改宽,覆盖 拒移除 owner / 拒降级 owner 两种语义.

    具体语义在 details.reason 区分: cannot_remove_owner / cannot_demote_owner.
    """

    code = ErrorCode.MEMBER_CANNOT_REMOVE_OWNER
    http_status = 422
    message = "Cannot modify project owner's role/membership"


class MemberRoleInvalidError(ValidationError):
    code = ErrorCode.MEMBER_ROLE_INVALID
    http_status = 422
    message = "Invalid member role"


class DimensionConfigInvalidError(ValidationError):
    code = ErrorCode.DIMENSION_CONFIG_INVALID
    http_status = 422
    message = "Invalid dimension configuration"


class AiKeyEncryptFailedError(AppError):
    code = ErrorCode.AI_KEY_ENCRYPT_FAILED
    http_status = 500
    message = "Failed to encrypt AI provider API key"


class ProjectArchivedError(AppError):
    """A3.1 — F2.3 M20 baseline-patch.

    M02 sprint 期 ErrorCode + AppError 子类配齐 (R13-1 parity);
    raise caller 在 M20 sprint move-team router 实装时建。
    标记位置 (R13-1 子选项 实证): code 注释 (本段) — 不入 ci-lint.sh 附加规则.
    """

    code = ErrorCode.PROJECT_ARCHIVED
    http_status = 422
    message = "Archived project cannot be moved to a team"


# ─── M03 功能模块树 (design §13) ─────────────────────────────────
# R-X5 子选项实证 (M02 sprint 末): R13-1 未实装期 ErrorCode 标记位置 = code 注释


class NodeNotFoundError(NotFoundError):
    code = ErrorCode.NODE_NOT_FOUND
    http_status = 404
    message = "Node not found"


class NodeNameEmptyError(ValidationError):
    """G2 — Pydantic min_length=1 拦得早 (router 层 422); 此 ErrorCode 保留备用 (R13-1 parity)."""

    code = ErrorCode.NODE_NAME_EMPTY
    http_status = 422
    message = "Node name cannot be empty"


class NodeParentNotFoundError(NotFoundError):
    code = ErrorCode.NODE_PARENT_NOT_FOUND
    http_status = 404
    message = "Parent node not found"


class NodeTypeImmutableError(ValidationError):
    code = ErrorCode.NODE_TYPE_IMMUTABLE
    http_status = 422
    message = "Node type cannot be changed after creation"


class NodeReorderInvalidError(ValidationError):
    code = ErrorCode.NODE_REORDER_INVALID
    http_status = 422
    message = "All nodes in reorder request must belong to the same parent"


class NodeDeleteHasChildrenError(ValidationError):
    """G2 决策硬删除级联子树, 此码保留备用不触发 (R13-1 parity)."""

    code = ErrorCode.NODE_DELETE_HAS_CHILDREN
    http_status = 422
    message = "Cannot delete node with children; delete children first or confirm cascade"


class NodeMoveCycleDetectedError(ValidationError):
    code = ErrorCode.NODE_MOVE_CYCLE_DETECTED
    http_status = 422
    message = "Cannot move node to its own descendant (cycle detected)"


# ─────────────── M04 功能项档案页 / 维度记录 ───────────────


class DimensionNotFoundError(NotFoundError):
    code = ErrorCode.DIMENSION_NOT_FOUND
    http_status = 404
    message = "Dimension record not found"


class DimensionTypeDisabledError(AppError):
    code = ErrorCode.DIMENSION_TYPE_DISABLED
    http_status = 422
    message = "This dimension type is disabled in current project"


class DimensionTypeNotFoundError(NotFoundError):
    code = ErrorCode.DIMENSION_TYPE_NOT_FOUND
    http_status = 404
    message = "Dimension type not found"


class DimensionContentInvalidError(ValidationError):
    code = ErrorCode.DIMENSION_CONTENT_INVALID
    http_status = 422
    message = "Dimension content does not match field schema"


class DimensionDuplicateError(ConflictError):
    code = ErrorCode.DIMENSION_DUPLICATE
    http_status = 409
    message = "Dimension record already exists for this node and type"


# ─────────────── M05 版本演进时间线 ───────────────


class VersionNotFoundError(NotFoundError):
    code = ErrorCode.VERSION_NOT_FOUND
    http_status = 404
    message = "Version record not found"


class VersionLabelDuplicateError(ConflictError):
    code = ErrorCode.VERSION_LABEL_DUPLICATE
    http_status = 409
    message = "A version with this label already exists for the node"


class VersionSnapshotInvalidError(ValidationError):
    code = ErrorCode.VERSION_SNAPSHOT_INVALID
    http_status = 422
    message = "snapshot_data does not match expected format"


# ─────────────── M06 竞品参考 ───────────────


class CompetitorNotFoundError(NotFoundError):
    code = ErrorCode.COMPETITOR_NOT_FOUND
    http_status = 404
    message = "Competitor not found"


class CompetitorRefNotFoundError(NotFoundError):
    code = ErrorCode.COMPETITOR_REF_NOT_FOUND
    http_status = 404
    message = "Competitor reference not found"


class CompetitorRefDuplicateError(ConflictError):
    code = ErrorCode.COMPETITOR_REF_DUPLICATE
    http_status = 409
    message = "This competitor is already referenced for this node"


class CompetitorCrossProjectError(ValidationError):
    code = ErrorCode.COMPETITOR_CROSS_PROJECT
    http_status = 422
    message = "Cannot reference a competitor from another project"


# ─────────────── M07 问题沉淀 ───────────────


class IssueNotFoundError(NotFoundError):
    code = ErrorCode.ISSUE_NOT_FOUND
    http_status = 404
    message = "Issue not found"


class IssueTransitionInvalidError(ValidationError):
    code = ErrorCode.ISSUE_TRANSITION_INVALID
    http_status = 422
    message = "Invalid status transition"


class IssueClosedError(ValidationError):
    code = ErrorCode.ISSUE_CLOSED_ERROR
    http_status = 422
    message = "Issue is closed and cannot be reopened; create a new issue instead"


class IssueAssigneeRequiredError(ValidationError):
    code = ErrorCode.ISSUE_ASSIGNEE_REQUIRED
    http_status = 422
    message = "assigned_to is required when transitioning to in_progress"


class IssueCategoryInvalidError(ValidationError):
    code = ErrorCode.ISSUE_CATEGORY_INVALID
    http_status = 422
    message = "Invalid issue category"


class IssueNodeCrossProjectError(ValidationError):
    code = ErrorCode.ISSUE_NODE_CROSS_PROJECT
    http_status = 422
    message = "The specified node does not belong to this project"


# ─────────────── M08 模块关系图 ───────────────


class RelationNotFoundError(NotFoundError):
    code = ErrorCode.RELATION_NOT_FOUND
    http_status = 404
    message = "Module relation not found"


class RelationDuplicateError(ConflictError):
    code = ErrorCode.RELATION_DUPLICATE
    http_status = 409
    message = "This relation already exists between the two nodes with the same type"


class RelationSelfLoopError(ValidationError):
    code = ErrorCode.RELATION_SELF_LOOP
    http_status = 422
    message = "source_node_id and target_node_id must be different"


class RelationNodeNotInProjectError(ValidationError):
    """R1-B P1-02 立修（M08 sprint，2026-05-08）：http_status 由 404 → 422 与
    M06 CompetitorCrossProjectError + M07 IssueNodeCrossProjectError 范式对齐
    （跨 project 引用校验 = 422 validation，非 404 资源不存在）。"""

    code = ErrorCode.RELATION_NODE_NOT_IN_PROJECT
    http_status = 422
    message = "One or both nodes do not belong to the given project"


class RelationTypeInvalidError(ValidationError):
    """R1-A P1-01 立修（M08 sprint，2026-05-08）：Pydantic Enum 先拦，本 ErrorCode
    保留备用（R13-1 parity；与 M03 NodeNameEmptyError / M07 IssueCategoryInvalidError
    同款 pattern）。"""

    code = ErrorCode.RELATION_TYPE_INVALID
    http_status = 422
    message = "Invalid relation_type value"


# ─────────────── M10 项目全景图 ───────────────


class OverviewProjectNotFoundError(NotFoundError):
    """R1 P1-02 立修注释（M10 sprint，2026-05-08）：生产路径下 router
    check_project_access(role="viewer") 已拦截 non-member → ProjectNotFoundError 404
    （M02 范式 code=project_not_found）。本 ErrorCode 仅 service 单测路径可达
    （test_svc_project_not_found_raises_404）；R13-1 parity 保留 + 与 M02 R-X5
    NodeNameEmptyError / M03 NODE_DELETE_HAS_CHILDREN 同款 pattern。"""

    code = ErrorCode.OVERVIEW_PROJECT_NOT_FOUND
    http_status = 404
    message = "Project not found or access denied"


class OverviewNodeNotFoundError(NotFoundError):
    code = ErrorCode.OVERVIEW_NODE_NOT_FOUND
    http_status = 404
    message = "Node not found in this project"


class OverviewNoDimensionsError(ValidationError):
    code = ErrorCode.OVERVIEW_NO_DIMENSIONS
    http_status = 422
    message = "Project has no enabled dimensions configured; completion rate cannot be calculated"


# ─────────────── M11 冷启动支持 ───────────────


class ColdStartTaskNotFoundError(NotFoundError):
    code = ErrorCode.COLD_START_TASK_NOT_FOUND
    http_status = 404
    message = "Cold start task not found"


class ColdStartCsvInvalidError(ValidationError):
    code = ErrorCode.COLD_START_CSV_INVALID
    http_status = 422
    message = "CSV file is invalid or cannot be parsed"


class ColdStartRowValidationFailedError(ValidationError):
    code = ErrorCode.COLD_START_ROW_VALIDATION_FAILED
    http_status = 422
    message = "One or more rows failed validation; see error_report for details"


class ColdStartBatchInsertFailedError(AppError):
    code = ErrorCode.COLD_START_BATCH_INSERT_FAILED
    http_status = 500
    message = "Batch insert failed; transaction rolled back"


class ColdStartTaskFinalizedError(ConflictError):
    code = ErrorCode.COLD_START_TASK_FINALIZED
    http_status = 409
    message = "Cold start task is in final state and cannot be re-triggered"


class ColdStartInvalidStateTransitionError(ConflictError):
    code = ErrorCode.COLD_START_INVALID_STATE_TRANSITION
    http_status = 409
    message = "Invalid state transition for cold start task"


class ColdStartFileTooLargeError(AppError):
    code = ErrorCode.COLD_START_FILE_TOO_LARGE
    http_status = 413
    message = "CSV file exceeds maximum allowed size"


# ─────────────── M12 功能对比矩阵（design §13）───────────────


class ComparisonSnapshotNotFoundError(NotFoundError):
    code = ErrorCode.COMPARISON_SNAPSHOT_NOT_FOUND
    message = "Comparison snapshot not found"


class ComparisonSnapshotNameEmptyError(ValidationError):
    code = ErrorCode.COMPARISON_SNAPSHOT_NAME_EMPTY
    message = "Snapshot name cannot be empty"


class ComparisonNodeNotFoundError(ValidationError):
    code = ErrorCode.COMPARISON_NODE_NOT_FOUND
    message = "One or more selected nodes do not belong to this project"


class ComparisonEmptySelectionError(ValidationError):
    code = ErrorCode.COMPARISON_EMPTY_SELECTION
    message = "Must select at least one node and one dimension for comparison"


class ComparisonSnapshotConflictError(ConflictError):
    code = ErrorCode.COMPARISON_SNAPSHOT_CONFLICT
    message = "Snapshot was modified by someone else; please refresh and retry"


# ─── M14 行业动态 (design §13) ───


class NewsNotFoundError(NotFoundError):
    code = ErrorCode.NEWS_NOT_FOUND
    message = "Industry news not found"


class NewsLinkDuplicateError(ConflictError):
    code = ErrorCode.NEWS_LINK_DUPLICATE
    message = "This node is already linked to the news"


class NewsLinkNotFoundError(NotFoundError):
    code = ErrorCode.NEWS_LINK_NOT_FOUND
    message = "News-node link not found"


class NewsForbiddenError(AppError):
    code = ErrorCode.NEWS_FORBIDDEN
    http_status = 403
    message = "Only the creator or platform admin can modify this news"


# ─── M13 AI 需求分析 (design §13) ───


class AnalysisNodeNotFoundError(NotFoundError):
    code = ErrorCode.ANALYSIS_NODE_NOT_FOUND
    message = "Node not found or not in project"


class AnalysisProviderNotConfiguredError(ValidationError):
    code = ErrorCode.ANALYSIS_PROVIDER_NOT_CONFIGURED
    message = "AI provider is not configured for this project; go to project settings to configure"


class AnalysisProviderError(AppError):
    code = ErrorCode.ANALYSIS_PROVIDER_ERROR
    http_status = 503
    message = "AI provider call failed (transient, please retry)"


class AnalysisTimeoutError(AppError):
    code = ErrorCode.ANALYSIS_TIMEOUT
    http_status = 504
    message = "Analysis exceeded server timeout (5min)"


class AnalysisQuotaExceededError(AppError):
    code = ErrorCode.ANALYSIS_QUOTA_EXCEEDED
    http_status = 429
    message = "AI quota exceeded"


class AnalysisSaveFailedError(AppError):
    code = ErrorCode.ANALYSIS_SAVE_FAILED
    http_status = 500
    message = "Failed to save analysis result"


class AnalysisInvalidLevelError(ValidationError):
    code = ErrorCode.ANALYSIS_INVALID_LEVEL
    message = "Invalid analysis level (must be L1/L2/L3)"


# ─── M15 数据流转 (design §13) ───


class ActivityStreamProjectNotFoundError(NotFoundError):
    code = ErrorCode.ACTIVITY_STREAM_PROJECT_NOT_FOUND
    message = "Project not found or access denied"


class ActivityStreamForbiddenError(AppError):
    code = ErrorCode.ACTIVITY_STREAM_FORBIDDEN
    http_status = 403
    message = "Only project owner or editor can view activity stream"


class ActivityStreamInvalidFilterError(ValidationError):
    code = ErrorCode.ACTIVITY_STREAM_INVALID_FILTER
    message = "Invalid filter parameters: from_dt must be before to_dt"


# ─── M17 AI 智能导入 (design §13 / R-X1 第二实例 / Queue 异步) ───


class ImportTaskNotFoundError(NotFoundError):
    code = ErrorCode.IMPORT_TASK_NOT_FOUND
    message = "Import task not found"


class ImportTaskFinalizedError(ConflictError):
    code = ErrorCode.IMPORT_TASK_FINALIZED
    http_status = 409
    message = "Import task is in final state and cannot be modified"


class ImportInvalidSourceError(ValidationError):
    code = ErrorCode.IMPORT_INVALID_SOURCE
    http_status = 422
    message = "Import source is invalid (corrupted zip / unreachable git URL)"


class ImportAIProviderError(AppError):
    code = ErrorCode.IMPORT_AI_PROVIDER_ERROR
    http_status = 503
    message = "AI provider call failed after retries"


class ImportBatchInsertFailedError(AppError):
    code = ErrorCode.IMPORT_BATCH_INSERT_FAILED
    http_status = 500
    message = "Batch insert failed; transaction rolled back"


class ImportQuotaExceededError(AppError):
    code = ErrorCode.IMPORT_QUOTA_EXCEEDED
    http_status = 429
    message = "AI quota exceeded for user or project"


class ImportTaskDuplicateError(AppError):
    """idempotency 命中——非错误，service 层用此类标识复用。

    http_status=200 是有意为之（design §13 字面）：复用上次任务 = 正常返回旧 task，
    router 层 catch 此异常时改返 200 + 复用 task 响应（区别于真错误的 4xx/5xx）。
    """

    code = ErrorCode.IMPORT_TASK_DUPLICATE
    http_status = 200
    message = "Reusing previous import task (idempotency hit)"


class ImportInvalidStateTransitionError(ConflictError):
    code = ErrorCode.IMPORT_INVALID_STATE_TRANSITION
    http_status = 409
    message = "Invalid state transition"


# ─── M20 团队 (M15 sprint baseline-patch / design §13) ───
# M15 sprint 期仅注册 + R13-1 parity；M20 sprint raise caller + e2e 回归


class TeamNotFoundError(NotFoundError):
    code = ErrorCode.TEAM_NOT_FOUND
    message = "Team not found"


class TeamNameDuplicateError(ConflictError):
    code = ErrorCode.TEAM_NAME_DUPLICATE
    message = "Team name already exists for this creator"


class TeamHasProjectsError(ValidationError):
    code = ErrorCode.TEAM_HAS_PROJECTS
    message = "Cannot delete team with active projects"


class TeamOwnerRequiredError(ValidationError):
    code = ErrorCode.TEAM_OWNER_REQUIRED
    message = "Team must have at least one owner"


class TeamMemberNotFoundError(NotFoundError):
    code = ErrorCode.TEAM_MEMBER_NOT_FOUND
    message = "Team member not found"


class TeamMemberDuplicateError(ConflictError):
    code = ErrorCode.TEAM_MEMBER_DUPLICATE
    message = "User already a team member"


class TeamPermissionDeniedError(AppError):
    code = ErrorCode.TEAM_PERMISSION_DENIED
    http_status = 403
    message = "Insufficient team role for this action"


class CrossTeamMoveForbiddenError(ValidationError):
    code = ErrorCode.CROSS_TEAM_MOVE_FORBIDDEN
    message = "Cannot move project across teams in single update"


# ─── M16 AI 快照 (design §13 / §12B 后台 fire-and-forget) ───


class SnapshotNodeNotFoundError(NotFoundError):
    code = ErrorCode.SNAPSHOT_NODE_NOT_FOUND
    message = "Node not found or not in project"


class SnapshotInsufficientVersionsError(ValidationError):
    code = ErrorCode.SNAPSHOT_INSUFFICIENT_VERSIONS
    message = "At least 3 version records required to generate snapshot"


class SnapshotProviderNotConfiguredError(ValidationError):
    code = ErrorCode.SNAPSHOT_PROVIDER_NOT_CONFIGURED
    message = "AI provider is not configured for this project"


class SnapshotProviderError(AppError):
    code = ErrorCode.SNAPSHOT_PROVIDER_ERROR
    http_status = 503
    message = "AI provider call failed"


class SnapshotTimeoutError(AppError):
    code = ErrorCode.SNAPSHOT_TIMEOUT
    http_status = 504
    message = "Snapshot generation exceeded server timeout (10min)"


class SnapshotQuotaExceededError(AppError):
    code = ErrorCode.SNAPSHOT_QUOTA_EXCEEDED
    http_status = 429
    message = "AI quota exceeded"


class SnapshotSaveFailedError(AppError):
    code = ErrorCode.SNAPSHOT_SAVE_FAILED
    http_status = 500
    message = "Failed to save snapshot to dimension records"


class SnapshotTaskNotFoundError(NotFoundError):
    code = ErrorCode.SNAPSHOT_TASK_NOT_FOUND
    message = "Snapshot task not found or not accessible"


class SnapshotNotReadyError(ConflictError):
    code = ErrorCode.SNAPSHOT_NOT_READY
    message = "Snapshot task is not ready for save (status != succeeded)"


class SnapshotTaskFinalizedError(ConflictError):
    code = ErrorCode.SNAPSHOT_TASK_FINALIZED
    message = "Snapshot task is in final state and cannot be modified"


class SnapshotInvalidStateTransitionError(ConflictError):
    code = ErrorCode.SNAPSHOT_INVALID_STATE_TRANSITION
    message = "Invalid state transition"


class SnapshotZombieError(AppError):
    """audit M2 修复：cron 兜底标记的 zombie 用，service 不实际 raise；前端通过
    error_code='snapshot_zombie' 区分用户文案。R13-1 parity 守护需此类存在。"""

    code = ErrorCode.SNAPSHOT_ZOMBIE
    http_status = 504
    message = "Task abnormally exited (zombie); please retry"


class SnapshotParseFailedError(AppError):
    code = ErrorCode.SNAPSHOT_PARSE_FAILED
    http_status = 502
    message = "AI output cannot be parsed as expected JSON schema"


class SnapshotInvalidDimensionKeyError(ValidationError):
    code = ErrorCode.SNAPSHOT_INVALID_DIMENSION_KEY
    message = "selected_dimension_keys contains key not in task review_data"


class SnapshotTaskPathMismatchError(ValidationError):
    """audit M5 修复：防跨 node 攻击（save 时 task.project_id/node_id 与 URL path 不一致）。"""

    code = ErrorCode.SNAPSHOT_TASK_PATH_MISMATCH
    message = "task does not belong to the project/node in URL path"


# ─── M18 语义搜索 (design §13 line 1226-1309) ───


class InvalidQueryLengthError(AppError):
    code = ErrorCode.INVALID_QUERY_LENGTH
    http_status = 400
    message = "Query length is invalid (must be 1-200 characters)"


class SearchTimeoutError(AppError):
    code = ErrorCode.SEARCH_TIMEOUT
    http_status = 504
    message = "Search exceeded server timeout"


class PgvectorUnavailableError(AppError):
    """不抛 HTTP，仅记录——search 路由捕获后降级 keyword_only 返 200。"""

    code = ErrorCode.PGVECTOR_UNAVAILABLE
    http_status = 503
    message = "pgvector extension unavailable; falling back to keyword search"


class EmbeddingProviderFailedError(AppError):
    code = ErrorCode.EMBEDDING_PROVIDER_FAILED
    http_status = 503
    message = "Embedding provider call failed"


class EmbeddingProviderTimeoutError(AppError):
    code = ErrorCode.EMBEDDING_PROVIDER_TIMEOUT
    http_status = 504
    message = "Embedding provider timed out"


class EmbeddingTargetNotFoundError(AppError):
    """noop 路径——worker 内捕获后跳过，不写 failures。"""

    code = ErrorCode.EMBEDDING_TARGET_NOT_FOUND
    http_status = 404
    message = "Embedding target not found in business table (noop)"


class EmbeddingZombieError(AppError):
    code = ErrorCode.EMBEDDING_ZOMBIE
    http_status = 504
    message = "Embedding task abnormally exited (zombie); marked dead_letter"


class EmbeddingTaskTerminalViolationError(AppError):
    code = ErrorCode.EMBEDDING_TASK_TERMINAL_VIOLATION
    http_status = 500
    message = "Attempted transition from terminal state"


class EmbeddingTaskInvalidTransitionError(AppError):
    code = ErrorCode.EMBEDDING_TASK_INVALID_TRANSITION
    http_status = 500
    message = "Invalid embedding task state transition"


class EmbeddingBackfillAlreadyRunningError(AppError):
    code = ErrorCode.EMBEDDING_BACKFILL_ALREADY_RUNNING
    http_status = 409
    message = "A backfill is already running for this project"


class EmbeddingModelUpgradeInvalidError(AppError):
    code = ErrorCode.EMBEDDING_MODEL_UPGRADE_INVALID
    http_status = 400
    message = "Model upgrade target is invalid or not configured"


class SilentFailure(BaseException):
    """audit m6 + verify L1+N4 + fix v2 决策 3=B：非 AppError 内部失败基类。

    继承 BaseException 而非 Exception 是 by-design——使其不被通用 except Exception 捕获，
    避免业务代码无意中"吞"掉本应在调用方显式处理的失败路径。

    使用约束（必读，否则会导致进程崩溃）：
    1. 调用方必须显式 except SilentFailure 或 except (Exception, SilentFailure) 才能捕获
    2. 在跨 await 边界（如 enqueue / cron）使用，避免污染主业务调用栈
    3. 若 except 未处理，会冒泡到 asyncio event loop 顶层导致 worker / task 异常退出
       —— 这是有意行为：派生数据失败必须可见而非静默吞错

    使用场景：业务删除尾调 enqueue_delete 失败、cleanup cron 局部失败等"内部不阻塞主路径但需可见"的失败
    禁用场景：业务路径主流程（应用 AppError）/ 跨 HTTP 边界（FastAPI 不渲染 BaseException）
    """

    def __init__(self, code: "ErrorCode", message: str, **metadata: Any) -> None:
        self.code = code
        self.message = message
        self.metadata = metadata
        super().__init__(message)


class EmbeddingDeleteFailedError(SilentFailure):
    """fix v2 决策 3=B 保留：从 AppError 移到 SilentFailure 基类。

    使用场景：业务删除 commit 后 enqueue_delete 失败 → 调用方必须 except SilentFailure。
    示例正确用法::

        try:
            self.embedding_service.enqueue_delete(...)
        except SilentFailure as e:
            logger.warning(f"enqueue_delete failed (non-blocking): {e}")
            # SilentFailure 已自带写 embedding_failures 副作用

    错误用法（会导致 worker 崩溃）::

        try:
            self.embedding_service.enqueue_delete(...)
        except Exception as e:    # ❌ SilentFailure 不被捕获，冒泡崩溃
            ...
    """

    def __init__(
        self,
        target_type: str,
        target_id: "Any",
        project_id: "Any",
        **kw: Any,
    ) -> None:
        super().__init__(
            code=ErrorCode.EMBEDDING_DELETE_FAILED,
            message=f"failed to enqueue delete for {target_type}:{target_id}",
            target_type=target_type,
            target_id=target_id,
            project_id=project_id,
            **kw,
        )
