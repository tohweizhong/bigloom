"""Unit tests for proposal prose generation and disk caching (Phase 2)."""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path

import pytest

from bigloom.proposal.facts import load_world_entities
from bigloom.proposal.prose import (
    VertexGeminiClient,
    load_prose,
    section_count,
    write_prose,
)
from bigloom.proposal.spec import ProposalSpec, ProseConfig


def _small_spec(*, provider: str = "deterministic") -> ProposalSpec:
    return ProposalSpec(
        world_pack="retail-close",
        subject="Greater Southern Waterfront Digital Twin Programme",
        sizes_mb=[5],
        chapters=[
            "Executive summary",
            "Implementation plan and phasing",
            "Annex A: Glossary and abbreviations",
        ],
        middle_chapter="Implementation plan and phasing",
        sections_per_chapter=2,
        annex_sections=1,
        figures=6,
        prose=ProseConfig(provider=provider, workers=2),  # type: ignore[arg-type]
    )


def test_section_count_differentiates_chapters_and_annexes() -> None:
    """Chapters use sections_per_chapter and annexes use annex_sections."""
    spec = _small_spec()
    assert section_count(spec, "Executive summary") == 2
    assert section_count(spec, "Annex A: Glossary and abbreviations") == 1


def test_deterministic_prose_writes_and_loads_cache(tmp_path: Path) -> None:
    """Deterministic mode writes outlines and sections offline and loads them back."""
    spec = _small_spec(provider="deterministic")
    entities = load_world_entities(spec, seed=42)
    cache_dir = tmp_path / "_prose_cache"

    write_prose(cache_dir, spec, entities, seed=42)
    loaded = load_prose(cache_dir, spec)

    assert len(loaded) == 3
    assert loaded[0][0] == "Executive summary"
    assert len(loaded[0][1]) == 2
    assert loaded[2][0] == "Annex A: Glossary and abbreviations"
    assert len(loaded[2][1]) == 1

    for _chapter, sections in loaded:
        for title, body in sections:
            assert title.strip()
            assert len(body.split()) >= 120
            assert entities.agency_name in body


def test_gemini_prose_caches_and_makes_zero_calls_on_second_run(tmp_path: Path) -> None:
    """A second write_prose run against the same cache makes zero Gemini calls."""
    spec = _small_spec(provider="gemini")
    entities = load_world_entities(spec, seed=42)
    cache_dir = tmp_path / "_prose_cache"

    calls: list[tuple[str, bool]] = []

    class FakeGeminiClient:
        def generate(
            self,
            prompt: str,
            *,
            json_mode: bool = False,
            temperature: float = 0.8,
        ) -> str:
            calls.append((prompt, json_mode))
            if json_mode:
                return json.dumps({"sections": ["Section Alpha", "Section Beta"]})
            return ("Synthetic paragraph with detailed programme narrative. " * 60).strip()

    fake = FakeGeminiClient()
    write_prose(cache_dir, spec, entities, client=fake)  # type: ignore[arg-type]
    first_call_count = len(calls)
    # 3 outlines + (2 + 2 + 1) sections = 8 calls
    assert first_call_count == 8

    # Second run against the populated cache makes zero calls
    write_prose(cache_dir, spec, entities, client=fake)  # type: ignore[arg-type]
    assert len(calls) == first_call_count


def test_vertex_gemini_client_stops_immediately_on_401_and_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 401 and 403 permission errors stop immediately without retrying."""
    client = VertexGeminiClient(
        project="test-project",
        account=None,
        model="gemini-3.8-flash",
        sleep_fn=lambda _: None,
    )
    monkeypatch.setattr(client, "_token", lambda: "fake-token")

    attempts = 0

    def fake_urlopen_403(req: object, timeout: int = 300) -> object:
        nonlocal attempts
        attempts += 1
        raise urllib.error.HTTPError(
            url="https://aiplatform.googleapis.com",
            code=403,
            msg="Forbidden",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b"Permission denied on project"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen_403)
    with pytest.raises(RuntimeError, match="403"):
        client.generate("Write a paragraph.")
    assert attempts == 1


def test_vertex_gemini_client_retries_transient_errors_and_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Transient HTTP 503 or URLError failures retry and return the generated text."""
    sleeps: list[float] = []
    client = VertexGeminiClient(
        project="test-project",
        account="user@example.com",
        model="gemini-3.8-flash",
        sleep_fn=sleeps.append,
    )
    monkeypatch.setattr(client, "_token", lambda: "fake-token")

    attempts = 0

    class FakeHTTPResponse:
        def __enter__(self) -> FakeHTTPResponse:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self) -> bytes:
            payload = {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "Thinking trace", "thought": True},
                                {"text": "Final section prose output."},
                            ]
                        }
                    }
                ]
            }
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen_transient(req: object, timeout: int = 300) -> FakeHTTPResponse:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise urllib.error.URLError("Temporary connection reset")
        return FakeHTTPResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen_transient)
    result = client.generate("Write a section.", json_mode=False)
    assert result == "Final section prose output."
    assert attempts == 3
    assert len(sleeps) == 2
