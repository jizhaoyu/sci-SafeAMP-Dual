import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bot, 
  Sparkles, 
  Cpu, 
  Zap, 
  Play, 
  Pause,
  Square, 
  Sliders,
  CheckCircle2, 
  AlertCircle, 
  ArrowRight, 
  Activity, 
  Shield, 
  Layers, 
  Terminal, 
  FileText, 
  ExternalLink, 
  RefreshCw, 
  Copy, 
  Check,
  Flame,
  Award,
  ChevronRight
} from 'lucide-react';
import { Molecule2DViewer } from './Molecule2DViewer';
import { useAppStore } from '../store/useAppStore';

interface PresetScenario {
  id: string;
  title: string;
  scenario: string;
  target_symbol: string;
  target_sequence: string;
  baseline_smiles: string;
  default_goal: string;
  target_pkd: number;
  min_admet_score: number;
  max_hemolysis_pct: number;
  tag: string;
}

interface CandidateRecord {
  id: string;
  generation: number;
  smiles: string;
  target_symbol: string;
  predicted_pkd: number;
  predicted_kd_nM: number;
  confidence_band: string;
  sa_score: number;
  solubility_logs: number;
  solubility_tier: string;
  caco2_tier: string;
  log_bb: number;
  bbb_tier: string;
  admet_score: number;
  hemolysis_risk_pct: number;
  hemolysis_provenance?: string;
  hemolysis_note?: string;
  modifications: string;
  rationale: string;
  parent_id?: string;
  timestamp: string;
}

interface StreamLog {
  id: string;
  timestamp: string;
  agent: string;
  thought: string;
  iteration?: number;
}

const DEFAULT_PRESETS: PresetScenario[] = [
  {
    id: "egfr_t790m_escape",
    title: "奥希替尼对抗 EGFR(T790M) 耐药突变自主改构",
    scenario: "kinase_escape",
    target_symbol: "EGFR(T790M)",
    target_sequence: "MRRHPKLTELATKLARLQKELDVVLQHKERLEKEAQKLEKELKKLKQENEVLKQENEQLKQEIELLKKEIELLKKEIEQLKQENEKLKQE",
    baseline_smiles: "CN1CCN(CC1)C2=CC(=C(C=C2)NC(=O)C=C)NC3=NC=CC(=N3)C4=CN(C5=CC=CC=C54)C",
    default_goal: "针对肺癌 T790M 门控耐药突变，改构克服空间位阻，将 pKd 提升至 ≥ 8.8，并维持良好水溶性与 hERG 心脏安全性",
    target_pkd: 8.8,
    min_admet_score: 68.0,
    max_hemolysis_pct: 5.0,
    tag: "肺癌靶向"
  },
  {
    id: "abl1_t315i_gatekeeper",
    title: "伊马替尼对抗 ABL1(T315I) 守门残基突破",
    scenario: "kinase_escape",
    target_symbol: "ABL1(T315I)",
    target_sequence: "MLEICLKLVGCKSKKGLSSSSSCYLEEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSITKGEKLRVLGYNHNGEWCEAQTKNGQGWVPSNYITPVNSLEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISLRYEGRVYHYRINTASDGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTI",
    baseline_smiles: "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5",
    default_goal: "克服慢粒白血病 T315I 守门突变缺失苏氨酸氧配位的问题，引入刚性碳碳三键或氟代等排体，追求 pKd ≥ 8.5",
    target_pkd: 8.5,
    min_admet_score: 65.0,
    max_hemolysis_pct: 6.0,
    tag: "慢粒白血病"
  },
  {
    id: "safeamp_dual_evolution",
    title: "双靶广谱低溶血抗菌肽协同演化",
    scenario: "safeamp_evolution",
    target_symbol: "Bacterial_Membrane_Kinase",
    target_sequence: "MRRVLILVLFLFVALAQSLVQGKKLAKLAKKWAKLAKKFL",
    baseline_smiles: "KWKKLLKKLLKKLLKKL",
    default_goal: "在增强耐药菌膜靶向与激酶抑制的同时，将哺乳动物红细胞溶血率控制在 < 5.0%，实现双靶平衡",
    target_pkd: 8.2,
    min_admet_score: 75.0,
    max_hemolysis_pct: 4.5,
    tag: "SafeAMP-Dual"
  }
];

