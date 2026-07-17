"""Flickr planning contracts that never contain provider credentials."""

from .budget import (
    FLICKR_BUDGET_SCHEMA_VERSION,
    BudgetDecisionError,
    FlickrHourlyBudget,
    HourlyBudgetPolicy,
)
from .query_compiler import (
    QUERY_DEFINITION_SCHEMA_VERSION,
    QueryCompilationError,
    compile_name_assertion,
    compile_name_assertions,
)
from .query_plan import (
    FLICKR_REST_ENDPOINT,
    FLICKR_SEARCH_METHOD,
    LOGICAL_QUERY_ASSOCIATION_SCHEMA_VERSION,
    PHYSICAL_QUERY_REQUEST_SCHEMA_VERSION,
    QUERY_REQUEST_LINK_SCHEMA_VERSION,
    QueryPlanError,
    build_logical_query_association,
    plan_physical_query_requests,
)

__all__ = [
    "FLICKR_BUDGET_SCHEMA_VERSION",
    "BudgetDecisionError",
    "FlickrHourlyBudget",
    "HourlyBudgetPolicy",
    "QUERY_DEFINITION_SCHEMA_VERSION",
    "QueryCompilationError",
    "compile_name_assertion",
    "compile_name_assertions",
    "FLICKR_REST_ENDPOINT",
    "FLICKR_SEARCH_METHOD",
    "LOGICAL_QUERY_ASSOCIATION_SCHEMA_VERSION",
    "PHYSICAL_QUERY_REQUEST_SCHEMA_VERSION",
    "QUERY_REQUEST_LINK_SCHEMA_VERSION",
    "QueryPlanError",
    "build_logical_query_association",
    "plan_physical_query_requests",
]
