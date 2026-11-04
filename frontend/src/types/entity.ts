/**
 * Rigorous chemical entity and target context types.
 * Enforces strict separation between Small Molecules (SMILES with preserved casing)
 * and Peptides (standard amino acid sequences).
 */

export interface SmallMoleculeEntity {
  kind: 'small_molecule';
  smiles: string; // Exact case preserved (aromatic c, n, o, s, halogens Cl, Br, stereochemistry @/@@, etc.)
  name: string;
  source?: string;
  input_hash?: string;
}

export interface PeptideEntity {
  kind: 'peptide';
  sequence: string; // Standard uppercase amino acid sequence
  name: string;
  terminal_mods?: string;
  source?: string;
  input_hash?: string;
}

export interface UnconfirmedEntity {
  kind: 'unconfirmed';
  sequence: string;
  name: string;
  source?: string;
  input_hash?: string;
}

export type ChemicalEntity = SmallMoleculeEntity | PeptideEntity | UnconfirmedEntity;

export interface TargetContext {
  id: string; // e.g. "ABL1", "EGFR-T790M"
  standardDisplayName: string;
  sequence: string;
  sequenceSummary?: string;
  source?: string;
  isMutant?: boolean;
  gatekeeperResidue?: string;
  mutationInfo?: string;
}

export interface CartItem {
  id: string;
  kind?: 'small_molecule' | 'peptide' | 'unknown';
  sequence: string; // Kept for backwards compatibility (SMILES or peptide seq)
  name: string;
  smiles?: string;
  p_amp?: number;
  p_hemo?: number;
  tsi?: number;
  pkd?: number;
  is_short?: boolean;
  addedAt: string;
  run_id?: string;
  source?: string;
  sa_score?: number;
  sa_tier?: string;
  admet?: any;
  target_symbol?: string;
  model_used?: string;
  parent_similarity?: number;
  modification_type?: string;
  scaffold_type?: string;
}
