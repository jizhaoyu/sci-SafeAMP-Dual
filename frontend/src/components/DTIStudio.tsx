import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  FlaskConical, 
  BarChart3,
  Layers,
  Atom,
  Activity,
  Flame,
  Download,
  ChevronDown,
  ChevronUp,
  Award,
  Palette,
  TestTube,
  Zap,
  Search,
  Filter,
  Dna
} from 'lucide-react';
import { 
  fetchDTIDrugs, 
  fetchDTITargets, 
  fetchDTIModels, 
  predictDTIAffinity, 
  profileKinasePanel,
  fetchBiophysicsInsights,
  fetchADMETProperties,
  type DTIDrug, 
  type DTITarget, 
  type DTIModelMeta,
  type DTIPredictionResult,
  type KinomeProfileItem,
  type BiophysicsInsights,
  type ADMETProperties,
  type ClinicalTargetRecord
} from '../api/dtiClient';
import { errorMessage } from '../api/client';
import { DTIEvidencePanel } from './DTIEvidencePanel';
import { useDTIEvidenceStatus, evidenceNotice, modelLimitationNotice, predictionScoreBand, PREDICTION_SCOPE_NOTICE, EVIDENCE_CSV_HEADERS, evidenceCSVValues, csvLine } from '../api/dtiEvidence';
import { DTIModelLimitations } from './DTIModelLimitations';
import { Molecule2DViewer } from './Molecule2DViewer';
import { KinasePocketViewer3D } from './KinasePocketViewer3D';
import { MoleculeSketcherModal } from './MoleculeSketcherModal';
import { ADMETRadarModal } from './ADMETRadarModal';
import { ClinicalTargetSelectorModal } from './ClinicalTargetSelectorModal';
import { DeNovoPocketGeneratorModal } from './DeNovoPocketGeneratorModal';
import { RetrosynthesisModal } from './RetrosynthesisModal';
import { VirtualScreeningModal } from './VirtualScreeningModal';

interface PresetPairItem {
  label: string;
  drugName: string;
  targetId: string | null;
  targetName: string;
  smiles: string;
  desc: string;
  category: 'leukemia' | 'lung' | 'melanoma' | 'lymphoma' | 'cycle';
  categoryLabel: string;
  badge: string;
  isAvailable: boolean;
  unavailableReason?: string;
}

const PRESET_PAIRS: PresetPairItem[] = [
  {
    label: '达沙替尼 → ABL1p (慢粒激酶催化态)',
    drugName: 'Dasatinib',
    targetId: 'ABL1p',
    targetName: 'ABL1 (Gene-Max)',
    smiles: 'CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO',
    desc: 'DAVIS 基准 ABL1 基因级最强亲和力参考配对（输入为全长野生型参考序列）',
    category: 'leukemia',
    categoryLabel: '白血病/慢粒催化态',
    badge: 'Gene-Max 基准',
    isAvailable: true
  },
  {
    label: '普纳替尼 → ABL1-T315I (超级耐药突变)',
    drugName: 'Ponatinib',
    targetId: null,
    targetName: 'ABL1-T315I',
    smiles: 'CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)C)C(F)(F)F',
    desc: '克服 T315I 门控位阻的新一代抑制剂 (DAVIS 基准集未收录该突变全长，暂不可运行基准预测)',
    category: 'leukemia',
    categoryLabel: '白血病/超级耐药',
    badge: '基准未收录',
    isAvailable: false,
    unavailableReason: 'DAVIS 基准目录中未包含 ABL1-T315I 全长测定记录，暂不可直接运行基准预测。'
  },
  {
    label: '奥希替尼 → EGFR-T790M (一代耐药门控突变)',
    drugName: 'Osimertinib',
    targetId: 'EGFR(T790M)',
    targetName: 'EGFR (Gene-Max)',
    smiles: 'CN1CCN(CC1)C2=CC(=C(C=C2)NC(=O)C=C)NC3=NC=CC(=N3)C4=CN(C5=CC=CC=C54)C',
    desc: 'DAVIS 基准 EGFR 基因级最强亲和力参考配对（输入为全长野生型参考序列，不区分 T790M 突变位移）',
    category: 'lung',
    categoryLabel: '肺癌/三代耐药',
    badge: 'Gene-Max 基准',
    isAvailable: true
  },
  {
    label: '吉非替尼 → EGFR (野生型)',
    drugName: 'Gefitinib',
    targetId: null,
    targetName: 'EGFR',
    smiles: 'COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4',
    desc: '第一代经典 EGFR 抑制剂 (DAVIS 基准集未收录野生型全长，仅收录 T790M)',
    category: 'lung',
    categoryLabel: '肺癌/一代经典',
    badge: '基准未收录',
    isAvailable: false,
    unavailableReason: 'DAVIS 基准目录未收录野生型 EGFR 全长序列，暂不可直接运行基准预测。'
  },
  {
    label: '洛拉替尼 → ALK-G1202R (溶剂前沿耐药突变)',
    drugName: 'Lorlatinib',
    targetId: null,
    targetName: 'ALK-G1202R',
    smiles: 'CC1CC2=C(C=CC(=C2)F)OCC(N3CCC(C3=O)N1)C4=CC=C(C=N4)C#N',
    desc: '大环第三代 ALK 抑制剂 (DAVIS 基准集未收录 G1202R 突变记录)',
    category: 'lung',
    categoryLabel: '肺癌/溶剂前沿',
    badge: '基准未收录',
    isAvailable: false,
    unavailableReason: 'DAVIS 基准目录未收录 ALK-G1202R 突变记录，暂不可直接运行基准预测。'
  },
  {
    label: '吡妥布替尼 → BTK-C481S (共价耐药突变)',
    drugName: 'Pirtobrutinib',
    targetId: null,
    targetName: 'BTK-C481S',
    smiles: 'CC(C)NC(=O)C1=CC(=C(C=C1)F)NC2=NC=C(C(=N2)C3=CC=CC=C3)C4=CC=C(C=C4)F',
    desc: '非共价可逆 BTK 抑制剂 (DAVIS 基准集未收录 C481S 突变记录)',
    category: 'lymphoma',
    categoryLabel: '淋巴瘤/可逆抑制',
    badge: '基准未收录',
    isAvailable: false,
    unavailableReason: 'DAVIS 基准目录未收录 BTK-C481S 突变记录，暂不可直接运行基准预测。'
  },
  {
    label: '维莫非尼 → BRAF-V600E (恶性黑色素瘤驱动)',
    drugName: 'Vemurafenib',
    targetId: 'BRAF(V600E)',
    targetName: 'BRAF (Gene-Max)',
    smiles: 'CCCS(=O)(=O)NC1=C(C(=C(C=C1)F)C(=O)C2=CNC3=C2C=C(C=N3)C4=CC=C(C=C4)Cl)F',
    desc: 'DAVIS 基准 BRAF 基因级最强亲和力参考配对（输入为全长野生型参考序列，不区分 V600E 突变特异性）',
    category: 'melanoma',
    categoryLabel: '黑色素瘤/变构',
    badge: 'Gene-Max 基准',
    isAvailable: true
  },
  {
    label: '帕博西尼 → CDK4 (细胞周期核心靶点)',
    drugName: 'Palbociclib',
    targetId: 'CDK4-cyclinD3',
    targetName: 'CDK4-cyclinD3',
    smiles: 'CC1=C(C(=O)N(C2=NC(=NC=C12)NC3=NC=C(C=C3)N4CCNCC4)C5CCCC5)C(=O)C',
    desc: '高选择性 CDK4/6 抑制剂，对应 DAVIS 基准集 CDK4-cyclinD3',
    category: 'cycle',
    categoryLabel: '乳腺癌/细胞周期',
    badge: 'CDK4/6 阻滞',
    isAvailable: true
  }
];

const POPULAR_DRUGS = [
  { name: 'Dasatinib', label: '达沙替尼 (ABL1)' },
  { name: 'Gefitinib', label: '吉非替尼 (EGFR)' },
  { name: 'Imatinib', label: '伊马替尼 (BCR-ABL)' },
  { name: 'Sorafenib', label: '索拉非尼 (BRAF)' },
  { name: 'Erlotinib', label: '厄洛替尼 (EGFR)' },
  { name: 'Lapatinib', label: '拉帕替尼 (HER2)' },
  { name: 'Sunitinib', label: '舒尼替尼 (VEGFR)' },
  { name: 'Bosutinib', label: '博舒替尼 (SRC)' },
];

const POPULAR_TARGETS = [
  { symbol: 'ABL1', label: 'ABL1 (慢粒白血病)' },
  { symbol: 'EGFR', label: 'EGFR (肺腺癌)' },
  { symbol: 'BRAF', label: 'BRAF (黑色素瘤)' },
  { symbol: 'SRC', label: 'SRC (原癌基因)' },
  { symbol: 'KIT', label: 'KIT (胃肠间质瘤)' },
  { symbol: 'FLT3', label: 'FLT3 (急性髓系白血病)' },
  { symbol: 'MET', label: 'MET (肝癌/肺癌旁路耐药)' },
  { symbol: 'KDR', label: 'KDR/VEGFR2 (血管新生)' },
];


