import type { DTIEvidenceStatus } from './dtiEvidence';

export interface DTIDrug {
  id: string;
  name: string;
  smiles: string;
  fold: number;
  is_test: boolean;
}

export interface DTITarget {
  id: string;
  canonical_gene_symbol?: string;
  standard_display_name?: string;
  is_misleading_mutation_label?: boolean;
  misleading_label_type?: string;
  target_semantic_type?: string;
  curation_note?: string;
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
  plan_a_protocol?: string;
  target_semantic_definition?: string;
  censoring_threshold_kd?: number;
  censoring_threshold_pkd?: number;
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
  research_evidence?: DTIEvidenceStatus;
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
    model_version?: string;
    model_sha256?: string;
    feature_version?: string;
    seed?: number;
    evaluation_scope?: string;
  };
  warning: string;
}

export interface KinomeProfileItem {
  research_evidence?: DTIEvidenceStatus;
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
  model_name?: string
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
  model_name?: string
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

export interface ADMETProperties {
  smiles: string;
  solubility_logs: number;
  solubility_mg_ml: number;
  solubility_tier: 'high' | 'moderate' | 'poor' | string;
  solubility_label: string;
  caco2_papp: number;
  caco2_tier: 'high' | 'moderate' | 'low' | string;
  caco2_label: string;
  log_bb: number;
  bbb_tier: 'cns_penetrant' | 'cns_balanced' | 'cns_impermeant' | string;
  bbb_label: string;
  cyp3a4_inhibition: 'low_risk' | 'moderate_risk' | 'high_risk' | string;
  cyp3a4_label: string;
  cyp2d6_inhibition: 'low_risk' | 'moderate_risk' | 'high_risk' | string;
  cyp2d6_label: string;
  herg_pic50: number;
  herg_risk: 'low' | 'medium' | 'high' | string;
  herg_label: string;
  herg_color: 'emerald' | 'amber' | 'rose' | string;
  admet_health_score: number;
  radar_scores: {
    solubility: number;
    permeability: number;
    herg_safety: number;
    cyp_stability: number;
    synthesis_sa: number;
  };
  traffic_lights: {
    solubility: string;
    permeability: string;
    herg_safety: string;
    cyp_stability: string;
  };
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
  sa_score?: number;
  sa_tier?: string;
  sa_label?: string;
  sa_color?: string;
  admet?: ADMETProperties;
  uncertainty_sigma?: number;
  calibrated_pkd?: number;
  calibrated_kd_nM?: number;
  delta_calibration?: number;
  calibrated_uncertainty_sigma?: number;
  calibrated_ei?: number;
  calibrated_ucb?: number;
  is_experimentally_verified?: boolean;
  rank_shift?: number;
}

export interface DTIOptimizeResult {
  research_evidence?: DTIEvidenceStatus;
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
    sa_score?: number;
    sa_tier?: string;
    sa_label?: string;
    sa_color?: string;
    admet?: ADMETProperties;
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
  model_sha256?: string;
  id: string;
  name: string;
  badge: string;
  badge_color: string;
  desc: string;
  is_recommended: boolean;
  benchmark_version?: string;
  model_version?: string;
  feature_dimension?: number;
  seed?: number;
  five_seed_ci_mean?: number;
  evaluation_scope?: string;
  metrics_by_domain?: Record<string, DomainMetrics & { n?: number }>;
  train_ci: number | null;
  train_mae?: number | null;
  dual_cold_ci?: number | null;
  cold_target_ci: number | null;
  cold_drug_ci: number | null;
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
  sa_score?: number;
  sa_tier?: string;
  sa_label?: string;
  sa_color?: string;
}

export interface ActiveLearningReport {
  research_evidence?: DTIEvidenceStatus;
  model_used?: string;
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

export interface PocketHydrogenBond {
  donor: string;
  acceptor: string;
  distance: number;
}

export interface PocketStructureResult {
  status: string;
  target_name: string;
  drug_name: string;
  pdb_code: string;
  resolution_info: string;
  binding_mode: string;
  dfg_conformation_label: string;
  hinge_residue: string;
  gatekeeper_residue: string;
  key_hydrogen_bonds: PocketHydrogenBond[];
  pdb_content: string;
  num_atoms: number;
}

export async function fetchKinasePocketStructure(
  target_name: string = 'ABL1',
  drug_name?: string,
  drug_smiles?: string
): Promise<PocketStructureResult> {
  const res = await fetch('/api/dti/pocket_structure', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_name, drug_name, drug_smiles })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || '3D 口袋结构解算失败');
  }
  return res.json();
}

export async function fetchADMETProperties(drug_smiles: string): Promise<ADMETProperties> {
  const res = await fetch('/api/dti/predict_admet', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drug_smiles })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'ADMET 属性预测解算失败');
  }
  return res.json();
}

