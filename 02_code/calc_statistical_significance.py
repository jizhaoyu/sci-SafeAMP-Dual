"""Compute paired cluster statistics from a completed run's prediction artifact."""
import argparse
from pathlib import Path
import pandas as pd
from evaluation import compare_models
from research_utils import read_json, sha256, write_json
from publication_artifacts import load_predictions

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Output exists; refusing to overwrite evidence.')
    try:
        frame,_=load_predictions(a.run)
        write_json(a.output,compare_models(frame))
    except (ValueError,FileNotFoundError) as exc:p.error(str(exc))

if __name__=='__main__':main()
