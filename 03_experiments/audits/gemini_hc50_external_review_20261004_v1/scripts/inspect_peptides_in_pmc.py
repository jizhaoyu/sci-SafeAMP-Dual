import re
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

for xml_file in ['PMC13510277.xml', 'PMC12412326.xml', 'PMC13515218.xml']:
    path = f'D:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/raw/{xml_file}'
    with open(path, 'r', encoding='utf-8') as f:
        t = f.read()
    print(f"\n==================== {xml_file} ====================")
    
    # Check peptide synthesis/sequence
    for kw in ['sequence', 'rink', 'wang', 'amidation', 'amidated', 'd-amino', 'c-terminal']:
        matches = [m.start() for m in re.finditer(kw, t, re.IGNORECASE)]
        print(f"  Keyword '{kw}': {len(matches)} occurrences")
        for pos in matches[:2]:
            snippet = t[max(0, pos-100):min(len(t), pos+200)]
            snippet = re.sub(r'<.*?>', ' ', snippet)
            print(f"    Snippet: {' '.join(snippet.split())}")
