"""Build a local research handoff after a fresh frozen MIC run validation."""
import argparse
import csv
from importlib.metadata import version
import json
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import train_mic_goat_baseline_v2 as frozen
from research_utils import ROOT, read_json, sha256, utc_now

RUNTIME = Path(__file__).with_name('mic_delivery_runtime.py')
SCOPE = 'admitted_cohort_oof_replay_only'
ARTIFACTS = {
    'protocol': 'protocol.json', 'freeze': 'freeze.json', 'validation': 'validation.json',
    'molecules': 'cohort/candidate_molecules.csv',
    'observations': 'cohort/candidate_observations.csv', 'fold_roles': 'cohort/fold_roles.csv',
    'features': 'run/fixed_features.npy', 'oof': 'run/oof_predictions.csv',
    'fold_metrics': 'run/fold_metrics.csv', 'pooled_metrics': 'run/pooled_descriptive_metrics.csv',
    'run_manifest': 'run/manifest.json',
}


def _unused(path):
    if path.exists() or path.is_symlink():
        raise FileExistsError(f'Refusing to overwrite output: {path}')


def _workspace_file(name):
    # Source manifests contain historical Windows separators as well as POSIX paths.
    path = (ROOT / str(name).replace('\\', '/')).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f'Missing or unsafe workspace source: {name}')
    return path


def _safe_source(path):
    if path.is_symlink() or path.suffix.lower() in {'.pem', '.key'} or any(
            p.lower().startswith(('.env', 'credentials.', 'secrets.', 'id_rsa')) or p.lower() in
            {'secrets', 'secret', 'credentials'} for p in path.parts):
        raise ValueError(f'Sensitive or linked source refused: {path.name}')


def _tree(directory):
    if directory.is_symlink():
        raise ValueError(f'Linked source directory refused: {directory}')
    paths = []
    for path in sorted(directory.rglob('*')):
        _safe_source(path)
        if path.is_file():
            paths.append(path)
    return paths


def _source_inventory(protocol):
    """Preserve the source audit directories and digest-bound input/output chains."""
    release = _workspace_file(protocol['release_manifest']).parent
    with (release / 'evidence/source_review.csv').open(encoding='utf-8', newline='') as stream:
        sources = list(csv.DictReader(stream))
    pending = set(_tree(release))
    pending.update(_workspace_file(protocol[key]) for key in
                   ('independent_partition_validation', 'readiness_state', 'parent_protocol_path'))
    pending.update(_workspace_file(name) for name in protocol['dependency_sha256'])
    pending.add(frozen.ENTRY)
    for source in sources:
        primary = _workspace_file(source['primary_file'])
        if sha256(primary) != source['sha256']:
            raise ValueError(f'Primary source checksum differs: {source["source_id"]}')
        # All metadata, supplements, figures, and original files remain together.
        relative = primary.relative_to(ROOT)
        if relative.parts[:2] != ('03_experiments', 'audits') or len(relative.parts) < 4:
            raise ValueError('Unexpected primary audit location')
        pending.update(_tree(ROOT.joinpath(*relative.parts[:3])))
    collected, historical_mismatches, certificate_references, certificates = {}, [], [], []
    while pending:
        path = pending.pop()
        if path in collected:
            continue
        _safe_source(path)
        collected[path] = sha256(path)
        if path.suffix.lower() != '.json':
            continue
        record = read_json(path)
        if not isinstance(record, dict):
            continue
        # Readiness/validation certificates are retained as historical evidence.
        # Their document inventories describe earlier states, not source-producing
        # manifests. Only the latter are followed as acquisition/release chains.
        if not isinstance(record.get('outputs'), dict):
            if isinstance(record.get('inputs'), dict):
                certificates.append(path.relative_to(ROOT).as_posix())
                for name, expected in record['inputs'].items():
                    if not isinstance(expected, str) or len(expected) != 64:
                        continue
                    candidate = (ROOT / str(name).replace('\\', '/')).resolve()
                    if not candidate.is_relative_to(ROOT):
                        raise ValueError('Unsafe historical certificate reference')
                    actual = sha256(candidate) if candidate.is_file() else None
                    if actual != expected:
                        certificate_references.append({'certificate': path.relative_to(ROOT).as_posix(),
                            'input': name, 'historical_sha256': expected, 'current_sha256': actual,
                            'status': 'unverified historical reference; historical snapshot unavailable'})
                    elif candidate.suffix.lower() == '.json':
                        # Preserve referenced immutable source manifests/certificates;
                        # do not substitute current documents for historical bytes.
                        pending.add(candidate)
            continue
        for field in ('inputs', 'outputs'):
            bindings = record.get(field, {})
            if not isinstance(bindings, dict):
                continue
            for name, digest in bindings.items():
                if not isinstance(digest, str) or len(digest) != 64:
                    continue
                normalized = str(name).replace('\\', '/')
                candidate = ROOT / normalized if field == 'inputs' else path.parent / normalized
                candidate = candidate.resolve()
                if not candidate.is_relative_to(ROOT) or not candidate.is_file():
                    raise ValueError(f'Missing or unsafe source binding: {name}')
                actual = sha256(candidate)
                if actual != digest:
                    if (field == 'outputs' or candidate.suffix.lower() != '.py'
                            or normalized in protocol['dependency_sha256']
                            or candidate == frozen.ENTRY):
                        raise ValueError(f'Source binding checksum differs: {name}')
                    historical_mismatches.append({
                        'manifest': path.relative_to(ROOT).as_posix(), 'input': normalized,
                        'historical_sha256': digest, 'current_sha256': actual,
                        'scope': 'historical source snapshot unavailable; not verified or reproducible'})
                pending.add(candidate)
    provenance = {'closure_scope': 'source/acquisition/release manifests with outputs: input/output digests; '
                  'historical certificates: preserve immutable JSON references only, not old document inventories',
                  'historical_certificates_without_source_input_recursion': sorted(certificates),
                  'historical_source_input_mismatches': sorted(historical_mismatches, key=lambda r: (r['manifest'], r['input'])),
                  'unverified_historical_certificate_references': sorted(certificate_references, key=lambda r: (r['certificate'], r['input']))}
    return release, collected, sources, provenance


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(value)


