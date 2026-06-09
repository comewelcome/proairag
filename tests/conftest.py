"""Root conftest.py - applies markers based on test location."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests with mocks (no DB required)")
    config.addinivalue_line("markers", "integration: Integration tests with real Docker database")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark unit tests
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        # Mark integration tests
        elif "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