export interface WetlabDispatchWell {
  plate_barcode: string;
  well_id: string;
  row: string;
  col: number;
  compound_id: string;
  compound_name: string;
  smiles: string;
  target_name: string;
  compound_type: 'positive_control' | 'candidate_derivative' | 'negative_control' | string;
  priority_tier: string;
  priority_color: 'emerald' | 'blue' | 'amber' | 'slate' | string;
  predicted_pkd: number;
  predicted_kd_nM: number;
  delta_pkd?: number;
  sa_score: number;
  sa_tier: string;
  admet_health_score: number;
  herg_risk: string;
  solubility_logs: number;
  stock_solvent: string;
  stock_concentration: string;
  stock_volume_ul: number;
  recommended_assay_top_uM: number;
  dilution_series: string;
}

export interface WetlabDispatchResult {
  plate_barcode: string;
  target_name: string;
  total_wells: number;
  candidates_count: number;
  tier1_count: number;
  tier2_count: number;
  tier3_count: number;
  average_sa_score: number;
  average_admet_health: number;
  wells: WetlabDispatchWell[];
  csv_content: string;
}

export async function generateWetlabDispatch(params: {
  target_name: string;
  baseline: any;
  candidates: any[];
  plate_barcode?: string;
}): Promise<WetlabDispatchResult> {
  const res = await fetch('/api/dti/wetlab_dispatch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || '生成 96 孔板投产清单失败');
  }
  return res.json();
}

export interface AcademicReportResult {
  research_evidence?: DTIEvidenceStatus;
  model_used?: string;
  markdown_report: string;
  html_report: string;
  target_name: string;
  generated_at: string;
}

export async function fetchAcademicReport(params: {
  model_used?: string;
  target_name: string;
  baseline: any;
  candidates: any[];
  biophysics?: any;
  admet?: any;
  active_learning?: any;
  author?: string;
}): Promise<AcademicReportResult> {
  const res = await fetch('/api/dti/academic_report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || '生成学术报告失败');
  }
  return res.json();
}

export interface WetlabMeasurement {
  name?: string;
  smiles: string;
  measured_kd_nM: number;
  measured_pkd?: number;
  notes?: string;
}

export interface WetlabFeedbackResult {
  status: string;
  target_name: string;
  assayed_count: number;
  updated_y_best: number;
  mae: number;
  rmse: number;
  mean_bias: number;
  assayed_evaluations: Array<{
    name: string;
    smiles: string;
    pred_pkd: number;
    meas_pkd: number;
    residual: number;
  }>;
  calibrated_candidates: CandidateDerivative[];
  promoted_candidates: CandidateDerivative[];
  narrative: string;
}

export async function submitWetlabFeedback(params: {
  target_name: string;
  candidates: any[];
  measurements: WetlabMeasurement[];
  y_best_reference?: number;
}): Promise<WetlabFeedbackResult> {
  const res = await fetch('/api/dti/wetlab_feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || '湿实验实测反馈校准失败');
  }
  return res.json();
}

export interface ClinicalTargetRecord {
  symbol: string;
  parent_symbol: string;
  name: string;
  uniprot_id: string;
  family: string;
  is_mutant: boolean;
  mutation_type?: string;
  mutation_description?: string;
  pdb_code: string;
  resolution: string;
  binding_mode_typical: string;
  hinge_residue: string;
  gatekeeper_residue: string;
  dfg_motif: string;
  indications: string[];
  approved_drugs: string[];
  chembl_id?: string;
  sequence_length: number;
  catalytic_sequence_snippet: string;
  clinical_phase_highest: string;
  enrichment?: {
    uniprot_id: string;
    chembl_id: string;
    database_cross_references: {
      uniprot_url: string;
      chembl_target_url?: string;
      pdb_rcsb_search: string;
    };
    biological_process: string[];
    subcellular_location: string;
    provenance: string;
  };
}

export async function getClinicalTargets(params?: {
  family?: string;
  include_mutants?: boolean;
  search?: string;
}): Promise<ClinicalTargetRecord[]> {
  const query = new URLSearchParams();
  if (params?.family) query.set('family', params.family);
  if (params?.include_mutants !== undefined) query.set('include_mutants', String(params.include_mutants));
  if (params?.search) query.set('search', params.search);

  const res = await fetch(`/api/dti/clinical_targets?${query.toString()}`);
  if (!res.ok) {
    throw new Error('获取临床靶点库失败');
  }
  return res.json();
}

export async function getClinicalTargetDetail(symbol: string): Promise<ClinicalTargetRecord> {
  const res = await fetch(`/api/dti/clinical_target/${encodeURIComponent(symbol)}`);
  if (!res.ok) {
    throw new Error(`获取靶点 ${symbol} 详情失败`);
  }
  return res.json();
}

