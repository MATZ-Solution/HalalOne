"""Shared test harness for the backend unit suite.

Two jobs:

1. **Make the agent module importable.** Several modules do work at *import* time —
   `embeddings.py` raises if `FIREWORKS_AI_API_KEY` is unset, `llm.py` raises without
   `GROQ_API_KEY`/`CEREBRAS_API_KEY`. Dummy values are placed in the environment below,
   at conftest import time (which pytest runs before it imports any test module), so a
   machine with no `.env` (CI) can still collect the suite. Note `log/logger.py` calls
   `load_dotenv(override=True)`, so a developer's real `.env` still wins locally — that
   is fine, because nothing here ever *calls* those clients.

2. **Keep every unit test off the network.** Typesense, the Fireworks embedding model,
   the Groq LLMs and Exa are all replaced by the fixtures below. A unit test that
   touches a real service is a bug in the test, not a feature.

Fixtures deliberately patch the symbol *where it is used* (e.g.
`...tools.tools.search_collection`), not where it is defined, because the agent modules
bind these names at import time.
"""
import copy
import os

# --- import-time safety net: must run before any test module imports the agent ---
os.environ.setdefault("FIREWORKS_AI_API_KEY", "test-fireworks-key")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("CEREBRAS_API_KEY", "test-cerebras-key")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "CRITICAL")

import pytest  # noqa: E402


_UNSET = object()


def _snapshot(value):
    """Deep-copy an argument so later mutation cannot rewrite the recorded history.

    Falls back to the original reference for anything not copyable (LLM clients, Pydantic
    models holding non-copyable state), which is fine — those are identity-compared.
    """
    try:
        return copy.deepcopy(value)
    except Exception:
        return value


class Recorder:
    """A stand-in callable that records how it was called and controls what it returns.

    Semantics mirror `unittest.mock` so the distinction is unambiguous:

      * ``returns=X``      — every call returns ``X`` (``X`` may itself be a list).
      * ``side_effect=[…]``— one entry is consumed per call, in order. An entry that is
        an ``Exception`` is raised rather than returned, which is how failure paths are
        exercised. Running past the end of the list fails loudly.

    ``side_effect`` wins if both are given.

    Arguments are **deep-copied** as they arrive. `KeywordFilterSearch` reuses and mutates
    one `active_filters` dict across its narrowing loop, so storing it by reference would
    make every recorded call show the *final* state — call 1 would appear to have been
    given the `canonical_id` filter that call 2 actually added. Snapshotting is what makes
    "what was this called with, at the time?" answerable.
    """

    def __init__(self, returns=None, side_effect=_UNSET):
        self.calls = []
        self._returns = returns
        self._side_effect = None if side_effect is _UNSET else list(side_effect)

    def __call__(self, *args, **kwargs):
        self.calls.append(
            {"args": _snapshot(args), "kwargs": {k: _snapshot(v) for k, v in kwargs.items()}}
        )
        if self._side_effect is not None:
            if not self._side_effect:
                raise AssertionError(
                    f"Recorder called {len(self.calls)} time(s) but its side_effect "
                    "list is exhausted — the code under test made more calls than the "
                    "test expected."
                )
            value = self._side_effect.pop(0)
        else:
            value = self._returns
        if isinstance(value, BaseException):
            raise value
        return value

    # --- assertion helpers -------------------------------------------------
    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def called(self) -> bool:
        return bool(self.calls)

    def kwargs_at(self, index: int) -> dict:
        """Keyword arguments of the call at `index` (calls are 0-based)."""
        return self.calls[index]["kwargs"]

    def set(self, returns=None, side_effect=_UNSET):
        """Reconfigure mid-test. Returns self so it can be chained onto a fixture."""
        self._returns = returns
        self._side_effect = None if side_effect is _UNSET else list(side_effect)
        return self


@pytest.fixture
def recorder():
    """Factory for `Recorder`s, so a test can build several with different returns."""
    return Recorder


@pytest.fixture
def fake_search_collection(monkeypatch):
    """Replace the Typesense keyword search used by `KeywordFilterSearch`.

    Defaults to returning no hits. Set results with
    `fake_search_collection.set(returns=[...])`, or give a per-call sequence with
    `.set(side_effect=[[hit], []])` to drive the multi-field narrowing loop.
    """
    rec = Recorder(returns=[])
    monkeypatch.setattr(
        "agents.langgraph_agent.tools.tools.search_collection", rec, raising=True
    )
    return rec


@pytest.fixture
def fake_embedding_model(monkeypatch):
    """Replace the Fireworks embedding model with a deterministic 3-dim vector."""

    class FakeEmbeddings:
        def __init__(self):
            self.calls = []
            self.vector = [0.1, 0.2, 0.3]

        def embed_query(self, text):
            self.calls.append(text)
            return self.vector

    fake = FakeEmbeddings()
    monkeypatch.setattr(
        "agents.langgraph_agent.tools.tools.embedding_model", fake, raising=True
    )
    return fake


@pytest.fixture
def fake_ts_client(monkeypatch):
    """Replace the raw Typesense client used by `SemanticFilterSearch`.

    `client.multi_search.perform` is a `Recorder`, reachable as `fake_ts_client.perform`.
    Set a raw Typesense-shaped response with `fake_ts_client.perform.set(returns={...})`,
    or `.set(side_effect=[Exception(...)])` to exercise the failure path.
    """

    class FakeMultiSearch:
        def __init__(self):
            self.perform = Recorder(returns={"results": [{"hits": []}]})

    class FakeClient:
        def __init__(self):
            self.multi_search = FakeMultiSearch()

        @property
        def perform(self):
            return self.multi_search.perform

    fake = FakeClient()
    monkeypatch.setattr(
        "agents.langgraph_agent.tools.tools.TS_CLIENT", fake, raising=True
    )
    return fake


@pytest.fixture
def stream_writer(monkeypatch):
    """Capture what a tool/node streams to the client.

    `get_stream_writer()` only works inside a running graph, so it is replaced with a
    factory returning a `Recorder`. Inspect `stream_writer.calls[i]["args"][0]` for the
    payload that was emitted.
    """
    rec = Recorder()
    monkeypatch.setattr(
        "agents.langgraph_agent.tools.tools.get_stream_writer",
        lambda: rec,
        raising=True,
    )
    return rec


@pytest.fixture
def make_product():
    """Build a Typesense-shaped product document; override any field via kwargs."""

    def _make(canonical_id="prod_1", **overrides):
        product = {
            "canonical_id": canonical_id,
            "norm_name": "halal chicken nuggets",
            "companies": ["Crestwood"],
            "halal_status": "halal",
            "cert_bodies": ["HFA"],
            "category_l1": "food",
            "category_l2": "frozen",
            "sold_in": ["United Kingdom"],
            "typical_uses": ["snack"],
            "health_info": ["high protein"],
        }
        product.update(overrides)
        return product

    return _make


# ---- chat_store fixtures ----
# These mock the async Supabase client so chat_store.py tests never touch the
# real database. The FakeQueryBuilder mirrors Supabase's fluent chaining API:
#   client.table("x").select("y").eq("k", "v").order("z").limit(n).execute()
# Each call returns `self` (for chaining), and `.execute()` returns a result
# object whose `.data` is whatever the test configured.


class _FakeResult:
    """Mimics the Supabase response object with a `.data` attribute."""
    def __init__(self, data):
        self.data = data


class _FakeQueryBuilder:
    """Fluent mock that records every call in the chain and returns a
    configurable result on `.execute()`. Supports chaining any method name
    so it matches Supabase's broad API surface without listing every method."""

    def __init__(self, data=None):
        self._data = data if data is not None else []
        self.calls = []  # [(method_name, args, kwargs), ...]

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return self

    # The Supabase client chains methods like .table().select().eq() etc.
    # Instead of listing every possible method, __getattr__ handles any call.
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a, **kw: self._record(name, *a, **kw)

    async def execute(self):
        self.calls.append(("execute", (), {}))
        return _FakeResult(self._data)

    def set_data(self, data):
        """Change the data returned by subsequent .execute() calls."""
        self._data = data
        return self


class _FakeNot:
    """Mimics `client.table(...).not_` which chains into `.in_(...)` etc."""
    def __init__(self, builder):
        self._builder = builder

    def in_(self, field, values):
        self._builder._record("not_.in_", field, values)
        return self._builder


class _FakeBucket:
    """Mimics `client.storage.from_(bucket_name)` for upload and signing."""

    def __init__(self):
        self.upload_calls = []
        self.sign_calls = []
        self._signed_urls = []  # list of dicts with signedURL key

    async def upload(self, path, data, options):
        self.upload_calls.append({"path": path, "data": data, "options": options})

    async def create_signed_urls(self, paths, ttl):
        self.sign_calls.append({"paths": paths, "ttl": ttl})
        return self._signed_urls

    def set_signed_urls(self, urls):
        """Configure what create_signed_urls returns."""
        self._signed_urls = urls
        return self


