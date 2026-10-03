#!/usr/bin/env python3
"""Gemini Enterprise evaluation harness for BigLoom with decoupled batch grading."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Any

from bigloom.grade import grade_responses
from bigloom.models import EvalCase, EvalResponse, LeakageVerdict, ManifestEntry
from bigloom.report import render_scorecard_markdown
from harnesses.gemini_enterprise.parse_stream_assist import (
    chunks_to_eval_response,
    parse_raw_chunks_text,
    parse_stream_assist_chunks,
)
from harnesses.gemini_enterprise.upload_m365 import DEFAULT_HTTP_CLIENT

DEFAULT_JUDGE_MODEL = "gemini-3.8-flash"
DEFAULT_JUDGE_REGION = "global"
SCRIPT_DIR = Path(__file__).resolve().parent


def is_auth_error(err: Exception) -> bool:
    """Return True when the exception indicates expired or invalid credentials."""
    text = str(err).lower()
    markers = (
        "reauthentication",
        "invalid_grant",
        "unauthenticated",
        "permission_denied",
        "401",
        "403",
    )
    return any(m in text for m in markers)


def get_gcp_access_token() -> str | None:
    """Retrieve an active OAuth2 access token from environment variables or gcloud."""
    for env_key in ("GCP_ACCESS_TOKEN", "ACCESS_TOKEN"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    commands = (
        ["gcloud", "auth", "application-default", "print-access-token"],
        ["gcloud", "auth", "print-access-token"],
    )
    for cmd in commands:
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
            if out:
                return out
        except (OSError, subprocess.SubprocessError):
            _ = cmd
    return None


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load JSON configuration from disk if present."""
    candidates = [
        config_path,
        Path("config.json"),
        SCRIPT_DIR / "config.json",
        SCRIPT_DIR / "config.example.json",
    ]
    for path in candidates:
        if path and path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return data
    return {}


def load_eval_cases(cases_path: Path) -> list[EvalCase]:
    """Load and validate EvalCase items from cases.json."""
    raw = json.loads(cases_path.read_text())
    return [EvalCase.model_validate(item) for item in raw]


def load_manifest_entries(manifest_path: Path | None) -> list[ManifestEntry]:
    """Load and validate ManifestEntry items from manifest.jsonl if provided."""
    if manifest_path is None or not manifest_path.exists():
        return []
    entries: list[ManifestEntry] = []
    for line in manifest_path.read_text().splitlines():
        if line.strip():
            entries.append(ManifestEntry.model_validate_json(line))
    return entries


def build_known_files(
    cases: list[EvalCase],
    manifest: list[ManifestEntry],
) -> list[str]:
    """Build the ordered list of target and distractor file paths."""
    files: list[str] = []
    for entry in manifest:
        for fpath in (entry.target_file, entry.distractor_file):
            if fpath not in files:
                files.append(fpath)
    for case in cases:
        if case.target_file not in files:
            files.append(case.target_file)
        if case.canary_trap and case.canary_trap.distractor_file not in files:
            files.append(case.canary_trap.distractor_file)
    return files


