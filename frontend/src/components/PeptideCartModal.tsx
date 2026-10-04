import React from 'react';
import { ShoppingCart, X, Trash2, Download, Activity, Zap, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const PeptideCartModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const { cart, removeFromCart, clearCart, setActivePeptide } = useAppStore();
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleExportCSV = () => {
    if (cart.length === 0) return;
    const header = 'Sequence,Name,P_AMP,P_Hemo,ComputationalRankingScore,AddedAt\n';
    const rows = cart.map(c => `"${c.sequence}","${c.name}",${c.p_amp},${c.p_hemo},${c.tsi},"${c.addedAt}"`).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `SafeAMP_Candidate_Library_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleSendToEvolution = (seq: string, name: string) => {
    setActivePeptide(seq, name);
    onClose();
    navigate('/evolution');
  };

  const handleSendToWheel = (seq: string, name: string) => {
    setActivePeptide(seq, name);
    onClose();
    navigate('/wheel');
  };

  const handleSendToReport = (seq: string, name: string) => {
    setActivePeptide(seq, name);
    onClose();
    navigate('/report');
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
          <div className="flex items-center gap-2.5 text-slate-800 dark:text-slate-100 font-semibold text-base">
            <ShoppingCart size={20} className="text-blue-600 dark:text-blue-400" />
            <span>候选多肽暂存库 (Candidate Peptide Library)</span>
            <span className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-300 px-2 py-0.5 rounded-full font-mono">
              {cart.length} 序列
            </span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-md">
            <X size={18} />
          </button>
        </div>

        {/* List Content */}
        <div className="p-6 overflow-y-auto flex-1 divide-y divide-slate-100 dark:divide-slate-800">
          {cart.length === 0 ? (
            <div className="py-12 text-center text-slate-400 dark:text-slate-600 flex flex-col items-center justify-center gap-3">
              <ShoppingCart size={40} className="stroke-[1.5]" />
              <p className="text-sm">暂存库为空。在筛选台或突变实验室中点击“存入候选库”即可暂存分子。</p>
            </div>
          ) : (
            cart.map(item => (
              <div key={item.id} className="py-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 group">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">{item.name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">({item.sequence.length} AA)</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-medium ${
                      item.tsi >= 0.5 
                        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800' 
                        : 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 border border-rose-200 dark:border-rose-800'
                    }`}>
                      {item.run_id ? '排序分数: ' + item.tsi.toFixed(3) : '未关联验证运行，需重新预测'}
                    </span>
                  </div>
                  <div className="font-mono text-xs text-slate-600 dark:text-slate-300 break-all select-all">
                    {item.sequence}
                  </div>
                  <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono mt-1">
                    <span>P_AMP: {item.run_id ? item.p_amp.toFixed(3) : '未计算'}</span>
                    <span>P_Hemo: {item.run_id ? item.p_hemo.toFixed(3) : '未计算'}</span>
                    <span>添加时间: {item.addedAt}</span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
                  <button 
                    onClick={() => handleSendToEvolution(item.sequence, item.name)} 
                    title="送入突变实验室"
                    className="p-1.5 text-xs text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/50 rounded border border-purple-200 dark:border-purple-800 flex items-center gap-1"
                  >
                    <Activity size={13} /> 突变
                  </button>
                  <button 
                    onClick={() => handleSendToWheel(item.sequence, item.name)} 
                    title="绘制螺旋轮构象"
                    className="p-1.5 text-xs text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/50 rounded border border-amber-200 dark:border-amber-800 flex items-center gap-1"
                  >
                    <Zap size={13} /> 螺旋
                  </button>
                  <button 
                    onClick={() => handleSendToReport(item.sequence, item.name)} 
                    title="生成计算研究报告"
                    className="p-1.5 text-xs text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/50 rounded border border-blue-200 dark:border-blue-800 flex items-center gap-1"
                  >
                    <FileText size={13} /> 报告
                  </button>
                  <button 
                    onClick={() => removeFromCart(item.id)} 
                    title="删除"
                    className="p-1.5 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 rounded transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
          <button 
            type="button"
            onClick={clearCart}
            disabled={cart.length === 0}
            className="text-xs text-rose-600 dark:text-rose-400 hover:underline disabled:opacity-40"
          >
            清空库
          </button>
          <div className="flex items-center gap-3">
            <button 
              type="button"
              onClick={handleExportCSV}
              disabled={cart.length === 0}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg shadow-2xs transition-colors disabled:opacity-40"
            >
              <Download size={13} /> 导出为 CSV
            </button>
            <button 
              type="button"
              onClick={onClose} 
              className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
            >
              完成
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
