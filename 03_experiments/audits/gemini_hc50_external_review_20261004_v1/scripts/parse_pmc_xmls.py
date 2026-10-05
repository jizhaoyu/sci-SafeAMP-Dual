import xml.etree.ElementTree as ET
import glob
import os
import re
import sys
import pandas as pd
sys.path.insert(0, 'D:/桌面文件/sci/02_code')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from research_data import sequence_identity

dev_df = pd.read_csv('D:/桌面文件/sci/03_experiments/prepared/amd02_evidence_clean_20261001/records.csv')
dev_seqs = dev_df['seq'].tolist()
dev_record_ids = dev_df['record_id'].tolist()

raw_xmls = glob.glob('D:/桌面文件/sci/03_experiments/audits/gemini_hc50_external_review_20261004_v1/raw/*.xml')

for xml_file in raw_xmls:
    print(f"\n==========================================")
    print(f"File: {os.path.basename(xml_file)}")
    with open(xml_file, 'r', encoding='utf-8') as f:
        xml_text = f.read()
    
    # Extract title
    title_m = re.search(r'<article-title>(.*?)</article-title>', xml_text, re.DOTALL)
    title = re.sub(r'<.*?>', '', title_m.group(1)).strip() if title_m else "No title"
    print(f"Title: {title}")
    
    # Search for sequences / tables
    # Find table wraps
    tables = re.findall(r'<table-wrap.*?</table-wrap>', xml_text, re.DOTALL)
    print(f"Number of tables found: {len(tables)}")
    
    # Search for "amidat" or "Rink" or "Wang" or "HC50" or "hemol" or "erythrocyte"
    has_amide = "amidat" in xml_text.lower() or "rink" in xml_text.lower()
    has_hc50 = "hc50" in xml_text.lower() or "hc<sub>50</sub>" in xml_text.lower() or "50% hemol" in xml_text.lower()
    has_human_rbc = "human erythrocyte" in xml_text.lower() or "human red blood" in xml_text.lower() or "hrbc" in xml_text.lower()
    print(f"Keywords: amide/rink={has_amide}, hc50/50%={has_hc50}, human_rbc={has_human_rbc}")
    
    # Look for sequences: 10-50 uppercase letters in tables or text
    # Let's inspect paragraphs mentioning hemolysis
    paras = re.findall(r'<p.*?</p>', xml_text, re.DOTALL)
    for p in paras:
        p_clean = re.sub(r'<.*?>', '', p).strip()
        if ("hemol" in p_clean.lower() or "hc50" in p_clean.lower()) and ("human" in p_clean.lower() or "rbc" in p_clean.lower() or "erythrocyte" in p_clean.lower()):
            print(f"  [Hemo snippet]: {p_clean[:250]}...")
