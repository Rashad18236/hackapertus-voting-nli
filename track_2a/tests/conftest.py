"""Shared test set-up (session 12): src/rankers.py keeps per-process state on purpose (the run's ranker, and models
that failed, so a run stops trying them); each test starts from the defaults."""

import pytest

from src import rankers


@pytest.fixture(autouse=True)
def fresh_ranker_state():
    yield
    rankers.reset()
