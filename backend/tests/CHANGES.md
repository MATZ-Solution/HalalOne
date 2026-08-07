# Agent module — remediation change log

Every production change made in response to the unit-test findings in
[`FINDINGS.md`](./FINDINGS.md), with the defect, the fix, and why the fix is the right one.

**Scope:** `backend/agents/langgraph_agent/` only. No API, database, schema, dependency or
deployment changes.

| | |
|---|---|
| Findings raised | 16 |
| **Fixed** | **11** (§1–§9) |
| Deferred with reasons | 5 (§10) |
| Tests before | 286 passed, 9 xfailed |
| Tests after | **310 passed, 3 xfailed** (the 3 are the deferred items) |
| Files changed | 5 production files |
| Behaviour changes needing sign-off | 2 — §7 (latency) and §9 (client-visible) |

Every fix is covered by a regression test that fails if the bug returns. Nothing here was
changed on speculation: each defect was reproduced against the running code first.

---

## 1 — Filter builder emitted the literal string `"None"` for unset filters

**Finding:** #1, #2 · **Severity:** Critical · **File:** `utils/utils.py`

### Error

`build_filter_string()` iterates `filter_args.model_dump()`, which returns **all nine**
fields including the ones the LLM never set (`None`). `None` is not a list, so each unset
field fell to the `else` branch and was formatted as a quoted string:

```python
>>> build_filter_string(FilterArgs(halal_status="halal"))
'category_l1:="None" && category_l2:="None" && halal_status:="halal" && sold_in:="None" && …'
```

The only caller is `SemanticFilterSearch`. So **every semantic search carrying any filter
asked Typesense for documents whose `category_l1` is literally `"None"`** — which no
document has. It returned zero results, silently, with no exception and no log line.

### Fix

```python
if k not in FILTER_FIELDS or not v:
    continue
```

### Justification

- **Restores a broken feature.** Filtered semantic search returned nothing before this;
  it is the whole point of the `filter_args` argument on that tool.
- **Not a new convention — an existing one.** `KeywordFilterSearch` already drops falsy
  filters the same way (`tools.py:24-27`). That inconsistency is exactly why the bug
  survived: one of the two search paths worked, so it looked like a sparse database.
- **Cannot over-filter.** The change only ever *removes* clauses, so no query that
  returned results before can return fewer now.
- Fixes findings #1 and #2 together: `FilterArgs()` with nothing set now yields `""`,
  which the caller already treats as "no filtering".

---

## 2 — Filter builder did not quote multi-word list values

**Finding:** #3 · **Severity:** Medium · **File:** `utils/utils.py`

### Error

```python
>>> build_filter_string(FilterArgs(sold_in=["United Kingdom"]))
'sold_in:=[United Kingdom]'      # Typesense mis-parses at the space
```

### Fix

```python
quoted = ",".join(f'"{i}"' for i in v)
parts.append(f"{k}:=[{quoted}]")
```

### Justification

- **Aligns two builders that disagreed.** `search_collection.py:29` already quotes each
  item when building the same expression. Two functions producing the same wire format in
  two different ways is the bug.
- **The affected values are the common ones here** — country names, certification bodies
  and marketplaces are routinely multi-word.
- Single-word values are unaffected either way, so nothing that worked before changes.

---

## 3 — Intent-classifier schema contradicted the prompt and the router

**Finding:** #4 · **Severity:** Low *(originally logged Critical — see below)* ·
**File:** `models/models.py`

### Error

`classify_intent_schema` declared a property `intent`, while `CLASSIFICATION_PROMPT` tells
the model to emit `classification` and `classify_intent` reads `classification`. One of
three declarations was out of step.

### Fix

Renamed the schema property `intent` → `classification`, and documented above it why the
prompt is the binding contract here. **No change to the router.**

### Justification

- **Zero runtime effect.** `with_structured_output(..., method='json_mode')` attaches a
  plain `JsonOutputParser`; the schema is never sent to the provider and never validated
  against. Confirmed directly rather than assumed:
  ```python
  >>> type(r.last).__name__            # 'JsonOutputParser'
  >>> r.last.invoke(AIMessage(content='{"classification": "direct"}'))
  {'classification': 'direct'}         # verbatim, key untouched
  ```
