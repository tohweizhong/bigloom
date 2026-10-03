"""Unit tests for the vendor-neutral evaluation run adapter."""

from __future__ import annotations

import json
from pathlib import Path

from bigloom.adapters import import_run_responses
from bigloom.models import EvalCase


def _sample_cases() -> list[EvalCase]:
    return [
        EvalCase(
            id="case-1",
            query="What is the FY2026 reserve budget?",
            target_file="large/doc1.docx",
            modality="text",
            golden_value="SGD 2,125,859",
            min_unit_index=5,
        ),
        EvalCase(
            id="case-2",
            query="What is the Q4 peak thermal efficiency?",
            target_file="large/doc2.pdf",
            modality="image",
            golden_value="28.24%",
            min_unit_index=5,
        ),
    ]


def test_import_json_and_jsonl_run_logs(tmp_path: Path) -> None:
    cases = _sample_cases()
    json_log = tmp_path / "run_report.json"
    json_log.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "id": "case-1",
                        "output": "The FY2026 reserve budget is SGD 2,125,859.",
                        "sources": ["large/doc1.docx"],
                        "tools": ["search_index", "read_file"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    res_json = import_run_responses(json_log, cases=cases)
    assert len(res_json) == 1
    assert res_json[0].case_id == "case-1"
    assert res_json[0].answer_text == "The FY2026 reserve budget is SGD 2,125,859."
    assert res_json[0].cited_files == ("large/doc1.docx",)
    assert res_json[0].tool_calls == ("search_index", "read_file")

    # JSONL log matching case_id by query text
    jsonl_log = tmp_path / "run_lines.jsonl"
    jsonl_log.write_text(
        json.dumps(
            {
                "query": "What is the Q4 peak thermal efficiency?",
                "response": "Peak efficiency reached 28.24%.",
                "citations": [{"path": "large/doc2.pdf"}],
                "tool_calls": [{"name": "download_document"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    res_jsonl = import_run_responses(jsonl_log, cases=cases)
    assert len(res_jsonl) == 1
    assert res_jsonl[0].case_id == "case-2"
    assert res_jsonl[0].cited_files == ("large/doc2.pdf",)
    assert res_jsonl[0].tool_calls == ("download_document",)


def test_import_agent_message_trace_directory(tmp_path: Path) -> None:
    cases = _sample_cases()
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    trace_file = trace_dir / "trace_01.json"
    trace_file.write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "What is the FY2026 reserve budget?"},
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {"type": "function", "function": {"name": "search_documents"}},
                            {"type": "function", "function": {"name": "fetch_documents"}},
                        ],
                    },
                    {
                        "role": "assistant",
                        "content": "The reserve budget is SGD 2,125,859.",
                        "citations": [{"file": "large/doc1.docx"}],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    trace_file_2 = trace_dir / "trace_02.json"
    trace_file_2.write_text(
        json.dumps(
            {
                "steps": [
                    {"role": "user", "content": "What is the Q4 peak thermal efficiency?"},
                    {
                        "role": "assistant",
                        "content": "Peak thermal efficiency is 28.24%.",
                        "citations": ["large/doc2.pdf"],
                        "tools": ["download_document"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    responses = import_run_responses(trace_dir, cases=cases)
    assert len(responses) == 2
    assert responses[0].case_id == "case-1"
    assert responses[0].answer_text == "The reserve budget is SGD 2,125,859."
    assert responses[0].cited_files == ("large/doc1.docx",)
    assert responses[0].tool_calls == ("search_documents", "fetch_documents")
    assert responses[1].case_id == "case-2"
    assert responses[1].tool_calls == ("download_document",)


def test_import_csv_evaluation_table(tmp_path: Path) -> None:
    cases = _sample_cases()
    csv_path = tmp_path / "eval_export.csv"
    csv_path.write_text(
        "query,answer,citations,tools\n"
        "\"What is the FY2026 reserve budget?\",\"SGD 2,125,859\",\"large/doc1.docx\",\"search;download_document\"\n"
        "\"What is the Q4 peak thermal efficiency?\",\"28.24%\",\"large/doc2.pdf\",\"search\"\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "responses.json"
    responses = import_run_responses(csv_path, out_path=out_path, cases=cases)
    assert len(responses) == 2
    assert out_path.is_file()
    assert responses[0].case_id == "case-1"
    assert responses[0].tool_calls == ("search", "download_document")
    assert responses[1].case_id == "case-2"
    assert responses[1].cited_files == ("large/doc2.pdf",)
