"""Restart a checkpointed cloud runner after SIGTERM, with explicit stop and limits."""
from pathlib import Path
import argparse
import os
import signal
import subprocess
import sys
import time


def supervise(command, state, delay=15.0, max_restarts=10):
    restarts = 0
    while not state['stop']:
        print(f'[SUPERVISOR] starting training | restart={restarts}/{max_restarts}', flush=True)
        child = subprocess.Popen(command, start_new_session=True)
        state['child'] = child
        code = child.wait()
        state['child'] = None
        if state['stop']:
            return 130
        if code == 0:
            print('[SUPERVISOR] training completed; no restart', flush=True)
            return 0
        if code not in (-signal.SIGTERM, 143):
            print(f'[SUPERVISOR] training failed with exit={code}; stopping for inspection', flush=True)
            return code if code > 0 else 128 - code
        if restarts >= max_restarts:
            print('[SUPERVISOR] restart limit reached; inspect platform before continuing', flush=True)
            return 143
        restarts += 1
        print(f'[SUPERVISOR] training received SIGTERM; resume in {delay:g}s', flush=True)
        time.sleep(delay)
    return 130


def other_training_processes():
    """Refuse a second runner or the user's older auto-restart scripts."""
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            arguments = (entry / 'cmdline').read_bytes().split(b'\0')
        except OSError:
            continue
        for argument in arguments:
            name = Path(os.fsdecode(argument)).name
            if name in ('run_experiments_v5.py', 'watch_training.sh', 'start_training.sh'):
                found.append((entry.name, name))
                break
    return found


def main():
    if sys.platform != 'linux':
        raise SystemExit('This tool is for the Linux cloud workspace; no local training was started.')
    import fcntl

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-restarts', type=int, default=10)
    parser.add_argument('--delay', type=float, default=15.0)
    args = parser.parse_args()
    if args.max_restarts < 0 or args.delay < 1:
        parser.error('max-restarts must be nonnegative and delay must be at least 1 second')
    root = Path(__file__).resolve().parent
    runner = root / 'output/dta-paper-run-v5-20261009/scripts/run_experiments_v5.py'
    if not runner.is_file():
        raise SystemExit(f'Missing runner: {runner}')
    if Path(sys.prefix).resolve() != (root / '.venv-cloud').resolve():
        raise SystemExit('Start with .venv-cloud/bin/python supervise_training.py')
    os.chdir(root)
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '8'
    lock = (root / '.training-supervisor.lock').open('a+')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise SystemExit('Another supervisor is already running; do not start a second one.')
    others = other_training_processes()
    if others:
        lock.close()
        raise SystemExit(f'Existing training/monitor processes: {others}. Stop them before starting.')

    state = {'stop': False, 'child': None}
    pid_path = root / 'training-supervisor.pid'
    pid_path.write_text(str(os.getpid()), encoding='ascii')

    def stop(signum, frame):
        state['stop'] = True
        child = state['child']
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        return supervise([sys.executable, '-u', str(runner)], state, args.delay, args.max_restarts)
    finally:
        child = state['child']
        if child is not None and child.poll() is None:
            stop(signal.SIGTERM, None)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        pid_path.unlink(missing_ok=True)
        lock.close()


if __name__ == '__main__':
    sys.exit(main())