- **It removes a live trap.** Under `json_mode` the mismatch is inert, but switching to
  `json_schema` or `function_calling` — a one-word edit — would make the schema binding
  and break routing instantly.

> ### ⚠️ Correction worth flagging to review
>
> This was first logged as **Critical**: "the router reads a key the schema never
> produces, so both branches are dead and every request falls through to `search_node`."
> I initially applied that fix — changing the router to read `intent`.
>
> **That was wrong, and it would have caused the exact outage the finding described.**
> Because the prompt (not the schema) shapes the reply, reading `intent` would have made
> `.get("intent")` always `None`, sending every greeting and follow-up through a full
> tool-calling search loop.
>
> It was caught by re-checking the premise before committing: the finding had been
> inferred from reading three files rather than reproduced end-to-end, and the fake LLM
> that "confirmed" it was returning `{"intent": ...}` — encoding the very assumption under
> test. Inspecting the parser LangChain actually attaches settled it. The change was
> reverted and re-aimed at the schema. **Intent routing was never broken in production.**

---

## 4 — `KeywordFilterSearch` crashed on non-string keyword values

**Finding:** #5 · **Severity:** Medium · **File:** `tools/tools.py`

### Error

`keyword_args` is typed `Dict[str, Any]`, so Pydantic validates the container but not its
contents. A model emitting a number inside `companies` / `health_info` / `typical_uses`:

```python
>>> KeywordFilterSearch.invoke({"keyword_args": {"companies": [123]}})
TypeError: sequence item 0: expected str instance, int found
```

`tool_node` does not guard `tool.invoke()`, so the exception escaped the tool, became a
`NodeError`, and the user got **"Some error occured, please try again."** — where "no
products found" was the honest answer, and where the turn could not recover.

### Fix

```python
query = " ".join(str(i) for i in v) if isinstance(v, list) else str(v)
```

### Justification

- **The input is LLM-generated, so it is untrusted by definition.** `Dict[str, Any]` is a
  deliberate escape hatch; anything reachable through it must not be able to fail a node.
- **Matches the bar the sibling tools already meet.** `SemanticFilterSearch` and
  `WebSearch` both catch broadly and return `[]`. This tool was the odd one out.
- **Coercion preserves intent.** A model that puts `123` in `companies` still means to
  search for "123"; `str()` searches for it instead of aborting the turn.

---

## 5 — `KeywordFilterSearch` crashed on documents without `canonical_id`

**Finding:** #6 · **Severity:** Low · **File:** `tools/tools.py`

### Error

The narrowing step indexed the field directly — `doc["canonical_id"]` — so any document
missing it raised `KeyError` and failed the node by the same route as §4. This fired even
on single-field queries, because the id collection sits inside the loop and runs after
*every* round, including the last one, where the ids are then never used.

### Fix

```python
if not documents:
    return []
matched_ids = [doc["canonical_id"] for doc in documents if doc.get("canonical_id")]
if matched_ids:
    active_filters["canonical_id"] = matched_ids
```

### Justification

- **A missing id should cost one document, not the whole turn.** Documents without an id
  are skipped; the rest still narrow correctly.
- **The `if matched_ids:` guard matters.** Assigning an empty list would emit
  `canonical_id:=[]`, which matches nothing — turning a missing-id blip into a silent
  empty result set. Leaving the previous filters intact is the safe degradation.
- Also flattens the redundant `top_results` temporary, making the "fields are ANDed, so
  stop at the first empty round" rule explicit.

---

## 6 — `SemanticFilterSearch` embedded the query outside its error guard

**Finding:** #7 · **Severity:** Medium · **File:** `tools/tools.py`

### Error

`embedding_model.embed_query()` is a network round-trip to Fireworks, and it sat *above*
the `try`. A provider outage, rate-limit or timeout escaped the tool and failed the node,
even though the very next line was a `try/except` that returns `[]` and logs.

### Fix

Moved the embedding call (and the params/filter construction that depends on it) inside
the existing `try`. No change to the handler.

### Justification

- **The guard was already there and already correct** — the call was simply on the wrong
  side of it. This is a scope correction, not new error handling.
- **It is the most likely failure in the tool.** A third-party inference API is less
  available than the local Typesense call that *was* guarded.
