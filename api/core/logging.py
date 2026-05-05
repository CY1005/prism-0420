import logging
import sys

import structlog

from api.core.config import settings

_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def configure_logging() -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        timestamper,
    ]

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_level = logging.DEBUG if settings.app_env == "local" else logging.INFO
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(root_level)

    for name in _UVICORN_LOGGERS:
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
        lg.setLevel(root_level)


log = structlog.get_logger()
