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
  Info
} from 'lucide-react';
import { 
  fetchDTIDrugs, 
  fetchDTITargets, 
  optimizeLeadMolecule,
  type DTIDrug, 
  type DTITarget, 
  type DTIOptimizeResult,
  type CandidateDerivative
} from '../api/dtiClient';
import { useAppStore } from '../store/useAppStore';
import { computeDrugLikeness } from '../utils/cheminformatics';
import { Molecule2DViewer } from './Molecule2DViewer';

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
  const [optimizationGoal, setOptimizationGoal] = useState<string>(OPTIMIZATION_GOALS[0].value);
  const [customInstruction, setCustomInstruction] = useState<string>('');
  const [evalModel, setEvalModel] = useState<string>('stacked_ensemble');

  // Execution states
  const [isOptimizing, setIsOptimizing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<DTIOptimizeResult | null>(null);
  
  // UI interaction states
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [cartSuccessId, setCartSuccessId] = useState<string | null>(null);

  const hasLLMConfigured = Boolean(apiKey && apiKey.trim().length > 0);

  useEffect(() => {
    // Load drugs
    fetchDTIDrugs().then(data => {
      setDrugs(data);
      if (data.length > 0) {
        // Find Dasatinib or take first
        const dasatinib = data.find(d => d.name.toLowerCase().includes('dasatinib')) || data[0];
        setDrugSmiles(dasatinib.smiles);
        setDrugDisplayName(dasatinib.name);
      }
    }).catch(err => console.error('Fetch drugs error:', err));

    // Load targets
    fetchDTITargets().then(data => {
      setTargets(data);
      if (data.length > 0) {
        // Find ABL1 or take first
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
    
    // Find matching target if available
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
      p_amp: 0.95, // 占位保持类型兼容
      p_hemo: 0.05,
      tsi: candidate.predicted_pkd,
    });
    setCartSuccessId(candidate.id);
    setTimeout(() => setCartSuccessId(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* 顶部标题与工作机制横幅 */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-xs">
                <Sparkles size={20} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <span>AI 先导化合物智能改构与分子进化工作台</span>
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300">
                    Lead Optimizer Studio
                  </span>
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  生成式药化微调假说 · 经典启发式结构变换 · DAVIS 冻结基准模型即时定量打分
                </p>
              </div>
            </div>
          </div>

          {/* 模式状态徽章 */}
          <div className="flex items-center gap-2 self-start md:self-auto">
            {hasLLMConfigured ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300">
                <Cpu size={15} className="text-emerald-600 dark:text-emerald-400" />
                <div className="text-left">
                  <span className="font-semibold">已连接大模型生成模式</span>
                  <span className="block text-[10px] text-emerald-600 dark:text-emerald-400 font-mono">
                    {llmProvider} ({modelName})
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800 text-xs text-sky-800 dark:text-sky-300">
                <Zap size={15} className="text-sky-600 dark:text-sky-400" />
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
            <span><strong>结构衍生物生成</strong>：基于药效团电子等排体、氟扫描、增溶侧链或 LLM 深度药化推理提出改构 SMILES。</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 flex items-center justify-center shrink-0 font-bold font-mono text-[11px]">2</span>
            <span><strong>冻结模型定量打分</strong>：严禁大模型捏造预测数值，所有候选分子均输入双盲隔离训练的 Ridge 基准模型即时评测。</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-300 flex items-center justify-center shrink-0 font-bold font-mono text-[11px]">3</span>
            <span><strong>增益阶梯呈现</strong>：计算 ΔpKd、Kd 结合增益倍数与亲和力等级跃迁，并可一键送入分子库暂存或跨模块分析。</span>
          </div>
        </div>
      </div>

      {/* 预设经典场景快捷选择 */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        <span className="text-slate-400 dark:text-slate-500 font-medium shrink-0 flex items-center gap-1">
          <Compass size={13} /> 经典改构探索场景：
        </span>
        {PRESET_EXAMPLES.map((item, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => applyPreset(item)}
            className="px-2.5 py-1 rounded-md bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 shrink-0 transition-colors shadow-2xs font-medium"
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* 参数配置与输入工作区 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* 左侧：母体小分子与受体激酶设定 (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-2.5">
              <FlaskConical size={16} className="text-blue-600" />
              <span>先导母体抑制剂 (Lead Mother Molecule)</span>
            </h3>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  从 DAVIS 基准抑制剂中快速选择
                </label>
                <span className="text-[11px] text-slate-400 font-mono">共 {drugs.length} 种已注册药物</span>
              </div>
              <select
                aria-label="从 DAVIS 基准抑制剂中快速选择"
                className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium focus:ring-2 focus:ring-blue-500"
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
                <span className="text-[10px] text-slate-400 font-mono">长度: {drugSmiles.length} 字符</span>
              </div>
              <textarea
                rows={2}
                value={drugSmiles}
                onChange={e => setDrugSmiles(e.target.value)}
                placeholder="例如：CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO"
                className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 font-mono text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* 靶点激酶 */}
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Dna size={16} className="text-indigo-600" />
                <span>靶点激酶受体 (Target Kinase Receptor)</span>
              </h3>

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
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200 font-medium"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                    从 379 种 DAVIS 激酶库预选
                  </label>
                  <select
                    aria-label="从 379 种 DAVIS 激酶库预选"
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
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
                  placeholder="如：MLEICLKLVGCKSKKGLSSSSSCYLEEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSITKGEKLRVLGYNHNGEWCEAQTKNGQGWVPSNYITPVNSLEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISLRYEGRVYHYRINTASDGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTVYGVSPNYDKWEMERTDITMKHKLGGGQYGEVYEGVWKKYSLTVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVVLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNKFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAKSPKPSNGAGVPNGALRESGGSGFRSPHLWKKSSTLTSSRLATGEEEGGGSSSKRFLRSCSASCVPHGAKDTEWRSVTLPRDLQSTGRQFDSSTFGGHKSEKPALPRKRAGENRSDQVTRGTVTPPPRLVKKNEEAADEVFKDIMESSPGSSPPNLTPKPLRRQVTVAPASGLPHKEEAEKGSALGTPAAAEPVTPTSKAGSGAPGGTSKGPAEESRVRRHKHSSESPGRDKGKLSRLKPAPPPPPAASAGKAGGKPSQSPSQEAAGEAVLGAKTKATSLVDAVNSDAAKPSQPGEGLKKPVLPATPKPQSAKPSGTPISPAPVPSTLPSASSALAGDQPSSTAFIPLISTRVSLRKTRQPPERIASGAITKGVVLDSTEALCLAISRNSEQMASHSAVLEAGKNLYTFCVSYVDSIQQMRNKFAFREAINKLENNLRELQICPATAGSGPAATQDFSKLLSSVKEISDIVQR"
                  className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 font-mono text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

          </div>
        </div>

        {/* 右侧：改构目标与执行控制 (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4 flex flex-col justify-between h-full">
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
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium focus:ring-2 focus:ring-blue-500"
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
                  rows={3}
                  value={customInstruction}
                  onChange={e => setCustomInstruction(e.target.value)}
                  placeholder="例如：在苯环无阻碍位点探查卤素结合；引入碱性中心；保持激酶铰链区双氢键供体-受体骨架..."
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-blue-500"
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
                  className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium"
                >
                  <option value="stacked_ensemble">★ Stacking 集成模型 [最新 · 激酶口袋增强 + 元融合 CI=0.7571]</option>
                  <option value="ridge">Ridge 岭回归 [经典基准 · 双盲冷启动 CI=0.7262]</option>
                  <option value="ridge_alpha10">Ridge α=10 [强正则化 · 双盲外推稳健 CI=0.7004]</option>
                  <option value="hist_gradient_boosting">HistGBM [梯度提升树 · 非线性已知域拟合]</option>
                </select>
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
                disabled={isOptimizing}
                className={`w-full py-3 px-4 rounded-xl font-semibold text-xs flex items-center justify-center gap-2 shadow-sm transition-all ${
                  isOptimizing
                    ? 'bg-blue-400 text-white cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white hover:shadow-md active:scale-[0.99]'
                }`}
              >
                {isOptimizing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>正在进行 AI 药化改构推理与基准定量打分...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>开始 AI 智能改构与定量亲和力评估 (Run Lead Optimization)</span>
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
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xs flex flex-col justify-between">
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
                <div className="text-xs text-slate-500 mt-1 font-mono">
                  Kd: <strong>{optimizeResult.baseline.predicted_kd_nM} nM</strong> · {optimizeResult.baseline.affinity_tier}
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
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                生成与打分衍生分子
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-blue-600 dark:text-blue-400">
                  {optimizeResult.summary.candidates_evaluated}
                </span>
                <span className="text-xs text-slate-500">个候选设计</span>
              </div>
              <div className="text-xs text-slate-500 mt-1">
                工作模式: <span className="font-mono text-slate-700 dark:text-slate-300">{optimizeResult.mode}</span>
              </div>
              <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 font-mono">
                打分模型: {optimizeResult.model_used}
              </span>
            </div>

            {/* 最佳改构方案 */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                最佳优化分子方案
              </span>
              <div className="text-base font-bold text-slate-800 dark:text-slate-100 truncate" title={optimizeResult.summary.best_candidate}>
                {optimizeResult.summary.best_candidate}
              </div>
              <div className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold mt-1 font-mono">
                预测最优 Kd: {optimizeResult.summary.best_kd_nM} nM
              </div>
              <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 font-semibold">
                最高增益候选
              </span>
            </div>

            {/* 最大亲和力增益 */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                最高亲和力增益 ΔpKd
              </span>
              <div className="flex items-baseline gap-2">
                <span className={`text-2xl font-bold font-mono ${
                  optimizeResult.summary.max_affinity_gain_pkd > 0 
                    ? 'text-emerald-600 dark:text-emerald-400' 
                    : 'text-slate-600 dark:text-slate-400'
                }`}>
                  {optimizeResult.summary.max_affinity_gain_pkd > 0 ? `+${optimizeResult.summary.max_affinity_gain_pkd}` : optimizeResult.summary.max_affinity_gain_pkd}
                </span>
                <span className="text-xs text-slate-500 font-mono">pKd 单位</span>
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {optimizeResult.summary.max_affinity_gain_pkd > 0 ? (
                  <span className="text-emerald-600 font-semibold flex items-center gap-1">
                    <ArrowUpRight size={13} /> 亲和结合力显著增强
                  </span>
                ) : (
                  <span className="text-slate-500 flex items-center gap-1">
                    <Minus size={13} /> 与母体基本相当
                  </span>
                )}
              </div>
              <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono">
                靶点: {optimizeResult.target_name}
              </span>
            </div>

          </div>

          {/* 候选分子改构阶梯呈现列表 */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <TrendingUp size={18} className="text-blue-600" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  改构衍生分子阶梯排行榜 (Molecular Evolution Ladder)
                </h3>
              </div>
              <span className="text-xs text-slate-400 font-mono">按预测 pKd 亲和力高低严格降序排列</span>
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

                        {/* 成药性指标 (Lipinski Rule of 5) 诊断条 */}
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 p-2 rounded-lg bg-slate-50/60 dark:bg-slate-950/40 border border-slate-100 dark:border-slate-800/80 text-[11px] font-mono text-slate-600 dark:text-slate-400">
                          <span>MW: <strong className="text-slate-800 dark:text-slate-200">{dl.mw}</strong> g/mol</span>
                          <span>LogP: <strong className="text-slate-800 dark:text-slate-200">{dl.logp}</strong></span>
                          <span>TPSA: <strong className="text-slate-800 dark:text-slate-200">{dl.tpsa}</strong> Å²</span>
                          <span>HBD/HBA: <strong className="text-slate-800 dark:text-slate-200">{dl.hbd}/{dl.hba}</strong></span>
                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-sans font-medium ${
                            dl.badge_color === 'emerald'
                              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                              : dl.badge_color === 'amber'
                              ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                              : 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                          }`}>
                            {dl.druglikeness_tier}
                          </span>
                        </div>

                        {/* SMILES 代码与复制 */}
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-slate-100 dark:bg-slate-950 rounded px-2.5 py-1.5 font-mono text-[11px] text-slate-600 dark:text-slate-300 truncate">
                            {cand.smiles}
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopySmiles(cand.id, cand.smiles)}
                            className="p-1.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors shrink-0 text-xs flex items-center gap-1"
                            title="复制 SMILES 字符串"
                          >
                            {copiedId === cand.id ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
                            <span className="text-[10px]">{copiedId === cand.id ? '已复制' : '复制'}</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSaveToCart(cand)}
                            className="p-1.5 rounded bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/60 text-blue-700 dark:text-blue-300 transition-colors shrink-0 text-xs flex items-center gap-1 font-medium"
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
                          <span className="text-[10px] text-slate-400 uppercase font-mono block">预测定量 pKd</span>
                          <span className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100">
                            {cand.predicted_pkd}
                          </span>
                          <span className="block text-xs font-mono text-slate-500">
                            Kd: <strong>{cand.predicted_kd_nM} nM</strong>
                          </span>
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
                            {cand.status} ({cand.fold_change}x)
                          </span>
                        </div>

                        <div className="text-right mt-2">
                          <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                            cand.affinity_tier_code === 'high_affinity'
                              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                              : 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                          }`}>
                            {cand.affinity_tier}
                          </span>
                        </div>
                      </div>

                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      )}

      {/* 底部科学自律声明 */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/30 text-xs text-slate-500 dark:text-slate-400 space-y-1">
        <div className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300">
          <Info size={14} className="text-blue-500" />
          <span>科学自律与计算验证声明</span>
        </div>
        <p className="leading-relaxed">
          本工作台为纯计算辅助设计系统。衍生分子的 SMILES 与假说由药化启发式引擎或用户配置的大模型生成，定量亲和力评估一律由经过双盲冷启动协议（Dual-Cold Split）独立训练和密码学哈希审计的 Ridge 冻结基准模型计算。所有预测增益均属计算先导探索，不可替代湿法生化活性（Kd/IC50）与晶体结构测定。
        </p>
      </div>

    </div>
  );
}
