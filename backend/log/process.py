"""The standard way to log a served user action.

`logged_process` wraps the body of a served action — an HTTP request or a
WebSocket message handler — and emits exactly two events around it:

    process.start   action=<name> [user_id, session_id, request_id, ...]
    process.end     action=<name> status=success|error duration_ms=<float> ...

It binds request_id / user_id / session_id into the contextvars for the duration
of the body, so EVERY log line produced while it runs — including a failure raised
deep inside a node, edge, tool or Valkey helper — is automatically correlated to
the same request and rendered in the same format.

Use it INSIDE the coroutine that runs the work (not around the spawn call), so
duration_ms measures the real end-to-end time of the action — for a streamed
prompt that's the full answer latency, not just the time to enqueue it.

    async def handle_prompt(session_id, message, token):
        async with logged_process("ws.prompt", user_id=user_id, session_id=session_id):
            async with pipeline_lease(session_id, token):
                await run_prompt_pipeline(session_id, user_id, message)
"""
import time
from uuid import uuid4
from contextlib import asynccontextmanager

from structlog.contextvars import bind_contextvars, clear_contextvars

from .logger import log


@asynccontextmanager
async def logged_process(
    action: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    **start_fields,
):
    """Log start/end (with status + duration) around a served action and bind its
    correlation context. Re-raises on error after logging process.end.

    Yields the request_id so a handler can echo it to the client if useful.
    """
    request_id = request_id or uuid4().hex
    # Each served action runs in its own asyncio task (a fresh context copy), so
    # clearing first keeps actions from leaking context into one another.
    clear_contextvars()
    ctx = {"action": action, "request_id": request_id}
    if user_id:
        ctx["user_id"] = user_id
    if session_id:
        ctx["session_id"] = session_id
    bind_contextvars(**ctx)

    started = time.perf_counter()
    log.info("process.start", **start_fields)
    try:
        yield request_id
    except Exception as exc:
        log.error(
            "process.end",
            status="error",
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
            error=str(exc),
            error_type=type(exc).__name__,
            exc_info=True,
        )
        raise
    else:
        log.info(
            "process.end",
            status="success",
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
    finally:
        clear_contextvars()
