import React, { useState, useEffect } from 'react';
import {
  X,
  Search,
  Filter,
  Layers,
  Sparkles,
  Zap,
  TrendingUp,
  Cpu,
  BarChart2,
  Package,
  Check,
  Copy,
  ArrowRight,
  TestTube,
  Box,
  Target,
  FlaskConical,
  Award,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import {
  fetchScreeningLibraries,
  runVirtualScreening,
  type ScreeningLibraryMeta,
  type VirtualScreeningHit,
  type VirtualScreeningResult
} from '../api/dtiClient';
import { Molecule2DViewer } from './Molecule2DViewer';

interface VirtualScreeningModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTargetSymbol?: string;
  onViewRetrosynthesis: (smiles: string, moleculeName: string) => void;
  onSelectLead?: (hit: VirtualScreeningHit) => void;
  onViewPocket3D?: (hit: VirtualScreeningHit) => void;
}

const QUICK_TARGETS = [
  { symbol: 'ABL1', label: 'ABL1 (野生型)' },
  { symbol: 'ABL1-T315I', label: 'ABL1-T315I (门控耐药)' },
  { symbol: 'EGFR', label: 'EGFR (肺癌主靶标)' },
  { symbol: 'EGFR-T790M', label: 'EGFR-T790M (一代TKI耐药)' },
  { symbol: 'BRAF-V600E', label: 'BRAF-V600E (黑色素瘤)' },
  { symbol: 'ALK-G1202R', label: 'ALK-G1202R (耐药突变)' }
];

