"""Agent Hard Constraint Validator & Steering Control Protocol (P3 Milestone).

Enforces:
- Separation of hard code-validated constraints from unstructured prompt text
- Strict rejection of unsupported constraints with UnsupportedConstraintError
- Deterministic property evaluation (MW, pKd, SA, motif sub-structures)
- Versioned constraint updating during confirmed pause states
- Candidate gatekeeping: non-compliant molecules are strictly filtered with logged rationale
"""
from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / "02_code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from admet_predictor import _extract_descriptors as compute_molecular_descriptors
from smiles_validator import validate_smiles, parse_charge, parse_h_count


BOND_CHARS = {'-', '=', '#', '$', ':', '/', '\\'}
BOND_ORDERS = {'-': 1.0, '=': 2.0, '#': 3.0, '$': 4.0, ':': 1.5, '/': 1.0, '\\': 1.0}
BRACKET_REGEX = re.compile(r'^\[([0-9]*)([A-Z][a-z]?|[a-z])(@{0,2})(H[0-9]*)?([+-]\d*|\++|-+)?(:[0-9]+)?\]$')


def parse_smiles_graph(fragment: str) -> Tuple[List[Dict[str, Any]], Dict[Tuple[int, int], float]]:
    """Parse validated connectivity; unsupported syntax is never silently discarded."""
    validate_smiles(fragment)
    i = 0
    n = len(fragment)
    atoms: List[Dict[str, Any]] = []
    atom_stack: List[int] = []
    current_atom_idx: Optional[int] = None
    pending_bond: Optional[float] = None
    open_rings: Dict[str, Tuple[int, Optional[float]]] = {}
    bonds: Dict[Tuple[int, int], float] = {}

    def connect(u: int, v: int, bo: float) -> None:
        atoms[u]['neighbors'].add(v)
        atoms[v]['neighbors'].add(u)
        bonds[(min(u, v), max(u, v))] = bo

    def bond_order(u: int, v: int, explicit: Optional[float]) -> float:
        if explicit is not None:
            return explicit
        return 1.5 if atoms[u]['is_aromatic'] and atoms[v]['is_aromatic'] else 1.0

    while i < n:
        char = fragment[i]
        if char in BOND_CHARS:
            pending_bond = BOND_ORDERS.get(char, 1.0)
            i += 1
            continue
        if char == '(':
            atom_stack.append(current_atom_idx)
            i += 1
            continue
        if char == ')':
            if atom_stack:
                current_atom_idx = atom_stack.pop()
            i += 1
            continue
        if char == '.':
            current_atom_idx = None
            pending_bond = None
            i += 1
            continue
        if char == '%' or char.isdigit():
            if char == '%':
                ring_id = fragment[i + 1:i + 3]
                i += 3
            else:
                ring_id = char
                i += 1
            close_bond = pending_bond
            pending_bond = None
            if ring_id in open_rings:
                other_idx, open_bond = open_rings.pop(ring_id)
                if current_atom_idx is not None:
                    bo = bond_order(current_atom_idx, other_idx, open_bond if open_bond is not None else close_bond)
                    connect(current_atom_idx, other_idx, bo)
            else:
                if current_atom_idx is not None:
                    open_rings[ring_id] = (current_atom_idx, close_bond)
            continue
        if char == '[':
            close_idx = fragment.find(']', i)
            if close_idx == -1:
                break
            bracket_content = fragment[i:close_idx + 1]
            match = BRACKET_REGEX.match(bracket_content)
            if not match:
                raise ValueError(f"不支持的括号原子: {bracket_content}")
            elem = match.group(2)
            atom_data = {'symbol': elem, 'is_aromatic': elem[0].islower(), 'neighbors': set(),
                         'charge': parse_charge(match.group(5)), 'hydrogens': parse_h_count(match.group(4))}
            new_idx = len(atoms)
            atoms.append(atom_data)
            if current_atom_idx is not None:
                connect(current_atom_idx, new_idx, bond_order(current_atom_idx, new_idx, pending_bond))
            current_atom_idx = new_idx
            pending_bond = None
            i = close_idx + 1
            continue
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
            atom_data = {'symbol': sym, 'is_aromatic': sym[0].islower(), 'neighbors': set(), 'charge': 0, 'hydrogens': 0}
            new_idx = len(atoms)
            atoms.append(atom_data)
            if current_atom_idx is not None:
                connect(current_atom_idx, new_idx, bond_order(current_atom_idx, new_idx, pending_bond))
            current_atom_idx = new_idx
            pending_bond = None
            continue
        raise ValueError(f"不支持的结构字符: {char}")
    return atoms, bonds


