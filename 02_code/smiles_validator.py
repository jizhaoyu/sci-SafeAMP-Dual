"""
Independent SMILES string validator for DTI Inference and Molecular Processing.

Provides strict structural, syntax, valence, coordination number, and aromaticity
validation without altering molecular parsing or feature generation fingerprints
in downstream models.
"""

import re
from typing import Set, Optional, Dict, List

# Complete chemical periodic table elements
PERIODIC_TABLE: Set[str] = {
    'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
    'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca',
    'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
    'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr',
    'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
    'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
    'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
    'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
    'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
    'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm',
    'Md', 'No', 'Lr',
    # Aromatic symbols supported in SMILES
    'b', 'c', 'n', 'o', 'p', 's', 'se', 'as'
}

ORGANIC_SUBSET: Set[str] = {'B', 'C', 'N', 'O', 'P', 'S', 'F', 'Cl', 'Br', 'I', 'b', 'c', 'n', 'o', 'p', 's'}
BOND_CHARS: Set[str] = {'-', '=', '#', '$', ':', '/', '\\'}
BOND_ORDERS = {'-': 1.0, '=': 2.0, '#': 3.0, '$': 4.0, ':': 1.5, '/': 1.0, '\\': 1.0}

BRACKET_REGEX = re.compile(r'^\[([0-9]*)([A-Z][a-z]?|[a-z])(@{0,2})(H[0-9]*)?([+-]\d*|\++|-+)?(:[0-9]+)?\]$')


def parse_charge(charge_str: Optional[str]) -> int:
    """Parse formal charge from bracket atom match."""
    if not charge_str:
        return 0
    if charge_str == '+':
        return 1
    if charge_str == '-':
        return -1
    if all(c == '+' for c in charge_str):
        return len(charge_str)
    if all(c == '-' for c in charge_str):
        return -len(charge_str)
    if charge_str.startswith('+'):
        return int(charge_str[1:]) if len(charge_str) > 1 else 1
    if charge_str.startswith('-'):
        return -int(charge_str[1:]) if len(charge_str) > 1 else -1
    return 0


def parse_h_count(h_str: Optional[str]) -> int:
    """Parse explicit hydrogen count from bracket atom match."""
    if not h_str:
        return 0
    if h_str == 'H':
        return 1
    return int(h_str[1:])


