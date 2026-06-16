"""
Tests for upload_validator utilities.
"""

import asyncio
import io

import pytest
from fastapi import UploadFile

from app.core.exceptions import ValidationException
from app.utils.upload_validator import (
    ALLOWED_EXTENSIONS,
    get_extension,
    is_allowed,
    is_zip,
    validate_upload_file,
)


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.new_event_loop().run_until_complete(coro)


def make_upload(filename: str, content: bytes) -> UploadFile:
    """Build a minimal UploadFile for testing."""
    return UploadFile(filename=filename, file=io.BytesIO(content))


# ── get_extension ─────────────────────────────────────────────────────────

def test_get_extension_cs() -> None:
    assert get_extension("Program.cs") == ".cs"


def test_get_extension_uppercase_normalised() -> None:
    assert get_extension("App.CS") == ".cs"


def test_get_extension_no_ext() -> None:
    assert get_extension("Makefile") == ""


# ── is_allowed ────────────────────────────────────────────────────────────

def test_is_allowed_cs() -> None:
    assert is_allowed("UserService.cs") is True


def test_is_allowed_csproj() -> None:
    assert is_allowed("MyApp.csproj") is True


def test_is_allowed_zip() -> None:
    assert is_allowed("project.zip") is True


def test_is_allowed_exe_false() -> None:
    assert is_allowed("bad.exe") is False


def test_is_allowed_py_false() -> None:
    assert is_allowed("script.py") is False


def test_all_allowed_extensions_pass() -> None:
    for ext in ALLOWED_EXTENSIONS:
        assert is_allowed(f"file{ext}") is True


# ── is_zip ────────────────────────────────────────────────────────────────

def test_is_zip_true() -> None:
    assert is_zip("archive.zip") is True


def test_is_zip_false_for_cs() -> None:
    assert is_zip("Foo.cs") is False


# ── validate_upload_file ──────────────────────────────────────────────────

def test_validate_valid_file() -> None:
    upload = make_upload("Valid.cs", b"public class Valid {}")
    content = run(validate_upload_file(upload, set()))
    assert content == b"public class Valid {}"


def test_validate_empty_filename_raises() -> None:
    upload = make_upload("", b"data")
    with pytest.raises(ValidationException, match="non-empty filename"):
        run(validate_upload_file(upload, set()))


def test_validate_unsupported_extension_raises() -> None:
    upload = make_upload("bad.py", b"print('hi')")
    with pytest.raises(ValidationException, match="unsupported extension"):
        run(validate_upload_file(upload, set()))


def test_validate_duplicate_filename_raises() -> None:
    upload = make_upload("Dup.cs", b"class Dup {}")
    with pytest.raises(ValidationException, match="Duplicate"):
        run(validate_upload_file(upload, {"Dup.cs"}))


def test_validate_empty_content_raises() -> None:
    upload = make_upload("Empty.cs", b"")
    with pytest.raises(ValidationException, match="empty"):
        run(validate_upload_file(upload, set()))


def test_validate_oversized_file_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch the per-file limit to 1 byte to trigger the size check."""
    from app.core import config as cfg_module

    original = cfg_module.Settings.max_file_size_bytes.fget  # type: ignore[attr-defined]

    monkeypatch.setattr(
        cfg_module.Settings,
        "max_file_size_bytes",
        property(lambda self: 1),
    )
    upload = make_upload("Big.cs", b"too large content")
    with pytest.raises(ValidationException, match="exceeds"):
        run(validate_upload_file(upload, set()))

    # Restore
    monkeypatch.setattr(cfg_module.Settings, "max_file_size_bytes", property(original))


def test_validate_multiple_files_different_names() -> None:
    seen: set[str] = set()
    for name in ["A.cs", "B.cs", "App.csproj"]:
        upload = make_upload(name, b"content")
        run(validate_upload_file(upload, seen))
        seen.add(name)
