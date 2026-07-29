"""
End-to-end migration verification — uses the live backend API.
Tests: upload → run → wait for completion → verify output files.
"""
import asyncio
import httpx
import time

BASE = "http://127.0.0.1:8000"

CS_SOURCE = b"""
using System;
using System.Collections.Generic;

namespace Calculator
{
    public class CalculatorService
    {
        private List<double> _history = new List<double>();

        public double Add(double a, double b)
        {
            double result = a + b;
            _history.Add(result);
            return result;
        }

        public double Subtract(double a, double b)
        {
            double result = a - b;
            _history.Add(result);
            return result;
        }

        public double Multiply(double a, double b)
        {
            double result = a * b;
            _history.Add(result);
            return result;
        }

        public List<double> GetHistory()
        {
            return _history;
        }
    }
}
"""

async def run():
    print("\n" + "="*65)
    print("  E2E Migration Test via Live Backend API")
    print("="*65)

    async with httpx.AsyncClient(timeout=60.0) as client:

        # 1. Check provider
        print("\n[1] PROVIDER CHECK")
        r = await client.get(f"{BASE}/api/ai/provider")
        pinfo = r.json()
        print(f"  configured_provider : {pinfo['configured_provider']}")
        print(f"  active_provider     : {pinfo['active_provider']}")
        print(f"  active_model        : {pinfo['active_model']}")
        print(f"  initialized         : {pinfo['initialized']}")
        assert pinfo["active_provider"] == "ollama", f"Expected ollama, got: {pinfo['active_provider']}"
        print("  OK provider=ollama verified")

        # 2. Create migration
        print("\n[2] CREATE MIGRATION")
        r = await client.post(f"{BASE}/api/migrations", json={"project_name": "e2e-api-test"})
        assert r.status_code == 201, f"Create failed: {r.status_code} {r.text}"
        mid = r.json()["migration_id"]
        print(f"  migration_id : {mid}")

        # 3. Upload C# file
        print("\n[3] UPLOAD C# FILE")
        files = [("files", ("CalculatorService.cs", CS_SOURCE, "text/plain"))]
        r = await client.post(f"{BASE}/api/migrations/{mid}/upload", files=files)
        assert r.status_code == 200, f"Upload failed: {r.status_code} {r.text}"
        upload_data = r.json()
        print(f"  uploaded_count : {upload_data['uploaded_count']}")
        print(f"  uploaded_files : {upload_data['uploaded_files']}")
        assert upload_data["uploaded_count"] == 1

        # 4. Run migration
        print("\n[4] RUN MIGRATION WORKFLOW")
        r = await client.post(f"{BASE}/api/migrations/{mid}/run", timeout=600.0)
        assert r.status_code == 200, f"Run failed: {r.status_code} {r.text}"
        run_data = r.json()
        print(f"  stage          : {run_data.get('stage')}")
        print(f"  is_complete    : {run_data.get('is_complete')}")
        print(f"  is_failed      : {run_data.get('is_failed')}")

        # 5. Get final migration state
        print("\n[5] FINAL MIGRATION STATE")
        r = await client.get(f"{BASE}/api/migrations/{mid}")
        assert r.status_code == 200
        mig = r.json()
        print(f"  current_stage        : {mig['current_stage']}")
        print(f"  generated_java_files : {len(mig['generated_java_files'])}")
        for gf in mig["generated_java_files"]:
            print(f"    - {gf['filename']}  compile_success={gf['compile_success']}")
        print(f"  compile_errors       : {len(mig.get('compile_errors', []))}")

        # 6. Check logs for provider info
        print("\n[6] PIPELINE LOGS (last 15)")
        logs = mig.get("logs", [])
        for log in logs[-15:]:
            print(f"  [{log.get('level','?')}] {log.get('message','')}")

    # 7. Check output folder on disk
    print("\n[7] OUTPUT FOLDER ON DISK")
    import os
    from pathlib import Path
    output_dir = Path(f"storage/generated/{mid}")
    if output_dir.exists():
        files_on_disk = list(output_dir.rglob("*"))
        print(f"  output_path  : {output_dir.resolve()}")
        print(f"  files on disk ({len(files_on_disk)}):")
        for f in files_on_disk:
            if f.is_file():
                size = f.stat().st_size
                print(f"    - {f.name}  ({size} bytes)")
    else:
        print(f"  WARNING: output folder does not exist: {output_dir}")

    # 8. Final report
    print("\n[8] FINAL REPORT")
    print("="*65)
    print(f"  Provider used            : {pinfo['active_provider']}")
    print(f"  Model used               : {pinfo['active_model']}")
    print(f"  Migration ID             : {mid}")
    final_stage = mig.get('current_stage', '?')
    java_files = mig.get('generated_java_files', [])
    compiled_count = sum(1 for gf in java_files if gf.get('compile_success'))
    print(f"  Final stage              : {final_stage}")
    print(f"  Java files generated     : {len(java_files)}")
    print(f"  Compiled successfully    : {compiled_count}")
    if output_dir.exists():
        print(f"  Output folder           : {output_dir.resolve()}")
    if final_stage == "saved":
        print("\n  ALL STAGES PASSED")
    else:
        print(f"\n  WORKFLOW ENDED AT: {final_stage}")
    print("="*65)


if __name__ == "__main__":
    asyncio.run(run())
