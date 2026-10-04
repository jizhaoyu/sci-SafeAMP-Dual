import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface CartPeptide {
  id: string;
  sequence: string;
  name: string;
  p_amp: number;
  p_hemo: number;
  tsi: number;
  is_short?: boolean;
  addedAt: string;
  run_id?: string;
}

interface AppState {
  // 可拔插大模型配置 (Pluggable Model Config)
  llmProvider: string;
  apiKey: string;
  apiBase: string;
  modelName: string;
  temperature: number;
  setLLMConfig: (config: Partial<Pick<AppState, 'llmProvider' | 'apiKey' | 'apiBase' | 'modelName' | 'temperature'>>) => void;

  // 跨模块流通分子 (Active Peptide across Studios)
  activeSequence: string;
  activePeptideName: string;
  setActivePeptide: (seq: string, name?: string) => void;

  // 候选分子库 (Peptide Cart)
  cart: CartPeptide[];
  addToCart: (peptide: Omit<CartPeptide, 'id' | 'addedAt'>) => boolean;
  removeFromCart: (id: string) => void;
  clearCart: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      llmProvider: 'deepseek',
      apiKey: '',
      apiBase: 'https://api.deepseek.com/v1',
      modelName: 'deepseek-chat',
      temperature: 0.0,
      setLLMConfig: (config) => set((state) => ({ ...state, ...config })),

      activeSequence: 'GIGAVLKVLTTGLPALISWIKRKRQQ',
      activePeptideName: 'Melittin (蜂毒素)',
      setActivePeptide: (seq, name) => set({ 
        activeSequence: seq.trim().toUpperCase(), 
        activePeptideName: name || 'Custom Peptide' 
      }),

      cart: [],
      addToCart: (peptide) => {
        const { cart } = get();
        const exists = cart.some(p => p.sequence === peptide.sequence);
        if (exists) return false;
        
        const newEntry: CartPeptide = {
          ...peptide,
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
          addedAt: new Date().toLocaleTimeString(),
        };
        set({ cart: [newEntry, ...cart] });
        return true;
      },
      removeFromCart: (id) => set((state) => ({ cart: state.cart.filter(p => p.id !== id) })),
      clearCart: () => set({ cart: [] }),
    }),
    {
      name: 'safeamp-lab-workspace-v3',
      version: 4,
      partialize: (state) => ({
        activeSequence: state.activeSequence,
        activePeptideName: state.activePeptideName,
        cart: state.cart,
        llmProvider: state.llmProvider,
        apiKey: state.apiKey,
        apiBase: state.apiBase,
        modelName: state.modelName,
        temperature: state.temperature,
      }),
      migrate: (state: any) => ({
        activeSequence: state?.activeSequence ?? '',
        activePeptideName: state?.activePeptideName ?? '',
        cart: (Array.isArray(state?.cart) ? state.cart : []) as CartPeptide[],
        llmProvider: state?.llmProvider ?? 'deepseek',
        apiKey: state?.apiKey ?? '',
        apiBase: state?.apiBase ?? 'https://api.deepseek.com/v1',
        modelName: state?.modelName ?? 'deepseek-chat',
        temperature: state?.temperature ?? 0.0,
      }),
    }
  )
);
