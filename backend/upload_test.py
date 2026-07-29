"""Quick upload test for Calculator.cs against port 8001."""
import urllib.request
import json

def main():
    BASE = "http://127.0.0.1:8001"

    # 1. Create migration
    body = json.dumps({"project_name": "SwaggerFixTest"}).encode()
    req = urllib.request.Request(
        BASE + "/api/migrations", data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    r = urllib.request.urlopen(req, timeout=10)
    created = json.loads(r.read())
    mid = created["migration_id"]
    print(f"Created migration: {mid}")

    # 2. Upload Calculator.cs from Desktop
    cs_path = r"c:\Users\Lenovo\OneDrive\Desktop\Calculator.cs"
    with open(cs_path, "rb") as f:
        cs_content = f.read()

    boundary = b"----boundary1234"
    crlf = b"\r\n"
    body_parts = (
        b"--" + boundary + crlf
        + b'Content-Disposition: form-data; name="files"; filename="Calculator.cs"' + crlf
        + b"Content-Type: application/octet-stream" + crlf + crlf
        + cs_content + crlf
        + b"--" + boundary + b"--" + crlf
    )
    req2 = urllib.request.Request(
        f"{BASE}/api/migrations/{mid}/upload",
        data=body_parts,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
        method="POST",
    )
    r2 = urllib.request.urlopen(req2, timeout=15)
    result = json.loads(r2.read())
    print(f"HTTP status      : {r2.status}")
    print(f"uploaded_count   : {result['uploaded_count']}")
    print(f"uploaded_files   : {result['uploaded_files']}")
    print(f"message          : {result['message']}")


if __name__ == "__main__":
    main()
