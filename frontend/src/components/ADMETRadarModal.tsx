import React from 'react';
import { 
  X, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  HeartPulse, 
  Droplets, 
  Activity, 
  Zap, 
  Binary, 
  ExternalLink,
  Flame,
  Info
} from 'lucide-react';
import type { ADMETProperties } from '../api/dtiClient';

interface ADMETRadarModalProps {
  isOpen: boolean;
  onClose: () => void;
  admet: ADMETProperties | null;
  moleculeName?: string;
  loading?: boolean;
}

const AXES = [
  { key: 'solubility', label: '水溶性 (LogS)', short: '水溶性' },
  { key: 'permeability', label: '膜透性 (Caco-2)', short: '膜透性' },
  { key: 'herg_safety', label: '心脏安全 (hERG)', short: '心脏安全' },
  { key: 'cyp_stability', label: '代谢稳定 (CYP)', short: '代谢稳定' },
  { key: 'synthesis_sa', label: '合成可达性 (SA)', short: '合成可行' }
];

export const ADMETRadarModal: React.FC<ADMETRadarModalProps> = ({
  isOpen,
  onClose,
  admet,
  moleculeName = '分子样本',
  loading = false
}) => {
  if (!isOpen) return null;

  // Radar geometry configuration
  const size = 300;
  const center = size / 2;
  const radius = 95;
  const numAxes = 5;

  const getCoordinates = (index: number, valueRatio: number) => {
    // Start at top (-pi/2) and go clockwise
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / numAxes;
    const r = radius * Math.max(0.1, Math.min(1.0, valueRatio));
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
      labelX: center + (radius + 24) * Math.cos(angle),
      labelY: center + (radius + 18) * Math.sin(angle)
    };
  };

  const radarScores = admet?.radar_scores || {
    solubility: 50,
    permeability: 50,
    herg_safety: 50,
    cyp_stability: 50,
    synthesis_sa: 50
  };

  const dataPoints = AXES.map((axis, i) => {
    const rawVal = radarScores[axis.key as keyof typeof radarScores] ?? 50;
    const ratio = rawVal / 100;
    return getCoordinates(i, ratio);
  });

  const polygonPath = dataPoints.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  // Grid levels (20%, 40%, 60%, 80%, 100%)
  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0];

  const healthScore = admet ? Math.round(admet.admet_health_score) : 0;
  const healthBadgeColor = 
    healthScore >= 80 ? 'text-emerald-700 bg-emerald-50 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-700' :
    healthScore >= 65 ? 'text-blue-700 bg-blue-50 border-blue-300 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-700' :
    healthScore >= 50 ? 'text-amber-700 bg-amber-50 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-700' :
    'text-rose-700 bg-rose-50 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-700';

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-4xl max-h-[92vh] flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 text-white shadow-md shadow-blue-500/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  ADMET 成药性与药代毒理全景雷达
                </h3>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                  QSAR & Physics-based
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-md">
                评估分子: <span className="font-medium text-slate-700 dark:text-slate-300">{moleculeName}</span>
              </p>
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="关闭 (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="py-24 flex flex-col items-center justify-center gap-4">
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
                正在解算物理化学描述符与 ADMET 药代特性...
              </p>
            </div>
          ) : !admet ? (
            <div className="py-20 text-center text-slate-500">
              暂无成药性数据，请重新触发预测。
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              
              {/* Left Column: 5-D Radar Chart & Overall Index */}
              <div className="lg:col-span-5 flex flex-col items-center justify-center p-5 bg-slate-50 dark:bg-slate-950/50 rounded-xl border border-slate-200 dark:border-slate-800">
                
                {/* Overall Score Badge */}
                <div className="w-full flex items-center justify-between pb-3 mb-2 border-b border-slate-200/80 dark:border-slate-800">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    成药性健康指数 (Health Score)
                  </span>
                  <div className={`px-2.5 py-1 rounded-full text-xs font-bold border ${healthBadgeColor}`}>
                    {healthScore} / 100 分
                  </div>
                </div>

                {/* SVG Radar Chart */}
                <div className="relative flex items-center justify-center my-2">
                  <svg width={size} height={size} className="overflow-visible select-none">
                    <defs>
                      <linearGradient id="radarAreaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.45" />
                        <stop offset="100%" stopColor="#6366f1" stopOpacity="0.20" />
                      </linearGradient>
                      <filter id="radarGlow" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#3b82f6" floodOpacity="0.3" />
                      </filter>
                    </defs>

                    {/* Concentric grid circles / polygons */}
                    {gridLevels.map((lvl, idx) => {
                      const pts = AXES.map((_, i) => {
                        const pt = getCoordinates(i, lvl);
                        return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
                      }).join(' ');
                      return (
                        <polygon
                          key={idx}
                          points={pts}
                          fill={idx % 2 === 0 ? 'currentColor' : 'transparent'}
                          className="text-slate-200/60 dark:text-slate-800/60"
                          stroke="currentColor"
                          strokeWidth="1"
                          strokeDasharray={idx < 4 ? '3 3' : 'none'}
                        />
                      );
                    })}

                    {/* Radial axis lines */}
                    {AXES.map((_, i) => {
                      const outerPt = getCoordinates(i, 1.0);
                      return (
                        <line
                          key={i}
                          x1={center}
                          y1={center}
                          x2={outerPt.x}
                          y2={outerPt.y}
                          className="stroke-slate-300 dark:stroke-slate-700"
                          strokeWidth="1"
                        />
                      );
                    })}

                    {/* Radar polygon */}
                    <polygon
                      points={polygonPath}
                      fill="url(#radarAreaGradient)"
                      stroke="#3b82f6"
                      strokeWidth="2.5"
                      filter="url(#radarGlow)"
                      className="transition-all duration-500 ease-out"
                    />

                    {/* Data dots */}
                    {dataPoints.map((pt, i) => (
                      <circle
                        key={i}
                        cx={pt.x}
                        cy={pt.y}
                        r="4.5"
                        fill="#2563eb"
                        stroke="#ffffff"
                        strokeWidth="2"
                        className="transition-all duration-500 ease-out hover:scale-125"
                      />
                    ))}

                    {/* Axis Labels */}
                    {AXES.map((axis, i) => {
                      const pt = getCoordinates(i, 1.0);
                      const rawVal = Math.round(radarScores[axis.key as keyof typeof radarScores] ?? 50);
                      const isTop = i === 0;
                      const isRight = i === 1 || i === 2;
                      const isLeft = i === 3 || i === 4;
                      return (
                        <g key={i}>
                          <text
                            x={pt.labelX}
                            y={pt.labelY - (isTop ? 6 : 0)}
                            textAnchor={isTop ? 'middle' : isRight ? 'start' : 'end'}
                            dominantBaseline="central"
                            className="text-[11px] font-semibold fill-slate-700 dark:fill-slate-200"
                          >
                            {axis.short}
                          </text>
                          <text
                            x={pt.labelX}
                            y={pt.labelY + 13 - (isTop ? 6 : 0)}
                            textAnchor={isTop ? 'middle' : isRight ? 'start' : 'end'}
                            dominantBaseline="central"
                            className="text-[10px] font-mono fill-blue-600 dark:fill-blue-400 font-bold"
                          >
                            {rawVal}分
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </div>

                <div className="w-full mt-4 text-[11px] text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200/80 dark:border-slate-800 text-center">
                  💡 五维各轴按 0~100 分归一化映射，外扩面积越大代表该化合物成药综合均衡性越好。
                </div>
              </div>

              {/* Right Column: Detailed ADMET Profiles & Pharmacological Annotations */}
              <div className="lg:col-span-7 space-y-4">
                
                {/* 1. Cardiac & Toxicity Alert (hERG) */}
                <div className={`p-4 rounded-xl border transition-colors ${
                  admet.herg_risk === 'low' ? 'bg-emerald-50/60 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-800' :
                  admet.herg_risk === 'medium' ? 'bg-amber-50/60 border-amber-200 dark:bg-amber-950/20 dark:border-amber-800' :
                  'bg-rose-50/60 border-rose-200 dark:bg-rose-950/20 dark:border-rose-800'
                }`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <HeartPulse className={`w-4 h-4 ${
                        admet.herg_risk === 'low' ? 'text-emerald-600' :
                        admet.herg_risk === 'medium' ? 'text-amber-600' : 'text-rose-600'
                      }`} />
                      <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                        hERG 钾离子通道阻断与心脏安全
                      </h4>
                    </div>
                    <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                      admet.herg_risk === 'low' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200' :
                      admet.herg_risk === 'medium' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200' :
                      'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-200'
                    }`}>
                      {admet.herg_risk === 'low' ? '低心脏毒性 (Safe)' :
                       admet.herg_risk === 'medium' ? '中度预警 (Caution)' : '高阻断风险 (High Risk)'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300">
                    {admet.herg_label}
                  </p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    若 pIC50 &ge; 6.0 (IC50 &lt; 1 µM) 易诱发 QT 间期延长与尖端扭转型室速 (TdP)。
                  </p>
                </div>

                {/* 2. Absorption & Solubility Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  
                  {/* Delaney ESOL Aqueous Solubility */}
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                        <Droplets className="w-3.5 h-3.5 text-blue-500" />
                        水溶解度 (Delaney ESOL)
                      </div>
                      <span className={`text-[11px] font-bold ${
                        admet.solubility_tier === 'high' ? 'text-emerald-600' :
                        admet.solubility_tier === 'moderate' ? 'text-blue-600' : 'text-amber-600'
                      }`}>
                        LogS {admet.solubility_logs}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-300 font-medium">
                      {admet.solubility_label}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      理论溶解浓度: 约 {admet.solubility_mg_ml} mg/mL
                    </div>
                  </div>

                  {/* Caco-2 Membrane Permeability */}
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                        <Activity className="w-3.5 h-3.5 text-indigo-500" />
                        Caco-2 膜表观通透性
                      </div>
                      <span className="text-[11px] font-bold text-indigo-600 dark:text-indigo-400">
                        {admet.caco2_papp} × 10⁻⁶ cm/s
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-300 font-medium">
                      {admet.caco2_label}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      反映小肠上皮被动与载体辅助吸收能力
                    </div>
                  </div>

                  {/* Clark Blood-Brain Barrier (LogBB) */}
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                        <Zap className="w-3.5 h-3.5 text-amber-500" />
                        血脑屏障透过 (Clark LogBB)
                      </div>
                      <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                        LogBB {admet.log_bb}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-300 font-medium">
                      {admet.bbb_label}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      {admet.bbb_tier === 'cns_penetrant' ? '易穿透血脑屏障 (适用脑转移)' : '外周分布型 (低 CNS 副作用)'}
                    </div>
                  </div>

                  {/* Cytochrome P450 (CYP) Metabolism */}
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
                        <Binary className="w-3.5 h-3.5 text-emerald-500" />
                        CYP450 药物相互作用 (DDI)
                      </div>
                      <span className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                        3A4 / 2D6
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-300 font-medium">
                      {admet.cyp3a4_label}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      {admet.cyp2d6_label}
                    </div>
                  </div>

                </div>

                {/* Medicinal Chemistry Optimization Insights */}
                <div className="p-4 rounded-xl bg-blue-50/60 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/60 text-xs">
                  <div className="flex items-center gap-1.5 font-bold text-blue-900 dark:text-blue-300 mb-1.5">
                    <Info className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                    药化改构指导建议 (Medicinal Chemistry Recommendation)
                  </div>
                  <ul className="space-y-1 text-slate-600 dark:text-slate-300 text-[11px] list-disc list-inside">
                    {admet.herg_risk !== 'low' && (
                      <li>
                        <strong className="text-rose-600 dark:text-rose-400">优化建议 (排毒):</strong> 检测到具有潜在的心脏通道静电吸引中心，建议降低骨架脂溶性或将强碱性胺替换为更弱碱性的氧杂环丁烷/环丙基胺。
                      </li>
                    )}
                    {admet.solubility_tier === 'poor' && (
                      <li>
                        <strong className="text-amber-600 dark:text-amber-400">优化建议 (增溶):</strong> Delaney LogS 偏低，可通过引入吗啉环、极性磺酰基或共价弹头外围极性片段提升水相暴露量。
                      </li>
                    )}
                    {admet.herg_risk === 'low' && admet.solubility_tier !== 'poor' && (
                      <li>
                        <strong className="text-emerald-600 dark:text-emerald-400">良好评价:</strong> 分子在极性表面积、亲脂性与心脏毒性风险上具有良好的平衡度，适宜作为先导分子进一步推进行为学试验。
                      </li>
                    )}
                  </ul>
                </div>

                {/* Raw SMILES copy bar */}
                <div className="flex items-center justify-between p-2.5 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-mono text-slate-600 dark:text-slate-300 truncate">
                  <span className="truncate pr-2">{admet.smiles}</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(admet.smiles)}
                    className="px-2 py-1 text-[11px] font-sans font-medium bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-50 transition-colors shrink-0"
                  >
                    复制 SMILES
                  </button>
                </div>

              </div>

            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 flex items-center justify-between">
          <div className="text-xs text-slate-500 dark:text-slate-400">
            Powered by Delaney ESOL · Clark LogBB · QSAR Cardiac Safety Engine
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-bold text-white bg-slate-800 hover:bg-slate-900 dark:bg-slate-700 dark:hover:bg-slate-600 rounded-lg transition-colors shadow-sm"
          >
            完成查看
          </button>
        </div>
      </div>
    </div>
  );
};
