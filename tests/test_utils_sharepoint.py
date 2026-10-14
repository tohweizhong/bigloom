"""Tests for utils/upload_to_sharepoint.py and utils/inventory_sharepoint.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from utils import (
    ConfigError,
    get_file_metadata,
    get_token,
    list_drive_recursive,
    list_files,
    load_env,
    remote_path,
    resolve_drive,
    upload_file,
    upload_manifest,
    validate,
    verify,
)
from utils import upload_to_sharepoint as sp_mod


def test_load_env_and_validate_aliases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify load_env normalizes both sharepoint.env and .env variable names."""
    for key in (
        "SP_SITE_URL",
        "SP_TENANT_ID",
        "SP_CLIENT_ID",
        "SP_CLIENT_SECRET",
        "SP_TARGET_FOLDER",
        "SP_DRIVE_NAME",
        "TENANT_ID",
        "CLIENT_ID",
        "CLIENT_SECRET",
        "SHAREPOINT_HOST",
        "SHAREPOINT_SITE_PATH",
        "SHAREPOINT_FOLDER_PATH",
        "SHAREPOINT_LIBRARY",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "TENANT_ID=t-123\n"
        "CLIENT_ID=c-123\n"
        "CLIENT_SECRET=s-123\n"
        "SHAREPOINT_HOST=contoso.sharepoint.com\n"
        "SHAREPOINT_SITE_PATH=/sites/BigLoomSite\n",
        encoding="utf-8",
    )
    cfg = load_env(env_file)
    validate(cfg)
    assert cfg["SP_TENANT_ID"] == "t-123"
    assert cfg["SP_SITE_URL"] == "https://contoso.sharepoint.com/sites/BigLoomSite"
    assert cfg["SP_TARGET_FOLDER"] == "BigLoom-Eval"


def test_list_files_prefers_large_and_traps_subfolders(tmp_path: Path) -> None:
    """Verify list_files only returns large/ and traps/ files from a BigLoom run directory."""
    (tmp_path / "large").mkdir()
    (tmp_path / "traps").mkdir()
    f_large = tmp_path / "large" / "bl-001.docx"
    f_trap = tmp_path / "traps" / "bl-001_draft.docx"
    f_meta = tmp_path / "manifest.jsonl"
    f_large.write_bytes(b"large")
    f_trap.write_bytes(b"trap")
    f_meta.write_text("{}", encoding="utf-8")

    found = list_files(tmp_path)
    assert found == [f_large, f_trap]


def test_upload_verify_and_inventory_with_mock_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify get_token, resolve_drive, upload_file, verify, upload_manifest, and inventory."""
    calls: list[tuple[str, str]] = []

    def fake_request(
        method: str,
        url: str,
        token: str | None = None,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        retries: int = 4,
    ) -> dict[str, Any]:
        calls.append((method, url))
        if "oauth2/v2.0/token" in url:
            return {"access_token": "tok-abc"}
        if "/sites/contoso.sharepoint.com:" in url:
            return {"id": "site-1"}
        if url.endswith("/sites/site-1/drives"):
            return {"value": [{"name": "Documents", "id": "drive-1"}]}
        if url.endswith("/createUploadSession"):
            return {"uploadUrl": "https://upload.example.com/session-1"}
        if url.startswith("https://upload.example.com/session-1"):
            return {"id": "item-large", "size": 5 * 1024 * 1024}
        if url.endswith("/children?$select=id,name,size,folder,file,webUrl,lastModifiedDateTime"):
            return {
                "value": [
                    {
                        "id": "item-1",
                        "name": "bl-001.docx",
                        "size": 1024,
                        "file": {},
                        "webUrl": "https://contoso.sharepoint.com/bl-001.docx",
                    }
                ]
            }
        return {
            "id": "item-1",
            "size": 1030,
            "webUrl": "https://contoso.sharepoint.com/bl-001.docx",
        }

    monkeypatch.setattr(sp_mod, "request", fake_request)
    import utils.inventory_sharepoint as inv_mod

    monkeypatch.setattr(inv_mod, "request", fake_request)

    cfg = {
        "SP_SITE_URL": "https://contoso.sharepoint.com/sites/Test",
        "SP_LIBRARY": "Documents",
        "SP_TARGET_FOLDER": "BigLoom-Eval",
        "SP_TENANT_ID": "t",
        "SP_CLIENT_ID": "c",
        "SP_CLIENT_SECRET": "s",
    }
    token = get_token(cfg)
    assert token == "tok-abc"
    site_id, drive_id = resolve_drive(cfg, token)
    assert (site_id, drive_id) == ("site-1", "drive-1")

    small_file = tmp_path / "small.docx"
    small_file.write_bytes(b"x" * 1024)
    dest = remote_path("BigLoom-Eval", Path("large/small.docx"))
    upload_file(drive_id, token, small_file, dest)
    assert verify(drive_id, token, dest, 1024, ".docx") is True

    manifest_path = tmp_path / "manifest.jsonl"
    (tmp_path / "large").mkdir()
    (tmp_path / "traps").mkdir()
    (tmp_path / "large" / "t.docx").write_bytes(b"x" * 1024)
    (tmp_path / "traps" / "d.docx").write_bytes(b"x" * 1024)
    manifest_path.write_text(
        json.dumps({"target_file": "large/t.docx", "distractor_file": "traps/d.docx"}) + "\n",
        encoding="utf-8",
    )
    uploaded, failed = upload_manifest(
        manifest_path, drive_id, token, "BigLoom-Eval", dry_run=False
    )
    assert len(uploaded) == 2
    assert failed == []

    meta = get_file_metadata(token, drive_id, "BigLoom-Eval/large/t.docx")
    assert meta["webUrl"] == "https://contoso.sharepoint.com/bl-001.docx"
    items = list_drive_recursive(token, drive_id, current_path="BigLoom-Eval")
    assert len(items) == 1
    assert items[0]["name"] == "bl-001.docx"


def test_validate_rejects_bad_site_url() -> None:
    """Verify validate raises ConfigError when SP_SITE_URL is not an https sharepoint.com URL."""
    with pytest.raises(ConfigError):
        validate(
            {
                "SP_SITE_URL": "http://example.com/sites/test",
                "SP_TARGET_FOLDER": "BigLoom",
                "SP_ACCESS_TOKEN": "tok",
            }
        )
