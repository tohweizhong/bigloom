#!/usr/bin/env python3
"""Inventory SharePoint or OneDrive folders and resolve file webUrl links via Microsoft Graph.

Adapted from sharepoint-research/utils/inventory_sharepoint_onedrive.py and
sharepoint-research/utils/get_onedrive_file_urls.py.
Uses only the Python standard library.

Usage:
  python3 utils/inventory_sharepoint.py
  python3 utils/inventory_sharepoint.py --folder BigLoom-Eval
  python3 utils/inventory_sharepoint.py --resolve-url BigLoom-Eval/large/bl-001-docx-5mb_fy2026_final.docx
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from .upload_to_sharepoint import (
    GRAPH,
    ConfigError,
    GraphError,
    find_default_env,
    get_token,
    load_env,
    request,
    resolve_drive,
    validate,
)


def get_file_metadata(
    token: str,
    drive_id: str,
    remote_item_path: str,
) -> dict[str, Any]:
    """Fetch metadata (including webUrl and size) for one remote path in a drive."""
    encoded = "/".join(
        urllib.parse.quote(part) for part in remote_item_path.strip("/").split("/") if part
    )
    url = f"{GRAPH}/drives/{drive_id}/root:/{encoded}"
    return request("GET", url, token)


def list_drive_recursive(
    token: str,
    drive_id: str,
    item_id: str = "root",
    current_path: str = "",
    max_depth: int = 3,
    current_depth: int = 0,
) -> list[dict[str, Any]]:
    """Recursively list files and folders in a SharePoint or OneDrive drive."""
    if current_depth > max_depth:
        return []
    if item_id == "root" and current_path:
        encoded = "/".join(
            urllib.parse.quote(part) for part in current_path.strip("/").split("/") if part
        )
        url = (
            f"{GRAPH}/drives/{drive_id}/root:/{encoded}:/children"
            "?$select=id,name,size,folder,file,webUrl,lastModifiedDateTime"
        )
    elif item_id == "root":
        url = (
            f"{GRAPH}/drives/{drive_id}/root/children"
            "?$select=id,name,size,folder,file,webUrl,lastModifiedDateTime"
        )
    else:
        url = (
            f"{GRAPH}/drives/{drive_id}/items/{item_id}/children"
            "?$select=id,name,size,folder,file,webUrl,lastModifiedDateTime"
        )

    data = request("GET", url, token)
    items = data.get("value", [])
    results: list[dict[str, Any]] = []
    for item in items:
        name = str(item.get("name", ""))
        item_path = f"{current_path.strip('/')}/{name}" if current_path else name
        size_bytes = int(item.get("size", 0))
        is_folder = "folder" in item
        entry = {
            "name": name,
            "path": item_path,
            "id": item.get("id"),
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024.0 * 1024.0), 2),
            "type": "folder" if is_folder else "file",
            "web_url": item.get("webUrl"),
            "last_modified": item.get("lastModifiedDateTime"),
        }
        results.append(entry)
        if is_folder and item.get("id"):
            results.extend(
                list_drive_recursive(
                    token=token,
                    drive_id=drive_id,
                    item_id=str(item["id"]),
                    current_path=item_path,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                )
            )
    return results


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for listing SharePoint files or resolving direct webUrl links."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="", help="Path to .env or sharepoint.env.")
    parser.add_argument("--folder", default="", help="Optional starting folder path in the drive.")
    parser.add_argument("--max-depth", type=int, default=3, help="Maximum folder recursion depth.")
    parser.add_argument(
        "--resolve-url",
        nargs="*",
        default=None,
        help="One or more remote file paths to resolve to webUrl.",
    )
    parser.add_argument("--out", default="", help="Optional JSON file path to save the inventory.")
    args = parser.parse_args(argv)

    env_path = Path(args.env).resolve() if args.env else find_default_env()
    try:
        cfg = load_env(env_path if env_path.is_file() else None)
        validate(cfg)
        token = get_token(cfg)
        _, drive_id = resolve_drive(cfg, token)
    except (ConfigError, GraphError, KeyError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    if args.resolve_url is not None:
        for rel_path in args.resolve_url:
            try:
                meta = get_file_metadata(token, drive_id, rel_path)
                print(f"{rel_path} -> {meta.get('webUrl')} ({meta.get('size', 0)} bytes)")
            except GraphError as err:
                print(f"ERROR {rel_path}: {err}", file=sys.stderr)
                return 1
        return 0

    items = list_drive_recursive(
        token=token,
        drive_id=drive_id,
        current_path=args.folder,
        max_depth=args.max_depth,
    )
    for item in items:
        print(
            f"{item['type'].upper():<6} | {item['size_mb']:8.2f} MiB | "
            f"{item['path']} | {item.get('web_url') or ''}"
        )
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        print(f"Saved {len(items)} inventory entries to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