- **Failures stay visible.** The existing `log.error("tool.semantic_search.failed", …)`
  fires, so this degrades loudly in logs and quietly for the user — the correct pairing.
  A test asserts the log line, so the failure can never become silent.

---

## 7 — Search loop discarded the final round's tool calls ⚠️ behaviour change

**Finding:** #11 · **Severity:** Low · **File:** `nodes/node.py`

### Error

`search_node` increments `search_call_iterations` **before** `should_continue` reads it, so
on the last permitted round the counter already equals `MAX_SEARCH_ITERATIONS` and
`iterations < MAX_SEARCH_ITERATIONS` was false. That round's tool calls were generated and
then thrown away. Only 3 of the 4 budgeted rounds ever executed, and the discarded
`AIMessage` — carrying tool calls no `ToolMessage` ever answered — stayed in
`state["messages"]` and was handed to the response LLM.

### Fix

```python
if has_tool_calls and iterations <= MAX_SEARCH_ITERATIONS:
```

### Justification

- **The constant now means what it says.** `MAX_SEARCH_ITERATIONS = 4` grants 4 executed
  tool rounds.
- **Removes a malformed conversation.** The final LLM no longer sees an unanswered tool
  call.
- **Removes wasted work.** The 4th LLM call was previously paid for and discarded.

> **⚠️ Trade-off for review.** This raises the worst case from 4 LLM calls + 3 tool rounds
> to 5 LLM calls + 4 tool rounds — roughly 25% more tail latency **on sessions that hit the
> cap**. Typical queries resolve in 1–2 rounds and are unaffected; only already-degenerate
> sessions reach it.
>
> **If that trade is unwanted, the zero-behaviour-change alternative is one character:**
> keep this fix and set `MAX_SEARCH_ITERATIONS = 3`. That reproduces today's exact
> execution budget while still fixing the off-by-one and the dangling tool call. I chose 4
> because it matches the documented intent, but 3 is equally defensible — it is a product
> call about latency, not a correctness one.

---

## 8 — `format_results` crashed on web-sourced products

**Finding:** #15 · **Severity:** Low · **File:** `main_langgraph_agent.py`

### Error

`' '.join(product.companies)` raised `TypeError` when `companies` was `None` — true of
every web-sourced product (`verified=False`), i.e. exactly the products the agent fell
back to the web to find.

### Fix

```python
companies = " ".join(product.companies or [])
cert_bodies = " ".join(product.cert_bodies or [])
```

### Justification

- The helper is currently **dead code** (its only call site is commented out at line 73),
  so this changes no live behaviour — it defuses a crash for whoever re-enables it.
- Fixing was preferred to deleting: the call site suggests it is intended for debugging,
  and a two-token guard is cheaper than re-deriving it later.

---

## 9 — Empty-query stream event had no `"type"` ⚠️ client-visible

**Finding:** #16 · **Severity:** Low · **File:** `main_langgraph_agent.py`

### Error

`stream_agent` yields five event kinds — `results`, `web_source`, `search_results`,
`tool_status`, `reasoning` — every one carrying a `"type"` discriminator, except the
empty-query validation event:

```python
{"response": "Please enter a valid query", "documents": []}     # no "type"
```

A client routing on `event["type"]` sees an unknown event on the one path that is pure
error handling.

### Fix

```python
yield {"type": "results", "response": "Please enter a valid query", "documents": []}
```

### Justification

- `"type"` **is** the protocol for this stream; the validation event was the only message
  not speaking it.
- `"results"` is the correct value — it is a terminal event carrying `response` +
  `documents`, structurally identical to the normal final event.
- **Additive.** A client ignoring unknown keys is unaffected; a client routing on `type`
  is fixed.

> **⚠️ Confirm with the frontend before deploy.** This is the only outward-facing change
> in this pass. If any client special-cases the *absence* of `type` to detect the
> validation response, it needs updating in the same release. `run_agent` (non-streaming)
> was deliberately left alone — it has no event framing at all, so a bare payload is
> consistent there.

---

## 10 — Deferred, with reasons

Five findings were **not** fixed. Each is still pinned by a test, so none can be forgotten.

### #12 — `SEARCH_PROMPT` says `"Haram"`, the collection may store `"Haraam"` (High)

