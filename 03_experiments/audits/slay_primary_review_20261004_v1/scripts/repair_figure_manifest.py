"""Preserve the first manifest; correct its empty self-hash in a new version."""
import json
from pathlib import Path
from acquire_public_sources import BASE, sha

folder = BASE / "figure_acquisition"
previous = folder / "manifest.json"
out = folder / "manifest_v2.json"
if out.exists():
    raise FileExistsError(out)
record = json.loads(previous.read_text(encoding="utf-8"))
for name, expected in record["outputs"].items():
    if name != "manifest.json" and sha(folder / name) != expected:
        raise ValueError(f"Changed figure source: {name}")
record["outputs"] = {name: expected for name, expected in record["outputs"].items() if name != "manifest.json"}
record["previous_manifest_sha256"] = sha(previous)
record["correction"] = "Initial manifest inadvertently included its empty self-hash while open. Source files unchanged; old manifest retained."
record["repair_script_sha256"] = sha(Path(__file__))
with out.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
print(sha(out))
