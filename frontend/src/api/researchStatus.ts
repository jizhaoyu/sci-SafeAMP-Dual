import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

interface ResearchStatus {
  status: string;
  reason?: string | null;
  dual_task_model?: { weights_loaded?: boolean };
}

export function researchUnavailableMessage(reason?: string | null): string {
  if (reason?.includes('No validated research run configured')) {
    return '尚未配置通过校验的双任务模型运行产物。需要先完成双任务数据准入、训练与结果复核，才能启用预测。';
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
  const ready = !query.isError && query.data?.status === 'healthy' && query.data?.dual_task_model?.weights_loaded === true;
  const message = query.isPending ? '正在检查双任务模型状态，请稍候。' : query.isError ?
    '暂时无法读取后端模型状态，请检查本地后端服务后重新检查。' : researchUnavailableMessage(query.data?.reason);
  const label = query.isPending ? '检查双任务模型状态…' : query.isError ? '双任务模型状态无法确认' : ready ?
    '双任务模型已通过运行校验' : '双任务模型未就绪';
  return { ...query, ready, message, label };
}