def has_benzene_ring(smiles: str) -> bool:
    """Verifies chemical graph presence of an aromatic or Kekule 6-membered benzene ring with arbitrary substituents and ring closures."""
    if not smiles or not isinstance(smiles, str):
        return False
    fragments = smiles.split('.')
    for frag in fragments:
        frag = frag.strip()
        if not frag:
            continue
        try:
            atoms, bonds = parse_smiles_graph(frag)
        except Exception:
            continue
        n = len(atoms)
        if n < 6:
            continue
        adj = [list(atoms[k]['neighbors']) for k in range(n)]
        found = False

        def dfs(path: List[int]) -> None:
            nonlocal found
            if found:
                return
            curr = path[-1]
            if len(path) == 6:
                if path[0] in adj[curr]:
                    cycle = path
                    # 1. Aromatic benzene ring (all 6 atoms are aromatic 'c')
                    if all(atoms[idx]['symbol'] == 'c' and atoms[idx]['charge'] == 0 for idx in cycle) and all(
                        bonds[(min(cycle[k], cycle[(k + 1) % 6]), max(cycle[k], cycle[(k + 1) % 6]))] == 1.5 for k in range(6)
                    ):
                        found = True
                        return
                    # 2. Kekule benzene ring (6 carbons with alternating single/double bonds in cycle sequence)
                    if all(atoms[idx]['symbol'] in ('C', 'c') for idx in cycle):
                        edge_orders = [
                            bonds.get((min(cycle[k], cycle[(k + 1) % 6]), max(cycle[k], cycle[(k + 1) % 6])), 1.0)
                            for k in range(6)
                        ]
                        if edge_orders in ([1.0, 2.0, 1.0, 2.0, 1.0, 2.0], [2.0, 1.0, 2.0, 1.0, 2.0, 1.0]):
                            found = True
                            return
                return
            for nbr in adj[curr]:
                if nbr > path[0] and nbr not in path:
                    if len(path) == 5:
                        if path[0] in adj[nbr]:
                            dfs(path + [nbr])
                    else:
                        dfs(path + [nbr])

        for start in range(n):
            if atoms[start]['symbol'] in ('c', 'C'):
                dfs([start])
                if found:
                    return True
    return False


def has_pyridine_ring(smiles: str) -> bool:
    """Verifies chemical graph presence of a 6-membered pyridine ring."""
    if not smiles or not isinstance(smiles, str):
        return False
    fragments = smiles.split('.')
    for frag in fragments:
        frag = frag.strip()
        if not frag:
            continue
        try:
            atoms, bonds = parse_smiles_graph(frag)
        except Exception:
            continue
        n = len(atoms)
        if n < 6:
            continue
        adj = [list(atoms[k]['neighbors']) for k in range(n)]
        found = False

        def dfs(path: List[int]) -> None:
            nonlocal found
            if found:
                return
            curr = path[-1]
            if len(path) == 6:
                if path[0] in adj[curr]:
                    cycle = path
                    symbols = [atoms[idx]['symbol'] for idx in cycle]
                    c_count = sum(1 for s in symbols if s in ('c', 'C'))
                    n_count = sum(1 for s in symbols if s in ('n', 'N'))
                    if c_count == 5 and n_count == 1:
                        # 1. Aromatic pyridine ring (5 aromatic carbons 'c' and 1 aromatic nitrogen 'n')
                        if symbols.count('c') == 5 and symbols.count('n') == 1 and all(
                            atoms[idx]['charge'] == 0 for idx in cycle
                        ) and all(
                            bonds[(min(cycle[k], cycle[(k + 1) % 6]), max(cycle[k], cycle[(k + 1) % 6]))] == 1.5 for k in range(6)
                        ):
                            found = True
                            return
                        # 2. Kekule pyridine ring (alternating single and double bonds in cycle sequence)
                        edge_orders = [
                            bonds.get((min(cycle[k], cycle[(k + 1) % 6]), max(cycle[k], cycle[(k + 1) % 6])), 1.0)
                            for k in range(6)
                        ]
                        if edge_orders in ([1.0, 2.0, 1.0, 2.0, 1.0, 2.0], [2.0, 1.0, 2.0, 1.0, 2.0, 1.0]):
                            found = True
                            return
                return
            for nbr in adj[curr]:
                if nbr > path[0] and nbr not in path:
                    if len(path) == 5:
                        if path[0] in adj[nbr]:
                            dfs(path + [nbr])
                    else:
                        dfs(path + [nbr])

        for start in range(n):
            if atoms[start]['symbol'] in ('c', 'C', 'n', 'N'):
                dfs([start])
                if found:
                    return True
    return False


