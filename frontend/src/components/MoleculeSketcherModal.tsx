import React, { useState, useEffect, useMemo } from 'react';
import { 
  X, 
  Check, 
  RotateCcw, 
  Copy, 
  Trash2, 
  Sparkles, 
  FlaskConical, 
  Layers, 
  Plus, 
  Info,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { Molecule2DViewer } from './Molecule2DViewer';
import { computeDrugLikeness, computeQuickSAScore } from '../utils/cheminformatics';

interface MoleculeSketcherModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (smiles: string) => void;
  initialSmiles?: string;
  title?: string;
}

interface ScaffoldPreset {
  name: string;
  category: string;
  smiles: string;
  desc: string;
}

const COMMON_SCAFFOLDS: ScaffoldPreset[] = [
  { name: '苯环 (Benzene)', category: '芳香环', smiles: 'c1ccccc1', desc: '经典单环芳香母核' },
  { name: '吡啶环 (Pyridine)', category: '杂环', smiles: 'c1ccncc1', desc: '六元含氮亲水杂环' },
  { name: '嘧啶环 (Pyrimidine)', category: '杂环', smiles: 'c1ncncc1', desc: '二氮六元激酶铰链受体' },
  { name: '噻唑环 (Thiazole)', category: '杂环', smiles: 'c1cscn1', desc: '五元硫氮杂环 (达沙替尼骨架)' },
  { name: '环己烷 (Cyclohexane)', category: '脂肪环', smiles: 'C1CCCCC1', desc: '脂环烃饱和母核' },
  { name: '哌嗪环 (Piperazine)', category: '脂肪杂环', smiles: 'C1CNCCN1', desc: '常用增溶与碱性药效尾' },
  { name: '嘌呤骨架 (Purine)', category: '双环', smiles: 'c1nc2[nH]cnc2n1', desc: '经典 ATP 腺嘌呤类似物' },
  { name: '喹唑啉母核 (Quinazoline)', category: '双环', smiles: 'c1ccc2c(c1)ncnc2', desc: 'EGFR 抑制剂经典核心 (吉非替尼母核)' },
  { name: '芳基脲母核 (Aryl Urea)', category: '变构基序', smiles: 'c1ccccc1NC(=O)Nc2ccccc2', desc: 'Type-II DFG-out 变构氢键供体网络' }
];

const FUNCTIONAL_GROUPS = [
  { label: '-F (氟代)', formula: '(F)', desc: '阻断代谢热点并增强脂溶性' },
  { label: '-Cl (氯代)', formula: '(Cl)', desc: '填充微观疏水口袋' },
  { label: '-CF3 (三氟甲基)', formula: '(C(F)(F)F)', desc: '极高疏水性变构深腔填充' },
  { label: '-OH (羟基)', formula: '(O)', desc: '增加氢键供体与水溶性' },
  { label: '-OMe (甲氧基)', formula: '(OC)', desc: '经典电子供体基团' },
  { label: '-Me (甲基)', formula: '(C)', desc: '提升亲和力“神奇甲基效应”' },
  { label: '-NH2 (氨基)', formula: '(N)', desc: '主链铰链区氢键供体' },
  { label: '-CN (氰基)', formula: '(C#N)', desc: '极性较强的拟卤素氢键受体' },
  { label: '-COOH (羧基)', formula: '(C(=O)O)', desc: '极性离子化头部' },
  { label: '-CONH2 (酰胺)', formula: '(C(=O)N)', desc: '刚性氢键网络骨架' }
];

const DRUG_TEMPLATES = [
  { name: '达沙替尼 (Dasatinib)', smiles: 'Cc1cccc(Cl)c1NC(=O)c2cnc(s2)Nc3cc(nc(n3)N4CCNCC4)C' },
  { name: '吉非替尼 (Gefitinib)', smiles: 'COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN4CCOCC4' },
  { name: '索拉非尼 (Sorafenib)', smiles: 'CNC(=O)c1cc(ccn1)Oc2ccc(NC(=O)Nc3ccc(Cl)c(c3)C(F)(F)F)cc2' },
  { name: '伊马替尼 (Imatinib)', smiles: 'Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc4nccc(n4)c5cccnc5' }
];

