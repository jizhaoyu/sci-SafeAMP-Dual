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
  Dna,
  ShoppingCart,
  FileText,
  Grid,
  Check,
  Copy,
  ExternalLink,
  PlusCircle,
  ArrowRight,
  Eye,
  RefreshCw,
  Box,
  CornerDownRight,
  Target,
  Beaker
} from 'lucide-react';
import { 
  fetchDTIDrugs, 
  fetchDTITargets, 
  fetchDTIModels, 
  predictDTIAffinity, 
  profileKinasePanel,
  fetchBiophysicsInsights,
  fetchADMETProperties,
  fetchAcademicReport,
  generateWetlabDispatch,
  type DTIDrug, 
  type DTITarget, 
  type DTIModelMeta,
  type DTIPredictionResult,
  type KinomeProfileItem,
  type BiophysicsInsights,
  type ADMETProperties,
  type ClinicalTargetRecord,
  type AcademicReportResult,
  type WetlabDispatchResult
} from '../api/dtiClient';
import { errorMessage } from '../api/client';
import { DTIEvidencePanel } from './DTIEvidencePanel';
import { useDTIEvidenceStatus, evidenceNotice, modelLimitationNotice, predictionScoreBand, PREDICTION_SCOPE_NOTICE, EVIDENCE_CSV_HEADERS, evidenceCSVValues, csvLine } from '../api/dtiEvidence';
import { DTIModelLimitations } from './DTIModelLimitations';
import { Molecule2DViewer } from './Molecule2DViewer';
import { KinasePocketViewer3D } from './KinasePocketViewer3D';
import { MoleculeSketcherModal } from './MoleculeSketcherModal';
import { ADMETRadarModal } from './ADMETRadarModal';
import { submitAsyncTask } from '../api/asyncTaskClient';
import { ClinicalTargetSelectorModal } from './ClinicalTargetSelectorModal';
import { DeNovoPocketGeneratorModal } from './DeNovoPocketGeneratorModal';
import { RetrosynthesisModal } from './RetrosynthesisModal';
import { VirtualScreeningModal } from './VirtualScreeningModal';
import { AcademicReportModal } from './AcademicReportModal';
import { WetlabDispatchModal } from './WetlabDispatchModal';
import { useAppStore } from '../store/useAppStore';
import { useNavigate, useLocation } from 'react-router-dom';

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
    label: '吉非替尼 → EGFR (敏感突变经典药)',
    drugName: 'Gefitinib',
    targetId: 'EGFR',
    targetName: 'EGFR',
    smiles: 'COC1=C(OCC2CCNCC2)C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl',
    desc: '第一代 EGFR 酪氨酸激酶抑制剂，经典 ATP 铰链竞争性结合',
    category: 'lung',
    categoryLabel: '肺癌/一代敏感',
    badge: '经典靶向药',
    isAvailable: true
  },
  {
    label: '阿来替尼 → ALK (二代高选择性抑制剂)',
    drugName: 'Alectinib',
    targetId: null,
    targetName: 'ALK',
    smiles: 'CCC1(C2=C(C=C(C=C2)C#N)C(=O)N(C1)C3=C4C(=CC(=C3)N5CCC(CC5)O)C(C)(C)CC4)C',
    desc: '针对 ALK 融合阳性非小细胞肺癌，高脑通透性二代靶向药物',
    category: 'lung',
    categoryLabel: '肺癌/ALK融合',
    badge: '基准未收录',
    isAvailable: false,
    unavailableReason: 'DAVIS 基准目录中未收录阿来替尼标准测定对，暂不可运行基准预测。'
  },
  {
    label: '伊布替尼 → BTK (B细胞淋巴瘤共价抑制剂)',
    drugName: 'Ibrutinib',
    targetId: null,
    targetName: 'BTK',
    smiles: 'C=CC(=O)N1CCC(CC1)N2C3=NC=NC(=C3C(=N2)C4=CC=C(C=C4)OC5=CC=CC=C5)N',
    desc: '不可逆共价靶向 BTK Cys481，恶性淋巴瘤一线突破药物',
    category: 'lymphoma',
    categoryLabel: '淋巴瘤/共价抑制',
    badge: '基准未收录',
    isAvailable: false,
    unavailableReason: 'DAVIS 基准目录中未收录伊布替尼标准测定对，暂不可直接运行基准预测。'
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
    label: '帕博西尼 → CDK4/CDK6 (细胞周期蛋白抑制剂)',
    drugName: 'Palbociclib',
    targetId: null,
    targetName: 'CDK4',
    smiles: 'CC1=C(C(=O)C2=CN=C(N=C2N1C3CCCC3)NC4=NC=C(C=C4)N5CCNCC5)C(=O)C',
    desc: '高选择性 CDK4/6 周期调控抑制剂，晚期乳腺癌一线标准方案',
    category: 'cycle',
    categoryLabel: '细胞周期/CDK4',
    badge: '基准未收录',
    isAvailable: false,
    unavailableReason: 'DAVIS 基准目录中未收录帕博西尼标准测定对，暂不可直接运行基准预测。'
  }
];

