import React, { useState, useEffect, useRef } from 'react';
import { 
  Zap, 
  Download, 
  Sparkles, 
  Check, 
  Copy, 
  PlusCircle, 
  Dna, 
  AlertCircle, 
  HelpCircle,
  Layers,
  ArrowRight
} from 'lucide-react';
import { useAppStore } from '../store/useAppStore';

interface ResiduePoint {
  pos: number;
  aa: string;
  angle_deg: number;
  x: number;
  y: number;
  cx?: number;
  cy?: number;
  category: string;
  color: string;
  hydrophobicity: number;
  charge: number;
}

interface HelicalWheelData {
  sequence: string;
  length: number;
  residues: ResiduePoint[];
  hydrophobic_moment: number;
  moment_angle_deg: number;
  hydrophobic_angle_span: number;
  net_charge: number;
  mean_hydrophobicity: number;
  projection_model: string;
  hydrophobicity_scale: string;
  disclaimer: string;
}

const PRESET_PEPTIDES = [
  {
    name: '蜂毒素 (Melittin)',
    sequence: 'GIGAVLKVLTTGLPALISWIKRKRQQ',
    desc: '典型强两亲性 α-螺旋抗菌肽，具有显著的亲水-疏水截面偏向性'
  },
  {
    name: '爪蟾抗菌肽 (Magainin 2)',
    sequence: 'GIGKFLHSAKKFGKAFVGEIMNS',
    desc: '经典两亲性天然防御肽，膜作用两亲螺旋模型分子'
  },
  {
    name: '人源抗菌肽 (LL-37 全长)',
    sequence: 'LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES',
    desc: '人体天然防御肽，包含多个带电赖氨酸/精氨酸碱性残基与疏水簇'
  }
];