def _normalize_motif(s: str) -> str:
    """Normalize common aromatic and Kekule benzene/pyridine rings across arbitrary single/two-digit ring closures."""
    norm = s
    # Support two-digit closures %10-%99 as well as single digits 0-9
    ring_pat = r'(%[0-9]{2}|[0-9])'
    # Generalized benzene: Kekule forms
    norm = re.sub(rf'C{ring_pat}=CC=CC=C\1', 'c1ccccc1', norm, flags=re.IGNORECASE)
    norm = re.sub(rf'C{ring_pat}C=CC=CC=\1', 'c1ccccc1', norm, flags=re.IGNORECASE)
    # Aromatic benzene
    norm = re.sub(rf'c{ring_pat}ccccc\1', 'c1ccccc1', norm)
    # Pyridine rings
    norm = re.sub(rf'C{ring_pat}=CC=NC=C\1', 'c1ccncc1', norm, flags=re.IGNORECASE)
    norm = re.sub(rf'C{ring_pat}=NC=CC=C\1', 'c1ccncc1', norm, flags=re.IGNORECASE)
    norm = re.sub(rf'c{ring_pat}ccncc\1', 'c1ccncc1', norm)
    norm = re.sub(rf'c{ring_pat}ncccc\1', 'c1ccncc1', norm)
    return norm


def is_benzene_motif(pattern: str) -> bool:
    p = pattern.strip()
    if p in ("c1ccccc1", "C1=CC=CC=C1", "c2ccccc2", "C2=CC=CC=C2", "c%10ccccc%10", "C%10=CC=CC=C%10"):
        return True
    norm = _normalize_motif(p)
    if norm in ("c1ccccc1", "C1=CC=CC=C1"):
        return True
    return False


def is_pyridine_motif(pattern: str) -> bool:
    p = pattern.strip()
    if p in ("c1ccncc1", "c1ncccc1", "c2ccncc2", "c2ncccc2", "c%10ccncc%10", "c%10ncccc%10"):
        return True
    norm = _normalize_motif(p)
    if norm in ("c1ccncc1", "c1ncccc1"):
        return True
    return False