def query_stream_assist_grpc(
    *,
    project_id: str,
    location: str,
    engine_id: str,
    assistant_id: str,
    query_text: str,
    data_store_ids: list[str],
    timeout: float = 180.0,
) -> tuple[list[dict[str, Any]], float, float]:
    """Query Discovery Engine AssistantServiceClient.stream_assist via gRPC."""
    from google.api_core.client_options import ClientOptions
    from google.cloud import discoveryengine_v1 as discoveryengine
    from google.protobuf.json_format import MessageToJson

    client_options = (
        None
        if location == "global"
        else ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
    )
    client = discoveryengine.AssistantServiceClient(client_options=client_options)
    assistant_name = client.assistant_path(
        project=project_id,
        location=location,
        collection="default_collection",
        engine=engine_id,
        assistant=assistant_id,
    )
    tools_spec = None
    if data_store_ids:
        specs = [
            {
                "data_store": (
                    f"projects/{project_id}/locations/{location}/"
                    f"collections/default_collection/dataStores/{ds_id}"
                )
            }
            for ds_id in data_store_ids
        ]
        tools_spec = {"vertex_ai_search_spec": {"data_store_specs": specs}}

    request = discoveryengine.StreamAssistRequest(
        name=assistant_name,
        query=discoveryengine.Query(text=query_text),
        tools_spec=tools_spec,
    )
    start_time = time.perf_counter()
    ttft_ms: float | None = None
    chunks: list[dict[str, Any]] = []

    for resp in client.stream_assist(request=request, timeout=timeout):
        chunk_dict = json.loads(MessageToJson(resp._pb))
        chunks.append(chunk_dict)
        if ttft_ms is None and resp.answer and resp.answer.replies:
            for reply in resp.answer.replies:
                gc = getattr(reply, "grounded_content", None)
                cnt = getattr(gc, "content", None) if gc else None
                if cnt and getattr(cnt, "text", "") and not getattr(cnt, "thought", False):
                    ttft_ms = (time.perf_counter() - start_time) * 1000.0
                    break

    total_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
    first_ms = round(ttft_ms, 1) if ttft_ms is not None else total_ms
    return chunks, first_ms, total_ms


def query_stream_assist_rest(
    *,
    project_id: str,
    location: str,
    engine_id: str,
    assistant_id: str,
    query_text: str,
    data_store_ids: list[str],
    access_token: str,
    http_client: Any = DEFAULT_HTTP_CLIENT,
) -> tuple[list[dict[str, Any]], float, float]:
    """Query the Discovery Engine streamAssist REST endpoint and return raw chunks."""
    host = (
        "discoveryengine.googleapis.com"
        if location == "global"
        else f"{location}-discoveryengine.googleapis.com"
    )
    assistant_name = (
        f"projects/{project_id}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}/assistants/{assistant_id}"
    )
    url = f"https://{host}/v1/{assistant_name}:streamAssist"
    body: dict[str, Any] = {"query": {"text": query_text}}
    if data_store_ids:
        specs = [
            {
                "dataStore": (
                    f"projects/{project_id}/locations/{location}/"
                    f"collections/default_collection/dataStores/{ds_id}"
                )
            }
            for ds_id in data_store_ids
        ]
        body["toolsSpec"] = {"vertexAiSearchSpec": {"dataStoreSpecs": specs}}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }
    start = time.perf_counter()
    resp = http_client.post(url, headers=headers, json=body)
    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 1)
    if resp.status_code != 200:
        raise RuntimeError(f"streamAssist failed ({resp.status_code}): {resp.text}")
    chunks = parse_raw_chunks_text(resp.text)
    return chunks, elapsed_ms, elapsed_ms


