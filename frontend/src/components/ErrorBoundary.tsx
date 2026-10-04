import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in UI component:', error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 my-4 rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50/70 dark:bg-rose-950/30 text-rose-900 dark:text-rose-200 space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="text-rose-600 dark:text-rose-400" size={20} />
            <h3 className="font-semibold text-base">
              {this.props.fallbackTitle || '页面组件运行异常'}
            </h3>
          </div>
          <p className="text-xs text-rose-700 dark:text-rose-300 font-mono break-all">
            {this.state.error?.message || '发生了未捕获的渲染错误'}
          </p>
          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={this.handleReset}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors cursor-pointer"
            >
              <RotateCcw size={14} />
              <span>重试该组件</span>
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-3 py-1.5 text-xs font-semibold text-rose-700 dark:text-rose-300 bg-white dark:bg-slate-800 border border-rose-300 dark:border-rose-800 hover:bg-rose-100 dark:hover:bg-slate-700 rounded-lg transition-colors cursor-pointer"
            >
              刷新整个页面
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
