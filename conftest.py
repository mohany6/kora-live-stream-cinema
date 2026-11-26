"""Root pytest bootstrap: make `src` importable without installing the package."""

import sys
from pathlib import Path
import pytest

_ROOT = Path(__file__).resolve().parent
for _path in (_ROOT / "src", _ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from live_score.api.security import global_rate_limiter
from live_score.api.cache import global_cache


@pytest.fixture(autouse=True)
def reset_rate_limiter_and_cache():
    global_rate_limiter.reset()
    global_cache.clear()
    yield
    global_rate_limiter.reset()
    global_cache.clear()