class _FakeStorage:
    """Mimics `client.storage.from_(bucket_name)`."""

    def __init__(self):
        self._buckets = {}

    def from_(self, bucket_name):
        if bucket_name not in self._buckets:
            self._buckets[bucket_name] = _FakeBucket()
        return self._buckets[bucket_name]


class FakeSupabase:
    """A fake async Supabase client. Use `set_data()` to control what the next
    query returns. Each call to `.table()` creates a fresh query builder so
    tests can inspect the chain independently.

    Usage in a test:
        fake_supabase.set_data([{"session_id": "s1", "user_id": "u1"}])
        result = await session_exists("s1", "u1")
        assert result is True
    """

    def __init__(self):
        self._data = []
        self._data_sequence = None  # for multi-call scenarios
        self._call_index = 0
        self.queries = []  # list of _FakeQueryBuilder instances
        self.storage = _FakeStorage()

    def table(self, name):
        if self._data_sequence is not None and self._call_index < len(self._data_sequence):
            data = self._data_sequence[self._call_index]
            self._call_index += 1
        else:
            data = self._data
        qb = _FakeQueryBuilder(data)
        qb._record("table", name)
        # Attach a fake `not_` property so `.not_.in_(...)` works.
        qb.not_ = _FakeNot(qb)
        self.queries.append(qb)
        return qb

    def set_data(self, data):
        """Set the data returned by every subsequent .execute(). Use for
        single-query tests."""
        self._data = data
        self._data_sequence = None
        self._call_index = 0
        return self

    def set_data_sequence(self, *datas):
        """Set data for multi-query functions. The first .table().execute()
        returns datas[0], the second returns datas[1], etc."""
        self._data_sequence = list(datas)
        self._call_index = 0
        return self


@pytest.fixture
def fake_supabase(monkeypatch):
    """Replace `get_supabase()` in chat_store with a FakeSupabase.

    Returns the fake so tests can call `.set_data(...)` to control results
    and inspect `.queries` to verify what was sent to the database.
    """
    fake = FakeSupabase()

    async def _get_fake():
        return fake

    monkeypatch.setattr("chat_store.get_supabase", _get_fake)
    return fake


@pytest.fixture
def fake_title_llm(monkeypatch):
    """Replace the title-generation LLM with a controllable fake.

    Usage:
        fake_title_llm.set(title="My Title", description="My desc")
    """
    from models.chat_title_description import LLMTitleSchema

    class FakeTitleLLM:
        def __init__(self):
            self._response = LLMTitleSchema(title="Test Title", description="Test description")
            self._should_raise = None

        def set(self, title="Test Title", description="Test description"):
            self._response = LLMTitleSchema(title=title, description=description)
            return self

        def set_error(self, exc):
            self._should_raise = exc
            return self

        async def ainvoke(self, messages):
            if self._should_raise:
                raise self._should_raise
            return self._response

    fake = FakeTitleLLM()
    # Patch the lazy-init function to return our fake.
    monkeypatch.setattr("chat_store._get_title_llm", lambda: fake)
    return fake


# ---- session_state fixtures ----
# These mock the async Valkey client so session_state.py tests never touch a
# real Redis/Valkey server.

class _FakeValkeyPipeline:
    """Buffers commands and executes them against the FakeValkey when
    execute() is called. Used by seed_history / append_history which need
    atomic multi-step writes (delete + rpush + expire in one round-trip)."""

    def __init__(self, valkey):
        self._valkey = valkey
        self._commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        pass

    def delete(self, *keys):
        self._commands.append(("delete", keys, {}))
        return self

    def rpush(self, key, *values):
        self._commands.append(("rpush", (key, *values), {}))
        return self

    def expire(self, key, seconds):
        self._commands.append(("expire", (key, seconds), {}))
        return self

    def zadd(self, key, mapping):
        self._commands.append(("zadd", (key, mapping), {}))
        return self

    async def execute(self):
        results = []
        for method, args, kwargs in self._commands:
            fn = getattr(self._valkey, method)
            result = await fn(*args, **kwargs)
            results.append(result)
        return results


