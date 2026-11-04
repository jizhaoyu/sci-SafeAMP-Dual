import type { CartItem } from '../types/entity';

/** Scientific scores have different meanings; legacy TSI is never a molecule pKd. */
export function cartScore(item: Pick<CartItem, 'kind' | 'pkd' | 'tsi'> & {item_type?: string}): number | null {
  const molecule = item.kind === 'small_molecule' || item.item_type === 'small_molecule';
  const value = molecule ? item.pkd : item.tsi;
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
