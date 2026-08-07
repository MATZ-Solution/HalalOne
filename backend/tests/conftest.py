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