class FakeValkey:
    """An in-memory fake of the async Valkey/Redis client.

    Unlike FakeSupabase (which pre-configures return values), this fake
    *actually stores and retrieves data* just like a real Redis would.
    This makes tests more natural:

        await fake_valkey.set("key", "value")
        assert await fake_valkey.get("key") == "value"

    Use `set_error(exc)` to make ALL subsequent calls raise, for testing
    the fail-open behaviour of every function in session_state.py.
    """

    def __init__(self):
        self._data = {}            # key -> string value (for SET/GET)
        self._lists = {}           # key -> [str, ...] (for RPUSH/LRANGE)
        self._sorted_sets = {}     # key -> {member: score} (for ZADD/ZREM)
        self._should_raise = None  # inject errors for fail-open testing
        self.calls = []            # [(method, args, kwargs), ...]

    def set_error(self, exc):
        """Make ALL subsequent calls raise this exception."""
        self._should_raise = exc

    def clear_error(self):
        """Stop raising and resume normal operation."""
        self._should_raise = None

    def _check_error(self):
        if self._should_raise:
            raise self._should_raise

    # ---- string commands ----

    async def set(self, key, value, nx=False, ex=None):
        self.calls.append(("set", (key, value), {"nx": nx, "ex": ex}))
        self._check_error()
        if nx and key in self._data:
            return None  # SET NX fails if the key already exists
        self._data[key] = value
        return True

    async def get(self, key):
        self.calls.append(("get", (key,), {}))
        self._check_error()
        return self._data.get(key)

    async def delete(self, *keys):
        self.calls.append(("delete", keys, {}))
        self._check_error()
        count = 0
        for k in keys:
            if self._data.pop(k, None) is not None:
                count += 1
            if self._lists.pop(k, None) is not None:
                count += 1
        return count

    async def exists(self, *keys):
        self.calls.append(("exists", keys, {}))
        self._check_error()
        return sum(1 for k in keys if k in self._data or k in self._lists)

    # ---- list commands ----

    async def lrange(self, key, start, stop):
        self.calls.append(("lrange", (key, start, stop), {}))
        self._check_error()
        lst = self._lists.get(key, [])
        if stop == -1:
            return lst[start:]
        return lst[start:stop + 1]

    async def rpush(self, key, *values):
        self.calls.append(("rpush", (key, *values), {}))
        self._check_error()
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].extend(values)
        return len(self._lists[key])

    async def expire(self, key, seconds):
        self.calls.append(("expire", (key, seconds), {}))
        self._check_error()
        # No-op in the fake — we don't simulate TTL expiry in tests.
        return 1 if key in self._data or key in self._lists else 0

    # ---- counter commands ----

    async def incr(self, key):
        self.calls.append(("incr", (key,), {}))
        self._check_error()
        current = int(self._data.get(key, "0"))
        new_val = current + 1
        self._data[key] = str(new_val)
        return new_val

    # ---- sorted-set commands ----

    async def zadd(self, key, mapping):
        self.calls.append(("zadd", (key, mapping), {}))
        self._check_error()
        if key not in self._sorted_sets:
            self._sorted_sets[key] = {}
        self._sorted_sets[key].update(mapping)
        return len(mapping)

    async def zrem(self, key, *members):
        self.calls.append(("zrem", (key, *members), {}))
        self._check_error()
        ss = self._sorted_sets.get(key, {})
        removed = sum(1 for m in members if ss.pop(m, None) is not None)
        return removed

    async def zcard(self, key):
        self.calls.append(("zcard", (key,), {}))
        self._check_error()
        return len(self._sorted_sets.get(key, {}))

    async def zremrangebyscore(self, key, min_score, max_score):
        self.calls.append(("zremrangebyscore", (key, min_score, max_score), {}))
        self._check_error()
        ss = self._sorted_sets.get(key, {})
        to_remove = [m for m, s in ss.items() if float(min_score) <= s <= float(max_score)]
        for m in to_remove:
            del ss[m]
        return len(to_remove)

    # ---- Lua script eval ----

    async def eval(self, script, numkeys, *args):
        """Simulate the four Lua scripts used across session_state.py and
        rate_limit.py, dispatched by keywords unique to each script:
          - 'zremrangebyscore' → _ADMIT_LUA  (connection cap)
          - 'incr'            → _WINDOW_LUA (fixed-window counter)
          - 'del'             → _RELEASE_LUA (pipeline lock release)
          - 'expire' only     → _RENEW_LUA  (pipeline lock renewal)
        """
        self.calls.append(("eval", (script, numkeys, *args), {}))
        self._check_error()

        if "zremrangebyscore" in script:
            # _ADMIT_LUA: prune stale entries, check capacity, add member
            key = args[0]
            cutoff = float(args[1])
            score = float(args[2])
            max_cap = int(args[3])
            conn_id = args[4]
            ss = self._sorted_sets.setdefault(key, {})
            # Remove entries with score <= cutoff (stale connections)
            ss_clean = {m: s for m, s in ss.items() if s > cutoff}
            self._sorted_sets[key] = ss_clean
            if len(ss_clean) >= max_cap:
                return 0
            ss_clean[conn_id] = score
            return 1

        if "incr" in script:
            # _WINDOW_LUA: increment counter, reject if over limit
            key = args[0]
            limit = int(args[1])
            current = int(self._data.get(key, "0"))
            new_val = current + 1
            self._data[key] = str(new_val)
            return 0 if new_val > limit else 1

        # session_state.py Lua scripts (compare-and-act on a token)
        key = args[0]
        token = args[1]
        stored = self._data.get(key)
        if stored == token:
            if "del" in script:
                self._data.pop(key, None)
                return 1
            return 1  # _RENEW_LUA — just return success
        return 0

    # ---- pipeline ----

    def pipeline(self, transaction=False):
        return _FakeValkeyPipeline(self)


