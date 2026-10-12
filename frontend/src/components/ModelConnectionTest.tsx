import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { LoaderCircle, PlugZap } from 'lucide-react';
import { apiClient } from '../api/client';

interface Props { provider: string; apiKey: string; base: string; model: string }
interface Result {
  status: 'connected';
  requested_model: string;
  returned_model: string;
  duration_seconds_full_response: number;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
}

export function ModelConnectionTest({ provider, apiKey, base, model }: Props) {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const request = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => { request.current?.abort(); request.current = null; };
  }, []);

  const testConnection = async () => {
    request.current?.abort();
    setResult(null);
    setError('');
    if (!['deepseek', 'openai', 'custom', 'ollama'].includes(provider)) {
      if (provider === 'anthropic') {
        setError('Anthropic 官方原生协议不同。若使用 Claude 兼容中转代理，请将服务商选择为“自定义提供商 (Custom)”并填写代理地址。');
      } else {
        setError('连接测试目前支持 DeepSeek、OpenAI、自定义提供商 (Custom) 及 Ollama 本地模型。');
      }
      return;
    }
    const trimmedKey = apiKey.trim() || (provider === 'ollama' ? 'ollama' : '');
    if (!trimmedKey || !base.trim() || !model.trim()) {
      setError('请填写 API Key、接口服务地址和模型标识。');
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    try {
      const response = await apiClient.post<Result>('/api/llm/test_connection', {
        provider, api_key: trimmedKey, base_url: base.trim(), model_name: model.trim(),
      }, { signal: controller.signal, timeout: 55000 });
      if (request.current === controller) setResult(response.data);
    } catch (cause: unknown) {
      if (controller.signal.aborted || request.current !== controller) return;
      if (axios.isAxiosError(cause)) {
        // Never surface Axios request config, which includes the credential.
        const data = cause.response?.data;
        const message = typeof data?.message === 'string' ? data.message :
          cause.code === 'ECONNABORTED' ? '等待超时；后端请求可能仍在完成，请稍后手动重试。' : '无法完成连接测试，请检查本地后端服务。';
        setError(apiKey.trim() ? message.replaceAll(apiKey.trim(), '[REDACTED]') : message);
      } else setError('连接测试失败，请检查本地后端服务。');
    } finally {
      if (request.current === controller) { request.current = null; setBusy(false); }
    }
  };

  return (
    <section className="space-y-2 pt-3 border-t border-slate-100 dark:border-slate-800" aria-label="模型连接测试">
      <button type="button" className="btn-lab-secondary text-xs flex items-center gap-2" disabled={busy} onClick={testConnection}>
        {busy ? <LoaderCircle size={14} className="animate-spin" /> : <PlugZap size={14} />}
        {busy ? '正在测试连接…' : '测试当前配置连接'}
      </button>
      <p className="text-[11px] text-slate-500 leading-relaxed">
        支持 DeepSeek、OpenAI 以及各类兼容 OpenAI 规范的自定义服务商（如 Grok、Claude 代理、Ollama、OneAPI 等）。测试将凭证经本地后端发送给所选服务商，仅请求固定中性短文本，可能产生微量 token 费用；不发送研究数据。测试不会保存草稿。
      </p>
      <div aria-live="polite" role="status" className="text-xs">
        {error && <p className="text-red-700 dark:text-red-400 break-words">{error}</p>}
        {result && <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200 space-y-1 break-words">
          <p className="font-semibold">连接成功 · 固定响应已验证</p>
          <p>请求模型：{result.requested_model}</p>
          <p>实际返回模型：{result.returned_model}</p>
          <p>完整响应耗时：{result.duration_seconds_full_response.toFixed(3)} 秒</p>
          <p>Token：输入 {result.usage.prompt_tokens} / 输出 {result.usage.completion_tokens} / 总计 {result.usage.total_tokens}</p>
          <p>此结果仅验证连接，科研模型就绪状态与研究门禁仍单独判定。</p>
        </div>}
      </div>
    </section>
  );
}
