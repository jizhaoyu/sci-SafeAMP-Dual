import React, { useState } from 'react';
import { 
  X, 
  Grid, 
  Download, 
  Copy, 
  Check, 
  FlaskConical, 
  Layers, 
  Info,
  CheckCircle2,
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import type { WetlabDispatchResult, WetlabDispatchWell } from '../api/dtiClient';

interface WetlabDispatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  dispatchResult: WetlabDispatchResult | null;
  loading?: boolean;
}

const ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
const COLS = Array.from({ length: 12 }, (_, i) => i + 1);

export const WetlabDispatchModal: React.FC<WetlabDispatchModalProps> = ({
  isOpen,
  onClose,
  dispatchResult,
  loading = false
}) => {
  if (!isOpen) return null;

  const [selectedWell, setSelectedWell] = useState<WetlabDispatchWell | null>(null);
  const [copiedCsv, setCopiedCsv] = useState(false);

  // Map wells by well_id for O(1) lookup
  const wellMap = React.useMemo(() => {
    const map = new Map<string, WetlabDispatchWell>();
    if (dispatchResult?.wells) {
      for (const w of dispatchResult.wells) {
        map.set(w.well_id, w);
      }
    }
    return map;
  }, [dispatchResult]);

  const handleDownloadCSV = () => {
    if (!dispatchResult) return;
    const blob = new Blob([dispatchResult.csv_content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${dispatchResult.plate_barcode}_Wetlab_Manifest.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCopyCSV = () => {
    if (!dispatchResult) return;
    navigator.clipboard.writeText(dispatchResult.csv_content);
    setCopiedCsv(true);
    setTimeout(() => setCopiedCsv(false), 2000);
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-5xl max-h-[92vh] flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-md shadow-emerald-500/20">
              <Grid className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  湿实验 96 孔板投产清单与移液规程
                </h3>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-mono">
                  {dispatchResult?.plate_barcode || 'PLATE-001'}
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                靶点: <span className="font-semibold text-slate-700 dark:text-slate-300">{dispatchResult?.target_name}</span> · 包含自动液体处理机 (Echo/Tecan) 适配输出
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyCSV}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              {copiedCsv ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedCsv ? '已复制 CSV' : '复制清单'}</span>
            </button>
            <button
              onClick={handleDownloadCSV}
              className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>下载孔板 CSV</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-24 flex flex-col items-center justify-center gap-4">
              <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                正在生成 96 孔板点位映射与稀释滴定清单...
              </p>
            </div>
          ) : !dispatchResult ? (
            <div className="py-20 text-center text-slate-500">
              暂无投产清单数据，请先在优化界面运行改构评估。
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              
              {/* Left Column: 96-Well Microplate Grid */}
              <div className="lg:col-span-8 bg-slate-50 dark:bg-slate-950/60 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
                
                {/* Summary badges */}
                <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-200/80 dark:border-slate-800 text-xs">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-slate-600 dark:text-slate-300">
                      总孔位: <strong className="text-slate-900 dark:text-white font-mono">{dispatchResult.total_wells}</strong> / 96
                    </span>
                    <span className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400 font-medium">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                      Tier 1 优先: {dispatchResult.tier1_count}
                    </span>
                    <span className="flex items-center gap-1.5 text-blue-700 dark:text-blue-400 font-medium">
                      <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                      Tier 2 拓展: {dispatchResult.tier2_count}
                    </span>
                    <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400 font-medium">
                      <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
                      对照孔: 2
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    均值 SA: {dispatchResult.average_sa_score} · 健康度: {dispatchResult.average_admet_health}分
                  </span>
                </div>

                {/* 96-Well Plate Layout */}
                <div className="overflow-x-auto pb-2">
                  <div className="inline-block min-w-[580px] w-full">
                    {/* Column numbers */}
                    <div 
                      style={{ display: 'grid', gridTemplateColumns: '28px repeat(12, minmax(0, 1fr))', gap: '6px' }} 
                      className="text-center text-[10px] font-mono font-bold text-slate-400 mb-1.5"
                    >
                      <div /> {/* Row letter space */}
                      {COLS.map(c => (
                        <div key={c} className="text-center">{String(c).padStart(2, '0')}</div>
                      ))}
                    </div>

                    {/* Rows */}
                    {ROWS.map((r) => (
                      <div 
                        key={r} 
                        style={{ display: 'grid', gridTemplateColumns: '28px repeat(12, minmax(0, 1fr))', gap: '6px' }} 
                        className="items-center mb-1.5"
                      >
                        <div className="text-center text-xs font-mono font-bold text-slate-500">{r}</div>
                        {COLS.map((c) => {
                          const wellId = `${r}${String(c).padStart(2, '0')}`;
                          const well = wellMap.get(wellId);
                          const isSelected = selectedWell?.well_id === wellId;

                          let bgClass = 'bg-slate-200/50 dark:bg-slate-800/40 text-slate-400 border-slate-200 dark:border-slate-800';
                          if (well) {
                            if (well.compound_type === 'positive_control') {
                              bgClass = 'bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-700 hover:scale-105';
                            } else if (well.compound_type === 'negative_control') {
                              bgClass = 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:scale-105';
                            } else if (well.priority_tier.includes('Tier 1')) {
                              bgClass = 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border-emerald-400 dark:border-emerald-600 hover:scale-105 shadow-2xs';
                            } else if (well.priority_tier.includes('Tier 2')) {
                              bgClass = 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200 border-blue-400 dark:border-blue-600 hover:scale-105';
                            } else {
                              bgClass = 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-200 border-amber-400 dark:border-amber-600 hover:scale-105';
                            }
                          }

                          return (
                            <button
                              key={wellId}
                              type="button"
                              onClick={() => well && setSelectedWell(well)}
                              title={well ? `${well.well_id}: ${well.compound_name} (${well.priority_tier})` : `${wellId} (空孔)`}
                              className={`w-8 h-8 rounded-full border text-[10px] font-mono font-bold flex items-center justify-center transition-all cursor-pointer ${bgClass} ${
                                isSelected ? 'ring-2 ring-emerald-500 scale-110 shadow-md z-10' : ''
                              }`}
                            >
                              {well ? (well.compound_type === 'positive_control' ? 'P' : well.compound_type === 'negative_control' ? 'N' : well.col) : ''}
                            </button>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-200/80 dark:border-slate-800">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                      P: 阳性对照 (Well A01)
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2.5 h-2.5 rounded-full bg-slate-500" />
                      N: 阴性 DMSO (Well H12)
                    </span>
                  </div>
                  <span>💡 点击任一孔位查看其化合物属性与移液参数</span>
                </div>
              </div>

              {/* Right Column: Selected Well Inspector & Protocol Guidelines */}
              <div className="lg:col-span-4 space-y-4">
                {selectedWell ? (
                  <div className="bg-slate-50 dark:bg-slate-950/60 p-4 rounded-xl border border-slate-200 dark:border-slate-800 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-200/80 dark:border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-md bg-emerald-600 text-white font-mono font-bold text-xs">
                          {selectedWell.well_id}
                        </span>
                        <span className="font-bold text-xs text-slate-900 dark:text-white truncate max-w-[140px]">
                          {selectedWell.compound_name}
                        </span>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        selectedWell.priority_tier.includes('Tier 1') ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' :
                        selectedWell.priority_tier.includes('Tier 2') ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300' :
                        'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                      }`}>
                        {selectedWell.priority_tier.split(' ')[0]}
                      </span>
                    </div>

                    <div className="space-y-1.5 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-400">预测亲和力:</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                          pKd {selectedWell.predicted_pkd} (Kd: {selectedWell.predicted_kd_nM} nM)
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">合成可行性 (SA):</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                          {selectedWell.sa_score} ({selectedWell.sa_tier})
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">成药健康分:</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                          {selectedWell.admet_health_score} 分
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">hERG 心脏安全:</span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {selectedWell.herg_risk === 'low' ? '低风险 (Safe)' : '中度预警'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">母液储备:</span>
                        <span className="font-mono text-slate-800 dark:text-slate-200">
                          {selectedWell.stock_concentration} in {selectedWell.stock_solvent} ({selectedWell.stock_volume_ul} µL)
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">最高工作浓度:</span>
                        <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                          {selectedWell.recommended_assay_top_uM} µM
                        </span>
                      </div>
                    </div>

                    <div className="p-2 bg-white dark:bg-slate-900 rounded-lg border border-slate-200/80 dark:border-slate-800 text-[10px] font-mono text-slate-500 break-all">
                      {selectedWell.smiles}
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-xs text-slate-400 bg-slate-50/50 dark:bg-slate-950/40 rounded-xl border border-dashed border-slate-200 dark:border-slate-800">
                    <FlaskConical className="w-8 h-8 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                    <span>在左侧点击任意孔位查看移液浓度与理化属性</span>
                  </div>
                )}

                {/* Automation & Liquid Handler Protocol */}
                <div className="p-4 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/60 text-xs space-y-2">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-900 dark:text-emerald-300">
                    <Info className="w-4 h-4 text-emerald-600" />
                    自动化工作站执行指引
                  </div>
                  <ul className="text-[11px] text-slate-600 dark:text-slate-300 space-y-1 list-disc list-inside">
                    <li><strong>格式标准:</strong> 导出的 CSV 文件直接兼容 Beckman Echo 声波移液系统与 Tecan Freedom EVO 自动加样器。</li>
                    <li><strong>梯度滴定:</strong> 推荐从 Well 启动 3 倍 8 点稀释，体系中终浓度 DMSO &le; 0.1%，规避非特异性激酶失活。</li>
                  </ul>
                </div>

              </div>

            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 flex items-center justify-between">
          <div className="text-xs text-slate-500">
            Standard ANSI/SLAS 1-2004 Microplate Specification
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-bold text-white bg-slate-800 hover:bg-slate-900 dark:bg-slate-700 dark:hover:bg-slate-600 rounded-lg transition-colors"
          >
            完成查看
          </button>
        </div>
      </div>
    </div>
  );
};
