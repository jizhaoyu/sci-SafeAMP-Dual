/**
 * Frontend client for asynchronous task processing and lifecycle management.
 */

export type AsyncTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';

export interface AsyncTaskEvent {
  event_seq: number;
  event_type: string;
  created_at: string;
  data?: Record<string, any>;
}

export interface AsyncTask {
  task_id: string;
  task_type: string;
  status: AsyncTaskStatus;
  progress: number;
  progress_stage: string;
  progress_current: number;
  progress_total: number;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  updated_at?: string;
  params?: Record<string, any>;
  result_summary?: Record<string, any>;
  result_path?: string;
  error_message?: string;
  cancellation_requested?: boolean;
}

export interface TaskSubmitResponse {
  task_id: string;
  is_new: boolean;
  status: AsyncTaskStatus;
  task_type: string;
  created_at: string;
}

export async function submitAsyncTask(
  taskType: string,
  params: Record<string, any>,
  idempotencyKey?: string
): Promise<TaskSubmitResponse> {
  const res = await fetch('/api/tasks/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_type: taskType,
      params,
      idempotency_key: idempotencyKey,
    }),
  });

  if (res.status === 429) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || '任务队列已满，单机并发达到上限，请稍候再试。');
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `任务提交失败 (HTTP ${res.status})`);
  }

  return res.json();
}

export async function fetchAsyncTaskStatus(taskId: string): Promise<AsyncTask> {
  const res = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`);
  if (!res.ok) {
    throw new Error(`获取任务状态失败 (${res.status})`);
  }
  return res.json();
}

export async function cancelAsyncTask(taskId: string, reason: string = '用户在页面主动取消'): Promise<void> {
  const res = await fetch(`/api/tasks/${encodeURIComponent(taskId)}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    throw new Error(`取消任务失败 (${res.status})`);
  }
}

export async function fetchAsyncTaskResult<T = any>(taskId: string): Promise<T> {
  const res = await fetch(`/api/tasks/${encodeURIComponent(taskId)}/result`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `获取任务计算结果失败 (${res.status})`);
  }
  return res.json();
}

export async function fetchAsyncTaskEvents(taskId: string): Promise<AsyncTaskEvent[]> {
  const res = await fetch(`/api/tasks/${encodeURIComponent(taskId)}/events`);
  if (!res.ok) {
    throw new Error(`获取任务日志流失败 (${res.status})`);
  }
  return res.json();
}

export async function fetchAsyncTasksList(
  taskType?: string,
  status?: string,
  limit: number = 20
): Promise<AsyncTask[]> {
  const params = new URLSearchParams();
  if (taskType) params.set('task_type', taskType);
  if (status) params.set('status', status);
  params.set('limit', limit.toString());

  const res = await fetch(`/api/tasks?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`获取任务列表失败 (${res.status})`);
  }
  return res.json();
}
