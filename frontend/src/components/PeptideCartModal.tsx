import React, { useState } from 'react';
import { ShoppingCart, X, Trash2, Download, Activity, FlaskConical, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAppStore, type CartPeptide } from '../store/useAppStore';
import { exportSmallMoleculesCSV, computeDrugLikeness } from '../utils/cheminformatics';
import { Molecule2DViewer } from './Molecule2DViewer';
import { cartScore } from '../utils/cartMetrics';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const PeptideCartModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const { cart, removeFromCart, clearCart, setActiveSmallMolecule, setActivePeptide } = useAppStore();
  const navigate = useNavigate();
  const [typeWarning, setTypeWarning] = useState<string | null>(null);

  if (!isOpen) return null;

  const smallMolecules = cart.filter(c => c.kind === 'small_molecule' || c.item_type === 'small_molecule');
  const peptides = cart.filter(c => c.kind === 'peptide' || (c.kind !== 'small_molecule' && c.item_type !== 'small_molecule'));

  const handleExportCSV = () => {
    if (cart.length === 0) return;

    if (smallMolecules.length > 0 && peptides.length === 0 && smallMolecules.every(c => cartScore(c) !== null)) {
      exportSmallMoleculesCSV(
        smallMolecules.map(c => ({
          name: c.name,
          smiles: c.smiles || c.sequence,
          pkd: cartScore(c)!,
          addedAt: c.addedAt,
        }))
      );
      return;
    }

    const header = 'Type,Name,Sequence_or_SMILES,Score_or_pKd,P_AMP,P_Hemo,AddedAt\n';
    const rows = cart.map(c => {
      const typeStr = (c.kind === 'small_molecule' || c.item_type === 'small_molecule') ? 'SmallMolecule' : 'Peptide';
      const seqStr = c.smiles || c.sequence;
      return `"${typeStr}","${c.name}","${seqStr}",${cartScore(c)?.toFixed(3) ?? ''},${c.p_amp ?? ''},${c.p_hemo ?? ''},"${c.addedAt}"`;
    }).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `DTI_Candidate_Library_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleSendToDTI = (item: CartPeptide) => {
    const isSmallMol = item.kind === 'small_molecule' || item.item_type === 'small_molecule';
    if (!isSmallMol) {
      setTypeWarning('多肽氨基酸序列与小分子激酶 DTI DAVIS 特征不兼容，不能作为小分子亲和力模型输入。');
      return;
    }
    const smiles = item.smiles || item.sequence;
    setActiveSmallMolecule(smiles, item.name, 'Candidate Cart');
    onClose();
    navigate('/dti', {
      state: {
        drugSmiles: smiles,
        drugName: item.name
      }
    });
  };

  const handleSendToEvolution = (item: CartPeptide) => {
    const isSmallMol = item.kind === 'small_molecule' || item.item_type === 'small_molecule';
    const cleanSeq = item.smiles || item.sequence;
    if (isSmallMol) {
      setActiveSmallMolecule(cleanSeq, item.name, 'Candidate Cart');
    } else {
      setActivePeptide(cleanSeq, item.name, 'Candidate Cart');
    }
    onClose();
    navigate('/evolution', {
      state: {
        drugSmiles: cleanSeq,
        drugName: item.name
      }
    });
  };

  const handleSendToWheel = (item: CartPeptide) => {
    const isSmallMol = item.kind === 'small_molecule' || item.item_type === 'small_molecule';
    if (isSmallMol) {
      setTypeWarning('小分子化学结构（SMILES）不支持二维螺旋轮图谱投影，仅多肽氨基酸序列可用。');
      return;
    }
    setActivePeptide(item.sequence, item.name, 'Candidate Cart');
    onClose();
    navigate('/helical-wheel');
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
          <div className="flex items-center gap-2.5 text-slate-800 dark:text-slate-100 font-semibold text-base">
            <ShoppingCart size={20} className="text-blue-600 dark:text-blue-400" />
            <span>候选分子暂存库 (Candidate Molecule Library)</span>
            <span className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300 px-2 py-0.5 rounded-full font-mono">
              {cart.length} 条记录
            </span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-md cursor-pointer">
            <X size={18} />
          </button>
        </div>

        {/* Warning Alert */}
        {typeWarning && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/70 text-amber-800 dark:text-amber-200 text-xs flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AlertTriangle size={15} className="shrink-0 text-amber-600" />
              <span>{typeWarning}</span>
            </div>
            <button onClick={() => setTypeWarning(null)} className="text-amber-600 hover:text-amber-800 dark:hover:text-amber-100 text-xs font-bold cursor-pointer">
              关闭
            </button>
          </div>
        )}

        {/* List Content */}
        <div className="p-6 overflow-y-auto flex-1 divide-y divide-slate-100 dark:divide-slate-800">
          {cart.length === 0 ? (
            <div className="py-12 text-center text-slate-400 dark:text-slate-600 flex flex-col items-center justify-center gap-3">
              <ShoppingCart size={40} className="stroke-[1.5]" />
              <p className="text-sm">暂存库为空。在筛选台或先导优化工作室中点击“存入候选库”即可暂存分子。</p>
            </div>
          ) : (
            cart.map(item => {
              const isSmallMol = item.kind === 'small_molecule' || item.item_type === 'small_molecule';
              const seqStr = item.smiles || item.sequence;
              const dl = isSmallMol ? computeDrugLikeness(seqStr) : null;

              return (
                <div key={item.id} className="py-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 group">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">{item.name}</span>
                      {isSmallMol ? (
                        <span className="text-[10px] text-sky-600 dark:text-sky-400 font-mono font-medium">(小分子 · {seqStr.length} 字符)</span>
                      ) : (
                        <span className="text-[10px] text-indigo-600 dark:text-indigo-400 font-mono font-medium">({seqStr.length} AA 多肽)</span>
                      )}
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-medium ${
                        isSmallMol
                          ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                          : (item.tsi || 0) >= 0.5 
                          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800' 
                          : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                      }`}>
                        {isSmallMol ? `预测 pKd: ${cartScore(item)?.toFixed(3) ?? '未计算'}` : (item.run_id ? '排序分数: ' + (cartScore(item)?.toFixed(3) ?? '未计算') : '多肽记录')}
                      </span>
                    </div>

                    <div className="font-mono text-xs text-slate-600 dark:text-slate-300 break-all select-all">
                      {seqStr}
                    </div>

                    {isSmallMol && dl ? (
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500 font-mono mt-1">
                        <span>MW: {dl.mw}</span>
                        <span>LogP: {dl.logp}</span>
                        <span>TPSA: {dl.tpsa} Å²</span>
                        <span className="text-emerald-600 dark:text-emerald-400">{dl.druglikeness_tier}</span>
                        <span>添加时间: {item.addedAt}</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono mt-1">
                        <span>Score: {item.tsi ? item.tsi.toFixed(3) : '未计算'}</span>
                        <span>添加时间: {item.addedAt}</span>
                      </div>
                    )}
                  </div>

                  {isSmallMol && (
                    <div className="shrink-0 self-center">
                      <Molecule2DViewer smiles={seqStr} name={item.name} width={76} height={48} showExpandButton={true} />
                    </div>
                  )}

                  <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
                    {isSmallMol ? (
                      <button 
                        onClick={() => handleSendToDTI(item)} 
                        title="送入 DTI 靶点亲和力预测工作台"
                        className="p-1.5 text-xs text-sky-600 dark:text-sky-400 hover:bg-sky-50 dark:hover:bg-sky-950/50 rounded border border-sky-200 dark:border-sky-800 flex items-center gap-1 cursor-pointer"
                      >
                        <FlaskConical size={13} /> DTI
                      </button>
                    ) : (
                      <button 
                        onClick={() => handleSendToWheel(item)} 
                        title="送入螺旋轮构象透视"
                        className="p-1.5 text-xs text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 rounded border border-indigo-200 dark:border-indigo-800 flex items-center gap-1 cursor-pointer"
                      >
                        螺旋轮
                      </button>
                    )}

                    <button 
                      onClick={() => handleSendToEvolution(item)} 
                      title="送入先导分子优化工作台"
                      className="p-1.5 text-xs text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/50 rounded border border-purple-200 dark:border-purple-800 flex items-center gap-1 cursor-pointer"
                    >
                      <Activity size={13} /> 优化
                    </button>

                    <button 
                      onClick={() => removeFromCart(item.id)} 
                      title="从暂存库移除"
                      className="p-1.5 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 rounded transition-colors cursor-pointer"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
          <button 
            type="button"
            onClick={clearCart}
            disabled={cart.length === 0}
            className="text-xs text-rose-600 dark:text-rose-400 hover:underline disabled:opacity-40 cursor-pointer"
          >
            清空库
          </button>
          <div className="flex items-center gap-3">
            <button 
              type="button"
              onClick={handleExportCSV}
              disabled={cart.length === 0}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg shadow-2xs transition-colors disabled:opacity-40 cursor-pointer"
            >
              <Download size={13} /> 导出为 CSV
            </button>
            <button 
              type="button"
              onClick={onClose} 
              className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors cursor-pointer"
            >
              完成
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
