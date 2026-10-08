import React, { useState, useEffect, useMemo } from 'react';
import { type ClinicalTargetRecord, getClinicalTargets } from '../api/dtiClient';


interface ClinicalTargetSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTarget: (target: ClinicalTargetRecord) => void;
  currentTargetSymbol?: string;
}

export const ClinicalTargetSelectorModal: React.FC<ClinicalTargetSelectorModalProps> = ({
  isOpen,
  onClose,
  onSelectTarget,
  currentTargetSymbol
}) => {
  const [targets, setTargets] = useState<ClinicalTargetRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedFamily, setSelectedFamily] = useState<string>('ALL');
  const [filterMutantsOnly, setFilterMutantsOnly] = useState<boolean>(false);
  const [selectedTargetDetail, setSelectedTargetDetail] = useState<ClinicalTargetRecord | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    getClinicalTargets({ include_mutants: true })
      .then((data) => {
        setTargets(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load clinical targets:', err);
        setLoading(false);
      });
  }, [isOpen]);

  const filteredTargets = useMemo(() => {
    return targets.filter((t) => {
      // Family filter
      if (selectedFamily !== 'ALL') {
        if (selectedFamily === 'MUTANT') {
          if (!t.is_mutant) return false;
        } else if (t.family !== selectedFamily) {
          return false;
        }
      }
      if (filterMutantsOnly && !t.is_mutant) {
        return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchSym = t.symbol.toLowerCase().includes(q);
        const matchName = t.name.toLowerCase().includes(q);
        const matchPdb = t.pdb_code.toLowerCase().includes(q);
        const matchP = t.parent_symbol.toLowerCase().includes(q);
        const matchInd = t.indications.some((ind) => ind.toLowerCase().includes(q));
        const matchDrugs = t.approved_drugs.some((d) => d.toLowerCase().includes(q));
        return matchSym || matchName || matchPdb || matchP || matchInd || matchDrugs;
      }
      return true;
    });
  }, [targets, selectedFamily, filterMutantsOnly, searchQuery]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-cyan-500/30 rounded-2xl w-full max-w-6xl max-h-[90vh] flex flex-col shadow-2xl shadow-cyan-950/50 overflow-hidden text-slate-100">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 bg-slate-900/90 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center text-xl shadow-lg shadow-cyan-500/20">
              🏛️
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-400">
                  临床抗肿瘤激酶与耐药突变体知识库
                </h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-900/60 text-cyan-300 border border-cyan-500/30">
                  {targets.length} 核心靶标
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-900/50 text-amber-300 border border-amber-500/30">
                  16 临床耐药突变体
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                覆盖 EGFR, ABL1, BRAF, ALK, BTK, JAK, CDK, VEGFR 等全家族抗肿瘤靶点与高发门控/溶剂前沿耐药突变，直通 UniProt 与 ChEMBL
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Filter & Search Bar */}
        <div className="p-4 bg-slate-900/60 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
          {/* Family Tabs */}
          <div className="flex items-center space-x-1.5 overflow-x-auto text-xs py-1">
            {[
              { id: 'ALL', label: '全部靶点' },
              { id: 'MUTANT', label: '🔥 核心耐药突变体' },
              { id: 'TK', label: 'TK 酪氨酸激酶' },
              { id: 'TKL', label: 'TKL 家族 (BRAF等)' },
              { id: 'CMGC', label: 'CMGC 家族 (CDK/MAPK)' },
              { id: 'AGC', label: 'AGC 家族 (AKT/ROCK)' },
              { id: 'STE', label: 'STE 家族 (MEK)' },
              { id: 'Other', label: '其它 (AURK/PLK/mTOR)' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedFamily(tab.id)}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all whitespace-nowrap ${
                  selectedFamily === tab.id
                    ? 'bg-cyan-500 text-slate-950 font-semibold shadow-sm'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search box */}
          <div className="relative min-w-[260px] flex-1 max-w-sm">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400 text-xs">
              🔍
            </span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索基因符号/适应症/上市药物 (如: T790M, 肺癌, 奥希替尼)..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-950/80 border border-slate-700 focus:border-cyan-500 rounded-lg text-xs text-slate-200 placeholder-slate-500 outline-none transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 flex items-center pr-2.5 text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Content Body: Target Grid */}
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400 space-y-3">
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-xs tracking-wider">正在加载全球临床激酶与耐药突变体知识库...</p>
            </div>
          ) : filteredTargets.length === 0 ? (
            <div className="text-center py-20 text-slate-400 space-y-2">
              <p className="text-sm">未找到符合条件的激酶靶点或突变体</p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedFamily('ALL');
                }}
                className="text-xs text-cyan-400 underline hover:text-cyan-300"
              >
                重置检索条件
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {filteredTargets.map((item) => {
                const isCurrent =
                  currentTargetSymbol &&
                  (currentTargetSymbol.toUpperCase() === item.symbol.toUpperCase() ||
                    currentTargetSymbol.toUpperCase() === item.parent_symbol.toUpperCase());

                return (
                  <div
                    key={item.symbol}
                    className={`relative rounded-xl border p-4 transition-all flex flex-col justify-between hover:shadow-lg ${
                      item.is_mutant
                        ? 'border-amber-500/40 bg-gradient-to-b from-amber-950/20 to-slate-900/80 hover:border-amber-400/70 shadow-amber-950/20'
                        : 'border-slate-800 bg-slate-900/70 hover:border-cyan-500/50 shadow-slate-950/30'
                    } ${isCurrent ? 'ring-2 ring-cyan-400' : ''}`}
                  >
                    <div>
                      {/* Top Badges */}
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex items-center space-x-1.5 flex-wrap">
                          <span
                            className={`text-sm font-bold tracking-wide px-2 py-0.5 rounded-md ${
                              item.is_mutant
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                            }`}
                          >
                            {item.symbol}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                            {item.family} 激酶
                          </span>
                        </div>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                            item.clinical_phase_highest === 'Approved'
                              ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-500/30'
                              : 'bg-indigo-900/60 text-indigo-300 border border-indigo-500/30'
                          }`}
                        >
                          {item.clinical_phase_highest === 'Approved' ? 'FDA/NMPA 批准' : item.clinical_phase_highest}
                        </span>
                      </div>

                      {/* Full Name */}
                      <h4 className="text-xs font-semibold text-slate-200 line-clamp-1 mb-1" title={item.name}>
                        {item.name}
                      </h4>

                      {/* Resistance Alert if Mutant */}
                      {item.is_mutant && item.mutation_description && (
                        <div className="my-2 p-2 rounded-lg bg-amber-950/40 border border-amber-500/30 text-[11px] text-amber-200/90 leading-relaxed">
                          <div className="font-semibold text-amber-300 flex items-center space-x-1 mb-0.5">
                            <span>⚡ {item.mutation_type || '耐药突变'}机理：</span>
                          </div>
                          <p className="line-clamp-2" title={item.mutation_description}>
                            {item.mutation_description}
                          </p>
                        </div>
                      )}

                      {/* Biophysics / Residues info */}
                      <div className="grid grid-cols-2 gap-1.5 my-2 text-[10px] text-slate-400 bg-slate-950/50 p-2 rounded-lg border border-slate-800/80">
                        <div>
                          <span className="text-slate-500">共晶PDB：</span>
                          <span className="text-cyan-300 font-mono font-medium ml-1">
                            {item.pdb_code} ({item.resolution})
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">结合模式：</span>
                          <span className="text-slate-200 font-medium ml-1">
                            {item.binding_mode_typical === 'type_ii'
                              ? 'Type II (变构深腔)'
                              : item.binding_mode_typical === 'covalent'
                              ? 'Covalent (共价)'
                              : item.binding_mode_typical === 'allosteric'
                              ? 'Allosteric (变构)'
                              : 'Type I (活性开门)'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">铰链区：</span>
                          <span className="text-slate-300 font-mono ml-1">{item.hinge_residue}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">守门人：</span>
                          <span className={`font-mono ml-1 ${item.is_mutant ? 'text-amber-400 font-bold' : 'text-slate-300'}`}>
                            {item.gatekeeper_residue}
                          </span>
                        </div>
                      </div>

                      {/* Drugs & Indications */}
                      <div className="space-y-1 mb-3 text-[11px]">
                        <div className="flex items-start space-x-1">
                          <span className="text-slate-500 shrink-0">标杆药物:</span>
                          <span className="text-slate-300 line-clamp-1" title={item.approved_drugs.join(', ')}>
                            {item.approved_drugs.join('、')}
                          </span>
                        </div>
                        <div className="flex items-start space-x-1">
                          <span className="text-slate-500 shrink-0">适应症:</span>
                          <span className="text-slate-400 line-clamp-1" title={item.indications.join(', ')}>
                            {item.indications.join(' · ')}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Bottom Action buttons */}
                    <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2">
                      <div className="flex items-center space-x-2 text-[10px] text-cyan-400/80">
                        <a
                          href={`https://www.uniprot.org/uniprotkb/${item.uniprot_id}/entry`}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:underline flex items-center space-x-0.5"
                          title="在 UniProt 中查看全长蛋白"
                        >
                          <span>UniProt: {item.uniprot_id}</span>
                          <span className="text-[8px]">↗</span>
                        </a>
                        {item.chembl_id && (
                          <a
                            href={`https://www.ebi.ac.uk/chembl/target_report_card/${item.chembl_id}/`}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:underline flex items-center space-x-0.5 text-indigo-400/80"
                            title="在 ChEMBL 中查看生化活性分布"
                          >
                            <span>ChEMBL ↗</span>
                          </a>
                        )}
                      </div>

                      <button
                        onClick={() => {
                          onSelectTarget(item);
                          onClose();
                        }}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-sm transition-all flex items-center space-x-1"
                      >
                        <span>载入靶点</span>
                        <span>➔</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-950/80 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between px-6">
          <span>
            共筛选出 <strong className="text-cyan-400">{filteredTargets.length}</strong> 个靶标条目
          </span>
          <span className="text-[11px] text-slate-500">
            SafeAMP-Dual 5.0 临床肿瘤药物基因组数据库 · UniProtKB / Swiss-Prot / ChEMBL 深度映射
          </span>
        </div>
      </div>
    </div>
  );
};
