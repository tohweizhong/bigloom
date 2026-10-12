#!/usr/bin/env python3
"""Upload a BigLoom output folder or manifest.jsonl to SharePoint or OneDrive via Microsoft Graph.

Adapted from sharepoint-research/worldloom/upload_to_sharepoint.py and
sharepoint-research/bless_limitations/utils/generate_upload_mocks.py.
Uses only the Python standard library.

Usage:
  python3 utils/upload_to_sharepoint.py --source runs/trial-5mb            # Dry run
  python3 utils/upload_to_sharepoint.py --source runs/trial-5mb --upload   # Upload and verify
  python3 utils/upload_to_sharepoint.py --manifest runs/trial-5mb/manifest.jsonl --upload
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

GRAPH = "https://graph.microsoft.com/v1.0"
SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024  # Microsoft Graph limit for a single PUT (4 MiB).
CHUNK_SIZE = 327680 * 12  # 3.75 MiB (multiple of 320 KiB required by Graph).
CONFLICT_VALUES = {"replace", "fail", "rename"}
OFFICE_SUFFIXES = {".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm"}
OFFICE_GROWTH_LIMIT = 64 * 1024  # SharePoint metadata overhead on saved Office files.


class ConfigError(Exception):
    """A required setting is missing or invalid."""


class GraphError(Exception):
    """Microsoft Graph returned an HTTP or connection error."""


def find_default_env() -> Path:
    """Locate the first existing .env or sharepoint.env file in the workspace."""
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [
        Path.cwd() / "sharepoint.env",
        Path.cwd() / ".env",
        repo_root / "sharepoint.env",
        repo_root / ".env",
        repo_root / "harnesses" / "gemini_enterprise" / ".env",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return repo_root / "sharepoint.env"


def load_env(path: Path | None = None) -> dict[str, str]:
    """Read KEY=VALUE settings from a file and merge with environment variables."""
    values: dict[str, str] = {}
    if path is not None:
        if not path.is_file():
            raise ConfigError(f"Settings file not found: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            values[key.strip()] = value.strip()

    for key in (
        "SP_SITE_URL",
        "SP_LIBRARY",
        "SP_TARGET_FOLDER",
        "SP_TENANT_ID",
        "SP_CLIENT_ID",
        "SP_CLIENT_SECRET",
        "SP_ACCESS_TOKEN",
        "SP_CONFLICT",
        "SOURCE_DIR",
        "TENANT_ID",
        "CLIENT_ID",
        "CLIENT_SECRET",
        "SHAREPOINT_HOST",
        "SHAREPOINT_SITE_PATH",
        "SHAREPOINT_FOLDER_PATH",
        "USER_PRINCIPAL_NAME",
    ):
        if key not in values and key in os.environ:
            values[key] = os.environ[key]

    # Normalize aliases between sharepoint.env and .env formats.
    if not values.get("SP_TENANT_ID") and values.get("TENANT_ID"):
        values["SP_TENANT_ID"] = values["TENANT_ID"]
    if not values.get("SP_CLIENT_ID") and values.get("CLIENT_ID"):
        values["SP_CLIENT_ID"] = values["CLIENT_ID"]
    if not values.get("SP_CLIENT_SECRET") and values.get("CLIENT_SECRET"):
        values["SP_CLIENT_SECRET"] = values["CLIENT_SECRET"]
    if (
        not values.get("SP_SITE_URL")
        and values.get("SHAREPOINT_HOST")
        and values.get("SHAREPOINT_SITE_PATH")
    ):
        host = values["SHAREPOINT_HOST"].strip("/")
        site_path = values["SHAREPOINT_SITE_PATH"].strip("/")
        if not site_path.startswith("sites/"):
            site_path = f"sites/{site_path}"
        values["SP_SITE_URL"] = f"https://{host}/{site_path}"
    if not values.get("SP_TARGET_FOLDER"):
        values["SP_TARGET_FOLDER"] = values.get("SHAREPOINT_FOLDER_PATH") or "BigLoom-Eval"
    if not values.get("SP_LIBRARY"):
        values["SP_LIBRARY"] = "Documents"
    return values


def check_file_mode(path: Path) -> None:
    """Warn when other local users can read the credentials file."""
    if not path.is_file():
        return
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        print(
            f"WARNING: {path.name} has mode {oct(mode)}. Run: chmod 600 {path}",
            file=sys.stderr,
        )


def validate(cfg: dict[str, str]) -> None:
    """Verify that required SharePoint or OneDrive settings are present."""
    has_site = bool(cfg.get("SP_SITE_URL"))
    has_upn = bool(cfg.get("USER_PRINCIPAL_NAME"))
    if not has_site and not has_upn:
        raise ConfigError(
            "Set SP_SITE_URL (or SHAREPOINT_HOST + SHAREPOINT_SITE_PATH) or USER_PRINCIPAL_NAME."
        )
    if not cfg.get("SP_TARGET_FOLDER"):
        raise ConfigError("Set SP_TARGET_FOLDER in the settings file or pass --target-folder.")
    if not cfg.get("SP_ACCESS_TOKEN"):
        missing = [
            k for k in ("SP_TENANT_ID", "SP_CLIENT_ID", "SP_CLIENT_SECRET") if not cfg.get(k)
        ]
        if missing:
            raise ConfigError(
                "Fill in these values in the settings file: " + ", ".join(missing)
            )
    if has_site:
        site = urllib.parse.urlparse(cfg["SP_SITE_URL"])
        if site.scheme != "https" or not site.netloc.endswith(".sharepoint.com"):
            raise ConfigError(
                "SP_SITE_URL must look like https://<tenant>.sharepoint.com/sites/<site>"
            )
    conflict = cfg.get("SP_CONFLICT", "replace")
    if conflict not in CONFLICT_VALUES:
        raise ConfigError(f"SP_CONFLICT must be one of {sorted(CONFLICT_VALUES)}")


def list_files(source: Path) -> list[Path]:
    """Return uploadable files under source in deterministic order.

    If source is a BigLoom run folder containing large/ or traps/, only files
    inside large/ and traps/ are returned so metadata files stay local.
    """
    if not source.is_dir():
        raise ConfigError(f"SOURCE_DIR is not a folder: {source}")
    large_dir = source / "large"
    traps_dir = source / "traps"
    if large_dir.is_dir() or traps_dir.is_dir():
        found: list[Path] = []
        for sub in (large_dir, traps_dir):
            if sub.is_dir():
                found.extend(sorted(p for p in sub.rglob("*") if p.is_file()))
        return found
    return sorted(p for p in source.rglob("*") if p.is_file())


def request(
    method: str,
    url: str,
    token: str | None = None,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    retries: int = 4,
) -> dict[str, Any]:
    """Send one HTTP request to Microsoft Graph and retry on 429 or 5xx."""
    hdrs = dict(headers or {})
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:500]
            if err.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = int(err.headers.get("Retry-After") or 2 ** (attempt + 1))
                print(f"  Graph returned {err.code}. Retry in {wait} s.", file=sys.stderr)
                time.sleep(wait)
                continue
            raise GraphError(
                f"{method} {url.split('?')[0]} -> HTTP {err.code}: {detail}"
            ) from None
        except (urllib.error.URLError, ConnectionError, TimeoutError) as err:
            if attempt < retries:
                wait = 2 ** (attempt + 1)
                print(f"  Connection error ({err}). Retry in {wait} s.", file=sys.stderr)
                time.sleep(wait)
                continue
            raise GraphError(f"{method} {url.split('?')[0]} -> {err}") from None
    raise GraphError(f"{method} {url} failed after {retries} retries")


def get_token(cfg: dict[str, str]) -> str:
    """Return SP_ACCESS_TOKEN or acquire an OAuth2 client-credentials token."""
    if cfg.get("SP_ACCESS_TOKEN"):
        return cfg["SP_ACCESS_TOKEN"]
    url = (
        f"https://login.microsoftonline.com/"
        f"{urllib.parse.quote(cfg['SP_TENANT_ID'])}/oauth2/v2.0/token"
    )
    form = urllib.parse.urlencode(
        {
            "client_id": cfg["SP_CLIENT_ID"],
            "client_secret": cfg["SP_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
    ).encode()
    data = request(
        "POST",
        url,
        body=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return str(data["access_token"])


def resolve_drive(cfg: dict[str, str], token: str) -> tuple[str, str]:
    """Return (site_id, drive_id) for a SharePoint site library or OneDrive user."""
    if cfg.get("SP_SITE_URL"):
        site = urllib.parse.urlparse(cfg["SP_SITE_URL"])
        path = site.path.rstrip("/")
        site_url = (
            f"{GRAPH}/sites/{site.netloc}:{urllib.parse.quote(path)}"
            if path
            else f"{GRAPH}/sites/{site.netloc}"
        )
        site_id = str(request("GET", site_url, token)["id"])
        drives = request("GET", f"{GRAPH}/sites/{site_id}/drives", token).get("value", [])
        wanted = cfg.get("SP_LIBRARY", "Documents").strip().lower()
        for drive in drives:
            if drive.get("name", "").lower() == wanted:
                return site_id, str(drive["id"])
        default_drive = request("GET", f"{GRAPH}/sites/{site_id}/drive", token)
        if default_drive.get("id"):
            return site_id, str(default_drive["id"])
        names = ", ".join(d.get("name", "?") for d in drives)
        raise ConfigError(
            f"Library '{cfg.get('SP_LIBRARY')}' not found. Libraries in this site: {names}"
        )

    upn = cfg["USER_PRINCIPAL_NAME"]
    od = request("GET", f"{GRAPH}/users/{urllib.parse.quote(upn)}/drive", token)
    return "onedrive", str(od["id"])


def remote_path(target: str, rel: Path) -> str:
    """Join the target remote folder and relative path with URL encoding."""
    parts = [p for p in target.strip("/").split("/") if p] + list(rel.parts)
    return "/".join(urllib.parse.quote(p) for p in parts)


def upload_file(
    drive_id: str,
    token: str,
    local: Path,
    dest: str,
    conflict: str = "replace",
) -> dict[str, Any]:
    """Upload one file using simple PUT (<= 4 MiB) or a resumable session (> 4 MiB)."""
    size = local.stat().st_size
    if size <= SIMPLE_UPLOAD_LIMIT:
        url = (
            f"{GRAPH}/drives/{drive_id}/root:/{dest}:/content"
            f"?@microsoft.graph.conflictBehavior={conflict}"
        )
        return request(
            "PUT",
            url,
            token,
            body=local.read_bytes(),
            headers={"Content-Type": "application/octet-stream"},
        )
    session = request(
        "POST",
        f"{GRAPH}/drives/{drive_id}/root:/{dest}:/createUploadSession",
        token,
        body=json.dumps({"item": {"@microsoft.graph.conflictBehavior": conflict}}).encode(),
        headers={"Content-Type": "application/json"},
    )
    upload_url = str(session["uploadUrl"])
    result: dict[str, Any] = {}
    with local.open("rb") as fh:
        start = 0
        while start < size:
            chunk = fh.read(CHUNK_SIZE)
            end = start + len(chunk) - 1
            result = request(
                "PUT",
                upload_url,
                None,
                body=chunk,
                headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{size}",
                },
            )
            start = end + 1
    return result


def verify(
    drive_id: str,
    token: str,
    dest: str,
    expected_size: int,
    suffix: str = "",
) -> bool:
    """Fetch the uploaded item metadata from Graph and verify its byte size."""
    item = request("GET", f"{GRAPH}/drives/{drive_id}/root:/{dest}", token)
    size = int(item.get("size", -1))
    if suffix.lower() in OFFICE_SUFFIXES:
        return expected_size <= size <= expected_size + OFFICE_GROWTH_LIMIT
    return size == expected_size


def upload_manifest(
    manifest_path: Path,
    drive_id: str,
    token: str,
    target_folder: str,
    conflict: str = "replace",
    dry_run: bool = False,
) -> tuple[list[str], list[str]]:
    """Upload and verify all target and distractor files listed in manifest.jsonl."""
    base_dir = manifest_path.parent
    rel_paths: list[Path] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        for key in ("target_file", "distractor_file", "relative_path"):
            val = record.get(key)
            if isinstance(val, str) and val:
                rel = Path(val)
                if rel not in rel_paths:
                    rel_paths.append(rel)

    uploaded: list[str] = []
    failed: list[str] = []
    for i, rel in enumerate(rel_paths, 1):
        local = base_dir / rel
        if dry_run:
            print(f"  would upload  {rel}")
            uploaded.append(str(rel))
            continue
        dest = remote_path(target_folder, rel)
        try:
            upload_file(drive_id, token, local, dest, conflict)
            ok = verify(drive_id, token, dest, local.stat().st_size, local.suffix)
        except GraphError as err:
            ok = False
            print(f"  [{i}/{len(rel_paths)}] FAIL  {rel}: {err}", file=sys.stderr)
        else:
            print(f"  [{i}/{len(rel_paths)}] {'OK  ' if ok else 'SIZE MISMATCH'}  {rel}")
        if ok:
            uploaded.append(str(rel))
        else:
            failed.append(str(rel))
    return uploaded, failed


def main(argv: list[str] | None = None) -> int:
    """Run the SharePoint upload CLI."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--env",
        default="",
        help="Path to the .env or sharepoint.env settings file.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload the files. Without this flag, the script performs a dry run.",
    )
    parser.add_argument(
        "--source",
        default="",
        help="Folder to upload (for example runs/trial-5mb).",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="Optional path to manifest.jsonl instead of scanning a folder.",
    )
    parser.add_argument(
        "--target-folder",
        default="",
        help="Override SP_TARGET_FOLDER in SharePoint.",
    )
    args = parser.parse_args(argv)

    env_path = Path(args.env).resolve() if args.env else find_default_env()
    try:
        cfg = load_env(env_path if env_path.is_file() else None)
        if args.target_folder:
            cfg["SP_TARGET_FOLDER"] = args.target_folder
        if args.source:
            cfg["SOURCE_DIR"] = args.source
        if env_path.is_file():
            check_file_mode(env_path)
        validate(cfg)
    except ConfigError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    conflict = cfg.get("SP_CONFLICT", "replace")
    try:
        token = get_token(cfg)
        _, drive_id = resolve_drive(cfg, token)
    except (GraphError, ConfigError, KeyError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 3

    target_label = cfg.get("SP_SITE_URL") or cfg.get("USER_PRINCIPAL_NAME")
    print(
        f"Target : {target_label}  library '{cfg.get('SP_LIBRARY', 'Documents')}'  "
        f"folder '{cfg['SP_TARGET_FOLDER']}'"
    )
    print(f"Drive  : {drive_id} (conflict={conflict})")

    if args.manifest:
        manifest_path = Path(args.manifest).resolve()
        if not manifest_path.is_file():
            print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
            return 2
        uploaded, failed = upload_manifest(
            manifest_path=manifest_path,
            drive_id=drive_id,
            token=token,
            target_folder=cfg["SP_TARGET_FOLDER"],
            conflict=conflict,
            dry_run=not args.upload,
        )
        if not args.upload:
            print("Dry run only. No file was uploaded. Add --upload to upload.")
            return 0
        print(f"Uploaded and verified: {len(uploaded)} of {len(uploaded) + len(failed)}.")
        return 1 if failed else 0

    base_parent = env_path.parent if env_path.is_file() else Path.cwd()
    raw_source = cfg.get("SOURCE_DIR", "runs/trial-5mb")
    source = (
        Path(raw_source).resolve()
        if Path(raw_source).is_absolute() or Path(raw_source).exists()
        else (base_parent / raw_source).resolve()
    )
    try:
        files = list_files(source)
    except ConfigError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    total = sum(f.stat().st_size for f in files)
    print(f"Source : {source}  ({len(files)} files, {total / 1024:.0f} KiB)")

    if not args.upload:
        for f in files:
            print(f"  would upload  {f.relative_to(source)}")
        print("Dry run only. No file was uploaded. Add --upload to upload.")
        return 0

    failed_files: list[str] = []
    for i, f in enumerate(files, 1):
        rel = f.relative_to(source)
        dest = remote_path(cfg["SP_TARGET_FOLDER"], rel)
        try:
            upload_file(drive_id, token, f, dest, conflict)
            ok = verify(drive_id, token, dest, f.stat().st_size, f.suffix)
        except GraphError as err:
            ok = False
            print(f"  [{i}/{len(files)}] FAIL  {rel}: {err}", file=sys.stderr)
        else:
            print(f"  [{i}/{len(files)}] {'OK  ' if ok else 'SIZE MISMATCH'}  {rel}")
        if not ok:
            failed_files.append(str(rel))

    print(f"Uploaded and verified: {len(files) - len(failed_files)} of {len(files)}.")
    if failed_files:
        print("Failed files:", *failed_files, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
