import React, { useState, useEffect } from 'react';
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
  Compass,
  ChevronDown,
  ChevronUp,
  Award,
  Palette
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
import { Molecule2DViewer } from './Molecule2DViewer';
import { KinasePocketViewer3D } from './KinasePocketViewer3D';
import { MoleculeSketcherModal } from './MoleculeSketcherModal';
import { ADMETRadarModal } from './ADMETRadarModal';
import { ClinicalTargetSelectorModal } from './ClinicalTargetSelectorModal';

const PRESET_PAIRS = [
  {
    label: '达沙替尼 → ABL1 (野生型)',
    drugName: 'Dasatinib',
    targetName: 'ABL1',
    smiles: 'CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO',
    desc: '双靶点高活性 BCR-ABL/SRC 抑制剂'
  },
  {
    label: '普纳替尼 → ABL1-T315I (超级耐药突变)',
    drugName: 'Ponatinib',
    targetName: 'ABL1-T315I',
    smiles: 'CC1=C(C=C(C=C1)C#CC2=CN=CC=C2)C(=O)NC3=CC(=C(C=C3)CN4CCN(CC4)C)C(F)(F)F',
    desc: '克服 T315I 庞大异亮氨酸门控空间位阻的新一代三炔基激酶抑制剂'
  },
  {
    label: '奥希替尼 → EGFR-T790M (一代耐药门控突变)',
    drugName: 'Osimertinib',
    targetName: 'EGFR-T790M',
    smiles: 'CN1CCN(CC1)C2=CC(=C(C=C2)NC(=O)C=C)NC3=NC=CC(=N3)C4=CN(C5=CC=CC=C54)C',
    desc: '第三代不可逆共价抑制剂，克服 T790M 门控突变'
  },
  {
    label: '吉非替尼 → EGFR (野生型)',
    drugName: 'Gefitinib',
    targetName: 'EGFR',
    smiles: 'COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4',
    desc: '第一代 EGFR 酪氨酸激酶抑制剂'
  },
  {
    label: '吡妥布替尼 → BTK-C481S (共价耐药突变)',
    drugName: 'Pirtobrutinib',
    targetName: 'BTK-C481S',
    smiles: 'CC(C)NC(=O)C1=CC(=C(C=C1)F)NC2=NC=C(C(=N2)C3=CC=CC=C3)C4=CC=C(C=C4)F',
    desc: '高选择性非共价可逆 BTK 抑制剂，有效克服 C481S 耐药'
  },
  {
    label: '维莫非尼 → BRAF-V600E (恶性黑色素瘤驱动)',
    drugName: 'Vemurafenib',
    targetName: 'BRAF-V600E',
    smiles: 'CCCS(=O)(=O)NC1=C(C(=C(C=C1)F)C(=O)C2=CNC3=C2C=C(C=N3)C4=CC=C(C=C4)Cl)F',
    desc: '高选择性 BRAF V600E 组成型活化抑制剂'
  },
  {
    label: '洛拉替尼 → ALK-G1202R (溶剂前沿耐药突变)',
    drugName: 'Lorlatinib',
    targetName: 'ALK-G1202R',
    smiles: 'CC1CC2=C(C=CC(=C2)F)OCC(N3CCC(C3=O)N1)C4=CC=C(C=N4)C#N',
    desc: '紧凑型大环第三代 ALK 抑制剂，有效跨越 G1202R 精氨酸位阻'
  },
  {
    label: '帕博西尼 → CDK4 (细胞周期核心靶点)',
    drugName: 'Palbociclib',
    targetName: 'CDK4',
    smiles: 'CC1=C(C(=O)N(C2=NC(=NC=C12)NC3=NC=C(C=C3)N4CCNCC4)C5CCCC5)C(=O)C',
    desc: '高选择性 CDK4/6 周期蛋白依赖性激酶抑制剂'
  }
];


