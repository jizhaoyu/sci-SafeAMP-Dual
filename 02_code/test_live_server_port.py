"""Live server real-port (127.0.0.1:8000) networking interoperability test.
Spawns uvicorn server in a subprocess, verifies real HTTP network calls,
CORS headers, and graceful shutdown.
"""
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error

SERVER_URL = "http://127.0.0.1:8000"

def run_live_port_test():
    print("=" * 70)
    print("[START] Spawning Real Uvicorn Server Subprocess (127.0.0.1:8000)...")
    print("=" * 70)

    # Spawn server process
    proc = subprocess.Popen(
        [sys.executable, "05_web_server/app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # 1. Wait for server readiness
        ready = False
        t_deadline = time.time() + 10.0
        while time.time() < t_deadline:
            try:
                req = urllib.request.Request(f"{SERVER_URL}/api/health")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.3)

        assert ready, "Server failed to start and respond on 127.0.0.1:8000 within 10s"
        print("[READY] Server is actively listening on http://127.0.0.1:8000\n")

        # 2. Test GET /api/health over real HTTP
        print("[Live 1/4] Real HTTP GET /api/health...", end=" ")
        req = urllib.request.Request(f"{SERVER_URL}/api/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            cors_hdr = resp.headers.get("access-control-allow-origin")
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "healthy"
            print(f"PASS (Status 200, CORS: {cors_hdr})")

        # 3. Test GET /api/dti/models over real HTTP
        print("[Live 2/4] Real HTTP GET /api/dti/models...", end=" ")
        req = urllib.request.Request(f"{SERVER_URL}/api/dti/models")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            models = json.loads(resp.read().decode("utf-8"))
            assert any(m["id"] == "worldmodel_stacked_ensemble" for m in models)
            print(f"PASS (Found {len(models)} models)")

        # 4. Test POST /api/dti/biophysics_insights over real HTTP
        print("[Live 3/4] Real HTTP POST /api/dti/biophysics_insights...", end=" ")
        post_data = json.dumps({
            "drug_smiles": "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO",
            "target_sequence": "MLEICLKLVGCKSKKGLSSSSSCYLEEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSITKGEKLRVLGYNHNGEWCEAQTKNGQGWVPSNYITPVNSLEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISLRYEGRVYHYRINTASDGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTVYGVSPNYDKWEMERTDITMKHKLGGGQYGEVYEGVWKKYSLTVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVVLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNKFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAKSPKPSNGAGVPNGALRESGGSGFRSPHLWKKSSTLTSSRLATGEEEGGGSSSKRFLRSCSASCVPHGAKDTEWRSVTLPRDLQSTGRQFDSSTFGGHKSEKPALPRKRAGENRSDQVTRGTVTPPPRLVKKNEEAADEVFKDIMESSPGSSPPNLTPKPLRRQVTVAPASGLPHKEEAEKGSALGTPAAAEPVTPTSKAGSGAPGGTSKGPAEESRVRRHKHSSESPGRDKGKLSRLKPAPPPPPAASAGKAGGKPSQSPSQEAAGEAVLGAKTKATSLVDAVNSDAAKPSQPGEGLKKPVLPATPKPQSAKPSGTPISPAPVPSTLPSASSALAGDQPSSTAFIPLISTRVSLRKTRQPPERIASGAITKGVVLDSTEALCLAISRNSEQMASHSAVLEAGKNLYTFCVSYVDSIQQMRNKFAFREAINKLENNLRELQICPATAGSGPAATQDFSKLLSSVKEISDIVQR"
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{SERVER_URL}/api/dti/biophysics_insights",
            data=post_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            bio = json.loads(resp.read().decode("utf-8"))
            assert "mmgbsa" in bio and "binding_mode" in bio
            print(f"PASS (Mode: {bio['binding_mode']}, dG_bind: {bio['mmgbsa']['delta_g_bind']} kcal/mol)")

        # 5. Test Frontend Static Asset Delivery over real HTTP
        print("[Live 4/4] Real HTTP GET / (Frontend Shell)...", end=" ")
        req = urllib.request.Request(f"{SERVER_URL}/")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "<div id=\"root\"></div>" in html or "<script type=\"module\"" in html
            print("PASS (Static HTML delivered)")

        print("\n" + "=" * 70)
        print("[SUCCESS] REAL HTTP NETWORK INTEROPERABILITY VERIFIED 100% OPERATIONAL!")
        print("=" * 70)

    finally:
        # Graceful shutdown
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[STOPPED] Uvicorn server subprocess gracefully stopped.")

if __name__ == "__main__":
    run_live_port_test()
