import React, { useState, useEffect } from 'react';
import { 
  X, 
  RotateCw, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  Ban, 
  Loader2, 
  ExternalLink,
  Activity
} from 'lucide-react';
import { 
  fetchAsyncTasksList, 
  cancelAsyncTask, 
  type AsyncTask, 
  type AsyncTaskStatus 
} from '../api/asyncTaskClient';

interface TaskCenterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectResult?: (task: AsyncTask) => void;
}

export function TaskCenterModal({ isOpen, onClose, onSelectResult }: TaskCenterModalProps) {
  const [tasks, setTasks] = useState<AsyncTask[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const loadTasks = async () => {
    setIsLoading(true);
    try {
      const data = await fetchAsyncTasksList(undefined, statusFilter === 'all' ? undefined : statusFilter, 30);
      setTasks(data);
    } catch (err) {
      console.error('Failed to load tasks:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadTasks();
      // Poll every 3s if any task is pending or running
      const timer = setInterval(() => {
        loadTasks();
      }, 3000);
      return () => clearInterval(timer);
    }
  }, [isOpen, statusFilter]);

  const handleCancel = async (taskId: string) => {
    setCancellingId(taskId);
    try {
      await cancelAsyncTask(taskId);
      await loadTasks();
    } catch (err) {
      console.error('Failed to cancel task:', err);
    } finally {
      setCancellingId(null);
    }
  };

  if (!isOpen) return null;

  const getStatusBadge = (status: AsyncTaskStatus) => {
    switch (status) {
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium font-mono bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/50 dark:text-blue-300 dark:border-blue-800">
            <Loader2 size={10} className="animate-spin" />
            执行中
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium font-mono bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800">
            <Clock size={10} />
            排队中
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium font-mono bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800">
            <CheckCircle2 size={10} />
            已完成
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium font-mono bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
            <Ban size={10} />
            已取消
          </span>
        );
      case 'interrupted':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium font-mono bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-950/50 dark:text-purple-300 dark:border-purple-800">
            <AlertTriangle size={10} />
            服务重启中断
          </span>
        );
      case 'failed':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium font-mono bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800">
            <AlertTriangle size={10} />
            异常失败
          </span>
        );
    }
  };

  const getTaskTypeName = (type: string) => {
    switch (type) {
      case 'kinase_profiling':
        return '激酶全谱/核心谱扫描';
      case 'virtual_screening':
        return '分子库通量虚拟筛选';
      case 'lead_optimization':
        return '先导分子演化衍生';
      default:
        return type;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 max-w-4xl w-full max-h-[85vh] flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="task-center-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-50 dark:bg-sky-950/70 flex items-center justify-center text-sky-600 dark:text-sky-400 shadow-inner">
              <Activity size={18} />
            </div>
            <div>
              <h2 id="task-center-title" className="text-sm font-bold text-slate-900 dark:text-slate-100">
                异步计算任务中心
              </h2>
              <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                持久化任务队列 · 支持离线执行与重启中断标记 · 随时安全取消
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadTasks}
              title="刷新任务列表"
              className="p-1.5 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
            >
              <RotateCw size={14} className={isLoading ? 'animate-spin' : ''} />
            </button>
            <button
              type="button"
              onClick={onClose}
              title="关闭窗口"
              className="p-1.5 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="px-6 py-2.5 border-b border-slate-100 dark:border-slate-800/80 bg-white dark:bg-slate-900 flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5">
            {['all', 'running', 'completed', 'failed'].map((filterKey) => (
              <button
                key={filterKey}
                type="button"
                onClick={() => setStatusFilter(filterKey)}
                className={`px-2.5 py-1 rounded-md font-mono text-[11px] transition-all cursor-pointer ${
                  statusFilter === filterKey
                    ? 'bg-sky-600 text-white font-medium shadow-2xs'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {filterKey === 'all' ? '全部任务' : filterKey === 'running' ? '进行中' : filterKey === 'completed' ? '已完成' : '失败/中断'}
              </button>
            ))}
          </div>

          <span className="text-[11px] font-mono text-slate-400">
            共 {tasks.length} 条记录
          </span>
        </div>

        {/* Task List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {tasks.length === 0 ? (
            <div className="text-center py-12 text-slate-400 dark:text-slate-500">
              <Clock size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-xs">暂无异步任务记录</p>
            </div>
          ) : (
            tasks.map((task) => {
              const isRunning = task.status === 'running' || task.status === 'pending';
              const percent = Math.round((task.progress || 0) * 100);

              return (
                <div
                  key={task.task_id}
                  className="bg-slate-50/70 dark:bg-slate-850/60 border border-slate-200/80 dark:border-slate-800 rounded-xl p-4 transition-all"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                          {getTaskTypeName(task.task_type)}
                        </span>
                        {getStatusBadge(task.status)}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                        <span>ID: {task.task_id}</span>
                        <span>·</span>
                        <span>提交于 {new Date(task.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      {isRunning && (
                        <button
                          type="button"
                          onClick={() => handleCancel(task.task_id)}
                          disabled={cancellingId === task.task_id}
                          className="px-2.5 py-1 text-[11px] font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-md transition-colors cursor-pointer"
                        >
                          {cancellingId === task.task_id ? '取消中...' : '终止任务'}
                        </button>
                      )}
                      {task.status === 'completed' && onSelectResult && (
                        <button
                          type="button"
                          onClick={() => onSelectResult(task)}
                          className="px-2.5 py-1 text-[11px] font-medium text-sky-600 dark:text-sky-400 hover:bg-sky-50 dark:hover:bg-sky-950/40 border border-sky-200 dark:border-sky-800 rounded-md transition-colors flex items-center gap-1 cursor-pointer"
                        >
                          <span>查看结果</span>
                          <ExternalLink size={10} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Progress Bar (if running or completed) */}
                  {(isRunning || task.status === 'completed') && (
                    <div className="mt-3 space-y-1.5">
                      <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400">
                        <span>{task.progress_stage || '处理中'}</span>
                        <span>{percent}% ({task.progress_current || 0}/{task.progress_total || 0})</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-750 rounded-full overflow-hidden">
                        <div 
                          className={`h-full transition-all duration-300 rounded-full ${
                            task.status === 'completed' ? 'bg-emerald-500' : 'bg-sky-500'
                          }`}
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Error / Interruption Detail */}
                  {task.error_message && (
                    <div className="mt-2 text-[11px] text-rose-600 dark:text-rose-400 font-mono bg-rose-50/50 dark:bg-rose-950/30 p-2 rounded-lg border border-rose-200/50 dark:border-rose-900/50">
                      {task.error_message}
                    </div>
                  )}

                  {/* Result Summary Preview */}
                  {task.result_summary && (
                    <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono text-slate-600 dark:text-slate-300 bg-slate-100/70 dark:bg-slate-800/60 p-2 rounded-lg">
                      {Object.entries(task.result_summary).slice(0, 4).map(([k, v]) => (
                        <div key={k} className="flex items-center gap-1">
                          <span className="text-slate-400">{k}:</span>
                          <span className="font-semibold text-slate-800 dark:text-slate-200">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/60 text-right">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