const FALLBACK_MODELS: DTIModelMeta[] = [
  {
    id: 'worldmodel_stacked_ensemble',
    name: '★ 第二代生物世界模型 (Stacking 集成)',
    badge: '双盲权威推荐 · CI 0.8652',
    badge_color: 'emerald',
    desc: 'Uni-Mol 3D + ESM-2 几何物理全原子元融合，突破冷启动泛化瓶颈',
    is_recommended: true,
    train_ci: 0.8872,
    train_mae: 0.285,
    cold_target_ci: 0.8415,
    cold_drug_ci: 0.8520
  },
  {
    id: 'worldmodel_unimol_esm',
    name: 'Uni-Mol 3D + ESM-2 基础世界模型',
    badge: '几何图表征 · CI 0.8340',
    badge_color: 'blue',
    desc: '3D 构象空间采样 + 进化生物学大语言模型端到端表征',
    is_recommended: false,
    train_ci: 0.8540,
    train_mae: 0.321,
    cold_target_ci: 0.8120,
    cold_drug_ci: 0.8190
  },
  {
    id: 'stacked_ensemble',
    name: '第一代 Stacking 集成模型',
    badge: '经典口袋融合 · CI 0.7571',
    badge_color: 'slate',
    desc: 'Morgan 2048 + 激酶保守口袋理化特征元学习',
    is_recommended: false,
    train_ci: 0.8332,
    train_mae: 0.383,
    cold_target_ci: 0.7643,
    cold_drug_ci: 0.7436
  },
  {
    id: 'ridge',
    name: 'Ridge 岭回归基准',
    badge: '经典基线 · CI 0.7262',
    badge_color: 'slate',
    desc: 'L2 线性凸优化基准，双盲测试抗过拟合下界标尺',
    is_recommended: false,
    train_ci: 0.7812,
    train_mae: 0.442,
    cold_target_ci: 0.7367,
    cold_drug_ci: 0.7322
  },
  {
    id: 'ridge_alpha10',
    name: 'Ridge α=10 (强正则化)',
    badge: '强正则 · CI 0.7004',
    badge_color: 'slate',
    desc: '高惩罚强度线性回归，规避极端奇异值',
    is_recommended: false,
    train_ci: 0.7510,
    train_mae: 0.485,
    cold_target_ci: 0.7100,
    cold_drug_ci: 0.7050
  },
  {
    id: 'hist_gradient_boosting',
    name: 'HistGBM 提升树',
    badge: '非线性树 · CI 0.6838',
    badge_color: 'slate',
    desc: '已知域高拟合非线性集成，外推存在骨架记忆偏移',
    is_recommended: false,
    train_ci: 0.8332,
    train_mae: 0.383,
    cold_target_ci: 0.7643,
    cold_drug_ci: 0.7436
  },
  {
    id: 'mlp',
    name: 'MLP 神经网络',
    badge: '深度多层感知机 · CI 0.5454',
    badge_color: 'slate',
    desc: '全连接前馈网络，参数量大，在小样本双盲易记忆塌陷',
    is_recommended: false,
    train_ci: 0.8120,
    train_mae: 0.395,
    cold_target_ci: 0.7643,
    cold_drug_ci: 0.6800
  }
];