def _motif_matches(pattern: str, target: str) -> bool:
    """Match atom/charge/bond topology; benzene and pyridine additionally accept Kekule form."""
    if not pattern or not target:
        return False
    # 1. Chemical graph substructure check for ring motifs
    if is_benzene_motif(pattern):
        return has_benzene_ring(target)
    if is_pyridine_motif(pattern):
        return has_pyridine_ring(target)

    query_atoms, query_bonds = parse_smiles_graph(pattern)
    atoms, bonds = parse_smiles_graph(target)
    order = sorted(range(len(query_atoms)), key=lambda i: len(query_atoms[i]['neighbors']), reverse=True)
    mapping: Dict[int, int] = {}
    used = set()
    attempts = 0

    def match(depth: int) -> bool:
        nonlocal attempts
        if depth == len(order):
            return True
        q = order[depth]
        for t, atom in enumerate(atoms):
            attempts += 1
            if attempts > 100_000:
                raise UnsupportedConstraintError("结构匹配超过计算上限，请缩小约束片段")
            if t in used or atom['symbol'] != query_atoms[q]['symbol'] or atom['charge'] != query_atoms[q]['charge']:
                continue
            if len(atom['neighbors']) < len(query_atoms[q]['neighbors']):
                continue
            if any(
                bonds.get((min(t, other), max(t, other))) != query_bonds[(min(q, neighbor), max(q, neighbor))]
                for neighbor, other in mapping.items() if neighbor in query_atoms[q]['neighbors']
            ):
                continue
            mapping[q] = t
            used.add(t)
            if match(depth + 1):
                return True
            used.remove(t)
            del mapping[q]
        return False

    return match(0)


class UnsupportedConstraintError(ValueError):
    """Raised when a steering constraint cannot be strictly validated by code."""
    pass


class InvalidConstraintUpdateError(RuntimeError):
    """Raised when updating constraints while pipeline is running without a confirmed pause."""
    pass


SUPPORTED_CONSTRAINT_KEYS = {
    "max_mw",
    "min_predicted_pkd",
    "max_hemolysis_pct",
    "max_sa_score",
    "must_contain_motif",
    "forbidden_motifs",
    "version"
}


