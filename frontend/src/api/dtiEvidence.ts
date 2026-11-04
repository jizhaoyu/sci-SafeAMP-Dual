import { useQuery } from '@tanstack/react-query';

export interface DTIModelDiagnostic {
  reviewed_at: string;
  model_sha256: string;
  diagnosis_sha256: string;
  scope: 'existing_DAVIS_diagnostic';
  high_affinity_count: number;
  high_affinity_mae_pkd: number;
  summary: string;
}

export function isModelDiagnostic(value: unknown): value is DTIModelDiagnostic {
  if (!value || typeof value !== 'object') return false;
  const record = value as Partial<DTIModelDiagnostic>;
  return record.scope === 'existing_DAVIS_diagnostic' && typeof record.summary === 'string'
    && typeof record.reviewed_at === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(record.reviewed_at)
    && typeof record.model_sha256 === 'string' && /^[0-9a-f]{64}$/.test(record.model_sha256)
    && typeof record.diagnosis_sha256 === 'string' && /^[0-9a-f]{64}$/.test(record.diagnosis_sha256)
    && Number.isInteger(record.high_affinity_count) && Number(record.high_affinity_count) > 0
    && typeof record.high_affinity_mae_pkd === 'number' && Number.isFinite(record.high_affinity_mae_pkd) && record.high_affinity_mae_pkd >= 0;
}

export interface DTIEvidenceStatus {
  status: 'available' | 'unavailable';
  reviewed_at: string | null;
  scope_label: string | null;
  reviewed_count: number | null;
  confirmed_point_count: number | null;
  admitted_count: number | null;
  external_evaluation_completed: boolean | null;
  human_review: string;
  message: string;
  evaluation_model?: string;
  model_diagnostics?: Record<string, DTIModelDiagnostic>;
  candidates?: Array<{ id: string; label: string; status: 'admitted' | 'pending_evidence' | 'excluded'; point_confirmed: boolean; reason: string }>;
}

export async function fetchDTIEvidenceStatus(): Promise<DTIEvidenceStatus> {
  const response = await fetch('/api/dti/evidence_status');
  if (!response.ok) throw new Error('研究证据状态暂不可用');
  const data = await response.json();
  if (!data || !['available', 'unavailable'].includes(data.status)) throw new Error('研究证据状态格式无法确认');
  if (data.status === 'available' && (
    typeof data.external_evaluation_completed !== 'boolean' || typeof data.admitted_count !== 'number' ||
    !Number.isInteger(data.reviewed_count) || !Number.isInteger(data.confirmed_point_count) ||
    data.reviewed_count <= 0 || typeof data.human_review !== 'string' ||
    data.confirmed_point_count < 0 || data.confirmed_point_count > data.reviewed_count ||
    !Array.isArray(data.candidates) || data.candidates.length !== data.reviewed_count ||
    data.candidates.some((candidate: Record<string, unknown>) => !candidate || typeof candidate.id !== 'string' || typeof candidate.label !== 'string' || typeof candidate.reason !== 'string' || typeof candidate.point_confirmed !== 'boolean' || !['admitted', 'pending_evidence', 'excluded'].includes(String(candidate.status))) ||
    new Set(data.candidates.map((candidate: { id: string }) => candidate.id)).size !== data.reviewed_count ||
    data.candidates.filter((candidate: { point_confirmed: boolean }) => candidate.point_confirmed).length !== data.confirmed_point_count ||
    typeof data.reviewed_at !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(data.reviewed_at)
  )) throw new Error('研究证据记录不完整');
  if (data.model_diagnostics !== undefined && (!data.model_diagnostics || typeof data.model_diagnostics !== 'object' || Array.isArray(data.model_diagnostics) || Object.values(data.model_diagnostics).some(value => !isModelDiagnostic(value)))) throw new Error('模型诊断记录不完整');
  return data;
}

export function useDTIEvidenceStatus() {
  const query = useQuery({ queryKey: ['dti-evidence-status'], queryFn: fetchDTIEvidenceStatus, staleTime: 30_000, retry: false });
  return { ...query, data: query.isError ? undefined : query.data };
}

export function evidenceNotice(data?: DTIEvidenceStatus): string {
  return data?.status === 'available'
    ? '计算预测用于研究探索；独立外部评价尚未完成，基准指标不代表该预测的实验准确度。'
    : '计算预测用于研究探索；独立外部评价状态无法确认。';
}

export const PREDICTION_SCOPE_NOTICE = '当前输出为计算探索分数；换算Kd未经实验确认，不能据此判断实测活性或可靠的靶点选择性。';

export function predictionScoreBand(pkd: number): string {
  if (!Number.isFinite(pkd)) return '分数无法确认';
  if (pkd >= 7) return 'pKd ≥ 7';
  if (pkd >= 6) return '6 ≤ pKd < 7';
  if (pkd >= 5) return '5 ≤ pKd < 6';
  return 'pKd < 5';
}

export function modelLimitationNotice(modelId?: string, data?: DTIEvidenceStatus, modelHash?: string): string {
  if (modelId !== 'f1_ridge') return '';
  const record = data?.status === 'available' ? data.model_diagnostics?.[modelId] : undefined;
  if (!isModelDiagnostic(record)) return 'F1模型限制记录暂无法确认，结果仅供计算探索。';
  if (modelHash && modelHash !== record.model_sha256) return '当前F1模型版本与已有诊断不一致，诊断限制的适用性尚未确认。';
  return `${record.summary} 基于${record.reviewed_at}冻结版本诊断${modelHash ? '' : '（当前版本尚未核对）'}。`;
}

export const EVIDENCE_CSV_HEADERS = ['Research_Evidence_Status', 'External_Evaluation_Completed', 'External_Admitted_Count', 'Evidence_Review_Date', 'External_MAE', 'External_RMSE', 'External_CI', 'Prediction_Use', 'Model_Limitations'];

export function evidenceCSVValues(data?: DTIEvidenceStatus, modelId?: string, modelHash?: string): Array<string | number> {
  const known = data?.status === 'available';
  const metricState = known ? 'not_evaluated' : 'unknown';
  return [known ? 'not_completed' : 'unknown', known ? 'false' : '', known ? data.admitted_count ?? '' : '', known ? data.reviewed_at ?? '' : '', metricState, metricState, metricState, `${evidenceNotice(data)} ${PREDICTION_SCOPE_NOTICE}`, modelLimitationNotice(modelId, data, modelHash)];
}

export function csvLine(values: Array<string | number>): string {
  return values.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',');
}

export function researchCopy(text: string): string {
  return text.replaceAll('高置信度领头物', '模型优先候选').replaceAll('高置信领头物', '模型优先候选')
    .replaceAll('实体分组无泄漏训练', '实体分组基准训练').replaceAll('双盲隔离训练', '基准划分训练')
    .replaceAll('贝叶斯校准 pKd', '反馈更新 pKd').replaceAll('确定性无效物', '模型低优先候选');
}

export function evidenceMarkdown(data?: DTIEvidenceStatus, modelId?: string, modelHash?: string): string {
  const limits = modelLimitationNotice(modelId, data, modelHash);
  return `\n\n## 研究证据与适用范围\n\n${evidenceNotice(data)} ${PREDICTION_SCOPE_NOTICE}\n\n证据复核日期：${data?.status === 'available' ? data.reviewed_at : '无法确认'}。外部评价指标：${data?.status === 'available' ? '未评估' : '无法确认'}。\n${limits ? `\n亲和力打分模型限制：${limits}\n` : ''}`;
}
