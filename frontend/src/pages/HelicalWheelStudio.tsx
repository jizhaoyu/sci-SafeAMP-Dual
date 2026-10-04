import React, { useState, useEffect, useRef } from 'react';
import { Target, Download, Zap, RefreshCw, ShoppingCart, Activity, FileText } from 'lucide-react';
import { apiClient, errorMessage } from '../api/client';
import { useAppStore } from '../store/useAppStore';
import { useNavigate } from 'react-router-dom';

interface ResiduePoint {
  idx: number;
  residue: string;
  angle_deg: number;
  cx: number;
  cy: number;
  category: string;
  color: string;
}

interface HelicalWheelData {
  sequence: string;
  length: number;
  residues: ResiduePoint[];
  hydrophobic_moment: number;
  moment_angle_deg: number;
  net_charge: number;
  mean_hydrophobicity: number;
}

export default function HelicalWheelStudio() {
  const { activeSequence, addToCart, setActivePeptide } = useAppStore();
  const [seq, setSeq] = useState(activeSequence);
  const [loading, setLoading] = useState(false);
  const [wheelData, setWheelData] = useState<HelicalWheelData | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const svgRef = useRef<SVGSVGElement | null>(null);
  const navigate = useNavigate();

  const handleFetchWheel = async (targetSeq: string) => {
    const cleaned = targetSeq.trim().replace(/\s/g, '').toUpperCase();
    if (!cleaned) {
      setErrorMsg('请输入有效的多肽序列');
      return;
    }

    setErrorMsg('');
    setLoading(true);
    try {
      const res = await apiClient.post<HelicalWheelData>('/api/helical_wheel', {
        sequence: cleaned
      });
      const raw = res.data as any;
      setWheelData({ ...raw, residues: raw.residues.map((r: any) => {
        const radius = 120 - 30 * Math.floor((r.pos - 1) / 18);
        const angle = r.angle_deg * Math.PI / 180;
        return { ...r, idx: r.pos - 1, residue: r.aa, cx: 160 + radius * Math.sin(angle), cy: 160 - radius * Math.cos(angle) };
      }) });
    } catch (err: any) {
      setWheelData(null);
      setErrorMsg(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeSequence) {
      // oxlint-disable-next-line react/set-state-in-effect
      setSeq(activeSequence);
      handleFetchWheel(activeSequence);
    }
  }, [activeSequence]);

  const handleExportPNG = () => {
    if (!svgRef.current) return;
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
      downloadLink.download = `HelicalWheel_${seq.slice(0, 8)}_${Date.now()}.png`;
      downloadLink.click();
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  // Eisenberg moment vector endpoints
  const cx0 = 160;
  const cy0 = 160;
  const momentLen = wheelData ? Math.min(100, Math.max(25, wheelData.hydrophobic_moment * 180)) : 50;
  const momentRad = wheelData ? (wheelData.moment_angle_deg * Math.PI) / 180 : 0;
  const arrowX = cx0 + momentLen * Math.sin(momentRad);
  const arrowY = cy0 - momentLen * Math.cos(momentRad);

  return (
    <div className="flex flex-col gap-6">
      {/* Studio Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <Zap className="text-amber-500" size={22} />
          螺旋轮构象与两亲性投影室 (Schiffer-Edmundson Helical Wheel Studio)
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          按每残基 100° 的理想螺旋假设绘制理化属性投影；每 18 个残基换一显示环以避免重叠，径向层仅用于排版，不代表真实结构或膜作用机制。
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Controls & Properties */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="lab-panel p-4 flex flex-col gap-3">
            <span className="lab-label">输入分析序列</span>
            
            <div className="flex gap-2">
              <input
                type="text"
                value={seq}
                onChange={(e) => setSeq(e.target.value)}
                placeholder="输入多肽序列 (例如 GIGAVLKVLTTGLPALISWIKRKRQQ)"
                className="lab-input font-mono text-xs uppercase flex-1"
              />
              <button
                type="button"
                onClick={() => handleFetchWheel(seq)}
                disabled={loading}
                className="btn-lab-primary px-3 py-2 text-xs flex items-center gap-1.5 whitespace-nowrap"
              >
                {loading ? <RefreshCw size={14} className="animate-spin" /> : <Target size={14} />}
                <span>投影 (Project)</span>
              </button>
            </div>

            {errorMsg && (
              <div className="text-xs text-rose-600 bg-rose-50 dark:bg-rose-950/40 p-2.5 rounded border border-rose-200 dark:border-rose-900">
                {errorMsg}
              </div>
            )}
          </div>

          {/* Physicochemical Property Cards */}
          {wheelData && (
            <div className="lab-panel p-4 flex flex-col gap-3">
              <span className="lab-label">生物物理特征计算矩阵</span>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500">序列全长 (Length)</div>
                  <div className="text-base font-bold font-mono text-slate-800 dark:text-slate-200">{wheelData.length} AA</div>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500">净电荷 (pH 7.4)</div>
                  <div className={`text-base font-bold font-mono ${wheelData.net_charge >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-rose-600 dark:text-rose-400'}`}>
                    {wheelData.net_charge > 0 ? `+${wheelData.net_charge.toFixed(1)}` : wheelData.net_charge.toFixed(1)}
                  </div>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500">两亲性力矩 (Eisenberg μH)</div>
                  <div className="text-base font-bold font-mono text-amber-600 dark:text-amber-400">
                    {wheelData.hydrophobic_moment.toFixed(3)}
                  </div>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-500">平均疏水性 (Kyte-Doolittle)</div>
                  <div className="text-base font-bold font-mono text-slate-800 dark:text-slate-200">
                    {wheelData.mean_hydrophobicity.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    addToCart({
                      sequence: wheelData.sequence,
                      name: 'Wheel-Analyzed',
                      p_amp: 0.9,
                      p_hemo: 0.5,
                      tsi: 0.7,
                    });
                  }}
                  className="btn-lab-secondary text-xs px-2.5 py-1.5 flex items-center gap-1"
                >
                  <ShoppingCart size={13} /> 存入候选库
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActivePeptide(wheelData.sequence, 'Wheel-Target');
                    navigate('/evolution');
                  }}
                  className="btn-lab-secondary text-xs px-2.5 py-1.5 flex items-center gap-1 text-purple-600 dark:text-purple-400"
                >
                  <Activity size={13} /> 送去突变
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActivePeptide(wheelData.sequence, 'Wheel-Target');
                    navigate('/report');
                  }}
                  className="btn-lab-secondary text-xs px-2.5 py-1.5 flex items-center gap-1 text-blue-600 dark:text-blue-400"
                >
                  <FileText size={13} /> 评估报告
                </button>
              </div>
            </div>
          )}

          {/* Color Legend */}
          <div className="lab-panel p-4 flex flex-col gap-2 text-xs">
            <span className="lab-label">残基极性与电荷着色规范</span>
            <div className="grid grid-cols-2 gap-2 text-slate-600 dark:text-slate-400">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: '#38bdf8' }}></span>
                <span>碱性正电 (Basic: R, K, H)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: '#f43f5e' }}></span>
                <span>酸性负电 (Acidic: D, E)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: '#f59e0b' }}></span>
                <span>强疏水性 (Hydrophobic: L, I, V, F, W)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: '#fbbf24' }}></span>
                <span>中度疏水 (Moderate: A, M, C)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: '#10b981' }}></span>
                <span>极性不带电 (Polar: S, T, N, Q, Y, G, P)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Section: SVG Helical Wheel Canvas */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="lab-panel p-5 flex flex-col items-center justify-center min-h-[440px] relative">
            <div className="w-full flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2 mb-2">
              <span className="lab-label">Schiffer-Edmundson 100° 二维矢量投影图</span>
              <button
                type="button"
                onClick={handleExportPNG}
                disabled={!wheelData}
                className="btn-lab-secondary text-xs px-2.5 py-1 flex items-center gap-1.5 disabled:opacity-40"
              >
                <Download size={13} /> 导出高清 PNG
              </button>
            </div>

            {loading ? (
              <div className="py-24 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
                <RefreshCw size={24} className="animate-spin text-amber-500" />
                <span className="text-xs">计算残基空间角与两亲性力矩中...</span>
              </div>
            ) : !wheelData ? (
              <div className="py-24 text-center text-slate-400 text-xs">
                请输入多肽序列后点击“投影”以生成螺旋轮。
              </div>
            ) : (
              <div className="w-full max-w-[420px] aspect-square flex items-center justify-center p-2">
                <svg 
                  ref={svgRef}
                  viewBox="0 0 320 320" 
                  className="w-full h-full select-none"
                >
                  <defs>
                    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                    </marker>
                  </defs>

                  {/* Concentric Guide Circles */}
                  <circle cx="160" cy="160" r="120" fill="none" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="3,3" className="dark:stroke-slate-800" />
                  <circle cx="160" cy="160" r="70" fill="none" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="2,2" className="dark:stroke-slate-800/60" />
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
                        className="dark:stroke-slate-800/40" 
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
                        opacity="0.5"
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
                    markerEnd="url(#arrow)"
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
                    <g key={`res-${r.idx}`} className="cursor-pointer">
                      <circle
                        cx={r.cx}
                        cy={r.cy}
                        r="11"
                        fill={r.color}
                        stroke="#ffffff"
                        strokeWidth="1.5"
                        className="shadow-md"
                      />
                      <text
                        x={r.cx}
                        y={r.cy + 3.5}
                        fill="#ffffff"
                        fontSize="9"
                        fontWeight="bold"
                        fontFamily="monospace"
                        textAnchor="middle"
                      >
                        {r.residue}
                      </text>
                      <text
                        x={r.cx + (r.cx > 160 ? 13 : -13)}
                        y={r.cy + 3}
                        fill="#64748b"
                        fontSize="7"
                        fontFamily="monospace"
                        textAnchor={r.cx > 160 ? 'start' : 'end'}
                      >
                        {r.idx + 1}
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