@pytest.fixture
def fake_valkey(monkeypatch):
    """Replace `get_valkey()` in session_state with a FakeValkey.

    Returns the fake so tests can pre-seed data and inspect calls.
    """
    fake = FakeValkey()

    async def _get_fake():
        return fake

    monkeypatch.setattr("session_state.get_valkey", _get_fake)
    return fake


@pytest.fixture
def fake_rate_valkey(monkeypatch):
    """Replace `get_valkey()` in rate_limit with a FakeValkey and clean up
    the module-level `_local_conns` set between tests.

    Returns the fake so tests can inspect sorted sets and counters.
    """
    import rate_limit

    fake = FakeValkey()

    async def _get_fake():
        return fake

    monkeypatch.setattr("rate_limit.get_valkey", _get_fake)
    # Clean up module-level state so tests don't leak into each other.
    rate_limit._local_conns.clear()
    yield fake
    rate_limit._local_conns.clear()


# ---- main.py pipeline fixtures ----
# main.py is the "glue" that wires session_state, chat_store, pubsub, the
# agent, and rate_limit together. To test its core pipeline functions in
# isolation we replace every external call with an AsyncMock.

@pytest.fixture
def main_mocks(monkeypatch):
    """Replace every external dependency of main.py with AsyncMocks.

    Returns a dict keyed by short names so tests can configure return
    values and assert calls, e.g.:

        main_mocks["load_history"].return_value = [...]
        await _load_context("s1", "u1")
        main_mocks["publish_chunk"].assert_called_once()
    """
    from unittest.mock import AsyncMock, MagicMock
    mocks = {}

    # -- session_state functions (imported with `from session_state import ...`) --
    for name in [
        "load_history", "seed_history", "append_history", "clear_history",
        "load_summary", "save_summary", "clear_summary",
        "load_compaction", "save_compaction", "clear_compaction",
        "is_session_known", "mark_session_known", "clear_session_known",
        "is_pipeline_inflight",
    ]:
        m = AsyncMock()
        monkeypatch.setattr(f"main.{name}", m)
        mocks[name] = m

    # -- pubsub --
    mocks["publish_chunk"] = AsyncMock()
    monkeypatch.setattr("main.publish_chunk", mocks["publish_chunk"])

    # -- agent --
    mocks["stream_agent"] = MagicMock()  # will be configured per-test as an async generator
    monkeypatch.setattr("main.stream_agent", mocks["stream_agent"])

    mocks["compact_session"] = AsyncMock()
    monkeypatch.setattr("main.compact_session", mocks["compact_session"])

    # -- chat_store (imported as `import chat_store`, so patch on the module) --
    for name in [
        "session_exists", "create_session", "insert_message",
        "get_sessions", "get_messages", "get_messages_excluding_ids",
        "get_latest_summary", "generate_title_description",
        "upload_chat_image", "delete_session",
    ]:
        m = AsyncMock()
        monkeypatch.setattr(f"chat_store.{name}", m)
        mocks[f"cs_{name}"] = m

    # -- rate_limit --
    mocks["try_consume_llm"] = AsyncMock(return_value=True)
    monkeypatch.setattr("main.try_consume_llm", mocks["try_consume_llm"])

    # -- token counter (synchronous) --
    mocks["count_tokens"] = MagicMock(return_value=100)  # safely under threshold
    monkeypatch.setattr("main.count_tokens_approximately", mocks["count_tokens"])

    from session_state import IDLE_COMPACTION
    # Sensible defaults so tests don't need to configure everything:
    mocks["is_session_known"].return_value = False
    mocks["cs_session_exists"].return_value = True  # session exists in DB
    mocks["load_compaction"].return_value = dict(IDLE_COMPACTION)
    mocks["load_history"].return_value = []
    mocks["load_summary"].return_value = None
    mocks["seed_history"].return_value = True
    mocks["save_summary"].return_value = True
    mocks["cs_insert_message"].return_value = "msg-001"
    mocks["cs_generate_title_description"].return_value = ("Test Title", "Test desc")

    return mocks


