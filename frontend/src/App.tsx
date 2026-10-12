import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Outlet, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDTIModelStatus } from './api/researchStatus';
import { Dna, Settings, ShoppingCart, Sun, Moon, FlaskConical, Sparkles } from 'lucide-react';
import { useAppStore } from './store/useAppStore';

import DTIStudioPage from './pages/DTIStudioPage';
import ScreeningStudio from './pages/ScreeningStudio';
import EvolutionStudio from './pages/EvolutionStudio';
import HelicalWheelStudio from './pages/HelicalWheelStudio';
import ReportStudio from './pages/ReportStudio';
import { SettingsModal } from './components/SettingsModal';
import { PeptideCartModal } from './components/PeptideCartModal';
import { ErrorBoundary } from './components/ErrorBoundary';

const queryClient = new QueryClient();

const NavTab = ({ 
  to, 
  icon: Icon, 
  label, 
  tag, 
  isActive 
}: { 
  to: string; 
  icon: any; 
  label: string; 
  tag?: string; 
  isActive: boolean; 
}) => (
  <NavLink to={to} className="shrink-0 cursor-pointer focus-ring rounded-lg">
    <div className={`relative flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs transition-all duration-200 cursor-pointer select-none ${
      isActive 
        ? 'bg-sky-600 text-white shadow-md shadow-sky-500/25 font-semibold dark:bg-sky-500 dark:text-slate-950' 
        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100/80 dark:hover:bg-slate-800/70'
    }`}>
      <Icon size={15} className={isActive ? 'text-white dark:text-slate-950' : 'text-slate-400 dark:text-slate-500'} />
      <span className="tracking-tight">{label}</span>
      {tag && (
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-medium transition-colors ${
          isActive 
            ? 'bg-sky-700/80 text-sky-100 dark:bg-sky-600/90 dark:text-slate-950' 
            : 'bg-slate-100 dark:bg-slate-800/90 text-slate-500 dark:text-slate-400 border border-slate-200/50 dark:border-slate-700/50'
        }`}>
          {tag}
        </span>
      )}
      {isActive && (
        <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-8 h-[2px] bg-sky-500 rounded-full dark:bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.8)]" />
      )}
    </div>
  </NavLink>
);

const GlobalHeader = ({ 
  isDark, 
  toggleDark, 
  openSettings, 
  openCart 
}: { 
  isDark: boolean; 
  toggleDark: () => void; 
  openSettings: () => void; 
  openCart: () => void; 
}) => {
  const { cart } = useAppStore();
  const dtiStatus = useDTIModelStatus();

  return (
    <header className="bg-white/90 dark:bg-slate-950/85 backdrop-blur-xl border-b border-slate-200/80 dark:border-slate-800/80 px-4 sm:px-6 lg:px-8 py-2.5 transition-colors shadow-2xs">
      <div className="max-w-[1920px] w-full mx-auto flex flex-wrap gap-3 items-center justify-between">
        
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-600 via-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-500/20 ring-1 ring-white/20">
            <Dna size={18} className="animate-pulse-subtle" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100 font-sans">
                SafeAMP · 药物靶点研究工作台
              </h1>
              <span className="text-[10px] bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/70 px-1.5 py-0.2 rounded font-mono font-medium tracking-wide">
                DAVIS 模型基准 · {dtiStatus.recommended?.model_version ? '20261010' : '历史版本'}
              </span>
            </div>
            <p className="hidden lg:flex text-xs text-slate-600 dark:text-slate-400 font-mono tracking-wide items-center gap-1.5">
              <span>{dtiStatus.recommended?.name || '模型目录加载中'}</span>
              <span className="text-slate-300 dark:text-slate-700">/</span>
              <span>DAVIS 激酶全矩阵 (25,772)</span>
              <span className="text-slate-300 dark:text-slate-700">/</span>
              <span>{dtiStatus.recommended?.dual_cold_ci != null ? `双冷 CI ${Number(dtiStatus.recommended.dual_cold_ci).toFixed(4)}` : '双冷指标待核验'}</span>
            </p>
          </div>
        </div>

        {/* System Online Badge */}
        <div role="status" className={`text-xs px-2.5 py-1 rounded-full border flex items-center gap-1.5 font-medium transition-all shadow-2xs ${
          dtiStatus.ready 
            ? 'text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700/60 bg-emerald-50/80 dark:bg-emerald-950/40' 
            : dtiStatus.is429
            ? 'text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-700/60 bg-amber-50/80 dark:bg-amber-950/40'
            : dtiStatus.isPending
            ? 'text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40'
            : 'text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-700/60 bg-rose-50/80 dark:bg-rose-950/40'
        }`} title={dtiStatus.message}>
          <span className={`w-2 h-2 rounded-full ${
            dtiStatus.ready 
              ? 'bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]' 
              : dtiStatus.is429
              ? 'bg-amber-500 animate-pulse'
              : dtiStatus.isPending
              ? 'bg-slate-400'
              : 'bg-rose-500'
          }`} />
          <span className="font-mono text-[11px]">{dtiStatus.label}</span>
        </div>

        {/* Global Action Tools */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleDark}
            title="切换日间/夜间模式"
            aria-label="切换日间/夜间模式"
            className="p-2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors cursor-pointer focus-ring"
          >
            {isDark ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-slate-600" />}
          </button>
          
          <button
            type="button"
            onClick={openSettings}
            title="配置中心 (大模型连接与密钥管理)"
            aria-label="模型配置"
            className="p-1.5 px-2.5 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-slate-200 dark:border-slate-800 transition-colors flex items-center gap-1.5 text-xs font-medium cursor-pointer focus-ring shadow-2xs"
          >
            <Settings size={14} className="text-slate-500 dark:text-slate-400" />
            <span>模型配置</span>
          </button>

          <button
            type="button"
            onClick={openCart}
            title="查看暂存的候选分子库"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800/90 hover:bg-slate-200/80 dark:hover:bg-slate-700/80 rounded-lg border border-slate-200 dark:border-slate-750 transition-all cursor-pointer focus-ring shadow-2xs"
          >
            <ShoppingCart size={14} className="text-slate-500 dark:text-slate-400" />
            <span>分子库</span>
            <span className="bg-sky-600 dark:bg-sky-500 text-white dark:text-slate-950 text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold">
              {cart.length}
            </span>
          </button>
        </div>

      </div>
    </header>
  );
};

const Layout = () => {
  const location = useLocation();
  const [isDark, setIsDark] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(true);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 antialiased">
      <GlobalHeader 
        isDark={isDark} 
        toggleDark={() => setIsDark(!isDark)} 
        openSettings={() => setSettingsOpen(true)}
        openCart={() => setCartOpen(true)}
      />

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <PeptideCartModal isOpen={cartOpen} onClose={() => setCartOpen(false)} />

      {/* Main Studio Navigation Bar */}
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-30">
        <div className="max-w-[1920px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0 overflow-x-auto py-1">
            <NavTab 
              to="/" 
              icon={FlaskConical} 
              label="药物靶点预测"
              isActive={location.pathname === '/' || location.pathname === '/dti'} 
            />
            <NavTab 
              to="/evolution" 
              icon={Sparkles} 
              label="先导分子优化"
              isActive={location.pathname === '/evolution'} 
            />
          </div>

          <div className="hidden xl:flex items-center gap-3 text-xs text-slate-500">
            <span className="hidden md:inline font-mono text-[11px] bg-slate-100 dark:bg-slate-800/80 px-2.5 py-1 rounded-md text-slate-600 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60">
              DAVIS 本地基准 379 个靶点 · 25,772 个配对 · 实体分组评价
            </span>
          </div>
        </div>
      </div>

      {/* Main Workstation Canvas */}
      <main className="flex-1 min-w-0 max-w-[1600px] w-full mx-auto p-4 sm:p-6 lg:px-8 2xl:px-10">
        {showDisclaimer && (
          <div className="mb-5 p-3 rounded-xl border border-sky-200/80 dark:border-sky-900/60 bg-sky-50/70 dark:bg-sky-950/30 text-sky-900 dark:text-sky-200 text-xs flex items-start justify-between gap-3 shadow-2xs">
            <div className="flex items-start gap-2.5 leading-relaxed">
              <span className="shrink-0 font-bold px-1.5 py-0.2 rounded text-[10px] bg-sky-200/70 dark:bg-sky-900/60 text-sky-900 dark:text-sky-200 mt-0.5">
                科研合规规范
              </span>
              <span>
                本系统提供计算研究探索。模型运行状态、历史基准指标与独立外部证据分别判断；预测和结构分析结果需经实验核查，当前证据状态见各工作台的研究证据面板。
              </span>
            </div>
            <button 
              type="button" 
              onClick={() => setShowDisclaimer(false)} 
              className="text-sky-600 dark:text-sky-400 hover:text-sky-800 dark:hover:text-sky-200 text-[11px] shrink-0 font-medium cursor-pointer"
              title="收起提示"
            >
              不再显示
            </button>
          </div>
        )}

        <ErrorBoundary fallbackTitle="科研工作台页面组件运行异常">
          <Outlet />
        </ErrorBoundary>
      </main>
      
      {/* Scientific Lab Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 py-3 text-center text-[11px] text-slate-400 font-mono">
        SafeAMP-Dual & DTI Studio · Computational research prototype · 外部评价状态见研究证据面板
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<DTIStudioPage />} />
            <Route path="dti" element={<DTIStudioPage />} />
            <Route path="amp-screening" element={<ScreeningStudio />} />
            <Route path="evolution" element={<EvolutionStudio />} />
            <Route path="wheel" element={<HelicalWheelStudio />} />
            <Route path="report" element={<ReportStudio />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
