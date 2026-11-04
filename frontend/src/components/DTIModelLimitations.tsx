import { isModelDiagnostic, modelLimitationNotice, type DTIEvidenceStatus } from '../api/dtiEvidence';

export function DTIModelLimitations({ modelId, evidence, modelHash }: { modelId?: string; evidence?: DTIEvidenceStatus; modelHash?: string }) {
  if (modelId !== 'f1_ridge') return null;
  const diagnostic = evidence?.status === 'available' ? evidence.model_diagnostics?.[modelId] : undefined;
  const versionMatches = isModelDiagnostic(diagnostic) && (!modelHash || modelHash === diagnostic.model_sha256);
  const notice = modelLimitationNotice(modelId, evidence, modelHash);
  return (
    <aside aria-label="F1模型使用限制" className="mt-3 rounded-xl border border-amber-300 bg-white/75 p-3 text-sm leading-relaxed text-slate-800 dark:border-amber-800 dark:bg-slate-900/70 dark:text-slate-200">
      <p className="font-semibold text-amber-900 dark:text-amber-200">F1 Ridge · 已记录的模型使用限制</p>
      {notice && <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{notice}</p>}
      <div className="mt-2 rounded-lg bg-amber-500/10 p-2 text-xs border border-amber-500/20">
        <span className="font-semibold text-amber-800 dark:text-amber-300">【方案 A 激酶基因级最强亲和力说明】</span>
        ：当前预测对应目标激酶基因全谱（含各类变体）的结合亲和力上限。输入序列为全长野生型参考序列，不具备区分单点耐药突变（如 EGFR T790M、BRAF V600E）的能力；Kd ≥ 10,000 nM (pKd ≤ 5.0) 严格属于右删失下限。
      </div>
      {versionMatches && <details className="mt-1">
        <summary className="min-h-11 cursor-pointer rounded py-3 font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600">查看F1诊断依据</summary>
        <p>原DAVIS目录中{diagnostic.high_affinity_count}个参考pKd＞8的配对均被低估，平均绝对误差{diagnostic.high_affinity_mae_pkd.toFixed(2)} pKd。包含训练内数据，是已有基准诊断；不能计为独立外部评价。</p>
        <p className="mt-2 break-all text-xs text-slate-600 dark:text-slate-400">诊断绑定模型：{diagnostic.model_sha256}；复核日期：{diagnostic.reviewed_at}。</p>
      </details>}
    </aside>
  );
}