def _json(path, value):
    _write(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def _copy(source, target, expected):
    _safe_source(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as incoming, target.open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    if sha256(target) != expected or sha256(source) != expected:
        raise ValueError(f'Source changed during export: {source}')


def _license_record(source):
    primary = _workspace_file(source['primary_file'])
    notices = []
    if primary.suffix.lower() == '.xml':
        document = ET.parse(primary)
        for element in document.iter():
            if element.tag.rsplit('}', 1)[-1] == 'license':
                notices.append({'text': ' '.join(''.join(element.itertext()).split()),
                                'attributes': dict(element.attrib)})
    return {**source, 'bundle_primary_file': 'evidence/workspace_sources/' +
            primary.relative_to(ROOT).as_posix(), 'primary_license_notices': notices,
            'redistribution_permission': 'not independently confirmed; local research handoff only'}


def _documents(output, protocol, sources, provenance):
    env = protocol['environment']
    _write(output / 'requirements-lock.txt', '\n'.join([
        '# Frozen Python ' + env['python'], 'numpy==' + env['numpy'], 'pandas==' + env['pandas'],
        'scikit-learn==' + env['scikit_learn'], 'joblib==' + env['joblib'],
        'scipy==' + version('scipy'), 'threadpoolctl==' + version('threadpoolctl'), '']))
    _write(output / 'MODEL_CARD.md', '''# MIC local exploratory model card

This handoff contains nine fold models: logistic regression, random forest, and
dummy prior, each at the single frozen three-fold partition. No best model is
selected and no model is fitted on the full cohort. The 17 admitted molecules,
42 assay statements, 44 fixed features and all 51 OOF probabilities are retained.
The binary E. coli MIC label uses positive upper bound <=32 µg/ml and negative
lower bound >=128 µg/ml; intermediate endpoints are excluded. Homology identity
>=0.40 and shared original studies define joint components. Each partition has
both classes; split seed=42. Repeated statements are not independent replicates.

The scope is replay of admitted cohort samples on their held-out fold only.
Pooled metrics are descriptive. Historical performance was already viewed;
this is exploratory follow-up, not prospective preregistration. Small cohort,
heterogeneous strains/assays and source limitations preclude external validity,
HC50, clinical safety, publication readiness, or formal dual-task conclusions.
The original dual-task study remains blocked. See protocol.json and preserved
evidence/source_review.csv for source-specific limitations and exact methods.

Joblib can execute code when loading. Only load a bundle obtained from a trusted
channel, with its manifest SHA256 supplied through that trusted channel. A hash
does not make an untrusted model safe. The runtime checks the supplied anchor,
all file digests and the frozen environment before loading models; it never fits.
''')
    _write(output / 'README.md', '''# MIC training delivery

This directory is self-contained for offline verification and OOF replay.
Use the exact Python and package versions in requirements-lock.txt. Keep the
manifest SHA256 supplied by the producer separately through a trusted channel.

    python runtime.py verify --bundle . --manifest-sha256 <trusted SHA256>
    python runtime.py replay --bundle . --manifest-sha256 <trusted SHA256>

For one admitted sample, append --sample-id <sample_id>; append --model
logistic_regression, random_forest or dummy_prior to select a predeclared model.
These are held-out fold predictions, not an arbitrary new peptide predictor.

Full training reproduction needs the original research workspace and all its
frozen dependencies, source evidence, historical artifacts and scientific gates.
The delivered sources are audit copies, not a standalone training installation.
From that workspace, choose unused run and delivery directories:

    python 02_code/mic_delivery.py retrain --protocol 03_experiments/protocols/protocol-mic-13.json --freeze 03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json --run 03_experiments/runs/<new-run> --output <new-delivery>

To package an existing frozen run after a fresh independent validation:

    python 02_code/mic_delivery.py build --protocol 03_experiments/protocols/protocol-mic-13.json --freeze 03_experiments/audits/protocol_mic_13_freeze_20261004_v1.json --run 03_experiments/runs/<run> --output <new-delivery>

All new output paths must be unused. The builder prints the manifest SHA256.
validation.json records a real independent no-fit recomputation, performed
before export. Original release decisions and audit certificates are in release/;
evidence/workspace_sources preserves original paths and input/output chains.
evidence/source_index.json maps citations and original source material inside this bundle.
Its closure_scope describes the source-producing manifests that were checked.
Historical certificates are retained, but their previous document inventories are
not verified as current inputs. Any unavailable historical source/document bytes
are listed with expected/current digests; copied current code is not proof of an
old source snapshot and cannot demonstrate the old pipeline's reproduction.
See MODEL_CARD.md for research restrictions and LICENSE_NOTICE.md for permissions.
''')
    _write(output / 'LICENSE_NOTICE.md', '''# Source attribution and permission notice

This is a local research handoff. It is not declared to be an open-source release
or a public redistribution grant. No global CC BY license is asserted. Individual
primary XML license notices, when present, are retained verbatim as data in
evidence/source_index.json along with DOI/URL citations and source locations.
Original acquisition/manifest metadata and source copyright text are copied in
evidence/workspace_sources. A missing XML license is not evidence of permission.
For PDFs, thesis documents, supplements, code and any source without explicit
matching license metadata, public redistribution permission is unconfirmed.
Review the original rights holder's terms before distributing those materials.
''')
    _json(output / 'evidence/source_index.json', {'sources': [_license_record(s) for s in sources],
          **provenance,
          'permission_scope': 'local research handoff; public redistribution not authorized by this package'})


def build_delivery(run, protocol, freeze, output):
    run, protocol, freeze, output = (Path(p).absolute() for p in (run, protocol, freeze, output))
    _unused(output)
    run, protocol, freeze = (p.resolve() for p in (run, protocol, freeze))
    output = output.resolve()
    if not run.is_relative_to(ROOT):
        raise ValueError('Frozen run validation requires a run inside the original research workspace')
    if not RUNTIME.is_file():
        raise ValueError('Standalone delivery runtime is missing')
    if not protocol.is_file() or not freeze.is_file():
        raise ValueError('Mandatory protocol and freeze missing')
    protected = {path: sha256(path) for path in (protocol, freeze, RUNTIME)}
    # The frozen validator checks gates, hashes, all nine models and 51 OOF rows;
    # its fit guards remain active. A previous certificate is never reused.
    with tempfile.TemporaryDirectory(prefix='mic-delivery-validation-') as temp:
        validation_path = Path(temp) / 'validation.json'
        validation = frozen.validate(run, validation_path, protocol, freeze)
        if (validation.get('status') != 'passed' or validation.get('models_reloaded') != 9
                or validation.get('oof_rows_independently_recomputed') != 51
                or validation.get('fit_calls_during_validation') != 0):
            raise ValueError('Independent validation lacks required coverage')
        spec = read_json(protocol)
        release, sources, source_rows, provenance = _source_inventory(spec)
        run_files = {path: sha256(path) for path in _tree(run)}
        if run_files[run / 'manifest.json'] != validation['run_manifest_sha256']:
            raise ValueError('Run manifest changed after independent validation')
        run_manifest = read_json(run / 'manifest.json')
        for name, digest in run_manifest['outputs'].items():
            if run_files.get(run / name) != digest:
                raise ValueError(f'Run output changed after independent validation: {name}')
        if output.is_relative_to(run) or output.is_relative_to(release):
            raise ValueError('Delivery output overlaps immutable inputs')
        if any(output.is_relative_to(path.parent) for path in sources):
            raise ValueError('Delivery output overlaps source evidence')
        output.mkdir(parents=True, exist_ok=False)
        for path, digest in run_files.items():
            _copy(path, output / 'run' / path.relative_to(run), digest)
        for path in _tree(release):
            relative = path.relative_to(release)
            _copy(path, output / 'release' / relative, sources[path])
            if relative.parts[0] in ('cohort', 'evidence'):
                _copy(path, output / relative, sources[path])
        for path, digest in sorted(sources.items()):
            _copy(path, output / 'evidence/workspace_sources' / path.relative_to(ROOT), digest)
        for path, name in ((protocol, 'protocol.json'), (freeze, 'freeze.json'), (RUNTIME, 'runtime.py')):
            _copy(path, output / name, protected[path])
        _copy(validation_path, output / 'validation.json', sha256(validation_path))
        independent = _workspace_file(spec['independent_partition_validation'])
        _copy(independent, output / 'release/independent_partition_validation.json', sources[independent])
        _documents(output, spec, source_rows, provenance)
        files = {path.relative_to(output).as_posix(): sha256(path) for path in _tree(output)}
        manifest = {'schema_version': 1, 'generated_at': utc_now(), 'scope': SCOPE,
                    'protocol_id': spec['protocol_id'], 'sample_ids': spec['sample_ids'],
                    'model_names': list(spec['models']), 'environment': spec['environment'],
                    'artifacts': ARTIFACTS, 'files': files,
                    'models': {name: {str(fold): f'run/fold_models/{name}_fold{fold}.joblib'
                                     for fold in range(3)} for name in spec['models']}}
        _json(output / 'manifest.json', manifest)
    return {'bundle_directory': str(output), 'manifest_sha256': sha256(output / 'manifest.json'),
            'validation': validation, 'manifest': manifest}


def retrain(run, protocol, freeze, output):
    run, output = (Path(p).absolute() for p in (run, output))
    _unused(run)
    _unused(output)
    run, output = run.resolve(), output.resolve()
    if not run.is_relative_to(ROOT):
        raise ValueError('Training run must be inside the original research workspace')
    if run.is_relative_to(output) or output.is_relative_to(run):
        raise ValueError('New run and delivery output must be separate')
    frozen.train(run, Path(protocol).resolve(), Path(freeze).resolve())
    return build_delivery(run, protocol, freeze, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('build', 'retrain'):
        child = commands.add_parser(command)
        for name in ('run', 'protocol', 'freeze', 'output'):
            child.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    entry = build_delivery if args.command == 'build' else retrain
    result = entry(args.run, args.protocol, args.freeze, args.output)
    print(json.dumps({key: result[key] for key in ('bundle_directory', 'manifest_sha256', 'validation')},
                     ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
