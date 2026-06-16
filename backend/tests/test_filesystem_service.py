"""
Tests for FileSystemService.
"""

import asyncio
from pathlib import Path

import pytest

from app.services.filesystem_service import FileSystemError, FileSystemService


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.new_event_loop().run_until_complete(coro)


MIGRATION_ID = "test-fs-00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def cleanup_dirs() -> None:  # type: ignore[return]
    """Remove test project dirs before and after each test."""
    svc = FileSystemService.get_instance()
    run(svc.delete_project(MIGRATION_ID))
    yield
    run(svc.delete_project(MIGRATION_ID))


# ── Singleton ─────────────────────────────────────────────────────────────

def test_singleton() -> None:
    a = FileSystemService.get_instance()
    b = FileSystemService.get_instance()
    assert a is b


# ── create_project_dir ────────────────────────────────────────────────────

def test_create_project_dir_returns_path() -> None:
    svc = FileSystemService.get_instance()
    path = run(svc.create_project_dir(MIGRATION_ID))
    assert isinstance(path, Path)
    assert path.exists()
    assert path.is_dir()


def test_create_project_dir_idempotent() -> None:
    svc = FileSystemService.get_instance()
    p1 = run(svc.create_project_dir(MIGRATION_ID))
    p2 = run(svc.create_project_dir(MIGRATION_ID))
    assert p1 == p2


def test_create_project_dir_creates_generated_and_temp() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    assert svc.get_generated_path(MIGRATION_ID).exists()
    assert svc.get_temp_path(MIGRATION_ID).exists()


# ── save_files ────────────────────────────────────────────────────────────

def test_save_files_writes_to_disk() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    saved = run(svc.save_files(MIGRATION_ID, [("Hello.cs", b"public class Hello {}")]))
    assert saved == ["Hello.cs"]
    dest = svc.get_project_path(MIGRATION_ID) / "Hello.cs"
    assert dest.exists()
    assert dest.read_bytes() == b"public class Hello {}"


def test_save_files_multiple() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    files = [("A.cs", b"class A {}"), ("B.cs", b"class B {}"), ("App.csproj", b"<Project/>")]
    saved = run(svc.save_files(MIGRATION_ID, files))
    assert len(saved) == 3


def test_save_files_sanitises_filename() -> None:
    """Path components in filenames should be stripped."""
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    saved = run(svc.save_files(MIGRATION_ID, [("../../evil.cs", b"bad")]))
    assert saved == ["evil.cs"]
    assert (svc.get_project_path(MIGRATION_ID) / "evil.cs").exists()


# ── list_files ────────────────────────────────────────────────────────────

def test_list_files_empty_dir() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    files = run(svc.list_files(MIGRATION_ID))
    assert files == []


def test_list_files_returns_saved_files() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    run(svc.save_files(MIGRATION_ID, [("Foo.cs", b"x"), ("Bar.cs", b"y")]))
    files = run(svc.list_files(MIGRATION_ID))
    assert "Foo.cs" in files
    assert "Bar.cs" in files


def test_list_files_with_extension_filter() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    run(svc.save_files(MIGRATION_ID, [("A.cs", b""), ("B.xml", b""), ("C.json", b"")]))
    cs_only = run(svc.list_files(MIGRATION_ID, extensions={".cs"}))
    assert "A.cs" in cs_only
    assert all(f.endswith(".cs") for f in cs_only)


def test_list_files_nonexistent_migration_returns_empty() -> None:
    svc = FileSystemService.get_instance()
    files = run(svc.list_files("nonexistent-migration-id"))
    assert files == []


# ── read_file ─────────────────────────────────────────────────────────────

def test_read_file_returns_content() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    run(svc.save_files(MIGRATION_ID, [("Read.cs", b"hello bytes")]))
    path = svc.get_project_path(MIGRATION_ID) / "Read.cs"
    content = run(svc.read_file(path))
    assert content == b"hello bytes"


def test_read_file_missing_raises() -> None:
    svc = FileSystemService.get_instance()
    with pytest.raises(FileSystemError):
        run(svc.read_file(Path("/nonexistent/path/file.cs")))


def test_read_file_text_decodes() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    run(svc.save_files(MIGRATION_ID, [("Text.cs", b"public class Foo {}")]))
    path = svc.get_project_path(MIGRATION_ID) / "Text.cs"
    text = run(svc.read_file_text(path))
    assert "Foo" in text


# ── delete_project ────────────────────────────────────────────────────────

def test_delete_project_removes_dirs() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    assert svc.get_project_path(MIGRATION_ID).exists()
    deleted = run(svc.delete_project(MIGRATION_ID))
    assert deleted is True
    assert not svc.get_project_path(MIGRATION_ID).exists()


def test_delete_project_nonexistent_returns_false() -> None:
    svc = FileSystemService.get_instance()
    result = run(svc.delete_project("nonexistent-00000000-0000-0000-0000-000000000099"))
    assert result is False


# ── project_exists ────────────────────────────────────────────────────────

def test_project_exists_true_after_create() -> None:
    svc = FileSystemService.get_instance()
    run(svc.create_project_dir(MIGRATION_ID))
    assert run(svc.project_exists(MIGRATION_ID)) is True


def test_project_exists_false_before_create() -> None:
    svc = FileSystemService.get_instance()
    assert run(svc.project_exists("never-created-migration")) is False
