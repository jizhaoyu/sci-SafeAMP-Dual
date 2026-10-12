import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export function errorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) return error instanceof Error ? error.message : '请求失败';
  if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
    return '请求超时（超过 30 秒），请检查网络连接或后端服务器状态。';
  }
  if (!error.response && error.request) {
    return '无法连接到后端服务，请确认本地后端已启动（端口 8000/8090）。';
  }
  if (error.response?.status === 429) {
    const retryAfter = error.response.headers?.['retry-after'] || error.response.headers?.['Retry-After'];
    const retryMsg = retryAfter ? `，请等待 ${retryAfter} 秒后重试` : '，请稍候重试';
    return `请求过于频繁（HTTP 429 限流）${retryMsg}。系统正在保护后端计算资源。`;
  }
  if (error.response?.status === 503) {
    const detail = error.response?.data?.detail;
    const reason = error.response?.data?.reason;
    const msg = typeof detail === 'string' ? detail : (detail?.message || reason || '服务未就绪');
    if (typeof msg === 'string' && (msg.includes('SAFEAMP_RUN_DIR') || msg.includes('No validated research run'))) {
      return '双任务模型未就绪 (503)：尚未配置通过校验的研究产物 (SAFEAMP_RUN_DIR)。';
    }
    return `服务暂不可用 (503): ${msg}`;
  }
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg ?? '输入不合法').join('; ');
  if (detail?.code === 'MODEL_NOT_VALIDATED') return '双任务模型未就绪：运行产物尚未完成配置或未通过校验，请重新检查模型状态。';
  return detail?.message ?? error.message ?? '请求失败';
}

export interface BatchJobResponse {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  total: number;
  completed: number;
  failed_count: number;
  results: any[];
  errors: Array<{ index: number; sequence: string; error: string }>;
  created_at: number;
  updated_at: number;
}

export async function submitBatchJob(sequences: string[]): Promise<{ job_id: string; status: string; total: number }> {
  const res = await apiClient.post('/api/batch_jobs', { sequences });
  return res.data;
}

export async function getBatchJob(jobId: string): Promise<BatchJobResponse> {
  const res = await apiClient.get(`/api/batch_jobs/${jobId}`);
  return res.data;
}

export async function cancelBatchJob(jobId: string): Promise<{ job_id: string; status: string }> {
  const res = await apiClient.delete(`/api/batch_jobs/${jobId}`);
  return res.data;
}