export default function DTIStudio() {
  const evidence = useDTIEvidenceStatus();
  const [drugs, setDrugs] = useState<DTIDrug[]>([]);
  const [targets, setTargets] = useState<DTITarget[]>([]);
  const [models, setModels] = useState<DTIModelMeta[]>([]);
  const [modelsLoading, setModelsLoading] = useState<boolean>(true);
  const [modelsError, setModelsError] = useState<string | null>(null);
  
  // Selection / Input states
  const [selectedDrugId, setSelectedDrugId] = useState<string>('');
  const [drugSmiles, setDrugSmiles] = useState<string>('');
  const [selectedTargetId, setSelectedTargetId] = useState<string>('');
  const [targetSequence, setTargetSequence] = useState<string>('');
  const [modelName, setModelName] = useState<string>('');
  const [show2DStructure, setShow2DStructure] = useState<boolean>(true);
  const [isSketcherOpen, setIsSketcherOpen] = useState<boolean>(false);

  // User interaction tracking to prevent async catalog fetch from overwriting user selections
  const userDrugInteractedRef = useRef<boolean>(false);
  const userTargetInteractedRef = useRef<boolean>(false);
  const pendingPresetTargetIdRef = useRef<string | null>(null);

  // Search & Filter expansion states
  const [presetCategory, setPresetCategory] = useState<string>('all');
  const [drugSearchQuery, setDrugSearchQuery] = useState<string>('');
  const [drugFoldFilter, setDrugFoldFilter] = useState<'all' | 'known' | 'test'>('all');
  const [targetSearchQuery, setTargetSearchQuery] = useState<string>('');
  const [targetFamilyFilter, setTargetFamilyFilter] = useState<string>('all');
  const [showAllPresets, setShowAllPresets] = useState<boolean>(false);
  const [showModelConfig, setShowModelConfig] = useState<boolean>(false);

  const filteredPresets = useMemo(() => {
    if (presetCategory === 'all') return PRESET_PAIRS;
    return PRESET_PAIRS.filter(p => p.category === presetCategory);
  }, [presetCategory]);

  const filteredDrugs = useMemo(() => {
    return drugs.filter(d => {
      if (drugFoldFilter === 'known' && d.is_test) return false;
      if (drugFoldFilter === 'test' && !d.is_test) return false;
      if (!drugSearchQuery.trim()) return true;
      const q = drugSearchQuery.toLowerCase().trim();
      return d.name.toLowerCase().includes(q) || d.id.toLowerCase().includes(q);
    });
  }, [drugs, drugFoldFilter, drugSearchQuery]);

  const filteredTargets = useMemo(() => {
    return targets.filter(t => {
      const sym = ((t as any).gene_symbol || t.id).toUpperCase();
      if (targetFamilyFilter === 'TK' && !sym.match(/^(ABL|EGFR|KIT|FLT|MET|KDR|SRC|JAK|FGFR|PDGFR|RET|ALK|ROS|NTRK|TEK|TIE|BTK|ITK|YES|FYN|LYN|LCK|HCK|FGR|BLK|CSK|SYK|ZAP|EPH|DDR|AXL|MER|TYRO)/)) return false;
      if (targetFamilyFilter === 'STE' && !sym.match(/^(MAP|PAK|SLK|STK|TAOK|YSK|MST|OXSR)/)) return false;
      if (targetFamilyFilter === 'AGC' && !sym.match(/^(AKT|PKA|PKC|PKG|ROCK|SGK|GRK|DMPK|RPS6|PRKX)/)) return false;
      if (targetFamilyFilter === 'CAMK' && !sym.match(/^(CAMK|CHEK|CHK|DAPK|MARK|MELK|NIM|PIM|SNF|TSSK|BRSK)/)) return false;
      if (targetFamilyFilter === 'TKL' && !sym.match(/^(BRAF|RAF|LRRK|IRAK|RIPK|MLK|TAK|ILK)/)) return false;
      if (!targetSearchQuery.trim()) return true;
      const q = targetSearchQuery.toLowerCase().trim();
      return t.id.toLowerCase().includes(q) || sym.toLowerCase().includes(q);
    });
  }, [targets, targetFamilyFilter, targetSearchQuery]);
  
  // Loading & Result states
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isProfiling, setIsProfiling] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<DTIPredictionResult | null>(null);
  const [profileModelName, setProfileModelName] = useState('');
  const [biophysicsInsights, setBiophysicsInsights] = useState<BiophysicsInsights | null>(null);
  const [profileResults, setProfileResults] = useState<KinomeProfileItem[] | null>(null);
  const [activeTab, setActiveTab] = useState<'predict' | 'profiling' | 'leaderboard'>('predict');

  // ADMET modal states
  const [admetModalOpen, setAdmetModalOpen] = useState<boolean>(false);
  const [currentAdmet, setCurrentAdmet] = useState<ADMETProperties | null>(null);
  const [admetLoading, setAdmetLoading] = useState<boolean>(false);

  // 60+ Clinical Targets Modal states
  const [isTargetModalOpen, setIsTargetModalOpen] = useState<boolean>(false);
  const [customTargetSymbol, setCustomTargetSymbol] = useState<string>('ABL1');

  // Phase 2: De Novo Pocket Generation & Retrosynthesis Route Planner states
  const [isDeNovoModalOpen, setIsDeNovoModalOpen] = useState<boolean>(false);
  const [isRetroModalOpen, setIsRetroModalOpen] = useState<boolean>(false);
  const [retroSmiles, setRetroSmiles] = useState<string>('');
  const [retroMolName, setRetroMolName] = useState<string>('目标小分子');

  // Phase 3: Ultra-Large Virtual Screening states
  const [isScreeningModalOpen, setIsScreeningModalOpen] = useState<boolean>(false);

  const handleOpenRetrosynthesis = (smi: string, name: string) => {
    setRetroSmiles(smi);
    setRetroMolName(name);
    setIsRetroModalOpen(true);
  };

  const handleSelectDeNovoCandidate = (candidate: any) => {
    userDrugInteractedRef.current = true;
    setDrugSmiles(candidate.smiles);
    setSelectedDrugId('');
    setIsDeNovoModalOpen(false);
  };

  const handleSelectScreeningHit = (hit: any) => {
    userDrugInteractedRef.current = true;
    setDrugSmiles(hit.smiles);
    setSelectedDrugId('');
    setIsScreeningModalOpen(false);
  };

  const handleSelectClinicalTarget = (rec: ClinicalTargetRecord) => {
    userTargetInteractedRef.current = true;
    pendingPresetTargetIdRef.current = null;
    setCustomTargetSymbol(rec.symbol);
    setTargetSequence(rec.catalytic_sequence_snippet);
    const exactMatching = targets.find(t => t.id.toUpperCase() === rec.symbol.toUpperCase() && t.sequence === rec.catalytic_sequence_snippet);
    if (exactMatching) {
      setSelectedTargetId(exactMatching.id);
    } else {
      setSelectedTargetId('custom');
    }
  };

  const handleOpenAdmet = async () => {
    if (!drugSmiles.trim()) return;
    setAdmetModalOpen(true);
    setAdmetLoading(true);
    try {
      const data = await fetchADMETProperties(drugSmiles.trim());
      setCurrentAdmet(data);
    } catch (err) {
      console.error('Failed to load ADMET:', err);
    } finally {
      setAdmetLoading(false);
    }
  };


  const isModelReady = useMemo(() => {
    return !modelsLoading && !modelsError && models.length > 0 && models.some(m => m.id === modelName);
  }, [modelsLoading, modelsError, models, modelName]);

  const loadModels = useCallback(() => {
    setModelsLoading(true);
    setModelsError(null);
    fetchDTIModels().then(data => {
      setModelsLoading(false);
      if (data && data.length > 0) {
        setModels(data);
        setModelsError(null);
        setModelName(current => {
          if (current && data.some(m => m.id === current)) {
            return current;
          }
          const rec = data.find(m => m.is_recommended);
          return rec ? rec.id : data[0].id;
        });
      } else {
        setModels([]);
        setModelsError('后端未返回任何已注册的 DTI 模型');
      }
    }).catch(err => {
      setModelsLoading(false);
      setModels([]);
      setModelsError(`未能从后端加载模型目录: ${errorMessage(err)}`);
      console.warn('Failed to fetch models from backend:', err);
    });
  }, []);

  useEffect(() => {
    // 1. Fetch Drugs - do not overwrite if user already selected/typed
    fetchDTIDrugs().then(data => {
      setDrugs(data);
      if (!userDrugInteractedRef.current && data.length > 0) {
        setDrugSmiles(prev => {
          if (!userDrugInteractedRef.current && (!prev || !prev.trim())) {
            setSelectedDrugId(data[0].id);
            return data[0].smiles;
          }
          return prev;
        });
      }
    }).catch(err => console.error('Drugs fetch error:', err));

    // 2. Fetch Targets - do not overwrite if user already selected/typed
    fetchDTITargets().then(data => {
      setTargets(data);
      if (pendingPresetTargetIdRef.current) {
        const targetId = pendingPresetTargetIdRef.current;
        const match = data.find(t => t.id === targetId);
        if (match) {
          setSelectedTargetId(match.id);
          setTargetSequence(match.sequence);
          setCustomTargetSymbol(match.id);
          pendingPresetTargetIdRef.current = null;
          return;
        }
      }
      if (!userTargetInteractedRef.current && data.length > 0) {
        setTargetSequence(prev => {
          if (!userTargetInteractedRef.current && (!prev || !prev.trim())) {
            setSelectedTargetId(data[0].id);
            return data[0].sequence;
          }
          return prev;
        });
      }
    }).catch(err => console.error('Targets fetch error:', err));

    // 3. Fetch Models
    loadModels();
  }, [loadModels]);

  const handleDrugChange = (drugId: string) => {
    userDrugInteractedRef.current = true;
    setSelectedDrugId(drugId);
    const d = drugs.find(item => item.id === drugId);
    if (d) setDrugSmiles(d.smiles);
  };

  const handleTargetChange = (targetId: string) => {
    userTargetInteractedRef.current = true;
    pendingPresetTargetIdRef.current = null;
    setSelectedTargetId(targetId);
    if (targetId === 'custom') {
      return;
    }
    const t = targets.find(item => item.id === targetId);
    if (t) {
      setTargetSequence(t.sequence);
      setCustomTargetSymbol(t.id);
    }
  };

  const executePredict = async (smilesToUse: string, seqToUse: string, selectedModel: string = modelName) => {
    if (!isModelReady) {
      setErrorMsg('DTI 模型未就绪或模型目录不可用，无法提交预测。');
      return;
    }
    if (!smilesToUse.trim() || !seqToUse.trim()) {
      setErrorMsg('请同时提供合法的小分子 SMILES 和靶点蛋白序列。');
      return;
    }
    setErrorMsg(null);
    setIsLoading(true);
    setBiophysicsInsights(null);

    try {
      // 1. DTI Affinity Prediction
      const res = await predictDTIAffinity(smilesToUse.trim(), seqToUse.trim(), selectedModel);
      setResult(res);

      // 2. Parallel / Async Biophysics Insights
      fetchBiophysicsInsights(smilesToUse.trim(), seqToUse.trim())
        .then(bio => setBiophysicsInsights(bio))
        .catch(bioErr => console.warn('Biophysics insights notice:', bioErr));

    } catch (err: any) {
      setResult(null); // Clear previous result on prediction failure
      setErrorMsg(errorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handlePredict = async () => {
    if (!isModelReady) {
      setErrorMsg('DTI 模型未就绪或模型目录不可用，无法提交预测。');
      return;
    }
    await executePredict(drugSmiles, targetSequence, modelName);
  };

  const handleApplyPreset = (preset: PresetPairItem, autoRun: boolean = false) => {
    userDrugInteractedRef.current = true;
    userTargetInteractedRef.current = true;
    setResult(null);
    setBiophysicsInsights(null);
    setErrorMsg(null);

    const smiles = preset.smiles;
    setDrugSmiles(smiles);
    const matchedDrug = drugs.find(d => d.name.toLowerCase().includes(preset.drugName.toLowerCase()));
    if (matchedDrug) {
      setSelectedDrugId(matchedDrug.id);
    } else {
      setSelectedDrugId('');
    }

    if (!preset.isAvailable || !preset.targetId) {
      pendingPresetTargetIdRef.current = null;
      setSelectedTargetId('custom');
      setTargetSequence('');
      setCustomTargetSymbol(preset.targetName);
      setErrorMsg(`示例【${preset.label}】暂不可运行：${preset.unavailableReason || '当前基准集未收录该突变/靶点全长记录，不沿用历史序列。'}`);
      return;
    }

    const matchedTarget = targets.find(t => t.id === preset.targetId);
    if (!matchedTarget) {
      pendingPresetTargetIdRef.current = preset.targetId;
      setSelectedTargetId(preset.targetId);
      setTargetSequence('');
      setCustomTargetSymbol(preset.targetName);
      setErrorMsg(`靶点目录加载中，已预约靶点【${preset.targetName}】…`);
      return;
    }

    pendingPresetTargetIdRef.current = null;
    setSelectedTargetId(matchedTarget.id);
    setTargetSequence(matchedTarget.sequence);
    setCustomTargetSymbol(matchedTarget.id);

    if (autoRun && smiles && matchedTarget.sequence) {
      if (!isModelReady) {
        setErrorMsg('DTI 模型未就绪，已载入示例，请待模型就绪后再运行。');
        return;
      }
      executePredict(smiles, matchedTarget.sequence, modelName);
    }
  };


  const handleRunProfiling = async () => {
    if (!isModelReady) {
      setErrorMsg('DTI 模型未就绪或模型目录不可用，无法进行激酶谱分析。');
      return;
    }
    if (!drugSmiles.trim()) {
      setErrorMsg('请先提供小分子 SMILES。');
      return;
    }
    setErrorMsg(null);
    setIsProfiling(true);
    try {
      const prof = await profileKinasePanel(drugSmiles.trim(), modelName);
      setProfileResults(prof);
      setProfileModelName(modelName);
      setActiveTab('profiling');
    } catch (err: any) {
      setErrorMsg(err.message || '激酶谱系分析失败。');
    } finally {
      setIsProfiling(false);
    }
  };

  const handleExportProfileCSV = () => {
    if (!profileResults || profileResults.length === 0) return;
    const header = csvLine(['Kinase', 'Length(AA)', 'Predicted_pKd', 'Predicted_Kd_nM', 'Prediction_Score_Band', 'Domain', 'Model_ID', ...EVIDENCE_CSV_HEADERS]) + '\n';
    const rows = profileResults.map(p => 
      csvLine([p.kinase_name, p.length, p.predicted_pkd.toFixed(3), p.predicted_kd_nM.toFixed(1), predictionScoreBand(p.predicted_pkd), p.domain, profileModelName, ...evidenceCSVValues(p.research_evidence ?? evidence.data, profileModelName)])
    ).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `kinome_selectivity_profile_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExportPrediction = () => {
    if (!result) return;
    const source = result.research_evidence ?? evidence.data;
    const record: Record<string, unknown> = { ...result, export_schema_version: 2, prediction_score_band: predictionScoreBand(result.predicted_pkd), research_evidence: source ?? { status: 'unavailable', external_evaluation_completed: null, admitted_count: null }, research_use: `${evidenceNotice(source)} ${PREDICTION_SCOPE_NOTICE}`, model_limitations: modelLimitationNotice(result.model_used, source, result.provenance.model_sha256) };
    delete record.affinity_tier;
    delete record.affinity_tier_code;
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `dti_prediction_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };


  return (
    <div className="studio-workspace space-y-6">
      {/* 顶部主横幅 / 协议卡片 */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-6 rounded-2xl border border-indigo-700/40 shadow-lg relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck size={13} />
                DTI RESEARCH BENCHMARK
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-200 border border-blue-500/30 flex items-center gap-1">
                <CheckCircle2 size={13} />
                DAVIS 亲和力研究基准
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-200 border border-amber-500/30 flex items-center gap-1">
                <Award size={13} />
                结构与亲和力计算探索
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              药物–靶点亲和力预测
            </h2>
            <p className="text-sm text-slate-300 mt-1 max-w-3xl leading-relaxed">
              选择或输入分子与靶点，运行预测，再查看亲和力评分与结构分析。初次使用可以先载入下方示例。
            </p>
          </div>
          
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTab('predict')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer focus-ring ${
                activeTab === 'predict' 
                  ? 'bg-blue-600 text-white shadow-md' 
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
              }`}
            >
              亲和力预测
            </button>
            <button
              onClick={() => setActiveTab('profiling')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer focus-ring ${
                activeTab === 'profiling' 
                  ? 'bg-blue-600 text-white shadow-md' 
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
              }`}
            >
              激酶选择性谱 (Kinome Panel)
            </button>
            <button
              onClick={() => setActiveTab('leaderboard')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer focus-ring ${
                activeTab === 'leaderboard' 
                  ? 'bg-blue-600 text-white shadow-md' 
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
              }`}
            >
              模型基准对比
            </button>
          </div>
        </div>
      </div>

      <DTIEvidencePanel modelId={modelName} modelHash={models.find(model => model.id === modelName)?.model_sha256} />

      {activeTab === 'predict' && (
        <div className="space-y-6">
          <nav aria-label="预测操作步骤" className="workflow-navigation">
            <a href="#molecule-input">填写分子</a>
            <a href="#target-input">选择靶点</a>
            <a href="#prediction-controls">选择模型与预测</a>
            <a href="#prediction-results">查看结果</a>
          </nav>
          <div className="studio-action-bar">
            <div className="min-w-0">
              <p className="font-semibold">{isLoading ? '预测进行中' : '检查输入后开始预测'}</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {drugSmiles.trim() ? '分子已填写' : '待填写分子'} · {targetSequence.trim() ? '靶点已填写' : '待填写靶点'}
              </p>
            </div>
            <button
              type="button"
              onClick={handlePredict}
              disabled={isLoading || !isModelReady || !drugSmiles.trim() || !targetSequence.trim()}
              className="btn-lab-primary min-h-11 px-5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FlaskConical size={16} className="mr-2" />
              {isLoading ? '正在预测…' : '开始预测'}
            </button>
            {errorMsg && <a href="#prediction-controls" className="text-sm font-medium text-rose-700 dark:text-rose-300">查看错误说明</a>}
          </div>
          
          {/* ⚡ 新手极速上手通道 (Hero Quick Start) */}
          <div className="studio-examples bg-slate-900 p-4 sm:p-5 rounded-2xl border border-slate-700 shadow-md space-y-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2.5">
              <div className="flex items-center gap-2">
                <Zap size={20} className="text-sky-300" />
                <div>
                  <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                    <span>从示例开始</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-400/30">
                      载入后可继续编辑
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-300 mt-0.5">
                    先载入分子和靶点，检查输入后再预测；也可以直接运行示例。
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setShowAllPresets(!showAllPresets)}
                className="text-xs text-blue-300 hover:text-white bg-blue-500/10 hover:bg-blue-500/20 border border-blue-400/30 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <span>{showAllPresets ? '收起更多案例' : '浏览全部 8 款经典对'}</span>
                <ChevronDown size={14} className={`transition-transform duration-200 ${showAllPresets ? 'rotate-180' : ''}`} />
              </button>
            </div>

            {/* 3 款核心明星案例横排 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {[PRESET_PAIRS[0], PRESET_PAIRS[2], PRESET_PAIRS[6]].map((item) => {
                const isCurrent = drugSmiles === item.smiles;
                return (
                  <div
                    key={item.label}
                    className={`p-3.5 rounded-xl border transition-all relative flex flex-col justify-between ${
                      isCurrent
                        ? 'bg-blue-950/70 border-blue-400 ring-2 ring-blue-400/50 shadow-lg'
                        : 'bg-slate-900/80 border-slate-700/80 hover:border-blue-400/80 hover:bg-slate-850'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-1 mb-1.5">
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-mono">
                          {item.categoryLabel}
                        </span>
                        <span className="text-[10px] font-semibold text-slate-400">
                          {item.badge}
                        </span>
                      </div>
                      <div className="text-xs font-bold text-white truncate">
                        {item.label}
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                        {item.desc}
                      </p>
                    </div>

                    <div className="pt-3 mt-2 border-t border-slate-800 flex items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => handleApplyPreset(item, false)}
                        className="text-[11px] text-slate-300 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-colors cursor-pointer"
                        title="仅填充输入框，不立即执行推断"
                      >
                        仅载入
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApplyPreset(item, true)}
                        className="text-[11px] font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 px-3 py-1 rounded-lg shadow-sm transition-all flex items-center gap-1 cursor-pointer"
                        title="填充输入并立即在右侧呈现推断结果"
                      >
                        <Zap size={14} />
                        <span>载入并预测</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 展开全部 8 款经典对 (按需展示) */}
            {showAllPresets && (
              <div className="pt-3 border-t border-slate-700/60 space-y-3 animate-in fade-in duration-200">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-slate-300">更多临床抗肿瘤激酶抑制剂对：</span>
                  <div className="flex items-center gap-1 overflow-x-auto text-xs no-scrollbar">
                    {[
                      { id: 'all', label: '全部 (8)' },
                      { id: 'leukemia', label: '白血病/慢粒 (2)' },
                      { id: 'lung', label: '非小细胞肺癌 (3)' },
                      { id: 'melanoma', label: '黑色素瘤 (1)' },
                      { id: 'lymphoma', label: '淋巴瘤 (1)' },
                      { id: 'cycle', label: '细胞周期 (1)' },
                    ].map(cat => (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => setPresetCategory(cat.id)}
                        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors cursor-pointer ${
                          presetCategory === cat.id
                            ? 'bg-blue-600 text-white font-bold'
                            : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        {cat.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
                  {filteredPresets.map((item, idx) => {
                    const isCurrent = drugSmiles === item.smiles;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleApplyPreset(item, true)}
                        title={`${item.desc} (点击直接载入并推断)`}
                        className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer relative group ${
                          isCurrent
                            ? 'bg-blue-950/70 border-blue-400 ring-2 ring-blue-400/40 shadow-xs'
                            : 'bg-slate-900/60 border-slate-800 hover:border-blue-500/60 hover:bg-slate-850'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                            {item.categoryLabel}
                          </span>
                          <span className="text-[9px] text-blue-400 font-semibold">
                            {isCurrent ? '✓ 当前已选' : '⚡ 点击推断'}
                          </span>
                        </div>
                        <div className="text-xs font-bold text-slate-200 truncate group-hover:text-blue-400">
                          {item.label}
                        </div>
                        <div className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">
                          {item.desc}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* 🔬 进阶研发管线工具箱 (收敛为紧凑专业工具栏) */}
          <details className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <summary className="cursor-pointer px-4 py-3 font-semibold text-sm focus-ring">更多研究工具 · 靶点库、分子生成与筛选</summary>
          <div className="bg-slate-900 p-3 sm:p-3.5 rounded-b-xl flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FlaskConical size={18} className="text-sky-300" />
              <div>
                <span className="text-xs font-bold text-slate-200">进阶研发管线工具箱 (Phase 1~3 Advanced Toolkit)</span>
                <span className="text-[10px] text-slate-400 ml-2 hidden lg:inline">完成亲和力预测后，可无缝对接突变库、从头分子生成与商业库海选</span>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 shrink-0">
              <button
                type="button"
                onClick={() => setIsTargetModalOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-left transition-colors flex items-center gap-2 cursor-pointer group"
                title="60+ 临床抗肿瘤激酶与核心耐药突变体知识库"
              >
                <Dna size={18} className="text-sky-300" />
                <div className="min-w-0">
                  <div className="text-[11px] font-bold text-slate-200 group-hover:text-cyan-400 truncate">60+ 临床靶点库</div>
                  <div className="text-[9px] text-slate-400 truncate">耐药突变体</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setIsDeNovoModalOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-left transition-colors flex items-center gap-2 cursor-pointer group"
                title="3D 口袋从头分子扩散生成与骨架跃迁"
              >
                <Sparkles size={18} className="text-indigo-300" />
                <div className="min-w-0">
                  <div className="text-[11px] font-bold text-slate-200 group-hover:text-indigo-400 truncate">3D 从头生成</div>
                  <div className="text-[9px] text-slate-400 truncate">骨架跃迁/耐药穿透</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleOpenRetrosynthesis(
                  drugSmiles || 'CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)C)C(F)(F)F',
                  customTargetSymbol ? `${customTargetSymbol} 抑制剂先导物` : '当前分子'
                )}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-left transition-colors flex items-center gap-2 cursor-pointer group"
                title="AI 计算机辅助逆合成路线规划"
              >
                <TestTube size={18} className="text-emerald-300" />
                <div className="min-w-0">
                  <div className="text-[11px] font-bold text-slate-200 group-hover:text-emerald-400 truncate">AI 逆合成规划</div>
                  <div className="text-[9px] text-slate-400 truncate">CAS 现货原料</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setIsScreeningModalOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-left transition-colors flex items-center gap-2 cursor-pointer group"
                title="超大规模虚拟筛选引擎"
              >
                <Search size={18} className="text-sky-300" />
                <div className="min-w-0">
                  <div className="text-[11px] font-bold text-slate-200 group-hover:text-blue-400 truncate">超大虚拟海选</div>
                  <div className="text-[9px] text-slate-400 truncate">Enamine/Kinase 库</div>
                </div>
              </button>
            </div>
          </div>


          </details>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Input Section (7 cols) */}
            <div className="lg:col-span-7 space-y-6">
              
              {/* 工作流三步指引指示器 (Workflow Stepper) */}
              <div className="bg-slate-100/90 dark:bg-slate-850 p-2.5 rounded-xl border border-slate-200/80 dark:border-slate-800 flex items-center justify-between text-xs font-semibold text-slate-600 dark:text-slate-300">
                <div className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">1</span>
                  <span>选小分子配体</span>
                </div>
                <span className="text-slate-400">➔</span>
                <div className="flex items-center gap-1.5 text-indigo-600 dark:text-indigo-400">
                  <span className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[10px] font-bold">2</span>
                  <span>定激酶靶点</span>
                </div>
                <span className="text-slate-400">➔</span>
                <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                  <span className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">3</span>
                  <span>启动推断与透视</span>
                </div>
              </div>

              {/* 1. Small Molecule Input Card */}
              <div id="molecule-input" className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-3.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xs">
                      1
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">步骤 1 · 小分子激酶抑制剂配体 (Small Molecule)</h3>
                      <span className="text-[10px] text-slate-400">支持 68 款基准小分子载入或输入任意 SMILES</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleOpenAdmet}
                      className="text-xs bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer font-medium"
                      title="查看当前小分子的多维 ADMET 成药性雷达图"
                    >
                      <ShieldCheck size={13} />
                      <span>ADMET 雷达</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsSketcherOpen(true)}
                      className="text-xs bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer font-medium"
                    >
                      <Palette size={13} />
                      <span>分子手绘画板</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setShow2DStructure(!show2DStructure)}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      <Atom size={13} />
                      <span>{show2DStructure ? '收起 2D 骨架' : '展开 2D 骨架'}</span>
                      {show2DStructure ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>
                  </div>
                </div>

                {/* 常用 FDA 药物快捷 Chips */}
                <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] py-1 border-y border-slate-100 dark:border-slate-800/80 no-scrollbar">
                  <span className="text-slate-400 shrink-0 font-medium text-[10px]">常用药物:</span>
                  {POPULAR_DRUGS.map(pop => (
                    <button
                      key={pop.name}
                      type="button"
                      onClick={() => {
                        const targetDrug = drugs.find(d => d.name.toLowerCase() === pop.name.toLowerCase());
                        if (targetDrug) {
                          handleDrugChange(targetDrug.id);
                        }
                      }}
                      className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 hover:bg-blue-50 dark:hover:bg-blue-900/40 text-slate-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-300 shrink-0 transition-colors cursor-pointer"
                    >
                      {pop.label}
                    </button>
                  ))}
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                      <label className="text-xs font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                        <Filter size={12} className="text-blue-500" />
                        <span>从 DAVIS 基准集挑选药物 (已关联 PubChem)：</span>
                      </label>
                      <div className="flex items-center gap-1 text-[10px]">
                        {[
                          { id: 'all', label: `全部 (${drugs.length})` },
                          { id: 'known', label: `训练已知 (${drugs.filter(d => !d.is_test).length})` },
                          { id: 'test', label: `折5盲测未知 (${drugs.filter(d => d.is_test).length})` },
                        ].map(f => (
                          <button
                            key={f.id}
                            type="button"
                            onClick={() => setDrugFoldFilter(f.id as any)}
                            className={`px-2 py-0.5 rounded transition-colors cursor-pointer ${
                              drugFoldFilter === f.id
                                ? 'bg-blue-600 text-white font-semibold'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                            }`}
                          >
                            {f.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="flex gap-2 mb-2">
                      <div className="relative flex-1">
                        <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                          type="text"
                          value={drugSearchQuery}
                          aria-label="搜索药物"
                          onChange={(e) => setDrugSearchQuery(e.target.value)}
                          placeholder="快速搜索药物名称 (例如: Dasatinib, Gefitinib, Imatinib)..."
                          className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus-ring text-slate-900 dark:text-slate-100"
                        />
                      </div>
                      {drugSearchQuery && (
                        <button
                          type="button"
                          onClick={() => setDrugSearchQuery('')}
                          className="px-2 py-1 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        >
                          清空
                        </button>
                      )}
                    </div>

                    <select
                      value={selectedDrugId}
                      aria-label="选择基准药物"
                      onChange={(e) => handleDrugChange(e.target.value)}
                      className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus-ring text-slate-900 dark:text-slate-100 font-medium"
                    >
                      {filteredDrugs.length === 0 ? (
                        <option value="">未找到匹配的小分子药物</option>
                      ) : (
                        filteredDrugs.map(d => (
                          <option key={d.id} value={d.id}>
                            {`${d.name} (CID: ${d.id}) ${d.is_test ? '【折 5 · 严格测试集未知药】' : '【折 ' + d.fold + ' · 训练域已知药】'}`}
                          </option>
                        ))
                      )}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="drug-smiles" className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                      SMILES 字符串（支持直接编辑或输入全新化合物）：
                    </label>
                    <textarea
                      rows={2}
                      id="drug-smiles"
                      aria-label="分子 SMILES"
                      value={drugSmiles}
                      onChange={(e) => {
                        userDrugInteractedRef.current = true;
                        setDrugSmiles(e.target.value);
                      }}
                      placeholder="输入小分子规范 SMILES..."
                      className="w-full font-mono text-xs p-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg focus-ring text-slate-900 dark:text-slate-100"
                    />
                  </div>

                  {/* 2D 拓扑结构即时渲染 */}
                  {show2DStructure && drugSmiles.trim() && (
                    <div className="p-3 bg-slate-50/70 dark:bg-slate-950/40 rounded-lg border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-4">
                      <div>
                        <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                          实时 2D 结构拓扑预览 (ChemDraw 风格)
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                          长度: {drugSmiles.length} 字符
                        </div>
                      </div>
                      <Molecule2DViewer smiles={drugSmiles} name="当前配体" width={180} height={90} showExpandButton={true} />
                    </div>
                  )}
                </div>
              </div>

              {/* 2. Target Kinase Input Card */}
              <div id="target-input" className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-3.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">
                      2
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">步骤 2 · 人类催化激酶靶点 (Kinase Domain Target)</h3>
                      <span className="text-[10px] text-slate-400">覆盖全人类激酶组 379 种催化结构域与 60+ 临床耐药突变</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsTargetModalOpen(true)}
                      className="text-xs bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer font-medium"
                      title="从 60+ 临床抗肿瘤激酶与耐药突变体知识库中选择"
                    >
                      <Dna size={13} />
                      <span>临床靶点库</span>
                    </button>
                    <span className="text-xs text-slate-500 font-mono hidden sm:inline">ESM-2 进化表征 + 催化口袋几何提取</span>
                  </div>
                </div>

                {/* 常用肿瘤靶点快捷 Chips */}
                <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] py-1 border-y border-slate-100 dark:border-slate-800/80 no-scrollbar">
                  <span className="text-slate-400 shrink-0 font-medium text-[10px]">常用靶点:</span>
                  {POPULAR_TARGETS.map(pop => (
                    <button
                      key={pop.symbol}
                      type="button"
                      onClick={() => {
                        const targetMatch = targets.find(t => t.id.toUpperCase() === pop.symbol.toUpperCase());
                        if (targetMatch) {
                          handleTargetChange(targetMatch.id);
                        }
                      }}
                      className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 hover:bg-indigo-50 dark:hover:bg-indigo-900/40 text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-300 shrink-0 transition-colors cursor-pointer"
                    >
                      {pop.label}
                    </button>
                  ))}
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                      <label className="text-xs font-medium text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                        <Filter size={12} className="text-indigo-500" />
                        <span>从 DAVIS 基准集 379 种激酶中选择：</span>
                      </label>
                      <div className="flex items-center gap-1 text-[10px] overflow-x-auto no-scrollbar">
                        {[
                          { id: 'all', label: `全部 (${targets.length})` },
                          { id: 'TK', label: 'TK 酪氨酸' },
                          { id: 'TKL', label: 'TKL 类似物' },
                          { id: 'STE', label: 'STE 丝苏氨酸' },
                          { id: 'AGC', label: 'AGC 家族' },
                          { id: 'CAMK', label: 'CAMK 家族' },
                        ].map(f => (
                          <button
                            key={f.id}
                            type="button"
                            onClick={() => setTargetFamilyFilter(f.id)}
                            className={`px-2 py-0.5 rounded transition-colors cursor-pointer shrink-0 ${
                              targetFamilyFilter === f.id
                                ? 'bg-indigo-600 text-white font-semibold'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                            }`}
                          >
                            {f.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="flex gap-2 mb-2">
                      <div className="relative flex-1">
                        <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                          type="text"
                          value={targetSearchQuery}
                          aria-label="搜索靶点"
                          onChange={(e) => setTargetSearchQuery(e.target.value)}
                          placeholder="快速搜索激酶靶标 (例如: ABL1, EGFR, BRAF, SRC, JAK, KIT)..."
                          className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus-ring text-slate-900 dark:text-slate-100"
                        />
                      </div>
                      {targetSearchQuery && (
                        <button
                          type="button"
                          onClick={() => setTargetSearchQuery('')}
                          className="px-2 py-1 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        >
                          清空
                        </button>
                      )}
                    </div>

                    <select
                      value={selectedTargetId}
                      aria-label="选择基准靶点"
                      onChange={(e) => handleTargetChange(e.target.value)}
                      className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus-ring text-slate-900 dark:text-slate-100 font-medium"
                    >
                      {(!selectedTargetId || selectedTargetId === 'custom' || !filteredTargets.some(t => t.id === selectedTargetId)) && (
                        <option value={selectedTargetId || 'custom'}>
                          {`【未收录/自定义】${customTargetSymbol || '自定义催化结构域序列'}`}
                        </option>
                      )}
                      {filteredTargets.length === 0 ? (
                        <option value="">未找到匹配的激酶靶点</option>
                      ) : (
                        filteredTargets.map(t => (
                          <option key={t.id} value={t.id}>
                            {`激酶: ${t.standard_display_name || t.id} (${t.length} aa) ${t.is_test ? '【折 5 · 严格测试集未知激酶】' : '【折 ' + t.fold + ' · 训练域已知激酶】'}`}
                          </option>
                        ))
                      )}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="target-sequence" className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                      靶点激酶氨基酸序列（Sequence，支持自定义突变序列）：
                    </label>
                    <textarea
                      rows={3}
                      id="target-sequence"
                      aria-label="靶点氨基酸序列"
                      value={targetSequence}
                      onChange={(e) => {
                        userTargetInteractedRef.current = true;
                        pendingPresetTargetIdRef.current = null;
                        setTargetSequence(e.target.value);
                      }}
                      placeholder="输入 20 种标准天然氨基酸序列..."
                      className="w-full font-mono text-xs p-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg focus-ring text-slate-900 dark:text-slate-100 uppercase"
                    />
                    <div className="text-[11px] text-slate-400 mt-1 flex justify-between">
                      <span>当前残基数：{targetSequence.replace(/\s/g, '').length} aa</span>
                      <span>支持标准激酶催化域（200~1000 aa）</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 3. Prediction Execution & Model Card */}
              <div id="prediction-controls" className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs">
                      3
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">步骤 3 · 启动结合亲和力预测 (Predict Affinity)</h3>
                      <span className="text-[10px] text-slate-400">点击主按钮即刻输出 pKd / Kd 与 3D 诱导契合构象</span>
                    </div>
                  </div>
                </div>

                {errorMsg && (
                  <div role="alert" className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
                    <AlertCircle size={15} />
                    <span>{errorMsg}</span>
                  </div>
                )}

                {/* 核心主行动按钮 (Primary Action CTA) */}
                <div className="flex flex-col sm:flex-row gap-2.5 pt-1">
                  <button
                    type="button"
                    onClick={handlePredict}
                    disabled={isLoading || !isModelReady || !drugSmiles.trim() || !targetSequence.trim()}
                    className="flex-1 py-3.5 px-5 bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm rounded-xl shadow-lg shadow-blue-600/25 transition-all flex items-center justify-center gap-2 cursor-pointer focus-ring"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>正在预测，请稍候…</span>
                      </>
                    ) : (
                      <>
                        <FlaskConical size={18} />
                        <span>开始预测</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleRunProfiling}
                    disabled={isProfiling || !isModelReady || !drugSmiles.trim()}
                    title={!isModelReady ? "模型目录不可用，暂无法分析" : "在 16 个核心代表性激酶谱上评估该分子的结合选择性"}
                    className="py-3.5 px-4 bg-slate-800 hover:bg-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer focus-ring shrink-0"
                  >
                    {isProfiling ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <BarChart3 size={16} />
                    )}
                    <span>激酶谱选择性分析</span>
                  </button>
                </div>

                {/* 当前预测模型（默认紧凑展示推荐模型，支持展开对比） */}
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 min-w-0">
                    <Layers size={14} className="text-emerald-500 shrink-0" />
                    <span className="text-slate-500 shrink-0">当前模型:</span>
                    <span className="font-bold text-slate-900 dark:text-slate-100 truncate">
                      {modelsLoading ? '正在加载模型目录…' : modelsError ? '模型目录加载失败' : (models.find(m => m.id === modelName)?.name || modelName || '未选择模型')}
                    </span>
                    {!modelsLoading && !modelsError && (
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 shrink-0">
                        {models.find(m => m.id === modelName)?.dual_cold_ci != null ? `双冷 CI ${models.find(m => m.id === modelName)?.dual_cold_ci?.toFixed(4)}` : models.find(m => m.id === modelName)?.train_ci != null ? `训练 CI ${models.find(m => m.id === modelName)?.train_ci}` : '基准就绪'}
                      </span>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => setShowModelConfig(!showModelConfig)}
                    disabled={modelsLoading || !!modelsError}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 shrink-0 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span>{showModelConfig ? '收起模型' : `切换对比模型 (${models.length}款)`}</span>
                    <ChevronDown size={12} className={`transition-transform duration-200 ${showModelConfig ? 'rotate-180' : ''}`} />
                  </button>
                </div>

                {models.find(m => m.id === modelName)?.model_version && (
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    <div>模型版本：{models.find(m => m.id === modelName)?.model_version}</div>
                    <div>{models.find(m => m.id === modelName)?.evaluation_scope}</div>
                  </div>
                )}

                {modelsError && (
                  <div role="alert" className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <AlertCircle size={15} className="shrink-0 text-rose-500" />
                      <span className="truncate">{modelsError}</span>
                    </div>
                    <button
                      type="button"
                      onClick={loadModels}
                      disabled={modelsLoading}
                      className="px-2.5 py-1 bg-rose-100 hover:bg-rose-200 dark:bg-rose-900/50 dark:hover:bg-rose-800/60 text-rose-800 dark:text-rose-200 rounded text-xs font-semibold shrink-0 cursor-pointer disabled:opacity-50"
                    >
                      {modelsLoading ? '重试中…' : '重试加载模型'}
                    </button>
                  </div>
                )}

                {/* 展开全部模型 (按需展开) */}
                {showModelConfig && models.length > 0 && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2 animate-in fade-in duration-200">
                    {models.map(m => {
                      const isSelected = modelName === m.id;
                      const isRec = m.is_recommended;
                      return (
                        <button
                          key={m.id}
                          type="button"
                          onClick={() => setModelName(m.id)}
                          className={`p-3 rounded-xl border text-left transition-all cursor-pointer focus-ring relative ${
                            isSelected
                              ? isRec
                                ? 'border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/40 ring-2 ring-emerald-500/50 shadow-xs'
                                : 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/40 ring-2 ring-blue-500/50 shadow-xs'
                              : isRec
                                ? 'border-emerald-300 dark:border-emerald-800/80 bg-emerald-50/10 hover:bg-emerald-50/30'
                                : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                          }`}
                        >
                          {isRec && (
                            <div className="absolute top-2 right-2 flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-600 text-white uppercase tracking-wider">
                              <Sparkles size={10} /> 默认推荐
                            </div>
                          )}
                          <div className={`text-xs font-bold ${isSelected ? 'text-slate-900 dark:text-white' : 'text-slate-700 dark:text-slate-200'}`}>
                            {m.name}
                          </div>
                          <div className={`text-[10px] font-semibold mt-0.5 ${
                            m.badge_color === 'emerald' ? 'text-emerald-600 dark:text-emerald-400' : 'text-blue-600 dark:text-blue-400'
                          }`}>
                            {m.badge}
                          </div>
                          <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                            {m.desc}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

            </div>

            {/* Right Result Display Section (5 cols) */}
            <div id="prediction-results" className="lg:col-span-5 min-w-0 space-y-6">
              {result ? (
                <div className="precision-card p-6 rounded-2xl shadow-xl space-y-5 animate-in fade-in duration-300 hud-bracket">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 dark:border-slate-800/80 pb-3">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-sky-500 animate-pulse" />
                      <span>预测推断与结合评分 (Affinity Output)</span>
                    </h3>
                    <span className="text-[10px] px-2.5 py-0.5 rounded-md font-mono font-bold bg-sky-50 dark:bg-sky-950/80 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                      {result.model_used.toUpperCase()}
                    </span>
                    <button type="button" onClick={handleExportPrediction} className="btn-lab-secondary min-h-11 px-3 text-xs">导出预测 JSON</button>
                  </div>
                  <p className="text-xs leading-relaxed text-amber-800 dark:text-amber-200">{evidenceNotice(result.research_evidence ?? evidence.data)}</p>

                  {/* High-Precision Spectral Bio-Gauge Hero */}
                  <div role="region" aria-label="预测分数与用途限制" className="p-5 rounded-2xl bg-gradient-to-b from-sky-50/70 via-white to-slate-50/50 dark:from-slate-900/90 dark:via-slate-900/60 dark:to-slate-950/90 border border-sky-200/70 dark:border-sky-900/40 shadow-inner space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-500 dark:text-slate-400 font-medium">预测负对数亲和力 (pKd)</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                        DAVIS Scale [5.0 - 10.8]
                      </span>
                    </div>

                    <div className="flex items-baseline justify-center gap-2 py-1">
                      <div className="text-5xl font-black text-sky-600 dark:text-sky-400 font-mono tracking-tight glow-cyan-text">
                        {result.predicted_pkd.toFixed(3)}
                      </div>
                      <span className="text-xs font-mono text-slate-400">pKd</span>
                    </div>
                    <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">{PREDICTION_SCOPE_NOTICE}</p>
                    <DTIModelLimitations modelId={result.model_used} modelHash={result.provenance.model_sha256} evidence={result.research_evidence ?? evidence.data} />

                    {/* Affinity Spectral Continuum Bar */}
                    <div className="space-y-1.5 pt-1">
                      <div className="relative w-full h-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                        <div 
                          className="absolute inset-0 bg-gradient-to-r from-slate-400 via-amber-400 to-emerald-400 opacity-80"
                        />
                        {/* Needle Indicator */}
                        <div 
                          className="absolute top-0 bottom-0 w-1.5 bg-slate-950 dark:bg-white shadow-sm transition-all duration-500 -translate-x-1/2"
                          style={{ left: `${Math.max(0, Math.min(100, ((result.predicted_pkd - 5.0) / 5.5) * 100))}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-[9px] font-mono text-slate-400">
                        <span>5.0</span>
                        <span>7.0</span>
                        <span>9.0</span>
                        <span>10.5+</span>
                      </div>
                    </div>
                    
                    {/* Thermodynamic & Physical Metrics Divider */}
                    <div className="pt-3 border-t border-slate-200/70 dark:border-slate-800/80 grid grid-cols-2 gap-3 text-xs">
                      <div className="p-2.5 rounded-xl bg-white/80 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800 text-center">
                        <span className="text-slate-500 dark:text-slate-400 block text-xs font-medium">由预测分数换算的 Kd</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-100 text-sm">
                          {result.predicted_kd_nM < 1000 
                            ? `${result.predicted_kd_nM.toFixed(1)} nM` 
                            : `${(result.predicted_kd_nM / 1000).toFixed(2)} μM`}
                        </span>
                        <span className="text-[9px] text-slate-400 block font-mono mt-0.5">
                          ~{(result.predicted_kd_nM * 1000).toFixed(0)} pM
                        </span>
                      </div>

                      <div className="p-2.5 rounded-xl bg-white/80 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800 text-center">
                        <span className="text-slate-500 dark:text-slate-400 block text-xs font-medium">预测分数区间</span>
                        <div className="mt-1">
                          <span className={`font-semibold px-2.5 py-0.5 rounded-full text-xs inline-block ${
                            result.predicted_pkd >= 7
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60'
                              : result.predicted_pkd >= 6
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60'
                              : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700'
                          }`}>
                            {predictionScoreBand(result.predicted_pkd)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* ADMET 成药性与毒理雷达卡片 */}
                  <div className="p-3.5 rounded-xl border border-indigo-200/80 dark:border-indigo-900/60 bg-gradient-to-r from-indigo-50/50 via-white to-blue-50/40 dark:from-slate-900/90 dark:via-indigo-950/20 dark:to-slate-900/90 flex flex-wrap items-center justify-between gap-3 shadow-2xs">
                    <div className="flex min-w-0 flex-1 basis-56 items-center gap-2.5">
                      <div className="p-2 rounded-xl bg-indigo-600 text-white shadow-xs">
                        <ShieldCheck size={16} />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-800 dark:text-slate-100 flex flex-wrap items-center gap-1.5">
                          <span>多维成药性与 ADMET 药代毒理评估</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-mono">
                            QSAR & Physics
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400 block mt-0.5">
                          hERG 心脏安全、Caco-2 膜透性、Delaney LogS、CYP3A4/2D6 抑制等 5 维雷达
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleOpenRetrosynthesis(drugSmiles, `${customTargetSymbol || '当前靶点'} 抑制剂`)}
                        className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-all cursor-pointer focus-ring"
                        title="AI 计算机辅助逆合成路线规划 (CAS 商业原料、反应条件与收率)"
                      >
                        <TestTube size={13} />
                        <span>逆合成路线</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleOpenAdmet}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-all cursor-pointer focus-ring"
                      >
                        <ShieldCheck size={13} />
                        <span>查看 ADMET 雷达</span>
                      </button>
                    </div>
                  </div>

                  {/* 3D 微观几何与热力学物理自由能透视卡片 */}
                  {biophysicsInsights ? (
                    <div className="p-4 rounded-xl border border-indigo-200/80 dark:border-indigo-900/60 bg-gradient-to-br from-indigo-50/40 via-white to-blue-50/30 dark:from-slate-900/90 dark:via-indigo-950/30 dark:to-slate-900/90 space-y-3.5 shadow-2xs">
                      <div className="flex items-center justify-between border-b border-indigo-100 dark:border-indigo-900/40 pb-2">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-950 dark:text-indigo-200">
                          <Activity size={14} className="text-indigo-500 animate-pulse" />
                          <span>3D 诱导契合与 MM-GBSA 物理透视</span>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 font-semibold border border-indigo-200 dark:border-indigo-800">
                          {biophysicsInsights.binding_mode_label}
                        </span>
                      </div>

                      {/* 构象与口袋几何芯片 */}
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="p-2.5 rounded-xl bg-white dark:bg-slate-950/70 border border-slate-200/80 dark:border-slate-800/80">
                          <span className="text-slate-400 text-[10px] block">诱导契合构象模式</span>
                          <span className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1 mt-0.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${biophysicsInsights.preferred_conformation.includes('Type I') ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                            {biophysicsInsights.preferred_conformation}
                          </span>
                          <span className="text-[10px] text-slate-400 block mt-1 font-mono">
                            DFG 翻转惩罚: {biophysicsInsights.dfg_flip_penalty_kcal.toFixed(2)} kcal
                          </span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-white dark:bg-slate-950/70 border border-slate-200/80 dark:border-slate-800/80">
                          <span className="text-slate-400 text-[10px] block">铰链区与门控位阻</span>
                          <span className="font-bold text-slate-800 dark:text-slate-200 block mt-0.5">
                            Hinge: {biophysicsInsights.hinge_score.toFixed(2)}
                          </span>
                          <span className="text-[10px] text-slate-400 block mt-1 font-mono">
                            Clash 惩罚: {biophysicsInsights.gatekeeper_clash.toFixed(2)}
                          </span>
                        </div>
                      </div>

                      {/* 第一性原理 MM-GBSA 能量沉降台阶与分解 */}
                      <div className="p-3 rounded-xl bg-white dark:bg-slate-950/70 border border-slate-200/80 dark:border-slate-800/80 space-y-2">
                        <div className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <Flame size={13} className="text-amber-500" />
                            <span>MM-GBSA 自由能物理分解：</span>
                          </span>
                          <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold glow-emerald-text text-xs">
                            ΔG = {biophysicsInsights.mmgbsa.delta_g_bind.toFixed(2)} kcal/mol
                          </span>
                        </div>

                        {/* First-Principles Energy Decomposition Chips */}
                        <div className="grid grid-cols-4 gap-1.5 text-center font-mono text-[10px] pt-1">
                          <div className="p-1.5 rounded-lg bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200/60 dark:border-emerald-800/40">
                            <span className="text-emerald-700 dark:text-emerald-400 block text-[9px]">ΔEvdw (引力)</span>
                            <span className="font-bold text-emerald-900 dark:text-emerald-200">{biophysicsInsights.mmgbsa.delta_e_vdw.toFixed(1)}</span>
                          </div>
                          <div className="p-1.5 rounded-lg bg-sky-50/60 dark:bg-sky-950/30 border border-sky-200/60 dark:border-sky-800/40">
                            <span className="text-sky-700 dark:text-sky-400 block text-[9px]">ΔEelec (静电)</span>
                            <span className="font-bold text-sky-900 dark:text-sky-200">{biophysicsInsights.mmgbsa.delta_e_elec.toFixed(1)}</span>
                          </div>
                          <div className="p-1.5 rounded-lg bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-800/40">
                            <span className="text-amber-700 dark:text-amber-400 block text-[9px]">ΔGsolv (溶剂)</span>
                            <span className="font-bold text-amber-900 dark:text-amber-200">{(biophysicsInsights.mmgbsa.delta_g_gb + biophysicsInsights.mmgbsa.delta_g_sa).toFixed(1)}</span>
                          </div>
                          <div className="p-1.5 rounded-lg bg-rose-50/60 dark:bg-rose-950/30 border border-rose-200/60 dark:border-rose-800/40">
                            <span className="text-rose-700 dark:text-rose-400 block text-[9px]">-TΔS (熵罚)</span>
                            <span className="font-bold text-rose-900 dark:text-rose-200">{biophysicsInsights.mmgbsa.minus_t_delta_s.toFixed(1)}</span>
                          </div>
                        </div>

                        <div className="text-[10px] text-slate-400 flex justify-between pt-1 border-t border-slate-100 dark:border-slate-800/60 font-mono">
                          <span>可旋转键自由度: {biophysicsInsights.mmgbsa.rotatable_bonds} 键</span>
                          <span>埋藏疏水 SASA: {biophysicsInsights.mmgbsa.buried_sasa.toFixed(1)} Å²</span>
                        </div>

                        {/* 3D 激酶微观催化口袋互作与氢键渲染器 */}
                        <div className="pt-2">
                          <KinasePocketViewer3D
                            targetName={customTargetSymbol || targets.find(t => t.id === selectedTargetId)?.id || 'ABL1'}
                            drugName={drugs.find(d => d.id === selectedDrugId)?.name || 'Dasatinib'}
                            drugSmiles={drugSmiles}
                            className="w-full"
                          />

                        </div>
                      </div>
                    </div>
                  ) : isLoading ? (
                    <div className="p-5 rounded-xl border border-dashed border-sky-300 dark:border-sky-800/80 bg-sky-50/20 dark:bg-sky-950/20 flex flex-col items-center justify-center gap-2 text-xs text-sky-600 dark:text-sky-400">
                      <div className="w-5 h-5 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
                      <span>正在解算 3D 几何诱导契合与 MM-GBSA 第一性原理自由能...</span>
                    </div>
                  ) : null}

                  {/* Domain & Zero-Leakage Badge */}
                  <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/60 space-y-2">
                    <div className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <ShieldCheck size={14} className="text-emerald-500" />
                        <span>拓扑评估域诊断：</span>
                      </span>
                      <span className="text-sky-600 dark:text-sky-400 font-mono text-[11px] font-bold">
                        {result.domain}
                      </span>
                    </div>
                    
                    <div className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                      {result.domain_label}
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 text-slate-500 font-mono">
                      <div className="bg-white dark:bg-slate-950/70 p-2 rounded-lg border border-slate-200/50 dark:border-slate-800">
                        训练药物最高相似度:
                        <span className="block font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                          {(result.max_drug_similarity_to_train * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="bg-white dark:bg-slate-950/70 p-2 rounded-lg border border-slate-200/50 dark:border-slate-800">
                        训练靶点描述符相似度:
                        <span className="block font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                          {(result.max_target_similarity_to_train * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Domain Metrics Reference */}
                  {result.domain_benchmark_metrics && Object.keys(result.domain_benchmark_metrics).length > 0 ? (
                    <div className="space-y-1.5 text-xs">
                      <div className="font-semibold text-slate-700 dark:text-slate-300">
                        此模型在对应历史基准域的指标（非本条预测的实验准确度）：
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-center text-[11px] font-mono">
                        <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800">
                          <span className="text-slate-400 block text-[10px]">RMSE 误差</span>
                          <span className="font-bold">{result.domain_benchmark_metrics.rmse?.toFixed(4)}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800">
                          <span className="text-slate-400 block text-[10px]">Pearson r</span>
                          <span className="font-bold">{result.domain_benchmark_metrics.pearson_r?.toFixed(4)}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900/80 border border-slate-200/60 dark:border-slate-800">
                          <span className="text-slate-400 block text-[10px]">CI 一致性指数</span>
                          <span className="font-bold text-sky-600 dark:text-sky-400">{result.domain_benchmark_metrics.concordance_index?.toFixed(4)}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">
                      此输入域没有该模型的已登记指标。相似度诊断不是预测置信度。
                    </div>
                  )}

                  {/* Provenance Alert */}
                  <div className="text-[11px] text-slate-400 border-t border-slate-200/60 dark:border-slate-800/80 pt-3 space-y-1">
                    <div>基准协议：<span className="font-mono text-slate-500">{result.provenance.protocol}</span></div>
                    <div>训练运行：<span className="font-mono text-slate-500">{result.provenance.training_run}</span></div>
                    {result.provenance.model_version && <div>模型版本：<span className="font-mono text-slate-500">{result.provenance.model_version}</span></div>}
                    <div className="text-amber-600 dark:text-amber-400 pt-1">{result.warning}</div>
                  </div>

                </div>
              ) : (
                <div className="h-full min-h-[480px] flex flex-col items-center justify-center p-6 sm:p-8 bg-gradient-to-b from-sky-50/50 via-white to-slate-50/60 dark:from-slate-900/80 dark:via-slate-900/50 dark:to-slate-950/80 border border-sky-100 dark:border-slate-800 rounded-2xl text-center shadow-xs space-y-5">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow-lg shadow-blue-500/25">
                    <Sparkles size={28} className="animate-pulse" />
                  </div>
                  
                  <div className="max-w-md space-y-1.5">
                    <h4 className="text-base font-bold text-slate-900 dark:text-slate-100">
                      欢迎进入 DTI 激酶亲和力世界模型工作台
                    </h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                      初次使用不知从何下手？点击下方经典临床案例，1 秒内即刻体验全原子 3D 诱导契合构象与物理自由能能量分解：
                    </p>
                  </div>

                  {/* 3 大明星案例一键触发 */}
                  <div className="w-full max-w-md grid grid-cols-1 gap-2.5 text-left">
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(PRESET_PAIRS[0], true)}
                      className="p-3 rounded-xl border border-sky-200 dark:border-sky-800/80 bg-white dark:bg-slate-850 hover:border-sky-400 dark:hover:border-sky-500 hover:shadow-md transition-all flex items-center justify-between group cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xl">💊</span>
                        <div>
                          <div className="text-xs font-bold text-slate-900 dark:text-slate-100 group-hover:text-sky-600 dark:group-hover:text-sky-400">
                            达沙替尼 → ABL1
                          </div>
                          <div className="text-[10px] text-slate-400">
                            基准目录参考配对 · 计算输出需实验核查
                          </div>
                        </div>
                      </div>
                      <span className="text-[11px] font-bold px-2 py-1 rounded-lg bg-sky-50 dark:bg-sky-950 text-sky-600 dark:text-sky-300 group-hover:bg-sky-600 group-hover:text-white transition-colors">
                        一键推断 ➔
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleApplyPreset(PRESET_PAIRS[2], true)}
                      className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-850 hover:border-indigo-400 dark:hover:border-indigo-500 hover:shadow-md transition-all flex items-center justify-between group cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xl">🫁</span>
                        <div>
                          <div className="text-xs font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                            奥希替尼 → EGFR T790M
                          </div>
                          <div className="text-[10px] text-slate-400">
                            非小细胞肺癌核心药 · 克服一代耐药门控突变
                          </div>
                        </div>
                      </div>
                      <span className="text-[11px] font-bold px-2 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-300 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                        一键推断 ➔
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleApplyPreset(PRESET_PAIRS[6], true)}
                      className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-850 hover:border-emerald-400 dark:hover:border-emerald-500 hover:shadow-md transition-all flex items-center justify-between group cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xl">🧬</span>
                        <div>
                          <div className="text-xs font-bold text-slate-900 dark:text-slate-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400">
                            维莫非尼 → BRAF V600E
                          </div>
                          <div className="text-[10px] text-slate-400">
                            恶性黑色素瘤驱动基因 · 高选择性变构抑制
                          </div>
                        </div>
                      </div>
                      <span className="text-[11px] font-bold px-2 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-300 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                        一键推断 ➔
                      </span>
                    </button>
                  </div>

                  {/* 3 步操作说明与左侧联动 */}
                  <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800/80 w-full max-w-md flex items-center justify-between text-[11px] text-slate-400">
                    <span className="flex items-center gap-1 font-medium">① 选药物配体</span>
                    <span>➔</span>
                    <span className="flex items-center gap-1 font-medium">② 指定激酶靶点</span>
                    <span>➔</span>
                    <span className="flex items-center gap-1 font-medium">③ 启动世界模型</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Profiling Tab */}
      {activeTab === 'profiling' && (
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <BarChart3 className="text-indigo-600" size={18} />
                核心激酶谱系选择性分析看板 (Kinome Selectivity Profile)
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                当前筛选小分子：<span className="font-mono font-bold text-slate-800 dark:text-slate-200">{drugSmiles ? drugSmiles.slice(0, 45) + '...' : '未载入'}</span>
                （覆盖 TK, CMGC, STE, AGC 等 16 种核心代表性激酶催化域）
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              {profileResults && profileResults.length > 0 && (
                <button
                  onClick={handleExportProfileCSV}
                  className="py-2 px-3.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer focus-ring"
                >
                  <Download size={14} />
                  <span>导出 CSV</span>
                </button>
              )}
              <button
                onClick={handleRunProfiling}
                disabled={isProfiling || !isModelReady || !drugSmiles.trim()}
                className="py-2 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs rounded-xl shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer focus-ring"
              >
                {isProfiling ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Sparkles size={14} />}
                <span>重新测定谱系</span>
              </button>
            </div>
          </div>

          {/* 亲和力标尺参考图例 */}
          <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/80 flex flex-wrap items-center justify-between gap-3 text-xs">
            <span className="font-semibold text-slate-700 dark:text-slate-300">预测分数标尺（实验活性未确认）：</span>
            <div className="flex flex-wrap items-center gap-4 text-[11px]">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-slate-600 dark:text-slate-400">预测 pKd ≥ 7.0</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-slate-600 dark:text-slate-400">预测 6.0 ≤ pKd &lt; 7.0</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-slate-400" />
                <span className="text-slate-600 dark:text-slate-400">预测 pKd &lt; 6.0</span>
              </span>
            </div>
          </div>

          {profileResults && profileResults.length > 0 ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {profileResults.map((item, idx) => {
                  const barPercent = Math.max(0, Math.min(100, ((item.predicted_pkd - 5.0) / 4.5) * 100));
                  return (
                    <div key={item.kinase_name} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-2.5">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-md bg-slate-200 dark:bg-slate-700 text-[10px] font-bold flex items-center justify-center font-mono">
                            {idx + 1}
                          </span>
                          <span className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                            {item.kinase_name}
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {item.length} aa
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="font-mono font-bold text-blue-600 dark:text-blue-400">
                            pKd {item.predicted_pkd.toFixed(2)}
                          </span>
                          <span className="text-[10px] text-slate-400 block font-mono">
                            Kd ≈ {item.predicted_kd_nM < 1000 ? `${item.predicted_kd_nM.toFixed(0)} nM` : `${(item.predicted_kd_nM / 1000).toFixed(1)} μM`}
                          </span>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full bg-slate-200 dark:bg-slate-700 h-2.5 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all duration-500 ${
                            item.predicted_pkd >= 7
                              ? 'bg-emerald-500'
                              : item.predicted_pkd >= 6
                              ? 'bg-amber-500'
                              : 'bg-slate-400'
                          }`}
                          style={{ width: `${barPercent}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                        <span className="font-sans font-medium">{predictionScoreBand(item.predicted_pkd)}</span>
                        <span className="text-[10px]">{item.domain}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-xs text-slate-400 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl">
              点击上方“重新测定谱系”或在预测控制台点击“激酶谱系选择性分析”，系统将自动筛选并在 16 个代表性激酶上输出亲和力阶梯图。
            </div>
          )}
        </div>
      )}

      {/* Model benchmark metrics come from the registered model catalogue. */}
      {activeTab === 'leaderboard' && (
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Award className="text-amber-500" size={18} />已注册模型与基准指标
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              指标来自各模型登记的实际版本，不是同一环境的统一排名。F1只报告已核验的双冷975对结果；其他域未报告时不借用F4指标。
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                  <th className="p-3 font-bold">评价域</th><th className="p-3 font-bold">配对数</th>
                  <th className="p-3 font-bold">模型</th><th className="p-3 font-bold">版本</th>
                  <th className="p-3 font-bold">CI ↑</th><th className="p-3 font-bold">RMSE ↓</th>
                  <th className="p-3 font-bold">MAE ↓</th><th className="p-3 font-bold">结果范围</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {models.flatMap(model => Object.entries(model.metrics_by_domain ?? {}).map(([domain, metrics]) => (
                  <tr key={`${model.id}:${domain}`} className={model.is_recommended ? 'bg-emerald-50/40 dark:bg-emerald-950/20' : ''}>
                    <td className="p-3">{{ strict_dual_cold_test: '双实体冷启动', cold_drug_test: '冷药物', cold_target_test: '冷靶点', train_block: '训练主块' }[domain] || domain}</td>
                    <td className="p-3 font-mono">{metrics.n ?? '未报告'}</td>
                    <td className="p-3 font-semibold">{model.name}</td>
                    <td className="p-3 text-[10px] break-words">{model.model_version || model.benchmark_version || '未登记'}</td>
                    <td className="p-3 font-mono">{metrics.concordance_index == null ? '未报告' : Number(metrics.concordance_index).toFixed(4)}</td>
                    <td className="p-3 font-mono">{metrics.rmse == null ? '未报告' : Number(metrics.rmse).toFixed(4)}</td>
                    <td className="p-3 font-mono">{metrics.mae == null ? '未报告' : Number(metrics.mae).toFixed(4)}</td>
                    <td className="p-3 text-[10px] text-slate-500">{model.evaluation_scope || '历史登记结果'}</td>
                  </tr>
                )))}
                {models.length === 0 && (
                  <tr><td colSpan={8} className="p-4 text-slate-500">{modelsLoading ? '正在读取模型指标…' : '当前没有可用的模型指标。'}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 分子结构手绘画板模态框 */}
      <MoleculeSketcherModal
        isOpen={isSketcherOpen}
        onClose={() => setIsSketcherOpen(false)}
        initialSmiles={drugSmiles}
        onApply={(s) => {
          setDrugSmiles(s);
          setSelectedDrugId('');
        }}
        title="配体分子结构手绘画板"
      />

      {/* 多维成药性与 ADMET 药代毒理评估雷达模态框 */}
      <ADMETRadarModal
        isOpen={admetModalOpen}
        onClose={() => setAdmetModalOpen(false)}
        admet={currentAdmet}
        moleculeName={drugs.find(d => d.id === selectedDrugId)?.name || '当前小分子配体'}
        loading={admetLoading}
      />

      {/* 60+ 临床抗肿瘤激酶与耐药突变体知识库模态框 */}
      <ClinicalTargetSelectorModal
        isOpen={isTargetModalOpen}
        onClose={() => setIsTargetModalOpen(false)}
        onSelectTarget={handleSelectClinicalTarget}
        currentTargetSymbol={customTargetSymbol}
      />

      {/* Phase 2: 3D 口袋从头分子扩散生成与骨架跃迁模态框 */}
      <DeNovoPocketGeneratorModal
        isOpen={isDeNovoModalOpen}
        onClose={() => setIsDeNovoModalOpen(false)}
        initialTargetSymbol={customTargetSymbol}
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
        initialTargetSymbol={customTargetSymbol}
        onViewRetrosynthesis={handleOpenRetrosynthesis}
        onSelectLead={handleSelectScreeningHit}
      />
    </div>
  );
}