def validate_atom_valence(atom: dict, fragment: str) -> None:
    """Validate chemical valence and coordination constraints of an atom."""
    elem = atom['symbol']
    charge = atom['charge']
    h_count = atom['h_count']
    bonds = atom['bonds']
    neighbors = atom['neighbors']
    coord_num = len(neighbors) + h_count
    total_valence = sum(bonds) + float(h_count)
    single_bonds = sum(1 for b in bonds if b == 1.0) + h_count

    # Period 2 elements (B, C, N, O, F) only have 4 valence orbitals (one 2s + three 2p).
    # Their coordination number (bonded neighbors + explicit H) can NEVER exceed 4.
    if elem in {'B', 'C', 'N', 'O', 'F', 'b', 'c', 'n', 'o'}:
        if coord_num > 4:
            raise ValueError(
                f"Invalid SMILES: Period 2 element '{elem}' exceeds maximum coordination number of 4 "
                f"(has {coord_num} connections) in '{fragment}'"
            )

    # 1. Carbon (C, c)
    if elem in {'C', 'c'}:
        if total_valence > 4.0:
            raise ValueError(
                f"Invalid SMILES: carbon atom valence exceeded: {total_valence} bonds > 4 in fragment '{fragment}'"
            )

    # 2. Oxygen (O, o)
    elif elem in {'O', 'o'}:
        if charge == 0:
            if coord_num > 2 or total_valence > 2.0:
                raise ValueError(
                    f"Invalid SMILES: neutral oxygen atom valence exceeded: {total_valence} bonds > 2 in fragment '{fragment}'"
                )
        elif charge > 0:
            if coord_num > 3 or total_valence > 3.0:
                raise ValueError(
                    f"Invalid SMILES: [O+] atom valence exceeded: {total_valence} bonds > 3 in fragment '{fragment}'"
                )
        elif charge < 0:
            if coord_num > 1 or total_valence > 1.0:
                raise ValueError(
                    f"Invalid SMILES: [O-] atom valence exceeded: {total_valence} bonds > 1 in fragment '{fragment}'"
                )

    # 3. Fluorine (F)
    elif elem == 'F':
        if coord_num > 1 or total_valence > 1.0:
            raise ValueError(
                f"Invalid SMILES: fluorine atom valence exceeded: {total_valence} bonds > 1 in fragment '{fragment}'"
            )

    # 4. Other Halogens (Cl, Br, I)
    elif elem in {'Cl', 'Br', 'I'}:
        if not atom['is_bracket'] and (coord_num > 1 or total_valence > 1.0):
            raise ValueError(
                f"Invalid SMILES: halogen {elem} atom valence exceeded: {total_valence} bonds > 1 in fragment '{fragment}'"
            )

    # 5. Nitrogen (N, n)
    elif elem in {'N', 'n'}:
        if charge == 0:
            # Neutral nitrogen ground state (2s2 2p3) can form at most 3 single bonds (e.g. amines).
            # Pentavalent neutral nitrogen (e.g. nitro) requires double bonds to oxygen.
            if single_bonds > 3:
                raise ValueError(
                    f"Invalid SMILES: neutral nitrogen cannot have {single_bonds} single bonds in fragment '{fragment}'"
                )
            if total_valence > 5.0:
                raise ValueError(
                    f"Invalid SMILES: nitrogen atom valence exceeded: {total_valence} bonds > 5 in fragment '{fragment}'"
                )
            if 3.0 < total_valence < 5.0:
                raise ValueError(
                    f"Invalid SMILES: neutral nitrogen cannot have valence {total_valence} in fragment '{fragment}'"
                )
        elif charge == 1:
            # [N+] is isoelectronic with carbon (e.g. quaternary ammonium, ammonium)
            if total_valence > 4.0:
                raise ValueError(
                    f"Invalid SMILES: [N+] atom valence exceeded: {total_valence} bonds > 4 in fragment '{fragment}'"
                )
        elif charge >= 2:
            # Higher positive formal charges reduce available valence electrons
            if coord_num > 3 or total_valence > 3.0:
                raise ValueError(
                    f"Invalid SMILES: [N+{charge}] atom exceeds allowable valence/coordination ({total_valence} bonds) in fragment '{fragment}'"
                )
        elif charge < 0:
            if coord_num > 2 or total_valence > 2.0:
                raise ValueError(
                    f"Invalid SMILES: [N-] atom valence exceeded: {total_valence} bonds > 2 in fragment '{fragment}'"
                )

    # 6. Sulfur (S, s)
    elif elem in {'S', 's'}:
        if total_valence > 6.0:
            raise ValueError(
                f"Invalid SMILES: sulfur atom valence exceeded: {total_valence} bonds > 6 in fragment '{fragment}'"
            )

    # 7. Phosphorus (P, p)
    elif elem in {'P', 'p'}:
        if total_valence > 5.0:
            raise ValueError(
                f"Invalid SMILES: phosphorus atom valence exceeded: {total_valence} bonds > 5 in fragment '{fragment}'"
            )

    # 8. Boron (B, b)
    elif elem in {'B', 'b'}:
        max_b = 4.0 if charge == -1 else 3.0
        if total_valence > max_b:
            raise ValueError(
                f"Invalid SMILES: boron atom valence exceeded: {total_valence} bonds > {max_b} in fragment '{fragment}'"
            )

    # 9. Hydrogen (H)
    elif elem == 'H':
        if total_valence > 1.0:
            raise ValueError(
                f"Invalid SMILES: hydrogen atom valence exceeded: {total_valence} bonds > 1 in fragment '{fragment}'"
            )


