"""Compatibility entry for corrected source review; never emits an admitted cohort."""
import argparse
from pathlib import Path
from audit_mic_evidence_repair import audit, DEFAULT_OUTPUT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result = audit(parser.parse_args().output)
    print({k: result[k] for k in ("status", "data_version", "records_released_for_training")})
