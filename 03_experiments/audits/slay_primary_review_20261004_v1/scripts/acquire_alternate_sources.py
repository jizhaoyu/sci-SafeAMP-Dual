"""Try documented public source routes; archive responses, never solve challenges."""
import json
from pathlib import Path
from acquire_public_sources import BASE, fetch, sha


def main():
    out = BASE / "alternate_acquisition"
    if out.exists():
        raise FileExistsError(out)
    (out / "raw").mkdir(parents=True, exist_ok=False)
    sources = {
        "europepmc_manuscript.pdf": "https://europepmc.org/articles/PMC5786472?pdf=render",
        "publisher_article.html": "https://www.sciencedirect.com/science/article/pii/S0092867417314514",
    }
    rows = [fetch(item, out) for item in sources.items()]
    with (out / "source_acquisition.json").open("x", encoding="utf-8") as stream:
        json.dump(rows, stream, ensure_ascii=False, indent=2)
    record = {"outputs": {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()},
              "script_sha256": sha(Path(__file__)), "pdf_url_basis": "Europe PMC metadata for PMID 29307492",
              "publisher_pii_basis": "DOI resolver redirect for 10.1016/j.cell.2017.12.009",
              "evidence_release_performed": False}
    with (out / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print(json.dumps([{k: row.get(k) for k in ("requested_file", "status", "bytes", "error")} for row in rows]))


if __name__ == "__main__":
    main()
