#!/usr/bin/env python3
"""Automated remote deployment pipeline and post-deployment verification for SafeAMP.

Usage:
    python 02_code/deploy_remote.py [--host 62.234.141.184] [--user ubuntu] [--skip-build] [--verify-only]
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT_DIR = Path(__file__).resolve().parents[1]

def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"[EXEC] {' '.join(str(c) for c in cmd)}")
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        print(f"[ERROR] Command failed with code {res.returncode}:\n{res.stderr}")
        sys.exit(res.returncode)
    return res

def build_frontend():
    frontend_dir = ROOT_DIR / "frontend"
    dist_dir = frontend_dir / "dist"
    print("=== [Phase 1/4] Building Frontend SPA ===")
    if not (frontend_dir / "package.json").exists():
        print(f"[SKIP] Frontend package.json not found in {frontend_dir}")
        return

    # Run npm run build
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    run_cmd([npm_cmd, "run", "build"], cwd=frontend_dir)
    if not (dist_dir / "index.html").exists():
        print("[ERROR] Frontend build finished but dist/index.html was not generated!")
        sys.exit(1)
    print(f"[OK] Frontend built successfully at {dist_dir}")

def upload_and_deploy(host: str, user: str):
    target = f"{user}@{host}"
    print(f"=== [Phase 2/4] Uploading Release Payload to {target} ===")

    # 1. Prepare remote temp dir
    run_cmd(["ssh", "-o", "BatchMode=yes", target, "rm -rf /tmp/safeamp_deploy && mkdir -p /tmp/safeamp_deploy/dist"])

    # 2. Upload files
    files_to_upload = [
        ROOT_DIR / "05_web_server" / "rate_limiter.py",
        ROOT_DIR / "02_code" / "patch_remote_app.py",
        ROOT_DIR / "safeamp.conf",
        ROOT_DIR / "remote_deploy.sh",
    ]
    for file_path in files_to_upload:
        if not file_path.exists():
            print(f"[ERROR] Required deploy file missing: {file_path}")
            sys.exit(1)
        run_cmd(["scp", str(file_path), f"{target}:/tmp/safeamp_deploy/{file_path.name}"])

    # 3. Upload frontend dist
    dist_dir = ROOT_DIR / "frontend" / "dist"
    if dist_dir.exists():
        print("Uploading frontend dist directory...")
        run_cmd(["scp", "-r", f"{dist_dir}/.", f"{target}:/tmp/safeamp_deploy/dist/"])

    print(f"=== [Phase 3/4] Executing Remote Deployment Script on {target} ===")
    res = run_cmd(["ssh", target, "bash /tmp/safeamp_deploy/remote_deploy.sh"])
    print(res.stdout)

def verify_endpoints(host: str) -> bool:
    print(f"=== [Phase 4/4] Verifying Remote Endpoints at http://{host}/ ===")
    base_url = f"http://{host}"
    all_passed = True

    checks = [
        {"name": "System Status", "path": "/api/system_status", "expected_key": "esm_model"},
        {"name": "Health Probe", "path": "/api/health", "expected_key": "status"},
        {"name": "Metrics Probe", "path": "/api/metrics", "expected_key": "rate_limiter"},
    ]

    for check in checks:
        url = f"{base_url}{check['path']}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SafeAMP-Deploy-Verifier/1.0"})
            start = time.monotonic()
            with urllib.request.urlopen(req, timeout=10) as response:
                duration = round((time.monotonic() - start) * 1000, 1)
                data = json.loads(response.read().decode("utf-8"))
                has_key = check["expected_key"] in data
                headers = dict(response.headers)
                rate_limit_header = "x-ratelimit-limit" in [k.lower() for k in headers.keys()]
                if response.status == 200 and has_key:
                    print(f"  [PASS] {check['name']} ({url}) - {response.status} OK in {duration}ms (RateLimit Header: {rate_limit_header})")
                else:
                    print(f"  [FAIL] {check['name']} ({url}) - Unexpected response: {data}")
                    all_passed = False
        except Exception as e:
            print(f"  [FAIL] {check['name']} ({url}) - Error: {e}")
            all_passed = False

    # Check Gzip and Security Headers
    try:
        req = urllib.request.Request(f"{base_url}/", headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=10) as response:
            headers = {k.lower(): v for k, v in response.headers.items()}
            has_x_frame = "x-frame-options" in headers
            has_nosniff = "x-content-type-options" in headers
            print(f"  [INFO] Security Headers -> X-Frame-Options: {has_x_frame}, nosniff: {has_nosniff}")
            if not has_x_frame or not has_nosniff:
                print("  [WARN] Some security headers were not detected.")
    except Exception as e:
        print(f"  [WARN] Could not verify root page headers: {e}")

    return all_passed

def main():
    parser = argparse.ArgumentParser(description="Deploy SafeAMP to remote server and verify.")
    parser.add_argument("--host", default="62.234.141.184", help="Remote server IP or hostname")
    parser.add_argument("--user", default="ubuntu", help="Remote SSH username")
    parser.add_argument("--skip-build", action="store_true", help="Skip frontend build")
    parser.add_argument("--verify-only", action="store_true", help="Only run verification against remote host")

    args = parser.parse_args()

    if not args.verify_only:
        if not args.skip_build:
            build_frontend()
        upload_and_deploy(args.host, args.user)

    success = verify_endpoints(args.host)
    if success:
        print("\n=======================================================")
        print(" [ALL CHECKS PASSED] Remote deployment verified 100%!")
        print("=======================================================")
        sys.exit(0)
    else:
        print("\n[FAILED] One or more verification checks failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
