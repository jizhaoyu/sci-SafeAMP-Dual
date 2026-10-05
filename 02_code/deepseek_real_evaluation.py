"""Compatibility CLI for bounded DeepSeek checks; credentials come from configuration.

Historical response records are preserved in output/verification. This entry no longer
uploads research narratives or creates unsupported diagnostic/peer-review claims.
Use --output with a new directory under 03_experiments/audits.
"""
from deepseek_live_smoke import main


if __name__ == "__main__":
    raise SystemExit(main())
