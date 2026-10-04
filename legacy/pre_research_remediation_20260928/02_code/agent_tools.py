import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import torch
import os
from ai_optimizer import AIPeptideOptimizer
from model_dual_task import SafeAMPDualNet
from feature_extractor import ESMFeatureExtractor
from helical_wheel import compute_helical_wheel_data

def search_pubmed(query: str) -> str:
    """Uses NCBI Entrez E-utilities API to search for recent literature abstracts."""
    try:
        # 1. Search for IDs
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmode=json&retmax=3"
        with urllib.request.urlopen(search_url) as response:
            search_data = json.loads(response.read().decode())
        
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return "No recent literature found."
            
        # 2. Fetch abstracts
        ids_str = ",".join(id_list)
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&retmode=xml"
        with urllib.request.urlopen(fetch_url) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        abstracts = []
        for article in root.findall(".//PubmedArticle"):
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No Title"
            abstract_text = ""
            for text_elem in article.findall(".//AbstractText"):
                if text_elem.text:
                    abstract_text += text_elem.text + " "
            if abstract_text:
                abstracts.append(f"Title: {title}\nAbstract: {abstract_text}")
                
        return "\n\n".join(abstracts)[:2000] # Truncate to save tokens
    except Exception as e:
        return f"Literature search failed: {str(e)}"

# Instantiate tools for Toxicology node
extractor = ESMFeatureExtractor()
model = SafeAMPDualNet()
weights_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights", "safeamp_dual_best.pt")
if os.path.exists(weights_path):
    model.load_state_dict(torch.load(weights_path, map_location=torch.device('cpu')))
model.eval()
ai_engine = AIPeptideOptimizer(model, extractor, device="cpu")

def run_toxicology_calc(sequence: str) -> dict:
    p_amp_val, p_hemo_val, tsi = ai_engine.evaluate_sequence(sequence)
    
    # Helical wheel
    wheel = compute_helical_wheel_data(sequence)
    
    return {
        "p_amp": p_amp_val,
        "p_hemo": p_hemo_val,
        "tsi": tsi,
        "net_charge": wheel["net_charge"],
        "mean_hydrophobicity": wheel["mean_hydrophobicity"],
        "hydrophobic_moment": wheel["hydrophobic_moment"]
    }
