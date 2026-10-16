"""Shared pytest setup for BigLoom."""

from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _corpus_cache() -> None:
    """Share one WorldLoom corpus cache across the test session, so each build input runs `worldloom build` once."""
    if "BIGLOOM_CORPUS_CACHE" not in os.environ:
        os.environ["BIGLOOM_CORPUS_CACHE"] = tempfile.mkdtemp(prefix="bigloom-corpus-cache-")
