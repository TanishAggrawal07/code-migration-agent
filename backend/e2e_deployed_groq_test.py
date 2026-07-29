"""
End-to-End (E2E) Test Suite for Deployed Code Migration Agent with Groq LLM

Target Server:
- Deployed Host: http://3.109.164.178:8000 (Backend API)
- Deployed Web:  http://3.109.164.178 (Frontend Port 80 / 3000)
- Model: Groq llama-3.3-70b-versatile
"""

import sys
import time
import requests
import json

BASE_URL = "http://3.109.164.178:8000"
FRONTEND_URL = "http://3.109.164.178"

def log(step: str, msg: str):
    print(f"[{step}] {msg}")

def run_e2e_tests():
    print("=================================================================")
    print("      E2E TEST SUITE — DEPLOYED CODE MIGRATION AGENT (GROQ)      ")
    print("=================================================================")
    print(f"Target Backend API : {BASE_URL}")
    print(f"Target Frontend UI  : {FRONTEND_URL}")
    print("=================================================================\n")

    # ── Test 1: Health Check ──────────────────────────────────────────────────
    log("TEST 1", "Verifying Backend /health endpoint...")
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data.get("status") == "healthy", f"Expected status healthy, got {data}"
    log("TEST 1", f"PASSED — Backend healthy: {data}\n")

    # ── Test 2: Web Interface Access ──────────────────────────────────────────
    log("TEST 2", "Verifying Frontend web interface on port 80...")
    r = requests.get(FRONTEND_URL, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "AI Code Migration Agent" in r.text or "<!DOCTYPE html>" in r.text
    log("TEST 2", f"PASSED — Web interface accessible (HTTP 200, {len(r.text)} bytes)\n")

    # ── Test 3: Active AI Provider Status (Groq) ─────────────────────────────
    log("TEST 3", "Verifying Active AI Provider via GET /api/ai/provider...")
    r = requests.get(f"{BASE_URL}/api/ai/provider", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    provider_data = r.json()
    log("TEST 3", f"Active Provider Details: {json.dumps(provider_data, indent=2)}")
    assert provider_data.get("active_provider") == "groq", f"Expected groq, got {provider_data}"
    assert "llama-3.3-70b" in provider_data.get("active_model", ""), f"Expected llama-3.3-70b model, got {provider_data}"
    log("TEST 3", f"PASSED — Active Provider is GROQ with Model: {provider_data.get('active_model')}\n")

    # ── Test 4: Create Migration Job ──────────────────────────────────────────
    log("TEST 4", "Creating new migration job via POST /api/migrations...")
    payload = {
        "project_name": "E2E Groq Calculator Migration",
        "source_framework": ".NET Core C#",
        "target_framework": "Spring Boot 3 Java"
    }
    r = requests.post(f"{BASE_URL}/api/migrations", json=payload, timeout=10)
    assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}: {r.text}"
    mig_data = r.json()
    migration_id = mig_data["migration_id"]
    log("TEST 4", f"PASSED — Migration created with ID: {migration_id}\n")

    # ── Test 5: File Upload ───────────────────────────────────────────────────
    log("TEST 5", f"Uploading sample C# code to migration {migration_id}...")
    sample_csharp_code = """using System;

namespace CalculatorApp
{
    public class CalculatorService
    {
        public int Add(int a, int b)
        {
            return a + b;
        }

        public int Multiply(int a, int b)
        {
            return a * b;
        }
    }
}
"""
    files = [
        ("files", ("CalculatorService.cs", sample_csharp_code, "text/plain"))
    ]
    r = requests.post(f"{BASE_URL}/api/migrations/{migration_id}/upload", files=files, timeout=15)
    assert r.status_code in (200, 201), f"Upload failed with {r.status_code}: {r.text}"
    upload_res = r.json()
    log("TEST 5", f"PASSED — Uploaded files: {upload_res.get('file_count', 1)} file(s)\n")

    # ── Test 6: Trigger Migration Workflow ────────────────────────────────────
    log("TEST 6", f"Triggering AI Migration Workflow with Groq for ID: {migration_id}...")
    r = requests.post(f"{BASE_URL}/api/migrations/{migration_id}/run", timeout=15)
    assert r.status_code in (200, 202), f"Run failed with {r.status_code}: {r.text}"
    run_res = r.json()
    log("TEST 6", f"Workflow execution started: {run_res.get('message')}\n")

    # ── Test 7: Poll Workflow Completion & Check Output ──────────────────────
    log("TEST 7", "Polling workflow execution status until completion...")
    completed = False
    for attempt in range(1, 30):
        time.sleep(3)
        r = requests.get(f"{BASE_URL}/api/migrations/{migration_id}", timeout=10)
        assert r.status_code == 200, f"Get status failed: {r.status_code}"
        state = r.json()
        current_stage = state.get("current_stage")
        completed_stages = state.get("completed_stages", [])
        log("POLL", f"Attempt {attempt}/30 — Stage: {current_stage} | Completed Stages: {completed_stages}")

        if current_stage in ("completed", "saved", "migrated", "failed"):
            completed = True
            log("TEST 7", f"Workflow reached stage: {current_stage}")
            assert current_stage != "failed", f"Workflow failed: {state.get('context')}"
            
            # Verify generated Java contents from context
            ctx = state.get("context", {})
            generated_contents = ctx.get("generated_file_contents", {})
            assert generated_contents, "No generated Java files found in context"
            for fname, content in generated_contents.items():
                log("TEST 7", f"Generated Java File: {fname} ({len(content)} bytes)")
                print(f"\n--- {fname} ---\n{content}\n---")
            break

    assert completed, "Workflow execution timed out after 90 seconds"
    log("TEST 7", "PASSED — Workflow execution completed successfully with Groq LLM!\n")

    # ── Test 8: Download Generated Migration Artifact ─────────────────────────
    log("TEST 8", f"Testing file download for migration {migration_id}...")
    r = requests.get(f"{BASE_URL}/api/migrations/{migration_id}/download", timeout=10)
    assert r.status_code == 200, f"Download failed with {r.status_code}"
    assert len(r.content) > 0, "Downloaded ZIP artifact is empty"
    log("TEST 8", f"PASSED — Successfully downloaded ZIP artifact ({len(r.content)} bytes)\n")

    print("=================================================================")
    print(" [SUCCESS] ALL 8 END-TO-END TESTS PASSED AGAINST DEPLOYED EC2!  ")
    print("=================================================================")

if __name__ == "__main__":
    try:
        run_e2e_tests()
    except AssertionError as ae:
        print(f"\n [FAIL] E2E TEST FAILED: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n [FAIL] UNEXPECTED ERROR: {e}")
        sys.exit(1)
