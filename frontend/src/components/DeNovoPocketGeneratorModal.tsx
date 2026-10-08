import React, { useState, useEffect } from 'react';
import {
  X,
  Sparkles,
  ShieldAlert,
  Layers,
  ArrowRight,
  Copy,
  Check,
  RefreshCw,
  Cpu,
  Compass,
  TestTube,
  FileText,
  Zap,
  Target,
  ExternalLink
} from 'lucide-react';
import {
  generateDeNovoMolecules,
  type DeNovoCandidate,
  type DeNovoPocketResult
} from '../api/dtiClient';

interface DeNovoPocketGeneratorModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTargetSymbol?: string;
  onViewRetrosynthesis: (smiles: string, moleculeName: string) => void;
  onSelectCandidate?: (candidate: DeNovoCandidate) => void;
}

const QUICK_TARGETS = [
  { symbol: 'ABL1', label: 'ABL1 (野生型)' },
  { symbol: 'ABL1-T315I', label: 'ABL1-T315I (门控位阻耐药)' },
  { symbol: 'EGFR-T790M', label: 'EGFR-T790M (一代TKI耐药)' },
  { symbol: 'ALK-G1202R', label: 'ALK-G1202R (克唑替尼耐药)' },
  { symbol: 'BTK-C481S', label: 'BTK-C481S (共价脱靶突变)' },
  { symbol: 'BRAF-V600E', label: 'BRAF-V600E (黑色素瘤活化)' }
];

