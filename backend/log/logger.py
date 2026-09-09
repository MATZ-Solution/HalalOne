"""Structured logging for the backend, built on structlog.

Renders human-friendly colored lines in development and one JSON object per line
in production (captured by AWS CloudWatch from stdout). The renderer is chosen by
APP_ENV; the level by LOG_LEVEL.

Two things are exported:
  * ``log``    — a structlog logger for structured events: ``log.info("evt", k=v)``.
  * ``logger`` — a stdlib logger kept for backward compatibility. Existing
                 ``logger.info(f"...")`` calls keep working and are rendered in the
                 SAME format, and — because stdlib records pass through the shared
                 processor chain — they also inherit whatever correlation context
                 (request_id / user_id / session_id) is bound for the current task.

So an internal failure logged deep in a node/tool/valkey helper comes out in the
same shape, and correlated to the same request, as the outer process events.
"""
import os
import sys
import logging
from dotenv import load_dotenv
import structlog

load_dotenv(override=True)

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
_IS_PROD = APP_ENV in ("production", "prod")

# Processors shared by structlog-native events and bridged stdlib records, so the
# two streams are indistinguishable in the output.
_TIMESTAMPER = structlog.processors.TimeStamper(fmt="iso", utc=True)
_SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,   # pull in request_id/user_id/session_id
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    _TIMESTAMPER,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,       # render exc_info=True / exceptions
]

_renderer = (
    structlog.processors.JSONRenderer()
    if _IS_PROD
    else structlog.dev.ConsoleRenderer(colors=True)
)

# structlog-native loggers: run the shared chain, then hand off to stdlib so a
# single handler/formatter renders everything.
structlog.configure(
    processors=_SHARED_PROCESSORS + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# The one formatter every record (native + foreign/stdlib) is rendered through.
_formatter = structlog.stdlib.ProcessorFormatter(
    foreign_pre_chain=_SHARED_PROCESSORS,   # applied to plain stdlib records
    processors=[
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        _renderer,
    ],
)

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_formatter)

_root = logging.getLogger()
_root.handlers.clear()
_root.addHandler(_handler)
_root.setLevel(LOG_LEVEL)


def get_logger(name: str = "halalify"):
    """Return a structlog logger for structured events."""
    return structlog.get_logger(name)


# Structured logger for new code.
log = get_logger("halalify")

# Backward-compatible stdlib logger. Existing modules do `from log.logger import
# logger`; keep it working and rendered identically.
logger = logging.getLogger("halalify")
