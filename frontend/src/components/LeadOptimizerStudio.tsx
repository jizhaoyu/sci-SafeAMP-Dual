import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Dna, 
  FlaskConical, 
  TrendingUp, 
  ArrowUpRight, 
  ArrowDownRight, 
  Minus, 
  Copy, 
  Check, 
  PlusCircle, 
  Cpu, 
  AlertCircle, 
  Compass, 
  Zap,
  Info,
  Grid,
  Download,
  HelpCircle,
  Box,
  Palette,
  ShieldCheck,
  FileText,
  RefreshCw,
  CheckCircle2,
  TestTube
} from 'lucide-react';
import { 
  fetchDTIDrugs, 
  fetchDTITargets, 
  optimizeLeadMolecule,
  evaluateActiveLearning,
  fetchADMETProperties,
  generateWetlabDispatch,
  fetchAcademicReport,
  submitWetlabFeedback,
  type DTIDrug, 
  type DTITarget, 
  type DTIOptimizeResult,
  type CandidateDerivative,
  type ActiveLearningReport,
  type ActiveLearningCandidate,
  type ADMETProperties,
  type WetlabDispatchResult,
  type AcademicReportResult,
  type WetlabFeedbackResult,
  type ClinicalTargetRecord
} from '../api/dtiClient';
import { useAppStore } from '../store/useAppStore';
import { useDTIModelStatus } from '../api/researchStatus';
import { useDTIEvidenceStatus, evidenceNotice, evidenceCSVValues, EVIDENCE_CSV_HEADERS, csvLine, researchCopy, evidenceMarkdown, predictionScoreBand, PREDICTION_SCOPE_NOTICE } from '../api/dtiEvidence';
import { DTIEvidencePanel } from './DTIEvidencePanel';
import { DTIModelLimitations } from './DTIModelLimitations';
import { computeDrugLikeness, computeQuickSAScore } from '../utils/cheminformatics';
import { Molecule2DViewer } from './Molecule2DViewer';
import { KinasePocketViewer3D } from './KinasePocketViewer3D';
import { MoleculeSketcherModal } from './MoleculeSketcherModal';
import { ADMETRadarModal } from './ADMETRadarModal';
import { WetlabDispatchModal } from './WetlabDispatchModal';
import { AcademicReportModal } from './AcademicReportModal';
import { ClinicalTargetSelectorModal } from './ClinicalTargetSelectorModal';
import { DeNovoPocketGeneratorModal } from './DeNovoPocketGeneratorModal';
import { RetrosynthesisModal } from './RetrosynthesisModal';
import { VirtualScreeningModal } from './VirtualScreeningModal';


const PRESET_EXAMPLES = [
  {
    label: '达沙替尼 (Dasatinib) → ABL1',
    drugName: 'Dasatinib',
    smiles: 'CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO',
    targetSymbol: 'ABL1',
    goal: '提升亲和力与结合强度',
    instruction: '在苯环无阻碍位点探查卤素结合，或在哌嗪环外围微调提升与门控残基的互作'
  },
  {
    label: '吉非替尼 (Gefitinib) → EGFR',
    drugName: 'Gefitinib',
    smiles: 'COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4',
    targetSymbol: 'EGFR',
    goal: '规避耐药突变骨架微调',
    instruction: '保留喹唑啉母环核心双氢键，对吗啉侧链与苯胺卤素进行电子等排修饰'
  },
  {
    label: '索拉非尼 (Sorafenib) → BRAF',
    drugName: 'Sorafenib',
    smiles: 'CNC(=O)C1=NC=CC(=C1)OC2=CC=C(C=C2)NC(=O)NC3=CC(=C(C=C3)Cl)C(F)(F)F',
    targetSymbol: 'BRAF',
    goal: '引入增溶侧链改善成药性',
    instruction: '在芳基脲两亲骨架外周修饰增溶极性中心，兼顾变构后口袋深度填充'
  }
];

const OPTIMIZATION_GOALS = [
  { value: '提升亲和力与结合强度', label: '提升亲和力与结合强度 (Potency & Kd Enhancement)' },
  { value: '引入增溶侧链改善成药性', label: '引入增溶侧链改善成药性 (Solubility & PK Optimization)' },
  { value: '阻断易代谢位点增加代谢稳定性', label: '阻断易代谢位点增加代谢稳定性 (Metabolic Stability & Soft-Spot Shielding)' },
  { value: '变构口袋空间填充与增益', label: '变构口袋空间填充与增益 (Allosteric Pocket Filling)' },
  { value: '规避耐药突变骨架微调', label: '规避耐药突变骨架微调 (Resistance Mutation Bypass)' },
];

