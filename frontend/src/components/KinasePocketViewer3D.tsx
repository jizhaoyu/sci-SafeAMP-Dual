import React, { useEffect, useRef, useState, useCallback } from 'react';
import { 
  RotateCcw, 
  Maximize2, 
  Minimize2, 
  Camera, 
  Layers, 
  Play, 
  Pause, 
  Eye, 
  Sparkles, 
  Info, 
  Loader2, 
  Activity,
  Flame,
  CheckCircle2
} from 'lucide-react';
import { fetchKinasePocketStructure, type PocketStructureResult } from '../api/dtiClient';

declare global {
  interface Window {
    $3Dmol?: any;
  }
}

interface KinasePocketViewer3DProps {
  targetName?: string;
  drugName?: string;
  drugSmiles?: string;
  className?: string;
  autoFetch?: boolean;
}

export const KinasePocketViewer3D: React.FC<KinasePocketViewer3DProps> = ({
  targetName = 'ABL1',
  drugName = 'Dasatinib',
  drugSmiles,
  className = '',
  autoFetch = true
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const [data, setData] = useState<PocketStructureResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isSpinning, setIsSpinning] = useState(false);
  const [renderMode, setRenderMode] = useState<'cartoon' | 'surface' | 'stick'>('cartoon');
  const [showHbonds, setShowHbonds] = useState(true);
  const [showLabels, setShowLabels] = useState(true);

  // Load 3Dmol script dynamically if not yet ready
  const ensure3Dmol = useCallback((): Promise<any> => {
    return new Promise((resolve, reject) => {
      if (window.$3Dmol) {
        resolve(window.$3Dmol);
        return;
      }
      const existing = document.querySelector('script[src="/vendor/3Dmol-min.js"]');
      if (existing) {
        existing.addEventListener('load', () => resolve(window.$3Dmol));
        existing.addEventListener('error', () => reject(new Error('无法加载 3Dmol.js 引擎')));
        return;
      }
      const script = document.createElement('script');
      script.src = '/vendor/3Dmol-min.js';
      script.async = true;
      script.onload = () => resolve(window.$3Dmol);
      script.onerror = () => reject(new Error('无法加载 3Dmol.js 引擎文件'));
      document.body.appendChild(script);
    });
  }, []);

  // Fetch pocket 3D structure data from backend
  const loadStructure = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchKinasePocketStructure(targetName, drugName, drugSmiles);
      setData(res);
    } catch (err: any) {
      setError(err.message || '加载 3D 口袋结构失败');
    } finally {
      setLoading(false);
    }
  }, [targetName, drugName, drugSmiles]);

  useEffect(() => {
    if (autoFetch) {
      loadStructure();
    }
  }, [autoFetch, loadStructure]);

  // Render or re-render 3D scene whenever data or render settings change
  const renderScene = useCallback(async () => {
    if (!containerRef.current || !data) return;

    try {
      const $3Dmol = await ensure3Dmol();
      if (!containerRef.current) return;

      // Clean existing viewer
      if (viewerRef.current) {
        viewerRef.current.clear();
      } else {
        containerRef.current.innerHTML = '';
        viewerRef.current = $3Dmol.createViewer(containerRef.current, {
          backgroundColor: '#050b14',
          defaultcolors: $3Dmol.rasmolElementColors
        });
      }

      const viewer = viewerRef.current;
      viewer.clear();

      // Add PDB model
      viewer.addModel(data.pdb_content, 'pdb');

      // Style configurations
      if (renderMode === 'cartoon') {
        // Protein cartoon with gradient spectrum
        viewer.setStyle({ hetflag: false }, {
          cartoon: { color: 'spectrum', opacity: 0.9, style: 'oval' }
        });
        // Key Hinge residues stick accent
        viewer.setStyle({ resi: [315, 316, 317, 318, 319, 320, 790, 793, 529, 532] }, {
          cartoon: { color: '#06b6d4', opacity: 1.0 },
          stick: { radius: 0.18, colorscheme: 'cyanCarbon' }
        });
        // DFG motif accent
        viewer.setStyle({ resi: [381, 382, 383, 594, 595, 596] }, {
          cartoon: { color: data.binding_mode === 'type_ii' ? '#f59e0b' : '#10b981', opacity: 1.0 },
          stick: { radius: 0.22, colorscheme: data.binding_mode === 'type_ii' ? 'yellowCarbon' : 'greenCarbon' }
        });
      } else if (renderMode === 'surface') {
        viewer.setStyle({ hetflag: false }, {
          cartoon: { color: '#475569', opacity: 0.6 }
        });
        viewer.addSurface($3Dmol.SurfaceType.VDW, {
          opacity: 0.35,
          color: '#38bdf8'
        }, { hetflag: false });
      } else if (renderMode === 'stick') {
        viewer.setStyle({ hetflag: false }, {
          stick: { radius: 0.15, colorscheme: 'amino' }
        });
      }

      // Small molecule ligand (HETATM)
      viewer.setStyle({ hetflag: true }, {
        stick: { radius: 0.28, colorscheme: 'magentaCarbon' }
      });

      // Hydrogen bonds (dashed yellow cylinders)
      if (showHbonds) {
        // Key coordinate anchors from crystallographic standard
        viewer.addCylinder({
          start: { x: 10.9, y: 13.7, z: 5.7 },
          end: { x: 13.5, y: 12.9, z: 4.8 },
          radius: 0.08,
          color: '#facc15',
          dashed: true
        });
        viewer.addCylinder({
          start: { x: 12.5, y: 10.2, z: 4.5 },
          end: { x: 13.0, y: 13.1, z: 4.7 },
          radius: 0.08,
          color: '#facc15',
          dashed: true
        });
      }

      // 3D Text Labels
      if (showLabels) {
        viewer.addLabel(`Hinge: ${data.hinge_residue}`, {
          position: { x: 13.8, y: 10.8, z: 5.0 },
          backgroundColor: '#0f172a',
          backgroundOpacity: 0.85,
          fontColor: '#38bdf8',
          fontSize: 11,
          borderThickness: 1,
          borderColor: '#0284c7'
        });
        viewer.addLabel(`${data.dfg_conformation_label.slice(0, 7)}`, {
          position: { x: 18.8, y: 15.2, z: 6.2 },
          backgroundColor: '#0f172a',
          backgroundOpacity: 0.85,
          fontColor: data.binding_mode === 'type_ii' ? '#fbbf24' : '#34d399',
          fontSize: 11,
          borderThickness: 1,
          borderColor: data.binding_mode === 'type_ii' ? '#d97706' : '#059669'
        });
        viewer.addLabel(data.drug_name, {
          position: { x: 11.2, y: 11.8, z: 4.2 },
          backgroundColor: '#0f172a',
          backgroundOpacity: 0.85,
          fontColor: '#f472b6',
          fontSize: 11,
          borderThickness: 1,
          borderColor: '#db2777'
        });
      }

      viewer.zoomTo();
      viewer.render();
      if (isSpinning) {
        viewer.spin(true);
      }
    } catch (e: any) {
      console.error('3Dmol render error:', e);
    }
  }, [data, renderMode, showHbonds, showLabels, isSpinning, ensure3Dmol]);

  useEffect(() => {
    renderScene();
  }, [renderScene]);

  // Handle window / container resize
  useEffect(() => {
    const handleResize = () => {
      if (viewerRef.current) {
        viewerRef.current.resize();
        viewerRef.current.render();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleResetCamera = () => {
    if (viewerRef.current) {
      viewerRef.current.zoomTo();
      viewerRef.current.render();
    }
  };

  const handleToggleSpin = () => {
    if (viewerRef.current) {
      const nextSpin = !isSpinning;
      setIsSpinning(nextSpin);
      viewerRef.current.spin(nextSpin);
    }
  };

  const handleScreenshot = () => {
    if (!viewerRef.current) return;
    try {
      const uri = viewerRef.current.pngURI();
      const a = document.createElement('a');
      a.href = uri;
      a.download = `${targetName}_${drugName}_pocket_3d.png`;
      a.click();
    } catch (e) {
      console.error('Snapshot failed', e);
    }
  };

  const handleToggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
    setTimeout(() => {
      if (viewerRef.current) {
        viewerRef.current.resize();
        viewerRef.current.zoomTo();
        viewerRef.current.render();
      }
    }, 150);
  };

  return (
    <div className={`flex flex-col bg-slate-900/90 rounded-2xl border border-slate-800 shadow-2xl overflow-hidden backdrop-blur-md transition-all duration-300 ${
      isFullscreen ? 'fixed inset-4 z-50 shadow-[0_0_80px_rgba(0,0,0,0.8)]' : className
    }`}>
      {/* 3D Viewer Header */}
      <div className="flex flex-wrap items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-white tracking-wide">
                {targetName} · 催化结合口袋 3D 微观构象
              </span>
              {data && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-mono">
                  {data.pdb_code}
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              {data ? `${data.resolution_info} · 配体: ${data.drug_name}` : 'WebGL 交互式激酶口袋原子级观测'}
            </p>
          </div>
        </div>

        {/* Conformation Badge */}
        {data && (
          <div className="flex items-center gap-1.5">
            <span className={`text-[11px] px-2.5 py-1 rounded-full font-medium flex items-center gap-1 border ${
              data.binding_mode === 'type_ii'
                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
            }`}>
              <Sparkles className="w-3 h-3" />
              {data.dfg_conformation_label}
            </span>
          </div>
        )}

        {/* Controls Toolbar */}
        <div className="flex items-center gap-1">
          {/* Mode Switch */}
          <div className="flex bg-slate-900 border border-slate-700/60 rounded-lg p-0.5 text-xs">
            <button
              onClick={() => setRenderMode('cartoon')}
              className={`px-2 py-1 rounded transition-colors ${
                renderMode === 'cartoon' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="卡通二级结构带状"
            >
              带状
            </button>
            <button
              onClick={() => setRenderMode('surface')}
              className={`px-2 py-1 rounded transition-colors ${
                renderMode === 'surface' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="VDW 范德华口袋空腔表面"
            >
              表面
            </button>
            <button
              onClick={() => setRenderMode('stick')}
              className={`px-2 py-1 rounded transition-colors ${
                renderMode === 'stick' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="全原子球棍模型"
            >
              球棍
            </button>
          </div>

          {/* Toggle H-Bonds */}
          <button
            onClick={() => setShowHbonds(!showHbonds)}
            className={`p-1.5 rounded-lg border text-xs transition-colors ${
              showHbonds 
                ? 'bg-yellow-500/15 border-yellow-500/40 text-yellow-300' 
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="显示/隐藏 铰链区关键氢键 (黄色虚线)"
          >
            <Flame className="w-3.5 h-3.5" />
          </button>

          {/* Toggle Labels */}
          <button
            onClick={() => setShowLabels(!showLabels)}
            className={`p-1.5 rounded-lg border text-xs transition-colors ${
              showLabels 
                ? 'bg-sky-500/15 border-sky-500/40 text-sky-300' 
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="显示/隐藏 残基文字标注"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>

          {/* Toggle Spin */}
          <button
            onClick={handleToggleSpin}
            className={`p-1.5 rounded-lg border text-xs transition-colors ${
              isSpinning 
                ? 'bg-purple-500/15 border-purple-500/40 text-purple-300' 
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title={isSpinning ? '暂停自动旋转' : '开启 360° 缓速自旋'}
          >
            {isSpinning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          {/* Reset Camera */}
          <button
            onClick={handleResetCamera}
            className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
            title="居中重置视角"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {/* Screenshot */}
          <button
            onClick={handleScreenshot}
            className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
            title="导出当前视角超清科研快照 PNG"
          >
            <Camera className="w-3.5 h-3.5" />
          </button>

          {/* Fullscreen */}
          <button
            onClick={handleToggleFullscreen}
            className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
            title={isFullscreen ? '退出全屏' : '全屏精密观测'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* 3D Canvas Box */}
      <div className="relative flex-1 min-h-[360px] bg-[#050b14] overflow-hidden">
        {loading && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-slate-950/70 backdrop-blur-xs gap-3">
            <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
            <p className="text-xs text-slate-300">解算晶体口袋原子坐标与氢键几何网络...</p>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-6 text-center bg-slate-950/80 gap-3">
            <Activity className="w-8 h-8 text-rose-400" />
            <p className="text-xs text-rose-300">{error}</p>
            <button
              onClick={loadStructure}
              className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition-colors"
            >
              重新解算
            </button>
          </div>
        )}

        {/* WebGL Canvas */}
        <div 
          ref={containerRef} 
          className="w-full h-full min-h-[360px] cursor-grab active:cursor-grabbing"
          style={{ width: '100%', height: isFullscreen ? 'calc(100vh - 120px)' : '360px' }}
        />

        {/* Legend Overlay at bottom-left */}
        <div className="absolute bottom-3 left-3 z-10 pointer-events-none flex flex-wrap gap-2 text-[10px]">
          <span className="px-2 py-1 rounded bg-slate-950/80 border border-slate-800/80 text-cyan-300 backdrop-blur-xs flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            铰链区: {data?.hinge_residue || 'Hinge'}
          </span>
          <span className="px-2 py-1 rounded bg-slate-950/80 border border-slate-800/80 text-amber-300 backdrop-blur-xs flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400"></span>
            DFG 基序: {data?.binding_mode === 'type_ii' ? 'DFG-out 变构' : 'DFG-in 活性'}
          </span>
          <span className="px-2 py-1 rounded bg-slate-950/80 border border-slate-800/80 text-pink-300 backdrop-blur-xs flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-pink-400"></span>
            小分子配体 (Ligand)
          </span>
          {showHbonds && (
            <span className="px-2 py-1 rounded bg-slate-950/80 border border-slate-800/80 text-yellow-300 backdrop-blur-xs flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
              关键氢键 (2.8~3.1 Å)
            </span>
          )}
        </div>
      </div>

      {/* Pocket Hydrogen Bonds & Residues Detail Footer */}
      {data && data.key_hydrogen_bonds && data.key_hydrogen_bonds.length > 0 && (
        <div className="px-4 py-2.5 bg-slate-950/90 border-t border-slate-800/80 text-[11px] text-slate-400">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="text-slate-300 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                解析关键氢键网络:
              </span>
              <div className="flex flex-wrap gap-2">
                {data.key_hydrogen_bonds.map((hb, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/60 text-slate-300 font-mono">
                    <span className="text-pink-300">{hb.donor}</span>
                    <span className="text-yellow-400 mx-1">···</span>
                    <span className="text-cyan-300">{hb.acceptor}</span>
                    <span className="text-slate-500 ml-1.5">({hb.distance} Å)</span>
                  </span>
                ))}
              </div>
            </div>
            <div className="text-[10px] text-slate-500 font-mono">
              网格原子数: {data.num_atoms} · 门控残基: {data.gatekeeper_residue}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