export default function AgentStudio() {
  const navigate = useNavigate();
  const { setActiveSmallMolecule, setActiveTarget } = useAppStore();

  const [presets] = useState<PresetScenario[]>(DEFAULT_PRESETS);
  const [selectedPresetId, setSelectedPresetId] = useState<string>("egfr_t790m_escape");

  // Run Configurations
  const [targetSymbol, setTargetSymbol] = useState("EGFR(T790M)");
  const [targetSequence, setTargetSequence] = useState(DEFAULT_PRESETS[0].target_sequence);
  const [baselineSmiles, setBaselineSmiles] = useState(DEFAULT_PRESETS[0].baseline_smiles);
  const [userGoal, setUserGoal] = useState(DEFAULT_PRESETS[0].default_goal);
  const [maxIterations, setMaxIterations] = useState(4);
  const [targetPkd, setTargetPkd] = useState(8.8);
  const [minAdmetScore, setMinAdmetScore] = useState(68.0);
  const [maxHemolysisPct, setMaxHemolysisPct] = useState(5.0);

  // Runtime Agent State
  const [isRunning, setIsRunning] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string>("idle"); // supervisor | designer | dti_auditor | safety_auditor | reporter | idle
  const [currentIteration, setCurrentIteration] = useState(0);
  const [logs, setLogs] = useState<StreamLog[]>([]);
  const [candidates, setCandidates] = useState<CandidateRecord[]>([]);
  const [bestCandidate, setBestCandidate] = useState<CandidateRecord | null>(null);
  const [finalVerdict, setFinalVerdict] = useState<any | null>(null);
  const [copiedSmiles, setCopiedSmiles] = useState(false);

  // Steering Control State (P3 Milestone)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [pauseRequested, setPauseRequested] = useState<boolean>(false);
  const [constraintsVersion, setConstraintsVersion] = useState<number>(1);
  const [maxMwConstraint, setMaxMwConstraint] = useState<string>('');
  const [mustMotifConstraint, setMustMotifConstraint] = useState<string>('');
  const [forbiddenMotifsConstraint, setForbiddenMotifsConstraint] = useState<string>('');
  const [minPkdConstraint, setMinPkdConstraint] = useState<string>('');
  const [steeringToast, setSteeringToast] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const logTerminalEndRef = useRef<HTMLDivElement | null>(null);

  const handlePause = async () => {
    if (!currentTaskId) return;
    setPauseRequested(true);
    try {
      await fetch(`/api/agent/${encodeURIComponent(currentTaskId)}/pause`, { method: 'POST' });
    } catch (err: any) {
      console.error('Failed to request pause:', err);
    }
  };

  const handleResume = async () => {
    if (!currentTaskId) return;
    try {
      await fetch(`/api/agent/${encodeURIComponent(currentTaskId)}/resume`, { method: 'POST' });
      setIsPaused(false);
      setPauseRequested(false);
    } catch (err: any) {
      console.error('Failed to resume:', err);
    }
  };

  const handleApplyConstraints = async () => {
    if (!currentTaskId) return;
    const body: { expected_version: number; constraints: Record<string, any> } = {
      expected_version: constraintsVersion,
      constraints: {}
    };
    if (maxMwConstraint.trim()) {
      body.constraints.max_mw = parseFloat(maxMwConstraint.trim());
    }
    if (mustMotifConstraint.trim()) {
      body.constraints.must_contain_motif = mustMotifConstraint.trim();
    }
    if (forbiddenMotifsConstraint.trim()) {
      body.constraints.forbidden_motifs = forbiddenMotifsConstraint.split(',').map(s => s.trim()).filter(Boolean);
    }
    if (minPkdConstraint.trim()) {
      body.constraints.min_predicted_pkd = parseFloat(minPkdConstraint.trim());
    }

    try {
      const res = await fetch(`/api/agent/${encodeURIComponent(currentTaskId)}/constraints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || '更新约束失败');
      }
      const data = await res.json();
      setConstraintsVersion(data.version);
      setSteeringToast(`硬约束已成功更新至 v${data.version}！正在恢复推演...`);
      setTimeout(() => setSteeringToast(null), 4000);
      await handleResume();
    } catch (err: any) {
      alert(`更新约束失败: ${err.message}`);
    }
  };

  // Auto-scroll logs
  useEffect(() => {
    logTerminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Load Preset
  const handleSelectPreset = (pId: string) => {
    const p = presets.find(item => item.id === pId);
    if (!p) return;
    setSelectedPresetId(pId);
    setTargetSymbol(p.target_symbol);
    setTargetSequence(p.target_sequence);
    setBaselineSmiles(p.baseline_smiles);
    setUserGoal(p.default_goal);
    setTargetPkd(p.target_pkd);
    setMinAdmetScore(p.min_admet_score);
    setMaxHemolysisPct(p.max_hemolysis_pct);
  };

  // Launch A2A Stream
  const handleStartA2APipeline = async () => {
    if (isRunning) return;

    setIsRunning(true);
    setActiveAgent("supervisor");
    setCurrentIteration(0);
    setLogs([]);
    setCandidates([]);
    setBestCandidate(null);
    setFinalVerdict(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch('/api/agent/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario: presets.find(p => p.id === selectedPresetId)?.scenario || "kinase_escape",
          user_goal: userGoal,
          target_symbol: targetSymbol,
          target_sequence: targetSequence,
          baseline_smiles: baselineSmiles,
          max_iterations: Number(maxIterations),
          target_pkd: Number(targetPkd),
          min_admet_score: Number(minAdmetScore),
          max_hemolysis_pct: Number(maxHemolysisPct)
        }),
        signal: controller.signal
      });

      if (!response.ok || !response.body) {
        throw new Error(`SSE 连接失败 (HTTP ${response.status})`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const rawEvent of events) {
          if (!rawEvent.trim()) continue;
          const lines = rawEvent.split('\n');
          let eventType = '';
          let dataStr = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.replace('event: ', '').trim();
            } else if (line.startsWith('data: ')) {
              dataStr = line.replace('data: ', '').trim();
            }
          }

          if (!dataStr) continue;

          try {
            const parsed = JSON.parse(dataStr);

            if (eventType === 'init') {
              if (parsed.task_id) setCurrentTaskId(parsed.task_id);
              if (parsed.constraints_version) setConstraintsVersion(parsed.constraints_version);
              setActiveAgent('supervisor');
              setLogs(prev => [...prev, {
                id: `log_${Date.now()}_init`,
                timestamp: new Date().toLocaleTimeString(),
                agent: 'supervisor',
                thought: parsed.message
              }]);
            } else if (eventType === 'agent_paused') {
              setIsPaused(true);
              setPauseRequested(false);
              if (parsed.constraints_version) setConstraintsVersion(parsed.constraints_version);
              setLogs(prev => [...prev, {
                id: `log_pause_${Date.now()}`,
                timestamp: new Date().toLocaleTimeString(),
                agent: 'supervisor',
                thought: `⏸️ ${parsed.message || '流水线已在轮次边界暂停，等待人工干预硬约束'}`
              }]);
            } else if (eventType === 'agent_resumed') {
              setIsPaused(false);
              setPauseRequested(false);
              if (parsed.constraints_version) setConstraintsVersion(parsed.constraints_version);
              setLogs(prev => [...prev, {
                id: `log_resume_${Date.now()}`,
                timestamp: new Date().toLocaleTimeString(),
                agent: 'supervisor',
                thought: `▶️ ${parsed.message || '流水线已恢复执行，已应用最新硬约束'}`
              }]);
            } else if (eventType === 'task_cancelled') {
              setIsRunning(false);
              setIsPaused(false);
              setPauseRequested(false);
              setLogs(prev => [...prev, {
                id: `log_cancel_${Date.now()}`,
                timestamp: new Date().toLocaleTimeString(),
                agent: 'supervisor',
                thought: `🛑 协同流水线已被取消终止`
              }]);
            } else if (eventType === 'agent_thought') {
              setActiveAgent(parsed.agent || 'supervisor');
              if (parsed.iteration) setCurrentIteration(parsed.iteration);
              setLogs(prev => [...prev, {
                id: `log_${Date.now()}_${Math.random()}`,
                timestamp: new Date().toLocaleTimeString(),
                agent: parsed.agent || 'supervisor',
                thought: parsed.thought,
                iteration: parsed.iteration
              }]);
            } else if (eventType === 'candidate_evaluated') {
              const cand: CandidateRecord = parsed.candidate;
              setCandidates(prev => [...prev, cand]);
              if (parsed.is_best) {
                setBestCandidate(cand);
              }
            } else if (eventType === 'iteration_complete') {
              setCurrentIteration(parsed.iteration);
            } else if (eventType === 'finished') {
              setActiveAgent('idle');
              setFinalVerdict(parsed.verdict);
              if (parsed.verdict?.best_molecule) {
                setBestCandidate(parsed.verdict.best_molecule);
              }
            }
          } catch (e) {
            console.error('SSE JSON 解析异常', e);
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setLogs(prev => [...prev, {
          id: `log_err_${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          agent: 'supervisor',
          thought: `⚠️ 协同流水线异常中断: ${err.message || '未知错误'}`
        }]);
      }
    } finally {
      setIsRunning(false);
      setActiveAgent('idle');
    }
  };

  const handleStopPipeline = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsRunning(false);
    setActiveAgent('idle');
    setLogs(prev => [...prev, {
      id: `log_stop_${Date.now()}`,
      timestamp: new Date().toLocaleTimeString(),
      agent: 'supervisor',
      thought: '🛑 用户已手动终止多智能体推演进程。'
    }]);
  };

  // Jump to DTI Studio with Best Candidate
  const handleJumpToDTI = () => {
    if (!bestCandidate) return;
    setActiveSmallMolecule(bestCandidate.smiles, bestCandidate.id, "A2A Agent Studio");
    setActiveTarget({
      id: targetSymbol,
      standardDisplayName: targetSymbol,
      sequence: targetSequence,
      source: "A2A Agent Studio"
    });
    navigate('/dti', {
      state: {
        drugSmiles: bestCandidate.smiles,
        drugName: bestCandidate.id,
        targetSymbol: targetSymbol,
        targetSequence: targetSequence
      }
    });
  };

  const handleCopySmiles = () => {
    if (!bestCandidate) return;
    navigator.clipboard.writeText(bestCandidate.smiles);
    setCopiedSmiles(true);
    setTimeout(() => setCopiedSmiles(false), 2000);
  };

  // Agent badge style helper
  const getAgentBadge = (agent: string) => {
    switch (agent) {
      case 'supervisor':
        return { label: 'Supervisor 调度中枢', color: 'bg-sky-50 text-sky-700 dark:bg-sky-950/70 dark:text-sky-300 border-sky-300 dark:border-sky-800' };
      case 'designer':
        return { label: 'Molecular Designer 改构', color: 'bg-purple-50 text-purple-700 dark:bg-purple-950/70 dark:text-purple-300 border-purple-300 dark:border-purple-800' };
      case 'dti_auditor':
        return { label: 'DTI Auditor 亲和力门禁', color: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800' };
      case 'safety_auditor':
        return { label: 'Safety Auditor 安全质控', color: 'bg-amber-50 text-amber-700 dark:bg-amber-950/70 dark:text-amber-300 border-amber-300 dark:border-amber-800' };
      case 'reporter':
        return { label: 'Wetlab Reporter 交付单', color: 'bg-rose-50 text-rose-700 dark:bg-rose-950/70 dark:text-rose-300 border-rose-300 dark:border-rose-800' };
      default:
        return { label: 'A2A Agent', color: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-300' };
    }
  };

  return (
    <div className="space-y-5">
      {/* 顶部标题栏与场景预置选择 */}
      <div className="bg-white/90 dark:bg-slate-900/90 p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 via-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Bot size={22} className={isRunning ? 'animate-bounce' : ''} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 font-sans">
                  A2A 跨端多智能体自主协同驾驶舱
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                  LangGraph 拓扑范式 · SSE 实时流
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                调度 MolecularDesigner、DTIAuditor 与 SafetyAuditor 展开无人值守式多目标自主改构
              </p>
            </div>
          </div>

          {/* 运行控制按钮 */}
          <div className="flex items-center gap-2">
            {!isRunning ? (
              <button
                type="button"
                onClick={handleStartA2APipeline}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-bold text-xs shadow-md shadow-sky-500/20 transition-all cursor-pointer"
              >
                <Play size={14} className="fill-white" />
                <span>启动 A2A 协同推演</span>
              </button>
            ) : (
              <div className="flex items-center gap-2">
                {!isPaused ? (
                  <button
                    type="button"
                    onClick={handlePause}
                    disabled={pauseRequested}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs shadow-md transition-all cursor-pointer"
                  >
                    <Pause size={13} className="fill-white" />
                    <span>{pauseRequested ? '等待轮次边界暂停...' : '暂停推演 (人工干预)'}</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleResume}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md transition-all cursor-pointer"
                  >
                    <Play size={13} className="fill-white" />
                    <span>恢复执行</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={handleStopPipeline}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-md shadow-rose-500/20 transition-all cursor-pointer"
                >
                  <Square size={13} className="fill-white" />
                  <span>终止任务</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* 预置经典场景快速选单 */}
        <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 flex items-center gap-1">
            <Zap size={13} className="text-amber-500" />
            <span>精选科研场景：</span>
          </span>
          {presets.map(p => (
            <button
              key={p.id}
              type="button"
              disabled={isRunning}
              onClick={() => handleSelectPreset(p.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                selectedPresetId === p.id
                  ? 'bg-sky-600 text-white shadow-xs font-bold'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              <span>{p.title}</span>
              <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                selectedPresetId === p.id ? 'bg-sky-700/90 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
              }`}>
                {p.tag}
              </span>
            </button>
          ))}
        </div>

        {/* 人工硬约束干预操作面板 (P3 Milestone) */}
        {isPaused && (
          <div className="mt-4 p-4 rounded-xl border border-amber-300 dark:border-amber-700/80 bg-amber-50/70 dark:bg-amber-950/40 text-slate-800 dark:text-slate-200 text-xs space-y-3 animate-in fade-in duration-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sliders size={16} className="text-amber-600 dark:text-amber-400" />
                <span className="font-bold text-amber-900 dark:text-amber-200">
                  流水线已在轮次边界安全暂停 · 人工硬约束干预 (Steering Panel · 当前版本 v{constraintsVersion})
                </span>
              </div>
              <span className="text-[11px] font-mono text-amber-700 dark:text-amber-400">
                代码硬门禁过滤 · 绝不以软提示词放行违规结构
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  分子量上限 (Max MW, Da)
                </label>
                <input
                  type="number"
                  placeholder="例如: 500"
                  value={maxMwConstraint}
                  onChange={(e) => setMaxMwConstraint(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  必须包含母核/基团 (Motif)
                </label>
                <input
                  type="text"
                  placeholder="例如: C#C (刚性炔键)"
                  title="按原子与键拓扑匹配；支持苯/吡啶环等价写法，不支持 SMARTS、括号原子和手性查询"
                  value={mustMotifConstraint}
                  onChange={(e) => setMustMotifConstraint(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  禁用基团/毒性片段 (逗号隔开)
                </label>
                <input
                  type="text"
                  placeholder="例如: Cl, Br"
                  title="按原子与键拓扑匹配，不按字符串包含判断；不支持的查询会被明确拒绝"
                  value={forbiddenMotifsConstraint}
                  onChange={(e) => setForbiddenMotifsConstraint(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  最低预测亲和力 (pKd 门限)
                </label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="例如: 8.0"
                  value={minPkdConstraint}
                  onChange={(e) => setMinPkdConstraint(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-amber-200 dark:border-amber-800">
              <button
                type="button"
                onClick={handleResume}
                className="px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium text-xs hover:bg-slate-300 cursor-pointer"
              >
                直接恢复 (不改动约束)
              </button>
              <button
                type="button"
                onClick={handleApplyConstraints}
                className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-xs cursor-pointer flex items-center gap-1.5"
              >
                <CheckCircle2 size={13} />
                <span>应用新约束并恢复推演 (升至 v{constraintsVersion + 1})</span>
              </button>
            </div>
          </div>
        )}

        {steeringToast && (
          <div className="mt-3 p-2.5 rounded-lg bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-xs flex items-center gap-2">
            <CheckCircle2 size={14} className="text-emerald-600" />
            <span>{steeringToast}</span>
          </div>
        )}
      </div>

      {/* 主工作区分割布局 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* 左栏：参数配置与智能体状态拓扑 (4/12) */}
        <div className="lg:col-span-4 space-y-4">
          
          {/* 1. 多智能体拓扑动态图 (Agent Topology Flow) */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                <Layers size={14} className="text-sky-500" />
                <span>智能体协同状态拓扑</span>
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                isRunning ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/80 dark:text-emerald-300 animate-pulse' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
              }`}>
                {isRunning ? `推演中 (轮次 ${currentIteration}/${maxIterations})` : '就绪待命'}
              </span>
            </div>

            {/* 拓扑节点图 */}
            <div className="space-y-2 pt-1 font-mono text-xs">
              {[
                { key: 'supervisor', title: '1. Supervisor (调度中枢)', desc: '监控全局目标、差额计算与终止判定' },
                { key: 'designer', title: '2. Molecular Designer (变构设计)', desc: '药化规则库变换、空间位阻消除' },
                { key: 'dti_auditor', title: '3. DTI Auditor (亲和力门禁)', desc: '双冷激酶特征交互、pKd / Kd 解算' },
                { key: 'safety_auditor', title: '4. Safety Auditor (安全质控)', desc: 'ADMET 药代雷达、溶血红细胞毒性' },
                { key: 'reporter', title: '5. Wetlab Reporter (交付单)', desc: '帕累托前沿提取、96孔板排单' },
              ].map(node => {
                const isActive = activeAgent === node.key;
                return (
                  <div
                    key={node.key}
                    className={`p-2.5 rounded-lg border transition-all ${
                      isActive 
                        ? 'bg-sky-50/80 dark:bg-sky-950/50 border-sky-400 ring-2 ring-sky-400/40 shadow-xs translate-x-1' 
                        : 'bg-slate-50/60 dark:bg-slate-800/40 border-slate-200/80 dark:border-slate-800/80 opacity-80'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-bold ${isActive ? 'text-sky-600 dark:text-sky-400' : 'text-slate-700 dark:text-slate-300'}`}>
                        {node.title}
                      </span>
                      {isActive && (
                        <span className="w-2 h-2 rounded-full bg-sky-500 animate-ping" />
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                      {node.desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 2. 目标与阈值配置卡片 */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800 space-y-3">
            <span className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <Cpu size={14} className="text-indigo-500" />
              <span>协同优化目标约束</span>
            </span>

            <div className="space-y-2.5 text-xs">
              <div>
                <span className="text-[10px] text-slate-400 block mb-1">靶点代码与描述：</span>
                <input
                  type="text"
                  disabled={isRunning}
                  value={targetSymbol}
                  onChange={(e) => setTargetSymbol(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5 font-mono text-slate-800 dark:text-slate-200"
                />
              </div>

              <div>
                <span className="text-[10px] text-slate-400 block mb-1">科研目标声明：</span>
                <textarea
                  disabled={isRunning}
                  rows={2}
                  value={userGoal}
                  onChange={(e) => setUserGoal(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg p-2 text-xs text-slate-800 dark:text-slate-200"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] text-slate-400 block mb-1">目标 pKd (≥)：</span>
                  <input
                    type="number"
                    step="0.1"
                    disabled={isRunning}
                    value={targetPkd}
                    onChange={(e) => setTargetPkd(Number(e.target.value))}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5 font-mono text-slate-800 dark:text-slate-200"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block mb-1">最大自主迭代轮次：</span>
                  <input
                    type="number"
                    min="1"
                    max="8"
                    disabled={isRunning}
                    value={maxIterations}
                    onChange={(e) => setMaxIterations(Number(e.target.value))}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5 font-mono text-slate-800 dark:text-slate-200"
                  />
                </div>
              </div>

              {/* 2D 初始分子预览 */}
              <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col items-center justify-center">
                <span className="text-[10px] text-slate-400 self-start mb-1 font-mono">初始先导母核结构式：</span>
                <Molecule2DViewer smiles={baselineSmiles} width={240} height={120} />
              </div>
            </div>
          </div>

        </div>

        {/* 右栏：实时推演流与演化卡片 (8/12) */}
        <div className="lg:col-span-8 space-y-4">
          
          {/* 实时推演日志控制台 (Live SSE Terminal) */}
          <div className="bg-slate-950 text-slate-200 rounded-xl border border-slate-800 flex flex-col h-[340px] shadow-sm overflow-hidden">
            <div className="px-4 py-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Terminal size={14} className="text-sky-400" />
                <span className="text-xs font-mono font-bold text-slate-200">
                  A2A 跨端协同推演终端 (Realtime Event Stream)
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-slate-400">
                  {logs.length} 个事件
                </span>
                <button
                  type="button"
                  onClick={() => setLogs([])}
                  className="text-[10px] text-slate-400 hover:text-white"
                >
                  清屏
                </button>
              </div>
            </div>

            <div className="flex-1 p-3.5 overflow-y-auto space-y-2.5 font-mono text-xs no-scrollbar">
              {logs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2">
                  <Terminal size={24} className="opacity-40" />
                  <span>点击上方“启动 A2A 协同推演”按钮，开启智能体多轮闭环自迭代</span>
                </div>
              ) : (
                logs.map(log => {
                  const badge = getAgentBadge(log.agent);
                  return (
                    <div key={log.id} className="leading-relaxed animate-fade-in flex items-start gap-2">
                      <span className="text-[10px] text-slate-500 shrink-0 pt-0.5">
                        [{log.timestamp}]
                      </span>
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border shrink-0 ${badge.color}`}>
                        {badge.label}
                      </span>
                      <span className="text-slate-300 break-words flex-1">
                        {log.thought}
                      </span>
                    </div>
                  );
                })
              )}
              <div ref={logTerminalEndRef} />
            </div>
          </div>

          {/* 最优突破成果与帕累托演化卡片 */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                <Award size={15} className="text-amber-500" />
                <span>当前最优改构先导物 (Best Candidate)</span>
              </span>
              {bestCandidate && (
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300">
                  ΔpKd: +{(bestCandidate.predicted_pkd - (candidates[0]?.predicted_pkd || bestCandidate.predicted_pkd)).toFixed(3)}
                </span>
              )}
            </div>

            {bestCandidate ? (
              <div className="p-3.5 rounded-xl bg-gradient-to-r from-sky-50/50 via-white to-indigo-50/30 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 border border-slate-200/80 dark:border-slate-800 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-black text-sky-600 dark:text-sky-400 font-mono">
                      {bestCandidate.predicted_pkd.toFixed(3)}
                    </span>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-slate-500">预测 pKd</span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Kd ≈ {bestCandidate.predicted_kd_nM < 1000 ? `${bestCandidate.predicted_kd_nM.toFixed(1)} nM` : `${(bestCandidate.predicted_kd_nM/1000).toFixed(2)} μM`}
                      </span>
                    </div>
                  </div>

                  {/* 核心指标矩阵 */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <div className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono">
                      ADMET 评分: <span className="font-bold text-emerald-600">{bestCandidate.admet_score.toFixed(1)}</span>
                    </div>
                    <div className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono">
                      合成难度 SA: <span className="font-bold text-indigo-600">{bestCandidate.sa_score.toFixed(1)}</span>
                    </div>
                    <div 
                      className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono"
                      title={bestCandidate.hemolysis_note || "基于经验规则的未校准启发式估算，非实验实测值"}
                    >
                      膜溶血估算*: <span className="font-bold text-amber-600">{bestCandidate.hemolysis_risk_pct}%</span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-200/80 dark:border-slate-800">
                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-slate-500">变构修饰策略：</span>
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                      {bestCandidate.modifications}
                    </p>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      {bestCandidate.rationale}
                    </p>
                  </div>

                  <div className="flex items-center justify-center p-2 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
                    <Molecule2DViewer smiles={bestCandidate.smiles} width={260} height={120} />
                  </div>
                </div>

                {/* 快捷跳转与导出按钮 */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200/80 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={handleCopySmiles}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
                  >
                    {copiedSmiles ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                    <span>{copiedSmiles ? '已复制 SMILES' : '复制新分子 SMILES'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleJumpToDTI}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-sky-600 hover:bg-sky-500 text-white shadow-xs transition-colors cursor-pointer"
                  >
                    <span>带入 DTI Studio 深入透视 (3D 口袋与激酶谱)</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-8 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-center text-xs text-slate-400">
                暂无推演产物，请在上方启动协同任务
              </div>
            )}
          </div>

          {/* 演化前沿候选群表格 */}
          {candidates.length > 0 && (
            <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800 space-y-2.5">
              <span className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                <Activity size={14} className="text-sky-500" />
                <span>分子演化轨迹序列 ({candidates.length} 款测试分子)</span>
              </span>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 text-[10px]">
                      <th className="py-1.5 px-2">分子编号</th>
                      <th className="py-1.5 px-2">轮次</th>
                      <th className="py-1.5 px-2">变构类型</th>
                      <th className="py-1.5 px-2">预测 pKd</th>
                      <th className="py-1.5 px-2">Kd (nM)</th>
                      <th className="py-1.5 px-2">ADMET</th>
                      <th className="py-1.5 px-2" title="基于经验规则的未校准启发式估算，非实验实测值">膜溶血估算*</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                    {candidates.map((c) => {
                      const isBest = c.id === bestCandidate?.id;
                      return (
                        <tr 
                          key={c.id} 
                          className={`hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors ${
                            isBest ? 'bg-sky-50/60 dark:bg-sky-950/40 font-bold' : ''
                          }`}
                        >
                          <td className="py-1.5 px-2 flex items-center gap-1">
                            {isBest && <span className="text-amber-500">★</span>}
                            <span>{c.id}</span>
                          </td>
                          <td className="py-1.5 px-2">G{c.generation}</td>
                          <td className="py-1.5 px-2 font-sans text-[11px] max-w-[140px] truncate" title={c.modifications}>
                            {c.modifications}
                          </td>
                          <td className="py-1.5 px-2 text-sky-600 dark:text-sky-400 font-bold">
                            {c.predicted_pkd.toFixed(3)}
                          </td>
                          <td className="py-1.5 px-2 text-slate-600 dark:text-slate-300">
                            {c.predicted_kd_nM.toFixed(1)}
                          </td>
                          <td className="py-1.5 px-2 text-emerald-600">
                            {c.admet_score.toFixed(1)}
                          </td>
                          <td className="py-1.5 px-2 text-amber-600">
                            {c.hemolysis_risk_pct}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