export const MoleculeSketcherModal: React.FC<MoleculeSketcherModalProps> = ({
  isOpen,
  onClose,
  onApply,
  initialSmiles = '',
  title = '分子结构交互手绘画板 (Molecule Sketcher)'
}) => {
  const [smiles, setSmiles] = useState(initialSmiles);
  const [history, setHistory] = useState<string[]>([initialSmiles]);
  const [historyIdx, setHistoryIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const init = initialSmiles || 'c1ccccc1';
      setSmiles(init);
      setHistory([init]);
      setHistoryIdx(0);
    }
  }, [isOpen, initialSmiles]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const updateSmiles = (newSmiles: string) => {
    const trimmed = newSmiles.trim();
    setSmiles(trimmed);
    const newHistory = history.slice(0, historyIdx + 1);
    newHistory.push(trimmed);
    setHistory(newHistory);
    setHistoryIdx(newHistory.length - 1);
  };

  const handleUndo = () => {
    if (historyIdx > 0) {
      const prev = history[historyIdx - 1];
      setHistoryIdx(historyIdx - 1);
      setSmiles(prev);
    }
  };

  const handleClear = () => {
    updateSmiles('');
  };

  const handleCopy = () => {
    if (!smiles) return;
    navigator.clipboard.writeText(smiles);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // Add scaffold to current molecule
  const handleAddScaffold = (scaffoldSmiles: string, mode: 'replace' | 'append') => {
    if (mode === 'replace' || !smiles) {
      updateSmiles(scaffoldSmiles);
    } else {
      updateSmiles(`${smiles}.${scaffoldSmiles}`);
    }
  };

  // Add functional group to current molecule
  const handleAddFunctionalGroup = (groupFormula: string) => {
    if (!smiles) {
      updateSmiles(groupFormula.replace(/[()]/g, ''));
    } else {
      // Append functional group bracketed or substituted
      updateSmiles(`${smiles}${groupFormula}`);
    }
  };

  // Real-time cheminformatics evaluation
  const properties = useMemo(() => {
    return computeDrugLikeness(smiles);
  }, [smiles]);

  const saScoreMeta = useMemo(() => {
    return computeQuickSAScore(smiles);
  }, [smiles]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div 
        className="w-full max-w-5xl max-h-[92vh] flex flex-col bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden text-slate-200"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-950/90 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <FlaskConical className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white tracking-wide flex items-center gap-2">
                {title}
                <span className="text-[11px] font-normal px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  双向实时同步画板
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                支持快速骨架模板拼接、官能团增删、实时 2D 拓扑预览与成药性/合成可达性 (SA Score) 即时估算
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Main workspace grid: Left Toolbar & Center Canvas & Right ADMET stats */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Core Scaffolds & Substituent Brushes (4 cols) */}
            <div className="lg:col-span-4 space-y-4">
              {/* Core Scaffolds */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    母核骨架模板库 (Scaffolds)
                  </span>
                  <span className="text-[10px] text-slate-500">点击置换或拼接</span>
                </div>
                <div className="grid grid-cols-2 gap-2 max-h-[190px] overflow-y-auto pr-1">
                  {COMMON_SCAFFOLDS.map(sc => (
                    <button
                      key={sc.name}
                      onClick={() => handleAddScaffold(sc.smiles, 'replace')}
                      className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 text-left transition-all group"
                      title={sc.desc}
                    >
                      <div className="text-[11px] font-medium text-slate-200 group-hover:text-cyan-300 truncate">
                        {sc.name.split(' ')[0]}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono truncate">
                        {sc.smiles}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Functional Group Brushes */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    修饰基团笔刷 (Substituents)
                  </span>
                  <span className="text-[10px] text-slate-500">追加修饰位点</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {FUNCTIONAL_GROUPS.map(fg => (
                    <button
                      key={fg.label}
                      onClick={() => handleAddFunctionalGroup(fg.formula)}
                      className="px-2 py-1.5 rounded-lg bg-slate-800/60 hover:bg-cyan-500/10 hover:border-cyan-500/30 border border-slate-700/50 text-left transition-all"
                      title={fg.desc}
                    >
                      <div className="text-[11px] font-medium text-slate-300">
                        {fg.label}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Classic Kinase Inhibitors Presets */}
              <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/60 space-y-2">
                <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
                  <FlaskConical className="w-3 h-3 text-emerald-400" />
                  临床经典激酶抑制剂模板
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {DRUG_TEMPLATES.map(dt => (
                    <button
                      key={dt.name}
                      onClick={() => updateSmiles(dt.smiles)}
                      className="text-[10px] px-2 py-1 rounded bg-slate-800/90 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition-colors"
                    >
                      {dt.name.split(' ')[0]}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Middle Column: 2D Chemical Canvas & Actions (5 cols) */}
            <div className="lg:col-span-5 flex flex-col space-y-4">
              {/* Canvas Preview Container */}
              <div className="relative flex-1 min-h-[300px] p-4 rounded-xl bg-slate-950/90 border border-slate-800 flex flex-col items-center justify-center overflow-hidden">
                {smiles ? (
                  <Molecule2DViewer
                    smiles={smiles}
                    name="画板分子拓扑"
                    width={340}
                    height={220}
                    showExpandButton={false}
                  />
                ) : (
                  <div className="text-center p-8 space-y-2 text-slate-500">
                    <FlaskConical className="w-10 h-10 mx-auto opacity-30 text-cyan-400" />
                    <p className="text-xs">画板为空，请从左侧选择骨架母核或在下方输入 SMILES</p>
                  </div>
                )}

                {/* Canvas Floating Quick Toolbar */}
                <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-slate-900/90 border border-slate-700/80 rounded-lg p-1">
                  <button
                    onClick={handleUndo}
                    disabled={historyIdx <= 0}
                    className="p-1 rounded text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:hover:text-slate-400 transition-colors"
                    title="撤销上一步"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={handleCopy}
                    className="p-1 rounded text-slate-400 hover:text-slate-200 transition-colors"
                    title="复制当前 SMILES"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    onClick={handleClear}
                    className="p-1 rounded text-rose-400 hover:text-rose-300 transition-colors"
                    title="清空画板"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Editable SMILES Input Bar */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-medium text-slate-300">SMILES 字符双向输入框:</span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    字符长度: {smiles.length}
                  </span>
                </div>
                <div className="relative">
                  <input
                    type="text"
                    value={smiles}
                    onChange={e => updateSmiles(e.target.value)}
                    placeholder="输入或粘贴规范 SMILES (如: c1ccccc1 或 Cc1cccc(Cl)c1NC(=O)...)"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-xl text-xs font-mono text-cyan-300 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50"
                  />
                </div>
              </div>
            </div>

            {/* Right Column: Real-time Property & SA Score Preview (3 cols) */}
            <div className="lg:col-span-3 space-y-4">
              {/* Synthetic Accessibility (SA Score) Highlight Card */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                    合成可达性 (SA Score)
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                    saScoreMeta.sa_color === 'emerald'
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                      : saScoreMeta.sa_color === 'cyan'
                      ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                      : saScoreMeta.sa_color === 'amber'
                      ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                      : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                  }`}>
                    {saScoreMeta.sa_score.toFixed(2)} / 10
                  </span>
                </div>

                <div className="space-y-1.5">
                  <div className="text-xs font-medium text-slate-200">
                    {saScoreMeta.sa_label}
                  </div>
                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-300 ${
                        saScoreMeta.sa_color === 'emerald'
                          ? 'bg-emerald-400'
                          : saScoreMeta.sa_color === 'cyan'
                          ? 'bg-cyan-400'
                          : saScoreMeta.sa_color === 'amber'
                          ? 'bg-amber-400'
                          : 'bg-rose-400'
                      }`}
                      style={{ width: `${Math.min(100, (saScoreMeta.sa_score / 10) * 100)}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-slate-400 leading-relaxed">
                    评分越低越容易合成 (1~3.5 商业原料可达，&gt;7 需多步全合成路线)。
                  </p>
                </div>
              </div>

              {/* Physicochemical Drug-likeness (Ro5) Card */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-cyan-400" />
                  类药性理化参数 (Ro5)
                </span>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                    <div className="text-slate-400">分子量 (MW)</div>
                    <div className="font-semibold text-white mt-0.5">{properties.mw}</div>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                    <div className="text-slate-400">脂水分配 LogP</div>
                    <div className="font-semibold text-white mt-0.5">{properties.logp}</div>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                    <div className="text-slate-400">供体/受体</div>
                    <div className="font-semibold text-white mt-0.5">{properties.hbd} / {properties.hba}</div>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                    <div className="text-slate-400">极性表面 TPSA</div>
                    <div className="font-semibold text-white mt-0.5">{properties.tpsa} Å²</div>
                  </div>
                </div>

                <div className="pt-1">
                  <span className={`text-[10px] px-2 py-1 rounded block text-center border font-medium ${
                    properties.badge_color === 'emerald' 
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                      : properties.badge_color === 'amber'
                      ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                      : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                  }`}>
                    {properties.druglikeness_tier}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-950/90 border-t border-slate-800">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>分子就绪后点击右侧按钮，结构将实时同步回填至当前分析输入框</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
            >
              取消
            </button>
            <button
              onClick={() => {
                if (smiles) {
                  onApply(smiles);
                  onClose();
                }
              }}
              disabled={!smiles}
              className="px-5 py-2 rounded-xl bg-linear-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-semibold shadow-lg shadow-cyan-500/20 disabled:opacity-40 disabled:pointer-events-none transition-all flex items-center gap-1.5"
            >
              <Check className="w-4 h-4" />
              应用并填入分析面板
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
