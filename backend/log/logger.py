"""Structured logging for the backend, built on structlog.

Renders human-friendly colored lines in development and one JSON object per line
in production. The renderer is chosen by APP_ENV; the level by LOG_LEVEL.

Setting LOG_FILE_PATH additionally mirrors every record into a rotating file as
JSON — always JSON, whatever APP_ENV says — so a log shipper (Grafana Alloy) can
tail it without the terminal losing its readable output.

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
import logging.handlers
from pathlib import Path
from dotenv import load_dotenv
import structlog

load_dotenv(override=True)

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
_IS_PROD = APP_ENV in ("production", "prod")

# A bad LOG_LEVEL must not be fatal. logging.setLevel() raises ValueError on an
# unrecognised name, and because this module is imported before anything else
# starts, that takes the whole service down at boot over a typo in .env — with
# the traceback going wherever stdout happens to point. Fall back to INFO and
# say so instead.
_VALID_LEVELS = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET")
_requested_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
if _requested_level in _VALID_LEVELS:
    LOG_LEVEL = _requested_level
    _level_warning = None
else:
    LOG_LEVEL = "INFO"
    _level_warning = (
        f"LOG_LEVEL={_requested_level!r} is not a valid level "
        f"({', '.join(_VALID_LEVELS)}); falling back to INFO"
    )

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

# Log shippers (Grafana Alloy, Promtail, Vector) tail a file rather than read
# another process's stdout, so when LOG_FILE_PATH is set every record is
# mirrored into one. The file is ALWAYS JSON regardless of APP_ENV — the
# terminal is read by a human and the file by a machine, and there is no reason
# to make those agree. Unset the variable and nothing below happens: stdout
# behaviour is exactly as it was.
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "").strip()

if LOG_FILE_PATH:
    # Anchor a relative path to the backend package root rather than the current
    # working directory. Otherwise the file lands in a different place depending
    # on whether uvicorn was started from backend/ or the repo root, and the
    # shipper ends up watching a path nothing ever writes to.
    _log_path = Path(LOG_FILE_PATH)
    if not _log_path.is_absolute():
        _log_path = Path(__file__).resolve().parent.parent / _log_path
    _log_path.parent.mkdir(parents=True, exist_ok=True)

    _file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    # Rotate so a long dev session can't quietly fill the disk. encoding is
    # explicit because Windows would otherwise default to cp1252 and raise on
    # the first non-ASCII product name that gets logged.
    _file_handler = logging.handlers.RotatingFileHandler(
        _log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _file_handler.setFormatter(_file_formatter)
    _root.addHandler(_file_handler)
_root.setLevel(LOG_LEVEL)


def get_logger(name: str = "halalify"):
    """Return a structlog logger for structured events."""
    return structlog.get_logger(name)


# Structured logger for new code.
log = get_logger("halalify")

# Surface a bad LOG_LEVEL now that there is somewhere to surface it to. Emitted
# at warning level so it survives whatever level we fell back to.
if _level_warning:
    log.warning("logging.config_invalid", detail=_level_warning)

# Backward-compatible stdlib logger. Existing modules do `from log.logger import
# logger`; keep it working and rendered identically.
logger = logging.getLogger("halalify")
