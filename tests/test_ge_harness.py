from __future__ import annotations

import json
import os
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


def test_harness_judge_and_eval_only_pipeline(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    import urllib.request

    from harnesses.gemini_enterprise.harness import (
        DEFAULT_JUDGE_MODEL,
        evaluate_single_record_with_judge,
        is_auth_error,
    )
    from harnesses.gemini_enterprise.harness import (
        main as harness_cli_main,
    )
    from harnesses.gemini_enterprise.upload_m365 import UrllibClient

    class FakeUrlResp:
        status = 200

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self) -> bytes:
            return b'{"ok": true}'

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=60.0: FakeUrlResp())
    uclient = UrllibClient()
    assert uclient.get("https://example.com").json()["ok"] is True
    assert uclient.post("https://example.com", data={"a": "1"}).status_code == 200
    assert uclient.post("https://example.com", json={"a": 1}).status_code == 200
    assert uclient.put("https://example.com", data=b"x").status_code == 200

    assert DEFAULT_JUDGE_MODEL == "gemini-3.8-flash"
    assert is_auth_error(RuntimeError("RefreshError: reauthentication is needed")) is True
    assert is_auth_error(RuntimeError("Normal network timeout")) is False

    manifest_path = tmp_path / "manifest.jsonl"
    manifest_entry = {
        "file_id": "doc_001",
        "format": "docx",
        "target_file": "docx/acacia_close_fy2026_18mb.docx",
        "target_size_bytes": 18 * 1024 * 1024,
        "target_sha256": "a" * 64,
        "distractor_file": "docx/acacia_close_fy2025_draft.docx",
        "distractor_size_bytes": 40000,
        "distractor_sha256": "b" * 64,
        "topic": "Acacia Retail Ledger Close",
        "period": "FY2026",
        "distractor_period": "FY2025",
        "text_metric_label": "Net Inventory Reserve",
        "text_golden_value": "AUD 14,892,311",
        "text_canary_value": "AUD 9,104,220",
        "text_unit_index": 6,
        "image_chart_title": "Quarterly Close Variance",
        "image_golden_value": "41.83%",
        "image_canary_value": "19.05%",
    }
    manifest_path.write_text(json.dumps(manifest_entry) + "\n")

    cases_path = tmp_path / "cases.json"
    cases_data = [
        {
            "id": "doc_001_text",
            "query": "What is the Net Inventory Reserve for Acacia Retail Ledger Close in FY2026?",
            "target_file": "docx/acacia_close_fy2026_18mb.docx",
            "modality": "text",
            "golden_value": "AUD 14,892,311",
            "acceptable_values": ["14,892,311"],
            "min_unit_index": 5,
            "canary_trap": {
                "distractor_file": "docx/acacia_close_fy2025_draft.docx",
                "canary_value": "AUD 9,104,220",
            },
        }
    ]
    cases_path.write_text(json.dumps(cases_data, indent=2))

    raw_dir = tmp_path / "raw_responses"
    raw_dir.mkdir()
    (raw_dir / "doc_001_text_run1_raw.json").write_text(
        json.dumps(_sample_stream_chunks(), indent=2)
    )

    class FakeJudgeHttp:
        def post(
            self,
            url: str,
            headers: dict[str, str] | None = None,
            data: dict[str, str] | None = None,
            json: Any = None,
        ) -> HttpResponse:
            import json as _json

            assert "gemini-3.8-flash:generateContent" in url
            payload = {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": _json.dumps(
                                        {
                                            "reasoning": "Matched golden value AUD 14,892,311.",
                                            "failure_mode": "NONE",
                                            "verdict": "PASS",
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }
            return HttpResponse(200, _json.dumps(payload))

    sample_rec = {
        "id": "doc_001_text",
        "query": cases_data[0]["query"],
        "golden_value": "AUD 14,892,311",
        "canary_value": "AUD 9,104,220",
        "target_file": "docx/acacia_close_fy2026_18mb.docx",
        "response_text": "The reserve is AUD 14,892,311.",
        "error": None,
        "blocked": False,
    }
    judged = evaluate_single_record_with_judge(
        sample_rec,
        project_id="proj-1",
        access_token="tok-1",
        http_client=FakeJudgeHttp(),
    )
    assert judged["status"] == "PASS"
    assert judged["failure_mode"] == "NONE"

    reports_dir = tmp_path / "reports"
    responses_out = tmp_path / "responses.json"
    rc = harness_cli_main(
        [
            "--cases",
            str(cases_path),
            "--manifest",
            str(manifest_path),
            "--raw-dir",
            str(raw_dir),
            "--reports-dir",
            str(reports_dir),
            "--responses-out",
            str(responses_out),
            "--eval-only",
            "--runs",
            "1",
        ]
    )
    assert rc == 0
    assert responses_out.exists()
    assert (reports_dir / "scorecard.md").exists()
    assert (reports_dir / "report.md").exists()
    assert (reports_dir / "assist_tokens.json").exists()
    report_md = (reports_dir / "report.md").read_text()
    assert "CORRECT_WITH_DOWNLOAD" in report_md
    assert "gemini-3.8-flash" in report_md

    # Test judge fallback branches (error, blocked, empty, canary trap, search miss)
    assert (
        evaluate_single_record_with_judge({"error": "boom"}, "p", None)["failure_mode"]
        == "API_ERROR"
    )
    assert (
        evaluate_single_record_with_judge({"blocked": True}, "p", None)["failure_mode"]
        == "POLICY_VIOLATION"
    )
    assert (
        evaluate_single_record_with_judge({"response_text": ""}, "p", None)["failure_mode"]
        == "EMPTY_RESPONSE"
    )
    assert (
        evaluate_single_record_with_judge(
            {
                "response_text": "AUD 9,104,220",
                "golden_value": "AUD 14,892,311",
                "canary_value": "AUD 9,104,220",
            },
            "p",
            None,
        )["failure_mode"]
        == "CANARY_TRAP"
    )
    assert (
        evaluate_single_record_with_judge(
            {
                "response_text": "No idea",
                "golden_value": "AUD 14,892,311",
                "canary_value": "AUD 9,104,220",
            },
            "p",
            None,
        )["failure_mode"]
        == "SEARCH_MISS"
    )

    # Test live runner mode with mocked HTTP client and config file
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "project_id": "proj-live",
                "location": "sg",
                "engine_id": "eng-1",
                "assistant_id": "default_assistant",
                "data_store_ids": ["ds-1"],
            }
        )
    )

    class FakeLiveHttp:
        def post(
            self,
            url: str,
            headers: dict[str, str] | None = None,
            data: dict[str, str] | None = None,
            json: Any = None,
        ) -> HttpResponse:
            import json as _json

            if ":streamAssist" in url:
                return HttpResponse(200, _json.dumps(_sample_stream_chunks()))
            return FakeJudgeHttp().post(url, headers=headers, data=data, json=json)

    os.environ["GCP_ACCESS_TOKEN"] = "tok-env"
    try:
        rc_live = harness_cli_main(
            [
                "--config",
                str(cfg_path),
                "--cases",
                str(cases_path),
                "--manifest",
                str(manifest_path),
                "--raw-dir",
                str(tmp_path / "raw_live"),
                "--reports-dir",
                str(tmp_path / "reports_live"),
                "--runs",
                "1",
            ],
            http_client=FakeLiveHttp(),
        )
        assert rc_live == 0
    finally:
        os.environ.pop("GCP_ACCESS_TOKEN", None)


