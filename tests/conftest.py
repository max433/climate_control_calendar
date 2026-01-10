"""Pytest configuration and fixtures."""
import pytest
import sys
from pathlib import Path

# Add custom_components to Python path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield
