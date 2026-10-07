import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  FlaskConical, 
  BarChart3
} from 'lucide-react';
import { 
  fetchDTIDrugs, 
  fetchDTITargets, 
  predictDTIAffinity, 
  profileKinasePanel,
  type DTIDrug, 
  type DTITarget, 
  type DTIPredictionResult,
  type KinomeProfileItem
} from '../api/dtiClient';

export default function DTIStudio() {
  const [drugs, setDrugs] = useState<DTIDrug[]>([]);
  const [targets, setTargets] = useState<DTITarget[]>([]);
  
  // Selection / Input states
  const [selectedDrugId, setSelectedDrugId] = useState<string>('');
  const [drugSmiles, setDrugSmiles] = useState<string>('');
  const [selectedTargetId, setSelectedTargetId] = useState<string>('');
  const [targetSequence, setTargetSequence] = useState<string>('');
  const [modelName, setModelName] = useState<string>('stacked_ensemble');
  
  // Loading & Result states
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isProfiling, setIsProfiling] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<DTIPredictionResult | null>(null);
  const [profileResults, setProfileResults] = useState<KinomeProfileItem[] | null>(null);
  const [activeTab, setActiveTab] = useState<'predict' | 'profiling' | 'leaderboard'>('predict');

  useEffect(() => {
    fetchDTIDrugs().then(data => {
      setDrugs(data);
      if (data.length > 0) {
        setSelectedDrugId(data[0].id);
        setDrugSmiles(data[0].smiles);
      }
    }).catch(err => console.error('Drugs fetch error:', err));

    fetchDTITargets().then(data => {
      setTargets(data);
      if (data.length > 0) {
        setSelectedTargetId(data[0].id);
        setTargetSequence(data[0].sequence);
      }
    }).catch(err => console.error('Targets fetch error:', err));
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

  const handlePredict = async () => {
    if (!drugSmiles.trim() || !targetSequence.trim()) {
      setErrorMsg('请同时提供合法的小分子 SMILES 和靶点蛋白序列。');
      return;
    }
    setErrorMsg(null);
    setIsLoading(true);
    try {
      const res = await predictDTIAffinity(drugSmiles.trim(), targetSequence.trim(), modelName);
      setResult(res);
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

  return (
    <div className="space-y-6">
      {/* Top Banner / Protocol Card */}
      <div className="bg-gradient-to-r from-blue-900/90 via-indigo-900/90 to-slate-900 text-white p-6 rounded-xl border border-blue-700/50 shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck size={13} />
                PROTOCOL-DTI-01 FROZEN
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-200 border border-blue-500/30 flex items-center gap-1">
                <CheckCircle2 size={13} />
                数学严格证明零泄漏 (Zero Leakage)
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight">DAVIS 激酶亲和力（Kd）双盲冷启动预测系统</h2>
            <p className="text-sm text-slate-300 mt-1 max-w-3xl">
              基于哈佛大学 Dataverse 官方金标准 DAVIS 激酶全矩阵（25,772 实测对，68 种小分子 $\times$ 379 种激酶），通过双图块拓扑隔离阻断记忆泛化，实现严格双盲（Dual-Cold）结合亲和力连续回归与激酶谱系选择性分析。
            </p>
          </div>
          
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTab('predict')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'predict' 
                  ? 'bg-blue-600 text-white shadow' 
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
              }`}
            >
              在线预测控制台
            </button>
            <button
              onClick={() => setActiveTab('profiling')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'profiling' 
                  ? 'bg-blue-600 text-white shadow' 
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
              }`}
            >
              激酶选择性谱 (Kinome Panel)
            </button>
            <button
              onClick={() => setActiveTab('leaderboard')}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'leaderboard' 
                  ? 'bg-blue-600 text-white shadow' 
                  : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
              }`}
            >
              四大域基准天梯榜
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'predict' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Input Section (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* 1. Small Molecule Input Card */}
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xs">
                    1
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">小分子激酶抑制剂配体 (Small Molecule)</h3>
                </div>
                <span className="text-xs text-slate-500 font-mono">Morgan 指纹 (r=2, 2048-bit)</span>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    从 DAVIS 基准集预置药物载入（已关联 PubChem 通用药名）：
                  </label>
                  <select
                    value={selectedDrugId}
                    onChange={(e) => handleDrugChange(e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
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
                    className="w-full font-mono text-xs p-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* 2. Target Kinase Input Card */}
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">
                    2
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">人类催化激酶靶点 (Kinase Domain Target)</h3>
                </div>
                <span className="text-xs text-slate-500 font-mono">AAC + 理化描述符 (28 维)</span>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    从 DAVIS 基准集 379 种人类激酶中选择（切换自动联动序列）：
                  </label>
                  <select
                    value={selectedTargetId}
                    onChange={(e) => handleTargetChange(e.target.value)}
                    className="w-full text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
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
                    rows={4}
                    value={targetSequence}
                    onChange={(e) => setTargetSequence(e.target.value)}
                    placeholder="输入 20 种标准天然氨基酸序列..."
                    className="w-full font-mono text-xs p-2.5 bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 uppercase"
                  />
                  <div className="text-[11px] text-slate-400 mt-1 flex justify-between">
                    <span>当前残基数：{targetSequence.replace(/\s/g, '').length} aa</span>
                    <span>支持标准激酶催化域（200~1000 aa）</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 3. Model Selector & Action Button */}
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <label className="block text-xs font-bold text-slate-800 dark:text-slate-200 mb-2">
                选择推断基线模型：
              </label>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
                {[
                  { id: 'stacked_ensemble', name: '★ Stacking 集成模型', badge: '最新产物 · CI 0.7571', desc: '激酶口袋增强 + 元学习融合' },
                  { id: 'ridge', name: 'Ridge 岭回归', badge: '经典基准 · CI 0.7262', desc: '双盲冷启动基线' },
                  { id: 'ridge_alpha10', name: 'Ridge α=10 (强正则)', badge: '双盲泛化最优', desc: '抗外推偏移' },
                  { id: 'hist_gradient_boosting', name: 'HistGBM 提升树', badge: '非线性树模型', desc: '已知域拟合强' },
                  { id: 'mlp', name: 'MLP 神经网络', badge: '深度感知机', desc: '非线性拟合' },
                  { id: 'dummy_mean', name: 'Dummy 统计均值', badge: '基线标尺', desc: '均值绝对下界' }
                ].map(m => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setModelName(m.id)}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      modelName === m.id
                        ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/40 text-blue-900 dark:text-blue-100 ring-1 ring-blue-500'
                        : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <div className="text-xs font-bold">{m.name}</div>
                    <div className="text-[10px] text-blue-600 dark:text-blue-400 font-medium">{m.badge}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{m.desc}</div>
                  </button>
                ))}
              </div>

              {errorMsg && (
                <div className="mb-4 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
                  <AlertCircle size={15} />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handlePredict}
                  disabled={isLoading}
                  className="flex-1 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>正在推断...</span>
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
                  className="py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
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
              <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-md space-y-5">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                    <Sparkles className="text-amber-500" size={16} />
                    预测推断结果 (Prediction Output)
                  </h3>
                  <span className="text-xs px-2 py-0.5 rounded font-mono bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
                    {result.model_used.toUpperCase()}
                  </span>
                </div>

                {/* Score Hero Panel */}
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center space-y-2">
                  <div className="text-xs text-slate-500 font-medium">预测负对数亲和力 (pKd)</div>
                  <div className="text-4xl font-extrabold text-blue-600 dark:text-blue-400 font-mono tracking-tight">
                    {result.predicted_pkd.toFixed(3)}
                  </div>
                  
                  <div className="pt-2 border-t border-slate-200 dark:border-slate-700 flex items-center justify-around text-xs">
                    <div>
                      <span className="text-slate-400 block text-[10px]">解离常数 (Kd)</span>
                      <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                        {result.predicted_kd_nM < 1000 
                          ? `${result.predicted_kd_nM.toFixed(1)} nM` 
                          : `${(result.predicted_kd_nM / 1000).toFixed(2)} μM`}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">亲和力分级</span>
                      <span className={`font-semibold px-2 py-0.5 rounded-full text-[11px] ${
                        result.affinity_tier_code === 'high_affinity'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                          : result.affinity_tier_code === 'moderate_affinity'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                          : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                      }`}>
                        {result.affinity_tier}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Domain & Zero-Leakage Badge */}
                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 space-y-2">
                  <div className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                    <span>拓扑评估域诊断：</span>
                    <span className="text-blue-600 dark:text-blue-400 font-mono text-[11px]">
                      {result.domain}
                    </span>
                  </div>
                  
                  <div className="text-xs text-slate-600 dark:text-slate-400">
                    {result.domain_label}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 text-slate-500 font-mono">
                    <div className="bg-slate-50 dark:bg-slate-800 p-2 rounded">
                      训练药物最高相似度:
                      <span className="block font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                        {(result.max_drug_similarity_to_train * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800 p-2 rounded">
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
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                        <span className="text-slate-400 block text-[10px]">RMSE 均方根误差</span>
                        <span className="font-bold">{result.domain_benchmark_metrics.rmse?.toFixed(4)}</span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                        <span className="text-slate-400 block text-[10px]">Pearson r 相关性</span>
                        <span className="font-bold">{result.domain_benchmark_metrics.pearson_r?.toFixed(4)}</span>
                      </div>
                      <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                        <span className="text-slate-400 block text-[10px]">CI 一致性指数</span>
                        <span className="font-bold text-blue-600 dark:text-blue-400">{result.domain_benchmark_metrics.concordance_index?.toFixed(4)}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Provenance Alert */}
                <div className="text-[11px] text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-3 space-y-1">
                  <div>基准协议：<span className="font-mono text-slate-500">{result.provenance.protocol}</span></div>
                  <div>训练运行：<span className="font-mono text-slate-500">{result.provenance.training_run}</span></div>
                  <div className="text-amber-600 dark:text-amber-400 pt-1">{result.warning}</div>
                </div>

              </div>
            ) : (
              <div className="h-full min-h-[350px] flex flex-col items-center justify-center p-8 bg-slate-50/50 dark:bg-slate-900/50 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl text-center">
                <FlaskConical size={36} className="text-slate-300 dark:text-slate-600 mb-3" />
                <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">等待输入执行推断</h4>
                <p className="text-xs text-slate-400 mt-1 max-w-xs">
                  在左侧选择或输入小分子与激酶序列后，点击“执行单点结合亲和力预测”或“激酶谱系选择性分析”，即可实时查看预测评分、评估域诊断与可靠度指标。
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Profiling Tab */}
      {activeTab === 'profiling' && (
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
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
            
            <button
              onClick={handleRunProfiling}
              disabled={isProfiling}
              className="py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-lg shadow-xs transition-colors flex items-center gap-1.5"
            >
              {isProfiling ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Sparkles size={14} />}
              <span>重新测定谱系</span>
            </button>
          </div>

          {profileResults && profileResults.length > 0 ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {profileResults.map((item, idx) => {
                  const barPercent = Math.max(0, Math.min(100, ((item.predicted_pkd - 5.0) / 4.5) * 100));
                  return (
                    <div key={item.kinase_name} className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-slate-200 dark:bg-slate-700 text-[10px] font-bold flex items-center justify-center">
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
                          <span className="text-[10px] text-slate-400 block">
                            Kd ≈ {item.predicted_kd_nM < 1000 ? `${item.predicted_kd_nM.toFixed(0)} nM` : `${(item.predicted_kd_nM / 1000).toFixed(1)} μM`}
                          </span>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
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

                      <div className="flex items-center justify-between text-[11px] text-slate-500">
                        <span>{item.affinity_tier}</span>
                        <span className="font-mono text-[10px]">{item.domain}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-xs text-slate-400 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              点击上方“重新测定谱系”或在预测控制台点击“激酶谱系选择性分析”，系统将自动筛选并在 16 个代表性激酶上输出亲和力阶梯图。
            </div>
          )}
        </div>
      )}

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
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
                <tr className="bg-blue-50/30 dark:bg-blue-950/20 font-semibold">
                  <td rowSpan={4} className="p-3 font-bold text-blue-900 dark:text-blue-200 border-r border-slate-200 dark:border-slate-800">
                    严格双盲冷启动<br />(Strict Dual-Cold Test)
                    <div className="text-[10px] text-blue-600 dark:text-blue-400 font-normal mt-0.5">药靶双未见 · 0 泄漏</div>
                  </td>
                  <td rowSpan={4} className="p-3 border-r border-slate-200 dark:border-slate-800 font-mono">
                    975 对<br />(3.78%)
                  </td>
                  <td className="p-3 font-bold text-emerald-600">Ridge (岭回归)</td>
                  <td className="p-3 font-mono">0.7958</td>
                  <td className="p-3 font-mono">0.5357</td>
                  <td className="p-3 font-mono">0.4065</td>
                  <td className="p-3 font-mono text-emerald-600 font-bold">0.7262</td>
                  <td className="p-3 text-[11px] text-slate-600 dark:text-slate-400">L2 正则化抗过拟合能力最强，双盲泛化最优</td>
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
                  <td className="p-3 font-bold">MLP / HistGBM</td>
                  <td className="p-3 font-mono">0.6287</td>
                  <td className="p-3 font-mono">0.4050</td>
                  <td className="p-3 font-mono">0.4903</td>
                  <td className="p-3 font-mono text-blue-600 font-bold">0.7643</td>
                  <td className="p-3 text-[11px] text-slate-600 dark:text-slate-400">已知小分子面对全新激酶时泛化良好</td>
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
                  <td className="p-3 font-bold text-emerald-600">Ridge (岭回归)</td>
                  <td className="p-3 font-mono">0.8237</td>
                  <td className="p-3 font-mono">0.5617</td>
                  <td className="p-3 font-mono">0.4464</td>
                  <td className="p-3 font-mono text-emerald-600 font-bold">0.7322</td>
                  <td className="p-3 text-[11px] text-slate-600 dark:text-slate-400">未知分子骨架虚拟筛选稳健有效</td>
                </tr>
                <tr>
                  <td className="p-3">HistGBM</td>
                  <td className="p-3 font-mono">0.8776</td>
                  <td className="p-3 font-mono">0.5642</td>
                  <td className="p-3 font-mono">0.3344</td>
                  <td className="p-3 font-mono">0.7436</td>
                  <td className="p-3 text-[11px] text-slate-500">CI 表现尚可，但 RMSE 偏高</td>
                </tr>

                {/* 4. Train Block */}
                <tr className="bg-slate-50/50 dark:bg-slate-800/40 text-slate-500">
                  <td className="p-3 font-bold border-r border-slate-200 dark:border-slate-800">
                    训练主块<br />(Train Block)
                  </td>
                  <td className="p-3 border-r border-slate-200 dark:border-slate-800 font-mono">
                    16,720 对<br />(64.88%)
                  </td>
                  <td className="p-3 font-semibold text-slate-700 dark:text-slate-300">HistGBM</td>
                  <td className="p-3 font-mono">0.6007</td>
                  <td className="p-3 font-mono">0.3833</td>
                  <td className="p-3 font-mono">0.7134</td>
                  <td className="p-3 font-mono font-bold">0.8332</td>
                  <td className="p-3 text-[11px]">已知化学空间内拟合上限，但双盲外推易过拟合</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
