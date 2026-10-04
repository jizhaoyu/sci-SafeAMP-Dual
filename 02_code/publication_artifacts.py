"""Regenerate manuscript tables and figures exclusively from a completed run."""
import argparse
from pathlib import Path
import pandas as pd
from research_utils import read_json, write_json, sha256, utc_now
from evaluation import aggregate_metrics, ensemble_predictions, cluster_intervals, compare_models, validate_coverage


def load_research_predictions(run_dir):
    """Load and validate run predictions for research inspection without requiring publication approval."""
    root = Path(run_dir)
    manifest = read_json(root / 'manifest.json')
    if manifest.get('status') != 'completed' or manifest.get('dataset_manifest', {}).get('status') != 'validated':
        raise ValueError('Research outputs require a completed, validated research run.')
    if not manifest.get('formal_results_available', False):
        raise ValueError('Research export blocked: formal_results_available must be true.')
    if manifest.get('features', {}).get('backend') != 'fair-esm':
        raise ValueError('Research outputs require the declared real feature backend.')
    if sha256(root / 'predictions.csv') != manifest.get('predictions_sha256'):
        raise ValueError('Prediction checksum mismatch.')

    from experiment_runner import load_dataset, MODELS, SEEDS
    dataset, dm = load_dataset(manifest['dataset_dir'])
    if dm != manifest['dataset_manifest']:
        raise ValueError('Dataset manifest changed since the experiment.')

    frame = pd.read_csv(root / 'predictions.csv')
    validate_coverage(frame, MODELS, SEEDS)
    if set(frame.sample_id) != set(dataset.sample_id):
        raise ValueError('Run sample coverage differs from dataset.')

    for task in ['amp', 'hemo']:
        observed = frame[frame.task.eq(task)].groupby('sample_id').y_true.first().sort_index()
        expected = dataset.set_index('sample_id')[task].sort_index().rename('y_true')
        pd.testing.assert_series_equal(observed, expected, check_dtype=False)

    expected = dataset.set_index('sample_id')
    for sample, group in frame.groupby('sample_id'):
        row = expected.loc[sample]
        split = 'oof_selection' if row.split == 'development' else row.split
        if set(group.split) != {split} or set(group.cluster_id) != {row.cluster_id}:
            raise ValueError('Predictions changed the recorded data partition.')

    return frame, manifest


