"""Extract primary evidence tables and sections from XMLs and PDF for v2."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pypdf

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw'

def text(node):
    return ' '.join(node.itertext()).strip() if node is not None else ''

def main():
    evidence = []
    
    # 1. XML sources
    xml_files = {
        'pandinin2014': RAW / 'pandinin2014.xml',
        'corvus2023': RAW / 'corvus2023.xml',
        'chmap2018': RAW / 'chmap2018.xml',
        'goat_antibacterial2018': RAW / 'goat_antibacterial2018.xml',
    }
    
    for sid, path in xml_files.items():
        article = ET.parse(path).getroot()
        tables = []
        for node in article.findall('.//table-wrap'):
            t_id = node.get('id')
            t_caption = text(node.find('.//caption'))
            rows = []
            for tr in node.findall('.//tr'):
                cells = [text(c) for c in tr if c.tag in ('td', 'th')]
                if cells:
                    rows.append(cells)
            tables.append({
                'id': t_id,
                'caption': t_caption,
                'rows': rows
            })
        
        sections = []
        for sec in article.findall('.//sec'):
            stitle = text(sec.find('title'))
            if any(k in stitle.lower() for k in ['synthesis', 'hemol', 'haemol', 'antimicrobial', 'bacterial', 'activity', 'mic', 'cytotox']):
                sections.append({
                    'title': stitle,
                    'text': text(sec)[:2000]
                })
        
        evidence.append({
            'source_id': sid,
            'source_type': 'JATS_XML',
            'tables': tables,
            'sections': sections
        })
    
    # 2. Hymenochirin thesis PDF
    pdf_path = RAW / 'mechkarska2013_thesis.pdf'
    reader = pypdf.PdfReader(str(pdf_path))
    thesis_tables = [
        {
            'id': 'Chapter6_Table1',
            'caption': 'Minimum inhibitory concentrations against microorganisms and hemolytic activity against human erythrocytes (LC50) of the peptides isolated from skin secretions of H. boettgeri.',
            'rows': [
                ['Peptide', 'E. coli (ATCC 25726)', 'P. aeruginosa', 'K. pneumoniae', 'S. aureus', 'C. albicans', 'LC50 (human RBC)'],
                ['Hymenochirin-1B', '20 µM', '40 µM', '20 µM', '10 µM', '80 µM', '225 µM'],
                ['Hymenochirin-2B', '20 µM', '20 µM', '20 µM', '40 µM', '80 µM', '>300 µM'],
                ['Hymenochirin-3B', '20 µM', '40 µM', '40 µM', '40 µM', '80 µM', '>300 µM'],
                ['Hymenochirin-4B', '20 µM', '20 µM', '20 µM', '20 µM', '80 µM', '160 µM'],
                ['Hymenochirin-5B', '40 µM', 'ND', 'ND', '80 µM', '160 µM', 'ND']
            ]
        },
        {
            'id': 'Chapter6_Fig4_Sequences',
            'caption': 'Amino acid sequences and molecular masses of hymenochirins from H. boettgeri.',
            'rows': [
                ['Peptide', 'Sequence', 'Observed Mr', 'Calculated Mr', 'Terminal C'],
                ['Hymenochirin-1B', 'IKLSPETKDNLKKVLKGAIKGAIAVAKMV.NH2', '3061.8', '3061.8', 'amidated (-NH2)'],
                ['Hymenochirin-2B', 'LKIPGFVKDTLKKVAKGIFSAVAGAMTPS', '2973.5', '2973.7', 'free carboxyl (-COOH)'],
                ['Hymenochirin-3B', 'IKIPAVVKDTLKKVAKGVLSAVAGALTQ', '2817.6', '2817.7', 'free carboxyl (-COOH)'],
                ['Hymenochirin-4B', 'IKIPAFVKDTLKKVAKGVISAVAGALTQ', '2865.9', '2865.7', 'free carboxyl (-COOH)'],
                ['Hymenochirin-5B', 'IKIPPIVKDTLKKVAKGVLSTIAGALST', '2861.0', '2860.8', 'free carboxyl (-COOH)']
            ]
        }
    ]
    thesis_sections = [
        {
            'title': 'Chapter 6 Section 2.4 Peptide synthesis',
            'text': reader.pages[130].extract_text()
        },
        {
            'title': 'Chapter 6 Section 2.5 Antimicrobial and hemolytic activities',
            'text': reader.pages[131].extract_text()
        },
        {
            'title': 'Chapter 6 Section 3.3 Results: Antimicrobial and hemolytic activities',
            'text': reader.pages[134].extract_text()
        }
    ]
    evidence.append({
        'source_id': 'hymenochirin2012',
        'source_type': 'AUTHOR_DEPOSITED_THESIS_PDF',
        'thesis_page_range': 'Chapter 6 (pp. 127-142)',
        'tables': thesis_tables,
        'sections': thesis_sections
    })
    
    with (ROOT / 'primary_evidence.json').open('w', encoding='utf-8') as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)
    
    print('primary_evidence.json generated successfully. Sources included:', len(evidence))

if __name__ == '__main__':
    main()
