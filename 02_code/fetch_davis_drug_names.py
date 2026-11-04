"""Fetch common clinical drug names from PubChem PUG REST API for DAVIS benchmark."""
import json
import urllib.request
from research_utils import ROOT, utc_now

def main():
    drugs_file = ROOT / "03_experiments/audits/dti_davis_field_review_20261006_v1/drugs.json"
    with open(drugs_file, "r", encoding="utf-8") as f:
        drugs = json.load(f)

    cids = list(drugs.keys())
    print(f"Querying PubChem PUG REST for {len(cids)} CIDs...")

    cid_str = ",".join(cids)
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid_str}/property/Title/JSON"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    props = data["PropertyTable"]["Properties"]
    cid_to_name = {}
    for p in props:
        cid = str(p["CID"])
        title = p.get("Title", f"CID-{cid}")
        cid_to_name[cid] = title

    print(f"Successfully retrieved {len(cid_to_name)} drug titles.")
    print("Examples:")
    for k in list(cid_to_name.keys())[:8]:
        print(f"  CID {k} -> {cid_to_name[k]}")

    out_path = ROOT / "03_experiments/prepared/dti_davis_features_20261006_v1/drug_names.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cid_to_name, f, indent=2, ensure_ascii=False)
    print(f"Saved drug names dictionary to: {out_path}")

if __name__ == "__main__":
    main()
