/**
 * Physicochemical descriptors, Lipinski Rule of 5 evaluation, and molecule export utilities.
 */

export interface DrugLikenessResult {
  mw: number;
  logp: number;
  hbd: number;
  hba: number;
  tpsa: number;
  rotatable_bonds: number;
  ro5_violations: number;
  ro5_pass: boolean;
  druglikeness_tier: string;
  badge_color: 'emerald' | 'amber' | 'rose';
}

export function computeDrugLikeness(smiles: string): DrugLikenessResult {
  const s = smiles.trim();

  // Atom weights
  const atomWeights: Record<string, number> = {
    C: 12.011, c: 12.011,
    N: 14.007, n: 14.007,
    O: 15.999, o: 15.999,
    F: 18.998,
    P: 30.974,
    S: 32.06, s: 32.06,
    Cl: 35.45,
    Br: 79.904,
    I: 126.90,
    H: 1.008,
  };

  const numCl = (s.match(/Cl/g) || []).length;
  const numBr = (s.match(/Br/g) || []).length;
  const cleanS = s.replace(/Cl|Br/g, '');

  const numC = (cleanS.match(/[Cc]/g) || []).length;
  const numN = (cleanS.match(/[Nn]/g) || []).length;
  const numO = (cleanS.match(/[Oo]/g) || []).length;
  const numF = (cleanS.match(/F/g) || []).length;
  const numS = (cleanS.match(/[Ss]/g) || []).length;
  const numP = (cleanS.match(/P/g) || []).length;

  const numDouble = (s.match(/=/g) || []).length;
  const numTriple = (s.match(/#/g) || []).length;
  const numRings = (s.match(/[0-9]/g) || []).length;

  const approxH = Math.max(0, numC * 2 + 2 - numDouble * 2 - numTriple * 4 - numRings);
  const mw =
    numC * atomWeights.C +
    numN * atomWeights.N +
    numO * atomWeights.O +
    numF * atomWeights.F +
    numCl * atomWeights.Cl +
    numBr * atomWeights.Br +
    numS * atomWeights.S +
    numP * atomWeights.P +
    approxH * atomWeights.H;

  // Hydrogen Bond Donors (HBD): OH and NH
  let hbd = (s.match(/O[Hh]|N[Hh]|\[nH\]|\[NH\]/g) || []).length;
  if (hbd === 0) {
    hbd = Math.floor((s.match(/[Nn][^=]/g) || []).length / 3);
  }

  // Hydrogen Bond Acceptors (HBA): N and O
  const hba = numN + numO;

  // LogP approximation (Ghose-Crippen based fragment heuristic)
  const logpContrib =
    numC * 0.25 +
    numCl * 0.65 +
    numBr * 0.85 +
    numF * 0.15 -
    numN * 0.45 -
    numO * 0.40 +
    numS * 0.35;
  const approxLogp = Math.round(logpContrib * 100) / 100;

  // TPSA approximation (Topological Polar Surface Area in Å²)
  const approxTpsa = Math.round((numN * 14.5 + numO * 18.0 + numS * 25.0) * 10) / 10;

  // Rotatable Bonds (non-ring single bonds heuristic)
  const rotBonds = Math.max(0, Math.floor((s.replace(/[0-9()=#]/g, '').match(/[A-Za-z][A-Za-z]/g) || []).length / 3));

  // Lipinski Rule of 5 violations:
  let violations = 0;
  if (mw > 500.0) violations += 1;
  if (approxLogp > 5.0) violations += 1;
  if (hbd > 5) violations += 1;
  if (hba > 10) violations += 1;

  let tier = '口服成药性优良 (Ro5 符合)';
  let badgeColor: 'emerald' | 'amber' | 'rose' = 'emerald';
  if (violations === 1) {
    tier = '口服成药性良好 (1项微偏)';
    badgeColor = 'amber';
  } else if (violations >= 2) {
    tier = '高分子量/低口服透膜';
    badgeColor = 'rose';
  }

  return {
    mw: Math.round(mw * 10) / 10,
    logp: approxLogp,
    hbd,
    hba,
    tpsa: approxTpsa,
    rotatable_bonds: rotBonds,
    ro5_violations: violations,
    ro5_pass: violations <= 1,
    druglikeness_tier: tier,
    badge_color: badgeColor,
  };
}

export function exportSmallMoleculesCSV(
  molecules: Array<{
    name: string;
    smiles: string;
    pkd: number;
    kd_nM?: number;
    addedAt?: string;
  }>
) {
  if (molecules.length === 0) return;

  const header = 'Molecule_Name,SMILES,Predicted_pKd,Predicted_Kd_nM,Affinity_Tier,MW_g_mol,LogP,HBD,HBA,TPSA_A2,Ro5_Violations,Added_At\n';
  const rows = molecules.map(m => {
    const prop = computeDrugLikeness(m.smiles);
    const kd = m.kd_nM ?? Math.round(Math.pow(10, 9.0 - m.pkd) * 100) / 100;
    const tier = kd < 100 ? 'High (<100nM)' : kd <= 1000 ? 'Moderate (100nM-1uM)' : 'Weak (>1uM)';
    return `"${m.name}","${m.smiles}",${m.pkd.toFixed(3)},${kd.toFixed(2)},"${tier}",${prop.mw},${prop.logp},${prop.hbd},${prop.hba},${prop.tpsa},${prop.ro5_violations},"${m.addedAt || new Date().toISOString()}"`;
  }).join('\n');

  const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `SafeAMP_DTI_Small_Molecules_${Date.now()}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export interface AtomNode {
  id: number;
  symbol: string;
  x: number;
  y: number;
  color: string;
  isHetero: boolean;
}

export interface BondEdge {
  from: number;
  to: number;
  order: number; // 1 = single, 2 = double, 1.5 = aromatic
}

export const ATOM_COLORS: Record<string, string> = {
  O: '#ef4444', // red
  N: '#3b82f6', // blue
  S: '#f59e0b', // amber
  F: '#10b981', // emerald
  Cl: '#059669', // green
  Br: '#8b5cf6', // purple
  I: '#a855f7', // violet
  P: '#ec4899', // pink
  C: '#64748b', // slate
};

export function parseSmilesTo2D(smiles: string): { nodes: AtomNode[]; bonds: BondEdge[] } {
  const s = smiles.trim();
  const nodes: AtomNode[] = [];
  const bonds: BondEdge[] = [];

  let curX = 40;
  let curY = 60;
  let curAngle = 0; // degrees
  const bondLength = 28;

  // Track ring openings: ringId -> atomIndex
  const ringOpenings: Record<string, number> = {};
  const branchStack: Array<{ x: number; y: number; angle: number; lastAtomId: number }> = [];

  let lastAtomId: number | null = null;
  let nextBondOrder = 1;

  let i = 0;
  while (i < s.length) {
    const ch = s[i];

    if (ch === '(') {
      if (lastAtomId !== null) {
        branchStack.push({
          x: curX,
          y: curY,
          angle: curAngle,
          lastAtomId,
        });
        curAngle += 60; // Diverge branch
      }
      i++;
      continue;
    }

    if (ch === ')') {
      const top = branchStack.pop();
      if (top) {
        curX = top.x;
        curY = top.y;
        curAngle = top.angle - 60; // Alternative direction
        lastAtomId = top.lastAtomId;
      }
      i++;
      continue;
    }

    if (ch === '=') {
      nextBondOrder = 2;
      i++;
      continue;
    }

    if (ch === '#') {
      nextBondOrder = 3;
      i++;
      continue;
    }

    if (/\d/.test(ch)) {
      const ringId = ch;
      if (lastAtomId !== null) {
        if (ringOpenings[ringId] !== undefined) {
          // Close ring
          bonds.push({
            from: ringOpenings[ringId],
            to: lastAtomId,
            order: 1.5,
          });
          delete ringOpenings[ringId];
        } else {
          // Open ring
          ringOpenings[ringId] = lastAtomId;
        }
      }
      i++;
      continue;
    }

    // Handle square bracket atom expression: [nH], [C@@H], [O-], [NH+], [Cl-], etc.
    if (ch === '[') {
      const closeIdx = s.indexOf(']', i);
      if (closeIdx !== -1) {
        const inside = s.substring(i + 1, closeIdx);
        // Strip leading digits (isotopes like 13C, 2H)
        const stripped = inside.replace(/^\d+/, '');

        let sym = '';
        let isAromatic = false;

        // Check 2-letter element first (case-insensitive Cl, Br, Si, Se, Pt, Fe, Cu, Zn, Na, etc.)
        const twoLetterMatch = stripped.match(/^(Cl|Br|Si|Se|Pt|Fe|Cu|Zn|Na|Mg|Ca|Li|Al|As|se|as)/i);
        if (twoLetterMatch) {
          const raw = twoLetterMatch[1];
          sym = raw.charAt(0).toUpperCase() + raw.charAt(1).toLowerCase();
          if (raw === 'se' || raw === 'as') {
            isAromatic = true;
          }
        } else if (stripped.length > 0) {
          const firstChar = stripped.charAt(0);
          if (/[a-z]/.test(firstChar)) {
            isAromatic = true;
            sym = firstChar.toUpperCase();
          } else if (/[A-Z]/.test(firstChar)) {
            sym = firstChar;
          }
        }

        i = closeIdx;

        if (sym && /[A-Z]/.test(sym)) {
          const id = nodes.length;

          // Calculate position
          if (lastAtomId !== null) {
            const rad = (curAngle * Math.PI) / 180;
            curX += bondLength * Math.cos(rad);
            curY += bondLength * Math.sin(rad);

            bonds.push({
              from: lastAtomId,
              to: id,
              order: isAromatic ? 1.5 : nextBondOrder,
            });
            nextBondOrder = 1;

            // Alternate zigzag angle
            curAngle = (id % 2 === 0 ? curAngle + 60 : curAngle - 60) % 360;
          }

          const isHetero = sym !== 'C';
          nodes.push({
            id,
            symbol: sym,
            x: curX,
            y: curY,
            color: ATOM_COLORS[sym] || '#64748b',
            isHetero,
          });

          lastAtomId = id;
        }

        i++;
        continue;
      }
    }

    // Atom identification
    let sym = ch.toUpperCase();
    let isAromatic = ch === 'c' || ch === 'n' || ch === 'o' || ch === 's';

    // Handle two-letter elements like Cl, Br
    if (i + 1 < s.length) {
      const pair = s.substring(i, i + 2);
      if (pair === 'Cl' || pair === 'Br') {
        sym = pair;
        i++;
      }
    }

    if (/[A-Z]/.test(sym)) {
      const id = nodes.length;

      // Calculate position
      if (lastAtomId !== null) {
        const rad = (curAngle * Math.PI) / 180;
        curX += bondLength * Math.cos(rad);
        curY += bondLength * Math.sin(rad);

        bonds.push({
          from: lastAtomId,
          to: id,
          order: isAromatic ? 1.5 : nextBondOrder,
        });
        nextBondOrder = 1;

        // Alternate zigzag angle
        curAngle = (id % 2 === 0 ? curAngle + 60 : curAngle - 60) % 360;
      }

      const isHetero = sym !== 'C';
      nodes.push({
        id,
        symbol: sym,
        x: curX,
        y: curY,
        color: ATOM_COLORS[sym] || '#64748b',
        isHetero,
      });

      lastAtomId = id;
    }

    i++;
  }

  return { nodes, bonds };
}
