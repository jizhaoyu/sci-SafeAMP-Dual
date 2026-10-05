"""Independent source-package and text checks; no formal release or training."""
import argparse
import ast
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
from bs4 import BeautifulSoup
import fitz
from acquire import BASE, ROOT, PREVIOUS, PRIOR_SHA, sha, write_json


def require(condition,message):
    if not condition:
        raise ValueError(message)


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    review=args.review.resolve();out=args.output.resolve()
    require(review.is_relative_to(BASE) and out.is_relative_to(BASE) and not out.exists(),'New verification path required inside batch')
    manifest=json.loads((review/'manifest.json').read_text(encoding='utf-8'))
    require(manifest['previous_review_manifest_sha256']==PRIOR_SHA==sha(PREVIOUS/'review/manifest.json'),'Prior manifest mismatch')
    for key in ['protected','inputs']:
        for name,expected in manifest[key].items():
            require(sha(ROOT/name)==expected,f'Changed {key}: {name}')
    for name,expected in manifest['outputs'].items():
        require(sha(review/name)==expected,f'Changed output: {name}')
    decisions=rows(review/'candidate_decisions.csv')
    identity=rows(review/'sequence_identity_review.csv')
    merged=rows(review/'merged_candidate_decisions.csv')
    prior=rows(PREVIOUS/'review/merged_candidate_decisions.csv')
    expected={'HIST_DRAMP20859','HIST_DRAMP20860','HIST_DRAMP20862','HIST_DRAMP20863','HIST_DRAMP20864'}
    require(len(decisions)==5 and {r['candidate_id'] for r in decisions}==expected,'Five-record scope mismatch')
    require(len(merged)==78 and len({r['candidate_id'] for r in merged})==78,'Cumulative coverage mismatch')
    old={r['candidate_id']:r for r in prior}
    current={r['candidate_id']:r for r in decisions}
    require(set(old)=={r['candidate_id'] for r in merged},'Universe changed')
    require(all(r==old[r['candidate_id']] for r in merged if r['candidate_id'] not in expected),'Other 73 records changed')
    require(all(r==current[r['candidate_id']] for r in merged if r['candidate_id'] in expected),'Merged followup differs')
    require(all(r['formal_release']==r['sequence_and_form_release']=='False' for r in merged),'Formal release changed')
    raw=BASE/'acquisition/raw'
    with zipfile.ZipFile(raw/'derived_mmc1.docx') as package:
        doc=ET.fromstring(package.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
        paragraphs=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:p',ns)]
        s1=next(text for text in paragraphs if 'Figure S1.' in text)
        require(all(text in s1 for text in ['Hemolytic activity','peripheral human blood','10 and 100 µM','SMAP-29','three independent measurements']),'S1 caption not reproduced')
        require(any('Figure S2.' in t for t in paragraphs) and any('Figure S3.' in t for t in paragraphs),'Supplement identity incomplete')
        rels=ET.fromstring(package.read('word/_rels/document.xml.rels'))
        relationships={r.attrib['Id']:r.attrib['Target'] for r in rels}
        displayed=[relationships[b.attrib['{'+ns['r']+'}embed']] for b in doc.findall('.//a:blip',ns)]
        require(displayed[0]=='media/image1.tiff' and set(displayed)=={'media/image1.tiff','media/image2.tiff','media/image3.tiff'},'Source media/figure relation changed')
        visual=json.loads((review/'visual_review.json').read_text(encoding='utf-8'))
        for entry in visual['images']:
            require(package.read(entry['source_media'])==(BASE/entry['extracted_file']).read_bytes(),'Embedded figure not preserved')
            with fitz.open(BASE/entry['extracted_file']) as figure:
                source_pix=figure[0].get_pixmap()
            # Decode PNG pixels directly: opening it as a page would scale using
            # PNG's 96 DPI metadata when get_pixmap renders at 72 DPI.
            rendered_pix=fitz.Pixmap(str(BASE/entry['render']))
            require(source_pix.width==rendered_pix.width and source_pix.height==rendered_pix.height and source_pix.samples==rendered_pix.samples,'Rendered original figure pixels differ')
        require(len(visual['images'])==3 and not visual['notes']['independent_human_review'],'Visual scope/attribution mismatch')
        require(not visual['notes']['s1_visual_findings']['rtCATH2_1_40_bar_present'],'Wrong molecule shown in S1')
    observations=rows(review/'single_point_observations.csv')
    displayed_ids=expected-{'HIST_DRAMP20863'}
    require(len(observations)==4 and {r['candidate_id'] for r in observations}==displayed_ids,'S1 molecule coverage changed')
    require(all(r['concentration']=='100' and r['concentration_unit']=='µM' and r['raw_numeric_hemolysis_percent']==r['formal_hc50']==r['formal_label']=='' and r['formal_release']=='False' for r in observations),'Single-point value promoted to numerical HC50/label')
    require({r['candidate_id'] for r in identity}==expected,'Identity coverage mismatch')
    for row in identity:
        number=row['candidate_id'].removeprefix('HIST_DRAMP')
        soup=BeautifulSoup((raw/f'DRAMP{number}.html').read_bytes(),'html.parser')
        # Read sibling li cells directly rather than reuse review.database_field.
        values={heading.get_text(strip=True):heading.find_parent('li').find_next_sibling('li').get_text(' ',strip=True)
                for heading in soup.find_all('h4') if heading.get_text(strip=True) in ['Sequence','Sequence Length','Mass']}
        require(row['database_sequence']==values['Sequence'] and row['database_reported_length']==values['Sequence Length'] and row['database_reported_mass']==values['Mass'],'DRAMP source fields mismatch')
        require(int(row['computed_database_sequence_length'])==len(values['Sequence']),'Database sequence length not reproduced')
        require((row['database_length_self_consistent']=='True')==(len(values['Sequence'])==int(values['Sequence Length'])),'Database consistency flag wrong')
    identity_map={r['candidate_id']:r for r in identity}
    require(identity_map['HIST_DRAMP20862']['database_reported_length']=='39' and identity_map['HIST_DRAMP20863']['database_reported_length']=='42','Length conflict fields changed')
    require(identity_map['HIST_DRAMP20859']['database_reported_mass']=='2181.45' and identity_map['HIST_DRAMP20859']['primary_2016_reported_mw_da']=='2510.8','TT(1-24) mass conflict lost')
    corroboration=BeautifulSoup((raw/'chang2006_pmc.html').read_bytes(),'html.parser')
    synthesis=next(p.get_text(' ',strip=True) for p in corroboration.select('p') if 'RRGKDSGGPKMGRKNSKGGWRGRPGSGSRPGFGSGI' in p.get_text())
    require('3,687.1' in synthesis and '143 to 178' in synthesis,'2006 source identity/mass mismatch')
    proposals=rows(review/'identity_correction_proposal.csv')
    require(len(proposals)==1 and proposals[0]['formal_release']=='False' and proposals[0]['status']=='identity_correction_proposal_unreleased','Correction improperly released')
    proposal=proposals[0]
    require(len(proposal['historical_inventory_sequence'])==35 and len(proposal['proposed_source_sequence'])==36,'Correction length mismatch')
    require(proposal['proposed_source_sequence']==identity_map['HIST_DRAMP20862']['primary_2016_sequence']==identity_map['HIST_DRAMP20862']['primary_2006_sequence'],'Primary corroboration mismatch')
    summary=json.loads((review/'summary.json').read_text(encoding='utf-8'))
    require(summary['merged_decision_counts']==dict(Counter(r['decision'] for r in merged)),'Summary differs from decisions')
    require(summary['merged_candidates_endpoint_screened']==sum(r['screen_status']!='original_not_acquired' for r in merged)==41,'Screened count mismatch')
    require(summary['remaining_original_access_gaps']==sum(r['screen_status']=='original_not_acquired' for r in merged)==37,'Access-gap count mismatch')
    require(summary['human_exact_hc50_values']==summary['formal_external_released']==summary['model_fit_calls']==0 and summary['formal_scientific_status']=='blocked' and not summary['training_state_changed'],'Formal state/fit count changed')
    require(summary['supplement_access_gap_resolved'] and not summary['full_docx_page_layout_verified'],'Supplement/layout attribution wrong')
    for p in (BASE/'scripts').glob('*.py'):
        tree=ast.parse(p.read_text(encoding='utf-8'))
        require(not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['fit','fit_transform','partial_fit'] for n in ast.walk(tree)),f'Model fitting added: {p.name}')
    result={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'passed','review_manifest_sha256':sha(review/'manifest.json'),
            'verification_script_sha256':sha(Path(__file__)),'protected_files_checked':len(manifest['protected']),'inputs_checked':len(manifest['inputs']),
            'outputs_checked':len(manifest['outputs']),'followup_candidates_checked':5,'merged_candidates_checked':78,'unchanged_other_candidates':73,
            'docx_media_pixel_matches':3,'database_source_fields_checked':15,'single_point_observations_checked':4,'identity_correction_proposals_checked':1,
            'full_docx_page_layout_verified':False,'independent_human_review':False,'formal_external_released':0,'model_fit_calls':0,
            'limitation':'Bound source/coverage/media checks; no numerical graph digitization, formal molecule clearance, or independent human review'}
    write_json(out,result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
