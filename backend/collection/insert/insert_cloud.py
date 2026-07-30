# """
# TypeSense collection lifecycle — schema definition, creation, inspection.

# This module is the SINGLE source of truth for the `facilities` collection
# schema. If a field is not declared here it does not exist in the index, and
# `facility_mapper` must not emit it (TypeSense would silently drop it, which is
# worse than an error because the field just quietly stops working).

# Design notes that are not obvious from the code:

# * Every field except `id`, `name` and `rating_sort` is `optional: true`. That is
#   not defensiveness — it comes straight from the source table, where 96 of 98
#   columns are nullable `text` and most rows have large gaps. A non-optional
#   field in TypeSense causes the WHOLE document to be rejected at import time
#   when the value is missing, so one over-strict field would silently drop tens
#   of thousands of facilities.

# * `rating_sort` exists purely so `default_sorting_field` has something valid to
#   point at. TypeSense requires that field to be a non-optional int32/float, and
#   `overall_rating` is empty for the vast majority of rows. `rating_sort` is
#   always emitted (0.0 when unrated), which also reproduces Postgres's
#   `ORDER BY overall_rating DESC NULLS LAST` exactly.

# * `overall_rating` is kept as a SEPARATE optional field even though it
#   duplicates `rating_sort`. The mobile app hides the rating row when the value
#   is null; if we collapsed the two and shipped 0.0, every unrated facility
#   would render a 0-star rating. Display value and sort value have genuinely
#   different semantics here.
# """
# from __future__ import annotations

# import logging
# from typing import Any

# from typesense.exceptions import ObjectAlreadyExists, ObjectNotFound

# from app.core.config import settings
# from app.core.typesense import get_typesense_client, run_typesense

# logger = logging.getLogger("app.typesense.collection")


# # --------------------------------------------------------------------------
# # Schema
# # --------------------------------------------------------------------------

# # Fields the free-text query runs against, in descending order of importance.
# # Order matters: it defines the positional alignment of QUERY_BY_WEIGHTS and of
# # the per-field `infix` / `num_typos` strings the search service builds.
# #
# # Adding a field here is enough — everything positional is DERIVED from this
# # tuple rather than hardcoded, so the arities can never drift apart. That
# # mattered: `infix` and `num_typos` are comma-separated lists that must have
# # exactly one entry per query_by field, and a mismatched count is a runtime
# # error from TypeSense, not something a linter would catch.
# QUERY_BY_FIELDS: tuple[str, ...] = ("name", "city", "address", "state", "zip_code")

# # Matching weights, positionally aligned with QUERY_BY_FIELDS. A hit on the
# # facility name should outrank a hit on the street address — without this,
# # searching "Napa" would rank a facility on "Napa Street" in another city above
# # the facilities actually located in Napa.
# QUERY_BY_WEIGHTS: tuple[int, ...] = (4, 3, 1, 2, 3)

# # Fields declared with `"infix": True` in the schema below. Only these can use
# # infix matching at query time; asking for it on any other field is an error.
# INFIX_FIELDS: frozenset[str] = frozenset({"name", "city"})

# # Typo tolerance PER FIELD, because a single global setting is wrong here.
# #
# #   name/city  2 — people misspell "Hospice" and "Albuquerque" constantly
# #   address    1 — addresses carry digits, where edits change meaning faster
# #   state      0 — "CA" and "GA" are one edit apart. A typo-tolerant state
# #                  match would silently return the wrong state's facilities.
# #   zip_code   0 — same problem, worse: "94559" and "94558" are adjacent real
# #                  ZIPs in different places. Prefix matching still works, so
# #                  "945" narrows correctly; only edits are refused.
# FIELD_NUM_TYPOS: dict[str, int] = {
#     "name": 2,
#     "city": 2,
#     "address": 1,
#     "state": 0,
#     "zip_code": 0,
# }

# FACET_FIELDS: tuple[str, ...] = (
#     "state",
#     "city",
#     "facility_type_category",
#     "facility_type",
#     "ownership_type",
# )


# def build_schema(collection_name: str | None = None) -> dict[str, Any]:
#     """
#     Return the collection schema as TypeSense expects it.

