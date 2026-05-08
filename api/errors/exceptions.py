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
