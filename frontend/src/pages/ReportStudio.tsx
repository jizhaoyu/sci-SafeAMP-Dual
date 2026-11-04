import React, { useState, useEffect } from 'react';
import { 
  FileSpreadsheet, 
  Download, 
  CheckCircle2, 
  Sparkles, 
  ShieldCheck, 
  Layers, 
  FolderArchive, 
  FileText, 
  BarChart3, 
  TestTube, 
  Copy, 
  Check, 
  ExternalLink,
  AlertTriangle,
  RefreshCw,
  Clock,
  Dna,
  Zap
} from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { 
  exportSupplementaryPackage, 
  getDownloadPackageUrl, 
  type SupplementaryPackageResult 
} from '../api/dtiClient';
import { fetchAsyncTasksList, type AsyncTask } from '../api/asyncTaskClient';
import { DTIEvidencePanel } from '../components/DTIEvidencePanel';
import { useDTIEvidenceStatus } from '../api/dtiEvidence';

export default function ReportStudio() {
  const { activeEntity, activeTarget, cart } = useAppStore();
  const evidence = useDTIEvidenceStatus();

  // Source configuration
  const [sourceMode, setSourceMode] = useState<'current_workspace' | 'async_task'>('current_workspace');
  const [completedTasks, setCompletedTasks] = useState<AsyncTask[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [loadingTasks, setLoadingTasks] = useState<boolean>(false);

  // Form Fields
  const [targetName, setTargetName] = useState<string>('ABL1');
  const [drugName, setDrugName] = useState<string>('Dasatinib (达沙替尼)');
  const [drugSmiles, setDrugSmiles] = useState<string>('CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO');
  const [authorName, setAuthorName] = useState<string>('DTI BioAI Research Laboratory');

  // Preview Tabs
  const [activeTab, setActiveTab] = useState<'inventory' | 'figures' | 'microplate' | 'report'>('inventory');

  // Export States
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [packageResult, setPackageResult] = useState<SupplementaryPackageResult | null>(null);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  // Sync with active entity/target from store on initial load
  useEffect(() => {
    if (activeEntity?.kind === 'small_molecule' && activeEntity.smiles) {
      setDrugSmiles(activeEntity.smiles);
      if (activeEntity.name) setDrugName(activeEntity.name);
    }
    if (activeTarget?.id || activeTarget?.standardDisplayName) {
      setTargetName(activeTarget.id || activeTarget.standardDisplayName);
    }
  }, [activeEntity, activeTarget]);

  // Load completed tasks when switching to async_task mode
  useEffect(() => {
    if (sourceMode === 'async_task') {
      setLoadingTasks(true);
      fetchAsyncTasksList(undefined, 'completed', 20)
        .then((tasks: AsyncTask[]) => {
          setCompletedTasks(tasks || []);
          if (tasks && tasks.length > 0) {
            setSelectedTaskId(tasks[0].task_id);
          }
        })
        .catch((err: any) => console.error('Failed to load completed tasks:', err))
        .finally(() => setLoadingTasks(false));
    }
  }, [sourceMode]);

  const calculatedCart = cart.filter(c => c.kind === 'small_molecule' && typeof c.pkd === 'number' && Number.isFinite(c.pkd));
  const recordedModels = [...new Set(calculatedCart.map(c => c.model_used).filter(Boolean))];
  const modelUsed = recordedModels.length === 1 ? recordedModels[0] : '请使用同一模型的已计算候选';
  const hasValidExportData = sourceMode === 'async_task' ? Boolean(selectedTaskId) : calculatedCart.length > 0;

  const handleExport = async () => {
    setIsExporting(true);
    setExportError(null);
    setPackageResult(null);

    try {
      const params: any = {
        target_name: targetName.trim(),
        author: authorName.trim()
      };

      if (sourceMode === 'async_task') {
        if (!selectedTaskId) {
          throw new Error('请先选择一个已完成的异步计算任务以导出交付包。');
        }
        params.task_id = selectedTaskId;
      } else {
        if (calculatedCart.length === 0) {
          throw new Error('当前工作区无已完成的模型预测数据。正式科研交付材料严禁导出未执行预测的假定数据。请先在先导优化工作台完成计算并将候选加入候选库，或切换为【已完成异步任务】。');
        }

        if (calculatedCart.some(c => !c.target_symbol || !c.model_used)) {
          throw new Error('候选缺少原始靶点或模型记录，请重新计算后加入分子库；旧缓存分数不能推定计算来源。');
        }

        // Filter candidates to strictly match targetName if target_symbol is specified, preserving target identity
        const matchedCart = calculatedCart.filter(c => 
          c.target_symbol?.trim().toLowerCase() === targetName.trim().toLowerCase()
        );

        if (matchedCart.length === 0 && calculatedCart.length > 0) {
          const availableTargets = [...new Set(calculatedCart.map(c => c.target_symbol).filter(Boolean))].join(', ');
          throw new Error(`当前候选库中的预测分子针对靶点 [${availableTargets || '其他靶点'}] 计算，与当前选择导出的靶点 [${targetName}] 不符。严禁将针对某一激酶计算的分数篡改重标为另一激酶。请选择匹配的靶点或重新进行目标激酶预测。`);
        }

        const models = [...new Set(matchedCart.map(c => c.model_used))];
        if (models.length !== 1) {
          throw new Error('当前候选来自不同预测模型，请分模型导出，避免把其他模型的分数重标为同一模型。');
        }
        const evaluatedBaseline = matchedCart.find(c => c.smiles?.trim() === drugSmiles.trim());

        const candidates = matchedCart.map((c, idx) => ({
          id: c.id || `cand_${idx + 1}`,
          name: c.name || `Candidate_${idx + 1}`,
          smiles: c.smiles || c.sequence,
          target_symbol: c.target_symbol,
          modification_type: c.modification_type || 'Workspace Candidate',
          source: c.source || 'workspace_design',
          scaffold_type: c.scaffold_type,
          parent_similarity: c.parent_similarity ?? (c.smiles && drugSmiles && c.smiles.trim() === drugSmiles.trim() ? 1.0 : undefined),
          predicted_pkd: c.pkd,
          delta_pkd: (c.pkd != null && evaluatedBaseline?.pkd != null) ? +(c.pkd - evaluatedBaseline.pkd).toFixed(4) : undefined,
          predicted_kd_nM: c.pkd != null ? Math.pow(10, 9 - c.pkd) : undefined,
          sa_score: c.sa_score,
          sa_tier: c.sa_tier || (c.sa_score != null ? (c.sa_score < 3.0 ? 'easy' : c.sa_score > 6.0 ? 'challenging' : 'moderate') : undefined),
          admet: c.admet || undefined
        }));

        const baselineData = evaluatedBaseline ? {
          name: drugName,
          smiles: drugSmiles,
          predicted_pkd: evaluatedBaseline.pkd,
          predicted_kd_nM: evaluatedBaseline.pkd != null ? Math.pow(10, 9 - evaluatedBaseline.pkd) : undefined,
          sa_score: evaluatedBaseline.sa_score,
          admet: evaluatedBaseline.admet,
        } : (drugSmiles ? {
          name: drugName,
          smiles: drugSmiles,
        } : {});

        params.result_payload = {
          target_name: targetName,
          model_used: models[0],
          baseline: baselineData,
          candidates,
          audit_metrics: {
            exported_candidates_count: candidates.length
          }
        };
      }

      const res = await exportSupplementaryPackage(params);
      setPackageResult(res);
    } catch (err: any) {
      setExportError(err.message || '导出交付包失败，请检查服务日志。');
    } finally {
      setIsExporting(false);
    }
  };

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300 pb-16">
      
      {/* 1. Header Banner */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-sm shrink-0">
            <FolderArchive size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                综合科研成果与科研交付工作台
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 font-bold font-mono">
                P5A 成果交付
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              一键生成符合国际主流期刊（Nature/J. Med. Chem.）规范的 Supplementary Materials 交付包（包含 SVG/PDF 矢量图表、96孔板排盘、非递归 SHA256SUMS 校验和）。
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting || !hasValidExportData}
            title={!hasValidExportData ? (sourceMode === 'async_task' ? '请选择已完成的异步计算任务' : '当前工作区无已完成预测数据，严禁导出伪造数据') : undefined}
            className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 shadow-sm flex items-center gap-2 transition-all cursor-pointer focus-ring disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isExporting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>正在生成科研成果数据包...</span>
              </>
            ) : (
              <>
                <Download size={15} />
                <span>生成并打包 Supplementary Materials (.ZIP)</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Warning when no valid export data is available */}
      {!hasValidExportData && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-200 text-xs flex items-start gap-2.5">
          <AlertTriangle size={16} className="text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong className="font-semibold block mb-0.5">未检测到有效计算结果，禁止导出科研交付包：</strong>
            {sourceMode === 'async_task'
              ? '请在下方【已完成异步任务】列表中选择一个成功完成的计算任务。'
              : '当前工作区尚未完成模型预测，且候选库中无有效计算结果。为确保学术严谨，系统严禁以固定默认值生成科研材料。请先在【先导化合物优化】或【激酶亲和力预测】工作台运行计算，或切换至【已完成异步任务】。'}
          </div>
        </div>
      )}

      {/* 2. Scientific Disclaimer Notice */}
      <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5">
        <AlertTriangle size={16} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="font-semibold block mb-0.5">严谨科研交付说明与事实校准原则：</strong>
          导出保留候选的原始靶点、实际模型和已计算指标。只有已完成的服务端任务可标记为已认证；工作区记录会明确标记为 Unverified，缺失指标保持为空。计算分数属于<strong>计算探索假说</strong>，仍需实验核查。数据包附带来源说明与 SHA-256 完整性指纹。
        </div>
      </div>

      {/* 3. Main Split View: Configuration & Live Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Data Source & Metadata Setup */}
        <div className="space-y-4">
          
          {/* Source Selection Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs space-y-3.5">
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider font-mono flex items-center gap-1.5">
              <Layers size={14} className="text-sky-500" />
              <span>数据来源选择 (Data Source)</span>
            </h3>

            <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl">
              <button
                type="button"
                onClick={() => setSourceMode('current_workspace')}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  sourceMode === 'current_workspace'
                    ? 'bg-white dark:bg-slate-900 text-sky-600 dark:text-sky-400 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-800'
                }`}
              >
                当前工作台设计
              </button>
              <button
                type="button"
                onClick={() => setSourceMode('async_task')}
                className={`py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                  sourceMode === 'async_task'
                    ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-800'
                }`}
              >
                已完成异步任务
              </button>
            </div>

            {sourceMode === 'async_task' ? (
              <div className="space-y-2 pt-1">
                <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block">
                  选择已归档的后台计算任务
                </label>
                {loadingTasks ? (
                  <div className="text-xs text-slate-400 py-3 text-center">正在加载已完成任务...</div>
                ) : completedTasks.length === 0 ? (
                  <div className="text-xs text-amber-600 dark:text-amber-400 p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
                    暂无已完成的持久化后台任务。可先在 DTI / 先导优化工作台发起计算或使用当前设计方案。
                  </div>
                ) : (
                  <select
                    value={selectedTaskId}
                    onChange={e => setSelectedTaskId(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-mono text-slate-900 dark:text-slate-100"
                  >
                    {completedTasks.map(t => (
                      <option key={t.task_id} value={t.task_id}>
                        [{t.task_type}] {t.task_id.slice(0, 8)}... - {t.created_at.slice(11, 19)}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            ) : (
              <div className="space-y-3 pt-1">
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    靶点激酶名称 (Target Kinase)
                  </label>
                  <input
                    type="text"
                    value={targetName}
                    onChange={e => setTargetName(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-mono"
                    placeholder="e.g. ABL1, EGFR, BRAF"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    先导母体名称 (Lead Molecule Name)
                  </label>
                  <input
                    type="text"
                    value={drugName}
                    onChange={e => setDrugName(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                    母体 SMILES 字符串
                  </label>
                  <input
                    type="text"
                    value={drugSmiles}
                    onChange={e => setDrugSmiles(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-mono"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                署名实验室 / 作者 (Author / Institution)
              </label>
              <input
                type="text"
                value={authorName}
                onChange={e => setAuthorName(e.target.value)}
                className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                基准评估模型 (DTI Reference Model)
              </label>
              <input
                type="text"
                value={modelUsed}
                className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono text-[11px]"
                disabled
              />
            </div>
          </div>

          {/* Research Evidence Mini Card */}
          <DTIEvidencePanel />

        </div>

        {/* Right Column: Previews & Download Action Card */}
        <div className="lg:col-span-2 space-y-4">
          
          {/* Export Result Banner (If generated) */}
          {packageResult && (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50 to-sky-50 dark:from-emerald-950/40 dark:via-teal-950/30 dark:to-sky-950/30 border border-emerald-300 dark:border-emerald-800 shadow-xs space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={18} className="text-emerald-600 dark:text-emerald-400" />
                  <span className="text-sm font-bold text-emerald-950 dark:text-emerald-100">
                    科研交付包打包构建成功！
                  </span>
                </div>
                <a
                  href={getDownloadPackageUrl(packageResult.package_id)}
                  download={`Supplementary_Materials_${packageResult.package_id}.zip`}
                  className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Download size={14} />
                  <span>立即下载 ZIP 成果包</span>
                </a>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-emerald-200/60 dark:border-emerald-900/60">
                  <span className="text-[10px] text-slate-400 block">包标识符:</span>
                  <strong className="text-slate-800 dark:text-slate-200 truncate block" title={packageResult.package_id}>
                    {packageResult.package_id}
                  </strong>
                </div>
                <div className="p-2 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-emerald-200/60 dark:border-emerald-900/60">
                  <span className="text-[10px] text-slate-400 block">资产文件总数:</span>
                  <strong className="text-emerald-600 dark:text-emerald-400 block">
                    {packageResult.total_files} 个文件
                  </strong>
                </div>
                <div className="p-2 rounded-lg bg-white/80 dark:bg-slate-900/80 border border-emerald-200/60 dark:border-emerald-900/60 col-span-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-slate-400">SHA-256 指纹:</span>
                    <button
                      type="button"
                      onClick={() => copyHash(packageResult.zip_sha256)}
                      className="text-[10px] text-sky-600 dark:text-sky-400 hover:underline flex items-center gap-0.5 cursor-pointer"
                    >
                      {copiedHash ? <Check size={11} /> : <Copy size={11} />}
                      <span>{copiedHash ? '已复制' : '复制哈希'}</span>
                    </button>
                  </div>
                  <strong className="text-[10px] text-slate-700 dark:text-slate-300 font-mono truncate block" title={packageResult.zip_sha256}>
                    {packageResult.zip_sha256}
                  </strong>
                </div>
              </div>
            </div>
          )}

          {exportError && (
            <div className="p-3.5 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-300">
              {exportError}
            </div>
          )}

          {/* Interactive Preview Panel */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xs overflow-hidden">
            
            {/* Tabs */}
            <div className="flex items-center border-b border-slate-100 dark:border-slate-800 px-4 pt-2 gap-2 overflow-x-auto">
              <button
                type="button"
                onClick={() => setActiveTab('inventory')}
                className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-1.5 shrink-0 ${
                  activeTab === 'inventory'
                    ? 'border-sky-500 text-sky-600 dark:text-sky-400'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <FolderArchive size={14} />
                <span>文件清单与资产目录 (Manifest)</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('figures')}
                className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-1.5 shrink-0 ${
                  activeTab === 'figures'
                    ? 'border-sky-500 text-sky-600 dark:text-sky-400'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <BarChart3 size={14} />
                <span>论文级矢量图表 (Figures)</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('microplate')}
                className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-1.5 shrink-0 ${
                  activeTab === 'microplate'
                    ? 'border-sky-500 text-sky-600 dark:text-sky-400'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <TestTube size={14} />
                <span>96 孔板湿法工单 (Wetlab)</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('report')}
                className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-all cursor-pointer flex items-center gap-1.5 shrink-0 ${
                  activeTab === 'report'
                    ? 'border-sky-500 text-sky-600 dark:text-sky-400'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <FileText size={14} />
                <span>学术评估报告摘要 (Brief)</span>
              </button>
            </div>

            {/* Tab Contents */}
            <div className="p-4">
              
              {/* TAB 1: Manifest Inventory */}
              {activeTab === 'inventory' && (
                <div className="space-y-3">
                  <p className="text-xs text-slate-500 leading-relaxed">
                    本数据包严格遵循 FAIR 原则（可发现、可访问、可互操作、可重用），打包时将按以下目录结构输出：
                  </p>
                  <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden text-xs">
                    <table className="w-full text-left">
                      <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 text-[11px] font-mono">
                        <tr>
                          <th className="p-2.5">文件相对路径</th>
                          <th className="p-2.5">格式</th>
                          <th className="p-2.5">规范用途</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono text-[11px]">
                        <tr>
                          <td className="p-2.5 font-bold text-sky-600">README.md</td>
                          <td className="p-2.5">Markdown</td>
                          <td className="p-2.5 font-sans text-slate-600 dark:text-slate-300">研究概述、免责声明、计算来源与指标总览</td>
                        </tr>
                        <tr>
                          <td className="p-2.5 font-bold text-sky-600">data_dictionary.csv</td>
                          <td className="p-2.5">CSV</td>
                          <td className="p-2.5 font-sans text-slate-600 dark:text-slate-300">标准化列名、数据类型、物理单位与来源方法定义</td>
                        </tr>
                        <tr>
                          <td className="p-2.5 font-bold text-emerald-600">predictions.csv</td>
                          <td className="p-2.5">CSV</td>
                          <td className="p-2.5 font-sans text-slate-600 dark:text-slate-300">母体与所有衍生候选预测打分（pKd, Kd, 适用域）</td>
                        </tr>
                        <tr>
                          <td className="p-2.5 font-bold text-emerald-600">candidates.csv</td>
                          <td className="p-2.5">CSV</td>
                          <td className="p-2.5 font-sans text-slate-600 dark:text-slate-300">详细候选分子、改构类型、来源标记、骨架保持/跃迁</td>
                        </tr>
                        <tr>
                          <td className="p-2.5 font-bold text-amber-600">excluded_records.csv</td>
                          <td className="p-2.5">CSV</td>
                          <td className="p-2.5 font-sans text-slate-600 dark:text-slate-300">因语法、分子量或硬约束被拦截的分子及拦截原因</td>
                        </tr>
                        <tr>
                          <td className="p-2.5 font-bold text-indigo-600">figures/*</td>
                          <td className="p-2.5">SVG / PDF / CSV</td>
                          <td className="p-2.5 font-sans text-slate-600 dark:text-slate-300">论文级矢量图表（分布图、漏斗图、SAR对比）及底层数据</td>
                        </tr>
                        <tr>
                          <td className="p-2.5 font-bold text-purple-600">wetlab/*</td>
                          <td className="p-2.5">CSV</td>
                          <td className="p-2.5 font-sans text-slate-600 dark:text-slate-300">96孔微孔板排盘工单与 Labcyte Echo 移液器点样清单</td>
                        </tr>
                        <tr>
                          <td className="p-2.5 font-bold text-slate-700 dark:text-slate-300">SHA256SUMS</td>
                          <td className="p-2.5">TXT</td>
                          <td className="p-2.5 font-sans text-slate-600 dark:text-slate-300">非递归 SHA-256 全文件完整性指纹，支持独立验签</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 2: Figures Preview */}
              {activeTab === 'figures' && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                  <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-2">
                    <span className="text-[10px] font-bold text-sky-600 uppercase font-mono block">Figure 1</span>
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200">亲和力分布与基准线 (Affinity Distribution)</h4>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      展示全部筛选或衍生分子的 pKd 频数分布直方图，标注母体参考结合位与高亲和力阈值线。
                    </p>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-300 font-mono">
                      SVG / PDF / CSV
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-2">
                    <span className="text-[10px] font-bold text-indigo-600 uppercase font-mono block">Figure 2</span>
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200">多级筛选与清洗漏斗 (Screening Funnel)</h4>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      横向条形图展现初始分子池、结构清洗、药化硬约束过滤至最终高亲和力分子的递进保留率。
                    </p>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-mono">
                      SVG / PDF / CSV
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-2">
                    <span className="text-[10px] font-bold text-emerald-600 uppercase font-mono block">Figure 3</span>
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200">构效关系亲和力增益 (SAR Comparison)</h4>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      对比各候选衍生相对于母体的 ΔpKd 变化幅度，区分骨架保持与骨架跃迁方案。
                    </p>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-mono">
                      SVG / PDF / CSV
                    </span>
                  </div>
                </div>
              )}

              {/* TAB 3: Microplate Preview */}
              {activeTab === 'microplate' && (
                <div className="space-y-3">
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-800 dark:text-slate-200 block">标准 96 孔微孔板布局规范：</span>
                      <span className="text-[11px] text-slate-500">
                        A01: 阳性对照 (母体先导) · H12: 阴性对照 (DMSO) · 其余孔位按优先度阶梯梯度排布
                      </span>
                    </div>
                    <span className="text-xs font-mono font-bold text-purple-600 dark:text-purple-400">
                      Echo 移液兼容
                    </span>
                  </div>
                  <div className="grid grid-cols-12 gap-1 p-2 bg-slate-100 dark:bg-slate-950 rounded-xl text-center font-mono text-[9px]">
                    {Array.from({ length: 96 }).map((_, i) => {
                      const isA01 = i === 0;
                      const isH12 = i === 95;
                      const isCand = i > 0 && i < 10;
                      return (
                        <div
                          key={i}
                          className={`h-7 rounded flex items-center justify-center font-bold ${
                            isA01
                              ? 'bg-red-500 text-white'
                              : isH12
                              ? 'bg-slate-400 text-white'
                              : isCand
                              ? 'bg-emerald-500 text-white'
                              : 'bg-white dark:bg-slate-800 text-slate-400'
                          }`}
                        >
                          {String.fromCharCode(65 + Math.floor(i / 12))}{(i % 12) + 1}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* TAB 4: Academic Report Preview */}
              {activeTab === 'report' && (
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 text-xs space-y-2.5 font-sans leading-relaxed text-slate-700 dark:text-slate-300">
                  <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    靶向人类催化激酶 {targetName} 的先导改构与多维成药性研究学术报告摘要
                  </h4>
                  <p>
                    针对靶标激酶 {targetName}，以临床已知活性分子 {drugName} 为基准先导物，通过 RDKit 拓扑构建与 DTI 模型打分，系统评估了周边官能团电子等排取代与骨架微调方案。
                  </p>
                  <p className="text-[11px] text-slate-500">
                    （完整中英文报告包括背景调研、机理假说、专利保护权利要求书草案与参考文献索引，已包含在数据包的 <code>reports/research_report.html</code> 与 <code>.md</code> 中）。
                  </p>
                </div>
              )}

            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
