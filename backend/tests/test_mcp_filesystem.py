"""
Tests for MCPFilesystem tool layer.
"""

import asyncio

import pytest

from app.mcp.filesystem_mcp import MCPFilesystem
from app.services.filesystem_service import FileSystemError, FileSystemService


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.new_event_loop().run_until_complete(coro)


MID = "test-mcp-00000000-0000-0000-0000-000000000002"


@pytest.fixture(autouse=True)
def setup_and_teardown() -> None:  # type: ignore[return]
    fs = FileSystemService.get_instance()
    run(fs.delete_project(MID))
    run(fs.create_project_dir(MID))
    yield
    run(fs.delete_project(MID))


@pytest.fixture
def mcp() -> MCPFilesystem:
    return MCPFilesystem(MID)


# ── write_file / read_file ────────────────────────────────────────────────

def test_write_and_read_file(mcp: MCPFilesystem) -> None:
    run(mcp.write_file("Hello.cs", "public class Hello {}"))
    content = run(mcp.read_file("Hello.cs"))
    assert "Hello" in content


def test_write_creates_parent_dirs(mcp: MCPFilesystem) -> None:
    run(mcp.write_file("src/Services/UserService.cs", "class UserService {}"))
    assert run(mcp.file_exists("src/Services/UserService.cs")) is True


def test_read_nonexistent_file_raises(mcp: MCPFilesystem) -> None:
    with pytest.raises(FileSystemError):
        run(mcp.read_file("DoesNotExist.cs"))


# ── list_directory ────────────────────────────────────────────────────────

def test_list_directory_empty(mcp: MCPFilesystem) -> None:
    files = run(mcp.list_directory("."))
    assert files == []


def test_list_directory_after_write(mcp: MCPFilesystem) -> None:
    run(mcp.write_file("A.cs", "class A {}"))
    run(mcp.write_file("B.cs", "class B {}"))
    files = run(mcp.list_directory("."))
    assert len(files) == 2
    names = [f.split("/")[-1] for f in files]
    assert "A.cs" in names
    assert "B.cs" in names


def test_list_directory_with_extension_filter(mcp: MCPFilesystem) -> None:
    run(mcp.write_file("X.cs", "class X {}"))
    run(mcp.write_file("Y.xml", "<root/>"))
    cs_files = run(mcp.list_directory(".", extensions={".cs"}))
    assert all(f.endswith(".cs") for f in cs_files)


def test_list_nonexistent_subdir_returns_empty(mcp: MCPFilesystem) -> None:
    files = run(mcp.list_directory("nonexistent"))
    assert files == []


# ── create_directory / delete_directory ──────────────────────────────────

def test_create_directory(mcp: MCPFilesystem) -> None:
    result = run(mcp.create_directory("newsubdir"))
    assert result is True
    fs = FileSystemService.get_instance()
    assert (fs.get_project_path(MID) / "newsubdir").exists()


def test_delete_directory(mcp: MCPFilesystem) -> None:
    run(mcp.create_directory("todelete"))
    result = run(mcp.delete_directory("todelete"))
    assert result is True
    fs = FileSystemService.get_instance()
    assert not (fs.get_project_path(MID) / "todelete").exists()


def test_delete_nonexistent_directory_returns_false(mcp: MCPFilesystem) -> None:
    result = run(mcp.delete_directory("ghost"))
    assert result is False


# ── file_exists ───────────────────────────────────────────────────────────

def test_file_exists_true_after_write(mcp: MCPFilesystem) -> None:
    run(mcp.write_file("Exists.cs", "class Exists {}"))
    assert run(mcp.file_exists("Exists.cs")) is True


def test_file_exists_false_for_missing(mcp: MCPFilesystem) -> None:
    assert run(mcp.file_exists("Missing.cs")) is False


# ── get_file_info ─────────────────────────────────────────────────────────

def test_get_file_info(mcp: MCPFilesystem) -> None:
    run(mcp.write_file("Info.cs", "class Info {}"))
    info = run(mcp.get_file_info("Info.cs"))
    assert info.name == "Info.cs"
    assert info.extension == ".cs"
    assert info.size_bytes > 0
    assert info.is_directory is False


def test_get_file_info_missing_raises(mcp: MCPFilesystem) -> None:
    with pytest.raises(FileSystemError):
        run(mcp.get_file_info("NoFile.cs"))


# ── Path traversal guard ──────────────────────────────────────────────────

def test_path_traversal_read_raises(mcp: MCPFilesystem) -> None:
    with pytest.raises(FileSystemError, match="traversal"):
        run(mcp.read_file("../../etc/passwd"))


def test_path_traversal_write_raises(mcp: MCPFilesystem) -> None:
    with pytest.raises(FileSystemError, match="traversal"):
        run(mcp.write_file("../../../evil.sh", "rm -rf /"))


def test_path_traversal_list_raises(mcp: MCPFilesystem) -> None:
    with pytest.raises(FileSystemError, match="traversal"):
        run(mcp.list_directory("../../"))
