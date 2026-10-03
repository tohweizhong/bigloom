"""Vendor-neutral adapters that convert saved evaluation logs into EvalResponse records."""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .models import EvalCase, EvalResponse


def _split_delimited(raw: str) -> tuple[str, ...]:
    """Split a comma- or semicolon-delimited string into non-empty items."""
    sep = ";" if ";" in raw else ","
    return tuple(item.strip() for item in raw.split(sep) if item.strip())


def _extract_string_list(value: Any) -> tuple[str, ...]:
    """Normalize a list of strings or dictionaries into a tuple of strings."""
    if value is None:
        return ()
    if isinstance(value, str):
        return _split_delimited(value)
    if not isinstance(value, Sequence):
        return ()
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            # Support OpenAI/MCP tool_calls and generic citation objects
            fn = item.get("function")
            if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                out.append(fn["name"].strip())
                continue
            for key in ("name", "tool", "path", "file", "uri", "source", "title"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    out.append(candidate.strip())
                    break
    return tuple(out)


def _normalize_trace_messages(messages: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Collapse an agent message trace (OpenAI or MCP format) into a flat record."""
    query = ""
    answer_text = ""
    citations: list[str] = []
    tools: list[str] = []

    for msg in messages:
        role = str(msg.get("role", "")).lower()
        content = msg.get("content")
        text_content = content.strip() if isinstance(content, str) else ""
        if role == "user" and text_content and not query:
            query = text_content
        elif role == "assistant" and text_content:
            answer_text = text_content

        for tool in _extract_string_list(msg.get("tool_calls") or msg.get("tools")):
            if tool not in tools:
                tools.append(tool)
        for cited in _extract_string_list(
            msg.get("citations") or msg.get("cited_files") or msg.get("sources")
        ):
            if cited not in citations:
                citations.append(cited)

    return {
        "query": query,
        "answer_text": answer_text,
        "cited_files": citations,
        "tool_calls": tools,
    }


def _record_to_eval_response(
    raw: dict[str, Any],
    query_map: dict[str, str],
    fallback_idx: int,
) -> EvalResponse:
    """Convert one raw dictionary record into a validated EvalResponse."""
    if isinstance(raw.get("messages"), list):
        merged = _normalize_trace_messages(raw["messages"])
        for k, v in raw.items():
            if k != "messages" and k not in merged:
                merged[k] = v
        raw = merged

    case_id = str(raw.get("case_id") or raw.get("id") or "").strip()
    query = str(raw.get("query") or raw.get("question") or "").strip()
    if not case_id and query:
        case_id = query_map.get(query.lower(), "")
    if not case_id:
        case_id = f"unmatched-{fallback_idx:03d}"

    answer_text = str(
        raw.get("answer_text")
        or raw.get("answer")
        or raw.get("response")
        or raw.get("output")
        or ""
    ).strip()

    cited_files = _extract_string_list(
        raw.get("cited_files") or raw.get("citations") or raw.get("sources")
    )
    tool_calls = _extract_string_list(
        raw.get("tool_calls") or raw.get("tools") or raw.get("actions")
    )

    return EvalResponse(
        case_id=case_id,
        answer_text=answer_text,
        cited_files=cited_files,
        tool_calls=tool_calls,
    )


def _load_raw_records_from_file(path: Path) -> list[dict[str, Any]]:
    """Read raw evaluation records from a .json, .jsonl, or .csv file."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    if suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            cleaned = line.strip()
            if cleaned:
                records.append(json.loads(cleaned))
        return records

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("results", "cases", "responses", "items", "runs"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
        return [payload]
    return []


def import_run_responses(
    input_path: Path,
    *,
    out_path: Path | None = None,
    cases: Sequence[EvalCase] | None = None,
) -> list[EvalResponse]:
    """Import saved evaluation logs (JSON, JSONL, CSV, or directory) into EvalResponse items."""
    query_map: dict[str, str] = {}
    if cases is not None:
        for case in cases:
            query_map[case.query.strip().lower()] = case.id

    raw_records: list[dict[str, Any]] = []
    if input_path.is_dir():
        for child in sorted(input_path.rglob("*")):
            if child.is_file() and child.suffix.lower() in {".json", ".jsonl", ".csv"}:
                raw_records.extend(_load_raw_records_from_file(child))
    else:
        raw_records.extend(_load_raw_records_from_file(input_path))

    responses = [
        _record_to_eval_response(rec, query_map, idx)
        for idx, rec in enumerate(raw_records, 1)
    ]

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [resp.model_dump() for resp in responses]
        out_path.write_text(json.dumps(serialized, indent=2) + "\n", encoding="utf-8")

    return responses
