export interface DTIDrug {
  id: string;
  name: string;
  smiles: string;
  fold: number;
  is_test: boolean;
}

export interface DTITarget {
  id: string;
  length: number;
  sequence: string;
  fold: number;
  is_test: boolean;
}

export interface DomainMetrics {
  rmse: number;
  mae: number;
  pearson_r: number;
  spearman_rho: number;
  concordance_index: number;
}

export interface DTIStatus {
  status: string;
  protocol_id: string;
  models_available: string[];
  default_model: string;
  num_drugs: number;
  num_targets: number;
  total_benchmark_pairs: number;
  metrics_summary: Record<string, {
    fit_time_seconds: number;
    domains: Record<string, DomainMetrics>;
  }>;
}

export interface DTIPredictionResult {
  predicted_pkd: number;
  predicted_kd_nM: number;
  affinity_tier: string;
  affinity_tier_code: 'high_affinity' | 'moderate_affinity' | 'weak_affinity' | 'inactive';
  model_used: string;
  domain: string;
  domain_label: string;
  max_drug_similarity_to_train: number;
  max_target_similarity_to_train: number;
  domain_benchmark_metrics: DomainMetrics;
  target_length: number;
  provenance: {
    protocol: string;
    benchmark: string;
    training_run: string;
  };
  warning: string;
}

export interface KinomeProfileItem {
  kinase_name: string;
  length: number;
  predicted_pkd: number;
  predicted_kd_nM: number;
  affinity_tier: string;
  affinity_tier_code: 'high_affinity' | 'moderate_affinity' | 'weak_affinity' | 'inactive';
  domain: string;
}

export async function fetchDTIStatus(): Promise<DTIStatus> {
  const res = await fetch('/api/dti/status');
  if (!res.ok) throw new Error('Failed to fetch DTI status');
  return res.json();
}

export async function fetchDTIDrugs(): Promise<DTIDrug[]> {
  const res = await fetch('/api/dti/drugs');
  if (!res.ok) throw new Error('Failed to fetch DTI drugs');
  return res.json();
}

export async function fetchDTITargets(): Promise<DTITarget[]> {
  const res = await fetch('/api/dti/targets');
  if (!res.ok) throw new Error('Failed to fetch DTI targets');
  return res.json();
}

export async function predictDTIAffinity(
  drug_smiles: string,
  target_sequence: string,
  model_name: string = 'stacked_ensemble'
): Promise<DTIPredictionResult> {
  const res = await fetch('/api/dti/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drug_smiles, target_sequence, model_name })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'Prediction failed');
  }
  return res.json();
}

export async function profileKinasePanel(
  drug_smiles: string,
  model_name: string = 'stacked_ensemble'
): Promise<KinomeProfileItem[]> {
  const res = await fetch('/api/dti/profile_panel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drug_smiles, model_name })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'Kinome profiling failed');
  }
  return res.json();
}

export interface CandidateDerivative {
  id: string;
  name: string;
  modification_type: string;
  smiles: string;
  rationale: string;
  predicted_pkd: number;
  predicted_kd_nM: number;
  delta_pkd: number;
  fold_change: number;
  affinity_tier: string;
  affinity_tier_code: 'high_affinity' | 'moderate_affinity' | 'weak_affinity' | 'inactive';
  domain: string;
  status: string;
  status_code: 'improved' | 'neutral' | 'decreased';
}

export interface DTIOptimizeResult {
  mode: string;
  fallback_reason?: string | null;
  target_name: string;
  model_used: string;
  baseline: {
    smiles: string;
    predicted_pkd: number;
    predicted_kd_nM: number;
    affinity_tier: string;
    affinity_tier_code: string;
    domain: string;
  };
  candidates: CandidateDerivative[];
  summary: {
    candidates_evaluated: number;
    best_candidate: string;
    max_affinity_gain_pkd: number;
    best_kd_nM: number;
  };
}

export interface DTIOptimizeParams {
  drug_smiles: string;
  target_sequence: string;
  target_name?: string;
  optimization_goal?: string;
  custom_instruction?: string;
  model_name?: string;
  llm_config?: {
    provider?: string;
    api_key?: string;
    api_base?: string;
    model?: string;
  };
}

export async function optimizeLeadMolecule(
  params: DTIOptimizeParams
): Promise<DTIOptimizeResult> {
  const res = await fetch('/api/dti/optimize_lead', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'Lead optimization failed');
  }
  return res.json();
}

export interface DTIModelMeta {
  id: string;
  name: string;
  badge: string;
  badge_color: string;
  desc: string;
  is_recommended: boolean;
  train_ci: number;
  train_mae: number;
  cold_target_ci: number;
  cold_drug_ci: number;
}

export async function fetchDTIModels(): Promise<DTIModelMeta[]> {
  const res = await fetch('/api/dti/models');
  if (!res.ok) throw new Error('Failed to fetch DTI models');
  return res.json();
}

export interface MMGBSABreakdown {
  delta_g_bind: number;
  delta_e_vdw: number;
  delta_e_elec: number;
  delta_g_gb: number;
  delta_g_sa: number;
  minus_t_delta_s: number;
  phys_predicted_pkd: number;
  rotatable_bonds: number;
  buried_sasa: number;
}

export interface BiophysicsInsights {
  binding_mode: string;
  binding_mode_label: string;
  preferred_conformation: string;
  dfg_flip_penalty_kcal: number;
  induced_fit_score: number;
  base_dock_score: number;
  hinge_score: number;
  gatekeeper_clash: number;
  mmgbsa: MMGBSABreakdown;
}

export async function fetchBiophysicsInsights(
  drug_smiles: string,
  target_sequence: string,
  gatekeeper_override?: string
): Promise<BiophysicsInsights> {
  const res = await fetch('/api/dti/biophysics_insights', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drug_smiles, target_sequence, gatekeeper_override })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'Biophysics insights failed');
  }
  return res.json();
}

export interface ActiveLearningCandidate {
  smiles: string;
  name: string;
  mean_pkd: number;
  uncertainty_sigma: number;
  expected_improvement: number;
  ucb_score: number;
  quadrant: string;
  quadrant_label: string;
  recommendation_reason: string;
}

export interface ActiveLearningReport {
  target_name: string;
  total_evaluated: number;
  y_best_reference: number;
  confident_hits: ActiveLearningCandidate[];
  breakthrough_hypotheses: ActiveLearningCandidate[];
  high_information_gain_blindspots: ActiveLearningCandidate[];
  known_inactives: ActiveLearningCandidate[];
  markdown_summary: string;
}

export async function evaluateActiveLearning(params: {
  target_sequence: string;
  target_name?: string;
  candidates: Array<{ name: string; smiles: string }>;
  y_best?: number;
}): Promise<ActiveLearningReport> {
  const res = await fetch('/api/dti/active_learning', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'Active learning evaluation failed');
  }
  return res.json();
}