If the collection stores `"Haraam"`, every haram-filtered search silently matches nothing.
The repo's own live-search harness states the canonical values are
`Halal, Haraam, Mushbooh` and treats `"Haram"` as a typo variant.

**Why not fixed:** the evidence is a comment in a test harness, not the database. The risk
is symmetric — if the collection really stores `"Haram"`, changing the prompt *breaks a
working path*. Local Typesense is not reachable from this environment, so I could not
confirm.

**To close (~1 minute, needs DB access):**
```python
TS_CLIENT.collections['halal_products'].documents.search(
    {'q':'*','query_by':'norm_name','facet_by':'halal_status','per_page':0})
```
The facet counts settle it. If `Haraam`, change the two spots in
`prompts/prompt.py` (lines ~57 and ~94-97) **and** the same two in `agents/main_agent.py`
(~318-320), then drop the `xfail`. **This is the highest-value open item.**

### #9 — Exa streaming frame format (High)

`WebSearch` parses `{"type": "results"|"done"}` events; Exa's documented `stream: true`
sends OpenAI-compatible `chat.completion.chunk` frames. If the docs are right, the web
fallback returns `[]` for every query.

**Why not fixed:** rewriting the parser correctly requires knowing whether `delta.content`
carries partial JSON tokens or whole objects — that cannot be determined offline, and a
wrong guess replaces a broken path with a differently broken one. **Needs one captured
live Exa response**, then the rewrite is straightforward.

### #8 — Exa 10-property schema cap (Low)

`WEB_OUTPUT_SCHEMA` uses all 10 properties Exa allows, so web products can never carry
`health_info`, `typical_uses` or `barcodes`. Adding one makes Exa reject **every** request,
and the error is swallowed — a silent web-search outage.

**Why not fixed:** it is a trade, not a bug — something must be dropped to add something.
That is a product call. A test now fails loudly if the count ever exceeds 10.

### #14 — `load_dotenv(override=True)` (Medium)

Overrides the test environment shim at import, and makes `KEEP_MESSAGES` a hidden function
of `.env`.

**Why not fixed:** `override=True` appears in **4 files including `main.py`**, the FastAPI
entrypoint. Changing env-var precedence on a deployed service needs ops sign-off on how
config reaches the container, and the blast radius is far wider than the agent module. The
harm is confined to test isolation, which the tests already work around explicitly.

### #13 — Unrendered `{{...}}` in non-template prompts (Low)

`CLASSIFICATION_PROMPT` and `SEARCH_PROMPT` are passed raw as `SystemMessage`, so their
`{{...}}` escapes reach the model literally.

**Why not fixed:** harmless today — models tolerate doubled braces, and this text is what
the current prompts were tuned against. Editing a production prompt is an unmeasurable
behaviour change without an eval set. Logged as a latent trap: it only becomes real if
someone converts either prompt to a `ChatPromptTemplate`, and a test now guards that.

---

## Verification

```bash
cd backend
./venv/Scripts/python.exe -m pytest        # Windows
python -m pytest                           # elsewhere
```

**310 passed, 3 xfailed.** The 3 remaining `xfail`s are #9, #12 and #14 above — open by
decision, not by oversight.

Fully offline: no LLM, Typesense, Fireworks or Exa calls. 16 tests that previously asserted
buggy behaviour were rewritten to assert the fixed behaviour, so each fix is now guarded
rather than merely applied.

### Files changed

| File | Findings |
|---|---|
| `agents/langgraph_agent/utils/utils.py` | #1, #2, #3 |
| `agents/langgraph_agent/tools/tools.py` | #5, #6, #7 |
| `agents/langgraph_agent/nodes/node.py` | #11 |
| `agents/langgraph_agent/models/models.py` | #4, #10 |
| `agents/langgraph_agent/main_langgraph_agent.py` | #15, #16 |

### Suggested review order

1. **§3** — the corrected misdiagnosis; the one place a finding was wrong.
2. **§7** — the latency trade-off, with a one-character alternative.
3. **§9** — the only client-visible change.
4. **§10 / #12** — the highest-value open item, one query from being closed.
5. §1, §2, §4, §5, §6, §8 — contained fixes, each with a regression test.
