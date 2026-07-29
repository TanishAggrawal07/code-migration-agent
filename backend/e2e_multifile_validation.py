"""
E2E Production Validation — Multi-File .NET → Java Migration
============================================================
Tests the complete migration pipeline against a realistic 7-file
SchoolManagement C# project and produces a detailed pass/fail report.

Usage:
    python e2e_multifile_validation.py

Requirements:
    - Backend running on http://localhost:8000
    OR
    - Run inline using the agent directly (no HTTP server required)
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# ── Project root to Python path ───────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("ENVIRONMENT", "test")

BACKEND_ROOT = Path(__file__).parent
PROJECT_DIR  = BACKEND_ROOT / "e2e_test_project"

# ── Source files in the test project ──────────────────────────────────────
SOURCE_FILES = [
    "Models/Student.cs",
    "Models/Teacher.cs",
    "Models/Course.cs",
    "Interfaces/IStudentRepository.cs",
    "Repositories/StudentRepository.cs",
    "Services/StudentService.cs",
    "Utilities/ValidationHelper.cs",
    "Program.cs",
]

# ── Expected Java output files (parallel to source) ───────────────────────
EXPECTED_JAVA = [f.replace(".cs", ".java") for f in SOURCE_FILES]

# ── Per-file structural expectations ──────────────────────────────────────
# Maps source filename → dict of expected members
EXPECTATIONS: dict[str, dict[str, list[str]]] = {
    "Models/Student.cs": {
        "classes":      ["Student"],
        "methods":      ["getFullName", "getAge", "isHonorRoll", "enrollInCourse", "toString"],
        "constructors": ["Student"],
        "properties":   ["id", "firstName", "lastName", "email", "dateOfBirth", "gpa", "enrolledCourses"],
        "no_placeholders": True,
    },
    "Models/Teacher.cs": {
        "classes":      ["Teacher"],
        "methods":      ["getFullName", "assignCourse", "getAnnualSalary", "getActiveCourses", "toString"],
        "constructors": ["Teacher"],
        "properties":   ["id", "firstName", "lastName", "email", "department", "salary", "teachingCourses"],
        "no_placeholders": True,
    },
    "Models/Course.cs": {
        "classes":      ["Course"],
        "methods":      ["getEnrollmentCount", "getAverageGPA", "getHonorStudents", "deactivateCourse", "toString"],
        "constructors": ["Course"],
        "properties":   ["courseId", "courseName", "description", "credits", "isActive"],
        "no_placeholders": True,
    },
    "Interfaces/IStudentRepository.cs": {
        "interfaces":   ["IStudentRepository"],
        "methods":      ["getById", "getAll", "getByGPARange", "getHonorStudents",
                         "add", "update", "delete", "exists", "count"],
        "no_placeholders": True,
    },
    "Repositories/StudentRepository.cs": {
        "classes":      ["StudentRepository"],
        "methods":      ["getById", "getAll", "getByGPARange", "getHonorStudents",
                         "add", "update", "delete", "exists", "count"],
        "constructors": ["StudentRepository"],
        "no_placeholders": True,
    },
    "Services/StudentService.cs": {
        "classes":      ["StudentService"],
        "methods":      ["getStudent", "getAllStudents", "getHonorRollStudents",
                         "getStudentsByGPARange", "registerStudent", "updateStudentGPA",
                         "removeStudent", "enrollStudentInCourse", "getTotalStudentCount",
                         "getEnrollmentSummary"],
        "constructors": ["StudentService"],
        "no_placeholders": True,
    },
    "Utilities/ValidationHelper.cs": {
        "classes":      ["ValidationHelper"],
        "methods":      ["validateStudent", "isValidEmail", "isValidGPA", "formatGPA", "isAdult"],
        "no_placeholders": True,
    },
    "Program.cs": {
        "classes":      ["Program"],
        "methods":      ["main"],
        "no_placeholders": True,
    },
}

PLACEHOLDER_PATTERNS = [
    r"//\s*other methods",
    r"//\s*remaining",
    r"//\s*TODO",
    r"//\s*implement later",
    r"//\s*\.\.\.rest",
    r"//\s*rest of",
    r"//\s*more methods",
    r"//\s*other code",
    r"//\s*implement",
    r"//\s*add your",
]

BANNER = "=" * 70


def _banner(title: str) -> None:
    print(f"\n{BANNER}")
    print(f"  {title}")
    print(BANNER)


def _ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def _fail(msg: str) -> None:
    print(f"  ❌ {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def _info(msg: str) -> None:
    print(f"  ℹ️  {msg}")


# ── Java source analysis helpers ───────────────────────────────────────────

def extract_java_classes(java: str) -> list[str]:
    return re.findall(r"\b(?:class|interface|enum)\s+(\w+)", java)


def extract_java_methods(java: str) -> list[str]:
    return re.findall(
        r"(?:public|private|protected|static|default|abstract)?\s*[\w<>\[\]]+\s+(\w+)\s*\(", java
    )


def has_placeholder(java: str) -> list[str]:
    found = []
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, java, re.IGNORECASE):
            found.append(pat)
    return found


def check_no_todo(java: str) -> bool:
    return not bool(re.search(r"\bTODO\b", java, re.IGNORECASE))


# ── Agent-level migration (no HTTP server required) ───────────────────────

async def run_migration_via_agent() -> dict[str, Any]:
    """
    Run the full migration pipeline directly through the agent layer.
    Bypasses HTTP and exercises Parser → Analyzer → Embedding → RAG →
    Migration → Structural check → Semantic check.
    """
    from app.core.startup import initialize_services
    from app.core.gemini_client import GeminiClient
    from app.parser.parser_service import ParserService
    from app.analyzer.analyzer_service import AnalyzerService
    from app.vectorstore.indexing_service import IndexingService
    from app.rag.retrieval_service import RetrievalService
    from app.agents.base_agent import MigrationAgent

    migration_id = f"e2e_val_{int(time.time())}"

    # ── STEP 0: initialize all AI services (GeminiClient, embeddings, ChromaDB) ──
    _banner("STEP 0 — Service Initialization")
    status = await initialize_services()
    _ok(f"GeminiClient initialized : {status.gemini}")
    _ok(f"EmbeddingService         : {status.embeddings}")
    _ok(f"ChromaDB                 : {status.chromadb}")
    _ok(f"TreeSitter               : {status.tree_sitter}")

    gemini = GeminiClient.get_instance()
    if not gemini.is_initialized:
        _fail(
            "No LLM provider available — Ollama is not running or has no models.\n"
            "  Start Ollama ('ollama serve') and ensure at least one model is loaded.\n"
            "  Run: ollama list"
        )
        return {"success": False, "generated_files": [], "migration_id": migration_id}

    _ok(f"Active provider: {gemini.active_provider_key} / {gemini.active_model}")


    # ── Collect file paths ────────────────────────────────────────────────
    abs_paths = []
    for rel in SOURCE_FILES:
        p = PROJECT_DIR / rel
        if p.exists():
            abs_paths.append(str(p))
        else:
            _fail(f"Source file missing: {p}")

    _banner("STEP 2 — Parser")
    svc = ParserService.get_instance()
    parse_result = await svc.parse_migration(
        migration_id=migration_id,
        uploaded_files=abs_paths,
        project_root=str(PROJECT_DIR),
    )
    _ok(f"Parsed {parse_result.total_files} file(s), {parse_result.total_chunks} chunk(s) [{parse_result.parser_mode} mode]")
    if parse_result.errors:
        for e in parse_result.errors:
            _warn(f"Parser error: {e}")

    _banner("STEP 3 — Analyzer")
    chunks      = parse_result.chunks
    parsed_files = parse_result.parsed_files
    analyzer = AnalyzerService.get_instance()
    analysis = await analyzer.analyze_chunks(chunks=chunks, parsed_files=parsed_files)
    _ok(f"Classes: {analysis.get('classes', [])}")
    _ok(f"Methods: {len(analysis.get('methods', []))} detected")
    _ok(f"Interfaces: {analysis.get('interfaces', [])}")
    _ok(f"Namespace: {analysis.get('namespace', '(none)')}")

    _banner("STEP 4 — Embeddings")
    indexer = IndexingService.get_instance()
    idx_result = await indexer.index_chunks(migration_id=migration_id, chunks=chunks, analysis=analysis)
    _ok(f"Indexed {idx_result.indexed} chunk(s) [mode={idx_result.mode}]")

    _banner("STEP 5 — RAG Retrieval")
    retriever = RetrievalService.get_instance()
    ctx_texts = await retriever.retrieve_for_chunks(migration_id=migration_id, chunks=chunks, top_k=5)
    _ok(f"Retrieved {len(ctx_texts)} context item(s)")

    _banner("STEP 6 — Migration Agent (with structural + semantic verification)")
    agent = MigrationAgent()
    result = await agent.safe_run({
        "chunks":            chunks,
        "retrieved_context": ctx_texts,
        "migration_id":      migration_id,
        "analysis":          analysis,
    })

    if result.status.value == "failed":
        _fail(f"Migration agent failed: {result.error}")
        return {"success": False, "generated_files": [], "migration_id": migration_id}

    generated_files: list[dict] = result.data.get("generated_files", [])
    _ok(f"Generated {len(generated_files)} Java file(s)")

    return {
        "success":         True,
        "generated_files": generated_files,
        "migration_id":    migration_id,
        "chunks":          chunks,
        "analysis":        analysis,
        "provider":        gemini.active_provider_key if gemini.is_initialized else "stub",
        "model":           gemini.active_model if gemini.is_initialized else "stub",
    }


# ── Per-file validation ───────────────────────────────────────────────────

def validate_file(
    source_rel: str,
    java_content: str,
    expectations: dict,
) -> dict[str, Any]:
    """Run all checklist items against one generated Java file."""
    issues: list[str] = []
    warnings: list[str] = []
    passes: list[str] = []

    java_lower = java_content.lower()

    # 1. Non-empty
    if not java_content.strip():
        issues.append("File is empty")
        return {"source": source_rel, "issues": issues, "warnings": warnings, "passes": passes}

    # 2. Classes / interfaces present
    found_types = set(c.lower() for c in extract_java_classes(java_content))
    for cls in expectations.get("classes", []):
        if cls.lower() in found_types:
            passes.append(f"class {cls} present")
        else:
            issues.append(f"MISSING class: {cls}")
    for iface in expectations.get("interfaces", []):
        if iface.lower() in found_types or iface.lower().replace("i", "", 1) in java_lower:
            passes.append(f"interface {iface} present")
        else:
            issues.append(f"MISSING interface: {iface}")

    # 3. Methods present (case-insensitive Java camelCase check)
    found_methods = set(m.lower() for m in extract_java_methods(java_content))
    for method in expectations.get("methods", []):
        if method.lower() in found_methods:
            passes.append(f"method {method}() present")
        else:
            issues.append(f"MISSING method: {method}()")

    # 4. Constructors present (class name appears in a constructor pattern)
    for ctor in expectations.get("constructors", []):
        # Java constructor: public ClassName(
        if re.search(rf"public\s+{re.escape(ctor)}\s*\(", java_content, re.IGNORECASE):
            passes.append(f"constructor {ctor}() present")
        else:
            issues.append(f"MISSING constructor: {ctor}()")

    # 5. Properties / fields present (look for field or getter)
    for prop in expectations.get("properties", []):
        prop_lower = prop.lower()
        has_field  = bool(re.search(rf"\b{re.escape(prop_lower)}\b", java_lower))
        has_getter = bool(re.search(rf"get{re.escape(prop_lower)}\s*\(", java_lower))
        if has_field or has_getter:
            passes.append(f"property/field {prop} present")
        else:
            warnings.append(f"property {prop} may be missing (no field or getter found)")

    # 6. No placeholder comments
    if expectations.get("no_placeholders"):
        placeholders = has_placeholder(java_content)
        if placeholders:
            issues.append(f"PLACEHOLDER comments found: {placeholders}")
        else:
            passes.append("No placeholder comments")

    # 7. No bare TODO blocks
    if not check_no_todo(java_content):
        issues.append("TODO block found")
    else:
        passes.append("No TODO blocks")

    # 8. Has package declaration
    if re.search(r"^\s*package\s+[\w.]+\s*;", java_content, re.MULTILINE):
        passes.append("Package declaration present")
    else:
        warnings.append("No package declaration found")

    # 9. Has at least one import (most files need some)
    if re.search(r"^\s*import\s+", java_content, re.MULTILINE):
        passes.append("Import statements present")
    else:
        warnings.append("No import statements found")

    return {"source": source_rel, "issues": issues, "warnings": warnings, "passes": passes}


# ── Main validation runner ────────────────────────────────────────────────

async def main() -> None:
    print(f"\n{'=' * 70}")
    print("  .NET → Java End-to-End Production Validation")
    print("  SchoolManagement — 8-file multi-class project")
    print(f"{'=' * 70}")

    t0 = time.time()
    result = await run_migration_via_agent()

    if not result["success"]:
        _banner("RESULT: FAILED — Migration did not complete")
        return

    generated: list[dict] = result["generated_files"]
    gen_by_filename = {gf["filename"]: gf for gf in generated}

    _banner("STEP 7 — Per-File Structural Validation")

    all_issues:   list[str] = []
    all_warnings: list[str] = []
    total_passes  = 0
    files_ok      = 0
    files_with_issues = 0

    validation_results: list[dict] = []

    for source_rel in SOURCE_FILES:
        java_rel     = source_rel.replace(".cs", ".java")
        java_basename = Path(java_rel).name
        exp          = EXPECTATIONS.get(source_rel, {})

        # Find the generated file (match by basename or full relative path)
        gf = gen_by_filename.get(java_basename) or gen_by_filename.get(java_rel)
        if gf is None:
            # Try partial match
            for k, v in gen_by_filename.items():
                if Path(k).name == java_basename:
                    gf = v
                    break

        if gf is None:
            vr = {
                "source":   source_rel,
                "issues":   [f"Java file '{java_basename}' was NOT generated"],
                "warnings": [],
                "passes":   [],
            }
        else:
            content = gf.get("full_content") or gf.get("content_preview", "")
            vr = validate_file(source_rel, content, exp)

        validation_results.append(vr)

        print(f"\n  ── {source_rel} → {java_basename}")
        for p in vr["passes"]:
            _ok(p)
        for w in vr["warnings"]:
            _warn(w)
        for iss in vr["issues"]:
            _fail(iss)

        if vr["issues"]:
            files_with_issues += 1
            all_issues.extend([f"[{source_rel}] {i}" for i in vr["issues"]])
        else:
            files_ok += 1
        all_warnings.extend([f"[{source_rel}] {w}" for w in vr["warnings"]])
        total_passes += len(vr["passes"])

    elapsed = time.time() - t0

    # ── Final report ──────────────────────────────────────────────────────
    _banner("FINAL PRODUCTION VALIDATION REPORT")

    print(f"\n  Project       : SchoolManagement (.NET → Java)")
    print(f"  C# files      : {len(SOURCE_FILES)}")
    print(f"  Java generated: {len(generated)}")
    print(f"  Provider used : {result.get('provider', 'stub')} / {result.get('model', 'stub')}")
    print(f"  Duration      : {elapsed:.1f}s")
    print()
    print(f"  Files fully passing : {files_ok} / {len(SOURCE_FILES)}")
    print(f"  Files with issues   : {files_with_issues}")
    print(f"  Total checks passed : {total_passes}")
    print(f"  Total issues        : {len(all_issues)}")
    print(f"  Total warnings      : {len(all_warnings)}")

    if all_issues:
        print(f"\n  ── Issues to fix ──")
        for iss in all_issues:
            print(f"    ❌ {iss}")
    else:
        print(f"\n  ── No structural issues found ✅")

    if all_warnings:
        print(f"\n  ── Warnings (non-blocking) ──")
        for w in all_warnings:
            print(f"    ⚠️  {w}")

    # Per-file Java content dump for manual inspection
    _banner("GENERATED JAVA — Content Previews")
    for gf in generated:
        fname = gf.get("filename", "?")
        content = gf.get("full_content") or gf.get("content_preview", "")
        print(f"\n{'─' * 60}")
        print(f"  FILE: {fname}  ({len(content)} chars)")
        print(f"{'─' * 60}")
        # Print first 50 lines
        lines = content.splitlines()
        for i, line in enumerate(lines[:50]):
            print(f"  {line}")
        if len(lines) > 50:
            print(f"  ... ({len(lines) - 50} more lines)")

    # ── Final verdict ─────────────────────────────────────────────────────
    _banner("VERDICT")
    if files_with_issues == 0:
        print("\n  ✅✅ ALL CHECKS PASSED — Migration is production-ready.")
    elif files_with_issues <= 2:
        print(f"\n  ⚠️  MOSTLY PASSING — {files_with_issues} file(s) have issues that need fixing.")
    else:
        print(f"\n  ❌ {files_with_issues} files have issues — see above for details.")

    print()


if __name__ == "__main__":
    asyncio.run(main())