def validate_smiles_fragment(fragment: str) -> None:
    """Validate a single connected SMILES fragment."""
    if not fragment:
        raise ValueError("Empty SMILES fragment.")

    if '()' in fragment or '[]' in fragment:
        raise ValueError(f"Empty branch or empty bracket in SMILES fragment: '{fragment}'")

    if fragment.count('(') != fragment.count(')'):
        raise ValueError(f"Unmatched parentheses in SMILES: '{fragment}'")
    if fragment.count('[') != fragment.count(']'):
        raise ValueError(f"Unmatched square brackets in SMILES: '{fragment}'")

    if fragment[0] in BOND_CHARS:
        raise ValueError(f"SMILES fragment cannot start with a bond: '{fragment[0]}'")
    if fragment[-1] in BOND_CHARS:
        raise ValueError(f"SMILES fragment cannot end with a bond: '{fragment[-1]}'")

    i = 0
    n = len(fragment)
    atoms: List[dict] = []  # list of dict(symbol, is_bracket, is_aromatic, charge, h_count, bonds=[], neighbors=set())
    atom_stack: List[int] = []
    current_atom_idx: Optional[int] = None
    pending_bond: Optional[float] = None
    open_rings: Dict[str, tuple] = {}  # ring_id -> (atom_idx, explicit_bond_order)

    def connect(u: int, v: int, bo: float) -> None:
        if u == v:
            raise ValueError(f"Invalid SMILES: self-loop bond on atom {u} in '{fragment}'")
        if v in atoms[u]['neighbors']:
            raise ValueError(f"Invalid SMILES: duplicate bond or ring closure between atom {u} and atom {v} in '{fragment}'")
        atoms[u]['bonds'].append(bo)
        atoms[u]['neighbors'].add(v)
        atoms[v]['bonds'].append(bo)
        atoms[v]['neighbors'].add(u)

    while i < n:
        char = fragment[i]

        # Bond symbols
        if char in BOND_CHARS:
            if pending_bond is not None:
                raise ValueError(f"Consecutive bond symbols: '{pending_bond}{char}'")
            pending_bond = BOND_ORDERS.get(char, 1.0)
            i += 1
            if i < n and fragment[i] == ')':
                raise ValueError("Trailing bond before closing branch parenthesis.")
            continue

        # Open branch '('
        if char == '(':
            if current_atom_idx is None:
                raise ValueError("Branch opens before any atom is defined.")
            if pending_bond is not None:
                raise ValueError(f"Invalid SMILES: bond symbol cannot immediately precede opening parenthesis in '{fragment}'")
            atom_stack.append(current_atom_idx)
            i += 1
            continue

        # Close branch ')'
        if char == ')':
            if not atom_stack:
                raise ValueError("Invalid SMILES: unmatched closing parenthesis.")
            if pending_bond is not None:
                raise ValueError("Invalid SMILES: trailing bond before closing branch parenthesis.")
            popped_idx = atom_stack.pop()
            current_atom_idx = popped_idx
            i += 1
            continue

        # Ring closures
        if char == '%' or char.isdigit():
            if current_atom_idx is None:
                raise ValueError("Invalid SMILES: ring closure number specified before any atom.")
            if char == '%':
                if i + 2 >= n or not (fragment[i + 1].isdigit() and fragment[i + 2].isdigit()):
                    raise ValueError(f"Invalid SMILES: invalid 2-digit ring closure at position {i}.")
                ring_id = fragment[i + 1:i + 3]
                i += 3
            else:
                ring_id = char
                i += 1

            close_bond = pending_bond
            pending_bond = None

            if ring_id in open_rings:
                other_idx, open_bond = open_rings.pop(ring_id)
                # Consistency check for explicit bonds specified at both ends of ring closure
                if open_bond is not None and close_bond is not None and open_bond != close_bond:
                    raise ValueError(
                        f"Invalid SMILES: conflicting explicit ring closure bonds for ring '{ring_id}' "
                        f"({open_bond} vs {close_bond}) in '{fragment}'"
                    )
                bo = open_bond if open_bond is not None else (close_bond if close_bond is not None else 1.0)
                connect(current_atom_idx, other_idx, bo)
            else:
                open_rings[ring_id] = (current_atom_idx, close_bond)
            continue

        # Bracket atom: [...]
        if char == '[':
            close_idx = fragment.find(']', i)
            if close_idx == -1:
                raise ValueError("Invalid SMILES: unclosed square bracket.")
            bracket_content = fragment[i:close_idx + 1]
            match = BRACKET_REGEX.match(bracket_content)
            if not match:
                raise ValueError(f"Invalid SMILES: malformed bracket atom '{bracket_content}'")
            elem = match.group(2)
            if elem not in PERIODIC_TABLE:
                raise ValueError(f"Invalid SMILES: unknown chemical element '{elem}' in '{bracket_content}'")

            charge = parse_charge(match.group(5))
            h_count = parse_h_count(match.group(4))
            is_aromatic = elem[0].islower()

            atom_data = {
                'symbol': elem,
                'is_bracket': True,
                'is_aromatic': is_aromatic,
                'charge': charge,
                'h_count': h_count,
                'bonds': [],
                'neighbors': set()
            }
            new_idx = len(atoms)
            atoms.append(atom_data)

            if current_atom_idx is not None:
                bo = pending_bond if pending_bond is not None else 1.0
                connect(current_atom_idx, new_idx, bo)
            elif pending_bond is not None:
                raise ValueError("Invalid SMILES: bond specified without preceding atom.")

            current_atom_idx = new_idx
            pending_bond = None
            i = close_idx + 1
            continue

        # Organic subset atoms: single or two letters
        if char in {'C', 'B', 'N', 'O', 'P', 'S', 'F', 'I', 'b', 'c', 'n', 'o', 'p', 's'}:
            if char == 'C' and i + 1 < n and fragment[i + 1] == 'l':
                sym = 'Cl'
                i += 2
            elif char == 'B' and i + 1 < n and fragment[i + 1] == 'r':
                sym = 'Br'
                i += 2
            else:
                sym = char
                i += 1

            is_aromatic = sym[0].islower()
            atom_data = {
                'symbol': sym,
                'is_bracket': False,
                'is_aromatic': is_aromatic,
                'charge': 0,
                'h_count': 0,
                'bonds': [],
                'neighbors': set()
            }
            new_idx = len(atoms)
            atoms.append(atom_data)

            if current_atom_idx is not None:
                bo = pending_bond if pending_bond is not None else 1.0
                connect(current_atom_idx, new_idx, bo)
            elif pending_bond is not None:
                raise ValueError("Invalid SMILES: bond specified without preceding atom.")

            current_atom_idx = new_idx
            pending_bond = None
            continue

        # Unrecognized character
        raise ValueError(f"Invalid character '{char}' in SMILES string.")

    if not atoms:
        raise ValueError(f"Invalid SMILES: no valid atoms found in fragment '{fragment}'")
    if open_rings:
        raise ValueError(f"Invalid SMILES: unclosed ring closures {list(open_rings.keys())} in '{fragment}'")
    if atom_stack:
        raise ValueError(f"Invalid SMILES: unclosed branch parentheses in '{fragment}'")
    if pending_bond is not None:
        raise ValueError(f"Invalid SMILES: trailing bond at end of fragment '{fragment}'")

    # Aromaticity verification: all lowercase aromatic atoms MUST belong to at least one cycle.
    # In an undirected graph, an edge (u, v) is part of at least one cycle iff it is NOT a bridge.
    # Therefore, a vertex belongs to at least one cycle iff it is incident to at least one non-bridge edge.
    num_atoms = len(atoms)
    adj = [list(atoms[idx]['neighbors']) for idx in range(num_atoms)]

    disc = [-1] * num_atoms
    low = [-1] * num_atoms
    bridges = set()
    timer = 0

    for root in range(num_atoms):
        if disc[root] != -1:
            continue
        stack = [(root, -1, 0)]  # (u, parent, next_neighbor_index)
        disc[root] = low[root] = timer
        timer += 1
        while stack:
            u, p, nbr_idx = stack[-1]
            if nbr_idx < len(adj[u]):
                v = adj[u][nbr_idx]
                stack[-1] = (u, p, nbr_idx + 1)
                if v == p:
                    continue
                if disc[v] != -1:
                    low[u] = min(low[u], disc[v])
                else:
                    disc[v] = low[v] = timer
                    timer += 1
                    stack.append((v, u, 0))
            else:
                stack.pop()
                if stack:
                    parent_u = stack[-1][0]
                    low[parent_u] = min(low[parent_u], low[u])
                    if low[u] > disc[parent_u]:
                        bridges.add((min(parent_u, u), max(parent_u, u)))

    in_cycle = [False] * num_atoms
    for u in range(num_atoms):
        for v in adj[u]:
            if (min(u, v), max(u, v)) not in bridges:
                in_cycle[u] = True
                break

    for idx, at in enumerate(atoms):
        if at['is_aromatic'] and not in_cycle[idx]:
            sym = at['symbol']
            raise ValueError(
                f"Invalid SMILES: aromatic atom '{sym}' at position {idx} is not part of a ring cycle in '{fragment}'"
            )
        validate_atom_valence(at, fragment)


def validate_smiles(smiles: str) -> None:
    """Validate a SMILES string (single molecule or multiple dot-separated fragments)."""
    if not smiles or not isinstance(smiles, str) or not smiles.strip():
        raise ValueError("SMILES must be a non-empty string.")

    s = smiles.strip()
    if len(s) < 1 or len(s) > 2048:
        raise ValueError(f"SMILES length ({len(s)}) out of valid range [1, 2048].")

    if s.startswith('.') or s.endswith('.') or '..' in s:
        raise ValueError(f"Invalid salt or dot notation in SMILES: '{s}'")

    fragments = s.split('.')
    for fragment in fragments:
        validate_smiles_fragment(fragment)
