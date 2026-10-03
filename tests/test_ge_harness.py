from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harnesses.gemini_enterprise.parse_stream_assist import (
    chunks_to_eval_response,
    parse_raw_chunks_text,
    parse_stream_assist_chunks,
)
from harnesses.gemini_enterprise.parse_stream_assist import (
    main as parse_cli_main,
)
from harnesses.gemini_enterprise.upload_m365 import (
    SIMPLE_UPLOAD_LIMIT_BYTES,
    HttpResponse,
    acquire_graph_access_token,
    load_env_file,
    resolve_drive_id,
    upload_manifest_files,
)
from harnesses.gemini_enterprise.upload_m365 import (
    main as upload_cli_main,
)


def _sample_stream_chunks() -> list[dict[str, Any]]:
    return [
        {
            "answer": {
                "state": "IN_PROGRESS",
                "replies": [
                    {
                        "groundedContent": {
                            "content": {
                                "role": "model",
                                "text": "**Accessing Document Content**\n",
                                "thought": True,
                            }
                        }
                    }
                ],
            },
            "assistToken": "tok-001",
        },
        {
            "action": {
                "toolName": "sharepoint_download_file",
                "parameters": {"file": "docx/acacia_close_fy2026_18mb.docx"},
            },
            "assistToken": "tok-001",
        },
        {
            "answer": {
                "state": "SUCCEEDED",
                "replies": [
                    {
                        "groundedContent": {
                            "content": {
                                "role": "model",
                                "text": "The reserve is AUD 14,892,311.",
                                "thought": False,
                            },
                            "textGroundingMetadata": {
                                "references": [
                                    {
                                        "content": "Reserve table...",
                                        "documentMetadata": {
                                            "uri": "https://contoso.sharepoint.com/sites/demo/Shared%20Documents/docx/acacia_close_fy2026_18mb.docx?web=1",
                                            "title": "acacia_close_fy2026_18mb.docx ",
                                        },
                                    }
                                ]
                            },
                        }
                    }
                ],
            },
            "assistToken": "tok-002",
        },
    ]


def test_parse_stream_assist_chunks_extracts_answer_citations_and_downloads(
    tmp_path: Path,
) -> None:
    chunks = _sample_stream_chunks()
    parsed = parse_stream_assist_chunks(
        chunks,
        known_files=[
            "docx/acacia_close_fy2026_18mb.docx",
            "docx/acacia_close_fy2025_draft.docx",
        ],
    )
    assert parsed["answer_text"] == "The reserve is AUD 14,892,311."
    assert parsed["assist_tokens"] == ["tok-001", "tok-002"]
    assert "docx/acacia_close_fy2026_18mb.docx" in parsed["cited_files"]
    assert "docx/acacia_close_fy2026_18mb.docx" in parsed["downloaded_files"]
    assert "download_document" in parsed["tool_calls"]
    assert parsed["blocked"] is False

    raw_file = tmp_path / "raw.json"
    raw_file.write_text(json.dumps(chunks))
    assert parse_cli_main([str(raw_file)]) == 0


def test_chunks_to_eval_response_handles_delimited_and_snippet_only() -> None:
    snippet_chunks = [
        {
            "answer": {
                "state": "IN_PROGRESS",
                "replies": [
                    {
                        "groundedContent": {
                            "content": {
                                "role": "model",
                                "text": "**Searching for Files**\n",
                                "thought": True,
                            }
                        }
                    }
                ],
            }
        },
        {
            "answer": {
                "state": "SUCCEEDED",
                "replies": [
                    {
                        "groundedContent": {
                            "content": {
                                "role": "model",
                                "text": "The reserve is AUD 14,892,311.",
                            },
                            "groundingSources": [
                                {
                                    "title": "acacia_close_fy2026_18mb.docx",
                                    "uri": "https://contoso.sharepoint.com/acacia_close_fy2026_18mb.docx",
                                }
                            ],
                        }
                    }
                ],
            }
        },
    ]
    delimited_text = (
        "--- [RESPONSE CHUNK 1] ---\n"
        + json.dumps(snippet_chunks[0])
        + "\n--- [RESPONSE CHUNK 2] ---\n"
        + json.dumps(snippet_chunks[1])
    )
    parsed_list = parse_raw_chunks_text(delimited_text)
    assert len(parsed_list) == 2

    eval_resp = chunks_to_eval_response(
        case_id="case_001_text",
        chunks=parsed_list,
        known_files=["docx/acacia_close_fy2026_18mb.docx"],
    )
    assert eval_resp.case_id == "case_001_text"
    assert eval_resp.answer_text == "The reserve is AUD 14,892,311."
    assert eval_resp.cited_files == ("docx/acacia_close_fy2026_18mb.docx",)
    assert eval_resp.tool_calls == ()


