import React, { useState } from 'react';
import { Settings, X, Key, Sliders, ShieldAlert, Check, RotateCcw, Eye, EyeOff } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

const PROVIDER_PRESETS: Record<string, { apiBase: string; modelName: string; label: string }> = {
  deepseek: {
    label: 'DeepSeek (默认)',
    apiBase: 'https://api.deepseek.com/v1',
    modelName: 'deepseek-chat',
  },
  openai: {
    label: 'OpenAI',
    apiBase: 'https://api.openai.com/v1',
    modelName: 'gpt-4o',
  },
  anthropic: {
    label: 'Anthropic Claude',
    apiBase: 'https://api.anthropic.com/v1',
    modelName: 'claude-3-5-sonnet-20241022',
  },
  ollama: {
    label: 'Ollama (本地私有部署)',
    apiBase: 'http://localhost:11434/v1',
    modelName: 'llama3:latest',
  },
  custom: {
    label: '自定义提供商 (Custom)',
    apiBase: '',
    modelName: '',
  },
};

export function SettingsModal({ isOpen, onClose }: Props) {
  const {
    llmProvider,
    apiKey,
    apiBase,
    modelName,
    temperature,
    setLLMConfig,
  } = useAppStore();

  const [provider, setProvider] = useState(llmProvider || 'deepseek');
  const [key, setKey] = useState(apiKey || '');
  const [base, setBase] = useState(apiBase || 'https://api.deepseek.com/v1');
  const [model, setModel] = useState(modelName || 'deepseek-chat');
  const [temp, setTemp] = useState(temperature ?? 0.0);
  const [showKey, setShowKey] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  if (!isOpen) return null;

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    const preset = PROVIDER_PRESETS[newProvider];
    if (preset && newProvider !== 'custom') {
      setBase(preset.apiBase);
      setModel(preset.modelName);
    }
  };

  const handleSave = () => {
    setLLMConfig({
      llmProvider: provider,
      apiKey: key.trim(),
      apiBase: base.trim(),
      modelName: model.trim(),
      temperature: temp,
    });
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 600);
  };

  const handleReset = () => {
    const defaultPreset = PROVIDER_PRESETS['deepseek'];
    setProvider('deepseek');
    setKey('');
    setBase(defaultPreset.apiBase);
    setModel(defaultPreset.modelName);
    setTemp(0.0);
    setLLMConfig({
      llmProvider: 'deepseek',
      apiKey: '',
      apiBase: defaultPreset.apiBase,
      modelName: defaultPreset.modelName,
      temperature: 0.0,
    });
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4" role="dialog" aria-modal="true" aria-label="配置中心">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl w-full max-w-xl max-h-[90vh] flex flex-col animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/50">
          <div className="flex items-center gap-2.5 text-slate-800 dark:text-slate-100 font-semibold text-base">
            <Settings size={20} className="text-blue-600 dark:text-blue-400" />
            <span>配置中心 · 可拔插模型设置</span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-md transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          
          {/* Research Governance Banner */}
          <div className="p-3.5 rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/20 text-xs text-amber-900 dark:text-amber-300 space-y-1.5">
            <div className="flex items-center gap-2 font-semibold">
              <ShieldAlert size={16} className="text-amber-600 dark:text-amber-400 shrink-0" />
              <span>科研安全与确定性规范 (Research Provenance & Isolation)</span>
            </div>
            <p className="leading-relaxed">
              SafeAMP-Dual 报告工坊优先采用本地确定性算法（Evidence-Bounded Local Engine）以确保科研可重复性与序列防泄露。设置外部大模型仅用于辅助报告文本生成，生物物理打分与突变筛选严格由本地 ESM-2 驱动。
            </p>
          </div>

          {/* Provider Selection */}
          <div className="space-y-1.5">
            <label className="lab-label">大模型服务提供商 (LLM Provider)</label>
            <select
              value={provider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="lab-input text-xs"
            >
              {Object.entries(PROVIDER_PRESETS).map(([keyVal, preset]) => (
                <option key={keyVal} value={keyVal}>
                  {preset.label}
                </option>
              ))}
            </select>
          </div>

          {/* Model Name */}
          <div className="space-y-1.5">
            <label className="lab-label">模型标识 (Model Identifier)</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="例如 deepseek-chat 或 gpt-4o"
              className="lab-input font-mono text-xs"
            />
          </div>

          {/* API Base URL */}
          <div className="space-y-1.5">
            <label className="lab-label">接口服务地址 (API Base URL)</label>
            <input
              type="text"
              value={base}
              onChange={(e) => setBase(e.target.value)}
              placeholder="https://api.deepseek.com/v1"
              className="lab-input font-mono text-xs"
            />
          </div>

          {/* API Key */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="lab-label flex items-center gap-1">
                <Key size={12} />
                <span>API 访问凭证 (API Key)</span>
              </label>
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="text-[11px] text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center gap-1"
              >
                {showKey ? <EyeOff size={12} /> : <Eye size={12} />}
                <span>{showKey ? '隐藏' : '显示'}</span>
              </button>
            </div>
            <input
              type={showKey ? 'text' : 'password'}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="sk-..."
              className="lab-input font-mono text-xs"
            />
            <p className="text-[11px] text-slate-400">
              凭证仅保存在浏览器本地会话与客户端缓存中，不上传至公共网络。
            </p>
          </div>

          {/* Temperature Slider */}
          <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <label className="lab-label flex items-center gap-1 mb-0">
                <Sliders size={12} />
                <span>采样温度 (Temperature): {temp.toFixed(1)}</span>
              </label>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                {temp === 0.0 ? '0.0 (确定性输出)' : temp < 0.5 ? '低发散度' : '高探索度'}
              </span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.1"
              value={temp}
              onChange={(e) => setTemp(parseFloat(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>0.0 (严谨科研报告)</span>
              <span>0.5 (平衡)</span>
              <span>1.0 (高度多样化)</span>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center gap-1 hover:underline"
          >
            <RotateCcw size={13} />
            <span>恢复默认</span>
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-lab-secondary text-xs px-3 py-1.5"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="btn-lab-primary text-xs px-4 py-1.5 flex items-center gap-1.5"
            >
              {savedSuccess ? <Check size={14} /> : null}
              <span>{savedSuccess ? '已保存配置' : '保存设置'}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