export default function DTIStudio() {
  const navigate = useNavigate();
  const location = useLocation();
  const { addToCart, setActiveSmallMolecule, setActiveTarget, activeEntity, activeTarget } = useAppStore();
  const evidence = useDTIEvidenceStatus();

  // Model & Catalog States
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
  const [show2DStructure, setShow2DStructure] = useState<boolean>(false);
  const [isSequenceExpanded, setIsSequenceExpanded] = useState<boolean>(false);
  const [isSketcherOpen, setIsSketcherOpen] = useState<boolean>(false);

  // User interaction tracking
  const userDrugInteractedRef = useRef<boolean>(false);
  const userTargetInteractedRef = useRef<boolean>(false);
  const pendingPresetTargetIdRef = useRef<string | null>(null);

  // Search & Filter expansion states
  const [presetCategory, setPresetCategory] = useState<string>('all');
  const [drugSearchQuery, setDrugSearchQuery] = useState<string>('');
  const [drugFoldFilter, setDrugFoldFilter] = useState<'all' | 'known' | 'test'>('all');
  const [showAllPresets, setShowAllPresets] = useState<boolean>(false);
  const [showModelConfig, setShowModelConfig] = useState<boolean>(false);

  // Loading & Result states
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStepText, setLoadingStepText] = useState<string>('正在准备解算环境...');
  const [isProfiling, setIsProfiling] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<DTIPredictionResult | null>(null);
  const [predictionIdentity, setPredictionIdentity] = useState<{smiles: string; target: string} | null>(null);
  const [profileModelName, setProfileModelName] = useState('');
  const [biophysicsInsights, setBiophysicsInsights] = useState<BiophysicsInsights | null>(null);
  const [profileResults, setProfileResults] = useState<KinomeProfileItem[] | null>(null);
  const [activeTab, setActiveTab] = useState<'predict' | 'profiling' | 'leaderboard'>('predict');
  const [resultFacetTab, setResultFacetTab] = useState<'pocket' | 'biophysics' | 'kinome' | 'dispatch'>('pocket');
  const [cartToast, setCartToast] = useState<boolean>(false);
  const [asyncNotice, setAsyncNotice] = useState<string | null>(null);
  const [isSubmittingAsync, setIsSubmittingAsync] = useState<boolean>(false);

  // ADMET modal states
  const [admetModalOpen, setAdmetModalOpen] = useState<boolean>(false);
  const [currentAdmet, setCurrentAdmet] = useState<ADMETProperties | null>(null);
  const [admetLoading, setAdmetLoading] = useState<boolean>(false);

  // 60+ Clinical Targets Modal states
  const [isTargetModalOpen, setIsTargetModalOpen] = useState<boolean>(false);
  const [customTargetSymbol, setCustomTargetSymbol] = useState<string>('ABL1');

  // Pipeline Modals
  const [isDeNovoModalOpen, setIsDeNovoModalOpen] = useState<boolean>(false);
  const [isRetroModalOpen, setIsRetroModalOpen] = useState<boolean>(false);
  const [retroSmiles, setRetroSmiles] = useState<string>('');
  const [retroMolName, setRetroMolName] = useState<string>('目标小分子');
  const [isScreeningModalOpen, setIsScreeningModalOpen] = useState<boolean>(false);

  // Academic Report & Wetlab Dispatch Modals
  const [academicReportOpen, setAcademicReportOpen] = useState<boolean>(false);
  const [academicReportData, setAcademicReportData] = useState<AcademicReportResult | null>(null);
  const [academicReportLoading, setAcademicReportLoading] = useState<boolean>(false);

  const [wetlabDispatchOpen, setWetlabDispatchOpen] = useState<boolean>(false);
  const [wetlabDispatchData, setWetlabDispatchData] = useState<WetlabDispatchResult | null>(null);
  const [wetlabDispatchLoading, setWetlabDispatchLoading] = useState<boolean>(false);

  // Filtered lists
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

  const isModelReady = useMemo(() => {
    return !modelsLoading && !modelsError && models.length > 0 && models.some(m => m.id === modelName);
  }, [modelsLoading, modelsError, models, modelName]);

  // 实时配体结构合法性校验 (Real-time SMILES Validation)
  const smilesValidation = useMemo(() => {
    const s = drugSmiles.trim();
    if (!s) return { isValid: false, status: 'empty', msg: '待输入' };
    if (s.length < 2) return { isValid: false, status: 'error', msg: '长度过短' };
    let openCount = 0;
    for (const c of s) {
      if (c === '(') openCount++;
      if (c === ')') openCount--;
      if (openCount < 0) return { isValid: false, status: 'error', msg: '括号未闭合' };
    }
    if (openCount !== 0) return { isValid: false, status: 'error', msg: '括号未闭合' };
    return { isValid: true, status: 'valid', msg: '结构式合规' };
  }, [drugSmiles]);

  // 实时靶点氨基酸序列校验 (Real-time Kinase Sequence Validation)
  const sequenceValidation = useMemo(() => {
    const clean = targetSequence.replace(/\s+/g, '').toUpperCase();
    if (!clean) return { isValid: false, length: 0, status: 'empty', msg: '待输入' };
    if (clean.length < 10) return { isValid: false, length: clean.length, status: 'error', msg: '过短 (<10 aa)' };
    if (clean.length > 4096) return { isValid: false, length: clean.length, status: 'error', msg: '超长 (>4096 aa)' };
    const invalidChars = clean.replace(/[ACDEFGHIKLMNPQRSTVWY]/g, '');
    if (invalidChars.length > 0) {
      return { 
        isValid: false, 
        length: clean.length, 
        status: 'error', 
        msg: `含非法残基 [${Array.from(new Set(invalidChars)).slice(0, 3).join('')}]` 
      };
    }
    return { isValid: true, length: clean.length, status: 'valid', msg: `${clean.length} aa 合规` };
  }, [targetSequence]);

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
          const bilinear = data.find(m => m.id === 'bilinear_esm2_interaction');
          if (bilinear) return bilinear.id;
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
    });
  }, []);

  useEffect(() => {
    // 1. Fetch Drugs
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

    // 2. Fetch Targets
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

  // 同步来自其他工作台（如智能体/分子库）的实体与靶点输入
  useEffect(() => {
    const routeState = location.state as {
      drugSmiles?: string;
      drugName?: string;
      targetSymbol?: string;
      targetSequence?: string;
    } | null;

    if (routeState?.drugSmiles) {
      setDrugSmiles(routeState.drugSmiles);
      userDrugInteractedRef.current = true;
      setSelectedDrugId('');
    } else if (activeEntity?.kind === 'small_molecule' && activeEntity.smiles && !userDrugInteractedRef.current) {
      setDrugSmiles(activeEntity.smiles);
      setSelectedDrugId('');
    }

    if (routeState?.targetSequence) {
      setTargetSequence(routeState.targetSequence);
      userTargetInteractedRef.current = true;
      if (routeState.targetSymbol) {
        setCustomTargetSymbol(routeState.targetSymbol);
        setSelectedTargetId(routeState.targetSymbol);
      }
    } else if (activeTarget?.sequence && !userTargetInteractedRef.current) {
      setTargetSequence(activeTarget.sequence);
      setCustomTargetSymbol(activeTarget.id || activeTarget.standardDisplayName);
      setSelectedTargetId(activeTarget.id);
    }
  }, [location.state, activeEntity, activeTarget]);

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
    if (targetId === 'custom') return;
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
    setLoadingStepText('1. 正在提取小分子 Morgan 指纹与靶点深度表征...');

    try {
      const stepTimer1 = setTimeout(() => {
        setLoadingStepText('2. 正在执行 Bilinear 双线性注意力交叉与亲和力回归...');
      }, 700);

      const stepTimer2 = setTimeout(() => {
        setLoadingStepText('3. 正在解算 3D 口袋几何诱导契合与 MM-GBSA 自由能分解...');
      }, 1500);

      // 1. DTI Affinity Prediction
      const res = await predictDTIAffinity(smilesToUse.trim(), seqToUse.trim(), selectedModel);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setResult(res);
      setPredictionIdentity({smiles: smilesToUse.trim(), target: targets.find(t => t.sequence === seqToUse)?.id || customTargetSymbol});

      // 2. Parallel / Async Biophysics Insights
      fetchBiophysicsInsights(smilesToUse.trim(), seqToUse.trim())
        .then(bio => setBiophysicsInsights(bio))
        .catch(bioErr => console.warn('Biophysics insights notice:', bioErr));

    } catch (err: any) {
      setResult(null);
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

  // Keyboard shortcut Ctrl+Enter
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (!isLoading && isModelReady && drugSmiles.trim() && targetSequence.trim()) {
          e.preventDefault();
          handlePredict();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isLoading, isModelReady, drugSmiles, targetSequence, modelName]);

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

  const handleResetAllInputs = () => {
    userDrugInteractedRef.current = false;
    userTargetInteractedRef.current = false;
    pendingPresetTargetIdRef.current = null;
    setDrugSmiles('');
    setSelectedDrugId('');
    setTargetSequence('');
    setSelectedTargetId('');
    setCustomTargetSymbol('ABL1');
    setResult(null);
    setBiophysicsInsights(null);
    setProfileResults(null);
    setErrorMsg(null);
  };

  const handleTriggerLeadOptimizer = () => {
    if (drugSmiles) {
      const molName = customTargetSymbol ? `${customTargetSymbol} 结合配体` : '候选小分子';
      setActiveSmallMolecule(drugSmiles, molName, "DTI Studio");
      if (targetSequence) {
        setActiveTarget({
          id: customTargetSymbol || selectedTargetId || 'Target',
          standardDisplayName: customTargetSymbol || selectedTargetId || 'Target',
          sequence: targetSequence,
          source: "DTI Studio"
        });
      }
      navigate('/evolution', {
        state: {
          drugSmiles: drugSmiles,
          drugName: molName,
          targetSymbol: customTargetSymbol || selectedTargetId || 'Target',
          targetSequence: targetSequence
        }
      });
    } else {
      navigate('/evolution');
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

  const handleRunAsyncFullProfiling = async () => {
    if (!isModelReady) {
      setErrorMsg('DTI 模型未就绪，无法提交后台全谱扫描。');
      return;
    }
    if (!drugSmiles.trim()) {
      setErrorMsg('请先提供小分子 SMILES。');
      return;
    }
    setErrorMsg(null);
    setIsSubmittingAsync(true);
    try {
      const resp = await submitAsyncTask('kinase_profiling', {
        drug_smiles: drugSmiles.trim(),
        model_name: modelName,
        panel: 'all'
      });
      setAsyncNotice(`已成功提交 379 激酶全库后台扫描任务 (ID: ${resp.task_id})，可点击顶部导航【任务中心】实时追踪进度与取消！`);
      setTimeout(() => setAsyncNotice(null), 8000);
    } catch (err: any) {
      setErrorMsg(err.message || '提交异步任务失败');
    } finally {
      setIsSubmittingAsync(false);
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
    const record: Record<string, unknown> = { 
      ...result, 
      export_schema_version: 2, 
      prediction_score_band: predictionScoreBand(result.predicted_pkd), 
      research_evidence: source ?? { status: 'unavailable', external_evaluation_completed: null, admitted_count: null }, 
      research_use: `${evidenceNotice(source)} ${PREDICTION_SCOPE_NOTICE}`, 
      model_limitations: modelLimitationNotice(result.model_used, source, result.provenance.model_sha256) 
    };
    delete record.affinity_tier;
    delete record.affinity_tier_code;
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `dti_prediction_${Date.now()}.json`;
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleAddToCart = () => {
    if (!result || !predictionIdentity) return;
    const added = addToCart({
      sequence: predictionIdentity.smiles,
      smiles: predictionIdentity.smiles,
      name: drugs.find(d => d.id === selectedDrugId)?.name || customTargetSymbol || '候选配体分子',
      pkd: result.predicted_pkd,
      target_symbol: predictionIdentity.target,
      model_used: result.model_used,
      kind: 'small_molecule',
      item_type: 'small_molecule'
    });
    setCartToast(true);
    setTimeout(() => setCartToast(false), 2000);
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

  const handleOpenRetrosynthesis = (smi: string, name: string) => {
    setRetroSmiles(smi);
    setRetroMolName(name);
    setIsRetroModalOpen(true);
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

  const handleCleanSequence = () => {
    setTargetSequence(prev => prev.replace(/\s+/g, '').toUpperCase());
  };

  const handleGenerateAcademicReport = async () => {
    if (!result) return;
    setAcademicReportLoading(true);
    setAcademicReportOpen(true);
    try {
      const report = await fetchAcademicReport({
        model_used: result.model_used,
        target_name: customTargetSymbol || targets.find(t => t.id === selectedTargetId)?.id || 'Target Kinase',
        baseline: {
          drug_name: drugs.find(d => d.id === selectedDrugId)?.name || 'Lead Molecule',
          smiles: drugSmiles,
          predicted_pkd: result.predicted_pkd,
          predicted_kd_nM: result.predicted_kd_nM,
        },
        candidates: [],
        biophysics: biophysicsInsights ? {
          binding_mode: biophysicsInsights.binding_mode,
          binding_mode_label: biophysicsInsights.binding_mode_label,
          mmgbsa: biophysicsInsights.mmgbsa,
          dfg_flip_penalty_kcal: biophysicsInsights.dfg_flip_penalty_kcal,
        } : undefined,
      });
      setAcademicReportData(report);
    } catch (err: any) {
      setErrorMsg(err.message || '生成学术报告失败');
    } finally {
      setAcademicReportLoading(false);
    }
  };

  const handleGenerateWetlabDispatch = async () => {
    if (!result) return;
    setWetlabDispatchLoading(true);
    setWetlabDispatchOpen(true);
    try {
      const dispatch = await generateWetlabDispatch({
        target_name: customTargetSymbol || targets.find(t => t.id === selectedTargetId)?.id || 'Target Kinase',
        baseline: {
          drug_name: drugs.find(d => d.id === selectedDrugId)?.name || 'Lead Molecule',
          smiles: drugSmiles,
          predicted_pkd: result.predicted_pkd,
          predicted_kd_nM: result.predicted_kd_nM,
        },
        candidates: [
          {
            name: drugs.find(d => d.id === selectedDrugId)?.name || 'Lead Derivative 1',
            smiles: drugSmiles,
            predicted_pkd: result.predicted_pkd,
            predicted_kd_nM: result.predicted_kd_nM,
          }
        ],
        plate_barcode: `PLT-${Date.now().toString().slice(-6)}`
      });
      setWetlabDispatchData(dispatch);
    } catch (err: any) {
      setErrorMsg(err.message || '生成投产清单失败');
    } finally {
      setWetlabDispatchLoading(false);
    }
  };

  return (
    <div className="studio-workspace space-y-4">
      {/* 顶部主横幅与工作台模式导航 */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-4 sm:p-5 rounded-2xl border border-indigo-700/40 shadow-md relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-wrap items-center justify-between gap-3 relative z-10">
          <div>
            <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck size={11} />
                DTI RESEARCH BENCHMARK
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/20 text-blue-200 border border-blue-500/30 flex items-center gap-1">
                <CheckCircle2 size={11} />
                DAVIS 激酶全矩阵 (25,772)
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-200 border border-amber-500/30 flex items-center gap-1">
                <Award size={11} />
                突破双冷退化 · CI 0.7514
              </span>
            </div>
            <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              药物–靶点亲和力预测
            </h2>
            <p className="text-xs text-slate-300 mt-0.5 max-w-2xl leading-relaxed">
              选择或输入分子与靶点，运行预测，即刻联动 3D 催化口袋与 MM-GBSA 第一性原理能量透视。
            </p>
          </div>
          
          <div className="flex flex-wrap gap-1.5 bg-slate-900/60 p-1 rounded-xl border border-white/10">
            <button
              onClick={() => setActiveTab('predict')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'predict' 
                  ? 'bg-sky-600 text-white shadow-xs' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/80'
              }`}
            >
              亲和力预测
            </button>
            <button
              onClick={() => setActiveTab('profiling')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'profiling' 
                  ? 'bg-sky-600 text-white shadow-xs' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/80'
              }`}
            >
              激酶选择性谱 (Kinome)
            </button>
            <button
              onClick={() => setActiveTab('leaderboard')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'leaderboard' 
                  ? 'bg-sky-600 text-white shadow-xs' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/80'
              }`}
            >
              已注册模型与基准
            </button>
          </div>
        </div>
      </div>

      {/* 外部证据状态复核面板 */}
      <DTIEvidencePanel modelId={modelName} modelHash={models.find(model => model.id === modelName)?.model_sha256} />

      {/* 亲和力预测主工作区 (双栏联动全视窗仪表盘) */}
      {activeTab === 'predict' && (
        <div className="space-y-4">
          
          {/* 经典案例极速切换条 (Sleek Presets Bar) */}
          <div className="bg-white/80 dark:bg-slate-900/80 p-2.5 sm:p-3 rounded-xl border border-slate-200/80 dark:border-slate-800 shadow-2xs space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="p-1 rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <Zap size={14} />
                </span>
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  经典肿瘤激酶配对
                </span>
                <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">
                  (点击快速载入 / ⚡ 点击极速推断)
                </span>
              </div>

              <div className="flex items-center gap-1 overflow-x-auto text-[11px] no-scrollbar">
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
                        ? 'bg-sky-600 text-white font-bold'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Presets Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
              {filteredPresets.map((item, idx) => {
                const isCurrent = drugSmiles === item.smiles;
                return (
                  <div
                    key={idx}
                    className={`p-2 rounded-lg border text-left transition-all relative flex items-center justify-between gap-1.5 ${
                      isCurrent
                        ? 'bg-sky-50 dark:bg-sky-950/40 border-sky-400 ring-1 ring-sky-400/50 shadow-2xs'
                        : 'bg-slate-50/60 dark:bg-slate-800/40 border-slate-200/80 dark:border-slate-700/60 hover:border-sky-300 dark:hover:border-sky-700'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(item, false)}
                      className="min-w-0 flex-1 text-left cursor-pointer"
                      title={`${item.desc} (点击载入输入框)`}
                    >
                      <div className="flex items-center gap-1">
                        <span className="text-[9px] font-semibold px-1 py-0.2 rounded bg-slate-200/80 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-mono">
                          {item.categoryLabel.split('/')[0]}
                        </span>
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                          {item.label.split('(')[0]}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 truncate mt-0.5">
                        {item.drugName} → {item.targetName}
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleApplyPreset(item, true)}
                      className="px-1.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white text-[10px] font-bold shrink-0 transition-colors cursor-pointer flex items-center gap-0.5 shadow-2xs"
                      title="直接载入并立即运行预测"
                    >
                      <Zap size={10} />
                      <span>推断</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 左右分屏核心联动工作台 (Desktop Dual-Pane Workbench) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:h-[calc(100vh-240px)] lg:min-h-[640px]">
            
            {/* 左栏：参数输入与控制台 (Left Console, 5 cols) */}
            <div className="lg:col-span-5 flex flex-col h-full bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
              
              {/* 控制台 4 步工作流引导条 (Workflow Pipeline Stepper) */}
              <div className="px-3.5 py-2 border-b border-slate-200/80 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-850/70 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-1 text-[11px]">
                  {/* Step 1 */}
                  <span className={`px-2 py-0.5 rounded-md font-medium flex items-center gap-1 transition-colors ${
                    smilesValidation.isValid
                      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-bold'
                      : 'bg-slate-200/70 dark:bg-slate-800 text-slate-500'
                  }`}>
                    <span className="w-3.5 h-3.5 rounded-full bg-current/20 flex items-center justify-center text-[9px] font-bold">1</span>
                    <span>配体</span>
                  </span>
                  <span className="text-slate-300 dark:text-slate-700">→</span>
                  
                  {/* Step 2 */}
                  <span className={`px-2 py-0.5 rounded-md font-medium flex items-center gap-1 transition-colors ${
                    sequenceValidation.isValid
                      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-bold'
                      : 'bg-slate-200/70 dark:bg-slate-800 text-slate-500'
                  }`}>
                    <span className="w-3.5 h-3.5 rounded-full bg-current/20 flex items-center justify-center text-[9px] font-bold">2</span>
                    <span>靶点</span>
                  </span>
                  <span className="text-slate-300 dark:text-slate-700">→</span>
                  
                  {/* Step 3 */}
                  <span className="px-2 py-0.5 rounded-md font-medium flex items-center gap-1 bg-sky-500/15 text-sky-700 dark:text-sky-300 font-bold">
                    <span className="w-3.5 h-3.5 rounded-full bg-current/20 flex items-center justify-center text-[9px] font-bold">3</span>
                    <span>模型</span>
                  </span>
                  <span className="text-slate-300 dark:text-slate-700">→</span>
                  
                  {/* Step 4 */}
                  <span className={`px-2 py-0.5 rounded-md font-medium flex items-center gap-1 transition-colors ${
                    result
                      ? 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 font-bold'
                      : 'bg-slate-200/70 dark:bg-slate-800 text-slate-400'
                  }`}>
                    <span className="w-3.5 h-3.5 rounded-full bg-current/20 flex items-center justify-center text-[9px] font-bold">4</span>
                    <span>{result ? '已透视' : '推断'}</span>
                  </span>
                </div>

                {/* 一键重置清空按钮 */}
                {(drugSmiles || targetSequence) && (
                  <button
                    type="button"
                    onClick={handleResetAllInputs}
                    className="text-[10px] text-slate-400 hover:text-rose-500 dark:hover:text-rose-400 flex items-center gap-1 transition-colors cursor-pointer px-1.5 py-0.5 rounded hover:bg-rose-50 dark:hover:bg-rose-950/40"
                    title="重置当前分子式与靶点序列"
                  >
                    <RefreshCw size={10} />
                    <span>重置</span>
                  </button>
                )}
              </div>

              {/* 独立顺畅滚动的输入表单区 */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                
                {/* 1. 小分子配体卡片 */}
                <div className="p-3.5 rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-850/40 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="w-4 h-4 rounded-full bg-sky-600 text-white flex items-center justify-center text-[10px] font-bold">1</span>
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">小分子激酶抑制剂配体</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setIsSketcherOpen(true)}
                        className="px-2 py-0.5 rounded text-[10px] bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 border border-sky-200 dark:border-sky-800 hover:bg-sky-100 transition-colors flex items-center gap-1 cursor-pointer"
                        title="手绘画板编辑分子骨架"
                      >
                        <Palette size={11} />
                        <span>画板</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleOpenAdmet}
                        className="px-2 py-0.5 rounded text-[10px] bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 transition-colors flex items-center gap-1 cursor-pointer"
                        title="多维 ADMET 成药性雷达"
                      >
                        <ShieldCheck size={11} />
                        <span>ADMET</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setShow2DStructure(!show2DStructure)}
                        className="px-2 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors flex items-center gap-1 cursor-pointer"
                        title="切换 2D 骨架渲染"
                      >
                        <Atom size={11} />
                        <span>{show2DStructure ? '收起2D' : '2D结构'}</span>
                      </button>
                    </div>
                  </div>

                  {/* 常用 FDA 药物快捷 Chips */}
                  <div className="flex items-center gap-1 overflow-x-auto text-[10px] py-0.5 no-scrollbar">
                    <span className="text-slate-400 shrink-0 font-medium">常用:</span>
                    {[
                      { name: '达沙替尼 (ABL1)', smi: 'CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO' },
                      { name: '吉非替尼 (EGFR)', smi: 'COC1=C(OCC2CCNCC2)C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl' },
                      { name: '伊马替尼 (BCR-ABL)', smi: 'CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5' },
                      { name: '索拉非尼 (BRAF)', smi: 'CNC(=O)C1=NC=CC(=C1)OC2=CC=C(C=C2)NC(=O)NC3=CC(=C(C=C3)Cl)C(F)(F)F' },
                      { name: '奥希替尼 (EGFR)', smi: 'CN1CCN(CC1)C2=CC(=C(C=C2)NC(=O)C=C)NC3=NC=CC(=N3)C4=CN(C5=CC=CC=C54)C' },
                      { name: '维莫非尼 (BRAF)', smi: 'CCCS(=O)(=O)NC1=C(C(=C(C=C1)F)C(=O)C2=CNC3=C2C=C(C=N3)C4=CC=C(C=C4)Cl)F' },
                    ].map(d => (
                      <button
                        key={d.name}
                        type="button"
                        onClick={() => {
                          userDrugInteractedRef.current = true;
                          setDrugSmiles(d.smi);
                          setSelectedDrugId('');
                        }}
                        className={`px-1.5 py-0.5 rounded shrink-0 transition-colors cursor-pointer ${
                          drugSmiles === d.smi 
                            ? 'bg-sky-600 text-white font-bold' 
                            : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200/80 dark:border-slate-700 hover:border-sky-400'
                        }`}
                      >
                        {d.name.split(' ')[0]}
                      </button>
                    ))}
                  </div>

                  {/* DAVIS 基准库下拉选择 */}
                  <div className="flex gap-1.5">
                    <select
                      value={selectedDrugId}
                      onChange={(e) => handleDrugChange(e.target.value)}
                      className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 font-mono focus-ring"
                    >
                      <option value="">从 DAVIS 基准库挑选 (68 款)...</option>
                      {filteredDrugs.map(d => (
                        <option key={d.id} value={d.id}>
                          {d.name} {d.is_test ? '【折5·盲测试集】' : '【已知训练域】'}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* SMILES 输入框 */}
                  <div>
                    <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1">
                      <div className="flex items-center gap-1.5">
                        <span>SMILES 规范分子式：</span>
                        {drugSmiles.trim() && (
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[9px] font-mono font-medium ${
                            smilesValidation.isValid 
                              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' 
                              : 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                          }`}>
                            <span className={`w-1 h-1 rounded-full ${smilesValidation.isValid ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`} />
                            {smilesValidation.msg}
                          </span>
                        )}
                      </div>
                      {drugSmiles && (
                        <button
                          type="button"
                          onClick={() => { userDrugInteractedRef.current = true; setDrugSmiles(''); setSelectedDrugId(''); }}
                          className="hover:text-rose-500 cursor-pointer"
                        >
                          清空
                        </button>
                      )}
                    </div>
                    <textarea
                      value={drugSmiles}
                      onChange={(e) => {
                        userDrugInteractedRef.current = true;
                        setDrugSmiles(e.target.value);
                      }}
                      placeholder="输入小分子 SMILES (如 CC1=C(C(=CC=C1)Cl)NC(=O)...)"
                      rows={2}
                      className={`w-full bg-white dark:bg-slate-900 border rounded-lg p-2 font-mono text-xs text-slate-900 dark:text-slate-100 focus-ring transition-colors ${
                        !drugSmiles.trim() 
                          ? 'border-slate-300 dark:border-slate-700' 
                          : smilesValidation.isValid 
                            ? 'border-emerald-400/80 dark:border-emerald-700/80' 
                            : 'border-rose-400/80 dark:border-rose-700/80'
                      }`}
                    />
                  </div>

                  {/* 2D 预览缩略图 */}
                  {show2DStructure && drugSmiles.trim() && (
                    <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-center">
                      <Molecule2DViewer smiles={drugSmiles} width={260} height={140} />
                    </div>
                  )}
                </div>

                {/* 2. 激酶靶点卡片 */}
                <div className="p-3.5 rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-850/40 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="w-4 h-4 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[10px] font-bold">2</span>
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">激酶靶点催化域序列</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setIsTargetModalOpen(true)}
                        className="px-2 py-0.5 rounded text-[10px] bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 transition-colors flex items-center gap-1 cursor-pointer"
                        title="60+ 临床靶点与耐药突变体知识库"
                      >
                        <Dna size={11} />
                        <span>靶点库</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleCleanSequence}
                        className="px-2 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer"
                        title="清除序列中的空格与非字母换行符"
                      >
                        清洗序列
                      </button>
                    </div>
                  </div>

                  {/* 靶点选择/符号 */}
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-[10px] text-slate-400 block mb-1">靶点目录选择：</span>
                      <select
                        value={selectedTargetId}
                        onChange={(e) => handleTargetChange(e.target.value)}
                        className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-800 dark:text-slate-200 font-mono focus-ring"
                      >
                        <option value="custom">自定义序列 / 突变体</option>
                        {targets.map(t => (
                          <option key={t.id} value={t.id}>
                            {t.id} ({t.length} aa)
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block mb-1">靶点标识代码：</span>
                      <input
                        type="text"
                        value={customTargetSymbol}
                        onChange={(e) => setCustomTargetSymbol(e.target.value)}
                        placeholder="如 ABL1, EGFR..."
                        className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-800 dark:text-slate-200 font-mono focus-ring"
                      />
                    </div>
                  </div>

                  {/* 靶点氨基酸序列 (可折叠防胀屏) */}
                  <div>
                    <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1">
                      <div className="flex items-center gap-1.5">
                        <span>氨基酸单字母序列 ({targetSequence.replace(/\s+/g, '').length} aa)：</span>
                        {targetSequence.trim() && (
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[9px] font-mono font-medium ${
                            sequenceValidation.isValid 
                              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' 
                              : 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                          }`}>
                            <span className={`w-1 h-1 rounded-full ${sequenceValidation.isValid ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`} />
                            {sequenceValidation.msg}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {targetSequence && (
                          <button
                            type="button"
                            onClick={() => { userTargetInteractedRef.current = true; setTargetSequence(''); setSelectedTargetId('custom'); }}
                            className="hover:text-rose-500 cursor-pointer"
                          >
                            清空
                          </button>
                        )}
                        {targetSequence.length > 200 && (
                          <button
                            type="button"
                            onClick={() => setIsSequenceExpanded(!isSequenceExpanded)}
                            className="text-sky-600 dark:text-sky-400 hover:underline cursor-pointer"
                          >
                            {isSequenceExpanded ? '收起预览' : '展开全长'}
                          </button>
                        )}
                      </div>
                    </div>
                    <textarea
                      value={targetSequence}
                      onChange={(e) => {
                        userTargetInteractedRef.current = true;
                        setTargetSequence(e.target.value);
                      }}
                      placeholder="输入靶点催化域序列 (如 MLEICLKLVGCKSKKGLS...)"
                      rows={isSequenceExpanded ? 6 : 2}
                      className={`w-full bg-white dark:bg-slate-900 border rounded-lg p-2 font-mono text-xs text-slate-900 dark:text-slate-100 focus-ring transition-colors ${
                        !targetSequence.trim() 
                          ? 'border-slate-300 dark:border-slate-700' 
                          : sequenceValidation.isValid 
                            ? 'border-emerald-400/80 dark:border-emerald-700/80' 
                            : 'border-rose-400/80 dark:border-rose-700/80'
                      }`}
                    />
                  </div>
                </div>

                {/* 3. 亲和力模型卡片 */}
                <div className="p-3.5 rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-850/40 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">3</span>
                      <span className="text-xs font-bold text-slate-900 dark:text-slate-100">亲和力预测模型引擎</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowModelConfig(!showModelConfig)}
                      className="text-[10px] text-sky-600 dark:text-sky-400 hover:underline flex items-center gap-0.5 cursor-pointer"
                    >
                      <span>{showModelConfig ? '收起切换' : `更多模型 (${models.length})`}</span>
                      <ChevronDown size={11} className={`transition-transform duration-200 ${showModelConfig ? 'rotate-180' : ''}`} />
                    </button>
                  </div>

                  {/* 默认推荐模型高亮条 */}
                  <div className="p-2.5 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-800/80 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-emerald-950 dark:text-emerald-200">
                          {models.find(m => m.id === modelName)?.name || 'Bilinear ESM-2 双线性交叉'}
                        </span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-600 text-white font-bold">
                          默认推荐
                        </span>
                      </div>
                      <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-mono block mt-0.5">
                        突破冷退化 · 双冷基准 CI 0.7514
                      </span>
                    </div>
                    <ShieldCheck size={18} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
                  </div>

                  {/* 展开其他模型供对比 */}
                  {showModelConfig && (
                    <div className="grid grid-cols-1 gap-1.5 pt-1 animate-in fade-in duration-200">
                      {models.map(m => {
                        const isSelected = modelName === m.id;
                        return (
                          <button
                            key={m.id}
                            type="button"
                            onClick={() => setModelName(m.id)}
                            className={`p-2 rounded-lg border text-left text-xs transition-colors cursor-pointer flex items-center justify-between ${
                              isSelected
                                ? 'bg-sky-50 dark:bg-sky-950/40 border-sky-400 text-sky-900 dark:text-sky-100 font-bold'
                                : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                          >
                            <span className="truncate">{m.name}</span>
                            <span className="text-[10px] text-slate-400 font-mono shrink-0 ml-2">{m.badge}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* 4. 研发管线工具箱快捷入口 */}
                <div className="p-3 rounded-xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-850/30 space-y-2">
                  <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block">
                    进阶研发管线快速入口 (Phase 1~3 Pipeline)
                  </span>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      type="button"
                      onClick={() => setIsDeNovoModalOpen(true)}
                      className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-indigo-400 text-left transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      <Sparkles size={14} className="text-indigo-500 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-[11px] font-bold text-slate-800 dark:text-slate-200 truncate">3D 从头生成</div>
                        <div className="text-[9px] text-slate-400">骨架跃迁/耐药突变</div>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleOpenRetrosynthesis(drugSmiles || 'CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)C)C(F)(F)F', customTargetSymbol ? `${customTargetSymbol} 抑制剂` : '当前分子')}
                      className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-400 text-left transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      <TestTube size={14} className="text-emerald-500 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-[11px] font-bold text-slate-800 dark:text-slate-200 truncate">AI 逆合成规划</div>
                        <div className="text-[9px] text-slate-400">商业 CAS 原料</div>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsScreeningModalOpen(true)}
                      className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-sky-400 text-left transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      <Search size={14} className="text-sky-500 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-[11px] font-bold text-slate-800 dark:text-slate-200 truncate">超大规模海选</div>
                        <div className="text-[9px] text-slate-400">Enamine 商业分子库</div>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={handleOpenAdmet}
                      className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-amber-400 text-left transition-colors cursor-pointer flex items-center gap-1.5"
                    >
                      <ShieldCheck size={14} className="text-amber-500 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-[11px] font-bold text-slate-800 dark:text-slate-200 truncate">ADMET 毒理雷达</div>
                        <div className="text-[9px] text-slate-400">hERG / Caco-2 安全</div>
                      </div>
                    </button>
                  </div>
                </div>

              </div>

              {/* 底部常驻悬浮操作条 (Sticky Bottom Action Bar) */}
              <div className="p-3 border-t border-slate-200/80 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-900/90 flex items-center justify-between gap-3 shrink-0">
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                    {isLoading ? '正在进行亲和力与物理透视解算…' : '配置完成，可立即启动推断'}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    快捷键: Ctrl + Enter / ⌘ + Enter
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handlePredict}
                  disabled={isLoading || !isModelReady || !drugSmiles.trim() || !targetSequence.trim()}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold text-xs shadow-md shadow-sky-500/20 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                >
                  {isLoading ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>解算中…</span>
                    </>
                  ) : (
                    <>
                      <FlaskConical size={14} />
                      <span>开始预测</span>
                    </>
                  )}
                </button>
              </div>

            </div>

            {/* 右栏：结果透视与可视化分析中心 (Right Analysis Center, 7 cols) */}
            <div className="lg:col-span-7 flex flex-col h-full bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
              
              {/* 透视中心顶部标题条 */}
              <div className="px-4 py-2.5 border-b border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-850/60 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <Activity size={14} className="text-sky-500" />
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                    实时透视中心 · 亲和力与结构分析
                  </span>
                </div>
                {result && (
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={handleAddToCart}
                      className="px-2 py-1 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 transition-colors flex items-center gap-1 cursor-pointer"
                      title="将当前分子与预测评分暂存至分子库"
                    >
                      <ShoppingCart size={11} />
                      <span>{cartToast ? '✓ 已暂存' : '存入分子库'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleExportPrediction}
                      className="px-2 py-1 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 transition-colors flex items-center gap-1 cursor-pointer"
                      title="导出预测结果完整 JSON 数据"
                    >
                      <Download size={11} />
                      <span>导出 JSON</span>
                    </button>
                  </div>
                )}
              </div>

              {/* 状态 1: 加载解算过程中 (Loading Skeleton) */}
              {isLoading ? (
                <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-5 animate-in fade-in duration-200">
                  <div className="relative">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-xl shadow-sky-500/25 animate-pulse">
                      <Sparkles size={28} />
                    </div>
                    <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-slate-900 border-2 border-white flex items-center justify-center">
                      <div className="w-3 h-3 border-2 border-sky-400 border-t-transparent rounded-full animate-spin" />
                    </div>
                  </div>

                  <div className="text-center space-y-1.5 max-w-sm">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      科学解算推进中
                    </h4>
                    <p className="text-xs text-sky-600 dark:text-sky-400 font-mono transition-all">
                      {loadingStepText}
                    </p>
                  </div>

                  {/* Skeletons */}
                  <div className="w-full max-w-md space-y-3 pt-2">
                    <div className="h-20 rounded-xl bg-slate-100 dark:bg-slate-800/60 animate-pulse" />
                    <div className="h-44 rounded-xl bg-slate-100 dark:bg-slate-800/60 animate-pulse" />
                  </div>
                </div>
              ) : result ? (
                /* 状态 2: 结果呈现状态 (Result Presentation with Facet Tabs) */
                <div className="flex-1 flex flex-col overflow-hidden">
                  
                  {/* 常驻顶部 KPI 核心指标条 */}
                  <div className="p-4 bg-gradient-to-r from-sky-50/60 via-white to-indigo-50/40 dark:from-slate-900/90 dark:via-slate-900/60 dark:to-slate-950/90 border-b border-slate-200/80 dark:border-slate-800 shrink-0">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      
                      {/* pKd 巨大字号核心卡 */}
                      <div className="flex items-baseline gap-2">
                        <span className="text-4xl sm:text-5xl font-black text-sky-600 dark:text-sky-400 font-mono tracking-tight glow-cyan-text">
                          {result.predicted_pkd.toFixed(3)}
                        </span>
                        <div className="flex flex-col">
                          <span className="text-xs font-mono font-bold text-slate-500">pKd 评分</span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            Kd ≈ {result.predicted_kd_nM < 1000 
                              ? `${result.predicted_kd_nM.toFixed(1)} nM` 
                              : `${(result.predicted_kd_nM / 1000).toFixed(2)} μM`}
                          </span>
                        </div>
                      </div>

                      {/* 强弱评级与标尺 */}
                      <div className="flex flex-col items-end gap-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                            result.predicted_pkd >= 7
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border-emerald-300'
                              : result.predicted_pkd >= 6
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border-amber-300'
                              : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-300'
                          }`}>
                            {predictionScoreBand(result.predicted_pkd)}
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200/60 dark:border-slate-700">
                            {result.model_used.toUpperCase()}
                          </span>
                        </div>

                        {/* Continuum Slider Bar */}
                        <div className="w-36 space-y-0.5">
                          <div className="relative w-full h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                            <div className="absolute inset-0 bg-gradient-to-r from-slate-400 via-amber-400 to-emerald-500 opacity-80" />
                            <div 
                              className="absolute top-0 bottom-0 w-1.5 bg-slate-950 dark:bg-white shadow-sm -translate-x-1/2"
                              style={{ left: `${Math.max(0, Math.min(100, ((result.predicted_pkd - 5.0) / 5.5) * 100))}%` }}
                            />
                          </div>
                          <div className="flex justify-between text-[8px] font-mono text-slate-400">
                            <span>5.0</span>
                            <span>7.0</span>
                            <span>10.5</span>
                          </div>
                        </div>
                      </div>

                    </div>
                  </div>

                  {/* 下游高频行动推荐条 (Action Chain Quick Bar) */}
                  <div className="px-4 py-2 bg-sky-500/5 dark:bg-sky-950/20 border-b border-sky-100 dark:border-sky-950/50 flex flex-wrap items-center justify-between gap-2 shrink-0">
                    <div className="flex items-center gap-2">
                      <span className="flex h-2 w-2 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
                      </span>
                      <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                        智能后续行动链：
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 text-xs">
                      {/* 1. 先导物改构 */}
                      <button
                        type="button"
                        onClick={handleTriggerLeadOptimizer}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium shadow-xs transition-colors cursor-pointer"
                        title="携带当前分子与亲和力靶点，直接转入先导物优化器"
                      >
                        <Sparkles size={13} />
                        <span>一键先导物改构</span>
                      </button>

                      {/* 2. 激酶全景选择性 */}
                      <button
                        type="button"
                        onClick={() => setResultFacetTab('kinome')}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-medium transition-colors cursor-pointer ${
                          resultFacetTab === 'kinome'
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:border-indigo-400'
                        }`}
                        title="查看当前配体对人源激酶组的结合选择性靶向树"
                      >
                        <Target size={13} />
                        <span>人源激酶选择谱</span>
                      </button>

                      {/* 3. 学术证据报告 */}
                      <button
                        type="button"
                        onClick={handleGenerateAcademicReport}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 hover:border-sky-400 font-medium transition-colors cursor-pointer"
                        title="生成符合顶级期刊标准的多模态学术图谱与证据链"
                      >
                        <FileText size={13} />
                        <span>学术图谱报告</span>
                      </button>

                      {/* 4. 湿实验派单 */}
                      <button
                        type="button"
                        onClick={handleGenerateWetlabDispatch}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 hover:border-emerald-400 font-medium transition-colors cursor-pointer"
                        title="生成 SPR / 激酶活性测定微孔板实验投产指令单"
                      >
                        <Beaker size={13} />
                        <span>湿实验投产单</span>
                      </button>
                    </div>
                  </div>

                  {/* 4 大分面选项卡 (Facet Tabs Bar) */}
                  <div className="px-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 flex items-center gap-1 overflow-x-auto shrink-0 no-scrollbar">
                    <button
                      type="button"
                      onClick={() => setResultFacetTab('pocket')}
                      className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                        resultFacetTab === 'pocket'
                          ? 'border-sky-500 text-sky-600 dark:text-sky-400 font-bold'
                          : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      <Atom size={13} />
                      <span>3D 催化口袋与结合位姿</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setResultFacetTab('biophysics')}
                      className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                        resultFacetTab === 'biophysics'
                          ? 'border-sky-500 text-sky-600 dark:text-sky-400 font-bold'
                          : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      <Flame size={13} />
                      <span>生物物理热力学 (MM-GBSA)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setResultFacetTab('kinome')}
                      className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                        resultFacetTab === 'kinome'
                          ? 'border-sky-500 text-sky-600 dark:text-sky-400 font-bold'
                          : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      <BarChart3 size={13} />
                      <span>激酶组选择性 (Kinome)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setResultFacetTab('dispatch')}
                      className={`px-3 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                        resultFacetTab === 'dispatch'
                          ? 'border-sky-500 text-sky-600 dark:text-sky-400 font-bold'
                          : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                      }`}
                    >
                      <FileText size={13} />
                      <span>下游决策与投产清单</span>
                    </button>
                  </div>

                  {/* 选项卡内容区 (Scrollable Content Body) */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    
                    {/* Tab 1: 3D 催化口袋 */}
                    {resultFacetTab === 'pocket' && (
                      <div className="space-y-3 animate-in fade-in duration-150">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-slate-800 dark:text-slate-200">
                            3D 激酶微观催化口袋与关键残基对齐
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            靶点: {customTargetSymbol || 'ABL1'} · 配体: {drugs.find(d => d.id === selectedDrugId)?.name || 'Dasatinib'}
                          </span>
                        </div>

                        {/* 3D 渲染器 */}
                        <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden bg-slate-950">
                          <KinasePocketViewer3D
                            targetName={customTargetSymbol || targets.find(t => t.id === selectedTargetId)?.id || 'ABL1'}
                            drugName={drugs.find(d => d.id === selectedDrugId)?.name || 'Dasatinib'}
                            drugSmiles={drugSmiles}
                            className="w-full"
                          />
                        </div>

                        {/* 残基微观交互与诱导契合提示 */}
                        {biophysicsInsights && (
                          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <span className="text-[10px] text-slate-400 block">构象结合模式：</span>
                              <span className="font-bold text-slate-800 dark:text-slate-200 mt-0.5 block">
                                {biophysicsInsights.preferred_conformation}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-400 block">门控残基 Clash 惩罚：</span>
                              <span className="font-mono font-bold text-slate-800 dark:text-slate-200 mt-0.5 block">
                                {biophysicsInsights.gatekeeper_clash.toFixed(2)} kcal
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Tab 2: 生物物理热力学 MM-GBSA */}
                    {resultFacetTab === 'biophysics' && (
                      <div className="space-y-3 animate-in fade-in duration-150">
                        {biophysicsInsights ? (
                          <div className="space-y-3">
                            <div className="p-3.5 rounded-xl bg-gradient-to-br from-indigo-50/40 via-white to-blue-50/30 dark:from-slate-900/90 dark:via-indigo-950/30 dark:to-slate-900/90 border border-indigo-200/80 dark:border-indigo-900/60 space-y-3">
                              <div className="flex items-center justify-between border-b border-indigo-100 dark:border-indigo-900/40 pb-2">
                                <span className="text-xs font-bold text-indigo-950 dark:text-indigo-200 flex items-center gap-1.5">
                                  <Flame size={13} className="text-amber-500" />
                                  <span>第一性原理 MM-GBSA 结合自由能物理分解</span>
                                </span>
                                <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                                  ΔG = {biophysicsInsights.mmgbsa.delta_g_bind.toFixed(2)} kcal/mol
                                </span>
                              </div>

                              {/* 4 维能量分解台阶 Chips */}
                              <div className="grid grid-cols-4 gap-1.5 text-center font-mono text-[10px]">
                                <div className="p-2 rounded-lg bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200/60 dark:border-emerald-800/40">
                                  <span className="text-emerald-700 dark:text-emerald-400 block text-[9px]">ΔEvdw (引力)</span>
                                  <span className="font-bold text-xs text-emerald-900 dark:text-emerald-200">{biophysicsInsights.mmgbsa.delta_e_vdw.toFixed(1)}</span>
                                </div>
                                <div className="p-2 rounded-lg bg-sky-50/60 dark:bg-sky-950/30 border border-sky-200/60 dark:border-sky-800/40">
                                  <span className="text-sky-700 dark:text-sky-400 block text-[9px]">ΔEelec (静电)</span>
                                  <span className="font-bold text-xs text-sky-900 dark:text-sky-200">{biophysicsInsights.mmgbsa.delta_e_elec.toFixed(1)}</span>
                                </div>
                                <div className="p-2 rounded-lg bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-800/40">
                                  <span className="text-amber-700 dark:text-amber-400 block text-[9px]">ΔGsolv (溶剂)</span>
                                  <span className="font-bold text-xs text-amber-900 dark:text-amber-200">{(biophysicsInsights.mmgbsa.delta_g_gb + biophysicsInsights.mmgbsa.delta_g_sa).toFixed(1)}</span>
                                </div>
                                <div className="p-2 rounded-lg bg-rose-50/60 dark:bg-rose-950/30 border border-rose-200/60 dark:border-rose-800/40">
                                  <span className="text-rose-700 dark:text-rose-400 block text-[9px]">-TΔS (熵罚)</span>
                                  <span className="font-bold text-xs text-rose-900 dark:text-rose-200">{biophysicsInsights.mmgbsa.minus_t_delta_s.toFixed(1)}</span>
                                </div>
                              </div>

                              <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-500 font-mono pt-1">
                                <div>可旋转单键自由度: {biophysicsInsights.mmgbsa.rotatable_bonds} 键</div>
                                <div className="text-right">埋藏疏水 SASA: {biophysicsInsights.mmgbsa.buried_sasa.toFixed(1)} Å²</div>
                              </div>
                            </div>

                            {/* 拓扑域与数据无泄漏诊断 */}
                            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-850/60 border border-slate-200 dark:border-slate-800 space-y-2">
                              <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
                                <span className="flex items-center gap-1.5">
                                  <ShieldCheck size={13} className="text-emerald-500" />
                                  <span>泛化拓扑域诊断：</span>
                                </span>
                                <span className="text-sky-600 dark:text-sky-400 font-mono">{result.domain}</span>
                              </div>
                              <p className="text-xs text-slate-500">{result.domain_label}</p>
                              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono pt-1">
                                <div className="p-2 bg-white dark:bg-slate-900 rounded border border-slate-200/60 dark:border-slate-800">
                                  训练药物最高相似度: <strong>{(result.max_drug_similarity_to_train * 100).toFixed(1)}%</strong>
                                </div>
                                <div className="p-2 bg-white dark:bg-slate-900 rounded border border-slate-200/60 dark:border-slate-800">
                                  训练靶点相似度: <strong>{(result.max_target_similarity_to_train * 100).toFixed(1)}%</strong>
                                </div>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                            正在解算生物物理热力学第一性原理自由能...
                          </div>
                        )}
                      </div>
                    )}

                    {/* Tab 3: 激酶组选择性 (Kinome) */}
                    {resultFacetTab === 'kinome' && (
                      <div className="space-y-3 animate-in fade-in duration-150">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                            16 种核心代表性激酶亲和力阶梯谱
                          </span>
                          <button
                            type="button"
                            onClick={handleRunProfiling}
                            disabled={isProfiling || !isModelReady}
                            className="px-2.5 py-1 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition-colors cursor-pointer flex items-center gap-1"
                          >
                            {isProfiling ? <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <RefreshCw size={11} />}
                            <span>测定谱系</span>
                          </button>
                        </div>

                        {profileResults && profileResults.length > 0 ? (
                          <div className="space-y-2">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                              {profileResults.map((item, idx) => (
                                <div key={item.kinase_name} className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-850/50 text-xs space-y-1">
                                  <div className="flex justify-between items-center">
                                    <span className="font-bold text-slate-800 dark:text-slate-200">{item.kinase_name}</span>
                                    <span className="font-mono font-bold text-sky-600 dark:text-sky-400">pKd {item.predicted_pkd.toFixed(2)}</span>
                                  </div>
                                  <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
                                    <div 
                                      className={`h-full rounded-full ${item.predicted_pkd >= 7 ? 'bg-emerald-500' : item.predicted_pkd >= 6 ? 'bg-amber-500' : 'bg-slate-400'}`}
                                      style={{ width: `${Math.max(0, Math.min(100, ((item.predicted_pkd - 5.0) / 4.5) * 100))}%` }}
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                            <div className="flex justify-end pt-1">
                              <button
                                type="button"
                                onClick={handleExportProfileCSV}
                                className="text-xs text-sky-600 dark:text-sky-400 hover:underline flex items-center gap-1 cursor-pointer"
                              >
                                <Download size={12} />
                                <span>导出完整激酶谱系 CSV</span>
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="p-8 text-center text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl space-y-2">
                            <p>尚未针对当前配体生成 16-激酶谱系数据</p>
                            <button
                              type="button"
                              onClick={handleRunProfiling}
                              disabled={isProfiling || !isModelReady}
                              className="px-3 py-1.5 rounded-lg bg-sky-600 text-white font-bold text-xs cursor-pointer inline-flex items-center gap-1"
                            >
                              <RefreshCw size={12} />
                              <span>一键开始测定激酶组选择性</span>
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Tab 4: 下游决策与投产清单 */}
                    {resultFacetTab === 'dispatch' && (
                      <div className="space-y-3 animate-in fade-in duration-150">
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">
                          实验决策转化与学术报告出口
                        </span>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {/* 学术报告卡片 */}
                          <div className="p-3.5 rounded-xl border border-sky-200 dark:border-sky-800/80 bg-sky-50/30 dark:bg-sky-950/20 space-y-2 flex flex-col justify-between">
                            <div>
                              <div className="flex items-center gap-1.5 text-xs font-bold text-sky-900 dark:text-sky-200">
                                <FileText size={15} className="text-sky-600" />
                                <span>学术研究简报与专利交底</span>
                              </div>
                              <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                                生成包含双线性亲和力评分、诱导契合构象与热力学 MM-GBSA 分解的学术 Markdown 与打印报告。
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={handleGenerateAcademicReport}
                              disabled={academicReportLoading}
                              className="w-full py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition-colors flex items-center justify-center gap-1 cursor-pointer"
                            >
                              {academicReportLoading ? '生成中…' : '生成学术研究简报'}
                            </button>
                          </div>

                          {/* 96 孔板投产清单卡片 */}
                          <div className="p-3.5 rounded-xl border border-indigo-200 dark:border-indigo-800/80 bg-indigo-50/30 dark:bg-indigo-950/20 space-y-2 flex flex-col justify-between">
                            <div>
                              <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900 dark:text-indigo-200">
                                <Grid size={15} className="text-indigo-600" />
                                <span>96 孔板微孔板投产清单</span>
                              </div>
                              <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                                自动排布高低对照、候选物分级与液体处理参数，支持一键导出湿实验生化测定 CSV 清单。
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={handleGenerateWetlabDispatch}
                              disabled={wetlabDispatchLoading}
                              className="w-full py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors flex items-center justify-center gap-1 cursor-pointer"
                            >
                              {wetlabDispatchLoading ? '排布中…' : '导出 96 孔板清单'}
                            </button>
                          </div>

                          {/* 逆合成路线规划卡片 */}
                          <div className="p-3.5 rounded-xl border border-emerald-200 dark:border-emerald-800/80 bg-emerald-50/30 dark:bg-emerald-950/20 space-y-2 flex flex-col justify-between">
                            <div>
                              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-900 dark:text-emerald-200">
                                <TestTube size={15} className="text-emerald-600" />
                                <span>AI 逆合成路线规划</span>
                              </div>
                              <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                                解构小分子合成砌块，匹配商业现货 CAS 原料与多步反应条件，评估原子经济性与收率。
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleOpenRetrosynthesis(drugSmiles, `${customTargetSymbol || '当前靶点'} 抑制剂`)}
                              className="w-full py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors flex items-center justify-center gap-1 cursor-pointer"
                            >
                              查看逆合成路线
                            </button>
                          </div>

                          {/* ADMET 成药性雷达卡片 */}
                          <div className="p-3.5 rounded-xl border border-amber-200 dark:border-amber-800/80 bg-amber-50/30 dark:bg-amber-950/20 space-y-2 flex flex-col justify-between">
                            <div>
                              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900 dark:text-amber-200">
                                <ShieldCheck size={15} className="text-amber-600" />
                                <span>多维成药性 ADMET 雷达</span>
                              </div>
                              <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                                评估心脏 hERG 毒性、肠道 Caco-2 膜通透性、溶解度 LogS 与细胞色素 P450 抑制特性。
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={handleOpenAdmet}
                              className="w-full py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-colors flex items-center justify-center gap-1 cursor-pointer"
                            >
                              展开成药性雷达
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                  </div>

                </div>
              ) : (
                /* 状态 3: 初始空状态 (科研就绪引导态与一键体验卡) */
                <div className="flex-1 flex flex-col items-center justify-center p-6 sm:p-8 text-center space-y-4">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-sky-600 to-indigo-600 text-white flex items-center justify-center shadow-lg shadow-sky-500/25">
                    <Sparkles size={28} className="animate-pulse" />
                  </div>

                  <div className="max-w-md space-y-1">
                    <h4 className="text-base font-bold text-slate-900 dark:text-slate-100">
                      科学计算就绪 · 等待推断启动
                    </h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                      在左侧配置小分子与激酶靶点，或点击下方明星案例一秒体验全原子结合透视：
                    </p>
                  </div>

                  {/* 3 大经典案例一键体验卡 */}
                  <div className="w-full max-w-md grid grid-cols-1 gap-2 text-left">
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(PRESET_PAIRS[0], true)}
                      className="p-3 rounded-xl border border-sky-200 dark:border-sky-800/80 bg-sky-50/30 dark:bg-slate-850 hover:border-sky-400 hover:shadow-xs transition-all flex items-center justify-between group cursor-pointer"
                    >
                      <div>
                        <div className="text-xs font-bold text-slate-900 dark:text-slate-100 group-hover:text-sky-600">
                          达沙替尼 → ABL1 (慢粒激酶催化态)
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          经典白血病突破药 · 纳摩尔级超高亲和力
                        </div>
                      </div>
                      <span className="text-[11px] font-bold px-2 py-1 rounded bg-sky-600 text-white group-hover:bg-sky-500 transition-colors flex items-center gap-0.5">
                        <Zap size={11} /> 体验
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleApplyPreset(PRESET_PAIRS[2], true)}
                      className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-850 hover:border-indigo-400 hover:shadow-xs transition-all flex items-center justify-between group cursor-pointer"
                    >
                      <div>
                        <div className="text-xs font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-600">
                          奥希替尼 → EGFR T790M (三代耐药门控突变)
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          非小细胞肺癌核心药 · 克服一代耐药门控突变
                        </div>
                      </div>
                      <span className="text-[11px] font-bold px-2 py-1 rounded bg-indigo-600 text-white group-hover:bg-indigo-500 transition-colors flex items-center gap-0.5">
                        <Zap size={11} /> 体验
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleApplyPreset(PRESET_PAIRS[6], true)}
                      className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-850 hover:border-emerald-400 hover:shadow-xs transition-all flex items-center justify-between group cursor-pointer"
                    >
                      <div>
                        <div className="text-xs font-bold text-slate-900 dark:text-slate-100 group-hover:text-emerald-600">
                          维莫非尼 → BRAF V600E (恶性黑色素瘤驱动)
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          恶性黑色素瘤驱动基因 · 高选择性变构抑制
                        </div>
                      </div>
                      <span className="text-[11px] font-bold px-2 py-1 rounded bg-emerald-600 text-white group-hover:bg-emerald-500 transition-colors flex items-center gap-0.5">
                        <Zap size={11} /> 体验
                      </span>
                    </button>
                  </div>

                  <div className="pt-2 text-[11px] text-slate-400 flex items-center gap-2">
                    <span>左侧输入</span>
                    <span>➔</span>
                    <span>点击开始预测 (Ctrl+Enter)</span>
                    <span>➔</span>
                    <span>右侧透视出图</span>
                  </div>
                </div>
              )}

            </div>

          </div>

        </div>
      )}

      {/* Profiling Tab (激酶谱系分析全宽看板) */}
      {activeTab === 'profiling' && (
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <BarChart3 className="text-sky-600" size={16} />
                核心激酶谱系选择性分析看板 (Kinome Selectivity Profile)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                当前分子：<span className="font-mono font-bold text-slate-800 dark:text-slate-200">{drugSmiles ? drugSmiles.slice(0, 50) + '...' : '未载入'}</span>
                （覆盖 TK, CMGC, STE, AGC 等 16 种核心激酶代表性催化域）
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              {profileResults && profileResults.length > 0 && (
                <button
                  type="button"
                  onClick={handleExportProfileCSV}
                  className="py-1.5 px-3 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold text-xs rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <Download size={13} />
                  <span>导出 CSV</span>
                </button>
              )}
              <button
                type="button"
                onClick={handleRunAsyncFullProfiling}
                disabled={isSubmittingAsync || !isModelReady || !drugSmiles.trim()}
                title="将该小分子提交至后台异步队列，测定全部 379 个激酶全矩阵亲和力"
                className="py-1.5 px-3 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 disabled:opacity-50 font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                {isSubmittingAsync ? <div className="w-3.5 h-3.5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" /> : <Activity size={13} />}
                <span>全谱后台扫描 (379 靶标)</span>
              </button>
              <button
                type="button"
                onClick={handleRunProfiling}
                disabled={isProfiling || !isModelReady || !drugSmiles.trim()}
                className="py-1.5 px-3.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-bold text-xs rounded-lg shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                {isProfiling ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <RefreshCw size={13} />}
                <span>快速核心谱扫描 (16 激酶)</span>
              </button>
            </div>
          </div>

          {asyncNotice && (
            <div className="mb-4 p-3 bg-indigo-50/80 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-indigo-900 dark:text-indigo-200 rounded-xl text-xs flex items-center justify-between gap-3 shadow-2xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-indigo-600 shrink-0" />
                <span>{asyncNotice}</span>
              </div>
              <button 
                type="button" 
                onClick={() => setAsyncNotice(null)}
                className="text-indigo-500 hover:text-indigo-700 text-[11px] shrink-0 font-medium"
              >
                关闭
              </button>
            </div>
          )}

          {profileResults && profileResults.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {profileResults.map((item, idx) => {
                const barPercent = Math.max(0, Math.min(100, ((item.predicted_pkd - 5.0) / 4.5) * 100));
                return (
                  <div key={item.kinase_name} className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-850/40 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <span className="w-4 h-4 rounded bg-slate-200 dark:bg-slate-700 text-[10px] font-bold flex items-center justify-center font-mono">
                          {idx + 1}
                        </span>
                        <span className="font-bold text-slate-800 dark:text-slate-200">
                          {item.kinase_name}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {item.length} aa
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="font-mono font-bold text-sky-600 dark:text-sky-400">
                          pKd {item.predicted_pkd.toFixed(2)}
                        </span>
                        <span className="text-[10px] text-slate-400 block font-mono">
                          Kd ≈ {item.predicted_kd_nM < 1000 ? `${item.predicted_kd_nM.toFixed(0)} nM` : `${(item.predicted_kd_nM / 1000).toFixed(1)} μM`}
                        </span>
                      </div>
                    </div>

                    <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${
                          item.predicted_pkd >= 7 ? 'bg-emerald-500' : item.predicted_pkd >= 6 ? 'bg-amber-500' : 'bg-slate-400'
                        }`}
                        style={{ width: `${barPercent}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>{predictionScoreBand(item.predicted_pkd)}</span>
                      <span>{item.domain}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl">
              点击上方“重新测定谱系”，系统将自动在 16 个代表性激酶上输出亲和力阶梯图。
            </div>
          )}
        </div>
      )}

      {/* Leaderboard Tab (模型基准指标) */}
      {activeTab === 'leaderboard' && (
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Award className="text-amber-500" size={16} />已注册模型与历史基准指标
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              指标来自各模型登记的真实版本。Bilinear ESM-2 模型在严格双实体冷启动测试中取得 CI 0.7514，突破单向退化瓶颈。
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                  <th className="p-2.5 font-bold">评价域</th>
                  <th className="p-2.5 font-bold">配对数</th>
                  <th className="p-2.5 font-bold">模型名称</th>
                  <th className="p-2.5 font-bold">版本</th>
                  <th className="p-2.5 font-bold">CI ↑</th>
                  <th className="p-2.5 font-bold">RMSE ↓</th>
                  <th className="p-2.5 font-bold">MAE ↓</th>
                  <th className="p-2.5 font-bold">推荐状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {models.flatMap(model => Object.entries(model.metrics_by_domain ?? {}).map(([domain, metrics]) => (
                  <tr key={`${model.id}:${domain}`} className={model.is_recommended ? 'bg-emerald-50/40 dark:bg-emerald-950/20 font-medium' : ''}>
                    <td className="p-2.5">{{ strict_dual_cold_test: '双实体冷启动', cold_drug_test: '冷药物', cold_target_test: '冷靶点', train_block: '训练主块' }[domain] || domain}</td>
                    <td className="p-2.5 font-mono">{metrics.n ?? '未报告'}</td>
                    <td className="p-2.5">{model.name}</td>
                    <td className="p-2.5 text-[10px] font-mono">{model.model_version || model.benchmark_version || '未登记'}</td>
                    <td className="p-2.5 font-mono text-sky-600 dark:text-sky-400 font-bold">{metrics.concordance_index == null ? '未报告' : Number(metrics.concordance_index).toFixed(4)}</td>
                    <td className="p-2.5 font-mono">{metrics.rmse == null ? '未报告' : Number(metrics.rmse).toFixed(4)}</td>
                    <td className="p-2.5 font-mono">{metrics.mae == null ? '未报告' : Number(metrics.mae).toFixed(4)}</td>
                    <td className="p-2.5">
                      {model.is_recommended ? (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-600 text-white text-[10px] font-bold">默认推荐</span>
                      ) : (
                        <span className="text-slate-400 text-[10px]">基准对比</span>
                      )}
                    </td>
                  </tr>
                )))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 模态框组 */}
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

      <ADMETRadarModal
        isOpen={admetModalOpen}
        onClose={() => setAdmetModalOpen(false)}
        admet={currentAdmet}
        moleculeName={drugs.find(d => d.id === selectedDrugId)?.name || '当前小分子配体'}
        loading={admetLoading}
      />

      <ClinicalTargetSelectorModal
        isOpen={isTargetModalOpen}
        onClose={() => setIsTargetModalOpen(false)}
        onSelectTarget={handleSelectClinicalTarget}
        currentTargetSymbol={customTargetSymbol}
      />

      <DeNovoPocketGeneratorModal
        isOpen={isDeNovoModalOpen}
        onClose={() => setIsDeNovoModalOpen(false)}
        initialTargetSymbol={customTargetSymbol}
        onViewRetrosynthesis={handleOpenRetrosynthesis}
        onSelectCandidate={handleSelectDeNovoCandidate}
      />

      <RetrosynthesisModal
        isOpen={isRetroModalOpen}
        onClose={() => setIsRetroModalOpen(false)}
        smiles={retroSmiles}
        moleculeName={retroMolName}
      />

      <VirtualScreeningModal
        isOpen={isScreeningModalOpen}
        onClose={() => setIsScreeningModalOpen(false)}
        initialTargetSymbol={customTargetSymbol}
        onViewRetrosynthesis={handleOpenRetrosynthesis}
        onSelectLead={handleSelectScreeningHit}
      />

      <AcademicReportModal
        isOpen={academicReportOpen}
        onClose={() => setAcademicReportOpen(false)}
        reportData={academicReportData}
        loading={academicReportLoading}
      />

      <WetlabDispatchModal
        isOpen={wetlabDispatchOpen}
        onClose={() => setWetlabDispatchOpen(false)}
        dispatchResult={wetlabDispatchData}
        loading={wetlabDispatchLoading}
      />
    </div>
  );
}
