"""Archive the Figure 5 URL observed in the acquired primary HTML."""
import json
from bs4 import BeautifulSoup
from acquire_public_sources import BASE, fetch, sha
from pathlib import Path

out = BASE / "figure_acquisition"
if out.exists():
    raise FileExistsError(out)
(out / "raw").mkdir(parents=True, exist_ok=False)
html = BASE / "acquisition/raw/pmc_article.html"
url = BeautifulSoup(html.read_bytes(), "html.parser").find(id="F5").find("img")["src"]
row = fetch(("figure_5.jpg", url), out)
with (out / "source_acquisition.json").open("x", encoding="utf-8") as stream:
    json.dump(row, stream, ensure_ascii=False, indent=2)
with (out / "manifest.json").open("x", encoding="utf-8") as stream:
    json.dump({"observed_link_source": str(html.relative_to(BASE)), "source_sha256": sha(html),
               "outputs": {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()},
               "script_sha256": sha(Path(__file__))}, stream, ensure_ascii=False, indent=2)
print(json.dumps(row))
