import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Outlet, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useResearchStatus } from './api/researchStatus';
import { Beaker, Dna, FileBarChart, Settings, ShoppingCart, Zap, Sun, Moon, FlaskConical, Sparkles } from 'lucide-react';
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
  <NavLink to={to} className="shrink-0 cursor-pointer">
    <div className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer ${
      isActive 
        ? 'bg-blue-600 text-white shadow-xs font-semibold' 
        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/80'
    }`}>
      <Icon size={15} className={isActive ? 'text-white' : 'text-slate-500 dark:text-slate-400'} />
      <span>{label}</span>
      {tag && (
        <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-normal transition-colors ${
          isActive 
            ? 'bg-blue-700/80 text-blue-100' 
            : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
        }`}>
          {tag}
        </span>
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
  const status = useResearchStatus();
  const ready = status.ready;

  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-4 sm:px-6 py-2.5 transition-colors">
      <div className="max-w-7xl mx-auto flex flex-wrap gap-3 items-center justify-between">
        
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-xs">
            <Dna size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100">SafeAMP-Dual & DTI Studio</h1>
              <span className="text-[10px] bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800/60 px-1.5 py-0.2 rounded font-mono font-medium">
                v4.3.0
              </span>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono tracking-wider">
              生物世界模型 · 激酶结合亲和力预测 (DAVIS) 与多肽工程工作台
            </p>
          </div>
        </div>

        {/* System Online Badge */}
        <div role="status" className={`text-xs px-2.5 py-1 rounded-full border flex items-center gap-1.5 font-medium transition-colors ${
          ready 
            ? 'text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700/60 bg-emerald-50 dark:bg-emerald-950/40' 
            : 'text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-700/60 bg-amber-50 dark:bg-amber-950/40'
        }`} title={ready ? status.label : status.message}>
          <span className={`w-2 h-2 rounded-full ${ready ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
          <span>{status.label}</span>
        </div>

        {/* Global Action Tools */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleDark}
            title="切换日间/夜间模式"
            className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer focus-ring"
          >
            {isDark ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          
          <button
            type="button"
            onClick={openSettings}
            title="配置中心 (大模型连接与密钥管理)"
            className="p-1.5 px-2.5 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors flex items-center gap-1.5 text-xs font-medium cursor-pointer focus-ring"
          >
            <Settings size={14} className="text-slate-500" />
            <span className="hidden sm:inline">模型配置</span>
          </button>

          <button
            type="button"
            onClick={openCart}
            title="查看暂存的候选分子库"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors cursor-pointer focus-ring"
          >
            <ShoppingCart size={14} />
            <span>分子库</span>
            <span className="bg-blue-600 text-white text-[10px] px-1.5 py-0.2 rounded-full font-mono">
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
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-[53px] z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          <NavTab 
            to="/" 
            icon={FlaskConical} 
            label="DTI 激酶亲和力" 
            tag="世界模型" 
            isActive={location.pathname === '/' || location.pathname === '/dti'} 
          />
          <NavTab 
            to="/evolution" 
            icon={Sparkles} 
            label="先导改构与进化" 
            tag="Lead Optimizer" 
            isActive={location.pathname === '/evolution'} 
          />
          <NavTab 
            to="/amp-screening" 
            icon={Beaker} 
            label="抗菌肽协同筛选" 
            tag="历史原型" 
            isActive={location.pathname === '/amp-screening'} 
          />
          <NavTab 
            to="/wheel" 
            icon={Zap} 
            label="螺旋轮两亲投影" 
            tag="2D/3D理化" 
            isActive={location.pathname === '/wheel'} 
          />
          <NavTab 
            to="/report" 
            icon={FileBarChart} 
            label="科研报告与导出" 
            tag="学术交付" 
            isActive={location.pathname === '/report'} 
          />
        </div>
      </div>

      {/* Main Workstation Canvas */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
        {showDisclaimer && (
          <div className="mb-5 p-3 rounded-xl border border-amber-200/80 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200 text-xs flex items-start justify-between gap-3 shadow-2xs">
            <div className="flex items-start gap-2.5 leading-relaxed">
              <span className="shrink-0 font-bold px-1.5 py-0.2 rounded text-[10px] bg-amber-200/70 dark:bg-amber-900/60 text-amber-900 dark:text-amber-200 mt-0.5">
                科研合规规范
              </span>
              <span>
                本系统为纯计算生物学研究原型。当前特征、拓扑隔离与实验产物通过校验后方可执行推断；理化图示不依赖预测模型，亦不能替代湿实验安全毒性论证。
              </span>
            </div>
            <button 
              type="button" 
              onClick={() => setShowDisclaimer(false)} 
              className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 text-[11px] shrink-0 font-medium cursor-pointer"
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
        SafeAMP-Dual & DTI Studio · Computational research prototype · Protocol-DTI-01 Verified
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
