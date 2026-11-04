import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChemicalEntity, SmallMoleculeEntity, PeptideEntity, TargetContext, CartItem } from '../types/entity';

export interface CartPeptide extends CartItem {
  item_type?: 'peptide' | 'small_molecule';
}

interface AppState {
  // 可拔插大模型配置 (Pluggable Model Config)
  llmProvider: string;
  apiKey: string;
  apiBase: string;
  modelName: string;
  temperature: number;
  setLLMConfig: (config: Partial<Pick<AppState, 'llmProvider' | 'apiKey' | 'apiBase' | 'modelName' | 'temperature'>>) => void;

  // 带类型的分子与靶点上下文 (Typed Entity & Target Context)
  activeEntity: ChemicalEntity | null;
  activeTarget: TargetContext | null;
  setActiveSmallMolecule: (smiles: string, name?: string, source?: string) => void;
  setActivePeptide: (seq: string, name?: string, source?: string) => void;
  setActiveEntity: (entity: ChemicalEntity | null) => void;
  setActiveTarget: (target: TargetContext | null) => void;
  clearActiveEntity: () => void;

  // 跨模块流通分子 (向后兼容已有组件)
  activeSequence: string;
  activePeptideName: string;

  // 候选分子库 (Peptide / Molecule Cart)
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

      activeEntity: {
        kind: 'peptide',
        sequence: 'GIGAVLKVLTTGLPALISWIKRKRQQ',
        name: 'Melittin (蜂毒素)',
        source: 'Default Preset'
      },
      activeTarget: null,

      activeSequence: 'GIGAVLKVLTTGLPALISWIKRKRQQ',
      activePeptideName: 'Melittin (蜂毒素)',

      setActiveSmallMolecule: (smiles: string, name?: string, source?: string) => {
        // Protect SMILES casing: trim only, NEVER convert to uppercase
        const cleanSmiles = (smiles || '').trim();
        const molName = name || 'Custom Small Molecule';
        const entity: SmallMoleculeEntity = {
          kind: 'small_molecule',
          smiles: cleanSmiles,
          name: molName,
          source
        };
        set({
          activeEntity: entity,
          activeSequence: cleanSmiles,
          activePeptideName: molName
        });
      },

      setActivePeptide: (seq: string, name?: string, source?: string) => {
        // Only standard amino acid sequences are standardized to uppercase
        const cleanSeq = (seq || '').trim().toUpperCase();
        const pepName = name || 'Custom Peptide';
        const entity: PeptideEntity = {
          kind: 'peptide',
          sequence: cleanSeq,
          name: pepName,
          source
        };
        set({
          activeEntity: entity,
          activeSequence: cleanSeq,
          activePeptideName: pepName
        });
      },

      setActiveEntity: (entity: ChemicalEntity | null) => {
        if (!entity) {
          set({ activeEntity: null, activeSequence: '', activePeptideName: '' });
          return;
        }
        if (entity.kind === 'small_molecule') {
          set({
            activeEntity: entity,
            activeSequence: entity.smiles,
            activePeptideName: entity.name
          });
        } else {
          set({
            activeEntity: entity,
            activeSequence: entity.sequence,
            activePeptideName: entity.name
          });
        }
      },

      setActiveTarget: (target: TargetContext | null) => set({ activeTarget: target }),

      clearActiveEntity: () => set({ activeEntity: null, activeSequence: '', activePeptideName: '' }),

