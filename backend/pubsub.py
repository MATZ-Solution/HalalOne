"""Cross-instance delivery of pipeline output.

A pipeline outlives the socket that started it: the browser reloads, the old
connection dies, and the new one may land on any instance in the fleet. So
pipeline chunks are never written straight to a socket. They are published to a
per-user Valkey channel, and every live connection for that user subscribes and
forwards whatever arrives. One delivery path, identical whether the pipeline and
the socket happen to share an instance or not.

Every chunk already carries its session_id and the client routes by it, so a
single per-user channel serves all of that user's sessions and tabs.

Fire-and-forget by design: pub/sub has no replay, so a chunk published while the
user has nothing connected is simply dropped. That is fine — the pipeline
persists the assistant message BEFORE publishing it (see _stream_and_persist), so
the durable copy is always in the DB and a reconnect picks it up via chat_history.
The channel carries live progress; the database is the source of truth.
"""
import json

from config.valkey_client import get_valkey
from log.logger import log


def user_channel(user_id: str) -> str:
    return f"chat:user:{user_id}"


async def publish_chunk(user_id: str, session_id: str, payload: dict) -> None:
    """Fan one pipeline chunk out to every connection this user has open.

    Best-effort: a publish failure loses live progress, never data — the answer
    is already persisted by the time the terminal chunk goes out.
    """
    try:
        vk = await get_valkey()
        await vk.publish(user_channel(user_id), json.dumps({**payload, "session_id": session_id}))
    except Exception as e:
        log.warning("pubsub.publish.failed", error=str(e), error_type=type(e).__name__)


async def subscribe_user(user_id: str):
    """Subscribe to a user's channel and return the live PubSub handle.

    Awaited before the receive loop starts so the subscription is established
    before the client can ask for anything — otherwise a pipeline finishing in
    that gap would publish into the void.
    """
    vk = await get_valkey()
    pubsub = vk.pubsub()
    await pubsub.subscribe(user_channel(user_id))
    return pubsub


async def close_pubsub(pubsub) -> None:
    """Unsubscribe and hand the connection back to the pool."""
    try:
        await pubsub.aclose()
    except Exception as e:
        log.debug("pubsub.close.failed", error=str(e), error_type=type(e).__name__)