def test_upload_manifest_files_uses_simple_put_and_resumable_session(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    small_rel = "docx/small_trap.docx"
    large_rel = "xlsx/large_target.xlsx"
    (tmp_path / "docx").mkdir()
    (tmp_path / "xlsx").mkdir()

    small_path = tmp_path / small_rel
    large_path = tmp_path / large_rel
    small_path.write_bytes(b"a" * 1024)
    large_path.write_bytes(b"b" * (SIMPLE_UPLOAD_LIMIT_BYTES + 2048))

    manifest_path = tmp_path / "manifest.jsonl"
    records = [
        {
            "target_file": large_rel,
            "distractor_file": small_rel,
        }
    ]
    manifest_path.write_text("\n".join(json.dumps(r) for r in records) + "\n")

    put_calls: list[tuple[str, int, dict[str, str]]] = []
    post_calls: list[str] = []

    class FakeSession:
        def get(
            self, url: str, headers: dict[str, str] | None = None
        ) -> HttpResponse:
            if "/sites/" in url and not url.endswith("/drive"):
                return HttpResponse(200, json.dumps({"id": "site-001"}))
            return HttpResponse(200, json.dumps({"id": "drive-123"}))

        def post(
            self,
            url: str,
            headers: dict[str, str] | None = None,
            data: dict[str, str] | None = None,
            json: Any = None,
        ) -> HttpResponse:
            import json as _json

            post_calls.append(url)
            if "oauth2/v2.0/token" in url:
                return HttpResponse(200, _json.dumps({"access_token": "tok-graph"}))
            return HttpResponse(
                200,
                _json.dumps({"uploadUrl": "https://upload.example.com/session123"}),
            )

        def put(
            self,
            url: str,
            headers: dict[str, str] | None = None,
            data: bytes = b"",
        ) -> HttpResponse:
            hdrs = headers or {}
            put_calls.append((url, len(data), hdrs))
            if "Content-Range" in hdrs:
                range_str = hdrs["Content-Range"]
                end_part, total_part = range_str.replace("bytes ", "").split("/")
                _, end_byte = end_part.split("-")
                if int(end_byte) + 1 < int(total_part):
                    return HttpResponse(202, "{}")
            return HttpResponse(201, json.dumps({"id": "item-1"}))

    client = FakeSession()
    env_file = tmp_path / ".env"
    env_file.write_text("SAMPLE_GRAPH_VAR=ok\n")
    load_env_file(env_file)

    token = acquire_graph_access_token("t1", "c1", "s1", http_client=client)
    assert token == "tok-graph"
    sp_drive = resolve_drive_id(
        token,
        sharepoint_host="contoso.sharepoint.com",
        sharepoint_site_path="/sites/demo",
        http_client=client,
    )
    assert sp_drive == "drive-123"
    od_drive = resolve_drive_id(
        token,
        user_principal_name="user@contoso.com",
        http_client=client,
    )
    assert od_drive == "drive-123"

    uploaded = upload_manifest_files(
        manifest_path=manifest_path,
        access_token=token,
        drive_id=sp_drive,
        remote_folder="BigLoom-Eval",
        http_client=client,
    )
    assert uploaded == [large_rel, small_rel]
    assert any("createUploadSession" in u for u in post_calls)
    assert any(
        "BigLoom-Eval/docx/small_trap.docx:/content" in url
        for url, _, _ in put_calls
    )
    chunk_puts = [
        c for c in put_calls if c[0] == "https://upload.example.com/session123"
    ]
    assert len(chunk_puts) >= 4

    import harnesses.gemini_enterprise.upload_m365 as up_mod

    monkeypatch.setenv("TENANT_ID", "t1")
    monkeypatch.setenv("CLIENT_ID", "c1")
    monkeypatch.setenv("CLIENT_SECRET", "s1")
    monkeypatch.setenv("USER_PRINCIPAL_NAME", "user@contoso.com")
    monkeypatch.setattr(
        up_mod,
        "acquire_graph_access_token",
        lambda **kw: "tok-graph",
    )
    monkeypatch.setattr(
        up_mod,
        "resolve_drive_id",
        lambda *a, **kw: "drive-123",
    )
    monkeypatch.setattr(
        up_mod,
        "upload_manifest_files",
        lambda **kw: [large_rel, small_rel],
    )
    assert upload_cli_main(["--manifest", str(manifest_path)]) == 0