export default function HelicalWheelStudio() {
  const { activeEntity, setActivePeptide, addToCart } = useAppStore();

  const [sequenceInput, setSequenceInput] = useState<string>('GIGAVLKVLTTGLPALISWIKRKRQQ');
  const [wheelData, setWheelData] = useState<HelicalWheelData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [copiedSeq, setCopiedSeq] = useState<boolean>(false);
  const [cartSuccess, setCartSuccess] = useState<boolean>(false);

  const svgRef = useRef<SVGSVGElement | null>(null);

  // Sync with active peptide in store
  useEffect(() => {
    if (activeEntity?.kind === 'peptide' && activeEntity.sequence) {
      setSequenceInput(activeEntity.sequence);
      handleCalculateWheel(activeEntity.sequence);
    } else {
      handleCalculateWheel(sequenceInput);
    }
  }, []);

  const handleCalculateWheel = async (seqToRun?: string) => {
    const raw = (seqToRun || sequenceInput).trim().toUpperCase();
    if (raw.length < 3) {
      setErrorMsg('多肽序列过短，至少需要 3 个氨基酸残基进行螺旋轮投影。');
      return;
    }

    setErrorMsg(null);
    setIsLoading(true);

    try {
      const res = await fetch('/api/helical_wheel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sequence: raw }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `螺旋轮计算请求失败 (HTTP ${res.status})`);
      }

      const data: HelicalWheelData = await res.json();

      // Compute display radius coordinates for multi-turn alpha-helix
      // Every 18 residues completes one full turn around wheel; step radius inward slightly to avoid overlapping
      const mappedResidues = data.residues.map((r, idx) => {
        const turnRing = Math.floor(idx / 18);
        const radius = Math.max(50, 120 - turnRing * 25);
        const angleRad = (r.angle_deg * Math.PI) / 180;
        return {
          ...r,
          cx: 160 + radius * Math.sin(angleRad),
          cy: 160 - radius * Math.cos(angleRad),
        };
      });

      setWheelData({
        ...data,
        residues: mappedResidues,
      });

      // Update active entity in store
      setActivePeptide(raw, `Peptide-${raw.slice(0, 6)}`);
    } catch (err: any) {
      setErrorMsg(err.message || '螺旋轮计算异常，请检查序列是否包含合法氨基酸。');
      setWheelData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportPNG = () => {
    if (!svgRef.current || !wheelData) return;
    const svgElement = svgRef.current;
    const svgString = new XMLSerializer().serializeToString(svgElement);
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 640;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, 640, 640);
      const pngUrl = canvas.toDataURL('image/png');
      const downloadLink = document.createElement('a');
      downloadLink.href = pngUrl;
      downloadLink.download = `HelicalWheel_${wheelData.sequence.slice(0, 8)}_${Date.now()}.png`;
      downloadLink.click();
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  const handleSaveToCart = () => {
    if (!wheelData) return;
    addToCart({
      sequence: wheelData.sequence,
      name: `Peptide-${wheelData.sequence.slice(0, 6)}`,
      kind: 'peptide',
      item_type: 'peptide',
      tsi: wheelData.hydrophobic_moment,
    });
    setCartSuccess(true);
    setTimeout(() => setCartSuccess(false), 2000);
  };

  const copySequence = () => {
    if (!wheelData) return;
    navigator.clipboard.writeText(wheelData.sequence);
    setCopiedSeq(true);
    setTimeout(() => setCopiedSeq(false), 2000);
  };

  // Eisenberg hydrophobic moment vector arrow
  const cx0 = 160;
  const cy0 = 160;
  const momentLen = wheelData ? Math.min(100, Math.max(25, wheelData.hydrophobic_moment * 180)) : 50;
  const momentRad = wheelData ? (wheelData.moment_angle_deg * Math.PI) / 180 : 0;
  const arrowX = cx0 + momentLen * Math.sin(momentRad);
  const arrowY = cy0 - momentLen * Math.cos(momentRad);

  return (
    <div className="space-y-6 animate-in fade-in duration-300 pb-16">
      
      {/* 1. Header Banner */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-600 flex items-center justify-center text-white shadow-sm shrink-0">
            <Zap size={22} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                多肽螺旋轮构象与两亲性投影工作台
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 font-bold font-mono">
                Schiffer-Edmundson 100°
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              基于每残基 100° 的 α-螺旋投影几何模型，计算 Eisenberg 疏水力矩（μH）、净电荷与两亲截面分布。
            </p>
          </div>
        </div>

        {wheelData && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleSaveToCart}
              className="px-3.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              {cartSuccess ? <Check size={14} className="text-emerald-500" /> : <PlusCircle size={14} />}
              <span>{cartSuccess ? '已存入暂存库' : '存入分子库'}</span>
            </button>
            <button
              type="button"
              onClick={handleExportPNG}
              className="px-3.5 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Download size={14} />
              <span>导出高分 PNG 图</span>
            </button>
          </div>
        )}
      </div>

      {/* 2. Scientific Disclaimer Banner */}
      <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5">
        <AlertCircle size={16} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="font-semibold block mb-0.5">科学投影假设与构象边界说明：</strong>
          螺旋轮属于理想化的二维物理化学投影方法（假设多肽处于连续规则 α-螺旋状态）。径向分环仅用于防止长多肽残基视觉重叠，<strong>绝不代表多肽实际折叠三维空间坐标或真实的跨膜离子通道机制</strong>。
        </div>
      </div>

      {/* 3. Main Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Control Panel (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs space-y-4">
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider font-mono flex items-center gap-1.5">
              <Dna size={14} className="text-amber-500" />
              <span>多肽输入与预设序列 (Sequence Input)</span>
            </h3>

            {/* Sequence Textarea */}
            <div>
              <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                多肽单字母序列 (AA Sequence, 3-100 残基)
              </label>
              <textarea
                rows={3}
                value={sequenceInput}
                onChange={e => setSequenceInput(e.target.value.toUpperCase())}
                placeholder="例如：GIGAVLKVLTTGLPALISWIKRKRQQ"
                className="w-full text-xs p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-mono tracking-wider focus-ring"
              />
              <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                <span>当前长度: <strong className="font-mono text-slate-700 dark:text-slate-300">{sequenceInput.trim().length}</strong> 残基</span>
                <button
                  type="button"
                  onClick={() => setSequenceInput('')}
                  className="hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                >
                  清空
                </button>
              </div>
            </div>

            {errorMsg && (
              <div className="p-2.5 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-300 flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Run Button */}
            <button
              type="button"
              onClick={() => handleCalculateWheel()}
              disabled={isLoading}
              className="w-full py-2.5 px-4 rounded-xl font-bold text-xs bg-amber-500 hover:bg-amber-600 text-white shadow-xs flex items-center justify-center gap-2 transition-all cursor-pointer focus-ring disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>正在解算螺旋轮空间两亲性...</span>
                </>
              ) : (
                <>
                  <Zap size={14} />
                  <span>计算螺旋轮投影与疏水力矩 (Calculate Helical Wheel)</span>
                </>
              )}
            </button>

            {/* Preset Peptides */}
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-2">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider font-mono block">
                经典两亲抗菌肽基准 (Presets)
              </span>
              <div className="space-y-1.5">
                {PRESET_PEPTIDES.map(p => (
                  <button
                    key={p.name}
                    type="button"
                    onClick={() => {
                      setSequenceInput(p.sequence);
                      handleCalculateWheel(p.sequence);
                    }}
                    className="w-full text-left p-2.5 rounded-xl border border-slate-200/80 dark:border-slate-800 hover:border-amber-300 dark:hover:border-amber-700/60 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-amber-50/30 dark:hover:bg-amber-950/10 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-amber-600 dark:group-hover:text-amber-400">
                        {p.name}
                      </span>
                      <ArrowRight size={12} className="text-slate-400 group-hover:text-amber-500 transition-transform group-hover:translate-x-0.5" />
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono block mt-0.5 truncate">
                      {p.sequence}
                    </span>
                  </button>
                ))}
              </div>
            </div>

          </div>

          {/* Color Legend Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-xs space-y-2">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider font-mono block">
              Kyte-Doolittle 残基色彩图例
            </span>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#38bdf8]" />
                <span className="text-slate-600 dark:text-slate-400">碱性阳离子 (K, R, H)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#f43f5e]" />
                <span className="text-slate-600 dark:text-slate-400">酸性阴离子 (D, E)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#f59e0b]" />
                <span className="text-slate-600 dark:text-slate-400">强疏水性 (I, V, L, F, C, M, A)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#10b981]" />
                <span className="text-slate-600 dark:text-slate-400">中性极性 (S, T, Y, N, Q, W, P, G)</span>
              </div>
            </div>
          </div>

        </div>

        {/* Right Canvas: Helical Wheel & Metric Dashboard (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          
          {wheelData && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-1">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">Eisenberg 疏水力矩</span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-bold font-mono text-amber-500">
                    {wheelData.hydrophobic_moment.toFixed(3)}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">μH</span>
                </div>
                <span className="text-[10px] text-slate-500 block">
                  {wheelData.hydrophobic_moment >= 0.35 ? '强两亲性螺旋' : wheelData.hydrophobic_moment >= 0.2 ? '中等两亲性' : '弱两亲性/非两亲'}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-1">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">净电荷 (pH 7.4)</span>
                <div className="flex items-baseline gap-1">
                  <span className={`text-2xl font-bold font-mono ${wheelData.net_charge > 0 ? 'text-sky-500' : wheelData.net_charge < 0 ? 'text-rose-500' : 'text-slate-600'}`}>
                    {wheelData.net_charge > 0 ? `+${wheelData.net_charge.toFixed(1)}` : wheelData.net_charge.toFixed(1)}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">e</span>
                </div>
                <span className="text-[10px] text-slate-500 block">阳离子性有利于膜识别</span>
              </div>

              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-1">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">平均疏水性 (KD)</span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-bold font-mono text-slate-800 dark:text-slate-200">
                    {wheelData.mean_hydrophobicity.toFixed(2)}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">H</span>
                </div>
                <span className="text-[10px] text-slate-500 block">Kyte-Doolittle 均值</span>
              </div>

              <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-1">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">力矩指向角度</span>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-bold font-mono text-indigo-500">
                    {wheelData.moment_angle_deg.toFixed(0)}°
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 block">疏水面跨度 ~{wheelData.hydrophobic_angle_span}°</span>
              </div>
            </div>
          )}

          {/* Interactive Wheel SVG Canvas */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs flex flex-col items-center justify-center min-h-[440px] relative overflow-hidden">
            
            {isLoading ? (
              <div className="py-24 text-center space-y-3">
                <div className="w-8 h-8 border-3 border-amber-500/20 border-t-amber-500 rounded-full animate-spin mx-auto" />
                <span className="text-xs text-slate-500 font-mono">计算残基极坐标与空间几何投影中...</span>
              </div>
            ) : !wheelData ? (
              <div className="py-24 text-center text-slate-400 text-xs">
                请输入多肽序列后点击“计算螺旋轮投影”
              </div>
            ) : (
              <div className="w-full max-w-[420px] aspect-square flex items-center justify-center p-2">
                <svg 
                  ref={svgRef}
                  viewBox="0 0 320 320" 
                  className="w-full h-full select-none"
                >
                  <defs>
                    <marker id="wheel-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                    </marker>
                  </defs>

                  {/* Concentric Guide Circles */}
                  <circle cx="160" cy="160" r="120" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3,3" className="dark:stroke-slate-800" />
                  <circle cx="160" cy="160" r="95" fill="none" stroke="#e2e8f0" strokeWidth="0.8" strokeDasharray="2,2" className="dark:stroke-slate-800/60" />
                  <circle cx="160" cy="160" r="70" fill="none" stroke="#f1f5f9" strokeWidth="0.8" strokeDasharray="2,2" className="dark:stroke-slate-800/40" />
                  <circle cx="160" cy="160" r="3" fill="#94a3b8" />

                  {/* 18-Spoke Angular Rays */}
                  {Array.from({ length: 18 }).map((_, s) => {
                    const rayAngle = (s * 20 * Math.PI) / 180;
                    const rx = 160 + 120 * Math.sin(rayAngle);
                    const ry = 160 - 120 * Math.cos(rayAngle);
                    return (
                      <line 
                        key={s} 
                        x1="160" y1="160" x2={rx} y2={ry} 
                        stroke="#f1f5f9" strokeWidth="0.7" 
                        className="dark:stroke-slate-800/30" 
                      />
                    );
                  })}

                  {/* Consecutive Backbone Connection Lines */}
                  {wheelData.residues.map((r, i) => {
                    if (i === 0) return null;
                    const prev = wheelData.residues[i - 1];
                    return (
                      <line
                        key={`line-${i}`}
                        x1={prev.cx}
                        y1={prev.cy}
                        x2={r.cx}
                        y2={r.cy}
                        stroke="#94a3b8"
                        strokeWidth="1"
                        opacity="0.4"
                      />
                    );
                  })}

                  {/* Eisenberg Hydrophobic Moment Vector Arrow */}
                  <line
                    x1={cx0}
                    y1={cy0}
                    x2={arrowX}
                    y2={arrowY}
                    stroke="#f59e0b"
                    strokeWidth="2.5"
                    markerEnd="url(#wheel-arrow)"
                  />
                  <text 
                    x={arrowX + 8} 
                    y={arrowY + 4} 
                    fill="#f59e0b" 
                    fontSize="9" 
                    fontWeight="bold" 
                    fontFamily="monospace"
                  >
                    μH ({wheelData.hydrophobic_moment.toFixed(2)})
                  </text>

                  {/* Residue Circles */}
                  {wheelData.residues.map((r) => (
                    <g key={`res-${r.pos}`} className="cursor-pointer">
                      <circle
                        cx={r.cx}
                        cy={r.cy}
                        r="11"
                        fill={r.color}
                        stroke="#ffffff"
                        strokeWidth="1.5"
                        className="shadow-sm"
                      />
                      <text
                        x={r.cx}
                        y={(r.cy ?? 0) + 3.5}
                        fill="#ffffff"
                        fontSize="9"
                        fontWeight="bold"
                        fontFamily="monospace"
                        textAnchor="middle"
                      >
                        {r.aa}
                      </text>
                      <text
                        x={(r.cx ?? 0) + ((r.cx ?? 0) > 160 ? 13 : -13)}
                        y={(r.cy ?? 0) + 3}
                        fill="#64748b"
                        fontSize="7"
                        fontFamily="monospace"
                        textAnchor={(r.cx ?? 0) > 160 ? 'start' : 'end'}
                      >
                        {r.pos}
                      </text>
                    </g>
                  ))}
                </svg>
              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
