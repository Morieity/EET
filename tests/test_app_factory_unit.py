"""Application wiring smoke unit test for Backend.Web.app_factory.

Does not start the HTTP server; only constructs the Flask app via
`create_app()` and asserts that all expected blueprints/routes are
registered. Network/LLM calls are not exercised.
"""

import os

import pytest


@pytest.fixture(scope="module")
def flask_app():
    os.environ.setdefault("LLM_API_KEY", "sk-placeholder-for-unit")
    from Backend.Web.app_factory import create_app

    return create_app()


def _route_paths(app) -> list[str]:
    return [str(rule) for rule in app.url_map.iter_rules()]


EXPECTED_ROUTE_PREFIXES = [
    "/api/chat",
    "/api/conversations",
    "/api/files",
    "/api/fault-trees",
    "/api/work-orders",
]


@pytest.mark.parametrize("prefix", EXPECTED_ROUTE_PREFIXES)
def test_app_factory_registers_expected_route_prefix(flask_app, prefix: str) -> None:
    rules = _route_paths(flask_app)
    assert any(prefix in rule for rule in rules), (
        f"expected at least one route containing {prefix!r}, "
        f"got: {sorted(rules)}"
    )


def test_app_factory_registers_unique_endpoint_names(flask_app) -> None:
    # Flask refuses to register two views under the same endpoint name; this
    # guards against accidental blueprint name collisions when adding new
    # endpoints.
    endpoints = [rule.endpoint for rule in flask_app.url_map.iter_rules()]
    assert len(endpoints) == len(set(endpoints))
