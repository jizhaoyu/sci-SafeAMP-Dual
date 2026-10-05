import urllib.request
import json
import xml.etree.ElementTree as ET
import os

pmc_list = [
    ("PMC13515218", "42653830"),
    ("PMC13510277", "42650737"),
    ("PMC13436381", "42370696"),
    ("PMC13216044", "42221479"),
    ("PMC12412326", "40864826"),
]

out_dir = "D:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/raw"
os.makedirs(out_dir, exist_ok=True)

for pmcid, pmid in pmc_list:
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmcid}&retmode=xml"
    file_path = os.path.join(out_dir, f"{pmcid}.xml")
    if not os.path.exists(file_path):
        try:
            print(f"Fetching {pmcid} (PMID {pmid})...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                content = resp.read()
            with open(file_path, "wb") as f:
                f.write(content)
            print(f"Saved {file_path} ({len(content)} bytes)")
        except Exception as e:
            print(f"Error fetching {pmcid}: {e}")
    else:
        print(f"Already exists: {file_path}")