def evaluate_single_record_with_judge(
    record: dict[str, Any],
    project_id: str,
    access_token: str | None,
    *,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    judge_region: str = DEFAULT_JUDGE_REGION,
    http_client: Any = DEFAULT_HTTP_CLIENT,
) -> dict[str, Any]:
    """Evaluate one recorded response with Vertex AI gemini-3.8-flash and deterministic fallback."""
    result = dict(record)
    result["status"] = "FAIL"
    result["failure_mode"] = "NONE"
    result["details"] = ""

    if record.get("error"):
        result["details"] = f"API Error: {record['error']}"
        result["failure_mode"] = "API_ERROR"
        return result

    if record.get("blocked"):
        result["details"] = "Blocked by enterprise policy."
        result["failure_mode"] = "POLICY_VIOLATION"
        return result

    response_text = str(record.get("response_text", "")).strip()
    if not response_text:
        result["details"] = "Empty response returned from backend."
        result["failure_mode"] = "EMPTY_RESPONSE"
        return result

    golden = str(record.get("golden_value", "")).strip()
    canary = str(record.get("canary_value", "")).strip()
    target_file = str(record.get("target_file", "")).strip()
    query = str(record.get("query", "")).strip()

    if access_token and project_id:
        host = (
            "aiplatform.googleapis.com"
            if judge_region == "global"
            else f"{judge_region}-aiplatform.googleapis.com"
        )
        url = (
            f"https://{host}/v1/projects/{project_id}/locations/{judge_region}/"
            f"publishers/google/models/{judge_model}:generateContent"
        )
        prompt = (
            "Evaluate whether the assistant response states the golden value for the target file.\n"
            f"Query: {query}\n"
            f"Target File: {target_file}\n"
            f"Golden Value: {golden}\n"
            f"Distractor Canary Value: {canary}\n"
            f"Assistant Response: {response_text}\n"
            'Return JSON with keys: "reasoning", "failure_mode" '
            '("NONE", "CANARY_TRAP", "SEARCH_MISS", or "CONNECTOR_LIMITATION"), '
            'and "verdict" ("PASS" or "FAIL").'
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": project_id,
        }
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
            },
        }
        try:
            res = http_client.post(url, headers=headers, json=body)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                judge_res = json.loads(raw_text)
                result["status"] = str(judge_res.get("verdict", "FAIL"))
                result["failure_mode"] = str(judge_res.get("failure_mode", "NONE"))
                result["details"] = str(judge_res.get("reasoning", ""))
                return result
        except (OSError, ValueError, KeyError, IndexError, TypeError) as err:
            _ = err

    low_resp = response_text.lower()
    if canary and canary.lower() in low_resp and golden.lower() not in low_resp:
        result["status"] = "FAIL"
        result["failure_mode"] = "CANARY_TRAP"
        result["details"] = f"Fallback check: matched distractor canary '{canary}'."
    elif golden and golden.lower() in low_resp:
        result["status"] = "PASS"
        result["failure_mode"] = "NONE"
        result["details"] = f"Fallback check: matched golden value '{golden}'."
    else:
        result["status"] = "FAIL"
        result["failure_mode"] = "SEARCH_MISS"
        result["details"] = f"Fallback check: missing golden value '{golden}'."
    return result


def batch_evaluate_records(
    records: list[dict[str, Any]],
    *,
    project_id: str,
    access_token: str | None,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    judge_region: str = DEFAULT_JUDGE_REGION,
    max_workers: int = 8,
    http_client: Any = DEFAULT_HTTP_CLIENT,
) -> list[dict[str, Any]]:
    """Evaluate all records in parallel with a thread pool."""
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(
                evaluate_single_record_with_judge,
                rec,
                project_id,
                access_token,
                judge_model=judge_model,
                judge_region=judge_region,
                http_client=http_client,
            )
            for rec in records
        ]
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())
    return sorted(results, key=lambda r: (str(r["id"]), int(r.get("run", 1))))


