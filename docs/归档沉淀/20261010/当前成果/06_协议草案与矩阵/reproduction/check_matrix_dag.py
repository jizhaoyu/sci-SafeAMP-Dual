"""Matrix dependency DAG validation and integrity check.

Verifies:
1. Experiment ID uniqueness.
2. All reuse_source_exp_id dependencies are resolvable to existing experiment_id entries.
3. Dependency graph is acyclic (no circular dependencies).
4. Pure forward inference rows have total_fits == 0.
5. Arithmetic consistency: total_fits == sum of breakdown columns, cost == total_fits * est_sec_per_fit.
6. Total fit count strictly equals 803.
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, List, Set
import pandas as pd

MATRIX_CSV = Path(__file__).resolve().parents[1] / "实验矩阵.csv"
OUT_JSON = Path(__file__).resolve().parent / "matrix_dag_audit.json"


def check_dag():
    print(f"Loading experiment matrix: {MATRIX_CSV}")
    assert MATRIX_CSV.exists(), f"Matrix file not found: {MATRIX_CSV}"
    
    df = pd.read_csv(MATRIX_CSV)
    print(f"Total rows in matrix: {len(df)}")
    
    # 1. Uniqueness of experiment_id
    exp_ids = df["experiment_id"].tolist()
    assert len(exp_ids) == len(set(exp_ids)), f"Duplicate experiment_id detected! Unique: {len(set(exp_ids))}, Total: {len(exp_ids)}"
    all_id_set = set(exp_ids)
    print(f"  [PASS] All {len(exp_ids)} experiment IDs are strictly unique.")
    
    # 2. Dependency resolution
    dep_graph: Dict[str, List[str]] = {}
    missing_deps = []
    
    for _, row in df.iterrows():
        e_id = row["experiment_id"]
        reuse_str = str(row["reuse_source_exp_id"]).strip()
        
        if reuse_str == "none" or not reuse_str:
            dep_graph[e_id] = []
            continue
            
        # Comma-separated list of IDs
        deps = [d.strip() for d in reuse_str.split(",") if d.strip()]
        dep_graph[e_id] = deps
        
        for dep in deps:
            if dep not in all_id_set:
                missing_deps.append((e_id, dep))
                
    if missing_deps:
        print("  [FAIL] Missing dependencies found:")
        for e_id, dep in missing_deps:
            print(f"    Experiment {e_id} references non-existent ID: {dep}")
        sys.exit(1)
    else:
        print("  [PASS] All dependency references resolve to valid experiment IDs.")
        
    # 3. Cycle detection (DFS)
    visited = {}  # 0: unvisited, 1: visiting, 2: visited
    for node in dep_graph:
        visited[node] = 0
        
    def dfs(node: str, path: List[str]) -> bool:
        visited[node] = 1
        path.append(node)
        for nbr in dep_graph.get(node, []):
            if visited.get(nbr, 0) == 1:
                cycle = " -> ".join(path + [nbr])
                raise ValueError(f"Cycle detected in dependency DAG: {cycle}")
            if visited.get(nbr, 0) == 0:
                if not dfs(nbr, path):
                    return False
        path.pop()
        visited[node] = 2
        return True
        
    for node in dep_graph:
        if visited[node] == 0:
            dfs(node, [])
    print("  [PASS] Dependency DAG is completely acyclic (no circular dependencies).")
    
    # 4. Pure forward inference check
    forward_rows = df[df["inner_validation_design"] == "none_evaluation_only"]
    assert len(forward_rows) == 8, f"Expected 8 forward inference rows, got {len(forward_rows)}"
    for _, r in forward_rows.iterrows():
        assert r["total_fits"] == 0, f"Forward inference row {r['experiment_id']} has total_fits != 0 ({r['total_fits']})"
        assert r["param_selection_fits"] == 0
        assert r["oof_fits"] == 0
        assert r["meta_fits"] == 0
        assert r["final_refits"] == 0
        assert r["total_cost_sec"] == 0.0
    print("  [PASS] All 8 forward inference rows have strictly total_fits == 0 and cost == 0.0.")
    
    # 5. Arithmetic breakdown consistency
    calc_fits = df["param_selection_fits"] + df["oof_fits"] + df["meta_fits"] + df["final_refits"]
    assert (calc_fits == df["total_fits"]).all(), "Arithmetic error: breakdown does not sum to total_fits!"
    
    calc_costs = (df["total_fits"] * df["est_sec_per_fit"]).round(2)
    assert (calc_costs == df["total_cost_sec"]).all(), "Arithmetic error: total_cost_sec != total_fits * est_sec_per_fit!"
    print("  [PASS] Row-wise fit breakdowns and cost products match with 100% precision.")
    
    # 6. Overall sum assertions
    p_sum = int(df["param_selection_fits"].sum())
    oof_sum = int(df["oof_fits"].sum())
    meta_sum = int(df["meta_fits"].sum())
    final_sum = int(df["final_refits"].sum())
    total_fits_sum = int(df["total_fits"].sum())
    total_cost_sum = float(df["total_cost_sec"].sum())
    
    assert p_sum == 0, f"Expected param_selection_fits == 0, got {p_sum}"
    assert oof_sum == 735, f"Expected oof_fits == 735, got {oof_sum}"
    assert meta_sum == 17, f"Expected meta_fits == 17, got {meta_sum}"
    assert final_sum == 51, f"Expected final_refits == 51, got {final_sum}"
    assert total_fits_sum == 803, f"Expected total_fits == 803, got {total_fits_sum}"
    assert abs(total_cost_sum - 4053.30) < 1e-2, f"Expected cost == 4053.30, got {total_cost_sum}"
    
    print("\nSummary Audit:")
    print(f"  param_selection_fits: {p_sum}")
    print(f"  oof_fits:             {oof_sum}")
    print(f"  meta_fits:            {meta_sum}")
    print(f"  final_refits:         {final_sum}")
    print(f"  total_fits:           {total_fits_sum}")
    print(f"  total_cost_sec:       {total_cost_sum:.2f} ({total_cost_sum/60.0:.2f} minutes)")
    
    result = {
        "status": "PASS",
        "exit_code": 0,
        "total_rows": len(df),
        "unique_ids": len(all_id_set),
        "missing_dependencies": len(missing_deps),
        "is_acyclic": True,
        "breakdown": {
            "param_selection_fits": p_sum,
            "oof_fits": oof_sum,
            "meta_fits": meta_sum,
            "final_refits": final_sum,
            "total_fits": total_fits_sum,
            "total_cost_sec": total_cost_sum,
            "total_cost_min": round(total_cost_sum / 60.0, 2)
        }
    }
    
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nAudit saved to: {OUT_JSON}")
    print("Matrix DAG verification completely PASSED.")
    sys.exit(0)


if __name__ == "__main__":
    check_dag()
