import { useState, useEffect, useRef } from 'react';
import { apiClient, errorMessage, submitBatchJob, getBatchJob, cancelBatchJob, type BatchJobResponse } from '../api/client';
import { useAppStore } from '../store/useAppStore';

type Mode = 'screening' | 'evolution' | 'report';
type Residue = { pos: number; aa: string; hydrophobicity: number; charge: number };
type Score = { sequence: string; amp_probability: number; hemo_probability: number; ranking_score?: number; therapeutic_safety_index?: number; residues: Residue[]; provenance?: Record<string, unknown> };
type Candidate = { mutation: string; mutated_seq: string; amp_prob: number; hemo_prob: number; tsi: number; rationale: string };
type Report = { standard_markdown_report: string; provenance: Record<string, unknown> };
const titles = { screening: '双任务研究预测', evolution: '探索性突变排序', report: '计算研究报告' };

function parseSequences(input: string): string[] {
  const lines = input.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
  if (!lines.some(x => x.startsWith('>'))) return lines;
  const sequences: string[] = [];
  let current = '';
  for (const line of lines) {
    if (line.startsWith('>')) {
      if (current) sequences.push(current);
      current = '';
    } else {
      current += line;
    }
  }
  if (current) sequences.push(current);
  return sequences;
}

const statusConfig: Record<string, { label: string; badgeClass: string }> = {
  queued: { label: '队列中', badgeClass: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-300 dark:border-amber-700' },
  running: { label: '执行中', badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-300 dark:border-blue-700' },
  completed: { label: '已完成', badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700' },
  cancelled: { label: '已取消', badgeClass: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700' },
  failed: { label: '失败', badgeClass: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300 border-rose-300 dark:border-rose-700' },
};

export default function ResearchStudio({ mode }: { mode: Mode }) {
  const { activeSequence, addToCart } = useAppStore();
  const [input, setInput] = useState(activeSequence);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [scores, setScores] = useState<Score[]>([]);
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [provenance, setProvenance] = useState<Record<string, unknown> | null>(null);

  // Batch job async queue states
  const [asyncQueueMode, setAsyncQueueMode] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<{
    completed: number;
    total: number;
    failed_count: number;
    status: BatchJobResponse['status'] | string;
  } | null>(null);
  const [jobErrors, setJobErrors] = useState<Array<{ index: number; sequence: string; error: string }>>([]);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, []);

  async function handleCancelJob() {
    if (!activeJobId) return;
    try {
      await cancelBatchJob(activeJobId);
      stopPolling();
      setJobProgress(prev => (prev ? { ...prev, status: 'cancelled' } : null));
      setActiveJobId(null);
      setPending(false);
      setError('作业已被用户取消。');
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function run() {
    stopPolling();
    setError('');
    setScores([]);
    setCandidates(null);
    setReport(null);
    setProvenance(null);
    setActiveJobId(null);
    setJobProgress(null);
    setJobErrors([]);

    const sequences = parseSequences(input);
    if (!sequences.length || (mode !== 'screening' && sequences.length !== 1)) {
      setError(mode === 'screening' ? '请输入至少一条序列。' : '此功能每次接收一条序列。');
      return;
    }

    setPending(true);

    try {
      if (mode === 'screening') {
        const useAsync = sequences.length > 15 || asyncQueueMode;
        if (useAsync) {
          const job = await submitBatchJob(sequences);
          const jobId = job.job_id;
          setActiveJobId(jobId);
          setJobProgress({
            completed: 0,
            total: job.total || sequences.length,
            failed_count: 0,
            status: 'queued',
          });

          // Poll getBatchJob(jobId) every 800ms
          pollIntervalRef.current = setInterval(async () => {
            try {
              const res = await getBatchJob(jobId);
              setJobProgress({
                completed: res.completed,
                total: res.total,
                failed_count: res.failed_count,
                status: res.status,
              });

              if (res.status === 'completed') {
                stopPolling();
                setActiveJobId(null);
                setPending(false);
                setScores(res.results as Score[]);
                if (res.results?.[0]?.provenance) {
                  setProvenance(res.results[0].provenance);
                }
                if (res.errors && res.errors.length > 0) {
                  setJobErrors(res.errors);
                }
              } else if (res.status === 'failed') {
                stopPolling();
                setActiveJobId(null);
                setPending(false);
                if (res.errors && res.errors.length > 0) {
                  setJobErrors(res.errors);
                  setError(`作业执行失败: ${res.errors[0]?.error || '未知错误'}`);
                } else {
                  setError('作业执行失败。');
                }
              } else if (res.status === 'cancelled') {
                stopPolling();
                setActiveJobId(null);
                setPending(false);
                setError('作业已取消。');
              }
            } catch (pollErr) {
              console.error('Polling error:', pollErr);
            }
          }, 800);

          return;
        } else {
          const { data } = await apiClient.post<Score[]>('/api/predict_batch', { sequences });
          setScores(data);
          setProvenance(data[0]?.provenance ?? null);
          setPending(false);
        }
      } else if (mode === 'evolution') {
        const { data } = await apiClient.post('/api/ai_optimize', { sequence: sequences[0] });
        setCandidates(data.solutions);
        setProvenance(data.provenance);
        setPending(false);
      } else {
        const { data } = await apiClient.post<Report>('/api/ai_report', { sequence: sequences[0] });
        setReport(data);
        setProvenance(data.provenance);
        setPending(false);
      }
    } catch (err) {
      stopPolling();
      setActiveJobId(null);
      setPending(false);
      setError(errorMessage(err));
    }
  }

  function exportResult() {
    const content = report?.standard_markdown_report ?? JSON.stringify({ scores, candidates, provenance }, null, 2);
    const blob = new Blob([content], { type: report ? 'text/markdown;charset=utf-8' : 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'safeamp-research.' + (report ? 'md' : 'json');
    link.click();
    URL.revokeObjectURL(url);
  }

  function exportCSV() {
    if (!scores.length) return;
    const header = 'Sequence,Length,P_AMP,P_Hemo,RankingScore\n';
    const rows = scores.map(s => {
      const score = s.ranking_score ?? s.therapeutic_safety_index ?? (s.amp_probability * (1 - s.hemo_probability));
      return `"${s.sequence}",${s.sequence.length},${s.amp_probability.toFixed(4)},${s.hemo_probability.toFixed(4)},${score.toFixed(4)}`;
    }).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `safeamp-screening-results-${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-col gap-5">
      <h2 className="text-xl font-bold">{titles[mode]}</h2>

      <div className="lab-panel p-4 text-sm space-y-2">
        <p>适用范围：10–50 个标准氨基酸、未修饰序列。抗菌端点为大肠杆菌 MIC；溶血端点为人红细胞 HC50。</p>
        <p>概率对应预定义实验标签，不是杀菌率或临床安全性。排序分数 P(amp) × (1 − P(hemo)) 不代表治疗窗口。</p>
        {mode === 'evolution' && <p>候选由同一预测器产生并评分，仅供探索；分数提高不是独立验证，也不能证明实测降毒或活性保留。</p>}
        {mode === 'report' && <p>报告在本地生成，记录运行来源与局限；尚无已核实的本项目发表记录可供引用。</p>}
      </div>

      <div className="lab-panel p-4 space-y-3">
        <label htmlFor={'research-' + mode} className="lab-label">
          {mode === 'screening' ? '序列 / 多行 FASTA（最多 128 条）' : '单条序列'}
        </label>
        <textarea
          id={'research-' + mode}
          rows={mode === 'screening' ? 6 : 3}
          className="lab-input w-full font-mono text-sm"
          value={input}
          onChange={e => setInput(e.target.value)}
        />

        {mode === 'screening' && (
          <div className="flex items-center justify-between pt-1">
            <label className="inline-flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={asyncQueueMode}
                onChange={e => setAsyncQueueMode(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span>异步作业队列模式（&gt;15 条序列自动启用）</span>
            </label>
            <span className="text-xs text-slate-400 font-mono">
              已输入 {parseSequences(input).length} 条序列
            </span>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            className="btn-lab-primary px-4 py-2 disabled:opacity-50"
            disabled={pending}
            onClick={run}
          >
            {pending ? '处理中…' : '运行' + titles[mode]}
          </button>
        </div>

        {error && <p role="alert" className="text-rose-600 dark:text-rose-300 break-words">{error}</p>}
      </div>

      {/* Laboratory-style Batch Progress Card */}
      {jobProgress && (
        <div className="lab-panel p-4 space-y-3 border-blue-200 dark:border-blue-900 bg-blue-50/20 dark:bg-blue-950/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                批量作业监视器 {activeJobId ? `[${activeJobId}]` : ''}
              </span>
              <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${statusConfig[jobProgress.status]?.badgeClass ?? 'bg-slate-100 text-slate-700 border-slate-300'}`}>
                {statusConfig[jobProgress.status]?.label ?? jobProgress.status}
              </span>
            </div>
            {activeJobId && (jobProgress.status === 'queued' || jobProgress.status === 'running') && (
              <button
                type="button"
                className="btn-lab-secondary text-xs px-3 py-1 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 border-rose-200 dark:border-rose-800"
                onClick={handleCancelJob}
              >
                取消作业
              </button>
            )}
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-mono text-slate-600 dark:text-slate-400">
              <span>已完成 {jobProgress.completed} / {jobProgress.total} (失败: {jobProgress.failed_count})</span>
              <span>{jobProgress.total > 0 ? Math.round((jobProgress.completed / jobProgress.total) * 100) : 0}%</span>
            </div>
            <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${jobProgress.total > 0 ? (jobProgress.completed / jobProgress.total) * 100 : 0}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Batch Job Error Alert Box */}
      {jobErrors.length > 0 && (
        <div role="alert" className="lab-panel p-4 border-rose-300 dark:border-rose-800 bg-rose-50/50 dark:bg-rose-950/20 text-rose-900 dark:text-rose-200 space-y-2">
          <div className="font-semibold text-sm flex items-center gap-2">
            <span>⚠️ 存在未通过计算的异常序列（共 {jobErrors.length} 条）：</span>
          </div>
          <ul className="list-disc list-inside text-xs space-y-1 font-mono max-h-48 overflow-y-auto">
            {jobErrors.map((err, idx) => (
              <li key={idx}>
                {err.index >= 0 ? `序号 #${err.index + 1}` : '系统'}
                {err.sequence ? ` [${err.sequence}...]` : ''}: {err.error}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Scores Result Header & Export Bar */}
      {scores.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 lab-panel bg-slate-50/50 dark:bg-slate-800/30">
          <div className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            筛选结果列表（已完成 {scores.length} 条序列预测）
          </div>
          <div className="flex items-center gap-2">
            <button type="button" className="btn-lab-secondary text-xs px-3 py-1.5" onClick={exportCSV}>
              导出 CSV 表格
            </button>
            <button type="button" className="btn-lab-secondary text-xs px-3 py-1.5" onClick={exportResult}>
              导出 JSON 记录
            </button>
          </div>
        </div>
      )}

      {/* Result Cards */}
      {scores.map((s, i) => {
        const score = s.ranking_score ?? s.therapeutic_safety_index ?? (s.amp_probability * (1 - s.hemo_probability));
        return (
          <div className="lab-panel p-4 space-y-3" key={i}>
            <p className="font-mono break-all">{s.sequence}</p>
            <p>抗菌标签概率 {s.amp_probability.toFixed(4)} · 溶血标签概率 {s.hemo_probability.toFixed(4)} · 排序分数 {score.toFixed(4)}</p>
            <p className="text-sm text-slate-500">残基理化属性提示（固定规则，不是梯度归因或机制解释）</p>
            <div className="flex flex-wrap gap-1">
              {s.residues.map(r => (
                <span
                  key={r.pos}
                  title={'位置 ' + r.pos + '; KD 疏水性 ' + r.hydrophobicity + '; 电荷估计 ' + r.charge}
                  className={'px-2 py-1 rounded font-mono ' + (r.hydrophobicity > 0 ? 'bg-amber-100 text-amber-950 dark:bg-amber-950/60 dark:text-amber-200' : 'bg-blue-100 text-blue-950 dark:bg-blue-950/60 dark:text-blue-200')}
                >
                  {r.aa}<sub>{r.pos}</sub>
                </span>
              ))}
            </div>
            <button
              className="btn-lab-secondary px-3 py-1"
              onClick={() => addToCart({
                sequence: s.sequence,
                name: 'Research candidate',
                p_amp: s.amp_probability,
                p_hemo: s.hemo_probability,
                tsi: score,
                run_id: String(s.provenance?.run_id ?? 'research-run'),
              })}
            >
              存入候选库
            </button>
          </div>
        );
      })}

      {candidates !== null && (
        <div className="lab-panel p-4 space-y-3">
          {!candidates.length && <p>未找到满足当前计算筛选条件的候选；这不表明原序列安全或最优。</p>}
          {candidates.map(c => (
            <div key={c.mutation} className="border-b border-slate-200 dark:border-slate-700 pb-3">
              <strong>{c.mutation}</strong>
              <p className="font-mono break-all">{c.mutated_seq}</p>
              <p>抗菌标签概率 {c.amp_prob.toFixed(4)} · 溶血标签概率 {c.hemo_prob.toFixed(4)} · 排序分数 {c.tsi.toFixed(4)}</p>
              <p>{c.rationale}</p>
            </div>
          ))}
        </div>
      )}

      {report && (
        <pre className="lab-panel p-4 whitespace-pre-wrap break-words text-sm">
          {report.standard_markdown_report}
        </pre>
      )}

      {provenance && (
        <div className="lab-panel p-4 space-y-3">
          <h3>运行来源</h3>
          <pre className="text-xs whitespace-pre-wrap break-words">{JSON.stringify(provenance, null, 2)}</pre>
          <div className="flex flex-wrap gap-2">
            <button className="btn-lab-secondary px-3 py-2" onClick={exportResult}>
              导出研究记录 (JSON)
            </button>
            {scores.length > 0 && (
              <button className="btn-lab-secondary px-3 py-2" onClick={exportCSV}>
                导出筛选结果 (CSV)
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