def render_combined_report_markdown(
    evaluated_records: list[dict[str, Any]],
    grade_by_case_id: dict[str, str],
    *,
    judge_model: str,
    judge_region: str,
) -> str:
    """Render a combined Markdown report showing BigLoom leakage verdicts and Judge results."""
    lines: list[str] = [
        "# Gemini Enterprise Large-File Evaluation Report",
        "",
        f"- **Judge Model**: `{judge_model}` (`{judge_region}`)",
        f"- **Total Executions**: {len(evaluated_records)}",
        "",
        "## Execution Results",
        "",
        "| Run | Case ID | BigLoom Verdict | Judge Verdict | Failure Mode | TTFT (ms) | Total Latency (ms) | Details |",
        "| :--- | :--- | :--- | :--- | :--- | ---: | ---: | :--- |",
    ]
    for rec in evaluated_records:
        cid = str(rec["id"])
        bl_verdict = grade_by_case_id.get(cid, LeakageVerdict.WRONG_ANSWER.value)
        details = str(rec.get("details", "")).replace("|", "\\|")
        lines.append(
            f"| {rec.get('run', 1)} | `{cid}` | `{bl_verdict}` | `{rec['status']}` | "
            f"`{rec.get('failure_mode', 'NONE')}` | {rec.get('ttft_ms', 0.0):.1f} | "
            f"{rec.get('total_latency_ms', 0.0):.1f} | {details} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None, *, http_client: Any = DEFAULT_HTTP_CLIENT) -> int:
    """Run the Gemini Enterprise harness and generate BigLoom and Judge reports."""
    config = load_config()
    parser = argparse.ArgumentParser(description="Run BigLoom queries against Gemini Enterprise.")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.json.")
    parser.add_argument("--cases", type=Path, required=True, help="Path to BigLoom cases.json.")
    parser.add_argument(
        "--manifest", type=Path, default=None, help="Optional path to BigLoom manifest.jsonl."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=SCRIPT_DIR / "raw_responses",
        help="Directory for raw StreamAssist JSON dumps.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=SCRIPT_DIR / "reports",
        help="Directory for output Markdown reports and token maps.",
    )
    parser.add_argument(
        "--responses-out",
        type=Path,
        default=None,
        help="Output path for normalized BigLoom EvalResponse JSON.",
    )
    parser.add_argument("--project-id", default=config.get("project_id", ""))
    parser.add_argument("--location", default=config.get("location", "global"))
    parser.add_argument("--engine-id", default=config.get("engine_id", ""))
    parser.add_argument("--assistant-id", default=config.get("assistant_id", "default_assistant"))
    parser.add_argument("--judge-model", default=os.environ.get("EVAL_JUDGE_MODEL", DEFAULT_JUDGE_MODEL))
    parser.add_argument("--judge-region", default=os.environ.get("EVAL_JUDGE_REGION", DEFAULT_JUDGE_REGION))
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--shuffle", action="store_true", default=False)
    parser.add_argument("--eval-workers", type=int, default=8)
    parser.add_argument("--eval-only", action="store_true")
    args = parser.parse_args(argv)

    if args.config:
        config = load_config(args.config)
        args.project_id = args.project_id or config.get("project_id", "")
        args.engine_id = args.engine_id or config.get("engine_id", "")
        args.location = config.get("location", args.location)

    cases = load_eval_cases(args.cases)
    manifest = load_manifest_entries(args.manifest)
    known_files = build_known_files(cases, manifest)

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.reports_dir.mkdir(parents=True, exist_ok=True)

    token = get_gcp_access_token() if not args.eval_only else None
    data_store_ids = [str(x) for x in config.get("data_store_ids", [])]

    records: list[dict[str, Any]] = []
    eval_responses_run1: list[EvalResponse] = []

    for run_idx in range(1, args.runs + 1):
        run_cases = list(cases)
        if args.shuffle and args.runs > 1:
            random.shuffle(run_cases)

        for idx, case in enumerate(run_cases, 1):
            raw_file = args.raw_dir / f"{case.id}_run{run_idx}_raw.json"
            chunks: list[dict[str, Any]] = []
            ttft_ms = 0.0
            total_latency_ms = 0.0
            err_str: str | None = None

            if args.eval_only:
                if not raw_file.exists():
                    alt_file = args.raw_dir / f"{case.id}_raw.json"
                    if alt_file.exists():
                        raw_file = alt_file
                if raw_file.exists():
                    chunks = parse_raw_chunks_text(raw_file.read_text())
            else:
                print(f"[Run {run_idx}/{args.runs} | {idx}/{len(run_cases)}] {case.id}: {case.query}")
                try:
                    if http_client is DEFAULT_HTTP_CLIENT:
                        try:
                            chunks, ttft_ms, total_latency_ms = query_stream_assist_grpc(
                                project_id=args.project_id,
                                location=args.location,
                                engine_id=args.engine_id,
                                assistant_id=args.assistant_id,
                                query_text=case.query,
                                data_store_ids=data_store_ids,
                                timeout=args.timeout,
                            )
                        except ImportError:
                            chunks, ttft_ms, total_latency_ms = query_stream_assist_rest(
                                project_id=args.project_id,
                                location=args.location,
                                engine_id=args.engine_id,
                                assistant_id=args.assistant_id,
                                query_text=case.query,
                                data_store_ids=data_store_ids,
                                access_token=token or "",
                                http_client=http_client,
                            )
                    else:
                        chunks, ttft_ms, total_latency_ms = query_stream_assist_rest(
                            project_id=args.project_id,
                            location=args.location,
                            engine_id=args.engine_id,
                            assistant_id=args.assistant_id,
                            query_text=case.query,
                            data_store_ids=data_store_ids,
                            access_token=token or "",
                            http_client=http_client,
                        )
                    raw_file.write_text(json.dumps(chunks, indent=2))
                except Exception as exc:
                    if is_auth_error(exc):
                        raise RuntimeError(
                            "Authentication expired during streamAssist run. Run bash login_workforce.sh."
                        ) from exc
                    err_str = str(exc)

            parsed = parse_stream_assist_chunks(chunks, known_files=known_files)
            if run_idx == 1:
                eval_responses_run1.append(
                    chunks_to_eval_response(case.id, chunks, known_files=known_files)
                )

            records.append(
                {
                    "id": case.id,
                    "run": run_idx,
                    "query": case.query,
                    "target_file": case.target_file,
                    "golden_value": case.golden_value,
                    "canary_value": case.canary_trap.canary_value if case.canary_trap else "",
                    "ttft_ms": ttft_ms,
                    "total_latency_ms": total_latency_ms,
                    "response_text": parsed["answer_text"],
                    "assist_tokens": parsed["assist_tokens"],
                    "cited_files": parsed["cited_files"],
                    "downloaded_files": parsed["downloaded_files"],
                    "blocked": parsed["blocked"],
                    "error": err_str,
                }
            )

    responses_out = args.responses_out or (args.reports_dir / "responses.json")
    responses_out.parent.mkdir(parents=True, exist_ok=True)
    responses_out.write_text(
        json.dumps([r.model_dump(mode="json") for r in eval_responses_run1], indent=2)
    )

    grade_report = grade_responses(cases, eval_responses_run1, corpus_files=known_files)
    (args.reports_dir / "grade_report.json").write_text(
        grade_report.model_dump_json(indent=2)
    )
    scorecard_md = render_scorecard_markdown(
        cases,
        grade_report,
        manifest_entries=manifest or None,
        out_path=args.reports_dir / "scorecard.md",
    )
    _ = scorecard_md

    evaluated = batch_evaluate_records(
        records,
        project_id=args.project_id,
        access_token=token,
        judge_model=args.judge_model,
        judge_region=args.judge_region,
        max_workers=args.eval_workers,
        http_client=http_client,
    )

    assist_map: dict[str, dict[str, Any]] = {}
    for rec in evaluated:
        cid = str(rec["id"])
        r_idx = int(rec.get("run", 1))
        assist_map.setdefault(cid, {})[f"run_{r_idx}"] = {
            "verdict": rec["status"],
            "failure_mode": rec.get("failure_mode", "NONE"),
            "assist_tokens": rec.get("assist_tokens", []),
        }
    (args.reports_dir / "assist_tokens.json").write_text(json.dumps(assist_map, indent=2))

    grade_by_id = {g.case_id: g.verdict.value for g in grade_report.results}
    combined_md = render_combined_report_markdown(
        evaluated,
        grade_by_id,
        judge_model=args.judge_model,
        judge_region=args.judge_region,
    )
    (args.reports_dir / "report.md").write_text(combined_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
