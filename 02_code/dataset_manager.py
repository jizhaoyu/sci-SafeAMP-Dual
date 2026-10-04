"""Compatibility entrypoint: only provenance-aware experimental data are accepted."""
from research_data import main, prepare, sequence_identity, ResearchDataError

# Kept as an explicit alias for callers; this is global NW, not CD-HIT.
calculate_sequence_identity = sequence_identity

if __name__ == "__main__":
    main()
