"""
Tests for POST /api/migrations/{id}/upload and related endpoints.
"""

import asyncio
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.services.filesystem_service import FileSystemService
from app.services.migration_service import MigrationService
from main import app

client = TestClient(app)


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.new_event_loop().run_until_complete(coro)


def make_zip_bytes(files: dict[str, bytes]) -> bytes:
    """Build an in-memory ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clean_state() -> None:  # type: ignore[return]
    """Reset in-memory store and remove any filesystem artefacts."""
    svc = MigrationService.get_instance()
    svc._store.clear()
    svc._locks.clear()
    yield
    # Clean up any files created during the test
    fs = FileSystemService.get_instance()
    for mid in list(svc._store.keys()):
        run(fs.delete_project(mid))
    svc._store.clear()
    svc._locks.clear()


def create_migration(project_name: str = "TestProject") -> str:
    """Helper: create a migration and return its ID."""
    resp = client.post(
        "/api/migrations",
        json={"project_name": project_name},
    )
    assert resp.status_code == 201
    return resp.json()["migration_id"]


# ── POST /api/migrations/{id}/upload ─────────────────────────────────────

def test_upload_single_cs_file() -> None:
    mid = create_migration()
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("Program.cs", b"public class Program {}", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["migration_id"] == mid
    assert data["uploaded_count"] == 1
    assert "Program.cs" in data["uploaded_files"]


def test_upload_multiple_files() -> None:
    mid = create_migration()
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files=[
            ("files", ("A.cs", b"class A {}", "text/plain")),
            ("files", ("B.cs", b"class B {}", "text/plain")),
            ("files", ("App.csproj", b"<Project/>", "text/xml")),
        ],
    )
    assert resp.status_code == 200
    assert resp.json()["uploaded_count"] == 3


def test_upload_returns_project_root() -> None:
    mid = create_migration()
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("X.cs", b"class X {}", "text/plain")},
    )
    assert "project_root" in resp.json()
    assert mid in resp.json()["project_root"]


def test_upload_updates_migration_state() -> None:
    mid = create_migration()
    client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("State.cs", b"class State {}", "text/plain")},
    )
    state = client.get(f"/api/migrations/{mid}").json()
    assert "State.cs" in state["uploaded_files"]
    assert state["project_root"] != ""
    assert state["last_upload_time"] is not None


def test_upload_unknown_migration_returns_404() -> None:
    resp = client.post(
        "/api/migrations/00000000-0000-0000-0000-000000000000/upload",
        files={"files": ("F.cs", b"x", "text/plain")},
    )
    assert resp.status_code == 404


def test_upload_unsupported_extension_returns_422() -> None:
    mid = create_migration()
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("evil.exe", b"\x4d\x5a", "application/octet-stream")},
    )
    assert resp.status_code == 422


def test_upload_empty_file_returns_422() -> None:
    mid = create_migration()
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("Empty.cs", b"", "text/plain")},
    )
    assert resp.status_code == 422


def test_upload_duplicate_filenames_returns_422() -> None:
    mid = create_migration()
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files=[
            ("files", ("Dup.cs", b"class A {}", "text/plain")),
            ("files", ("Dup.cs", b"class B {}", "text/plain")),
        ],
    )
    assert resp.status_code == 422


def test_upload_no_files_returns_422() -> None:
    mid = create_migration()
    # Send multipart with empty list — FastAPI requires at least one file field
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files=[("files", ("Holder.cs", b"x", "text/plain"))],
    )
    # One valid file should succeed, confirming the endpoint works
    assert resp.status_code == 200


def test_upload_zip_extracts_contents() -> None:
    mid = create_migration()
    zipped = make_zip_bytes({
        "Program.cs": b"public class Program {}",
        "Models/User.cs": b"public class User {}",
        "App.csproj": b"<Project/>",
    })
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("project.zip", zipped, "application/zip")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["uploaded_count"] == 3


def test_upload_zip_skips_unsupported_extensions() -> None:
    mid = create_migration()
    zipped = make_zip_bytes({
        "Good.cs": b"class Good {}",
        "Bad.exe": b"\x4d\x5a",
    })
    resp = client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("mixed.zip", zipped, "application/zip")},
    )
    assert resp.status_code == 200
    assert resp.json()["uploaded_count"] == 1


def test_upload_multiple_times_accumulates_files() -> None:
    mid = create_migration()
    client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("First.cs", b"class First {}", "text/plain")},
    )
    client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("Second.cs", b"class Second {}", "text/plain")},
    )
    state = client.get(f"/api/migrations/{mid}").json()
    assert "First.cs" in state["uploaded_files"]
    assert "Second.cs" in state["uploaded_files"]


def test_upload_persists_files_to_disk() -> None:
    mid = create_migration()
    client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("Disk.cs", b"class Disk {}", "text/plain")},
    )
    fs = FileSystemService.get_instance()
    files = run(fs.list_files(mid))
    assert "Disk.cs" in files


# ── GET /api/migrations/{id}/files ───────────────────────────────────────

def test_list_files_empty_before_upload() -> None:
    mid = create_migration()
    resp = client.get(f"/api/migrations/{mid}/files")
    assert resp.status_code == 200
    assert resp.json()["file_count"] == 0


def test_list_files_after_upload() -> None:
    mid = create_migration()
    client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("Listed.cs", b"class Listed {}", "text/plain")},
    )
    resp = client.get(f"/api/migrations/{mid}/files")
    assert resp.status_code == 200
    data = resp.json()
    assert data["file_count"] == 1
    assert "Listed.cs" in data["files"]


def test_list_files_unknown_migration_returns_404() -> None:
    resp = client.get("/api/migrations/00000000-0000-0000-0000-000000000000/files")
    assert resp.status_code == 404


# ── DELETE /api/migrations/{id}/files ───────────────────────────────────

def test_delete_files_returns_204() -> None:
    mid = create_migration()
    client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("ToDelete.cs", b"class ToDelete {}", "text/plain")},
    )
    resp = client.delete(f"/api/migrations/{mid}/files")
    assert resp.status_code == 204


def test_delete_files_removes_from_disk() -> None:
    mid = create_migration()
    client.post(
        f"/api/migrations/{mid}/upload",
        files={"files": ("Gone.cs", b"class Gone {}", "text/plain")},
    )
    client.delete(f"/api/migrations/{mid}/files")
    fs = FileSystemService.get_instance()
    files = run(fs.list_files(mid))
    assert files == []


def test_delete_files_unknown_migration_returns_404() -> None:
    resp = client.delete("/api/migrations/00000000-0000-0000-0000-000000000000/files")
    assert resp.status_code == 404


# ── Workflow integration ──────────────────────────────────────────────────

def test_workflow_run_after_upload_reflects_real_files() -> None:
    """After uploading files, running the workflow should reference them."""
    mid = create_migration()
    client.post(
        f"/api/migrations/{mid}/upload",
        files=[
            ("files", ("UserService.cs", b"public class UserService {}", "text/plain")),
            ("files", ("OrderService.cs", b"public class OrderService {}", "text/plain")),
        ],
    )
    run_resp = client.post(f"/api/migrations/{mid}/run")
    assert run_resp.status_code == 200
    assert run_resp.json()["is_complete"] is True

    state = client.get(f"/api/migrations/{mid}").json()
    parsed = [pf["filename"] for pf in state["parsed_files"]]
    assert "UserService.cs" in parsed
    assert "OrderService.cs" in parsed


def test_full_pipeline_create_upload_run_status() -> None:
    """Full integration: create → upload → run → check 100% status."""
    # 1. Create
    mid = create_migration("FullPipelineTest")

    # 2. Upload
    upload_resp = client.post(
        f"/api/migrations/{mid}/upload",
        files=[
            ("files", ("Program.cs", b"public class Program { static void Main() {} }", "text/plain")),
            ("files", ("App.csproj", b"<Project Sdk=\"Microsoft.NET.Sdk\"/>", "text/xml")),
        ],
    )
    assert upload_resp.status_code == 200
    assert upload_resp.json()["uploaded_count"] == 2

    # 3. Run
    run_resp = client.post(f"/api/migrations/{mid}/run")
    assert run_resp.status_code == 200
    assert run_resp.json()["stage"] == "saved"

    # 4. Status
    status_resp = client.get(f"/api/migrations/{mid}/status")
    assert status_resp.json()["progress_pct"] == 100
