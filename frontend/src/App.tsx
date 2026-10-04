import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Outlet, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { apiClient } from './api/client';
import { Activity, Beaker, Dna, FileBarChart, Settings, ShoppingCart, Zap, Sun, Moon } from 'lucide-react';
import { useAppStore } from './store/useAppStore';

import ScreeningStudio from './pages/ScreeningStudio';
import EvolutionStudio from './pages/EvolutionStudio';
import HelicalWheelStudio from './pages/HelicalWheelStudio';
import ReportStudio from './pages/ReportStudio';
import { SettingsModal } from './components/SettingsModal';
import { PeptideCartModal } from './components/PeptideCartModal';
import { ErrorBoundary } from './components/ErrorBoundary';

const queryClient = new QueryClient();

const NavTab = ({ to, icon: Icon, label, isActive }: { to: string, icon: any, label: string, isActive: boolean }) => (
  <NavLink to={to}>
    <div className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs font-semibold transition-all ${
      isActive 
        ? 'bg-blue-600 text-white shadow-xs' 
        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800'
    }`}>
      <Icon size={15} />
      <span>{label}</span>
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
  const status = useQuery({ queryKey: ['research-status'], queryFn: async () => (await apiClient.get('/api/system_status')).data, refetchInterval: 30000, retry: false });
  const ready = status.data?.status === 'healthy';

  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xs border-b border-slate-200 dark:border-slate-800 px-6 py-2.5">
      <div className="max-w-7xl mx-auto flex flex-wrap gap-2 items-center justify-between">
        
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
            <Dna size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100">SafeAMP-Dual Research</h1>
              <span className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 px-1.5 py-0.2 rounded font-mono font-medium">
                v4.0.0
              </span>
            </div>
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-mono tracking-wider uppercase">
              计算生物学与抗微生物肽工程实验工作台
            </p>
          </div>
        </div>

        {/* System Online Badges */}
        <div role="status" className={'text-xs px-2 py-1 rounded border ' + (ready ? 'text-emerald-700 border-emerald-500' : 'text-amber-700 border-amber-500')} title={status.data?.reason ?? ''}>
          {status.isPending ? '检查模型状态…' : ready ? '研究模型已通过运行校验' : '研究模型不可用'}
        </div>

        {/* Global Action Tools */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleDark}
            title="切换日间/夜间模式"
            className="p-1.5 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          
          <button
            type="button"
            onClick={openSettings}
            title="配置中心 (可拔插模型设置)"
            className="p-1.5 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1 text-xs"
          >
            <Settings size={16} />
            <span className="hidden sm:inline">配置中心</span>
          </button>

          <button
            type="button"
            onClick={openCart}
            title="查看暂存的候选多肽分子库"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-700 transition-colors"
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

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200">
      <GlobalHeader 
        isDark={isDark} 
        toggleDark={() => setIsDark(!isDark)} 
        openSettings={() => setSettingsOpen(true)}
        openCart={() => setCartOpen(true)}
      />

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <PeptideCartModal isOpen={cartOpen} onClose={() => setCartOpen(false)} />

      {/* Main Studio Navigation Bar */}
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-1.5 flex items-center gap-2 overflow-x-auto">
          <NavTab to="/" icon={Beaker} label="1. 高通量协同筛选" isActive={location.pathname === '/'} />
          <NavTab to="/evolution" icon={Activity} label="2. 探索性突变排序" isActive={location.pathname === '/evolution'} />
          <NavTab to="/wheel" icon={Zap} label="3. 螺旋轮与两亲投影" isActive={location.pathname === '/wheel'} />
          <NavTab to="/report" icon={FileBarChart} label="4. 科研报告与导出" isActive={location.pathname === '/report'} />
        </div>
      </div>

      {/* Main Workstation Canvas */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
        <p className="mb-5 p-3 rounded border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 text-amber-950 dark:text-amber-200 text-sm">纯计算研究原型。当前数据、来源隔离与实验产物通过校验后才能预测；理化图示不依赖预测模型，也不能证明真实构象或安全性。</p>
        <ErrorBoundary fallbackTitle="科研工作台页面组件运行异常">
          <Outlet />
        </ErrorBoundary>
      </main>
      
      {/* Scientific Lab Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 py-3 text-center text-[11px] text-slate-400 font-mono">
        SafeAMP-Dual · Computational research prototype · No clinical validation
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
            <Route index element={<ScreeningStudio />} />
            <Route path="evolution" element={<EvolutionStudio />} />
            <Route path="wheel" element={<HelicalWheelStudio />} />
            <Route path="report" element={<ReportStudio />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
