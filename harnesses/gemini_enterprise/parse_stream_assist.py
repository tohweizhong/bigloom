#!/usr/bin/env python3
"""Parse raw StreamAssist chunks into structured records and BigLoom EvalResponse items."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from bigloom.models import EvalResponse

DEEP_READ_THOUGHT_MARKERS = (
    "accessing document content",
    "loading content retrieval skills",
    "loading content skills",
    "reading full file",
    "downloading file",
    "extracting document text",
)

DOWNLOAD_TOOL_MARKERS = (
    "download",
    "get_file",
    "read_file",
    "fetch_file",
    "fetch_documents",
    "get_content",
    "get_document_content",
    "document_content",
)


def parse_raw_chunks_text(content: str) -> list[dict[str, Any]]:
    """Parse raw JSON array text or chunk-delimited StreamAssist dump text."""
    clean = content.strip()
    if not clean:
        return []
    if clean.startswith("[") and clean.endswith("]"):
        loaded = json.loads(clean)
        if isinstance(loaded, list):
            return [c for c in loaded if isinstance(c, dict)]

    parts = re.split(r"--- \[RESPONSE CHUNK \d+\] ---", clean)
    parsed: list[dict[str, Any]] = []
    for part in parts:
        raw = part.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        if isinstance(obj, dict):
            parsed.append(obj)
    return parsed


def _match_known_file(candidate: str, known_files: list[str] | None) -> str | None:
    """Resolve a URI or title against known manifest relative paths."""
    raw = unquote(candidate).strip()
    if not raw:
        return None
    base = raw.split("?", 1)[0].rstrip("/").split("/")[-1].strip()
    if not known_files:
        return base or raw
    for known in known_files:
        known_base = known.split("/")[-1]
        if raw.endswith(known) or base == known_base or known_base in raw:
            return known
    return base or None


def _add_unique(target: list[str], value: str | None) -> None:
    if value and value not in target:
        target.append(value)


def parse_stream_assist_chunks(
    chunks: list[dict[str, Any]],
    known_files: list[str] | None = None,
) -> dict[str, Any]:
    """Extract answer text, assist tokens, cited files, downloaded files, and tool calls."""
    answer_parts: list[str] = []
    thought_parts: list[str] = []
    assist_tokens: list[str] = []
    skipped_reasons: list[str] = []
    cited_files: list[str] = []
    downloaded_files: list[str] = []
    tool_calls: list[str] = []
    saw_deep_read_thought = False

    for chunk in chunks:
        token = chunk.get("assistToken")
        if isinstance(token, str) and token.strip():
            _add_unique(assist_tokens, token.strip())

        action = chunk.get("action")
        if isinstance(action, dict):
            tool_name = str(
                action.get("toolName")
                or action.get("name")
                or action.get("function")
                or ""
            ).strip()
            if tool_name:
                _add_unique(tool_calls, tool_name)
            action_blob = json.dumps(action)
            action_lower = action_blob.lower()
            is_download_action = any(m in action_lower for m in DOWNLOAD_TOOL_MARKERS)
            if is_download_action:
                _add_unique(tool_calls, "download_document")
                if known_files:
                    for known in known_files:
                        if known in action_blob or known.split("/")[-1] in action_blob:
                            _add_unique(downloaded_files, known)
                params = action.get("parameters")
                if isinstance(params, dict):
                    for key in ("file", "path", "uri", "filename", "document"):
                        val = params.get(key)
                        if isinstance(val, str):
                            _add_unique(
                                downloaded_files,
                                _match_known_file(val, known_files),
                            )

        answer = chunk.get("answer")
        if not isinstance(answer, dict):
            continue

        ans_token = answer.get("assistToken")
        if isinstance(ans_token, str) and ans_token.strip():
            _add_unique(assist_tokens, ans_token.strip())

        for reason in answer.get("assistSkippedReasons", []):
            _add_unique(skipped_reasons, str(reason))

        for reply in answer.get("replies", []):
            if not isinstance(reply, dict):
                continue
            grounded = reply.get("groundedContent")
            if not isinstance(grounded, dict):
                continue

            content = grounded.get("content")
            if isinstance(content, dict):
                text = content.get("text", "")
                if isinstance(text, str) and text:
                    if content.get("thought", False):
                        thought_parts.append(text)
                        text_lower = text.lower()
                        if any(m in text_lower for m in DEEP_READ_THOUGHT_MARKERS):
                            saw_deep_read_thought = True
                    else:
                        answer_parts.append(text)

            for src in grounded.get("groundingSources", []):
                if isinstance(src, dict):
                    for key in ("uri", "title"):
                        val = src.get(key)
                        if isinstance(val, str):
                            _add_unique(cited_files, _match_known_file(val, known_files))

            tgm = grounded.get("textGroundingMetadata")
            if isinstance(tgm, dict):
                for ref in tgm.get("references", []):
                    if not isinstance(ref, dict):
                        continue
                    doc_meta = ref.get("documentMetadata")
                    if isinstance(doc_meta, dict):
                        for key in ("uri", "title"):
                            val = doc_meta.get(key)
                            if isinstance(val, str):
                                _add_unique(cited_files, _match_known_file(val, known_files))

    if saw_deep_read_thought:
        _add_unique(tool_calls, "get_document_content")
        if not downloaded_files and cited_files:
            for cited in cited_files:
                _add_unique(downloaded_files, cited)

    full_answer = "".join(answer_parts).strip()
    blocked = "CUSTOMER_POLICY_VIOLATION" in skipped_reasons or (
        "blocked by your organization" in full_answer.lower()
    )

    return {
        "answer_text": full_answer,
        "thought_text": "".join(thought_parts).strip(),
        "assist_tokens": assist_tokens,
        "skipped_reasons": skipped_reasons,
        "cited_files": cited_files,
        "downloaded_files": downloaded_files,
        "tool_calls": tool_calls,
        "blocked": blocked,
    }


def chunks_to_eval_response(
    case_id: str,
    chunks: list[dict[str, Any]],
    known_files: list[str] | None = None,
) -> EvalResponse:
    """Convert raw StreamAssist chunks for one case into a normalized EvalResponse."""
    parsed = parse_stream_assist_chunks(chunks, known_files=known_files)
    return EvalResponse(
        case_id=case_id,
        answer_text=parsed["answer_text"],
        cited_files=tuple(parsed["cited_files"]),
        tool_calls=tuple(parsed["tool_calls"]),
    )


def main(argv: list[str] | None = None) -> int:
    """Inspect a raw StreamAssist chunk file from the command line."""
    parser = argparse.ArgumentParser(description="Inspect raw StreamAssist response chunks.")
    parser.add_argument("file", type=Path, help="Path to raw JSON response file.")
    args = parser.parse_args(argv)

    chunks = parse_raw_chunks_text(args.file.read_text())
    parsed = parse_stream_assist_chunks(chunks)
    print(json.dumps(parsed, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
