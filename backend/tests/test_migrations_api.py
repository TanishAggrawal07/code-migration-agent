"""
Tests for /api/migrations endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.services.migration_service import MigrationService
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store() -> None:
    """Wipe the in-memory store before each test."""
    svc = MigrationService.get_instance()
    svc._store.clear()
    svc._locks.clear()


# ── POST /api/migrations ──────────────────────────────────────────────────

def test_create_migration_returns_201() -> None:
    resp = client.post("/api/migrations", json={"project_name": "MyApp"})
    assert resp.status_code == 201


def test_create_migration_returns_migration_id() -> None:
    resp = client.post("/api/migrations", json={"project_name": "MyApp"})
    data = resp.json()
    assert "migration_id" in data
    assert len(data["migration_id"]) == 36   # UUID4


def test_create_migration_returns_status_created() -> None:
    resp = client.post("/api/migrations", json={"project_name": "MyApp"})
    assert resp.json()["status"] == "created"


def test_create_migration_with_files() -> None:
    resp = client.post(
        "/api/migrations",
        json={"project_name": "WithFiles", "uploaded_files": ["a.cs", "b.cs"]},
    )
    assert resp.status_code == 201


def test_create_migration_empty_name_returns_422() -> None:
    resp = client.post("/api/migrations", json={"project_name": ""})
    assert resp.status_code == 422


def test_create_migration_missing_name_returns_422() -> None:
    resp = client.post("/api/migrations", json={})
    assert resp.status_code == 422


# ── GET /api/migrations ───────────────────────────────────────────────────

def test_list_migrations_empty() -> None:
    resp = client.get("/api/migrations")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_migrations_after_creation() -> None:
    client.post("/api/migrations", json={"project_name": "A"})
    client.post("/api/migrations", json={"project_name": "B"})
    resp = client.get("/api/migrations")
    assert resp.json()["total"] == 2


# ── GET /api/migrations/{id} ──────────────────────────────────────────────

def test_get_migration_returns_state() -> None:
    created = client.post("/api/migrations", json={"project_name": "GetTest"}).json()
    mid = created["migration_id"]
    resp = client.get(f"/api/migrations/{mid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["migration_id"] == mid
    assert data["project_name"] == "GetTest"


def test_get_migration_unknown_returns_404() -> None:
    resp = client.get("/api/migrations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_get_migration_has_current_stage() -> None:
    created = client.post("/api/migrations", json={"project_name": "StageTest"}).json()
    resp = client.get(f"/api/migrations/{created['migration_id']}")
    assert "current_stage" in resp.json()


# ── POST /api/migrations/{id}/run ────────────────────────────────────────

def test_run_workflow_returns_200() -> None:
    created = client.post("/api/migrations", json={"project_name": "RunTest"}).json()
    resp = client.post(f"/api/migrations/{created['migration_id']}/run")
    assert resp.status_code == 200


def test_run_workflow_returns_expected_keys() -> None:
    created = client.post("/api/migrations", json={"project_name": "KeyTest"}).json()
    resp = client.post(f"/api/migrations/{created['migration_id']}/run")
    data = resp.json()
    for key in ("migration_id", "stage", "is_complete", "is_failed", "message"):
        assert key in data, f"Missing key: {key}"


def test_run_workflow_completes_to_saved() -> None:
    created = client.post("/api/migrations", json={"project_name": "SavedTest"}).json()
    resp = client.post(f"/api/migrations/{created['migration_id']}/run")
    data = resp.json()
    assert data["stage"] == "saved"
    assert data["is_complete"] is True
    assert data["is_failed"] is False


def test_run_workflow_unknown_id_returns_404() -> None:
    resp = client.post("/api/migrations/00000000-0000-0000-0000-000000000000/run")
    assert resp.status_code == 404


def test_run_workflow_updates_stored_state() -> None:
    created = client.post("/api/migrations", json={"project_name": "UpdatedState"}).json()
    mid = created["migration_id"]
    client.post(f"/api/migrations/{mid}/run")
    state_resp = client.get(f"/api/migrations/{mid}")
    assert state_resp.json()["current_stage"] == "saved"


def test_run_workflow_twice_sequential_works() -> None:
    """After the first run completes the running flag is cleared — second run must succeed."""
    created = client.post("/api/migrations", json={"project_name": "TwiceTest"}).json()
    mid = created["migration_id"]
    r1 = client.post(f"/api/migrations/{mid}/run")
    r2 = client.post(f"/api/migrations/{mid}/run")
    assert r1.status_code == 200
    assert r2.status_code == 200


# ── GET /api/migrations/{id}/status ──────────────────────────────────────

def test_pipeline_status_before_run() -> None:
    created = client.post("/api/migrations", json={"project_name": "StatusPre"}).json()
    mid = created["migration_id"]
    resp = client.get(f"/api/migrations/{mid}/status")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("current_stage", "completed", "remaining", "progress_pct"):
        assert key in data


def test_pipeline_status_after_run() -> None:
    created = client.post("/api/migrations", json={"project_name": "StatusPost"}).json()
    mid = created["migration_id"]
    client.post(f"/api/migrations/{mid}/run")
    resp = client.get(f"/api/migrations/{mid}/status")
    data = resp.json()
    assert data["progress_pct"] == 100
    assert data["is_complete"] is True
    assert data["current_stage"] == "saved"


def test_pipeline_status_unknown_id_returns_404() -> None:
    resp = client.get("/api/migrations/00000000-0000-0000-0000-000000000000/status")
    assert resp.status_code == 404


# ── DELETE /api/migrations/{id} ───────────────────────────────────────────

def test_delete_migration_returns_204() -> None:
    created = client.post("/api/migrations", json={"project_name": "DeleteMe"}).json()
    resp = client.delete(f"/api/migrations/{created['migration_id']}")
    assert resp.status_code == 204


def test_delete_migration_removes_from_list() -> None:
    created = client.post("/api/migrations", json={"project_name": "Gone"}).json()
    mid = created["migration_id"]
    client.delete(f"/api/migrations/{mid}")
    resp = client.get(f"/api/migrations/{mid}")
    assert resp.status_code == 404


def test_delete_unknown_returns_404() -> None:
    resp = client.delete("/api/migrations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ── GET /api/migrations/{id}/download ──────────────────────────────────────

def test_download_unknown_returns_404() -> None:
    resp = client.get("/api/migrations/00000000-0000-0000-0000-000000000000/download")
    assert resp.status_code == 404


def test_download_empty_returns_400() -> None:
    created = client.post("/api/migrations", json={"project_name": "NoGenTest"}).json()
    mid = created["migration_id"]
    resp = client.get(f"/api/migrations/{mid}/download")
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "NoOutputGenerated"


def test_download_success() -> None:
    import zipfile
    import io
    from app.services.filesystem_service import FileSystemService
    import asyncio

    def run(coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    created = client.post("/api/migrations", json={"project_name": "DownloadTest"}).json()
    mid = created["migration_id"]

    # Manually write a generated java file into filesystem
    fs = FileSystemService.get_instance()
    # Ensure dirs are initialized
    run(fs.create_project_dir(mid))
    generated_dir = fs.get_generated_path(mid)
    
    # Save a fake Java class
    java_file = generated_dir / "Sample.java"
    java_file.write_text("public class Sample {}", encoding="utf-8")

    try:
        resp = client.get(f"/api/migrations/{mid}/download")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        
        # Verify contents of zip
        zip_data = io.BytesIO(resp.content)
        with zipfile.ZipFile(zip_data) as zf:
            namelist = zf.namelist()
            assert "Sample.java" in namelist
            assert zf.read("Sample.java") == b"public class Sample {}"
    finally:
        # Cleanup created folders
        run(fs.delete_project(mid))