export async function searchClinicalTargets(query: string): Promise<{
  query: string;
  total_hits: number;
  results: ClinicalTargetRecord[];
}> {
  const res = await fetch('/api/dti/search_targets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  if (!res.ok) {
    throw new Error('靶点检索失败');
  }
  return res.json();
}

export interface DeNovoCandidate {
  candidate_id: string;
  name: string;
  smiles: string;
  generation_mode: string;
  design_rationale: string;
  molecular_weight: number;
  clogp: number;
  predicted_pkd: number;
  predicted_kd_nM: number;
  delta_g_bind_kcal: number;
  sa_score: number;
  sa_label: string;
  ip_novelty_score: number;
  nearest_fda_drug: string;
  nearest_similarity: number;
  synthetic_feasibility: string;
  key_interactions_predicted: string[];
}

export interface DeNovoPocketResult {
  status: string;
  target_symbol: string;
  is_mutant_target: boolean;
  gatekeeper_residue: string;
  generation_mode: string;
  generation_mode_label: string;
  total_generated: number;
  candidates: DeNovoCandidate[];
  summary: string;
}

export interface CommercialPrecursor {
  reagent_id: string;
  name: string;
  cas_number: string;
  smiles: string;
  estimated_cost: string;
  suppliers: string[];
  commercial_purity: string;
}

export interface ReactionStep {
  step_number: number;
  step_title: string;
  reaction_type: string;
  reactants: string[];
  reactant_smiles: string[];
  product_name: string;
  product_smiles: string;
  catalyst_and_bases: string;
  solvent_and_conditions: string;
  estimated_yield_percent: number;
  operational_difficulty: string;
  purification_method: string;
}

export interface RetrosynthesisRoutePlan {
  target_molecule_name: string;
  target_smiles: string;
  total_steps: number;
  route_convergence: string;
  cumulative_yield_percent: number;
  atom_economy_rating: string;
  commercial_precursors: CommercialPrecursor[];
  synthesis_steps: ReactionStep[];
  expert_chemist_evaluation: string;
}

export async function generateDeNovoMolecules(req: {
  target_symbol: string;
  target_sequence?: string;
  generation_mode?: 'scaffold_hopping' | 'gatekeeper_bypasser' | 'pocket_growth';
  num_candidates?: number;
  novelty_floor?: number;
}): Promise<DeNovoPocketResult> {
  const res = await fetch('/api/dti/de_novo_generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '从头分子生成失败' }));
    throw new Error(err.detail || '从头分子生成失败');
  }
  return res.json();
}

export async function planRetrosynthesisRoute(req: {
  smiles: string;
  molecule_name?: string;
}): Promise<RetrosynthesisRoutePlan> {
  const res = await fetch('/api/dti/retrosynthesis_plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '逆合成规划失败' }));
    throw new Error(err.detail || '逆合成规划失败');
  }
  return res.json();
}

export interface ScreeningLibraryMeta {
  id: string;
  name: string;
  description: string;
  total_compounds: number;
  average_mw: number;
  vendor_source: string;
}

export interface VirtualScreeningHit {
  rank: number;
  compound_id: string;
  name: string;
  smiles: string;
  cluster_id: number;
  is_cluster_representative: boolean;
  predicted_pkd: number;
  predicted_kd_nM: number;
  delta_g_bind_kcal: number;
  sa_score: number;
  sa_label: string;
  molecular_weight: number;
  clogp: number;
  cas_number: string;
  vendor_source: string;
  key_interactions: string[];
}

export interface VirtualScreeningResult {
  status: string;
  target_symbol: string;
  is_mutant_target: boolean;
  gatekeeper_residue: string;
  library_id: string;
  library_name: string;
  total_screened: number;
  stage1_passed: number;
  stage2_passed: number;
  total_hits: number;
  num_clusters: number;
  screening_time_seconds: number;
  throughput_cpd_per_sec: number;
  hits: VirtualScreeningHit[];
  cluster_distribution: Record<string, number>;
  affinity_distribution: Record<string, number>;
  summary: string;
}

export async function fetchScreeningLibraries(): Promise<ScreeningLibraryMeta[]> {
  const res = await fetch('/api/dti/screening_libraries');
  if (!res.ok) throw new Error('获取商业筛选分子库失败');
  return res.json();
}

export async function runVirtualScreening(req: {
  target_symbol: string;
  target_sequence?: string;
  library_id?: string;
  custom_compounds?: Array<{ id?: string; name?: string; smiles: string }>;
  max_hits?: number;
  min_pkd_threshold?: number;
  diversity_cutoff?: number;
}): Promise<VirtualScreeningResult> {
  const res = await fetch('/api/dti/virtual_screen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '虚拟筛选执行失败' }));
    throw new Error(err.detail || '虚拟筛选执行失败');
  }
  return res.json();
}
