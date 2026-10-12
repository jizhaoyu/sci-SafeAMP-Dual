import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { apiClient, errorMessage } from './client';

export interface ResearchStatus {
  status: string;
  reason?: string | null;
  dual_task_model?: { weights_loaded?: boolean };
}

export function researchUnavailableMessage(reason?: string | null): string {
  if (reason?.includes('No validated research run configured') || reason?.includes('SAFEAMP_RUN_DIR')) {
    return '尚未配置通过校验的双任务模型运行产物 (SAFEAMP_RUN_DIR)。需要先完成双任务数据准入、训练与结果复核，才能启用预测。';
  }
  return '双任务模型运行产物尚未通过校验，预测、突变排序和研究报告生成暂不可用。';
}

export function useResearchStatus() {
  const query = useQuery({
    queryKey: ['research-status'],
    queryFn: async () => (await apiClient.get<ResearchStatus>('/api/system_status')).data,
    refetchInterval: 30000,
    staleTime: 10000,
    retry: false,
  });

  const err = query.error;
  const is429 = axios.isAxiosError(err) && err.response?.status === 429;
  const is503 = axios.isAxiosError(err) && err.response?.status === 503;
  const isOffline = axios.isAxiosError(err) && !err.response && !!err.request;

  const ready = !query.isError && query.data?.status === 'healthy' && query.data?.dual_task_model?.weights_loaded === true;

  let label: string;
  let message: string;

  if (query.isPending) {
    label = '检查双任务模型状态…';
    message = '正在检查双任务模型状态，请稍候。';
  } else if (is429) {
    label = '双任务请求受限 (429)';
    message = errorMessage(err);
  } else if (is503) {
    label = '双任务模型未就绪 (503)';
    message = errorMessage(err);
  } else if (isOffline) {
    label = '后端服务离线';
    message = '无法连接到后端服务，请确认本地后端已启动（端口 8000/8090）。';
  } else if (query.isError) {
    label = '双任务模型状态无法确认';
    message = errorMessage(err);
  } else if (ready) {
    label = '双任务模型已通过运行校验';
    message = '双任务模型已就绪，可进行 MIC 与 HC50 筛选。';
  } else {
    label = '双任务模型未就绪';
    message = researchUnavailableMessage(query.data?.reason);
  }

  return { ...query, ready, is429, is503, isOffline, message, label };
}

export function useDTIModelStatus() {
  const query = useQuery({
    queryKey: ['dti-models-status'],
    queryFn: async () => (await apiClient.get<any[]>('/api/dti/models')).data,
    refetchInterval: 30000,
    staleTime: 10000,
    retry: false,
  });

  const modelCount = Array.isArray(query.data) ? query.data.length : 0;
  const recommended = Array.isArray(query.data) ? query.data.find((m: any) => m.is_recommended) : null;
  const err = query.error;
  const is429 = axios.isAxiosError(err) && err.response?.status === 429;
  const is503 = axios.isAxiosError(err) && err.response?.status === 503;
  const isOffline = axios.isAxiosError(err) && !err.response && !!err.request;

  const ready = !query.isError && modelCount > 0;

  let label: string;
  let message: string;

  if (query.isPending) {
    label = '正在连接推理引擎…';
    message = '正在检查 DTI 推理引擎模型目录…';
  } else if (is429) {
    label = 'DTI 请求受限 (429)';
    message = errorMessage(err);
  } else if (is503) {
    label = 'DTI 服务暂不可用 (503)';
    message = 'DTI 模型服务暂不可用 (503)，请检查后端配置。';
  } else if (isOffline) {
    label = '后端服务离线';
    message = '无法连接到 DTI 后端服务，请确认本地后端已启动（端口 8000/8090）。';
  } else if (query.isError) {
    label = 'DTI 状态异常';
    message = errorMessage(err);
  } else if (modelCount === 0) {
    label = '未注册模型';
    message = 'DTI 后端已连接，但未检测到任何注册模型。';
  } else {
    const ciText = recommended?.dual_cold_ci != null ? `历史双冷基准 CI ${Number(recommended.dual_cold_ci).toFixed(4)}` : (recommended?.train_ci != null ? `训练集 CI ${recommended.train_ci}` : '模型目录就绪');
    label = `DTI 预测模型在线 (${ciText})`;
    message = `已连接 DTI 推理引擎，${modelCount} 款模型已就绪${recommended?.name ? `，默认：${recommended.name}` : ''}`;
  }

  return { ...query, ready, is429, is503, isOffline, label, message, modelCount, recommended };
}