export default function LeadOptimizerStudio() {
  const { llmProvider, apiKey, apiBase, modelName, addToCart } = useAppStore();
  
  // Data lists
  const [drugs, setDrugs] = useState<DTIDrug[]>([]);
  const [targets, setTargets] = useState<DTITarget[]>([]);
  
  // Form Inputs
  const [drugSmiles, setDrugSmiles] = useState<string>('');
  const [drugDisplayName, setDrugDisplayName] = useState<string>('Custom Lead');
  const [targetSequence, setTargetSequence] = useState<string>('');
  const [targetName, setTargetName] = useState<string>('ABL1 (激酶靶点)');
  const [isTargetModalOpen, setIsTargetModalOpen] = useState<boolean>(false);
  const [optimizationGoal, setOptimizationGoal] = useState<string>(OPTIMIZATION_GOALS[0].value);

  const [customInstruction, setCustomInstruction] = useState<string>('');
  const [chosenModel, setEvalModel] = useState<string>('');
  const modelStatus = useDTIModelStatus();
  const evidence = useDTIEvidenceStatus();
  const registeredModels = modelStatus.ready ? modelStatus.data ?? [] : [];
  const evalModel = registeredModels.some(model => model.id === chosenModel)
    ? chosenModel : (registeredModels.find(model => model.is_recommended)?.id ?? registeredModels[0]?.id ?? '');

  // Execution states
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<DTIOptimizeResult | null>(null);
  
  // Active Learning states
  const [activeLearningReport, setActiveLearningReport] = useState<ActiveLearningReport | null>(null);
  const [isLoadingActiveLearning, setIsLoadingActiveLearning] = useState<boolean>(false);
  const [resultViewTab, setResultViewTab] = useState<'ladder' | 'active_learning'>('ladder');
  
  // UI interaction states
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copiedReport, setCopiedReport] = useState<boolean>(false);
  const [cartSuccessId, setCartSuccessId] = useState<string | null>(null);
  const [isSketcherOpen, setIsSketcherOpen] = useState<boolean>(false);
  const [showPocket3D, setShowPocket3D] = useState<boolean>(false);
  const [active3DPair, setActive3DPair] = useState<{ drugName: string; smiles: string } | null>(null);

  // ADMET modal states
  const [admetModalOpen, setAdmetModalOpen] = useState<boolean>(false);
  const [currentAdmet, setCurrentAdmet] = useState<ADMETProperties | null>(null);
  const [currentAdmetName, setCurrentAdmetName] = useState<string>('');
  const [admetLoading, setAdmetLoading] = useState<boolean>(false);

  const handleOpenAdmet = async (moleculeName: string, smiles: string, precomputedAdmet?: ADMETProperties) => {
    setCurrentAdmetName(moleculeName);
    if (precomputedAdmet) {
      setCurrentAdmet(precomputedAdmet);
      setAdmetModalOpen(true);
      return;
    }
    setAdmetModalOpen(true);
    setAdmetLoading(true);
    try {
      const data = await fetchADMETProperties(smiles);
      setCurrentAdmet(data);
    } catch (err) {
      console.error('Failed to load ADMET:', err);
    } finally {
      setAdmetLoading(false);
    }
  };

  // Wet-lab Dispatch Modal
  const [dispatchModalOpen, setDispatchModalOpen] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<WetlabDispatchResult | null>(null);
  const [dispatchLoading, setDispatchLoading] = useState(false);

  const handleOpenDispatch = async () => {
    if (!optimizeResult) return;
    setDispatchModalOpen(true);
    setDispatchLoading(true);
    try {
      const res = await generateWetlabDispatch({
        target_name: optimizeResult.target_name,
        baseline: optimizeResult.baseline,
        candidates: optimizeResult.candidates
      });
      setDispatchResult(res);
    } catch (err) {
      console.error('Failed to generate wetlab dispatch:', err);
    } finally {
      setDispatchLoading(false);
    }
  };

  // Academic Report Modal
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportData, setReportData] = useState<AcademicReportResult | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const handleOpenReport = async () => {
    if (!optimizeResult) return;
    setReportModalOpen(true);
    setReportLoading(true);
    try {
      const res = await fetchAcademicReport({
        model_used: optimizeResult.model_used,
        target_name: optimizeResult.target_name,
        baseline: optimizeResult.baseline,
        candidates: optimizeResult.candidates,
        active_learning: activeLearningReport
      });
      setReportData(res);
    } catch (err) {
      console.error('Failed to generate academic report:', err);
    } finally {
      setReportLoading(false);
    }
  };

  // Wet-lab Feedback Calibration State
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackResult, setFeedbackResult] = useState<WetlabFeedbackResult | null>(null);
  const [inputMeasuredKd, setInputMeasuredKd] = useState<string>('12.5');
  const [showFeedbackPanel, setShowFeedbackPanel] = useState(false);

  const handleSubmitFeedback = async (targetCandSmiles?: string, targetCandName?: string) => {
    if (!optimizeResult || !optimizeResult.candidates.length) return;
    const kdVal = parseFloat(inputMeasuredKd);
    if (isNaN(kdVal) || kdVal <= 0) return;

    setFeedbackSubmitting(true);
    const targetSmiles = targetCandSmiles || optimizeResult.candidates[0].smiles;
    const targetName = targetCandName || optimizeResult.candidates[0].name;

    try {
      const res = await submitWetlabFeedback({
        target_name: optimizeResult.target_name,
        candidates: optimizeResult.candidates,
        measurements: [{
          name: targetName,
          smiles: targetSmiles,
          measured_kd_nM: kdVal,
          notes: 'Wet-lab in vitro assay feedback'
        }],
        y_best_reference: optimizeResult.baseline.predicted_pkd
      });
      setFeedbackResult(res);
      // Update optimizeResult candidates with calibrated ones
      setOptimizeResult({
        ...optimizeResult,
        candidates: res.calibrated_candidates
      });
    } catch (err) {
      console.error('Failed to submit wet-lab feedback:', err);
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  // Phase 2: De Novo Pocket Generation & Retrosynthesis Route Planner states
  const [isDeNovoModalOpen, setIsDeNovoModalOpen] = useState(false);
  const [isRetroModalOpen, setIsRetroModalOpen] = useState(false);
  const [retroSmiles, setRetroSmiles] = useState('');
  const [retroMolName, setRetroMolName] = useState('先导化合物');

  const handleOpenRetrosynthesis = (smi: string, name: string) => {
    setRetroSmiles(smi);
    setRetroMolName(name);
    setIsRetroModalOpen(true);
  };

  const handleSelectDeNovoCandidate = (candidate: any) => {
    setDrugSmiles(candidate.smiles);
    setIsDeNovoModalOpen(false);
  };

  // Phase 3: Ultra-Large Virtual Screening states
  const [isScreeningModalOpen, setIsScreeningModalOpen] = useState(false);

  const handleSelectScreeningHit = (hit: any) => {
    setDrugSmiles(hit.smiles);
    setDrugDisplayName(hit.name || '海选筛选苗头分子');
    setIsScreeningModalOpen(false);
  };

  const hasLLMConfigured = Boolean(apiKey && apiKey.trim().length > 0);

  useEffect(() => {
    // Load drugs
    fetchDTIDrugs().then(data => {
      setDrugs(data);
      if (data.length > 0) {
        const dasatinib = data.find(d => d.name.toLowerCase().includes('dasatinib')) || data[0];
        setDrugSmiles(dasatinib.smiles);
        setDrugDisplayName(dasatinib.name);
      }
    }).catch(err => console.error('Fetch drugs error:', err));

    // Load targets
    fetchDTITargets().then(data => {
      setTargets(data);
      if (data.length > 0) {
        const abl1 = data.find(t => t.id.toUpperCase().includes('ABL1') || t.id.toLowerCase().includes('abl')) || data[0];
        setTargetSequence(abl1.sequence);
        setTargetName(abl1.id);
      }
    }).catch(err => console.error('Fetch targets error:', err));
  }, []);

  const handleSelectDrug = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const dId = e.target.value;
    const found = drugs.find(item => item.id === dId);
    if (found) {
      setDrugSmiles(found.smiles);
      setDrugDisplayName(found.name);
    }
  };

  const handleSelectTarget = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const tId = e.target.value;
    const found = targets.find(item => item.id === tId);
    if (found) {
      setTargetSequence(found.sequence);
      setTargetName(found.id);
    }
  };

  const applyPreset = (preset: typeof PRESET_EXAMPLES[0]) => {
    setDrugSmiles(preset.smiles);
    setDrugDisplayName(preset.drugName);
    setOptimizationGoal(preset.goal);
    setCustomInstruction(preset.instruction);
    
    const matchedTarget = targets.find(t => t.id.toUpperCase().includes(preset.targetSymbol.toUpperCase()));
    if (matchedTarget) {
      setTargetSequence(matchedTarget.sequence);
      setTargetName(matchedTarget.id);
    }
  };

  const handleRunOptimization = async () => {
    if (!drugSmiles.trim() || !targetSequence.trim()) {
      setErrorMsg('请同时提供合法的小分子 SMILES 和靶点蛋白序列。');
      return;
    }
    setErrorMsg(null);
    setIsOptimizing(true);
    setOptimizeResult(null);
    setActiveLearningReport(null);

    try {
      const payload: any = {
        drug_smiles: drugSmiles.trim(),
        target_sequence: targetSequence.trim(),
        target_name: targetName || 'Target Kinase',
        optimization_goal: optimizationGoal,
        custom_instruction: customInstruction.trim(),
        model_name: evalModel,
      };

      if (hasLLMConfigured) {
        payload.llm_config = {
          provider: llmProvider,
          api_key: apiKey,
          api_base: apiBase,
          model: modelName,
        };
      }

      const res = await optimizeLeadMolecule(payload);
      setOptimizeResult(res);

      // Auto-trigger Active Learning evaluation for all generated candidates
      if (res.candidates && res.candidates.length > 0) {
        setIsLoadingActiveLearning(true);
        evaluateActiveLearning({
          target_sequence: targetSequence.trim(),
          target_name: targetName || 'Target Kinase',
          candidates: res.candidates.map(c => ({ name: c.name, smiles: c.smiles })),
          y_best: res.baseline.predicted_pkd
        }).then(report => {
          setActiveLearningReport(report);
        }).catch(alErr => {
          console.warn('Active learning evaluation note:', alErr);
        }).finally(() => {
          setIsLoadingActiveLearning(false);
        });
      }

    } catch (err: any) {
      setErrorMsg(err.message || '优化执行失败，请检查输入格式或网络状态。');
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleCopySmiles = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handleSaveToCart = (candidate: CandidateDerivative) => {
    addToCart({
      sequence: candidate.smiles,
      name: candidate.name,
      p_amp: 0.95,
      p_hemo: 0.05,
      tsi: candidate.predicted_pkd,
    });
    setCartSuccessId(candidate.id);
    setTimeout(() => setCartSuccessId(null), 2000);
  };

  const handleExportActiveLearningCSV = () => {
    if (!activeLearningReport) return;
    const allCands: ActiveLearningCandidate[] = [
      ...activeLearningReport.confident_hits,
      ...activeLearningReport.breakthrough_hypotheses,
      ...activeLearningReport.high_information_gain_blindspots,
      ...activeLearningReport.known_inactives
    ];
    const reportEvidence = activeLearningReport.research_evidence ?? evidence.data;
    const header = csvLine(['Candidate_Name', 'SMILES', 'Mean_pKd', 'Model_Dispersion_Sigma', 'Expected_Improvement_EI', 'UCB_Score', 'Quadrant', 'Recommendation', 'Lead_Optimization_Model_ID', 'Active_Learning_Model_ID', ...EVIDENCE_CSV_HEADERS]) + '\n';
    const rows = allCands.map(c => csvLine([c.name, c.smiles, c.mean_pkd.toFixed(3), c.uncertainty_sigma.toFixed(3), c.expected_improvement.toFixed(4), c.ucb_score.toFixed(3), researchCopy(c.quadrant_label), researchCopy(c.recommendation_reason), optimizeResult?.model_used ?? 'unknown', activeLearningReport.model_used ?? 'not_reported', ...evidenceCSVValues(reportEvidence, optimizeResult?.model_used)])).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `active_learning_matrix_${targetName.replace(/\s+/g, '_')}_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyMarkdownReport = () => {
    if (!activeLearningReport) return;
    navigator.clipboard.writeText(researchCopy(activeLearningReport.markdown_summary) + evidenceMarkdown(activeLearningReport.research_evidence ?? evidence.data, optimizeResult?.model_used));
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* 顶部标题与工作机制横幅 */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-emerald-500 flex items-center justify-center text-white shadow-md">
                <Sparkles size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <span>AI 先导化合物智能改构与贝叶斯主动学习工作台</span>
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
                    Lead Optimizer Studio 2.0
                  </span>
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  生成式药化微调假说 · 注册模型计算打分 · 主动学习探索/利用候选排序
                </p>
              </div>
            </div>
          </div>

          {/* 模式状态徽章 */}
          <div className="flex items-center gap-2 self-start md:self-auto">
            {hasLLMConfigured ? (
              <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300">
                <Cpu size={16} className="text-emerald-600 dark:text-emerald-400" />
                <div className="text-left">
                  <span className="font-semibold">已连接大模型生成模式</span>
                  <span className="block text-[10px] text-emerald-600 dark:text-emerald-400 font-mono">
                    {llmProvider} ({modelName})
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800 text-xs text-sky-800 dark:text-sky-300">
                <Zap size={16} className="text-sky-600 dark:text-sky-400" />
                <div className="text-left">
                  <span className="font-semibold">内置经典药化启发式引擎</span>
                  <span className="block text-[10px] text-sky-600 dark:text-sky-400">
                    零依赖离线执行 (右上角可配置 API Key)
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 机制约束说明 */}
        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800/80 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-slate-600 dark:text-slate-400">
          <div className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 flex items-center justify-center shrink-0 font-bold font-mono text-[11px]">1</span>
            <span><strong>结构衍生物生成</strong>：基于药效团电子等排体、氟扫描、增溶侧链或 LLM 深度药化推理提出改构分子。</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 flex items-center justify-center shrink-0 font-bold font-mono text-[11px]">2</span>
            <span><strong>模型计算打分</strong>：候选分子由所选注册模型预测亲和力；历史基准表现与独立外部证据分别呈现。</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-300 flex items-center justify-center shrink-0 font-bold font-mono text-[11px]">3</span>
            <span><strong>主动学习候选排序</strong>：结合预测均值与模型分散度划分模型优先候选和探索候选，供后续实验决策参考。</span>
          </div>
        </div>
      </div>

      <DTIEvidencePanel modelId={evalModel} modelHash={registeredModels.find(model => model.id === evalModel)?.model_sha256} />

      {/* 预设经典场景快捷选择 */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-400 dark:text-slate-500 font-medium shrink-0 flex items-center gap-1.5">
          <Compass size={14} className="text-blue-500" /> 经典改构探索场景：
        </span>
        {PRESET_EXAMPLES.map((item, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => applyPreset(item)}
            className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 shrink-0 transition-colors shadow-2xs font-medium cursor-pointer focus-ring"
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* 参数配置与输入工作区 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* 左侧：母体小分子与受体激酶设定 (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-2.5">
              <FlaskConical size={16} className="text-blue-600" />
              <span>先导母体抑制剂 (Lead Mother Molecule)</span>
            </h3>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  从 DAVIS 基准抑制剂中快速选择
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsScreeningModalOpen(true)}
                    className="text-xs bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded-md flex items-center gap-1 font-semibold transition-colors cursor-pointer"
                    title="从 Enamine / 商业激酶分子库中超大规模虚拟筛选获得先导 Hits"
                  >
                    <Zap size={12} className="text-yellow-500 animate-pulse" />
                    <span>商业库海选 Hits</span>
                  </button>
                  <span className="text-[11px] text-slate-400 font-mono">共 {drugs.length} 种已注册药物</span>
                </div>
              </div>
              <select
                aria-label="从 DAVIS 基准抑制剂中快速选择"
                className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium focus-ring"
                onChange={handleSelectDrug}
                value={drugs.find(d => d.smiles === drugSmiles)?.id || ''}
              >
                <option value="">-- 选择先导抑制剂或在下方输入自定义 SMILES --</option>
                {drugs.map(d => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.id}) {d.is_test ? '· [测试集]' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  先导物 SMILES 规范表达式
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsSketcherOpen(true)}
                    className="text-xs bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30 px-2.5 py-0.5 rounded-md flex items-center gap-1 transition-colors cursor-pointer font-medium"
                  >
                    <Palette size={12} />
                    <span>打开手绘画板</span>
                  </button>
                  <span className="text-[10px] text-slate-400 font-mono">长度: {drugSmiles.length} 字符</span>
                </div>
              </div>
              <textarea
                rows={2}
                value={drugSmiles}
                onChange={e => setDrugSmiles(e.target.value)}
                placeholder="例如：CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO"
                className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 font-mono text-slate-800 dark:text-slate-200 focus-ring"
              />
            </div>

            {/* 靶点激酶 */}
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Dna size={16} className="text-indigo-600" />
                  <span>靶点激酶受体 (Target Kinase Receptor)</span>
                </h3>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setIsDeNovoModalOpen(true)}
                    className="text-xs bg-purple-500/10 hover:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30 px-2 py-0.5 rounded-md flex items-center gap-1 font-semibold transition-colors cursor-pointer"
                    title="3D 口袋从头分子扩散生成与骨架跃迁"
                  >
                    <Sparkles size={12} className="text-amber-400 animate-pulse" />
                    <span>3D 从头生成</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenRetrosynthesis(
                      drugSmiles || 'CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)C)C(F)(F)F',
                      targetName ? `${targetName} 先导化合物` : '先导化合物'
                    )}
                    className="text-xs bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-md flex items-center gap-1 font-semibold transition-colors cursor-pointer"
                    title="AI 计算机辅助逆合成路线规划"
                  >
                    <TestTube size={12} />
                    <span>逆合成规划</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsTargetModalOpen(true)}
                    className="text-xs bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-md flex items-center gap-1 font-semibold transition-colors cursor-pointer"
                    title="从 60+ 临床抗肿瘤激酶与耐药突变体知识库中选择靶点与序列"
                  >
                    <span>🏛️ 60+ 临床靶点库</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">

                <div>
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                    靶点名称 / 激酶代号
                  </label>
                  <input
                    type="text"
                    value={targetName}
                    onChange={e => setTargetName(e.target.value)}
                    placeholder="如：ABL1, EGFR, BRAF"
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200 font-medium focus-ring"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                    从 379 种 DAVIS 激酶库预选
                  </label>
                  <select
                    aria-label="从 379 种 DAVIS 激酶库预选"
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus-ring font-medium"
                    onChange={handleSelectTarget}
                    value={targets.find(t => t.id === targetName)?.id || ''}
                  >
                    <option value="">-- 选择代表性激酶靶点 --</option>
                    {targets.slice(0, 50).map(t => (
                      <option key={t.id} value={t.id}>
                        {t.id} (残基数: {t.length} AA)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    激酶全长或结构域氨基酸序列 (FASTA)
                  </label>
                  <span className="text-[10px] text-slate-400 font-mono">残基数: {targetSequence.length} AA</span>
                </div>
                <textarea
                  rows={3}
                  value={targetSequence}
                  onChange={e => setTargetSequence(e.target.value)}
                  placeholder="输入氨基酸序列..."
                  className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 font-mono text-slate-800 dark:text-slate-200 focus-ring uppercase"
                />
              </div>
            </div>

          </div>
        </div>

        {/* 右侧：改构目标与执行控制 (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-4 flex flex-col justify-between h-full">
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-2.5">
                <Sparkles size={16} className="text-amber-500" />
                <span>进化改构策略与药化约束</span>
              </h3>

              {/* 优化目标下拉 */}
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 block">
                  核心优化目标 (Optimization Goal)
                </label>
                <select
                  aria-label="核心优化目标"
                  value={optimizationGoal}
                  onChange={e => setOptimizationGoal(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium focus-ring"
                >
                  {OPTIMIZATION_GOALS.map(g => (
                    <option key={g.value} value={g.value}>{g.label}</option>
                  ))}
                </select>
              </div>

              {/* 专家指令输入框 */}
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                  自定义药化设计指令 (Custom Prompt / Instruction)
                </label>
                <textarea
                  rows={2}
                  value={customInstruction}
                  onChange={e => setCustomInstruction(e.target.value)}
                  placeholder="例如：在苯环无阻碍位点探查卤素结合；引入碱性中心；保持激酶铰链区双氢键供体-受体骨架..."
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200 focus-ring"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  {hasLLMConfigured 
                    ? '大模型将根据此指令在药效团假说下进行定向修饰与机理推导。' 
                    : '启发式引擎下将自动匹配经典药化规则库。若需自由生成请配置大模型 Key。'}
                </p>
              </div>

              {/* 评估基线模型选择 */}
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                  亲和力定量打分基准模型 (DTI Model)
                </label>
                <select
                  aria-label="亲和力定量打分基准模型"
                  value={evalModel}
                  onChange={e => setEvalModel(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium focus-ring"
                >
                  {!modelStatus.ready && <option value="">{modelStatus.label}</option>}
                  {modelStatus.ready && modelStatus.data?.map(model => <option key={model.id} value={model.id}>{model.name}{model.is_recommended ? '（服务默认）' : ''}</option>)}
                </select>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{modelStatus.message}。服务默认仅表示运行配置；外部评价状态见研究证据面板。</p>
              </div>
            </div>

            {/* 执行按钮 */}
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
              {errorMsg && (
                <div className="mb-3 p-2.5 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-400 flex items-center gap-2">
                  <AlertCircle size={15} className="shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleRunOptimization}
                disabled={isOptimizing || !modelStatus.ready || !evalModel}
                className={`w-full py-3 px-4 rounded-xl font-semibold text-xs flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer focus-ring ${
                  isOptimizing
                    ? 'bg-blue-400 text-white cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-600 hover:from-blue-700 hover:to-emerald-700 text-white hover:shadow-md active:scale-[0.99]'
                }`}
              >
                {isOptimizing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>正在进行 AI 药化改构推理与世界模型打分...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>开始智能改构与贝叶斯主动学习评估 (Run Lead Optimization)</span>
                  </>
                )}
              </button>
            </div>

          </div>
        </div>

      </div>

      {/* 结果呈现区域 */}
      {optimizeResult && (
        <div className="space-y-5 animate-in fade-in slide-in-from-bottom-3 duration-300">
          <p className="rounded-xl border border-amber-200 p-3 text-sm text-amber-900 dark:border-amber-800 dark:text-amber-200">{evidenceNotice(optimizeResult.research_evidence ?? evidence.data)} 实际打分模型：{optimizeResult.model_used}。</p>
          <DTIModelLimitations modelId={optimizeResult.model_used} evidence={optimizeResult.research_evidence ?? evidence.data} />
          
          {/* 降级警示提示条 */}
          {optimizeResult.mode === 'heuristic_fallback' && (
            <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5 shadow-xs">
              <AlertCircle size={16} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">外部大模型调用未完成，已自动降级为药化启发式专家规则生成：</span>
                <p className="mt-0.5 text-amber-800 dark:text-amber-300">
                  {optimizeResult.fallback_reason || '接口响应异常或超时，系统已自动启用标准苯环对位氟化、变构三氟甲基取代与增溶侧链规则生成候选设计。'}
                </p>
              </div>
            </div>
          )}

          {/* 母体分子基准 & KPI 指标栏 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            
            {/* 母体基准 */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  先导母体基准 (Baseline Lead)
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold font-mono text-slate-800 dark:text-slate-100">
                    {optimizeResult.baseline.predicted_pkd}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">pKd</span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-300">{PREDICTION_SCOPE_NOTICE}</p>
                <div className="text-xs text-slate-500 mt-1 font-mono">
                  换算 Kd: <strong>{optimizeResult.baseline.predicted_kd_nM} nM</strong> · {predictionScoreBand(optimizeResult.baseline.predicted_pkd)}
                </div>
                {/* SA Score Display */}
                <div className="mt-1 flex items-center gap-1.5 text-[11px] font-mono">
                  <span className="text-slate-400">SA 可达性:</span>
                  <strong className={
                    (optimizeResult.baseline.sa_score ?? computeQuickSAScore(optimizeResult.baseline.smiles).sa_score) <= 3.5
                      ? 'text-emerald-500'
                      : (optimizeResult.baseline.sa_score ?? computeQuickSAScore(optimizeResult.baseline.smiles).sa_score) <= 5.0
                      ? 'text-cyan-500'
                      : 'text-amber-500'
                  }>
                    {(optimizeResult.baseline.sa_score ?? computeQuickSAScore(optimizeResult.baseline.smiles).sa_score).toFixed(2)}
                  </strong>
                  <span className="text-[10px] text-slate-500">
                    ({optimizeResult.baseline.sa_label || computeQuickSAScore(optimizeResult.baseline.smiles).sa_label.split(' ')[0]})
                  </span>
                </div>
                {/* ADMET Health Radar Trigger */}
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => handleOpenAdmet(drugDisplayName, optimizeResult.baseline.smiles, optimizeResult.baseline.admet)}
                    className="w-full flex items-center justify-between px-2.5 py-1 rounded-lg bg-indigo-50/80 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 border border-indigo-200/80 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-[11px] font-semibold transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck size={12} className="text-indigo-600 dark:text-indigo-400" />
                      <span>ADMET 健康分:</span>
                    </span>
                    <span className="font-mono font-bold">
                      {optimizeResult.baseline.admet ? `${Math.round(optimizeResult.baseline.admet.admet_health_score)} 分` : '查看雷达'}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenRetrosynthesis(optimizeResult.baseline.smiles, drugDisplayName)}
                    className="w-full mt-1.5 flex items-center justify-between px-2.5 py-1 rounded-lg bg-emerald-50/80 dark:bg-emerald-950/40 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 border border-emerald-200/80 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-[11px] font-semibold transition-colors cursor-pointer"
                  >
                    <span className="flex items-center gap-1.5">
                      <TestTube size={12} className="text-emerald-600 dark:text-emerald-400" />
                      <span>AI 逆合成路线:</span>
                    </span>
                    <span className="font-mono font-bold">CAS 路线</span>
                  </button>
                </div>
              </div>
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono truncate max-w-[120px]">
                  {optimizeResult.baseline.domain}
                </span>
                <Molecule2DViewer smiles={drugSmiles} name={drugDisplayName} width={90} height={52} showExpandButton={true} />
              </div>
            </div>

            {/* 评估候选衍生数量 */}
            <div className="precision-card rounded-2xl p-4 shadow-sm space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-mono">
                GENERATED CANDIDATES
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-black font-mono text-sky-600 dark:text-sky-400 glow-cyan-text">
                  {optimizeResult.summary.candidates_evaluated}
                </span>
                <span className="text-xs text-slate-500 font-medium">个衍生方案</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                生成引擎: <span className="font-mono text-slate-700 dark:text-slate-300 font-bold">{optimizeResult.mode}</span>
              </div>
              <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded-md bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 font-mono border border-sky-200 dark:border-sky-800">
                评估模型: {optimizeResult.model_used}
              </span>
            </div>

            {/* 最佳改构方案 */}
            <div className="precision-card rounded-2xl p-4 shadow-sm space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-mono">
                TOP CANDIDATE SCHEME
              </span>
              <div className="text-base font-bold text-slate-900 dark:text-slate-100 truncate" title={optimizeResult.summary.best_candidate}>
                {optimizeResult.summary.best_candidate}
              </div>
              <div className="text-xs text-emerald-600 dark:text-emerald-400 font-bold mt-1 font-mono glow-emerald-text">
                模型排序对应 Kd: {optimizeResult.summary.best_kd_nM} nM
              </div>
              <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-semibold border border-emerald-200 dark:border-emerald-800">
                按模型分数排序 · 实验未确认
              </span>
            </div>

            {/* 最大亲和力增益 */}
            <div className="precision-card rounded-2xl p-4 shadow-sm space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-mono">
                MODEL SCORE CHANGE (ΔpKd)
              </span>
              <div className="flex items-baseline gap-2">
                <span className={`text-3xl font-black font-mono ${
                  optimizeResult.summary.max_affinity_gain_pkd > 0 
                    ? 'text-emerald-600 dark:text-emerald-400 glow-emerald-text' 
                    : 'text-slate-600 dark:text-slate-400'
                }`}>
                  {optimizeResult.summary.max_affinity_gain_pkd > 0 ? `+${optimizeResult.summary.max_affinity_gain_pkd}` : optimizeResult.summary.max_affinity_gain_pkd}
                </span>
                <span className="text-xs text-slate-500 font-mono">pKd</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                {optimizeResult.summary.max_affinity_gain_pkd > 0 ? (
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                    <ArrowUpRight size={13} /> 模型分数增加，实验改善未确认
                  </span>
                ) : (
                  <span className="text-slate-500 flex items-center gap-1">
                    <Minus size={13} /> 与先导母体相当
                  </span>
                )}
              </div>
              <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800/90 text-slate-600 dark:text-slate-400 font-mono border border-slate-200 dark:border-slate-700">
                靶标: {optimizeResult.target_name}
              </span>
            </div>

          </div>

          {/* 3D 激酶催化口袋微观互作观测窗 (若被用户触发展开) */}
          {showPocket3D && (
            <div className="p-4 rounded-2xl bg-slate-900 border border-slate-700/80 shadow-lg space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white flex items-center gap-2">
                  <Box size={15} className="text-purple-400" />
                  <span>3D 激酶结合口袋原子级微观互作：{active3DPair?.drugName || drugDisplayName} + {targetName}</span>
                </span>
                <button
                  type="button"
                  onClick={() => setShowPocket3D(false)}
                  className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  收起 3D 观测窗
                </button>
              </div>
              <KinasePocketViewer3D
                targetName={targetName.split(' ')[0]}
                drugName={active3DPair?.drugName || drugDisplayName}
                drugSmiles={active3DPair?.smiles || drugSmiles}
                className="w-full"
              />
            </div>
          )}

          {/* 切换展示模式：阶梯排行榜 vs 主动学习四象限矩阵 */}
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setResultViewTab('ladder')}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer focus-ring ${
                  resultViewTab === 'ladder'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
                }`}
              >
                <TrendingUp size={14} />
                <span>分子阶梯排行榜 (Ladder View)</span>
              </button>
              
              <button
                type="button"
                onClick={() => setResultViewTab('active_learning')}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer focus-ring ${
                  resultViewTab === 'active_learning'
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
                }`}
              >
                <Grid size={14} />
                <span>贝叶斯主动学习探索/利用矩阵 (Active Learning Matrix)</span>
                {isLoadingActiveLearning && (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setShowFeedbackPanel(!showFeedbackPanel)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer focus-ring transition-colors ${
                  showFeedbackPanel 
                    ? 'bg-indigo-600 text-white' 
                    : 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100'
                }`}
              >
                <RefreshCw size={13} className={feedbackResult ? 'text-emerald-400' : ''} />
                <span>{feedbackResult ? '已完成湿法校准' : '湿实验数据回流'}</span>
              </button>
              <button
                type="button"
                onClick={handleOpenDispatch}
                className="px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 text-xs font-semibold flex items-center gap-1.5 cursor-pointer focus-ring transition-colors"
                title="生成并导出 96 孔板布局与液体处理机 (Echo/Tecan) 清单"
              >
                <Grid size={13} />
                <span>96 孔板投产清单</span>
              </button>
              <button
                type="button"
                onClick={handleOpenReport}
                className="px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 text-xs font-semibold flex items-center gap-1.5 cursor-pointer focus-ring transition-colors"
                title="生成学术研究报告全文及马库什专利通式交底书"
              >
                <FileText size={13} />
                <span>生成学术交付报告</span>
              </button>
              {resultViewTab === 'active_learning' && activeLearningReport && (
                <>
                  <button
                    type="button"
                    onClick={handleExportActiveLearningCSV}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 cursor-pointer focus-ring"
                  >
                    <Download size={13} />
                    <span>导出验证清单 (CSV)</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleCopyMarkdownReport}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 cursor-pointer focus-ring"
                  >
                    {copiedReport ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                    <span>{copiedReport ? '已复制报告' : '复制学术总结'}</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* 湿实验实测数据回流与模型重校准面板 */}
          {showFeedbackPanel && (
            <div className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/40 dark:bg-slate-900/80 space-y-3 animate-in fade-in duration-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <RefreshCw size={15} className={`text-indigo-600 ${feedbackSubmitting ? 'animate-spin' : ''}`} />
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    湿实验生化测定数据回流与先导物局部空间经验贝叶斯重校准
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={() => setShowFeedbackPanel(false)}
                  className="text-xs text-slate-400 hover:text-slate-600 cursor-pointer"
                >
                  收起
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <span className="text-slate-600 dark:text-slate-300">
                  选定实测分子: <strong className="text-slate-900 dark:text-slate-100">{optimizeResult.candidates[0]?.name}</strong>
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="text-slate-500">实测 Kd (nM):</span>
                  <input
                    type="number"
                    step="0.1"
                    value={inputMeasuredKd}
                    onChange={e => setInputMeasuredKd(e.target.value)}
                    className="w-24 px-2 py-1 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded text-xs font-mono text-slate-900 dark:text-slate-100"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => setInputMeasuredKd('12.0')}
                  className="px-2.5 py-1 rounded bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-[11px] font-medium transition-colors cursor-pointer"
                >
                  填入模拟实测 12.0 nM
                </button>
                <button
                  type="button"
                  onClick={() => handleSubmitFeedback()}
                  disabled={feedbackSubmitting}
                  className="px-3.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg text-xs shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer focus-ring"
                >
                  {feedbackSubmitting ? '正在贝叶斯重校准...' : '提交实测数据并重排阶梯榜'}
                </button>
              </div>
              {feedbackResult && (
                <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-[11px] text-emerald-800 dark:text-emerald-200 font-medium leading-relaxed">
                  ✓ {feedbackResult.narrative}
                </div>
              )}
            </div>
          )}

          {/* TAB 1: 候选分子改构阶梯呈现列表 */}
          {resultViewTab === 'ladder' && (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <TrendingUp size={18} className="text-blue-600" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    改构衍生分子阶梯排行榜 (Molecular Evolution Ladder)
                  </h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">按模型 pKd 分数排序，实验活性未确认</span>
              </div>

              <div className="space-y-3">
                {optimizeResult.candidates.map((cand, idx) => {
                  const isBest = idx === 0 && cand.delta_pkd > 0;
                  const dl = computeDrugLikeness(cand.smiles);

                  return (
                    <div
                      key={cand.id}
                      className={`p-4 rounded-xl border transition-all ${
                        isBest 
                          ? 'border-emerald-300 dark:border-emerald-800 bg-emerald-50/20 dark:bg-emerald-950/10 shadow-xs'
                          : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:border-slate-300 dark:hover:border-slate-700'
                      }`}
                    >
                      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                        {/* 1. 左侧：方案信息、机理与成药性评估 */}
                        <div className="space-y-2.5 flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`w-6 h-6 rounded-md flex items-center justify-center font-mono font-bold text-xs ${
                              isBest 
                                ? 'bg-emerald-600 text-white' 
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                            }`}>
                              #{idx + 1}
                            </span>
                            <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                              {cand.name}
                            </h4>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-medium">
                              {cand.modification_type}
                            </span>
                            {cand.is_experimentally_verified && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-600 text-white font-bold flex items-center gap-1 shadow-2xs">
                                <CheckCircle2 size={11} /> 湿实验已测定 (Verified)
                              </span>
                            )}
                            {cand.rank_shift !== undefined && cand.rank_shift > 0 && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 font-bold flex items-center gap-0.5 font-mono">
                                ↑ 排名上升 {cand.rank_shift} 位
                              </span>
                            )}
                            {isBest && (
                              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 font-semibold flex items-center gap-1">
                                <Sparkles size={11} /> 最优演进方案
                              </span>
                            )}
                          </div>

                          {/* 药效团与机理阐述 */}
                          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-100 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                            <strong className="text-slate-900 dark:text-slate-200 block mb-0.5 text-[11px] font-semibold">
                              🔬 药化改构依据与空间互作假说：
                            </strong>
                            {cand.rationale}
                          </div>

                          {/* 成药性指标 (Lipinski Rule of 5) 与合成可达性 (SA Score) 诊断条 */}
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 p-2 rounded-lg bg-slate-50/60 dark:bg-slate-950/40 border border-slate-100 dark:border-slate-800/80 text-[11px] font-mono text-slate-600 dark:text-slate-400">
                            <span>MW: <strong className="text-slate-800 dark:text-slate-200">{dl.mw}</strong> g/mol</span>
                            <span>LogP: <strong className="text-slate-800 dark:text-slate-200">{dl.logp}</strong></span>
                            <span>TPSA: <strong className="text-slate-800 dark:text-slate-200">{dl.tpsa}</strong> Å²</span>
                            <span>HBD/HBA: <strong className="text-slate-800 dark:text-slate-200">{dl.hbd}/{dl.hba}</strong></span>
                            <span>
                              SA 可达性: <strong className={
                                (cand.sa_score ?? computeQuickSAScore(cand.smiles).sa_score) <= 3.5
                                  ? 'text-emerald-500'
                                  : (cand.sa_score ?? computeQuickSAScore(cand.smiles).sa_score) <= 5.0
                                  ? 'text-cyan-500'
                                  : 'text-amber-500'
                              }>
                                {(cand.sa_score ?? computeQuickSAScore(cand.smiles).sa_score).toFixed(2)}
                              </strong>
                            </span>
                            <span className={`text-[10px] px-1.5 py-0.2 rounded font-sans font-medium border ${
                              (cand.sa_tier || computeQuickSAScore(cand.smiles).sa_tier) === 'easy'
                                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                                : (cand.sa_tier || computeQuickSAScore(cand.smiles).sa_tier) === 'moderate'
                                ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                                : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                            }`}>
                              {cand.sa_label || computeQuickSAScore(cand.smiles).sa_label}
                            </span>
                            {cand.admet && (
                              <button
                                type="button"
                                onClick={() => handleOpenAdmet(cand.name, cand.smiles, cand.admet)}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-sans text-[10px] font-bold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 transition-colors cursor-pointer"
                              >
                                <ShieldCheck size={11} className="text-indigo-500" />
                                <span>ADMET: {Math.round(cand.admet.admet_health_score)}分 ({cand.admet.herg_risk === 'low' ? '心脏安全' : '中度预警'})</span>
                              </button>
                            )}
                          </div>

                          {/* SMILES 代码与复制 */}
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-slate-100 dark:bg-slate-950 rounded px-2.5 py-1.5 font-mono text-[11px] text-slate-600 dark:text-slate-300 truncate">
                              {cand.smiles}
                            </div>
                            <button
                              type="button"
                              onClick={() => handleCopySmiles(cand.id, cand.smiles)}
                              className="p-1.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors shrink-0 text-xs flex items-center gap-1 cursor-pointer focus-ring"
                              title="复制 SMILES 字符串"
                            >
                              {copiedId === cand.id ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
                              <span className="text-[10px]">{copiedId === cand.id ? '已复制' : '复制'}</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleOpenAdmet(cand.name, cand.smiles, cand.admet)}
                              className="p-1.5 rounded bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 transition-colors shrink-0 text-xs flex items-center gap-1 font-medium cursor-pointer focus-ring"
                              title="查看成药性雷达图与多维 ADMET 药代毒理评估"
                            >
                              <ShieldCheck size={14} />
                              <span className="text-[10px]">成药雷达</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setActive3DPair({ drugName: cand.name, smiles: cand.smiles });
                                setShowPocket3D(true);
                              }}
                              className="p-1.5 rounded bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 hover:bg-purple-100 dark:hover:bg-purple-900/60 text-purple-700 dark:text-purple-300 transition-colors shrink-0 text-xs flex items-center gap-1 font-medium cursor-pointer focus-ring"
                              title="观测候选物与靶点激酶催化口袋的 3D 微观构象"
                            >
                              <Box size={14} />
                              <span className="text-[10px]">3D 口袋</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleOpenRetrosynthesis(cand.smiles, cand.name)}
                              className="p-1.5 rounded bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 transition-colors shrink-0 text-xs flex items-center gap-1 font-medium cursor-pointer focus-ring"
                              title="AI 计算机辅助逆合成路线规划 (CAS 原料、工艺条件与收率)"
                            >
                              <TestTube size={14} />
                              <span className="text-[10px]">逆合成</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleSaveToCart(cand)}
                              className="p-1.5 rounded bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/60 text-blue-700 dark:text-blue-300 transition-colors shrink-0 text-xs flex items-center gap-1 font-medium cursor-pointer focus-ring"
                              title="存入候选分子暂存库"
                            >
                              {cartSuccessId === cand.id ? <Check size={14} className="text-emerald-600" /> : <PlusCircle size={14} />}
                              <span className="text-[10px]">{cartSuccessId === cand.id ? '已存入' : '存入分子库'}</span>
                            </button>
                          </div>
                        </div>

                        {/* 2. 中间：2D 骨架拓扑结构图 */}
                        <div className="shrink-0 flex items-center justify-center self-center lg:self-stretch">
                          <Molecule2DViewer smiles={cand.smiles} name={cand.name} width={170} height={110} />
                        </div>

                        {/* 3. 右侧：定量指标与亲和力增益 */}
                        <div className="flex lg:flex-col items-center lg:items-end justify-between lg:justify-center border-t lg:border-t-0 lg:border-l border-slate-100 dark:border-slate-800 pt-3 lg:pt-0 lg:pl-4 min-w-[150px]">
                          <div className="text-left lg:text-right">
                            {cand.calibrated_pkd !== undefined ? (
                              <>
                                <span className="text-[10px] text-indigo-500 uppercase font-mono block font-bold">反馈更新 pKd</span>
                                <span className="text-xl font-black font-mono text-indigo-600 dark:text-indigo-400">
                                  {cand.calibrated_pkd}
                                </span>
                                <span className="block text-xs font-mono text-slate-500">
                                  换算 Kd: <strong>{cand.calibrated_kd_nM} nM</strong> (原分数 {cand.predicted_pkd})
                                </span>
                              </>
                            ) : (
                              <>
                                <span className="text-[10px] text-slate-400 uppercase font-mono block">模型分数 pKd</span>
                                <span className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100">
                                  {cand.predicted_pkd}
                                </span>
                                <span className="block text-xs font-mono text-slate-500">
                                  换算 Kd: <strong>{cand.predicted_kd_nM} nM</strong>
                                </span>
                              </>
                            )}
                          </div>

                          <div className="text-right mt-2">
                            <div className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold font-mono ${
                              cand.status_code === 'improved'
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                : cand.status_code === 'decreased'
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                                : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                            }`}>
                              {cand.status_code === 'improved' && <ArrowUpRight size={13} />}
                              {cand.status_code === 'decreased' && <ArrowDownRight size={13} />}
                              {cand.status_code === 'neutral' && <Minus size={13} />}
                              <span>{cand.delta_pkd > 0 ? `+${cand.delta_pkd}` : cand.delta_pkd} pKd</span>
                            </div>
                            <span className="block text-[10px] text-slate-400 mt-0.5">
                              模型分数变化 · 换算比 {cand.fold_change}x
                            </span>
                          </div>

                          <div className="text-right mt-2">
                            <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                              cand.predicted_pkd >= 7
                                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                                : 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                            }`}>
                              预测分数区间：{predictionScoreBand(cand.predicted_pkd)}
                            </span>
                          </div>
                        </div>

                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 2: 主动学习四象限探索/利用矩阵 */}
          {resultViewTab === 'active_learning' && (
            <div className="space-y-4">
              {activeLearningReport ? (
                <div className="space-y-4">
                  {/* 四象限概览卡片 */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
                    
                    {/* Q1: 高置信度领头物 */}
                    <div className="p-4 rounded-xl border border-emerald-300 dark:border-emerald-700/60 bg-gradient-to-br from-emerald-50/80 via-white to-emerald-50/30 dark:from-emerald-950/40 dark:via-slate-900/60 dark:to-slate-950/80 space-y-2 shadow-2xs relative overflow-hidden">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                          <Check size={14} className="text-emerald-600 dark:text-emerald-400" />
                          模型优先候选 (Hits)
                        </span>
                        <span className="px-2 py-0.5 rounded-md text-xs font-bold bg-emerald-600 text-white font-mono shadow-xs">
                          {activeLearningReport.confident_hits.length}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                        高预测均值 μ + 低模型分散度 σ。可优先考虑实验核查，尚未确认实际结合效果。
                      </p>
                    </div>

                    {/* Q2: 突破假说 */}
                    <div className="p-4 rounded-xl border border-sky-300 dark:border-sky-700/60 bg-gradient-to-br from-sky-50/80 via-white to-sky-50/30 dark:from-sky-950/40 dark:via-slate-900/60 dark:to-slate-950/80 space-y-2 shadow-2xs relative overflow-hidden">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-sky-800 dark:text-sky-300 flex items-center gap-1.5">
                          <Sparkles size={14} className="text-sky-600 dark:text-sky-400" />
                          突破假说 (Breakthrough)
                        </span>
                        <span className="px-2 py-0.5 rounded-md text-xs font-bold bg-sky-600 text-white font-mono shadow-xs">
                          {activeLearningReport.breakthrough_hypotheses.length}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                        高计算期望提升 (Top EI)。适合作为探索假说，仍需确认结构可行性与实验亲和力。
                      </p>
                    </div>

                    {/* Q3: 认知盲区 */}
                    <div className="p-4 rounded-xl border border-amber-300 dark:border-amber-700/60 bg-gradient-to-br from-amber-50/80 via-white to-amber-50/30 dark:from-amber-950/40 dark:via-slate-900/60 dark:to-slate-950/80 space-y-2 shadow-2xs relative overflow-hidden">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                          <HelpCircle size={14} className="text-amber-600 dark:text-amber-400" />
                          认知盲区 (High-Info)
                        </span>
                        <span className="px-2 py-0.5 rounded-md text-xs font-bold bg-amber-500 text-slate-950 font-mono font-bold shadow-xs">
                          {activeLearningReport.high_information_gain_blindspots.length}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                        高模型分散度 σ。可考虑补充实验数据，探索模型判断差异较大的区域。
                      </p>
                    </div>

                    {/* Q4: 确定性无效物 */}
                    <div className="p-4 rounded-xl border border-slate-300 dark:border-slate-750 bg-gradient-to-br from-slate-100/80 via-white to-slate-50/30 dark:from-slate-900/80 dark:via-slate-900/40 dark:to-slate-950/80 space-y-2 shadow-2xs relative overflow-hidden">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                          <Minus size={14} className="text-slate-400" />
                          模型低优先候选 (Low Priority)
                        </span>
                        <span className="px-2 py-0.5 rounded-md text-xs font-bold bg-slate-500 text-white font-mono shadow-xs">
                          {activeLearningReport.known_inactives.length}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                        低预测均值 μ + 低模型分散度 σ。当前模型排序较低，实际活性仍需实验判断。
                      </p>
                    </div>

                  </div>

                  {/* 候选分子四象限决策明细表 */}
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                      <div>
                        <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                          <Grid size={16} className="text-emerald-600" />
                          贝叶斯获取函数评分与象限排布
                        </h4>
                        <p className="text-xs text-slate-500 mt-0.5">
                          当前参考最优母体基准 y* (y_best) = {activeLearningReport.y_best_reference.toFixed(3)} pKd
                        </p>
                      </div>
                      <span className="text-xs text-slate-400 font-mono">
                        共评估 {activeLearningReport.total_evaluated} 个分子
                      </span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                            <th className="p-3 font-bold">候选分子名称</th>
                            <th className="p-3 font-bold">象限分类</th>
                            <th className="p-3 font-bold">预测均值 (μ)</th>
                            <th className="p-3 font-bold">模型分散度 (σ)</th>
                            <th className="p-3 font-bold text-blue-600 dark:text-blue-400">期望提升 (EI)</th>
                            <th className="p-3 font-bold">UCB 上界得分</th>
                            <th className="p-3 font-bold text-emerald-600 dark:text-emerald-400">SA 合成可达性</th>
                            <th className="p-3 font-bold">湿实验推荐理由</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                          {[
                            ...activeLearningReport.confident_hits,
                            ...activeLearningReport.breakthrough_hypotheses,
                            ...activeLearningReport.high_information_gain_blindspots,
                            ...activeLearningReport.known_inactives
                          ].map((cand, cIdx) => (
                            <tr key={cIdx} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                              <td className="p-3">
                                <div className="font-bold text-slate-900 dark:text-slate-100">{cand.name}</div>
                                <div className="font-mono text-[10px] text-slate-400 truncate max-w-[200px]">{cand.smiles}</div>
                              </td>
                              <td className="p-3">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                  cand.quadrant === 'confident_hits'
                                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                                    : cand.quadrant === 'breakthrough_hypotheses'
                                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                                    : cand.quadrant === 'high_uncertainty_exploration'
                                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                                    : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                                }`}>
                                  {researchCopy(cand.quadrant_label)}
                                </span>
                              </td>
                              <td className="p-3 font-mono font-bold text-slate-800 dark:text-slate-200">
                                {cand.mean_pkd.toFixed(3)}
                              </td>
                              <td className="p-3 font-mono text-slate-500">
                                ±{cand.uncertainty_sigma.toFixed(3)}
                              </td>
                              <td className="p-3 font-mono text-blue-600 dark:text-blue-400 font-bold">
                                {cand.expected_improvement.toFixed(4)}
                              </td>
                              <td className="p-3 font-mono font-medium">
                                {cand.ucb_score.toFixed(3)}
                              </td>
                              <td className="p-3 font-mono">
                                <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                                  (cand.sa_tier || computeQuickSAScore(cand.smiles).sa_tier) === 'easy'
                                    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                                    : (cand.sa_tier || computeQuickSAScore(cand.smiles).sa_tier) === 'moderate'
                                    ? 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/30'
                                    : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30'
                                }`}>
                                  {(cand.sa_score ?? computeQuickSAScore(cand.smiles).sa_score).toFixed(2)}
                                </span>
                              </td>
                              <td className="p-3 text-[11px] text-slate-600 dark:text-slate-400 max-w-xs">
                                {researchCopy(cand.recommendation_reason)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center text-xs text-slate-400 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900">
                  <Grid size={36} className="mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                  <span>正在计算主动学习获取函数或暂无分子数据...</span>
                </div>
              )}
            </div>
          )}

        </div>
      )}

      {/* 底部科学自律声明 */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/30 text-xs text-slate-500 dark:text-slate-400 space-y-1">
        <div className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300">
          <Info size={14} className="text-blue-500" />
          <span>科学自律与贝叶斯主动学习声明</span>
        </div>
        <p className="leading-relaxed">
          本工作台提供计算辅助设计。改构假说由药化启发式引擎或用户配置的大模型生成，亲和力由注册模型预测；实际模型以结果记录为准。主动学习排序仅供实验候选选择参考，模型分散度不等同于实验验证的置信区间。{evidenceNotice(evidence.data)}
        </p>
      </div>

      {/* 分子结构手绘画板模态框 */}
      <MoleculeSketcherModal
        isOpen={isSketcherOpen}
        onClose={() => setIsSketcherOpen(false)}
        initialSmiles={drugSmiles}
        onApply={(s) => {
          setDrugSmiles(s);
          setDrugDisplayName('自定义手绘分子');
        }}
        title="先导物分子手绘画板"
      />

      {/* 多维成药性与 ADMET 药代毒理评估雷达模态框 */}
      <ADMETRadarModal
        isOpen={admetModalOpen}
        onClose={() => setAdmetModalOpen(false)}
        admet={currentAdmet}
        moleculeName={currentAdmetName}
        loading={admetLoading}
      />

      {/* 湿实验 96 孔板投产清单与移液规程模态框 */}
      <WetlabDispatchModal
        isOpen={dispatchModalOpen}
        onClose={() => setDispatchModalOpen(false)}
        dispatchResult={dispatchResult}
        loading={dispatchLoading}
      />

      {/* 学术交付评估报告与专利交底书生成模态框 */}
      <AcademicReportModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        reportData={reportData}
        loading={reportLoading}
      />

      {/* 60+ 临床抗肿瘤激酶与耐药突变体知识库模态框 */}
      <ClinicalTargetSelectorModal
        isOpen={isTargetModalOpen}
        onClose={() => setIsTargetModalOpen(false)}
        onSelectTarget={(rec) => {
          setTargetName(rec.symbol);
          setTargetSequence(rec.catalytic_sequence_snippet);
        }}
        currentTargetSymbol={targetName}
      />

      {/* Phase 2: 3D 口袋从头分子扩散生成与骨架跃迁模态框 */}
      <DeNovoPocketGeneratorModal
        isOpen={isDeNovoModalOpen}
        onClose={() => setIsDeNovoModalOpen(false)}
        initialTargetSymbol={targetName}
        onViewRetrosynthesis={handleOpenRetrosynthesis}
        onSelectCandidate={handleSelectDeNovoCandidate}
      />

      {/* Phase 2: AI 计算机辅助逆合成路线规划模态框 */}
      <RetrosynthesisModal
        isOpen={isRetroModalOpen}
        onClose={() => setIsRetroModalOpen(false)}
        smiles={retroSmiles}
        moleculeName={retroMolName}
      />

      {/* Phase 3: 超大规模虚拟筛选引擎与商业分子库海选模态框 */}
      <VirtualScreeningModal
        isOpen={isScreeningModalOpen}
        onClose={() => setIsScreeningModalOpen(false)}
        initialTargetSymbol={targetName}
        onViewRetrosynthesis={handleOpenRetrosynthesis}
        onSelectLead={handleSelectScreeningHit}
      />
    </div>
  );

}
