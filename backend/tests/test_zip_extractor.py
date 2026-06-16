"""
Tests for the ZIP extraction utility.
"""

import asyncio
import io
import zipfile
from pathlib import Path

import pytest

from app.core.exceptions import ValidationException
from app.utils.zip_extractor import extract_zip


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.new_event_loop().run_until_complete(coro)


def make_zip(files: dict[str, bytes]) -> bytes:
    """Build a ZIP archive in memory from a dict of {name: content}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.fixture
def tmp_target(tmp_path: Path) -> Path:
    target = tmp_path / "extracted"
    target.mkdir()
    return target


# ── Happy path ────────────────────────────────────────────────────────────

def test_extract_cs_file(tmp_target: Path) -> None:
    zipped = make_zip({"Program.cs": b"public class Program {}"})
    extracted = run(extract_zip(zipped, tmp_target))
    assert "Program.cs" in extracted
    assert (tmp_target / "Program.cs").read_bytes() == b"public class Program {}"


def test_extract_multiple_files(tmp_target: Path) -> None:
    zipped = make_zip({
        "A.cs": b"class A {}",
        "B.cs": b"class B {}",
        "App.csproj": b"<Project/>",
    })
    extracted = run(extract_zip(zipped, tmp_target))
    assert len(extracted) == 3


def test_extract_preserves_subdirectory_structure(tmp_target: Path) -> None:
    zipped = make_zip({"src/Services/UserService.cs": b"class UserService {}"})
    extracted = run(extract_zip(zipped, tmp_target))
    assert any("UserService.cs" in e for e in extracted)
    assert (tmp_target / "src" / "Services" / "UserService.cs").exists()


def test_extract_skips_unsupported_extensions(tmp_target: Path) -> None:
    zipped = make_zip({
        "Good.cs": b"class Good {}",
        "Bad.exe": b"\x4d\x5a",
        "Also.dll": b"\x4d\x5a",
    })
    extracted = run(extract_zip(zipped, tmp_target))
    assert all(e.endswith(".cs") for e in extracted)
    assert not (tmp_target / "Bad.exe").exists()


def test_extract_skips_directories_only_extracts_files(tmp_target: Path) -> None:
    """Only files should be extracted, not directory entries."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Add a directory entry the Python 3.10-compatible way (trailing slash)
        dir_info = zipfile.ZipInfo("emptydir/")
        zf.writestr(dir_info, "")
        zf.writestr("Foo.cs", b"class Foo {}")
    extracted = run(extract_zip(buf.getvalue(), tmp_target))
    assert all(not e.endswith("/") for e in extracted)


def test_extract_returns_relative_paths(tmp_target: Path) -> None:
    zipped = make_zip({"src/Foo.cs": b"class Foo {}"})
    extracted = run(extract_zip(zipped, tmp_target))
    for e in extracted:
        assert not Path(e).is_absolute()


def test_extract_creates_target_if_missing(tmp_path: Path) -> None:
    target = tmp_path / "new_dir" / "sub"
    zipped = make_zip({"X.cs": b"class X {}"})
    extracted = run(extract_zip(zipped, target))
    assert len(extracted) == 1


# ── Zip Slip attack prevention ────────────────────────────────────────────

def test_zip_slip_raises_validation_error(tmp_target: Path) -> None:
    """Archive containing path-traversal entries must be rejected."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../../../etc/passwd", b"root:x:0:0")
    with pytest.raises(ValidationException, match="Zip Slip"):
        run(extract_zip(buf.getvalue(), tmp_target))


# ── Invalid archive ───────────────────────────────────────────────────────

def test_invalid_zip_raises_validation_error(tmp_target: Path) -> None:
    with pytest.raises(ValidationException):
        run(extract_zip(b"this is not a zip file", tmp_target))


def test_empty_zip_returns_empty_list(tmp_target: Path) -> None:
    zipped = make_zip({})
    extracted = run(extract_zip(zipped, tmp_target))
    assert extracted == []