export const DeNovoPocketGeneratorModal: React.FC<DeNovoPocketGeneratorModalProps> = ({
  isOpen,
  onClose,
  initialTargetSymbol = 'ABL1-T315I',
  onViewRetrosynthesis,
  onSelectCandidate
}) => {
  const [targetSymbol, setTargetSymbol] = useState(initialTargetSymbol);
  const [generationMode, setGenerationMode] = useState<'scaffold_hopping' | 'gatekeeper_bypasser' | 'pocket_growth'>('scaffold_hopping');
  const [numCandidates, setNumCandidates] = useState(4);
  const [noveltyFloor, setNoveltyFloor] = useState(0.30);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DeNovoPocketResult | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    if (initialTargetSymbol) {
      setTargetSymbol(initialTargetSymbol);
      if (initialTargetSymbol.includes('T315I') || initialTargetSymbol.includes('T790M')) {
        setGenerationMode('gatekeeper_bypasser');
      }
    }
  }, [initialTargetSymbol]);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await generateDeNovoMolecules({
        target_symbol: targetSymbol,
        generation_mode: generationMode,
        num_candidates: numCandidates,
        novelty_floor: noveltyFloor
      });
      setResult(data);
    } catch (err: any) {
      setError(err?.message || '从头分子生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleCopySmiles = (id: string, smiles: string) => {
    navigator.clipboard.writeText(smiles);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-6xl max-h-[92vh] flex flex-col bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border-b border-slate-700/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-inner">
              <Sparkles className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold tracking-tight text-white">
                  3D 口袋从头分子扩散生成与骨架跃迁工作台
                </h3>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                  De Novo Diffusion & IP Hopping
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                结合 3D 催化空腔几何、活化环构象与门控残基空间位阻，实时生成高 IP 专利突破性、高亲和力并兼具合成可达性的全新骨架候选物
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Control Bar */}
        <div className="p-6 bg-slate-800/40 border-b border-slate-700/60 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Target Input & Quick Select */}
            <div className="space-y-1.5 md:col-span-1">
              <label className="text-xs font-medium text-slate-300 flex items-center space-x-1.5">
                <Target className="w-3.5 h-3.5 text-indigo-400" />
                <span>目标激酶 / 耐药突变体</span>
              </label>
              <input
                type="text"
                value={targetSymbol}
                onChange={(e) => setTargetSymbol(e.target.value.toUpperCase())}
                placeholder="例如 ABL1-T315I, EGFR"
                className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-lg text-sm font-mono text-white focus:outline-none focus:border-indigo-500 transition"
              />
              <div className="flex flex-wrap gap-1 mt-1">
                {QUICK_TARGETS.slice(0, 4).map((t) => (
                  <button
                    key={t.symbol}
                    onClick={() => {
                      setTargetSymbol(t.symbol);
                      if (t.symbol.includes('T315I') || t.symbol.includes('T790M')) {
                        setGenerationMode('gatekeeper_bypasser');
                      }
                    }}
                    className={`text-[10px] px-1.5 py-0.5 rounded border transition ${
                      targetSymbol === t.symbol
                        ? 'bg-indigo-600/30 border-indigo-400 text-indigo-200 font-semibold'
                        : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {t.symbol}
                  </button>
                ))}
              </div>
            </div>

            {/* Generation Mode Selector */}
            <div className="space-y-1.5 md:col-span-2">
              <label className="text-xs font-medium text-slate-300 flex items-center space-x-1.5">
                <Compass className="w-3.5 h-3.5 text-emerald-400" />
                <span>从头分子生成与构象引导模式</span>
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setGenerationMode('scaffold_hopping')}
                  className={`p-2.5 rounded-lg border text-left flex flex-col justify-between transition ${
                    generationMode === 'scaffold_hopping'
                      ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200 ring-1 ring-indigo-500/50'
                      : 'bg-slate-900/60 border-slate-700/80 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <span className="text-xs font-semibold">骨架跃迁模式</span>
                  <span className="text-[10px] text-slate-400 mt-1">突破现有专利壁垒，生物电子等排体重排</span>
                </button>

                <button
                  type="button"
                  onClick={() => setGenerationMode('gatekeeper_bypasser')}
                  className={`p-2.5 rounded-lg border text-left flex flex-col justify-between transition ${
                    generationMode === 'gatekeeper_bypasser'
                      ? 'bg-emerald-600/20 border-emerald-500 text-emerald-200 ring-1 ring-emerald-500/50'
                      : 'bg-slate-900/60 border-slate-700/80 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <span className="text-xs font-semibold">门控突变规避模式</span>
                  <span className="text-[10px] text-slate-400 mt-1">亚埃级刚性链接穿透 T315I/T790M 位阻</span>
                </button>

                <button
                  type="button"
                  onClick={() => setGenerationMode('pocket_growth')}
                  className={`p-2.5 rounded-lg border text-left flex flex-col justify-between transition ${
                    generationMode === 'pocket_growth'
                      ? 'bg-cyan-600/20 border-cyan-500 text-cyan-200 ring-1 ring-cyan-500/50'
                      : 'bg-slate-900/60 border-slate-700/80 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <span className="text-xs font-semibold">空腔生长延伸模式</span>
                  <span className="text-[10px] text-slate-400 mt-1">深腔诱导契合与溶剂暴露区增溶延伸</span>
                </button>
              </div>
            </div>

            {/* Candidate Count & Action */}
            <div className="space-y-1.5 md:col-span-1 flex flex-col justify-between">
              <div>
                <label className="text-xs font-medium text-slate-300 flex items-center justify-between">
                  <span>生成候选物数量: {numCandidates}</span>
                  <span className="text-[10px] text-slate-400">新颖度 ≥ {Math.round(noveltyFloor * 100)}%</span>
                </label>
                <div className="flex items-center space-x-2 mt-1.5">
                  {[4, 6, 8].map((c) => (
                    <button
                      key={c}
                      onClick={() => setNumCandidates(c)}
                      className={`flex-1 py-1 text-xs rounded border transition ${
                        numCandidates === c
                          ? 'bg-indigo-600 border-indigo-400 text-white font-bold'
                          : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-white'
                      }`}
                    >
                      {c} 个
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleGenerate}
                disabled={loading || !targetSymbol.trim()}
                className="w-full mt-2 py-2.5 px-4 bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 disabled:opacity-50 text-white font-semibold rounded-lg shadow-lg flex items-center justify-center space-x-2 transition cursor-pointer"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-white" />
                    <span>3D空间扩散生成中...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 text-amber-300 fill-amber-300" />
                    <span>启动 3D 口袋从头生成</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center space-x-3">
              <ShieldAlert className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!result && !loading && (
            <div className="py-16 text-center text-slate-500 space-y-3">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 shadow-inner">
                <Cpu className="w-8 h-8 opacity-70" />
              </div>
              <h4 className="text-base font-semibold text-slate-300">尚未运行 3D 口袋从头扩散生成</h4>
              <p className="text-xs max-w-lg mx-auto text-slate-400">
                请在上方选择目标激酶（如野生型 ABL1 或伊马替尼耐药的 ABL1-T315I）与设计模式，算法将基于物理场与深度学习架构，实时生成新化学实体并解算 MM-GBSA 物理自由能与专利突破性。
              </p>
            </div>
          )}

          {result && (
            <div className="space-y-6">
              {/* Summary Banner */}
              <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                      生成报告摘要
                    </span>
                    <span className="text-slate-600">•</span>
                    <span className="text-xs text-slate-300 font-mono">
                      靶点: <strong className="text-white">{result.target_symbol}</strong>
                    </span>
                    {result.is_mutant_target && (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                        耐药门控突变体 ({result.gatekeeper_residue})
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-300">{result.summary}</p>
                </div>
                <div className="flex items-center space-x-3 text-xs">
                  <div className="text-center px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700">
                    <span className="block text-[10px] text-slate-400">生成候选数</span>
                    <span className="text-sm font-bold text-white">{result.total_generated}</span>
                  </div>
                  <div className="text-center px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700">
                    <span className="block text-[10px] text-slate-400">生成模式</span>
                    <span className="text-xs font-semibold text-emerald-400">{result.generation_mode_label.split(' ')[0]}</span>
                  </div>
                </div>
              </div>

              {/* Candidate Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {result.candidates.map((cand, idx) => (
                  <div
                    key={cand.candidate_id}
                    className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-indigo-500/60 transition shadow-lg flex flex-col justify-between space-y-4"
                  >
                    {/* Top Row: Name, Mode Badge, IP Novelty */}
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800">
                              {cand.candidate_id}
                            </span>
                            <h4 className="text-sm font-bold text-white">{cand.name}</h4>
                          </div>
                          <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                            {cand.design_rationale}
                          </p>
                        </div>

                        {/* IP Novelty Badge */}
                        <div className="flex flex-col items-end flex-shrink-0">
                          <span className={`px-2.5 py-1 text-xs font-extrabold rounded-lg border shadow-sm ${
                            cand.ip_novelty_score >= 0.45
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                              : 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                          }`}>
                            IP 新颖度 {(cand.ip_novelty_score * 100).toFixed(0)}%
                          </span>
                          <span className="text-[10px] text-slate-400 mt-0.5">
                            vs {cand.nearest_fda_drug} (相似度 {(cand.nearest_similarity * 100).toFixed(0)}%)
                          </span>
                        </div>
                      </div>

                      {/* Chemical Property Strip */}
                      <div className="grid grid-cols-4 gap-2 mt-4 pt-3 border-t border-slate-700/60 text-center">
                        <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                          <span className="text-[10px] text-slate-400 block">预测亲和力</span>
                          <span className="text-xs font-bold text-emerald-400 font-mono">
                            {cand.predicted_kd_nM < 1000 ? `${cand.predicted_kd_nM} nM` : `${(cand.predicted_kd_nM / 1000).toFixed(2)} µM`}
                          </span>
                          <span className="text-[9px] text-slate-500 block">pKd {cand.predicted_pkd}</span>
                        </div>

                        <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                          <span className="text-[10px] text-slate-400 block">MM-GBSA 物理能</span>
                          <span className="text-xs font-bold text-cyan-400 font-mono">
                            {cand.delta_g_bind_kcal} <span className="text-[9px] font-normal">kcal/mol</span>
                          </span>
                          <span className="text-[9px] text-slate-500 block">自发强结合</span>
                        </div>

                        <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                          <span className="text-[10px] text-slate-400 block">合成可达性</span>
                          <span className="text-xs font-bold text-amber-300 font-mono">
                            SA {cand.sa_score}
                          </span>
                          <span className="text-[9px] text-slate-400 block truncate">{cand.sa_label.slice(0, 5)}</span>
                        </div>

                        <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                          <span className="text-[10px] text-slate-400 block">分子量 / cLogP</span>
                          <span className="text-xs font-bold text-slate-200 font-mono">
                            {cand.molecular_weight}
                          </span>
                          <span className="text-[9px] text-slate-400 block font-mono">cLogP {cand.clogp}</span>
                        </div>
                      </div>

                      {/* Key Interactions */}
                      <div className="mt-3.5 space-y-1">
                        <span className="text-[11px] font-semibold text-slate-300 flex items-center space-x-1">
                          <Zap className="w-3 h-3 text-amber-400" />
                          <span>3D 口袋关键相互作用预测:</span>
                        </span>
                        <ul className="text-[11px] text-slate-400 space-y-0.5 list-disc list-inside">
                          {cand.key_interactions_predicted.map((inter, i) => (
                            <li key={i} className="truncate">{inter}</li>
                          ))}
                        </ul>
                      </div>

                      {/* SMILES box */}
                      <div className="mt-3 p-2 bg-slate-950/80 rounded-lg border border-slate-800 flex items-center justify-between">
                        <span className="text-[10px] font-mono text-slate-400 truncate max-w-[85%] select-all">
                          {cand.smiles}
                        </span>
                        <button
                          onClick={() => handleCopySmiles(cand.candidate_id, cand.smiles)}
                          className="text-slate-400 hover:text-white p-1 rounded transition"
                          title="复制 SMILES"
                        >
                          {copiedId === cand.candidate_id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Bottom Action Buttons */}
                    <div className="pt-2 border-t border-slate-700/60 flex items-center justify-between gap-3">
                      <button
                        onClick={() => onViewRetrosynthesis(cand.smiles, cand.name)}
                        className="flex-1 py-1.5 px-3 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center justify-center space-x-1.5 transition"
                      >
                        <TestTube className="w-3.5 h-3.5 text-emerald-400" />
                        <span>AI 计算机辅助逆合成路线</span>
                      </button>

                      {onSelectCandidate && (
                        <button
                          onClick={() => onSelectCandidate(cand)}
                          className="py-1.5 px-3 rounded-lg bg-slate-700 hover:bg-indigo-600 text-slate-200 hover:text-white text-xs font-semibold flex items-center space-x-1 transition"
                        >
                          <span>载入先导优化</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