      cart: [],
      addToCart: (peptide) => {
        const { cart } = get();
        const exists = cart.some(p => p.sequence === peptide.sequence);
        if (exists) return false;
        
        const itemType = peptide.item_type || (peptide.kind === 'small_molecule' ? 'small_molecule' : 'peptide');
        const newEntry: CartPeptide = {
          ...peptide,
          kind: peptide.kind || (itemType === 'small_molecule' ? 'small_molecule' : 'peptide'),
          item_type: itemType,
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
      name: 'dti-lab-workspace-v1',
      version: 7,
      partialize: (state) => ({
        activeEntity: state.activeEntity,
        activeTarget: state.activeTarget,
        activeSequence: state.activeSequence,
        activePeptideName: state.activePeptideName,
        cart: state.cart,
        llmProvider: state.llmProvider,
        apiBase: state.apiBase,
        modelName: state.modelName,
        temperature: state.temperature,
      }),
      migrate: (persistedState: any, version: number) => {
        const state = persistedState || {};
        const oldSeq = (state.activeSequence || '').trim();
        const oldName = (state.activePeptideName || '').trim();

        let migratedEntity: ChemicalEntity | null = state.activeEntity || null;

        // Correct previous misclassification from older versions (v5/v6)
        if (migratedEntity && version < 7) {
          if (migratedEntity.kind === 'peptide') {
            const seq = (migratedEntity.sequence || '').trim();
            // CCO or other common small molecules mistakenly labeled as peptide
            if (/^(CCO|CC|CCC|CCCC|CCN|CCOC|CCOCC)$/i.test(seq) || /[=#()0-9cnosp]/.test(seq) || /O/i.test(seq)) {
              migratedEntity = {
                kind: 'small_molecule',
                smiles: seq,
                name: migratedEntity.name || 'Migrated Molecule'
              };
            }
          } else if (migratedEntity.kind === 'unconfirmed') {
            const seq = (migratedEntity.sequence || '').trim();
            // Melittin or unambiguous standard peptides wrongly fallen into unconfirmed
            const hasSmilesSyntax = /[0-9=#()[\]@\-+\\/%]/.test(seq) || /[cnosp]/.test(seq);
            const isStandardPeptide = /^[ACDEFGHIKLMNPQRSTVWY]{4,}$/.test(seq.toUpperCase()) && !hasSmilesSyntax && !/[OBJZ]/.test(seq.toUpperCase());
            if (isStandardPeptide) {
              migratedEntity = {
                kind: 'peptide',
                sequence: seq.toUpperCase(),
                name: migratedEntity.name || 'Migrated Peptide'
              };
            }
          }
        }

        if (!migratedEntity && oldSeq) {
          if (state.kind === 'small_molecule' || state.item_type === 'small_molecule') {
            migratedEntity = {
              kind: 'small_molecule',
              smiles: oldSeq,
              name: oldName || 'Migrated Molecule'
            };
          } else if (state.kind === 'peptide' || state.item_type === 'peptide') {
            migratedEntity = {
              kind: 'peptide',
              sequence: oldSeq.toUpperCase(),
              name: oldName || 'Migrated Peptide'
            };
          } else {
            // Case-sensitive SMILES syntax: ring digits, bonds, lowercase aromatic [cnosp]
            const hasSmilesSyntax = /[0-9=#()[\]@\-+\\/%]/.test(oldSeq) || /[cnosp]/.test(oldSeq);
            const isCommonFormula = /^(CCO|CC|CCC|CCCC|CCN|CCOC|CCOCC|C#N|C=O)$/i.test(oldSeq);
            const isUnambiguousSmiles = hasSmilesSyntax || isCommonFormula;

            // Unambiguous peptide: standard 20 amino acids (ACDEFGHIKLMNPQRSTVWY), length >= 4, no lowercase, no digits, no O
            const isUnambiguousPeptide = /^[ACDEFGHIKLMNPQRSTVWY]{4,}$/.test(oldSeq.toUpperCase()) && !hasSmilesSyntax && !/[OBJZ]/.test(oldSeq.toUpperCase());

            if (isUnambiguousSmiles && !isUnambiguousPeptide) {
              migratedEntity = {
                kind: 'small_molecule',
                smiles: oldSeq,
                name: oldName || 'Migrated Molecule'
              };
            } else if (isUnambiguousPeptide && !isUnambiguousSmiles) {
              migratedEntity = {
                kind: 'peptide',
                sequence: oldSeq.toUpperCase(),
                name: oldName || 'Migrated Peptide'
              };
            } else {
              // Ambiguous: preserve raw sequence and mark as unconfirmed
              migratedEntity = {
                kind: 'unconfirmed',
                sequence: oldSeq,
                name: oldName || 'Unconfirmed Entity'
              };
            }
          }
        }

        const migratedCart: CartPeptide[] = (Array.isArray(state.cart) ? state.cart : []).map((item: any) => {
          const kind = item.kind || (item.item_type === 'small_molecule' ? 'small_molecule' : 'peptide');
          return {
            ...item,
            kind,
            item_type: item.item_type || (kind === 'small_molecule' ? 'small_molecule' : 'peptide'),
            sequence: item.sequence || item.smiles || ''
          };
        });

        return {
          ...state,
          activeEntity: migratedEntity,
          activeTarget: state.activeTarget || null,
          activeSequence: oldSeq,
          activePeptideName: oldName,
          cart: migratedCart,
          llmProvider: state.llmProvider ?? 'deepseek',
          apiBase: state.apiBase ?? 'https://api.deepseek.com/v1',
          modelName: state.modelName ?? 'deepseek-chat',
          temperature: state.temperature ?? 0.0,
        };
      },
      // Discard credentials in cache
      merge: (persisted, current) => ({ ...current, ...(persisted as Partial<AppState>), apiKey: '' }),
    }
  )
);