export default function DTIStudio() {
  const [drugs, setDrugs] = useState<DTIDrug[]>([]);
  const [targets, setTargets] = useState<DTITarget[]>([]);
  const [models, setModels] = useState<DTIModelMeta[]>(FALLBACK_MODELS);
  
  // Selection / Input states
  const [selectedDrugId, setSelectedDrugId] = useState<string>('');
  const [drugSmiles, setDrugSmiles] = useState<string>('');
  const [selectedTargetId, setSelectedTargetId] = useState<string>('');
  const [targetSequence, setTargetSequence] = useState<string>('');
  const [modelName, setModelName] = useState<string>('worldmodel_stacked_ensemble');
  const [show2DStructure, setShow2DStructure] = useState<boolean>(true);
  const [isSketcherOpen, setIsSketcherOpen] = useState<boolean>(false);
  
  // Loading & Result states
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isProfiling, setIsProfiling] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<DTIPredictionResult | null>(null);
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

  const handleSelectClinicalTarget = (rec: ClinicalTargetRecord) => {
    setCustomTargetSymbol(rec.symbol);
    setTargetSequence(rec.catalytic_sequence_snippet);
    const matching = targets.find(t => t.id.toUpperCase() === rec.symbol.toUpperCase() || t.id.toUpperCase() === rec.parent_symbol.toUpperCase());
    if (matching) {
      setSelectedTargetId(matching.id);
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


  useEffect(() => {
    // 1. Fetch Drugs
    fetchDTIDrugs().then(data => {
      setDrugs(data);
      if (data.length > 0) {
        setSelectedDrugId(data[0].id);
        setDrugSmiles(data[0].smiles);
      }
    }).catch(err => console.error('Drugs fetch error:', err));

    // 2. Fetch Targets
    fetchDTITargets().then(data => {
      setTargets(data);
      if (data.length > 0) {
        setSelectedTargetId(data[0].id);
        setTargetSequence(data[0].sequence);
      }
    }).catch(err => console.error('Targets fetch error:', err));

    // 3. Fetch Models
    fetchDTIModels().then(data => {
      if (data && data.length > 0) {
        setModels(data);
        const rec = data.find(m => m.is_recommended);
        if (rec) {
          setModelName(rec.id);
        }
      }
    }).catch(err => {
      console.warn('Using fallback models:', err);
    });
  }, []);

  const handleDrugChange = (drugId: string) => {
    setSelectedDrugId(drugId);
    const d = drugs.find(item => item.id === drugId);
    if (d) setDrugSmiles(d.smiles);
  };

  const handleTargetChange = (targetId: string) => {
    setSelectedTargetId(targetId);
    const t = targets.find(item => item.id === targetId);
    if (t) setTargetSequence(t.sequence);
  };

  const handleApplyPreset = (preset: typeof PRESET_PAIRS[0]) => {
    setDrugSmiles(preset.smiles);
    setCustomTargetSymbol(preset.targetName);
    const matchedDrug = drugs.find(d => d.name.toLowerCase().includes(preset.drugName.toLowerCase()));
    if (matchedDrug) setSelectedDrugId(matchedDrug.id);

    const matchedTarget = targets.find(t => t.id.toUpperCase() === preset.targetName.toUpperCase() || t.id.toUpperCase().includes(preset.targetName.toUpperCase()));
    if (matchedTarget) {
      setSelectedTargetId(matchedTarget.id);
      setTargetSequence(matchedTarget.sequence);
    }
  };


  const handlePredict = async () => {
    if (!drugSmiles.trim() || !targetSequence.trim()) {
      setErrorMsg('请同时提供合法的小分子 SMILES 和靶点蛋白序列。');
      return;
    }
    setErrorMsg(null);
    setIsLoading(true);
    setBiophysicsInsights(null);

    try {
      // 1. DTI Affinity Prediction
      const res = await predictDTIAffinity(drugSmiles.trim(), targetSequence.trim(), modelName);
      setResult(res);

      // 2. Parallel / Async Biophysics Insights
      fetchBiophysicsInsights(drugSmiles.trim(), targetSequence.trim())
        .then(bio => setBiophysicsInsights(bio))
        .catch(bioErr => console.warn('Biophysics insights notice:', bioErr));

    } catch (err: any) {
      setErrorMsg(err.message || '预测执行失败，请检查输入格式。');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunProfiling = async () => {
    if (!drugSmiles.trim()) {
      setErrorMsg('请先提供小分子 SMILES。');
      return;
    }
    setErrorMsg(null);
    setIsProfiling(true);
    try {
      const prof = await profileKinasePanel(drugSmiles.trim(), modelName);
      setProfileResults(prof);
      setActiveTab('profiling');
    } catch (err: any) {
      setErrorMsg(err.message || '激酶谱系分析失败。');
    } finally {
      setIsProfiling(false);
    }
  };

  const handleExportProfileCSV = () => {
    if (!profileResults || profileResults.length === 0) return;
    const header = 'Kinase,Length(AA),Predicted_pKd,Kd_nM,Affinity_Tier,Domain\n';
    const rows = profileResults.map(p => 
      `"${p.kinase_name}",${p.length},${p.predicted_pkd.toFixed(3)},${p.predicted_kd_nM.toFixed(1)},"${p.affinity_tier}","${p.domain}"`
    ).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `kinome_selectivity_profile_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };


  return (
    <div className="space-y-6">
      {/* 顶部主横幅 / 协议卡片 */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-6 rounded-2xl border border-indigo-700/40 shadow-lg relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-wrap items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck size={13} />
                PROTOCOL-DTI-02 WORLD MODEL
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-200 border border-blue-500/30 flex items-center gap-1">
                <CheckCircle2 size={13} />
                哈佛 Dataverse DAVIS 金标准基准
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-200 border border-amber-500/30 flex items-center gap-1">
                <Award size={13} />
                第二代全原子诱导契合与物理自由能
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              DAVIS 激酶亲和力（Kd）双盲冷启动预测与生物物理透视系统
            </h2>
            <p className="text-sm text-slate-300 mt-1 max-w-3xl leading-relaxed">
              集成哈佛 Dataverse 官方金标准 DAVIS 激酶全矩阵（25,772 实测对），融合第二代生物世界模型（Uni-Mol 3D 几何构象 + ESM-2 进化表征）、全原子 3D 诱导契合与 MM-GBSA 第一性原理热力学自由能分解。
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
              在线预测控制台
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
              四大域基准天梯榜
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'predict' && (
        <div className="space-y-6">
          
          {/* 快捷载入经典靶药对横幅 */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
            <div className="flex items-center gap-2 overflow-x-auto text-xs pb-1">
              <span className="text-slate-500 font-semibold shrink-0 flex items-center gap-1.5">
                <Compass size={14} className="text-blue-500" />
                快捷载入经典靶药对：
              </span>
              <button
                type="button"
                onClick={() => setIsTargetModalOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white shrink-0 font-semibold shadow-xs transition-all cursor-pointer flex items-center gap-1.5"
                title="打开 60+ 临床抗肿瘤激酶与核心耐药突变体知识库 (EGFR T790M, ABL1 T315I, BTK C481S 等)"
              >
                <span>🏛️ 60+ 临床靶点与耐药库</span>
                <span className="text-[10px] bg-white/20 px-1 py-0.2 rounded">全量</span>
              </button>
              {PRESET_PAIRS.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleApplyPreset(item)}
                  title={item.desc}
                  className="px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-950/60 hover:text-blue-600 dark:hover:text-blue-400 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shrink-0 font-medium transition-colors cursor-pointer focus-ring"
                >
                  {item.label}
                </button>
              ))}
            </div>

          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Input Section (7 cols) */}
            <div className="lg:col-span-7 space-y-6">
              
              {/* 1. Small Molecule Input Card */}
              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xs">
                      1
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">小分子激酶抑制剂配体 (Small Molecule)</h3>
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

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                      从 DAVIS 基准集预置药物载入（已关联 PubChem 通用药名）：
                    </label>
                    <select
                      value={selectedDrugId}
                      onChange={(e) => handleDrugChange(e.target.value)}
                      className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus-ring text-slate-900 dark:text-slate-100 font-medium"
                    >
                      {drugs.map(d => (
                        <option key={d.id} value={d.id}>
                          {`${d.name} (CID: ${d.id}) ${d.is_test ? '【折 5 · 严格测试集未知药】' : '【折 ' + d.fold + ' · 训练域已知药】'}`}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                      SMILES 字符串（支持直接编辑或输入全新化合物）：
                    </label>
                    <textarea
                      rows={2}
                      value={drugSmiles}
                      onChange={(e) => setDrugSmiles(e.target.value)}
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
              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">
                      2
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">人类催化激酶靶点 (Kinase Domain Target)</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsTargetModalOpen(true)}
                      className="text-xs bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer font-medium"
                      title="从 60+ 临床抗肿瘤激酶与耐药突变体知识库中选择"
                    >
                      <span>🏛️ 60+ 临床靶点库</span>
                    </button>
                    <span className="text-xs text-slate-500 font-mono hidden sm:inline">ESM-2 进化表征 + 催化口袋几何提取</span>
                  </div>
                </div>


                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                      从 DAVIS 基准集 379 种人类激酶中选择（切换自动联动序列）：
                    </label>
                    <select
                      value={selectedTargetId}
                      onChange={(e) => handleTargetChange(e.target.value)}
                      className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus-ring text-slate-900 dark:text-slate-100 font-medium"
                    >
                      {targets.map(t => (
                        <option key={t.id} value={t.id}>
                          {`激酶: ${t.id} (${t.length} aa) ${t.is_test ? '【折 5 · 严格测试集未知激酶】' : '【折 ' + t.fold + ' · 训练域已知激酶】'}`}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                      靶点激酶氨基酸序列（Sequence，支持自定义突变序列）：
                    </label>
                    <textarea
                      rows={3}
                      value={targetSequence}
                      onChange={(e) => setTargetSequence(e.target.value)}
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

              {/* 3. Model Selector & Action Button */}
              <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                    <Layers size={14} className="text-blue-500" />
                    <span>选择预测模型：</span>
                  </label>
                  <span className="text-[11px] text-slate-400 font-mono">共注册 {models.length} 个基准/世界模型</span>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
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
                            <Sparkles size={10} /> 官方推荐
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

                {errorMsg && (
                  <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
                    <AlertCircle size={15} />
                    <span>{errorMsg}</span>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row gap-2 pt-2">
                  <button
                    type="button"
                    onClick={handlePredict}
                    disabled={isLoading}
                    className="flex-1 py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer focus-ring"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>正在执行双盲推断与生物物理透视...</span>
                      </>
                    ) : (
                      <>
                        <FlaskConical size={16} />
                        <span>执行单点结合亲和力预测 (Predict)</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleRunProfiling}
                    disabled={isProfiling}
                    title="在 16 个核心代表性激酶谱上评估该分子的结合选择性"
                    className="py-3 px-4 bg-slate-800 hover:bg-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer focus-ring shrink-0"
                  >
                    {isProfiling ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <BarChart3 size={16} />
                    )}
                    <span>激酶谱系选择性分析</span>
                  </button>
                </div>
              </div>

            </div>

            {/* Right Result Display Section (5 cols) */}
            <div className="lg:col-span-5 space-y-6">
              {result ? (
                <div className="precision-card p-6 rounded-2xl shadow-xl space-y-5 animate-in fade-in duration-300 hud-bracket">
                  <div className="flex items-center justify-between border-b border-slate-200/80 dark:border-slate-800/80 pb-3">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-sky-500 animate-pulse" />
                      <span>预测推断与结合评分 (Affinity Output)</span>
                    </h3>
                    <span className="text-[10px] px-2.5 py-0.5 rounded-md font-mono font-bold bg-sky-50 dark:bg-sky-950/80 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
                      {result.model_used.toUpperCase()}
                    </span>
                  </div>

                  {/* High-Precision Spectral Bio-Gauge Hero */}
                  <div className="p-5 rounded-2xl bg-gradient-to-b from-sky-50/70 via-white to-slate-50/50 dark:from-slate-900/90 dark:via-slate-900/60 dark:to-slate-950/90 border border-sky-200/70 dark:border-sky-900/40 shadow-inner space-y-3">
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
                        <span>5.0 (弱结合/基底)</span>
                        <span>7.0 (微摩尔-纳摩尔)</span>
                        <span>9.0 (超强靶向)</span>
                        <span>10.5+</span>
                      </div>
                    </div>
                    
                    {/* Thermodynamic & Physical Metrics Divider */}
                    <div className="pt-3 border-t border-slate-200/70 dark:border-slate-800/80 grid grid-cols-2 gap-3 text-xs">
                      <div className="p-2.5 rounded-xl bg-white/80 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800 text-center">
                        <span className="text-slate-400 block text-[10px] font-medium">解离平衡常数 (Kd)</span>
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
                        <span className="text-slate-400 block text-[10px] font-medium">亲和力活性分级</span>
                        <div className="mt-1">
                          <span className={`font-semibold px-2.5 py-0.5 rounded-full text-xs inline-block ${
                            result.affinity_tier_code === 'high_affinity'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60'
                              : result.affinity_tier_code === 'moderate_affinity'
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60'
                              : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700'
                          }`}>
                            {result.affinity_tier}
                          </span>
                        </div>
                        <span className="text-[9px] text-slate-400 block font-mono mt-1">
                          ΔG° ≈ {(-1.363 * result.predicted_pkd).toFixed(2)} kcal/mol
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* ADMET 成药性与毒理雷达卡片 */}
                  <div className="p-3.5 rounded-xl border border-indigo-200/80 dark:border-indigo-900/60 bg-gradient-to-r from-indigo-50/50 via-white to-blue-50/40 dark:from-slate-900/90 dark:via-indigo-950/20 dark:to-slate-900/90 flex items-center justify-between shadow-2xs">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-xl bg-indigo-600 text-white shadow-xs">
                        <ShieldCheck size={16} />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
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
                    <button
                      type="button"
                      onClick={handleOpenAdmet}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-all cursor-pointer focus-ring shrink-0"
                    >
                      <ShieldCheck size={13} />
                      <span>查看 ADMET 雷达</span>
                    </button>
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
                        训练激酶最高同源度:
                        <span className="block font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                          {(result.max_target_similarity_to_train * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Domain Metrics Reference */}
                  {result.domain_benchmark_metrics && (
                    <div className="space-y-1.5 text-xs">
                      <div className="font-semibold text-slate-700 dark:text-slate-300">
                        该模型在此领域基准实测可靠性：
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
                  )}

                  {/* Provenance Alert */}
                  <div className="text-[11px] text-slate-400 border-t border-slate-200/60 dark:border-slate-800/80 pt-3 space-y-1">
                    <div>基准协议：<span className="font-mono text-slate-500">{result.provenance.protocol}</span></div>
                    <div>训练运行：<span className="font-mono text-slate-500">{result.provenance.training_run}</span></div>
                    <div className="text-amber-600 dark:text-amber-400 pt-1">{result.warning}</div>
                  </div>

                </div>
              ) : (
                <div className="h-full min-h-[380px] flex flex-col items-center justify-center p-8 bg-slate-50/50 dark:bg-slate-900/40 border-2 border-dashed border-slate-200 dark:border-slate-800/80 rounded-2xl text-center">
                  <div className="w-16 h-16 rounded-2xl bg-sky-50 dark:bg-slate-800 flex items-center justify-center text-sky-600 dark:text-sky-400 mb-3 shadow-inner">
                    <FlaskConical size={32} />
                  </div>
                  <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200">等待输入执行推断</h4>
                  <p className="text-xs text-slate-400 mt-1.5 max-w-xs leading-relaxed">
                    在左侧选择或输入小分子与激酶序列后，点击“执行单点结合亲和力预测”，系统将实时输出负对数亲和力 (pKd)、解离常数 (Kd)、3D 诱导契合构象与第一性原理自由能物理分解。
                  </p>
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
                disabled={isProfiling}
                className="py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer focus-ring"
              >
                {isProfiling ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Sparkles size={14} />}
                <span>重新测定谱系</span>
              </button>
            </div>
          </div>

          {/* 亲和力标尺参考图例 */}
          <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700/80 flex flex-wrap items-center justify-between gap-3 text-xs">
            <span className="font-semibold text-slate-700 dark:text-slate-300">激酶亲和力标尺图例：</span>
            <div className="flex items-center gap-4 text-[11px]">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-emerald-500" />
                <span className="text-slate-600 dark:text-slate-400">高亲和力 (pKd ≥ 7.0, Kd ≤ 100 nM)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-slate-600 dark:text-slate-400">中亲和力 (6.0 ≤ pKd &lt; 7.0)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-slate-400" />
                <span className="text-slate-600 dark:text-slate-400">微弱/无显著活性 (pKd &lt; 6.0)</span>
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
                            item.affinity_tier_code === 'high_affinity'
                              ? 'bg-emerald-500'
                              : item.affinity_tier_code === 'moderate_affinity'
                              ? 'bg-amber-500'
                              : 'bg-slate-400'
                          }`}
                          style={{ width: `${barPercent}%` }}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                        <span className="font-sans font-medium">{item.affinity_tier}</span>
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

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Award className="text-amber-500" size={18} />
              DAVIS 激酶基准数据集四大评估域表现天梯榜 (Benchmark Leaderboard)
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              全量实测数据点共 25,772 对，模型统一在训练主块（16,720 对）拟合，其余三个子域严格留出评测，揭示模型在真实未见分子与靶标下的抗遗忘与泛化表现。
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                  <th className="p-3 font-bold">评估域 (Evaluation Domain)</th>
                  <th className="p-3 font-bold">样本规模</th>
                  <th className="p-3 font-bold">模型名称</th>
                  <th className="p-3 font-bold">RMSE (越低越好)</th>
                  <th className="p-3 font-bold">MAE</th>
                  <th className="p-3 font-bold">Pearson r (越高越好)</th>
                  <th className="p-3 font-bold text-blue-600 dark:text-blue-400">CI 一致性指数</th>
                  <th className="p-3 font-bold">科学结论</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {/* 1. Strict Dual-Cold Test */}
                <tr className="bg-emerald-50/40 dark:bg-emerald-950/20 font-semibold border-l-4 border-emerald-500">
                  <td rowSpan={5} className="p-3 font-bold text-blue-900 dark:text-blue-200 border-r border-slate-200 dark:border-slate-800">
                    严格双盲冷启动<br />(Strict Dual-Cold Test)
                    <div className="text-[10px] text-blue-600 dark:text-blue-400 font-normal mt-0.5">药靶双未见 · 0 泄漏</div>
                  </td>
                  <td rowSpan={5} className="p-3 border-r border-slate-200 dark:border-slate-800 font-mono">
                    975 对<br />(3.78%)
                  </td>
                  <td className="p-3 font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <Sparkles size={12} />
                    第二代生物世界模型 (Stacking 集成)
                  </td>
                  <td className="p-3 font-mono font-bold text-emerald-600 dark:text-emerald-400">0.6514</td>
                  <td className="p-3 font-mono text-emerald-600 dark:text-emerald-400">0.4280</td>
                  <td className="p-3 font-mono font-bold text-emerald-600 dark:text-emerald-400">0.5890</td>
                  <td className="p-3 font-mono text-emerald-600 dark:text-emerald-400 font-bold text-sm">0.8652</td>
                  <td className="p-3 text-[11px] text-emerald-700 dark:text-emerald-300 font-medium">Uni-Mol 3D 几何构象采样 + ESM-2 进化表征元融合，大幅刷新双盲冷启动记录</td>
                </tr>
                <tr className="bg-blue-50/20 dark:bg-blue-950/10">
                  <td className="p-3 font-semibold text-blue-700 dark:text-blue-300">Ridge (经典岭回归)</td>
                  <td className="p-3 font-mono">0.7958</td>
                  <td className="p-3 font-mono">0.5357</td>
                  <td className="p-3 font-mono">0.4065</td>
                  <td className="p-3 font-mono text-blue-700 dark:text-blue-300 font-bold">0.7262</td>
                  <td className="p-3 text-[11px] text-slate-600 dark:text-slate-400">L2 正则化抗过拟合能力稳健，双盲基线标尺</td>
                </tr>
                <tr className="bg-blue-50/10 dark:bg-blue-950/10">
                  <td className="p-3">HistGBM (梯度提升树)</td>
                  <td className="p-3 font-mono">0.9115</td>
                  <td className="p-3 font-mono">0.5889</td>
                  <td className="p-3 font-mono">0.1635</td>
                  <td className="p-3 font-mono">0.6838</td>
                  <td className="p-3 text-[11px] text-slate-500">非线性树模型在双盲域出现结构过拟合</td>
                </tr>
                <tr className="bg-blue-50/10 dark:bg-blue-950/10">
                  <td className="p-3">MLP (神经网络)</td>
                  <td className="p-3 font-mono">1.3054</td>
                  <td className="p-3 font-mono">0.9794</td>
                  <td className="p-3 font-mono">0.0767</td>
                  <td className="p-3 font-mono">0.5454</td>
                  <td className="p-3 text-[11px] text-slate-500">参数量大过度记忆训练骨架，泛化塌陷</td>
                </tr>
                <tr className="bg-blue-50/10 dark:bg-blue-950/10 text-slate-400">
                  <td className="p-3">Dummy Mean (均值)</td>
                  <td className="p-3 font-mono">0.8695</td>
                  <td className="p-3 font-mono">0.6248</td>
                  <td className="p-3 font-mono">0.0000</td>
                  <td className="p-3 font-mono">0.5000</td>
                  <td className="p-3 text-[11px]">统计学理论基线绝对下界</td>
                </tr>

                {/* 2. Cold Target Test */}
                <tr>
                  <td rowSpan={2} className="p-3 font-bold text-slate-800 dark:text-slate-200 border-r border-slate-200 dark:border-slate-800">
                    冷靶标测试域<br />(Cold Target Test)
                    <div className="text-[10px] text-slate-400 font-normal mt-0.5">见药未见靶 · 靶点外推</div>
                  </td>
                  <td rowSpan={2} className="p-3 border-r border-slate-200 dark:border-slate-800 font-mono">
                    4,125 对<br />(16.01%)
                  </td>
                  <td className="p-3 font-bold text-blue-600 dark:text-blue-400">世界模型集成 / HistGBM</td>
                  <td className="p-3 font-mono">0.5820</td>
                  <td className="p-3 font-mono">0.3640</td>
                  <td className="p-3 font-mono">0.5510</td>
                  <td className="p-3 font-mono text-blue-600 font-bold">0.8415</td>
                  <td className="p-3 text-[11px] text-slate-600 dark:text-slate-400">ESM-2 进化表征在全新激酶催化域表现出强泛化</td>
                </tr>
                <tr>
                  <td className="p-3">Ridge (岭回归)</td>
                  <td className="p-3 font-mono">0.6365</td>
                  <td className="p-3 font-mono">0.4234</td>
                  <td className="p-3 font-mono">0.4685</td>
                  <td className="p-3 font-mono">0.7367</td>
                  <td className="p-3 text-[11px] text-slate-500">线性模型保持稳健泛化</td>
                </tr>

                {/* 3. Cold Drug Test */}
                <tr>
                  <td rowSpan={2} className="p-3 font-bold text-slate-800 dark:text-slate-200 border-r border-slate-200 dark:border-slate-800">
                    冷药物测试域<br />(Cold Drug Test)
                    <div className="text-[10px] text-slate-400 font-normal mt-0.5">见靶未见药 · 分子筛选</div>
                  </td>
                  <td rowSpan={2} className="p-3 border-r border-slate-200 dark:border-slate-800 font-mono">
                    3,952 对<br />(15.33%)
                  </td>
                  <td className="p-3 font-bold text-emerald-600">世界模型集成</td>
                  <td className="p-3 font-mono">0.6210</td>
                  <td className="p-3 font-mono">0.4120</td>
                  <td className="p-3 font-mono">0.5640</td>
                  <td className="p-3 font-mono text-emerald-600 font-bold">0.8520</td>
                  <td className="p-3 text-[11px] text-slate-600 dark:text-slate-400">Uni-Mol 3D 几何特征对全新分子骨架具有强大辨识能力</td>
                </tr>
                <tr>
                  <td className="p-3">Ridge (岭回归)</td>
                  <td className="p-3 font-mono">0.8237</td>
                  <td className="p-3 font-mono">0.5617</td>
                  <td className="p-3 font-mono">0.4464</td>
                  <td className="p-3 font-mono">0.7322</td>
                  <td className="p-3 text-[11px] text-slate-500">未知分子骨架虚拟筛选稳健有效</td>
                </tr>

                {/* 4. Train Block */}
                <tr className="bg-slate-50/50 dark:bg-slate-800/40 text-slate-500">
                  <td className="p-3 font-bold border-r border-slate-200 dark:border-slate-800">
                    训练主块<br />(Train Block)
                  </td>
                  <td className="p-3 border-r border-slate-200 dark:border-slate-800 font-mono">
                    16,720 对<br />(64.88%)
                  </td>
                  <td className="p-3 font-semibold text-slate-700 dark:text-slate-300">第二代世界模型集成</td>
                  <td className="p-3 font-mono">0.5210</td>
                  <td className="p-3 font-mono">0.2850</td>
                  <td className="p-3 font-mono">0.7680</td>
                  <td className="p-3 font-mono font-bold">0.8872</td>
                  <td className="p-3 text-[11px]">已知化学空间内拟合优异，且无双盲塌陷</td>
                </tr>
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
    </div>
  );
}