# ---- main_langgraph_agent.py fixtures ----
# Tests for compact_session and stream_agent need to mock session_state,
# chat_store, and the LLM calls. We also mock the compiled search_agent
# graph so stream_agent tests don't run the real LangGraph.

@pytest.fixture
def agent_mocks(monkeypatch):
    """Replace external dependencies of main_langgraph_agent.py.

    Returns a dict of mocks keyed by short names.
    """
    from unittest.mock import AsyncMock, MagicMock
    import agents.langgraph_agent.main_langgraph_agent as agent_mod
    mocks = {}

    # -- session_state (accessed via `session_state.load_history(...)`) --
    for name in [
        "load_history", "load_summary", "save_summary", "seed_history",
        "clear_summary", "clear_history",
    ]:
        m = AsyncMock()
        monkeypatch.setattr(f"session_state.{name}", m)
        mocks[name] = m

    # -- chat_store (accessed via `chat_store.insert_summary(...)`) --
    mocks["cs_insert_summary"] = AsyncMock()
    monkeypatch.setattr("chat_store.insert_summary", mocks["cs_insert_summary"])

    # -- summarize_conversation (sync LLM call, wrapped in to_thread) --
    mocks["summarize_conversation"] = MagicMock(return_value=["Folded summary of the conversation."])
    monkeypatch.setattr(
        "agents.langgraph_agent.main_langgraph_agent.summarize_conversation",
        mocks["summarize_conversation"],
    )

    # -- the compiled search_agent graph (for stream_agent tests) --
    mocks["search_agent"] = MagicMock()
    monkeypatch.setattr(
        "agents.langgraph_agent.main_langgraph_agent.search_agent",
        mocks["search_agent"],
    )

    # Sensible defaults
    mocks["load_history"].return_value = []
    mocks["load_summary"].return_value = {}
    mocks["save_summary"].return_value = True
    mocks["seed_history"].return_value = True

    return mocks


# ---- vision_llm.py fixtures ----

@pytest.fixture
def vision_llm_mock(monkeypatch):
    """Replace the Groq vision LLM with an AsyncMock.

    Returns the mock so tests can configure `.return_value` or `.side_effect`
    to simulate different LLM response scenarios.
    """
    from unittest.mock import MagicMock, AsyncMock
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    monkeypatch.setattr("llms.vision_llm.vision_llm", mock_llm)
    return mock_llm.ainvoke


# ---- search_collection.py fixtures ----

@pytest.fixture
def ts_client_mock(monkeypatch):
    """Replace the Typesense client with a MagicMock.

    Allows tests to intercept the `.search()` call and inspect the
    search_parameters payload (especially the dynamically built filter_by string)
    without needing a live Typesense server.
    """
    from unittest.mock import MagicMock
    mock_ts = MagicMock()
    # Setup the deeply nested chain: TS_CLIENT.collections[...].documents.search()
    mock_collections = MagicMock()
    mock_collection = MagicMock()
    mock_documents = MagicMock()
    mock_search = MagicMock(return_value={"hits": []})
    
    # Wire it up
    mock_documents.search = mock_search
    mock_collection.documents = mock_documents
    
    # We use a side_effect or just return the same mock_collection for any key
    mock_collections.__getitem__.return_value = mock_collection
    mock_ts.collections = mock_collections

    monkeypatch.setattr("collection.search.search_collection.TS_CLIENT", mock_ts)
    
    # Return the inner search mock so tests can easily assert what it was called with
    return mock_search
