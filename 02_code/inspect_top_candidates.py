import urllib.request
import ssl
import xml.etree.ElementTree as ET
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

targets = [
    ("PMC10721899", "PA-P-1 hybrid peptide"),
    ("PMC12382740", "Cathelicidin-based peptides"),
    ("PMC10812447", "GATR-3 peptide"),
    ("PMC12818343", "Non-immune EPs (Nat Commun)")
]

for pmcid, desc in targets:
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmcid}&retmode=xml"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"\n==================== {pmcid}: {desc} ====================")
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        
        # 1. Title
        title_el = root.find('.//article-title')
        print("Title:", ''.join(title_el.itertext()) if title_el is not None else '')
        
        # 2. Synthesis and Resin check
        for sec in root.iter('sec'):
            stitle = ''.join(sec.find('title').itertext()) if sec.find('title') is not None else ''
            if any(k in stitle.lower() for k in ['synthesis', 'peptide synthesis', 'material', 'hemolyt', 'haemolyt']):
                for p in sec.findall('p'):
                    txt = re.sub(r'\s+', ' ', ''.join(p.itertext()).strip())
                    if any(w in txt.lower() for w in ['resin', 'wang', 'rink', 'fmoc', 'amidat', 'free carboxyl', 'c-termin']):
                        print(f"  Synthesis/Resin snippet [{stitle}]: {txt[:300]}...")
                        
        # 3. Table review for MIC and Hemolysis
        for t in root.iter('table-wrap'):
            tid = t.attrib.get('id', '')
            cap = ''.join(t.find('caption').itertext()) if t.find('caption') is not None else ''
            print(f"  Table {tid}: {cap}")
            for tr in t.iter('tr')[:6]:
                cells = [re.sub(r'\s+', ' ', ''.join(c.itertext()).strip()) for c in tr.findall('td') + tr.findall('th')]
                print("    | " + " | ".join(cells))
    except Exception as e:
        print("Error fetching/parsing:", e)
