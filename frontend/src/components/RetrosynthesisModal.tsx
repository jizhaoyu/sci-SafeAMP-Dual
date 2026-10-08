import React, { useState, useEffect } from 'react';
import {
  X,
  TestTube,
  Package,
  Layers,
  ArrowRight,
  TrendingUp,
  Percent,
  FlaskConical,
  ExternalLink,
  Copy,
  Check,
  AlertCircle,
  Clock,
  Sparkles,
  Download,
  Info
} from 'lucide-react';
import {
  planRetrosynthesisRoute,
  type RetrosynthesisRoutePlan,
  type CommercialPrecursor,
  type ReactionStep
} from '../api/dtiClient';

interface RetrosynthesisModalProps {
  isOpen: boolean;
  onClose: () => void;
  smiles: string;
  moleculeName?: string;
}

export const RetrosynthesisModal: React.FC<RetrosynthesisModalProps> = ({
  isOpen,
  onClose,
  smiles,
  moleculeName = '目标化合物'
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<RetrosynthesisRoutePlan | null>(null);
  const [copiedCas, setCopiedCas] = useState<string | null>(null);
  const [copiedSmi, setCopiedSmi] = useState(false);

  useEffect(() => {
    if (isOpen && smiles) {
      loadRetrosynthesisPlan();
    }
  }, [isOpen, smiles]);

  if (!isOpen) return null;

  const loadRetrosynthesisPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await planRetrosynthesisRoute({
        smiles,
        molecule_name: moleculeName
      });
      setPlan(data);
    } catch (err: any) {
      setError(err?.message || '逆合成路线规划失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCas = (cas: string) => {
    navigator.clipboard.writeText(cas);
    setCopiedCas(cas);
    setTimeout(() => setCopiedCas(null), 1800);
  };

  const handleCopySmi = () => {
    navigator.clipboard.writeText(smiles);
    setCopiedSmi(true);
    setTimeout(() => setCopiedSmi(false), 1800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-5xl max-h-[92vh] flex flex-col bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-slate-900 via-emerald-950/30 to-slate-900 border-b border-slate-700/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-inner">
              <TestTube className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold tracking-tight text-white">
                  AI 计算机辅助逆合成路线规划 (AI Retrosynthesis Planner)
                </h3>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  CAS & Synthon Disconnection
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                基于现代有机合成逻辑切断逆合成子，输出包含真实商业 CAS 试剂、催化剂与步阶收率的前向合成方案
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

        {/* Target Molecule Summary */}
        <div className="px-6 py-3 bg-slate-800/60 border-b border-slate-700/60 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-3">
            <span className="font-semibold text-slate-300">目标分子:</span>
            <span className="font-bold text-white bg-slate-900 px-2 py-0.5 rounded border border-slate-700">
              {moleculeName}
            </span>
            <span className="font-mono text-slate-400 truncate max-w-md hidden sm:inline select-all">
              {smiles}
            </span>
          </div>
          <button
            onClick={handleCopySmi}
            className="text-xs px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded text-slate-300 hover:text-white flex items-center space-x-1.5 transition"
          >
            {copiedSmi ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>已复制 SMILES</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>复制 SMILES</span>
              </>
            )}
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="py-20 text-center space-y-3">
              <FlaskConical className="w-10 h-10 mx-auto text-emerald-400 animate-bounce" />
              <p className="text-sm font-semibold text-slate-300">正在进行拓扑切断与商业 CAS 库匹配...</p>
              <p className="text-xs text-slate-500">正在搜索毕得医药、药石科技、Enamine 现货试剂库与最佳催化剂溶剂体系</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {plan && !loading && (
            <div className="space-y-6">
              {/* KPI Header Bar */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center">
                  <span className="text-xs text-slate-400 block">合成总步数</span>
                  <span className="text-xl font-bold text-white mt-1 block">
                    {plan.total_steps} 步
                  </span>
                  <span className="text-[10px] text-emerald-400 block mt-0.5">短程高收率</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center">
                  <span className="text-xs text-slate-400 block">路线拓扑构型</span>
                  <span className="text-xs font-bold text-indigo-300 mt-1.5 block truncate">
                    {plan.route_convergence.split(' ')[0]}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">模块化装配</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center">
                  <span className="text-xs text-slate-400 block">预估累积总收率</span>
                  <span className="text-xl font-bold text-emerald-400 font-mono mt-1 block">
                    {plan.cumulative_yield_percent}%
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">理论摩尔收率</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center">
                  <span className="text-xs text-slate-400 block">原子经济性评价</span>
                  <span className="text-xl font-bold text-cyan-300 mt-1 block">
                    {plan.atom_economy_rating}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">低副产物废弃</span>
                </div>
              </div>

              {/* Commercial Precursors Section */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                    <Package className="w-4 h-4 text-emerald-400" />
                    <span>商业现货起始原料清单 (Commercial Starting Materials)</span>
                  </h4>
                  <span className="text-[11px] text-slate-400">
                    共收录 {plan.commercial_precursors.length} 种商业可采购核心砌块
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {plan.commercial_precursors.map((p) => (
                    <div
                      key={p.reagent_id}
                      className="p-3.5 rounded-xl bg-slate-800/90 border border-slate-700/80 hover:border-emerald-500/50 transition space-y-2 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                            {p.reagent_id}
                          </span>
                          <button
                            onClick={() => handleCopyCas(p.cas_number)}
                            className="text-[11px] font-mono text-indigo-300 hover:text-indigo-200 flex items-center space-x-1"
                            title="点击复制 CAS 号"
                          >
                            <span>CAS: {p.cas_number}</span>
                            {copiedCas === p.cas_number ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                        <h5 className="text-xs font-semibold text-white mt-1.5 line-clamp-1" title={p.name}>
                          {p.name}
                        </h5>
                        <p className="text-[10px] font-mono text-slate-400 mt-1 truncate">
                          {p.smiles}
                        </p>
                      </div>

                      <div className="pt-2 border-t border-slate-700/60 text-[11px] space-y-1">
                        <div className="flex justify-between text-slate-400">
                          <span>预估单价:</span>
                          <span className="font-semibold text-amber-300 font-mono">{p.estimated_cost}</span>
                        </div>
                        <div className="flex justify-between text-slate-400">
                          <span>纯度规格:</span>
                          <span className="text-slate-200">{p.commercial_purity}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 truncate">
                          <span>现货供应商: </span>
                          <span className="text-slate-300">{p.suppliers.join(' / ')}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Reaction Steps Tree */}
              <div className="space-y-4">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                  <Layers className="w-4 h-4 text-indigo-400" />
                  <span>逐步前向反应工艺路线 (Stepwise Synthetic Reaction Process)</span>
                </h4>

                <div className="space-y-4">
                  {plan.synthesis_steps.map((step) => (
                    <div
                      key={step.step_number}
                      className="p-5 rounded-xl bg-slate-800/80 border border-slate-700/80 relative space-y-3"
                    >
                      {/* Step Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center space-x-2">
                          <span className="w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center flex-shrink-0">
                            {step.step_number}
                          </span>
                          <h5 className="text-sm font-bold text-white">{step.step_title}</h5>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="px-2.5 py-0.5 text-xs font-semibold rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                            {step.reaction_type}
                          </span>
                          <span className="px-2.5 py-0.5 text-xs font-bold font-mono rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                            收率 {step.estimated_yield_percent}%
                          </span>
                        </div>
                      </div>

                      {/* Reactants and Product Schema */}
                      <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-700/60 text-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-2">
                        <div className="space-y-0.5">
                          <span className="text-[10px] text-slate-400 block font-semibold">反应原料:</span>
                          <span className="text-slate-200">{step.reactants.join(' + ')}</span>
                        </div>
                        <ArrowRight className="w-4 h-4 text-slate-500 hidden md:block flex-shrink-0" />
                        <div className="space-y-0.5 text-right md:text-left">
                          <span className="text-[10px] text-slate-400 block font-semibold">生成产物:</span>
                          <span className="text-emerald-300 font-medium">{step.product_name}</span>
                        </div>
                      </div>

                      {/* Detailed Reagents & Conditions */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
                        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800 space-y-1">
                          <span className="text-[11px] font-semibold text-slate-400 block">催化剂与碱配体体系:</span>
                          <p className="text-slate-200 font-mono text-[11px]">{step.catalyst_and_bases}</p>
                          <span className="text-[10px] text-slate-500 block">难度评级: {step.operational_difficulty}</span>
                        </div>

                        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800 space-y-1">
                          <span className="text-[11px] font-semibold text-slate-400 block">溶剂配比与温控条件:</span>
                          <p className="text-slate-200 font-mono text-[11px]">{step.solvent_and_conditions}</p>
                          <span className="text-[10px] text-slate-500 block">纯化规程: {step.purification_method}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Chemist Evaluation Callout */}
              <div className="p-4 rounded-xl bg-slate-800/90 border border-indigo-500/30 flex items-start space-x-3">
                <Sparkles className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1 text-xs">
                  <span className="font-bold text-white">资深计算化学与工艺药化专家评审意见:</span>
                  <p className="text-slate-300 leading-relaxed">{plan.expert_chemist_evaluation}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