export const VirtualScreeningModal: React.FC<VirtualScreeningModalProps> = ({
  isOpen,
  onClose,
  initialTargetSymbol = 'ABL1',
  onViewRetrosynthesis,
  onSelectLead,
  onViewPocket3D
}) => {
  const [libraries, setLibraries] = useState<ScreeningLibraryMeta[]>([]);
  const [selectedLibId, setSelectedLibId] = useState<string>('kinase_privileged');
  const [targetSymbol, setTargetSymbol] = useState<string>(initialTargetSymbol);
  const [maxHits, setMaxHits] = useState<number>(10);
  const [minPkd, setMinPkd] = useState<number>(5.0);
  const [diversityCutoff, setDiversityCutoff] = useState<number>(0.40);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VirtualScreeningResult | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedClusterFilter, setSelectedClusterFilter] = useState<string>('all');

  useEffect(() => {
    if (isOpen) {
      fetchScreeningLibraries()
        .then(data => {
          setLibraries(data);
          if (data.length > 0 && !selectedLibId) {
            setSelectedLibId(data[0].id);
          }
        })
        .catch(console.error);
    }
  }, [isOpen]);

  useEffect(() => {
    if (initialTargetSymbol) {
      setTargetSymbol(initialTargetSymbol);
    }
  }, [initialTargetSymbol]);

  if (!isOpen) return null;

  const handleStartScreening = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runVirtualScreening({
        target_symbol: targetSymbol,
        library_id: selectedLibId,
        max_hits: maxHits,
        min_pkd_threshold: minPkd,
        diversity_cutoff: diversityCutoff
      });
      setResult(data);
      setSelectedClusterFilter('all');
    } catch (err: any) {
      setError(err?.message || '虚拟筛选运行失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleCopySmiles = (id: string, smiles: string) => {
    navigator.clipboard.writeText(smiles);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const filteredHits = result ? result.hits.filter(h => {
    if (selectedClusterFilter === 'all') return true;
    return `骨架簇-${h.cluster_id}` === selectedClusterFilter;
  }) : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-6xl max-h-[94vh] flex flex-col bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-slate-900 via-cyan-950/40 to-slate-900 border-b border-slate-700/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 shadow-inner">
              <Search className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold tracking-tight text-white">
                  超大规模商业现货分子库虚拟筛选工作台
                </h3>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  Ultra-Large Virtual Screening & Butina Clustering
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                基于三级漏斗架构（矢量化初筛 → 世界模型与 MM-GBSA 双核重排 → Butina 拓扑多样性分群），秒级淘选纳摩尔级苗头化合物 (Hits)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="关闭筛选工作台"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Screening Configuration Panel */}
        <div className="p-6 bg-slate-800/40 border-b border-slate-700/60 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Target Select */}
            <div className="space-y-1.5 md:col-span-1">
              <label className="text-xs font-medium text-slate-300 flex items-center space-x-1.5">
                <Target className="w-3.5 h-3.5 text-cyan-400" />
                <span>目标激酶 / 耐药突变体</span>
              </label>
              <input
                type="text"
                value={targetSymbol}
                onChange={(e) => setTargetSymbol(e.target.value.toUpperCase())}
                placeholder="例如 ABL1-T315I, EGFR"
                className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-lg text-sm font-mono text-white focus:outline-none focus:border-cyan-500 transition"
              />
              <div className="flex flex-wrap gap-1 mt-1">
                {QUICK_TARGETS.slice(0, 4).map((t) => (
                  <button
                    key={t.symbol}
                    onClick={() => setTargetSymbol(t.symbol)}
                    className={`text-[10px] px-1.5 py-0.5 rounded border transition ${
                      targetSymbol === t.symbol
                        ? 'bg-cyan-600/30 border-cyan-400 text-cyan-200 font-semibold'
                        : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {t.symbol}
                  </button>
                ))}
              </div>
            </div>

            {/* Library Selector */}
            <div className="space-y-1.5 md:col-span-2">
              <label className="text-xs font-medium text-slate-300 flex items-center space-x-1.5">
                <Package className="w-3.5 h-3.5 text-indigo-400" />
                <span>预置商业现货分子库 (Commercial HTS Libraries)</span>
              </label>
              <div className="grid grid-cols-3 gap-2">
                {libraries.map((lib) => (
                  <button
                    key={lib.id}
                    type="button"
                    onClick={() => setSelectedLibId(lib.id)}
                    className={`p-2.5 rounded-lg border text-left flex flex-col justify-between transition cursor-pointer ${
                      selectedLibId === lib.id
                        ? 'bg-cyan-600/20 border-cyan-500 text-cyan-200 ring-1 ring-cyan-500/50'
                        : 'bg-slate-900/60 border-slate-700/80 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <div>
                      <span className="text-xs font-semibold block">{lib.name.split(' (')[0]}</span>
                      <span className="text-[10px] text-slate-400 mt-1 line-clamp-2">{lib.description}</span>
                    </div>
                    <span className="text-[9px] font-mono text-cyan-400 mt-2 block">
                      {lib.total_compounds} 个现货分子 • 均重 {lib.average_mw}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Criteria & Action */}
            <div className="space-y-1.5 md:col-span-1 flex flex-col justify-between">
              <div>
                <label className="text-xs font-medium text-slate-300 flex items-center justify-between">
                  <span>输出 Top Hits 数量: {maxHits}</span>
                  <span className="text-[10px] text-slate-400">门限 pKd ≥ {minPkd}</span>
                </label>
                <div className="flex items-center space-x-2 mt-1.5">
                  {[8, 12, 15].map((cnt) => (
                    <button
                      key={cnt}
                      onClick={() => setMaxHits(cnt)}
                      className={`flex-1 py-1 text-xs rounded border transition ${
                        maxHits === cnt
                          ? 'bg-cyan-600 border-cyan-400 text-white font-bold'
                          : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-white'
                      }`}
                    >
                      {cnt} 个
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleStartScreening}
                disabled={loading || !targetSymbol.trim()}
                className="w-full mt-2 py-2.5 px-4 bg-gradient-to-r from-cyan-600 via-indigo-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 disabled:opacity-50 text-white font-semibold rounded-lg shadow-lg flex items-center justify-center space-x-2 transition cursor-pointer"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-white" />
                    <span>高速三级漏斗筛选中...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 text-amber-300 fill-amber-300" />
                    <span>启动高通量虚拟筛选</span>
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
              <X className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!result && !loading && (
            <div className="py-20 text-center text-slate-500 space-y-3">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 shadow-inner">
                <Search className="w-8 h-8 opacity-70" />
              </div>
              <h4 className="text-base font-semibold text-slate-300">尚未执行超大规模虚拟筛选</h4>
              <p className="text-xs max-w-lg mx-auto text-slate-400">
                请在上方选择目标激酶（如 ABL1 或耐药突变体 ABL1-T315I）与现货商业分子库，算法将启动三级漏斗高通量矢量化计算，自动完成物理自由能评价与 Butina 多样性分群。
              </p>
            </div>
          )}

          {result && (
            <div className="space-y-6">
              {/* Screening Performance KPI Bar */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center">
                  <span className="text-[10px] text-slate-400 block">海选分子总量</span>
                  <span className="text-xl font-bold text-white mt-1 block font-mono">{result.total_screened}</span>
                  <span className="text-[9px] text-cyan-400 block mt-0.5">全量商业现货</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center">
                  <span className="text-[10px] text-slate-400 block">漏斗初筛 / 精筛</span>
                  <span className="text-base font-bold text-indigo-300 mt-1 block font-mono">
                    {result.stage1_passed} → {result.stage2_passed}
                  </span>
                  <span className="text-[9px] text-slate-400 block mt-0.5">高精过滤重排</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center">
                  <span className="text-[10px] text-slate-400 block">淘选 Hits / 骨架簇</span>
                  <span className="text-xl font-bold text-emerald-400 mt-1 block font-mono">
                    {result.total_hits} 个 / {result.num_clusters} 簇
                  </span>
                  <span className="text-[9px] text-emerald-300 block mt-0.5">Butina 拓扑去重</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center">
                  <span className="text-[10px] text-slate-400 block">耗时 / 筛选通量</span>
                  <span className="text-base font-bold text-amber-300 mt-1 block font-mono">
                    {result.screening_time_seconds}s
                  </span>
                  <span className="text-[9px] text-slate-400 block mt-0.5 font-mono">{result.throughput_cpd_per_sec} cpd/s</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-800/80 border border-slate-700/80 text-center col-span-2 md:col-span-1">
                  <span className="text-[10px] text-slate-400 block">目标靶点状态</span>
                  <span className="text-sm font-bold text-white mt-1 block truncate">{result.target_symbol}</span>
                  <span className="text-[9px] text-cyan-300 block mt-0.5">
                    {result.is_mutant_target ? `门控位点: ${result.gatekeeper_residue}` : '野生型催化腔'}
                  </span>
                </div>
              </div>

              {/* Cluster Filter Buttons */}
              <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-700/60">
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Filter className="w-3.5 h-3.5 text-cyan-400" />
                  <span>按多样性骨架簇过滤:</span>
                </span>
                <button
                  onClick={() => setSelectedClusterFilter('all')}
                  className={`text-xs px-2.5 py-1 rounded-lg border transition ${
                    selectedClusterFilter === 'all'
                      ? 'bg-cyan-600 border-cyan-400 text-white font-bold'
                      : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white'
                  }`}
                >
                  全部 Hits ({result.hits.length})
                </button>
                {Object.entries(result.cluster_distribution).map(([cKey, count]) => (
                  <button
                    key={cKey}
                    onClick={() => setSelectedClusterFilter(cKey)}
                    className={`text-xs px-2.5 py-1 rounded-lg border transition ${
                      selectedClusterFilter === cKey
                        ? 'bg-indigo-600 border-indigo-400 text-white font-bold'
                        : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white'
                    }`}
                  >
                    {cKey} ({count} 个)
                  </button>
                ))}
              </div>

              {/* Top Hits Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredHits.map((hit) => (
                  <div
                    key={hit.compound_id}
                    className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:border-cyan-500/60 transition shadow-lg flex flex-col justify-between space-y-3"
                  >
                    <div>
                      {/* Top Header: Rank, Name, Cluster, Rep badge */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800">
                              #{hit.rank} {hit.compound_id}
                            </span>
                            <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                              骨架簇-{hit.cluster_id}
                            </span>
                            {hit.is_cluster_representative && (
                              <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-0.5">
                                <Award className="w-2.5 h-2.5" />
                                簇母核代表
                              </span>
                            )}
                          </div>
                          <h4 className="text-sm font-bold text-white mt-1">{hit.name}</h4>
                        </div>

                        {/* CAS Tag */}
                        <div className="text-right">
                          <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800 block">
                            CAS: {hit.cas_number}
                          </span>
                          <span className="text-[9px] text-slate-500 block mt-0.5">{hit.vendor_source.split(' / ')[0]}</span>
                        </div>
                      </div>

                      {/* 2D Structure Preview & Chemistry Props */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-700/60">
                        <div className="sm:col-span-1 flex items-center justify-center p-2 rounded-lg bg-slate-950/80 border border-slate-800">
                          <Molecule2DViewer smiles={hit.smiles} name={hit.name} width={130} height={75} showExpandButton={true} />
                        </div>

                        <div className="sm:col-span-2 grid grid-cols-2 gap-2 text-center text-xs">
                          <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                            <span className="text-[10px] text-slate-400 block">预测亲和力</span>
                            <span className="text-xs font-bold text-emerald-400 font-mono">
                              {hit.predicted_kd_nM < 1000 ? `${hit.predicted_kd_nM} nM` : `${(hit.predicted_kd_nM / 1000).toFixed(2)} µM`}
                            </span>
                            <span className="text-[9px] text-slate-500 block">pKd {hit.predicted_pkd}</span>
                          </div>

                          <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                            <span className="text-[10px] text-slate-400 block">MM-GBSA 物理能</span>
                            <span className="text-xs font-bold text-cyan-400 font-mono">
                              {hit.delta_g_bind_kcal} <span className="text-[9px] font-normal">kcal/mol</span>
                            </span>
                            <span className="text-[9px] text-slate-500 block">强自发结合</span>
                          </div>

                          <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                            <span className="text-[10px] text-slate-400 block">合成可达性</span>
                            <span className="text-xs font-bold text-amber-300 font-mono">
                              SA {hit.sa_score}
                            </span>
                            <span className="text-[9px] text-slate-400 block truncate">{hit.sa_label.slice(0, 4)}</span>
                          </div>

                          <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                            <span className="text-[10px] text-slate-400 block">分子量 / cLogP</span>
                            <span className="text-xs font-bold text-slate-200 font-mono">{hit.molecular_weight}</span>
                            <span className="text-[9px] text-slate-400 block font-mono">cLogP {hit.clogp}</span>
                          </div>
                        </div>
                      </div>

                      {/* SMILES Box */}
                      <div className="mt-2.5 p-1.5 bg-slate-950/80 rounded border border-slate-800 flex items-center justify-between">
                        <span className="text-[10px] font-mono text-slate-400 truncate max-w-[85%] select-all">
                          {hit.smiles}
                        </span>
                        <button
                          onClick={() => handleCopySmiles(hit.compound_id, hit.smiles)}
                          className="text-slate-400 hover:text-white p-1 rounded transition cursor-pointer"
                          title="复制 SMILES"
                        >
                          {copiedId === hit.compound_id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Bottom Action Strip */}
                    <div className="pt-2 border-t border-slate-700/60 flex items-center justify-between gap-2 text-xs">
                      {onViewPocket3D && (
                        <button
                          onClick={() => onViewPocket3D(hit)}
                          className="py-1 px-2 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/40 text-purple-300 text-[11px] font-semibold flex items-center space-x-1 transition cursor-pointer"
                        >
                          <Box className="w-3 h-3 text-purple-400" />
                          <span>3D 口袋</span>
                        </button>
                      )}

                      <button
                        onClick={() => onViewRetrosynthesis(hit.smiles, hit.name)}
                        className="py-1 px-2.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 text-[11px] font-semibold flex items-center space-x-1 transition cursor-pointer"
                      >
                        <TestTube className="w-3 h-3 text-emerald-400" />
                        <span>AI 逆合成路线</span>
                      </button>

                      {onSelectLead && (
                        <button
                          onClick={() => onSelectLead(hit)}
                          className="py-1 px-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-semibold flex items-center space-x-1 transition cursor-pointer"
                        >
                          <span>先导改构</span>
                          <ArrowRight className="w-3 h-3" />
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