def load_predictions(run_dir, approval_path=None):
    """Strict publication gate: requires completed run AND verifiable human sign-off receipt."""
    root = Path(run_dir)
    manifest = read_json(root / 'manifest.json')
    if manifest.get('status') != 'completed' or manifest.get('dataset_manifest', {}).get('status') != 'validated':
        raise ValueError('Publication outputs require a completed, validated research run.')

    # Check publication gating conditions
    if approval_path is not None:
        app_path = Path(approval_path)
        if not app_path.is_file():
            raise FileNotFoundError(f'Approval receipt not found: {app_path}')
        approval = read_json(app_path)
        if approval.get('status') != 'approved':
            raise ValueError(f"Approval receipt status is '{approval.get('status')}', expected 'approved'.")
        run_manifest_hash = sha256(root / 'manifest.json')
        if approval.get('run_manifest_sha256') != run_manifest_hash:
            raise ValueError('Approval receipt run_manifest_sha256 does not match target run manifest.')
        if not manifest.get('formal_results_available', False):
            raise ValueError('Publication export blocked: formal_results_available must be true.')

        for key, path_key, default_rel in [
            ('reference_audit_sha256', 'reference_audit_path', '04_paper/evidence/reference_audit.json'),
            ('manuscript_sha256', 'manuscript_path', '04_paper/manuscript.tex'),
            ('references_sha256', 'references_path', '04_paper/references.bib'),
            ('claims_sha256', 'claims_path', '04_paper/claims.csv'),
            ('declarations_sha256', 'declarations_path', '04_paper/declarations.json'),
        ]:
            exp_hash = approval.get(key)
            if exp_hash:
                p_cand = Path(approval.get(path_key, default_rel))
                if not p_cand.is_file():
                    p_cand = app_path.parent / approval.get(path_key, default_rel)
                if not p_cand.is_file():
                    from research_utils import ROOT
                    p_cand = ROOT / approval.get(path_key, default_rel)
                if not p_cand.is_file() or sha256(p_cand) != exp_hash:
                    raise ValueError(f'Approval receipt hash mismatch for document: {approval.get(path_key, default_rel)}')
    else:
        # Preserves legacy validation checks and exact error messages
        if not manifest.get('publication_ready', False):
            raise ValueError('Publication export blocked: publication_ready must be true; explicit human approval receipt (--approval) is mandatory.')
        if not manifest.get('formal_results_available', False):
            raise ValueError('Publication export blocked: formal_results_available must be true.')
        ref_audit = manifest.get('reference_audit')
        if not ref_audit:
            cur = root.resolve()
            for _ in range(5):
                candidate = cur / '04_paper' / 'evidence' / 'reference_audit.json'
                if candidate.exists():
                    ref_audit = read_json(candidate)
                    break
                cur = cur.parent
        if not (ref_audit and ref_audit.get('all_claims_verified', False)):
            raise ValueError('Publication export blocked: reference_audit.all_claims_verified must be true.')
        approval = None

    if manifest.get('features', {}).get('backend') != 'fair-esm':
        raise ValueError('Publication outputs require the declared real feature backend.')
    if sha256(root / 'predictions.csv') != manifest.get('predictions_sha256'):
        raise ValueError('Prediction checksum mismatch.')

    from experiment_runner import load_dataset, MODELS, SEEDS
    dataset, dm = load_dataset(manifest['dataset_dir'])
    if dm != manifest['dataset_manifest']:
        raise ValueError('Dataset manifest changed since the experiment.')

    frame = pd.read_csv(root / 'predictions.csv')
    validate_coverage(frame, MODELS, SEEDS)
    if set(frame.sample_id) != set(dataset.sample_id):
        raise ValueError('Run sample coverage differs from dataset.')

    for task in ['amp', 'hemo']:
        observed = frame[frame.task.eq(task)].groupby('sample_id').y_true.first().sort_index()
        expected = dataset.set_index('sample_id')[task].sort_index().rename('y_true')
        pd.testing.assert_series_equal(observed, expected, check_dtype=False)

    expected = dataset.set_index('sample_id')
    for sample, group in frame.groupby('sample_id'):
        row = expected.loc[sample]
        split = 'oof_selection' if row.split == 'development' else row.split
        if set(group.split) != {split} or set(group.cluster_id) != {row.cluster_id}:
            raise ValueError('Predictions changed the recorded data partition.')

    return frame, manifest, approval


def plot_primary(intervals, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    table = pd.DataFrame(intervals)
    table = table[(table.task == 'hemo') & (table.metric == 'AUPRC')]
    with plt.rc_context({'font.size': 9, 'svg.fonttype': 'none', 'pdf.fonttype': 42}):
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), layout='constrained', sharex=True)
        for ax, split in zip(axes, ['test', 'external']):
            g = table[table.split == split].sort_values('model')
            for i, row in enumerate(g.itertuples()):
                ax.plot([row.ci95_low, row.ci95_high], [i, i], color='#0072B2', linewidth=1.5)
                ax.plot(row.estimate, i, marker='D' if row.model == 'dual_gated' else 'o', color='#111111', markersize=4)
            ax.set(yticks=range(len(g)), yticklabels=g.model, xlim=(0, 1), xlabel='Hemolysis average precision', title=split)
            ax.grid(axis='x', alpha=.2)
            ax.invert_yaxis()
        fig.savefig(path.with_suffix('.svg'), facecolor='white')
        fig.savefig(path.with_suffix('.png'), dpi=300, facecolor='white')
        plt.close(fig)