@dataclass
class AgentHardConstraints:
    """Verifiable hard constraints enforced by programmatic checks on every candidate."""
    version: int = 1
    max_mw: Optional[float] = None
    min_predicted_pkd: Optional[float] = None
    max_hemolysis_pct: Optional[float] = None
    max_sa_score: Optional[float] = None
    must_contain_motif: Optional[str] = None
    forbidden_motifs: List[str] = field(default_factory=list)

    def __post_init__(self):
        for pattern in [self.must_contain_motif, *self.forbidden_motifs]:
            if not pattern:
                continue
            if any(token in pattern for token in ('@', '*', '?', ';', '!', '&', '~', '[', ']')):
                raise UnsupportedConstraintError("片段约束仅支持明确原子/键拓扑和苯/吡啶环，不支持 SMARTS、括号原子或立体化学查询")
            try:
                atoms, _ = parse_smiles_graph(pattern)
                if len(atoms) > 64:
                    raise ValueError("片段不得超过 64 个原子")
            except ValueError as exc:
                raise UnsupportedConstraintError(f"不支持的结构约束: {exc}") from exc

    @classmethod
    def from_dict(cls, data: Dict[str, Any], current_version: int = 1) -> AgentHardConstraints:
        """Parses constraints and validates that all specified keys are supported."""
        unsupported = set(data.keys()) - SUPPORTED_CONSTRAINT_KEYS
        if unsupported:
            raise UnsupportedConstraintError(
                f"以下约束不受硬编码验证器支持: {sorted(list(unsupported))}。"
                f"支持的硬约束键包括: {sorted(list(SUPPORTED_CONSTRAINT_KEYS))}。"
                f"严禁仅将自然语言软提示作为有效约束声明。"
            )

        def _parse_float(val: Any) -> Optional[float]:
            if val is None:
                return None
            try:
                return float(val)
            except Exception:
                return float("nan")

        new_version = int(data.get("version", current_version + 1))
        max_mw = _parse_float(data.get("max_mw"))
        min_pkd = _parse_float(data.get("min_predicted_pkd"))
        max_hemo = _parse_float(data.get("max_hemolysis_pct"))
        max_sa = _parse_float(data.get("max_sa_score"))
        must_motif = str(data["must_contain_motif"]).strip() if data.get("must_contain_motif") else None
        forbidden = [str(m).strip() for m in data.get("forbidden_motifs", []) if str(m).strip()]

        return cls(
            version=new_version,
            max_mw=max_mw,
            min_predicted_pkd=min_pkd,
            max_hemolysis_pct=max_hemo,
            max_sa_score=max_sa,
            must_contain_motif=must_motif,
            forbidden_motifs=forbidden,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate_candidate(
        self,
        smiles: str,
        predicted_pkd: Optional[float] = None,
        hemolysis_risk_pct: Optional[float] = None,
        sa_score: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates a candidate against all active hard constraints.
        Returns: (passed, failure_reason)
        """
        if not smiles or not isinstance(smiles, str):
            return False, "无效的分子 SMILES 结构"
        if self.must_contain_motif or self.forbidden_motifs:
            try:
                parse_smiles_graph(smiles)
            except ValueError as exc:
                return False, f"无效或不支持的分子结构: {exc}"

        # 1. Structural motifs (exact & normalized aromatic/Kekule equivalence)
        if self.must_contain_motif:
            if not _motif_matches(self.must_contain_motif, smiles):
                return False, f"未包含必需结构片段 (必须包含 '{self.must_contain_motif}')"

        for forbidden in self.forbidden_motifs:
            if forbidden and _motif_matches(forbidden, smiles):
                return False, f"包含禁用结构基团/毒性片段 ('{forbidden}')"

        # 2. Molecular Weight check
        if self.max_mw is not None:
            if math.isnan(self.max_mw) or math.isinf(self.max_mw) or self.max_mw <= 0:
                return False, f"最大分子量约束数值非法 ({self.max_mw})"
            desc = compute_molecular_descriptors(smiles)
            mw = desc["mw"]
            if mw > self.max_mw:
                return False, f"分子量超出硬约束上限 ({mw:.1f} Da > {self.max_mw:.1f} Da)"

        # 3. Predicted affinity pKd check (fail closed if required but missing or NaN)
        if self.min_predicted_pkd is not None:
            if math.isnan(self.min_predicted_pkd) or math.isinf(self.min_predicted_pkd):
                return False, f"最小亲和力约束数值非法 ({self.min_predicted_pkd})"
            if predicted_pkd is None or math.isnan(predicted_pkd) or math.isinf(predicted_pkd):
                return False, f"缺少必须的预测亲和力指标 (要求 min_predicted_pkd={self.min_predicted_pkd:.2f})"
            if predicted_pkd < self.min_predicted_pkd:
                return False, f"预测亲和力低于硬约束门限 (pKd {predicted_pkd:.2f} < {self.min_predicted_pkd:.2f})"

        # 4. Hemolysis percentage check (fail closed if required but missing or NaN)
        if self.max_hemolysis_pct is not None:
            if math.isnan(self.max_hemolysis_pct) or math.isinf(self.max_hemolysis_pct):
                return False, f"溶血风险约束数值非法 ({self.max_hemolysis_pct})"
            if hemolysis_risk_pct is None or math.isnan(hemolysis_risk_pct) or math.isinf(hemolysis_risk_pct):
                return False, f"缺少必须的溶血风险指标 (要求 max_hemolysis_pct={self.max_hemolysis_pct:.1f}%)"
            if hemolysis_risk_pct > self.max_hemolysis_pct:
                return False, f"估计溶血风险超出硬约束门限 ({hemolysis_risk_pct:.1f}% > {self.max_hemolysis_pct:.1f}%)"

        # 5. Synthetic Accessibility check (fail closed if required but missing or NaN)
        if self.max_sa_score is not None:
            if math.isnan(self.max_sa_score) or math.isinf(self.max_sa_score):
                return False, f"合成难度约束数值非法 ({self.max_sa_score})"
            if sa_score is None or math.isnan(sa_score) or math.isinf(sa_score):
                return False, f"缺少必须的合成难度指标 (要求 max_sa_score={self.max_sa_score:.1f})"
            if sa_score > self.max_sa_score:
                return False, f"合成难度超出硬约束门限 (SA {sa_score:.1f} > {self.max_sa_score:.1f})"

        return True, None


@dataclass
class AgentCheckpoint:
    """A persistent execution checkpoint representing the state of an agent session."""
    task_id: str
    generation: int
    parent_id: Optional[str]
    parent_smiles: str
    constraints_version: int
    best_pkd: float
    candidates_count: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize checkpoint to a JSON-compatible dictionary."""
        return asdict(self)
