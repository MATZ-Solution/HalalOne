# Agent module — QA findings

Defects found while unit-testing `backend/agents/langgraph_agent/`, layer by layer.
Every finding was reproduced against the running code, not inferred from reading it.

Each one is pinned by a test. Open defects are marked `xfail(strict=True)`, so the suite
stays green and turns **red the moment the bug is fixed** (reported as `XPASS`) — the
signal to delete the marker and let the test guard the fix from then on.

**Status as of the remediation pass: 11 of 16 fixed, 5 deferred.** Every fix, and the
reasoning behind each deferral, is written up for review in
[`CHANGES.md`](./CHANGES.md). Suite: **310 passed, 3 xfailed**.

Status legend: 🟢 fixed (guarded by a regression test) · 🟡 deferred (needs a decision or
an external confirmation — still `xfail`/characterised) · 🔵 re-diagnosed

| # | Severity | Component | Summary | Status |
|---|----------|-----------|---------|--------|
| 1 | **Critical** | `utils.build_filter_string` | Unset filters emit `field:="None"`, so semantic search with any filter matches nothing | 🟢 fixed |
| 2 | **High** | `utils.build_filter_string` | An empty `FilterArgs()` produces the most restrictive filter possible instead of no filter | 🟢 fixed |
| 3 | Medium | `utils.build_filter_string` | List values are unquoted, so multi-word values mis-parse | 🟢 fixed |
| 4 | ~~Critical~~ **Low** | `models.classify_intent_schema` | **Re-diagnosed — the original code was correct.** `json_mode` never validates against the schema, and the prompt asks for `classification`, so the router reading `classification` was right; the *schema* was the one out of step | 🔵 fixed in the schema |
| 5 | Medium | `tools.KeywordFilterSearch` | Non-string keyword values crash the tool, failing the whole node | 🟢 fixed |
| 6 | Low | `tools.KeywordFilterSearch` | Unguarded `doc["canonical_id"]`, and it runs on the final round where it is useless | 🟢 fixed |
| 7 | Medium | `tools.SemanticFilterSearch` | `embed_query()` runs outside the `try/except`, so an embedding-provider failure crashes the node | 🟢 fixed |
| 8 | Low | `web_search.WEB_OUTPUT_SCHEMA` | Schema sits exactly at Exa's 10-property cap, so web-fallback products can never carry `health_info` / `typical_uses` / `barcodes` | 🟡 deferred — needs a product call on which field to trade |
| 9 | **High** | `web_search.stream_web_search` / `tools.WebSearch` | Parses `{"type": "results"\|"done"}` events, but Exa's `stream: true` sends OpenAI-compatible `chat.completion.chunk` frames — the web fallback can never return a product | 🟡 deferred — rewrite needs a live Exa stream to confirm delta semantics |
| 10 | Low | `models.FilterArgs` | The list fields' comment promises `[]` defaults "for easier handling" but they actually default to `None` — a misleading contract for every consumer | 🟢 fixed (comment corrected; defaults kept) |
| 11 | Low | `nodes.should_continue` | The search-loop cap is off by one: only 3 of the 4 `MAX_SEARCH_ITERATIONS` rounds ever execute their tool calls — the 4th round is always discarded, and the response LLM is handed an unanswered tool-call message | 🟢 fixed — **changes worst-case latency, see CHANGES.md** |
| 12 | **High** | `prompts.SEARCH_PROMPT` | Normalises `halal_status` to `"Haram"` (one `a`), but the collection stores `"Haraam"` (two `a`'s) — exact-match haram filters silently match nothing | 🟡 deferred — one live Typesense query decides it; guessing wrong breaks a working path |
| 13 | Low | `prompts` | `CLASSIFICATION_PROMPT` / `SEARCH_PROMPT` carry `{{...}}` template escapes that are never rendered (passed raw as `SystemMessage`), while `FINAL_RESPONSE_PROMPT` is a real template — an inconsistent split that silently changes what the model sees if one gets templatised | 🟡 deferred — harmless today; editing a prompt is an unmeasurable behaviour change |
| 14 | Medium | `main_langgraph_agent` | `load_dotenv(override=True)` at import silently overrides `conftest.py`'s environment shim with the repo `.env` (`APP_ENV=test` → `development`, dummy API keys → real ones), and makes `KEEP_MESSAGES` a hidden function of `.env` (`SUMMARY_KEEP_TURNS=1` → 2 instead of the documented 20) | 🟡 deferred — spans 4 files incl. the app entrypoint; needs ops sign-off |
| 15 | Low | `main_langgraph_agent` | `format_results` is dead code (only a commented-out call) that would crash on web-sourced products — `' '.join(product.companies)` with no `companies` | 🟢 fixed |
| 16 | Low | `main_langgraph_agent` | `stream_agent`'s empty-query event is the only event without a `"type"` discriminator (`{"response", "documents"}` vs `{"type": "results", ...}`), so a client keying on event type gets an untyped event | 🟢 fixed — **client-visible, confirm with frontend** |

**Layers covered so far:** Layer 1 (`utils`) ✅ · Layer 2 `KeywordFilterSearch` ✅ ·
`SemanticFilterSearch` ✅ · `WebSearch` (schema + `stream_web_search` + tool) ✅ ·
`models` (schemas, inputs, state) ✅ · Layer 3 (`prompts`) ✅ · Layer 4 (`nodes`) ✅ ·
Layer 5 (`LLMs` + streaming / summarization) ✅.

---

## 1 — Unset filter fields are emitted as the literal string `"None"`

**Severity:** Critical — silent wrong results, no exception, no log line.
**Where:** [`utils/utils.py:15-26`](../agents/langgraph_agent/utils/utils.py#L15-L26)
**Pinned by:** `test_utils.py::TestKnownDefects::test_unset_fields_are_omitted`

### Reproduction

```python
>>> build_filter_string(FilterArgs(halal_status="halal"))
'category_l1:="None" && category_l2:="None" && halal_status:="halal" && sold_in:="None"
 && cert_bodies:="None" && cert_numbers:="None" && fda_numbers:="None"
 && barcodes:="None" && marketplace:="None"'
```

### Cause

`FilterArgs` defaults all nine fields to `None`. `model_dump()` returns every field,
including the unset ones. `None` is not a `list`, so each unset field falls through to
the `else` branch and is formatted as a quoted string:

```python
for k, v in filter_args.model_dump().items():
    if k not in FILTER_FIELDS:
        continue
    if isinstance(v, list):
        parts.append(f'{k}:=[{",".join(str(i) for i in v)}]')
    else:
        parts.append(f'{k}:="{v}"')   # <-- v is None -> 'category_l1:="None"'
```

### Impact

`build_filter_string` has exactly one caller: `SemanticFilterSearch`
([`tools/tools.py:73-75`](../agents/langgraph_agent/tools/tools.py#L73-L75)). Whenever the
LLM supplies *any* `filter_args`, Typesense is asked for documents whose `category_l1` is
literally the string `"None"` — which no document has. **Semantic search returns zero
results for every filtered query.** The tool returns `[]`, the agent reports "no products
found", and nothing is logged, so it looks like a sparse database rather than a bug.

Note `KeywordFilterSearch` is unaffected: it builds its filters separately at
[`tools.py:24-27`](../agents/langgraph_agent/tools/tools.py#L24-L27) and drops falsy
values with `if v`. That inconsistency is why the bug survived — one of the two search
paths works fine.

### Suggested fix

Skip falsy values, matching what `KeywordFilterSearch` already does:

```python
for k, v in filter_args.model_dump().items():
    if k not in FILTER_FIELDS or not v:
        continue
```

This resolves findings 1 and 2 together.

---

## 2 — `FilterArgs()` with nothing set is not treated as "no filters"

**Severity:** High.
**Where:** same function.
**Pinned by:** `test_utils.py::TestKnownDefects::test_all_unset_is_equivalent_to_no_filters`

`build_filter_string(FilterArgs())` returns nine `:="None"` clauses rather than `""`.
The caller guards with `if filter_str:`, so an empty string correctly means "no
filtering" — but the function never returns one for a constructed-but-empty model. Same
root cause and same fix as finding 1; listed separately because it is a distinct caller
contract (`None` and `FilterArgs()` should behave identically, and today they do not).

---

## 3 — List filter values are interpolated unquoted

**Severity:** Medium — only bites values containing spaces, but those are common here
(country names, certification bodies, marketplaces).
**Where:** [`utils/utils.py:23`](../agents/langgraph_agent/utils/utils.py#L23)
**Pinned by:** `test_utils.py::TestKnownDefects::test_list_values_containing_spaces_are_quoted`

```python
>>> build_filter_string(FilterArgs(sold_in=["United Kingdom"]))
'... && sold_in:=[United Kingdom] && ...'      # Typesense mis-parses at the space
```

The other filter builder in this codebase quotes each item
([`search_collection.py:29`](../collection/search/search_collection.py#L29)):

```python
quoted = ",".join(f'"{i}"' for i in v)
```

So the two filter builders disagree on the same wire format. Align this one with it:

```python
if isinstance(v, list):
    quoted = ",".join(f'"{i}"' for i in v)
    parts.append(f"{k}:=[{quoted}]")
```

---

## 4 — `classify_intent_schema` declares a key nothing uses *(re-diagnosed)*

> **Correction.** This was first logged as Critical: "the router reads `classification`,
> the schema declares `intent`, so both branches are unreachable and every request falls
> through to `search_node`." **That diagnosis was wrong, and acting on it would have
> caused the outage it described.** The severity is Low and the fix belongs in the schema,
> not the router. The original write-up is superseded by what follows.

**Severity:** Low — a contradiction between three declarations, with no runtime effect.
**Where:** [`models/models.py:17-29`](../agents/langgraph_agent/models/models.py#L17-L29)
**Pinned by:** `test_models.py::TestClassifyIntentSchema` (schema/router/prompt agreement)
and `test_nodes.py::TestClassifyIntent` (routing behaviour)

### What is actually true

`with_structured_output(schema, method='json_mode')` attaches a plain `JsonOutputParser`.
It does **not** send the schema to the provider and does **not** validate or remap the
reply. Verified directly:

```python
>>> r = extracter_llm.with_structured_output(classify_intent_schema, method='json_mode')
>>> type(r.last).__name__
'JsonOutputParser'
>>> r.last.invoke(AIMessage(content='{"classification": "direct"}'))
{'classification': 'direct'}          # returned verbatim, key untouched
```

So the reply's shape is dictated entirely by `CLASSIFICATION_PROMPT`, which instructs the
model to emit `{{"classification": "search"}}` / `{{"classification": "direct"}}` and
repeats it across nine worked examples. The router reading `.get("classification")` was
therefore reading **the key that actually arrives**. Intent routing worked.

The real defect is narrower: `classify_intent_schema` was the only one of the three
declarations (schema / prompt / router) using `intent`. It misleads every reader — as it
did here — and would become a live bug the moment anyone switched the call to
`method='json_schema'` or `function_calling`, where the schema *is* enforced.

### Fix applied

Renamed the schema property `intent` → `classification`, so all three agree. Zero runtime
effect under `json_mode` (the schema is never transmitted). The tests now assert the
agreement in both directions, so the next person to touch any one of the three gets a
failure instead of a plausible-looking contradiction.

### Lesson for the register

The finding was inferred from reading three files, not reproduced end-to-end — the one
finding here that skipped the "reproduce it first" rule, and the one that was wrong. A
fake LLM returning `{"intent": ...}` "confirmed" it, but that fixture encoded the very
assumption under test. What settled it was inspecting the parser LangChain actually
attaches.

---

## 5 — Non-string keyword values crash the tool instead of degrading

**Severity:** Medium — reachable purely from LLM output, and it fails the node rather
than the search.
**Where:** [`tools/tools.py:40`](../agents/langgraph_agent/tools/tools.py#L40)
**Pinned by:** `test_tools_keyword_search.py::TestMalformedLLMArguments::test_non_string_list_items_raise_typeerror`
(a characterisation test — it asserts the crash, so it fails loudly once this is fixed),
plus the schema-side root cause in
`test_models.py::TestKeywordFilterInput::test_keyword_args_accepts_any_value_types`

### Reproduction

```python
>>> KeywordFilterSearch.invoke({"keyword_args": {"companies": [123]}})
TypeError: sequence item 0: expected str instance, int found
```

### Cause

`KeywordFilterInput.keyword_args` is typed `Dict[str, Any]`, so Pydantic validates that
it *is* a dict but nothing about the values inside. The query is then built with:

```python
query = " ".join(v) if isinstance(v, list) else v
```

which requires every item to be a `str`. A model emitting a numeric barcode, year, or
quantity inside `companies` / `health_info` / `typical_uses` is enough.

### Impact

`tool_node` calls `tool.invoke(...)` with no exception handling
([`node.py:91`](../agents/langgraph_agent/nodes/node.py#L91)), so the `TypeError` escapes
the node, becomes a `NodeError`, and `default_error_handler` returns *"Some error
occured, please try again."*. The user sees a failure where "no products found" would
have been the honest answer — and the conversation cannot recover, because the bad tool
call is what ended the turn.

Both sibling tools already degrade instead of crashing: `SemanticFilterSearch`
([`tools.py:81-83`](../agents/langgraph_agent/tools/tools.py#L81-L83)) and `WebSearch`
([`tools.py:119-121`](../agents/langgraph_agent/tools/tools.py#L119-L121)) each catch
broadly and return `[]`. This tool is the odd one out.

### Suggested fix

Coerce rather than assume, and match the siblings' defensive posture:

```python
query = " ".join(str(i) for i in v) if isinstance(v, list) else str(v)
```

---

## 6 — `doc["canonical_id"]` is unguarded, and runs a round too many

**Severity:** Low — depends on a document lacking what should be a mandatory field.
Logged because the fix is one character and the failure mode is a hard crash.
**Where:** [`tools/tools.py:49`](../agents/langgraph_agent/tools/tools.py#L49)
**Pinned by:** `test_tools_keyword_search.py::TestMalformedLLMArguments::test_document_without_canonical_id_raises_keyerror`

```python
>>> # search_collection returns [{"norm_name": "no id here"}]
>>> KeywordFilterSearch.invoke({"keyword_args": {"norm_name": "a"}})
KeyError: 'canonical_id'
```

Two things worth noting:

1. **Direct indexing.** Any indexed document missing `canonical_id` crashes the tool, and
   by the same route as finding 5 it fails the whole node. `.get("canonical_id")` (with
   `None`s filtered out) removes the crash.
2. **It runs on the final round too.** The id collection sits inside the `for` loop, so it
   also executes after the *last* keyword field — where the collected ids are assigned to
   `active_filters` and then never read again. So the single-field case, which has no
   narrowing to do at all, can still crash on dead work. Guarding the assignment to
   non-final rounds would make the intent clearer and shrink the blast radius.

---

## 7 — `SemanticFilterSearch` embeds the query outside its error guard

**Severity:** Medium — reachable purely from external provider downtime, and it fails the
node rather than the search.
**Where:** [`tools/tools.py:63-64`](../agents/langgraph_agent/tools/tools.py#L63-L64)
**Pinned by:** `test_tools_semantic_search.py::TestFailurePaths::test_embedding_failure_escapes_the_tool`
(a characterisation test — it asserts the crash, so it fails loudly once the call is guarded)

### Reproduction

```python
>>> # embedding_model.embed_query raises (Fireworks down / rate-limited)
>>> SemanticFilterSearch.invoke({"semantic_query": "x"})
RuntimeError: embedding provider down
```

### Cause

The `try/except` starts *after* the embedding call and the filter-string build:

```python
embedding = embedding_model.embed_query(semantic_query)   # <-- outside the try
embedding_str = ",".join(map(str, embedding))
...
filter_str = build_filter_string(filter_args)             # <-- also outside
...
try:
    result = TS_CLIENT.multi_search.perform(...)
    ...
except Exception as e:
    log.error("tool.semantic_search.failed", ...)
    return []
```

The tool's *own* failure guard only covers the Typesense round-trip and response parsing.
The sibling `KeywordFilterSearch` has the same escape-hatch problem (finding 5), but that
path is LLM-output-dependent; this one fires whenever the embedding API is unreachable —
the exact failure mode `try/except` in the rest of the tool exists to absorb.

### Impact

An `embed_query` failure escapes the tool, becomes a `NodeError` via `tool_node`
([`node.py:91`](../agents/langgraph_agent/nodes/node.py#L91)), and the user gets *"Some
error occured, please try again."* instead of *"no products found"* — and the bad tool
call ends the turn, so the conversation cannot recover. The Typesense failure path in the
same function handles this correctly (returns `[]` and logs), which is what makes the
inconsistency visible.

### Suggested fix

Move the embed call and filter build inside the existing `try`, so every external failure
degrades identically:

```python
try:
    embedding = embedding_model.embed_query(semantic_query)
    embedding_str = ",".join(map(str, embedding))
    ...
    result = TS_CLIENT.multi_search.perform({"searches": [params]}, {})
    ...
except Exception as e:
    log.error("tool.semantic_search.failed", error=str(e), error_type=type(e).__name__)
    return []
```

---

## 8 — Web-fallback products can never carry `health_info`, `typical_uses`, or `barcodes`

**Severity:** Low — a coverage gap on the fallback path, not a crash.
**Where:** [`web_search.py:29-47`](../agents/langgraph_agent/tools/web_search.py#L29-L47)
**Pinned by:** `test_web_search_schema.py::TestConsistencyWithProductModel::test_fallback_products_lack_health_info_typical_uses_and_barcodes`
(a characterisation test — it asserts the fields are absent, so it trips the moment one
is re-enabled, and the cap test next to it forces the compensating removal)

### Reproduction

Static inspection of the constant:

```python
>>> set(WEB_OUTPUT_SCHEMA["properties"]) - (KEYWORD_FIELDS | FILTER_FIELDS)
set()
>>> (KEYWORD_FIELDS | FILTER_FIELDS) - set(WEB_OUTPUT_SCHEMA["properties"])
{'barcodes', 'health_info', 'typical_uses'}
```

### Cause

Exa caps structured-output schemas at **10 properties** (max nesting depth 2, per its
docs), and the schema uses all 10. `health_info`, `typical_uses` and `barcodes` were the
"lower-value" fields cut to stay within the limit, so they are commented out. There is
nothing left in the budget: re-enabling any one of them pushes the count to 11 and Exa
rejects every request — and because `stream_web_search` catches the `HTTPError`, yields
nothing, and `WebSearch` returns `[]`, the failure would be silent.

### Impact

`health_info` and `typical_uses` are DB keyword fields the *DB* path searches on. When
the DB has no match and the agent escalates to the web, the synthesized product arrives
without the exact attributes the user asked about ("high protein" → `health_info`,
"baking" → `typical_uses`). `_CANDIDATE_FIELDS` in `node.py` also lists all three for the
final LLM to judge relevance, so web results can never satisfy those queries.

### Note

Everything else about the schema checks out: all 10 properties exist on `OutputSchema`
(so `_project` keeps them), every field has a description, there are no grounding /
confidence fields (Exa returns `output.grounding` automatically), and the schema is what
`stream_web_search` actually sends as `outputSchema`. The cap test
(`TestExaConstraints::test_property_count_stays_within_exa_cap`) is what turns a future
11th property into a loud CI failure instead of a silent web-search outage.

---

## 9 — `WebSearch` parses an SSE frame format Exa does not send

**Severity:** High — the entire web-fallback path is non-functional against the real API.
**Where:** [`web_search.py:79-89`](../agents/langgraph_agent/tools/web_search.py#L79-L89) and
[`tools.py:103-118`](../agents/langgraph_agent/tools/tools.py#L103-L118)
**Pinned by:** `test_tools_web_search.py::TestExaStreamingContract::test_documented_exa_chunk_produces_a_product`
(`xfail` — the intended behaviour) and `...::test_documented_exa_chunk_is_ignored`
(a characterisation of the current behaviour)

### Reproduction

The parser expects hand-rolled events shaped `{"type": "results", ...}` and
`{"type": "done", "output": {"content": ..., "grounding": ...}}`. Feeding it the frame
shape Exa documents for `stream: true` yields nothing:

```python
>>> EXA_CHUNK = {"object": "chat.completion.chunk",
...              "choices": [{"index": 0, "delta": {"role": "assistant",
...                          "content": '{"norm_name": "KitKat"}'}, "finish_reason": None}]}
>>> EXA_CHUNK.get("type")
None                                          # neither "results" nor "done"
>>> WebSearch.invoke({"query": "x"})
[]
```

### Cause

Per Exa's Search API guide, `stream: true` switches `/search` to SSE mode and every
`data:` frame is an **OpenAI-compatible chat-completion chunk**:

```json
{"object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "..."}, "finish_reason": null}]}
```

`stream_web_search` yields each parsed frame verbatim, and `WebSearch` reads
`event.get("type")` — a key an Exa chunk never carries (`"object"` instead). So neither
the source-streaming branch nor the synthesis branch ever fires, `product` stays `None`,
and the tool returns `[]`. The same gap breaks the live "searching sources…" UX: sources
arrive as `delta.content` chunks, not as a `results` list.

### Impact

The DB path is the primary search, so this only bites after both
`KeywordFilterSearch`/`SemanticFilterSearch` return nothing. When they do, the agent
escalates to `WebSearch` — and silently gets "no products found" for every query, because
the synthesized product is never extracted from the deltas. The failure is silent
(returns `[]`, no log line), so it looks like "the web had nothing" rather than "the
parser is wrong".

### Note on provenance

This finding is grounded in Exa's official current docs (Search API guide, July 2026) and
reproduced against the running parser (a documented-format frame deterministically yields
`[]`). It was not verified with a live Exa call, since the test suite is fully offline.
If Exa's streaming format is in fact the `{"type": ...}` shape the code expects, this
finding is void — but the current docs say otherwise, and the characterisation test will
fail loudly if the parser is reworked to the chunk format.

### Suggested fix

Assemble the synthesis from the delta chunks instead of matching event `type`s:

```python
product = None
grounding = []
for event in stream_web_search(query):
    choices = event.get("choices") or []
    for choice in choices:
        content = (choice.get("delta") or {}).get("content")
        if content:
            # Exa streams the product JSON incrementally; accumulate and parse when
            # finish_reason is set, then emit web_source / take product + grounding.
            ...
```

The exact delta semantics (whether `delta.content` carries partial JSON tokens or whole
objects) need to be confirmed against a live stream before implementation.

## 10 — `FilterArgs`' list fields contradict their own default comment

**Severity:** Low — a misleading contract, not a crash.
**Where:** [`models/models.py:103`](../agents/langgraph_agent/models/models.py#L103)
**Pinned by:** `test_models.py::TestFilterArgs::test_list_fields_default_to_empty_list_per_the_comment`

### Reproduction

```python
>>> FilterArgs().sold_in
None          # comment says: "List fields (default to empty list instead of None for easier handling)"
>>> FilterArgs().model_dump()
{'category_l1': None, 'category_l2': None, 'halal_status': None, 'sold_in': None, ...}
```

### Cause

The comment at [`models.py:103`](../agents/langgraph_agent/models/models.py#L103) promises
the six list fields default to `[]` "for easier handling", but all nine fields are plain
`Optional[...] = None`. `sold_in`, `cert_bodies`, `cert_numbers`, `fda_numbers`,
`barcodes` and `marketplace` all come back `None`.

### Impact

`model_dump()` is what `build_filter_string` iterates, so every `None` here is what
becomes a `:="None"` clause (findings 1–2). Defaulting to `[]` would *not* fix those —
it would emit `field:=[]` instead — so this finding is only about the misleading
contract: a future consumer reading the comment and writing `for c in f.sold_in:` crashes
on `None`. Because `None` and `[]` both land in the same `else`/empty path once finding 1
is fixed, aligning the defaults to the comment is safe either way.

### Suggested fix

Either drop the comment, or make the fields genuinely default to empty lists — after
finding 1 lands, the two behave identically through `build_filter_string`:

```python
sold_in: Optional[list[str]] = Field(default_factory=list, description="Countries where product is sold")
```

---

## 11 — The search-loop cap discards the 4th round's tool calls

**Severity:** Low — one wasted LLM round per search session, plus a dangling tool-call
message handed to the response LLM.
**Where:** [`nodes/node.py:60-73`](../agents/langgraph_agent/nodes/node.py#L60-L73)
**Pinned by:** `test_nodes.py::TestShouldContinue::test_the_final_search_rounds_tool_calls_are_always_dropped`
and `...::test_effective_tool_budget_is_three_rounds` (characterisation tests — they pin
the current behaviour so the off-by-one is visible the moment it is fixed)

### Reproduction

`should_continue` routes to `tool_node` only while `search_call_iterations <
MAX_SEARCH_ITERATIONS` (4), and `search_call_iterations` is incremented by `search_node`
*before* the check. So round 4 is reached with `iterations == 4`:

```python
>>> state = {"messages": [AIMessage(content="x", tool_calls=[...])], "search_call_iterations": 4}
>>> should_continue(state)
'response_node'     # round 4's tool calls are dropped, never executed
```

### Impact

The LLM does not know round 4 is the last, so on every search session it spends a 4th
LLM call generating tool calls that are silently discarded. Only 3 tool rounds ever
execute. Worse, the discarded AIMessage-with-`tool_calls` stays in `state["messages"]`,
so `response_node` hands the final LLM a conversation containing an *unanswered* tool
call — no `ToolMessage` ever answered it. This is also the reason finding 6's
`KeywordFilterSearch` narrowing runs "on the final round where it is useless": that round
never gets to use its results.

### Suggested fix

Let the last round's tool calls actually run, then cap on the round *after*:

```python
if has_tool_calls and iterations <= MAX_SEARCH_ITERATIONS:
    return "tool_node"
return "response_node"
```

This makes the budget 4 executed tool rounds; the loop exits when the model stops calling
tools or the cap is crossed. The characterisation tests above flip and must be updated to
match.

## 12 — `SEARCH_PROMPT` normalises `halal_status` to a spelling the collection does not use

**Severity:** High — silent wrong results for the single most important status query
("is X halal?" → the `Haram` answer path).
**Where:** [`prompts/prompt.py:94-97`](../agents/langgraph_agent/prompts/prompt.py#L94-L97)
(and the filter table at line 57)
**Pinned by:** `test_prompts.py::TestSearchPrompt::test_halal_status_normalises_to_the_collection_spelling`
(`xfail` — the intended behaviour)

### Reproduction

The prompt tells the model the only valid `halal_status` values are `"Halal"`,
`"Haram"`, `"Mushbooh"`, and to map `"haram", "hraam", "haraam"` → `"Haram"` (one `a`):

```python
>>> '"Haram"' in SEARCH_PROMPT
True
>>> '"Haraam"' in SEARCH_PROMPT
False
```

But the repo's own live search-verification harness
([`tests/search_tests/search_tests.py:599`](../search_tests/search_tests.py#L599)) documents
the collection's values explicitly:

```
- halal_status: Only 3 values (Halal, Haraam, Mushbooh). 'Haram' (1 char short)
```

and treats `"Haram"` as a typo variant (`[TYPO] Haram (missing a — common alternate
spelling) ... should fuzzy-match to Haraam`, line 401).

### Impact

`KeywordFilterSearch` and `build_filter_string` emit exact-match filters
(`halal_status:="Haram"`). If the collection stores `"Haraam"`, every haram-filtered
search — DB keyword path *and* semantic path — matches zero documents. The agent reports
"no products found" for queries like "is this haram" / "find haram ingredients", silently,
with no log line. The three statuses are the one place this matters most: `Halal` is the
happy default and `Mushbooh` happens to match, so only the `Haram` branch is broken.

### Note on provenance

Like finding 9, this was **not** verified with a live Typesense query (the suite is fully
offline and `data/canonical_products.json` is not in the repo). It is grounded in the
repo's own search harness, which runs against the live collection and states the canonical
values outright. If the collection in fact stores `"Haram"`, this finding is void — but
the harness disagrees, and the same wrong spelling appears in the legacy
`agents/main_agent.py:318-320`, suggesting a copy-paste across both prompts.

### Suggested fix

Normalise to the stored spelling:

```python
- "haram", "hraam", "haraam" → `"Haram"`     →     - "haram", "hraam", "haraam" → `"Haraam"`
```

and update the table row at line 57 (plus the same two spots in `agents/main_agent.py`).
Confirm the live value once before applying.

---

## 13 — Unrendered `{{...}}` template escapes in the non-template prompts

**Severity:** Low — invisible until a prompt is accidentally templatised.
**Where:** [`prompts/prompt.py:10,14,18,22,…`](../agents/langgraph_agent/prompts/prompt.py#L10)
**Pinned by:** `test_prompts.py::TestTemplateSplit::test_only_final_response_prompt_has_single_brace_placeholders`
and `...::test_classification_and_search_prompts_carry_double_braces` (characterisation)

### Reproduction

```python
>>> CLASSIFICATION_PROMPT.count("{{")
10                      # "Return ONLY valid JSON: {{"classification": "search"}} ..."
>>> SEARCH_PROMPT.count("{{")
3                       # tool examples like KeywordFilterSearch(keyword_args={{...}})
>>> FINAL_RESPONSE_PROMPT.count("{{")
0                       # and it is the only prompt with real {placeholders}
```

### Cause

`CLASSIFICATION_PROMPT` and `SEARCH_PROMPT` are passed **raw** to the model
(`SystemMessage(CLASSIFICATION_PROMPT)` at `node.py:23`, `SystemMessage(SEARCH_PROMPT)` at
`node.py:52`) — never through a `ChatPromptTemplate`. Their `{{ ... }}` are the leftover
of a template format, and the model literally sees the double braces. Only
`FINAL_RESPONSE_PROMPT` is actually templated (`response_node` uses
`ChatPromptTemplate.from_template`).

### Impact

Today, nil in practice — models tolerate the doubled braces. The finding is the *latent
trap*: the moment anyone converts `CLASSIFICATION_PROMPT` or `SEARCH_PROMPT` to a
`ChatPromptTemplate`, the escapes render to single braces and the JSON examples the model
sees change silently. The two prompt families also disagree about their own format, which
is exactly the kind of drift that bites at the LLM boundary.

### Suggested fix

Make the non-template prompts plain JSON (`{"classification": "search"}`), or convert
them to real templates with single-brace placeholders — but pick one and make the split
visible.

---

## 14 — `load_dotenv(override=True)` clobbers the test environment on import

**Severity:** Medium — a silent test-environment hazard with a real, visible side
effect on module state.
**Where:** [`main_langgraph_agent.py:19`](../agents/langgraph_agent/main_langgraph_agent.py#L19)
and [`main_langgraph_agent.py:23`](../agents/langgraph_agent/main_langgraph_agent.py#L23)
**Pinned by:** `test_llm_streaming.py::test_keep_messages_uses_the_documented_default_of_ten_turns`
(`xfail` — the intended behaviour)

### Reproduction

```python
>>> import agents.langgraph_agent.main_langgraph_agent as m
>>> m.KEEP_MESSAGES
2        # docstring promises int(os.getenv("SUMMARY_KEEP_TURNS", "10")) * 2 == 20
>>> os.environ["APP_ENV"]
'development'   # conftest.py set this to "test" before the import
```

### Cause

`conftest.py` shims the environment with `os.environ.setdefault(...)` before any
agent module is imported. `main_langgraph_agent` then calls `load_dotenv(override=True)`
— and `.env` at the backend root defines the same keys plus `APP_ENV=development`
and `SUMMARY_KEEP_TURNS=1`. `override=True` means the `.env` wins over whatever
was already in the environment, so importing this one module silently replaces the
test shim with production configuration. `KEEP_MESSAGES` is read *after* that load,
so it comes up as `2` (from `SUMMARY_KEEP_TURNS=1`) instead of the documented
default `20`.

### Impact

- Any test (or test session) that imports `main_langgraph_agent` — directly or via
  the summarizer / compaction code — inherits `APP_ENV=development` and the real
  API keys from `.env`, defeating the isolation that `tests/conftest.py` exists to
  provide. A future test that gates on `APP_ENV == "test"` or verifies a dummy key
  will be wrong in a way that is invisible until it hits the network.
- `KEEP_MESSAGES` is environment-dependent at import time (2 vs 20), so
  `compact_session` behaviour differs between machines and checkouts unless the
  test patches `main.KEEP_MESSAGES` explicitly (which the Layer 5 tests do).
- `.env` also carries unparseable comment lines (`; TYPESENSE_HOST` etc.), which
  is why the import prints `python-dotenv could not parse...` warnings.

### Suggested fix

Load without overriding (default `override=False`), so env vars set before the
import — exactly what `conftest.py` does — win:

```python
load_dotenv()   # instead of load_dotenv(override=True)
```

or have `conftest.py` load the `.env` itself first and then pin the shim values.

---

## 15 — `format_results` is dead code that would crash on web-sourced products

**Severity:** Low — unreachable today, a crash waiting for someone to uncomment it.
**Where:** [`main_langgraph_agent.py:55-57`](../agents/langgraph_agent/main_langgraph_agent.py#L55-L57)
**Pinned by:** `test_llm_streaming.py::test_format_results_crashes_on_products_without_companies`
(a characterisation test — it asserts the crash, so it fails loudly once the call
is guarded)

### Reproduction

```python
>>> product = SimpleNamespace(norm_name="X", companies=None, cert_bodies=["B"])
>>> format_results([product])
TypeError: can only join an iterable
```

### Cause

`format_results`' only caller is a commented-out `# format_results(final.products)`
at line 73. Its body does `' '.join(product.companies)` and `' '.join(product.cert_bodies)`.
DB products always carry these fields, but web-sourced products (`verified=False`,
synthesised by `WebSearch`) do not — `product["companies"]` is absent, and once
uncommented the helper crashes exactly on the products the agent fell back to the
web for. (`context_token_count` at line 136 is likewise exported but never called —
a pure helper, harmless.)

### Suggested fix

Either delete the dead helper, or make it defensive and wire it in:

```python
companies = " ".join(product.companies or [])
cert_bodies = " ".join(product.cert_bodies or [])
```

---

## 16 — `stream_agent`'s empty-query event lacks the `"type"` discriminator

**Severity:** Low — a client-facing inconsistency on the error path.
**Where:** [`main_langgraph_agent.py:184-186`](../agents/langgraph_agent/main_langgraph_agent.py#L184-L186)
**Pinned by:** `test_llm_streaming.py::TestStreamAgent::test_empty_query_yields_the_validation_event_without_streaming`
(a characterisation test — it asserts the current shape)

### Reproduction

```python
>>> [e async for e in stream_agent("", [])]
[{'response': 'Please enter a valid query', 'documents': []}]     # no "type"
>>> # non-empty query ends with:
{'type': 'results', 'response': ..., 'documents': [...]}
```

### Cause

The empty-query guard yields the bare payload while every other event emitted by
`stream_agent` (`results`, `web_source`, `search_results`, `tool_status`,
`reasoning`) carries a `"type"` key. `run_agent` returns the same bare payload —
consistent there, because `run_agent` has no event framing at all.

### Impact

A streaming client that routes on `event["type"]` (as the other four event kinds
demand) treats the empty-query event as unknown. The `"type"` key is the protocol;
the validation response is the one message that doesn't speak it.

### Suggested fix

Add `"type": "results"` to the empty-query yield, or document it as the
non-streaming response envelope and have clients special-case it.

---

## Running the suite

```bash
cd backend
./venv/Scripts/python.exe -m pytest          # Windows
python -m pytest                             # elsewhere
```

`xfailed` in the summary = a known bug from this document, still open.
`XPASS` = a bug was fixed; remove its `xfail` marker and update the table above.

Findings are pinned in one of two ways, depending on how clear-cut they are:

* **`xfail(strict=True)`** (findings 1–4, 9–10, 12, 14) — outright defects or
  contracts the code contradicts. The test states the correct behaviour and is
  expected to fail today.
* **Characterisation tests** (findings 5–8, 11, 13, 15–16) — crash paths,
  degradation gaps and design choices where hardening is a judgement call, not an
  obvious defect. The test asserts what the code does *now* (via `pytest.raises`,
  or by asserting the degraded / current output), so it goes red the moment the
  behaviour changes, forcing a deliberate decision rather than a silent drift.