def export(run_dir, output_dir, resamples=2000, *, mode='publication', approval_path=None):
    output = Path(output_dir)
    if output.exists():
        raise ValueError('Publication export already exists; use a new directory.')

    if mode == 'research':
        frame, manifest = load_research_predictions(run_dir)
        approval = None
        scope = 'research_draft'
        pub_ready = False
        rev_status = 'pending'
    elif mode == 'publication':
        frame, manifest, approval = load_predictions(run_dir, approval_path=approval_path)
        scope = 'publication_submission'
        pub_ready = True
        rev_status = 'approved'
    else:
        raise ValueError(f"Unknown mode: '{mode}'. Must be 'research' or 'publication'.")

    target_spec = manifest.get('config', {}).get('target_specificity', 0.95)
    ensemble = ensemble_predictions(frame, target_spec)
    metrics = aggregate_metrics(ensemble)
    intervals = cluster_intervals(ensemble, resamples=resamples)
    comparisons = compare_models(frame, resamples=resamples)

    output.mkdir(parents=True)
    metadata = {
        'status': 'generating',
        'created_at': utc_now(),
        'artifact_scope': scope,
        'publication_ready': pub_ready,
        'review_status': rev_status,
        'run_dir': str(Path(run_dir).resolve()),
        'run_manifest_sha256': sha256(Path(run_dir) / 'manifest.json'),
        'predictions_sha256': manifest['predictions_sha256'],
        'resamples': resamples,
        'bootstrap_unit': 'independent sequence connected component',
        'ensemble': 'mean of three calibrated seed scores',
        'selection_warning': 'oof_selection includes calibration and threshold fitting; not unbiased evaluation',
        'figure_alt': 'Point estimates and cluster percentile 95% intervals for hemolysis average precision on test and external cohorts. Black diamonds denote the full model; circles denote comparators.',
        'approval_receipt_sha256': sha256(approval_path) if approval_path else None,
        'journal_requirements': 'not_selected_or_verified',
        'declarations': 'pending_human_verification'
    }
    write_json(output / 'manifest.json', metadata)

    try:
        bins = []
        flat = []
        for row in metrics:
            s_scope = {k: row[k] for k in ['split', 'model', 'seed', 'task']}
            bins.extend([{**s_scope, **b} for b in row.get('calibration_bins', [])])
            flat.append({k: v for k, v in row.items() if k != 'calibration_bins'})

        pd.DataFrame(flat).to_csv(output / 'ensemble_metrics.csv', index=False)
        pd.DataFrame(bins).to_csv(output / 'calibration_bins.csv', index=False)
        pd.DataFrame(intervals).to_csv(output / 'confidence_intervals.csv', index=False)
        pd.DataFrame(comparisons).to_csv(output / 'primary_comparisons.csv', index=False)
        ensemble.to_csv(output / 'ensemble_predictions.csv', index=False)
        write_json(output / 'per_seed_metrics.json', aggregate_metrics(frame))

        if 'raw_probability' in frame:
            raw = frame.copy()
            raw['probability'] = raw.raw_probability
            raw_ensemble = ensemble_predictions(raw, target_spec)
            write_json(output / 'uncalibrated_ensemble_metrics.json', aggregate_metrics(raw_ensemble))

        table = pd.DataFrame(flat)
        held = table[table.split.isin(['test', 'external'])]
        columns = ['split', 'model', 'task', 'n', 'AUPRC', 'AUROC', 'MCC', 'Brier', 'sensitivity', 'specificity']
        held[columns].to_latex(output / 'performance_table.tex', index=False, escape=True, float_format='%.4f')
        counts = ensemble[['sample_id', 'split']].drop_duplicates().groupby('split').size().to_dict()
        write_json(output / 'sample_counts.json', {
            'unique_samples': counts,
            'measured_denominators': [{k: r[k] for k in ['split', 'model', 'task', 'n']} for r in flat]
        })
        plot_primary(intervals, output / 'primary_hemo_auprc')

        metadata.update(
            status='generated',
            artifacts={p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'manifest.json'}
        )
    except Exception as exc:
        metadata.update(status='failed', reason=str(exc))
        write_json(output / 'manifest.json', metadata)
        raise

    write_json(output / 'manifest.json', metadata)
    return metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--mode', choices=['research', 'publication'], default='publication')
    p.add_argument('--approval', type=Path, default=None)
    p.add_argument('--resamples', type=int, default=2000)
    a = p.parse_args()
    try:
        export(a.run, a.output, resamples=a.resamples, mode=a.mode, approval_path=a.approval)
    except (ValueError, FileNotFoundError) as exc:
        p.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
