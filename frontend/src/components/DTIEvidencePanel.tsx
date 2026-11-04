import { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, Eye, FileSearch, RefreshCw, X } from 'lucide-react';
import { useDTIEvidenceStatus } from '../api/dtiEvidence';
import { DTIModelLimitations } from './DTIModelLimitations';

export function DTIEvidencePanel({ modelId, modelHash }: { modelId?: string; modelHash?: string }) {
  const evidence = useDTIEvidenceStatus();
  const data = evidence.data;
  const known = data?.status === 'available';

  const [isDismissed, setIsDismissed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('dti_evidence_dismissed') === 'true';
    } catch {
      return false;
    }
  });

  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const toggleDismiss = (dismiss: boolean) => {
    setIsDismissed(dismiss);
    try {
      if (dismiss) {
        localStorage.setItem('dti_evidence_dismissed', 'true');
      } else {
        localStorage.removeItem('dti_evidence_dismissed');
      }
    } catch {}
  };

  if (isDismissed) {
    return (
      <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-amber-50/40 dark:bg-amber-950/20 border border-amber-200/50 dark:border-amber-900/30 text-xs text-amber-800/80 dark:text-amber-300/80 transition-all">
        <div className="flex items-center gap-1.5">
          <FileSearch size={13} className="text-amber-600 dark:text-amber-400" />
          <span>研究证据合规面板已隐藏（当前处于计算探索模式）</span>
        </div>
        <button
          type="button"
          onClick={() => toggleDismiss(false)}
          className="flex items-center gap-1 text-[11px] font-medium text-amber-700 dark:text-amber-300 hover:underline cursor-pointer"
        >
          <Eye size={12} />
          <span>恢复显示</span>
        </button>
      </div>
    );
  }

  return (
    <section
      aria-label="研究证据状态"
      aria-busy={evidence.isPending}
      className={`rounded-2xl border border-amber-200 bg-amber-50/60 p-3 sm:p-4 transition-all duration-200 dark:border-amber-800/60 dark:bg-amber-950/20 ${
        isExpanded ? 'min-h-[220px]' : ''
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0 flex-1 flex flex-wrap items-center gap-x-3 gap-y-1">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
            <FileSearch size={16} className="shrink-0 text-amber-700 dark:text-amber-300" />
            <span>研究证据状态</span>
          </h3>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            data?.admitted_count && data.admitted_count > 0
              ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300'
              : 'bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300'
          }`}>
            {evidence.isPending ? '正在核对…' : known ? (data.admitted_count && data.admitted_count > 0 ? '外部证据复核准入已完成' : '独立外部评价尚未完成（探索模式）') : '状态无法确认'}
          </span>
          {!isExpanded && known && (
            <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline">
              · 复核 {data.reviewed_count} 条 / 准入 {data.admitted_count} 条
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() => void evidence.refetch()}
            disabled={evidence.isFetching}
            aria-label="刷新证据状态"
            className="rounded-lg border border-amber-300 px-2.5 py-1 text-xs font-medium text-amber-900 transition-colors hover:bg-amber-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-60 dark:border-amber-700 dark:text-amber-200 dark:hover:bg-amber-900/40 cursor-pointer"
          >
            <RefreshCw size={13} className={`mr-1 inline ${evidence.isFetching ? 'animate-spin motion-reduce:animate-none' : ''}`} />
            刷新
          </button>

          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="rounded-lg border border-amber-300/80 px-2.5 py-1 text-xs font-medium text-amber-900 hover:bg-amber-100 dark:border-amber-700/80 dark:text-amber-200 dark:hover:bg-amber-900/40 flex items-center gap-1 cursor-pointer"
          >
            {isExpanded ? (
              <>
                <ChevronUp size={13} />
                <span>收起详情</span>
              </>
            ) : (
              <>
                <ChevronDown size={13} />
                <span>展开详情</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => toggleDismiss(true)}
            title="隐藏此证据面板"
            aria-label="隐藏证据面板"
            className="p-1 rounded-md text-amber-700/70 hover:text-amber-900 hover:bg-amber-200/50 dark:text-amber-400/70 dark:hover:text-amber-200 dark:hover:bg-amber-900/50 transition-colors cursor-pointer"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      <DTIModelLimitations modelId={modelId} modelHash={modelHash} evidence={data} />

      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-amber-200/60 dark:border-amber-800/40 animate-in fade-in duration-150">
          {known ? (
            <>
              <dl className="grid grid-cols-3 gap-2 sm:gap-4">
                {[[data.reviewed_count, '本阶段复核'], [data.confirmed_point_count, '原图点值确认'], [data.admitted_count, '正式准入']].map(([count, label]) => (
                  <div key={label as string} className={`rounded-xl border p-2.5 sm:p-3 ${
                    label === '正式准入' && typeof count === 'number' && count > 0
                      ? 'border-emerald-300 dark:border-emerald-800/80 bg-emerald-50/40 dark:bg-emerald-950/30'
                      : 'border-amber-200/70 bg-white/75 dark:border-amber-900/60 dark:bg-slate-900/60'
                  }`}>
                    <dt className="text-xs leading-4 text-slate-700 dark:text-slate-300">{label as string}</dt>
                    <dd className={`mt-1 text-xl font-semibold tabular-nums ${
                      label === '正式准入' && typeof count === 'number' && count > 0 ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-900 dark:text-slate-100'
                    }`}>{count}<span className="ml-1 text-xs font-normal">条</span></dd>
                  </div>
                ))}
              </dl>
              <p className="mt-2.5 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                {typeof data.admitted_count === 'number' && data.admitted_count > 0
                  ? '已完成高置信度外部基准点复核，5条经典对正式准入，3条证据不足已规范排除。'
                  : '模型运行就绪与科学证据分开判断。当前可做计算探索；Davis基准结果不等同于独立外部泛化验证。'}
              </p>
              <details className="mt-2 text-slate-700 dark:text-slate-300">
                <summary className="py-1.5 text-xs font-medium cursor-pointer rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600">查看复核与准入明细 · {data.reviewed_at}</summary>
                <p className="mb-2 text-xs leading-relaxed">范围：{data.scope_label}。约定评估模型为{data.evaluation_model}。已核准条目已锁定序列与SMILES结构。</p>
                <ul className="space-y-1.5 max-h-60 overflow-y-auto">
                  {(data.candidates ?? []).map(candidate => (
                    <li key={candidate.id} className="rounded-lg bg-white/80 p-2.5 dark:bg-slate-900/70 text-xs">
                      <div className="flex flex-wrap items-center justify-between gap-1">
                        <span className="break-words font-medium">{candidate.label}</span>
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                          candidate.status === 'admitted'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200'
                            : candidate.status === 'excluded'
                            ? 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                            : 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-200'
                        }`}>
                          {candidate.status === 'admitted' ? '已准入' : candidate.status === 'excluded' ? '已排除' : '待定'}
                        </span>
                      </div>
                      <p className="mt-0.5 text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">{candidate.reason}</p>
                    </li>
                  ))}
                </ul>
              </details>
            </>
          ) : (
            <p className="flex items-start gap-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
              <AlertCircle size={15} className="mt-0.5 shrink-0" />
              {evidence.isPending ? '证据状态正在读取，模型运行状态单独检查。' : '暂时无法读取有效的研究记录，复核数量和外部指标均无法确认。探索性预测仍由模型运行状态决定。'}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
