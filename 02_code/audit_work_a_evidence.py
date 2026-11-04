import sys
import xml.etree.ElementTree as ET
import re

sys.stdout.reconfigure(encoding='utf-8')

def audit_a1():
    print("================== A1: PMID 35835842 (DP3) ==================")
    tree = ET.parse(r'03_experiments/audits/dual_task_readiness_20261005_v1/hemo_positive_batch_original_acquisition_v1/35835842.xml')
    root = tree.getroot()
    
    # 1. Title, Abstract, DOI
    for article_id in root.iter('article-id'):
        print(f"ID ({article_id.attrib.get('pub-id-type')}): {article_id.text}")
        
    # 2. Table 1 & Table 2
    for table in root.iter('table-wrap'):
        t_id = table.attrib.get('id', '')
        caption = ''.join(table.find('caption').itertext()) if table.find('caption') is not None else ''
        print(f"\n--- Table {t_id}: {caption} ---")
        for tr in table.iter('tr'):
            cells = [re.sub(r'\s+', ' ', ''.join(cell.itertext()).strip()) for cell in tr.findall('td') + tr.findall('th')]
            if any('DP3' in c or 'Haemolytic' in c or 'HC50' in c or 'Peptide' in c or 'Sequence' in c or 'Mouse' in c or 'Erythrocyte' in c for c in cells):
                print("  ROW:", " | ".join(cells))
            elif any('DP' in c for c in cells):
                print("  ROW (DP):", " | ".join(cells))
                
    # 3. Section on Haemolysis / Synthesis
    for sec in root.iter('sec'):
        title = ''.join(sec.find('title').itertext()) if sec.find('title') is not None else ''
        sec_text = ''.join(sec.itertext())
        if any(k in title.lower() for k in ['haemolyt', 'hemolyt', 'peptide synthesis', 'erythrocyte']):
            print(f"\nSection Title: {title}")
            for p in sec.findall('p'):
                print("  P:", re.sub(r'\s+', ' ', ''.join(p.itertext()).strip()))

if __name__ == '__main__':
    audit_a1()
