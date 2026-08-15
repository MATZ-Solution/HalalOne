"""Unit tests for `collection/search/search_collection.py`.

This module acts as the translator between the AI's filter dictionary and
Typesense's search query syntax. We use the `ts_client_mock` fixture to
intercept the database call and verify that the `search_parameters` payload
is built perfectly (especially the complex `filter_by` string).
"""
import pytest

from collection.search.search_collection import search_collection

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════════════════════════════
# search_collection — dynamic payload builder
# ═══════════════════════════════════════════════════════════════════════

class TestSearchCollection:
    def test_validation_guards_return_empty_list(self, ts_client_mock):
        """Empty inputs intentionally raise ValueError which is caught, logged,
        and returns an empty list without crashing."""
        assert search_collection("", "norm_name", "halal_products", {}) == []
        assert search_collection("chicken", "", "halal_products", {}) == []
        assert search_collection("chicken", "norm_name", "", {}) == []
        
        # The database was never called
        ts_client_mock.assert_not_called()

    def test_database_exception_returns_empty_list(self, ts_client_mock):
        """If the Typesense client throws an exception, it is caught and
        returns an empty list to fail gracefully."""
        ts_client_mock.side_effect = Exception("Database offline")
        
        result = search_collection("chicken", "norm_name", "halal_products", {})
        
        assert result == []

    def test_empty_results_handled_correctly(self, ts_client_mock):
        """When Typesense returns zero hits."""
        ts_client_mock.return_value = {"hits": []}
        
        result = search_collection("chicken", "norm_name", "halal_products", {})
        
        assert result == []

    def test_valid_results_unpacked_correctly(self, ts_client_mock):
        """Typesense wraps results in a `{"document": {...}}` envelope. The
        function unpacks them into a flat list of dicts."""
        ts_client_mock.return_value = {
            "hits": [
                {"document": {"norm_name": "Chicken A", "halal_status": "Halal"}},
                {"document": {"norm_name": "Chicken B", "halal_status": "Doubtful"}}
            ]
        }
        
        result = search_collection("chicken", "norm_name", "halal_products", {})
        
        assert len(result) == 2
        assert result[0]["norm_name"] == "Chicken A"
        assert result[1]["halal_status"] == "Doubtful"

    def test_string_array_field_omits_drop_tokens(self, ts_client_mock):
        """When querying a STRING_ARRAY_FIELD like 'companies',
        drop_tokens_threshold should not be present in the payload."""
        search_collection("nestle", "companies", "halal_products", {})
        
        payload = ts_client_mock.call_args[0][0]
        assert payload["q"] == "nestle"
        assert payload["query_by"] == "companies"
        assert "drop_tokens_threshold" not in payload

    def test_standard_string_field_injects_drop_tokens(self, ts_client_mock):
        """When querying a normal field like 'norm_name', the function
        injects 'drop_tokens_threshold': 0 into the payload."""
        search_collection("chicken", "norm_name", "halal_products", {})
        
        payload = ts_client_mock.call_args[0][0]
        assert payload["drop_tokens_threshold"] == 0

    def test_no_filters_omits_filter_by_key(self, ts_client_mock):
        """An empty filter dict generates no filter string."""
        search_collection("chicken", "norm_name", "halal_products", {})
        
        payload = ts_client_mock.call_args[0][0]
        assert "filter_by" not in payload

    def test_string_filter_formats_with_quotes(self, ts_client_mock):
        """{"halal_status": "Halal"} -> halal_status:="Halal" """
        filters = {"halal_status": "Halal"}
        search_collection("chicken", "norm_name", "halal_products", filters)
        
        payload = ts_client_mock.call_args[0][0]
        assert payload["filter_by"] == 'halal_status:="Halal"'

    def test_list_filter_formats_with_brackets_and_quotes(self, ts_client_mock):
        """{"sold_in": ["UK", "USA"]} -> sold_in:=["UK","USA"] """
        filters = {"sold_in": ["UK", "USA"]}
        search_collection("chicken", "norm_name", "halal_products", filters)
        
        payload = ts_client_mock.call_args[0][0]
        assert payload["filter_by"] == 'sold_in:=["UK","USA"]'

    def test_multiple_filters_join_with_double_ampersand(self, ts_client_mock):
        """Tests that multiple filters are perfectly joined with ` && `."""
        filters = {
            "category_l1": "Food",
            "sold_in": ["UK", "USA"]
        }
        search_collection("chicken", "norm_name", "halal_products", filters)
        
        payload = ts_client_mock.call_args[0][0]
        # Dictionaries maintain insertion order in modern Python, so the order is predictable
        assert payload["filter_by"] == 'category_l1:="Food" && sold_in:=["UK","USA"]'
