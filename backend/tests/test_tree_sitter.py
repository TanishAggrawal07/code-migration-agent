"""
Tests for TreeSitterService — covers both real and stub parser paths.
"""

import asyncio
import pytest

from app.parser.tree_sitter_service import (
    TreeSitterService,
    TreeSitterServiceError,
    ClassInfo,
    MethodInfo,
)

SAMPLE_CSHARP = """
using System;
using System.Collections.Generic;

namespace MyApp
{
    public class UserService
    {
        private readonly IUserRepository _repo;

        public UserService(IUserRepository repo)
        {
            _repo = repo;
        }

        public async Task<User> GetUserById(int id)
        {
            return await _repo.FindAsync(id);
        }

        private void ValidateUser(User user)
        {
            if (user == null) throw new ArgumentNullException(nameof(user));
        }
    }

    public static class StringExtensions
    {
        public static string ToSnakeCase(this string value)
        {
            return value.ToLower().Replace(" ", "_");
        }
    }
}
"""


def run(coro):  # type: ignore[no-untyped-def]
    """Run a coroutine in a fresh event loop."""
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def reset_service() -> None:  # type: ignore[return]
    """Reset service state before each test for isolation."""
    svc = TreeSitterService.get_instance()
    svc._initialized = False
    svc._using_stub = False
    svc._parser = None
    svc._language = None
    yield
    svc._initialized = False
    svc._using_stub = False


def test_tree_sitter_service_singleton() -> None:
    """TreeSitterService must be a singleton."""
    a = TreeSitterService.get_instance()
    b = TreeSitterService.get_instance()
    assert a is b


def test_initialize_returns_true() -> None:
    """initialize() must always return True (real or stub)."""
    svc = TreeSitterService.get_instance()
    result = run(svc.initialize())
    assert result is True


def test_is_initialized_after_initialize() -> None:
    """is_initialized must be True after calling initialize()."""
    svc = TreeSitterService.get_instance()
    run(svc.initialize())
    assert svc.is_initialized is True


def test_parse_raises_when_not_initialized() -> None:
    """parse_code must raise TreeSitterServiceError when not initialized."""
    svc = TreeSitterService.get_instance()
    svc._initialized = False

    with pytest.raises(TreeSitterServiceError):
        run(svc.parse_code("public class Foo {}"))


def test_parse_code_returns_dict() -> None:
    """parse_code must return a dict with expected keys."""
    svc = TreeSitterService.get_instance()
    run(svc.initialize())
    result = run(svc.parse_code(SAMPLE_CSHARP))
    assert isinstance(result, dict)
    assert "root_type" in result
    assert "source_lines" in result
    assert "using_stub" in result
    assert result["source_lines"] > 0


def test_extract_classes_returns_list_of_classinfo() -> None:
    """extract_classes must return a list of ClassInfo objects."""
    svc = TreeSitterService.get_instance()
    run(svc.initialize())
    classes = run(svc.extract_classes(SAMPLE_CSHARP))
    assert isinstance(classes, list)
    for cls in classes:
        assert isinstance(cls, ClassInfo)


def test_extract_classes_finds_both_classes() -> None:
    """Stub or real parser must find UserService and StringExtensions."""
    svc = TreeSitterService.get_instance()
    run(svc.initialize())
    classes = run(svc.extract_classes(SAMPLE_CSHARP))
    names = [c.name for c in classes]
    assert len(classes) >= 2
    assert "UserService" in names
    assert "StringExtensions" in names


def test_extract_methods_returns_list_of_methodinfo() -> None:
    """extract_methods must return a list of MethodInfo objects."""
    svc = TreeSitterService.get_instance()
    run(svc.initialize())
    methods = run(svc.extract_methods(SAMPLE_CSHARP))
    assert isinstance(methods, list)
    for method in methods:
        assert isinstance(method, MethodInfo)


def test_extract_methods_finds_known_methods() -> None:
    """Stub or real parser must find at least one known method."""
    svc = TreeSitterService.get_instance()
    run(svc.initialize())
    methods = run(svc.extract_methods(SAMPLE_CSHARP))
    assert len(methods) >= 1
    names = [m.name for m in methods]
    assert any(n in names for n in ("GetUserById", "ValidateUser", "ToSnakeCase"))


def test_stub_parse_always_works() -> None:
    """Stub parse must handle any string input without raising."""
    result = TreeSitterService._stub_parse(SAMPLE_CSHARP)
    assert result["using_stub"] is True
    assert result["source_lines"] > 0
    assert result["root_type"] == "compilation_unit"


def test_stub_extract_classes_finds_both() -> None:
    """Stub class extractor must find both classes in the sample."""
    classes = TreeSitterService._stub_extract_classes(SAMPLE_CSHARP)
    assert len(classes) >= 2
    names = [c.name for c in classes]
    assert "UserService" in names
    assert "StringExtensions" in names


def test_stub_extract_methods_finds_methods() -> None:
    """Stub method extractor must find methods in the sample."""
    methods = TreeSitterService._stub_extract_methods(SAMPLE_CSHARP)
    assert len(methods) >= 1
    names = [m.name for m in methods]
    assert any(n in names for n in ("GetUserById", "ValidateUser", "ToSnakeCase"))


def test_is_available_returns_bool() -> None:
    """is_available must return a bool."""
    svc = TreeSitterService.get_instance()
    assert isinstance(svc.is_available, bool)
