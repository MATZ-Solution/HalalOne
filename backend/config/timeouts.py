"""Central duration budgets for external calls (LLM, embedding, agent turn).

Distinct from rate_limit.py (how much) and session_state.py (how long state is
kept) — this is "how long may a single call/turn take before we give up."
Env-overridable so an operator can retune without a code change.
"""
import os


def _s(name: str, default: str) -> float:
    return float(os.getenv(name, default))


LLM_TIMEOUT_S = _s("LLM_TIMEOUT_S", "30")
"""Text-only Groq calls: extracter/standard/summarizer/judge/halalify LLMs."""

VISION_LLM_TIMEOUT_S = _s("VISION_LLM_TIMEOUT_S", "60")
"""Groq vision calls (image product extraction) — needs more headroom."""

EMBEDDING_TIMEOUT_S = _s("EMBEDDING_TIMEOUT_S", "20")
"""Fireworks embedding calls. FireworksEmbeddings has no timeout kwarg of its
own (it builds an internal OpenAI client with none exposed), so this bounds
the call site via asyncio.wait_for(asyncio.to_thread(...)), not a constructor
kwarg."""

SUMMARY_TIMEOUT_S = _s("SUMMARY_TIMEOUT_S", "45")
"""Hard cap on the conversation-summarizer LLM call (main_langgraph_agent.py
compact_session). A hang (as opposed to an error) would otherwise leave the
session stuck in "compacting" forever, since the caller's try/except only
catches raised exceptions. On timeout the caller raises, which flows into
compact_session's fallback (full, un-compacted context)."""

VALKEY_TIMEOUT_S = _s("VALKEY_TIMEOUT_S", "5")
"""Socket + connect timeout for the Valkey client. Valkey is on the hot path of
nearly every request (rate limiting, session state, pubsub), so it should fail
fast rather than hang. Note: valkey.asyncio's Connection class already
defaults socket_timeout to 5 when unset, so this mostly makes an existing
implicit default explicit and operator-tunable rather than fixing a genuine
unbounded hang."""

SUPABASE_TIMEOUT_S = _s("SUPABASE_TIMEOUT_S", "20")
"""Postgrest timeout for the Supabase client (chat_store, session auth).
supabase-py's own default (DEFAULT_POSTGREST_CLIENT_TIMEOUT) is 120s, which is
bounded but too generous for a request that's also sitting behind chat_store's
own 3-attempt retry wrapper — tightened here for a snappier failure on the hot
path rather than genuinely fixing an unbounded call."""

AGENT_TIMEOUT_S = _s("AGENT_TIMEOUT_S", "120")
"""Outer bound on a full run_agent/stream_agent turn (search -> judge ->
possibly loop -> response, several LLM calls chained across up to
MAX_KEYWORD_CALLS=5 search iterations with JUDGE_MAX_RETRIES=2 each — see
utils/utils.py and nodes/node.py). This is a hang safety net sized for
realistic latency plus margin, not the theoretical worst case if every
chained call individually maxed out its own LLM_TIMEOUT_S (that sum would be
10+ minutes and defeat the point of a turn-level bound). A legitimate but
unusually slow multi-iteration run may hit this and surface a timeout to the
user rather than hang indefinitely — an accepted tradeoff. Retune via env if
production latency data says otherwise."""
