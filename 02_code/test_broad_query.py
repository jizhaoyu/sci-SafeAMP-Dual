import urllib.request
import urllib.parse
import json
import ssl
import sys

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

q = '("human erythrocytes" OR "human red blood cells") AND ("HC50") AND ("antimicrobial") AND OPEN_ACCESS:y'
url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=' + urllib.parse.quote(q) + '&format=json&resultType=core&pageSize=25'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print("Hits:", data.get("hitCount", 0))
    for idx, item in enumerate(data.get("resultList", {}).get("result", [])[:15]):
        pmid = item.get("pmid", "")
        pmcid = item.get("pmcid", "")
        year = item.get("pubYear", "")
        title = item.get("title", "")[:70]
        print(f"{idx+1}. PMID:{pmid} | PMCID:{pmcid} [{year}] {title}")
