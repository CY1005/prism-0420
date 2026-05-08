from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from api.auth import tenant_filter
from api.core.config import settings
from api.core.db import SessionLocal, engine
from api.core.logging import configure_logging, log
from api.core.redis import get_redis
from api.dao.project_dao import M02TenantContext
from api.errors import register_exception_handlers
from api.routers import (
    analyze_router,
    cold_start_router,
    comparison_router,
    competitor_router,
    dimension_router,
    issue_router,
    module_relation_router,
    node_router,
    overview_router,
    project_router,
    version_router,
)
from api.routers import auth as auth_router
from api.services.auth_service import get_auth_service
from api.services.dimension_service import DimensionService
from api.services.node_service import register_child_service

configure_logging()


def _validate_startup_config() -> None:
    """ADR-004 §3.3 部署约束：INTERNAL_TOKEN 长度校验。

    - prod: < 32 字节 raise（阻断启动）
    - 非 prod: < 16 字节 warning，≥16 字节通过
    """
    token = settings.internal_token
    if settings.app_env == "prod":
        if len(token) < 32:
            raise RuntimeError("INTERNAL_TOKEN must be >= 32 bytes in prod (ADR-004 §3.3)")
    else:
        if len(token) < 16:
            log.warning(
                "config.internal_token_short",
                env=settings.app_env,
                length=len(token),
                hint="dev allows >= 16 bytes; prod requires >= 32",
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_startup_config()
    # M02 子片 2: 注入 TenantContext concrete impl (覆盖 B2.4 scaffold Protocol)
    tenant_filter.set_tenant_context(M02TenantContext())
    # M04 子片 3: R-X2 第一真注入（M03 delete_node 调下游 → DimensionService 清下游）
    register_child_service("dimension", DimensionService().delete_by_node_id)
    # M06 子片 3: R-X2 第二真注入（CompetitorService 清 competitor_refs）
    from api.services.competitor_service import CompetitorService

    register_child_service("competitor", CompetitorService().delete_by_node_id)
    # M07 子片 3: R-X2 **第三真注入（orphan 语义）** — IssueService 游离化 issues
    from api.services.issue_service import IssueService

    register_child_service("issue", IssueService().orphan_by_node_id)
    # M08 子片 3: R-X2 **第四真注入（双向 + delete 语义）** — ModuleRelationService
    from api.services.module_relation_service import ModuleRelationService

    register_child_service("module_relation", ModuleRelationService().delete_by_node_id)
    log.info(
        "app.startup",
        version="0.1.0",
        tenant_context="M02 (project_members)",
        child_services=["dimension", "competitor", "issue", "module_relation"],
    )
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        try:
            async with SessionLocal() as db:
                created = await get_auth_service().bootstrap_admin_if_empty(
                    db,
                    email=settings.bootstrap_admin_email,
                    password=settings.bootstrap_admin_password,
                    name=settings.bootstrap_admin_name,
                )
            if created is not None:
                log.info("app.bootstrap_admin_created", email=created.email)
        except Exception as exc:  # noqa: BLE001
            log.warning("app.bootstrap_admin_failed", error=str(exc))
    else:
        log.info("app.bootstrap_admin_skipped", reason="env not set")
    yield
    log.info("app.shutdown")


app = FastAPI(title="prism-0420", version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)
app.include_router(auth_router.router)
app.include_router(project_router.router)
app.include_router(node_router.router)
app.include_router(dimension_router.router)
app.include_router(dimension_router.completion_router)
app.include_router(version_router.router)
app.include_router(competitor_router.competitor_router)
app.include_router(competitor_router.competitor_ref_router)
app.include_router(issue_router.issue_router)
app.include_router(issue_router.issue_node_router)
app.include_router(module_relation_router.relation_router)
app.include_router(module_relation_router.relation_node_router)
app.include_router(overview_router.overview_router)
app.include_router(cold_start_router.cold_start_router)
app.include_router(comparison_router.comparison_router)
app.include_router(analyze_router.analyze_router)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/readyz")
async def readyz() -> dict[str, object]:
    pg_ok = False
    redis_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pg_ok = True
    except Exception:
        pg_ok = False

    redis = get_redis()
    try:
        redis_ok = bool(await redis.ping())
    except Exception:
        redis_ok = False
    finally:
        await redis.aclose()

    return {"pg": pg_ok, "redis": redis_ok, "ok": pg_ok and redis_ok}