#     A function rather than a module constant so the same schema can be applied
#     to a versioned collection name (e.g. `facilities_20260724T101500`) during a
#     zero-downtime reindex, without duplicating the field list.
#     """
#     return {
#         "name": collection_name or settings.TYPESENSE_COLLECTION,
#         "default_sorting_field": "rating_sort",
#         "enable_nested_fields": False,
#         "fields": [
#             # ---- identity ----
#             # `id` is TypeSense's reserved document key. It is always a string
#             # and is NOT declared in `fields`; the mapper supplies it from the
#             # source table's `uuid` primary key.
#             {
#                 "name": "name",
#                 "type": "string",
#                 "sort": True,  # tie-breaker for equal ratings
#                 # Prefix search ("Sunri" -> "Sunrise") works out of the box.
#                 # `infix` additionally allows mid-word matching ("ospice" ->
#                 # "Hospice"), which prefix search cannot do. It costs extra
#                 # index size, so it is enabled only on the two fields people
#                 # actually type fragments of.
#                 "infix": True,
#             },
#             # ---- searchable location text ----
#             {"name": "address", "type": "string", "optional": True},
#             {
#                 "name": "city",
#                 "type": "string",
#                 "facet": True,
#                 "sort": True,
#                 "optional": True,
#                 "infix": True,
#             },
#             {"name": "state", "type": "string", "facet": True, "optional": True},
#             {"name": "zip_code", "type": "string", "facet": True, "optional": True},
#             # ---- classification ----
#             {
#                 "name": "facility_type",
#                 "type": "string",
#                 "facet": True,
#                 "optional": True,
#             },
#             {
#                 "name": "facility_type_category",
#                 "type": "string",
#                 "facet": True,
#                 "optional": True,
#             },
#             {
#                 "name": "ownership_type",
#                 "type": "string",
#                 "facet": True,
#                 "optional": True,
#             },
#             # ---- geo ----
#             # Returned to the client for map pins. Stored as plain floats
#             # rather than a `geopoint` because radius search is out of Phase 1
#             # scope and roughly two thirds of rows have no coordinates at all.
#             # See MODULE NOTE at the bottom before adding `location`.
#             {"name": "latitude", "type": "float", "index": False, "optional": True},
#             {"name": "longitude", "type": "float", "index": False, "optional": True},
#             # ---- numerics ----
#             {"name": "overall_rating", "type": "float", "optional": True},
#             {"name": "bed_count", "type": "int32", "optional": True},
#             # Always present. Backs `default_sorting_field`. See module docstring.
#             {"name": "rating_sort", "type": "float"},
#             # ---- sync bookkeeping ----
#             # Epoch seconds. Lets us verify "is the index actually current?"
#             # against Postgres without a full document diff, and gives the sync
#             # service a cheap way to detect stale documents.
#             {"name": "updated_at", "type": "int64", "optional": True},
#         ],
#     }


# # --------------------------------------------------------------------------
# # Lifecycle
# # --------------------------------------------------------------------------


# async def collection_exists(collection_name: str | None = None) -> bool:
#     """Whether the collection is already present. Never raises."""
#     name = collection_name or settings.TYPESENSE_COLLECTION
#     client = get_typesense_client()
#     try:
#         await run_typesense(client.collections[name].retrieve)
#         return True
#     except ObjectNotFound:
#         return False


# async def ensure_collection(collection_name: str | None = None) -> bool:
#     """
#     Create the collection if it does not exist. Idempotent and safe to call on
#     every startup and at the top of the import script.

#     Returns:
#         True if this call created it, False if it already existed.

#     Deliberately does NOT migrate an existing collection to a changed schema.
#     TypeSense cannot retype an existing field in place, and silently altering a
#     live index is exactly the kind of thing that should be an explicit,
#     operator-initiated action — see `recreate_collection`.
#     """
#     name = collection_name or settings.TYPESENSE_COLLECTION
#     client = get_typesense_client()

#     if await collection_exists(name):
#         logger.info("TypeSense collection %r already exists — nothing to do", name)
#         return False

#     schema = build_schema(name)
#     try:
#         await run_typesense(client.collections.create, schema)
#     except ObjectAlreadyExists:
#         # Two workers booting at once both saw "does not exist" and both tried
#         # to create. Not an error — the desired end state is reached either way.
#         logger.info("TypeSense collection %r was created concurrently", name)
#         return False

#     logger.info(
#         "Created TypeSense collection %r | fields=%d default_sort=%s",
#         name,
#         len(schema["fields"]),
#         schema["default_sorting_field"],
#     )
#     return True


# async def drop_collection(collection_name: str | None = None) -> bool:
#     """
#     Delete the collection and every document in it.

#     Returns False if it did not exist. Destructive by design — callers must
#     make the intent explicit; nothing calls this automatically.
#     """
#     name = collection_name or settings.TYPESENSE_COLLECTION
#     client = get_typesense_client()
#     try:
#         await run_typesense(client.collections[name].delete)
#     except ObjectNotFound:
#         logger.warning("Cannot drop TypeSense collection %r — it does not exist", name)
#         return False

#     logger.warning("Dropped TypeSense collection %r", name)
#     return True


# async def recreate_collection(collection_name: str | None = None) -> None:
#     """
#     Drop and recreate — used ONLY when the schema itself changed.

#     Leaves the index empty, so it must be followed by a full import. During
#     that window search returns zero results, which is why the import script
#     (Step 7) will use an alias-based swap instead for production reindexes.
#     """
#     name = collection_name or settings.TYPESENSE_COLLECTION
#     logger.warning("Recreating TypeSense collection %r — index will be EMPTY until reimported", name)
#     await drop_collection(name)
#     await ensure_collection(name)


# async def get_collection_stats(collection_name: str | None = None) -> dict[str, Any] | None:
#     """
#     Document count and field count, for health checks and import verification.
#     Returns None when the collection does not exist.
#     """
#     name = collection_name or settings.TYPESENSE_COLLECTION
#     client = get_typesense_client()
#     try:
#         info = await run_typesense(client.collections[name].retrieve)
#     except ObjectNotFound:
#         return None

#     return {
#         "name": info.get("name"),
#         "num_documents": info.get("num_documents", 0),
#         "num_fields": len(info.get("fields", [])),
#         "created_at": info.get("created_at"),
#     }


# # --------------------------------------------------------------------------
# # MODULE NOTE — adding geo radius search later (Phase 2)
# # --------------------------------------------------------------------------
# # To support "facilities within N miles", add:
# #     {"name": "location", "type": "geopoint", "optional": True}
# # and have the mapper emit `[lat, lng]` ONLY when both coordinates parse and
# # fall in valid ranges. TypeSense cannot filter by radius across two separate
# # float fields, so the dedicated geopoint is required.
# #
# # Adding a field to a live collection is an ALTER (client.collections[n].update)
# # and does not drop existing documents — but existing documents will not gain
# # the new field until they are re-imported. Budget a full 60k reindex for it.