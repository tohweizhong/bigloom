#!/usr/bin/env python3
"""Upload generated BigLoom artifacts to OneDrive or SharePoint via Microsoft Graph."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SIMPLE_UPLOAD_LIMIT_BYTES = 4 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 320 * 1024 * 4


class HttpResponse:
    """Normalized HTTP response wrapper for stdlib urllib calls."""

    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text

    def json(self) -> dict[str, Any]:
        loaded = json.loads(self.text) if self.text else {}
        return loaded if isinstance(loaded, dict) else {}


class UrllibClient:
    """Minimal requests-compatible HTTP client backed by urllib.request."""

    def _request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> HttpResponse:
        req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                return HttpResponse(resp.status, resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as err:
            return HttpResponse(err.code, err.read().decode("utf-8", errors="replace"))

    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        return self._request("GET", url, headers=headers)

    def post(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> HttpResponse:
        hdrs = dict(headers or {})
        raw_body: bytes | None = None
        if json is not None:
            import json as _json

            raw_body = _json.dumps(json).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        elif data is not None:
            raw_body = urllib.parse.urlencode(data).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
        return self._request("POST", url, headers=hdrs, body=raw_body)

    def put(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        data: bytes = b"",
    ) -> HttpResponse:
        return self._request("PUT", url, headers=headers, body=data)


DEFAULT_HTTP_CLIENT = UrllibClient()


def load_env_file(env_path: Path | None = None) -> None:
    """Load key-value pairs from a local .env file into os.environ."""
    candidates = [env_path] if env_path else [Path(".env"), Path(__file__).parent / ".env"]
    for path in candidates:
        if path and path.exists():
            for line in path.read_text().splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, val = stripped.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())
            break


def acquire_graph_access_token(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    http_client: Any = DEFAULT_HTTP_CLIENT,
) -> str:
    """Acquire an app-only Microsoft Graph token via OAuth2 client credentials."""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    resp = http_client.post(url, data=data)
    if resp.status_code != 200:
        raise RuntimeError(f"Graph token request failed ({resp.status_code}): {resp.text}")
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Graph token response did not include access_token.")
    return str(token)


def resolve_drive_id(
    access_token: str,
    *,
    user_principal_name: str | None = None,
    sharepoint_host: str | None = None,
    sharepoint_site_path: str | None = None,
    http_client: Any = DEFAULT_HTTP_CLIENT,
) -> str:
    """Resolve the target Microsoft Graph drive ID for OneDrive or SharePoint."""
    headers = {"Authorization": f"Bearer {access_token}"}
    if sharepoint_host and sharepoint_site_path:
        clean_site = sharepoint_site_path.strip("/")
        rel = (
            f"/sites/{clean_site.split('sites/')[-1]}"
            if "sites/" in clean_site
            else f"/sites/{clean_site}"
        )
        site_url = f"https://graph.microsoft.com/v1.0/sites/{sharepoint_host}:{rel}"
        site_resp = http_client.get(site_url, headers=headers)
        if site_resp.status_code != 200:
            raise RuntimeError(
                f"SharePoint site lookup failed ({site_resp.status_code}): {site_resp.text}"
            )
        site_id = site_resp.json()["id"]
        drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
        drive_resp = http_client.get(drive_url, headers=headers)
        if drive_resp.status_code != 200:
            raise RuntimeError(
                f"SharePoint drive lookup failed ({drive_resp.status_code}): {drive_resp.text}"
            )
        return str(drive_resp.json()["id"])

    if user_principal_name:
        od_url = f"https://graph.microsoft.com/v1.0/users/{user_principal_name}/drive"
        od_resp = http_client.get(od_url, headers=headers)
        if od_resp.status_code != 200:
            raise RuntimeError(f"OneDrive lookup failed ({od_resp.status_code}): {od_resp.text}")
        return str(od_resp.json()["id"])

    raise ValueError("Specify either SharePoint host/site or user_principal_name.")


def _remote_item_path(remote_folder: str, relative_path: str) -> str:
    clean_folder = remote_folder.strip("/")
    clean_rel = relative_path.strip("/")
    return f"{clean_folder}/{clean_rel}" if clean_folder else clean_rel


def upload_file_simple(
    access_token: str,
    drive_id: str,
    remote_path: str,
    local_filepath: Path,
    http_client: Any = DEFAULT_HTTP_CLIENT,
) -> None:
    """Upload a file smaller than 4 MB with a single HTTP PUT request."""
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{remote_path}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
    }
    resp = http_client.put(url, headers=headers, data=local_filepath.read_bytes())
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Simple PUT failed for {remote_path} ({resp.status_code}): {resp.text}"
        )


def upload_file_session(
    access_token: str,
    drive_id: str,
    remote_path: str,
    local_filepath: Path,
    http_client: Any = DEFAULT_HTTP_CLIENT,
    chunk_size: int = UPLOAD_CHUNK_BYTES,
) -> None:
    """Upload a file of 4 MB or larger with a Graph resumable upload session."""
    session_url = (
        f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{remote_path}:/createUploadSession"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "item": {
            "@microsoft.graph.conflictBehavior": "replace",
            "name": local_filepath.name,
        }
    }
    session_resp = http_client.post(session_url, headers=headers, json=body)
    if session_resp.status_code != 200:
        raise RuntimeError(
            f"Upload session creation failed for {remote_path} ({session_resp.status_code}): {session_resp.text}"
        )
    upload_url = session_resp.json().get("uploadUrl")
    if not upload_url:
        raise RuntimeError(f"No uploadUrl returned for {remote_path}.")

    file_size = local_filepath.stat().st_size
    with local_filepath.open("rb") as handle:
        start_byte = 0
        while start_byte < file_size:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            end_byte = start_byte + len(chunk) - 1
            chunk_headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
            }
            put_resp = http_client.put(upload_url, headers=chunk_headers, data=chunk)
            if put_resp.status_code in (200, 201):
                break
            if put_resp.status_code == 202:
                start_byte = end_byte + 1
                continue
            raise RuntimeError(
                f"Chunk upload failed for {remote_path} ({put_resp.status_code}): {put_resp.text}"
            )


def upload_manifest_files(
    manifest_path: Path,
    access_token: str,
    drive_id: str,
    remote_folder: str = "",
    http_client: Any = DEFAULT_HTTP_CLIENT,
) -> list[str]:
    """Upload all target and distractor files listed in a BigLoom manifest.jsonl file."""
    base_dir = manifest_path.parent
    uploaded: list[str] = []
    for line in manifest_path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        rel_paths: list[str] = []
        for key in ("target_file", "distractor_file", "relative_path"):
            val = record.get(key)
            if isinstance(val, str) and val and val not in rel_paths:
                rel_paths.append(val)
        for rel_path in rel_paths:
            if rel_path in uploaded:
                continue
            local_path = base_dir / rel_path
            remote_path = _remote_item_path(remote_folder, rel_path)
            size_bytes = local_path.stat().st_size
            if size_bytes < SIMPLE_UPLOAD_LIMIT_BYTES:
                upload_file_simple(
                    access_token=access_token,
                    drive_id=drive_id,
                    remote_path=remote_path,
                    local_filepath=local_path,
                    http_client=http_client,
                )
            else:
                upload_file_session(
                    access_token=access_token,
                    drive_id=drive_id,
                    remote_path=remote_path,
                    local_filepath=local_path,
                    http_client=http_client,
                )
            uploaded.append(rel_path)
    return uploaded


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for uploading a BigLoom manifest to OneDrive or SharePoint."""
    parser = argparse.ArgumentParser(description="Upload BigLoom manifest files to Microsoft 365.")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to manifest.jsonl.")
    parser.add_argument(
        "--remote-folder",
        default="",
        help="Remote folder in target drive (defaults to SP_TARGET_FOLDER or BigLoom-Eval).",
    )
    parser.add_argument("--env", type=Path, default=None, help="Optional path to .env file.")
    args = parser.parse_args(argv)

    load_env_file(args.env)
    tenant_id = os.environ.get("TENANT_ID") or os.environ["SP_TENANT_ID"]
    client_id = os.environ.get("CLIENT_ID") or os.environ["SP_CLIENT_ID"]
    client_secret = os.environ.get("CLIENT_SECRET") or os.environ["SP_CLIENT_SECRET"]
    token = acquire_graph_access_token(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    sp_host = os.environ.get("SHAREPOINT_HOST")
    sp_site_path = os.environ.get("SHAREPOINT_SITE_PATH")
    sp_site_url = os.environ.get("SP_SITE_URL", "")
    if (not sp_host or not sp_site_path) and sp_site_url:
        parsed_url = urllib.parse.urlparse(sp_site_url)
        sp_host = parsed_url.netloc
        sp_site_path = parsed_url.path

    drive_id = resolve_drive_id(
        token,
        user_principal_name=os.environ.get("USER_PRINCIPAL_NAME"),
        sharepoint_host=sp_host,
        sharepoint_site_path=sp_site_path,
    )
    remote_folder = (
        args.remote_folder
        or os.environ.get("SP_TARGET_FOLDER")
        or "BigLoom-Eval"
    )
    uploaded = upload_manifest_files(
        manifest_path=args.manifest,
        access_token=token,
        drive_id=drive_id,
        remote_folder=remote_folder,
    )
    print(f"Uploaded {len(uploaded)} files to drive {drive_id} under '{remote_folder}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
