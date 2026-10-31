#!/usr/bin/env python3
# Design Lab worker v1.1.0 (2026-10-31) — runs on the owner's Mac.
#
# Owner's own asks: "heavy work ... on my Mac"; the video "scheduled for
# work after 9 PM or 10 PM when my MacBook will be on ... generated
# overnight ... send it to the client the next day morning".
#
# Every 30 s: say "I'm on" (design_workers heartbeat, shown in the Design
# Lab), then take the oldest queued job that this Mac can do and whose
# run_after time has passed (the Design Lab sets run_after to tonight
# 9 / 10 PM for the video). The job is claimed atomically (only if it is
# still 'queued'), so two Macs never take the same job. While a job runs,
# macOS is kept awake (caffeinate). Results go to the project's Drive
# folder + documents, and a new stage version waits for approval.
#
#   python3 worker.py              run for ever (launchd starts it at login)
#   python3 worker.py --once       take at most one job, then stop
#   python3 worker.py --selftest   check the .env, Supabase and Drive, then stop
import argparse
import datetime as dt
import logging
import logging.handlers
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from nrg import config as cfgmod                       # noqa: E402
from nrg.supa import Supa                              # noqa: E402
from nrg.drive import Drive                            # noqa: E402
from nrg.jobs import Job, NotBuiltYet, now_iso         # noqa: E402
import handlers                                        # noqa: E402

os.makedirs(os.path.join(HERE, 'logs'), exist_ok=True)
log = logging.getLogger('designlab')
log.setLevel(logging.INFO)
_fh = logging.handlers.RotatingFileHandler(os.path.join(HERE, 'logs', 'worker.log'), maxBytes=2_000_000, backupCount=5)
_fh.setFormatter(logging.Formatter('%(asctime)s  %(levelname)s  %(message)s'))
log.addHandler(_fh)
log.addHandler(logging.StreamHandler(sys.stdout))

STOP = False


def code_stamp() -> float:
    """Newest change to the worker's own files — after a GitHub Desktop 'Pull' it moves, the worker exits
    between jobs and launchd starts the new version (KeepAlive)."""
    newest = 0.0
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in ('.venv', 'logs', '__pycache__', '.git')]
        for f in files:
            if f.endswith('.py') or f in ('VERSION', 'requirements.txt'):
                newest = max(newest, os.path.getmtime(os.path.join(root, f)))
    return newest


def _stop(*_):
    global STOP
    STOP = True
    log.info('Stopping after the current step…')


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)


class Worker:
    def __init__(self, cfg):
        self.cfg = cfg
        self.db = Supa(cfg.supabase_url, cfg.service_key)
        self.drive = Drive(cfg.sa_email, cfg.sa_private_key)
        self.name = cfg.worker_name
        self.caps = handlers.capabilities()
        self.heartbeat_ok = True
        self.current_job = None
        self.wait_awake = None  # caffeinate held until tonight's job is due

    # ------------------------------------------------------------ heartbeat
    def heartbeat(self, status: str) -> None:
        try:
            self.db.upsert('design_workers', {
                'worker': self.name, 'host': socket.gethostname(), 'version': cfgmod.VERSION, 'capabilities': self.caps,
                'status': status, 'current_job_id': self.current_job, 'last_seen': now_iso(),
            }, on_conflict='worker')
            self.heartbeat_ok = True
        except Exception as e:  # the table may not exist yet — never stop working for this
            if self.heartbeat_ok:
                log.warning(f'Heartbeat not recorded (the Design Lab will show the Mac as unknown): {e}')
            self.heartbeat_ok = False

    # ------------------------------------------------------------ jobs
    def release_stale(self) -> None:
        """Jobs this Mac was running when it slept / quit go back in the queue."""
        rows = self.db.update('design_jobs', {'status': 'eq.running', 'worker': f'eq.{self.name}'}, {'status': 'queued', 'started_at': None})
        if rows:
            log.info(f'Put {len(rows)} unfinished job(s) back in the queue.')

    def next_job(self) -> dict | None:
        if not self.caps:
            return None
        rows = self.db.select('design_jobs', {
            'status': 'eq.queued', 'stage': f"in.({','.join(self.caps)})",
            'or': f'(run_after.is.null,run_after.lte.{now_iso()})',
            'select': '*', 'order': 'created_at.asc', 'limit': 5,
        })
        for r in rows:
            claimed = self.db.update('design_jobs', {'job_id': f"eq.{r['job_id']}", 'status': 'eq.queued'},
                                     {'status': 'running', 'worker': self.name, 'started_at': now_iso(), 'error': None})
            if claimed:
                return claimed[0]
        return None

    def stay_awake_for_tonight(self) -> None:
        """The Mac wakes at 8:55 PM (pmset, see README); if a job this Mac can do is due within 4 hours,
        keep it from dozing off again before then, so the 9 / 10 PM video really starts on time."""
        if sys.platform != 'darwin' or not self.caps or not shutil.which('caffeinate'):
            return
        if self.wait_awake and self.wait_awake.poll() is None:
            return
        try:
            nxt = self.db.select('design_jobs', {'status': 'eq.queued', 'stage': f"in.({','.join(self.caps)})", 'run_after': f'gt.{now_iso()}',
                                                 'select': 'run_after', 'order': 'run_after.asc', 'limit': 1})
        except Exception:
            return
        if not nxt:
            return
        due = dt.datetime.fromisoformat(nxt[0]['run_after'].replace('Z', '+00:00'))
        secs = (due - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if 0 < secs <= 4 * 3600:
            log.info(f'A job is due at {due.astimezone().strftime("%I:%M %p")} — keeping the Mac awake until then.')
            self.wait_awake = subprocess.Popen(['caffeinate', '-i', '-t', str(int(secs) + 120)])

    def run_job(self, row: dict) -> None:
        self.current_job = row['job_id']
        self.heartbeat('running')
        awake = None
        if sys.platform == 'darwin' and shutil.which('caffeinate'):
            awake = subprocess.Popen(['caffeinate', '-dimsu', '-w', str(os.getpid())])  # keep the Mac awake while this job runs
        started = time.time()
        log.info(f"Job {row['job_id'][:8]} · {row['stage']} · started")
        job = None
        try:
            job = Job(self.db, self.drive, row, self.name)
            job.drive_root = self.cfg.drive_root
            result = handlers.run(job) or {}
            summary = result.get('summary') or 'Done.'
            if not result.get('no_version'):
                job.save_version(result)
            self.db.update('design_jobs', {'job_id': f"eq.{row['job_id']}"}, {
                'status': 'done', 'finished_at': now_iso(), 'output': {'summary': summary, 'document_ids': job.document_ids}})
            log.info(f"Job {row['job_id'][:8]} · done in {time.time() - started:.0f} s · {len(job.document_ids)} file(s)")
        except NotBuiltYet as e:
            self.db.update('design_jobs', {'job_id': f"eq.{row['job_id']}"}, {'status': 'failed', 'finished_at': now_iso(), 'error': str(e)})
            log.info(f"Job {row['job_id'][:8]} · {e}")
        except Exception as e:
            log.error(f"Job {row['job_id'][:8]} · failed: {e}\n{traceback.format_exc()}")
            msg = f'{type(e).__name__}: {e}'[:900]
            try:
                self.db.update('design_jobs', {'job_id': f"eq.{row['job_id']}"}, {'status': 'failed', 'finished_at': now_iso(), 'error': msg})
            except Exception as e2:
                log.error(f'Could not even mark the job failed: {e2}')
        finally:
            if awake:
                awake.terminate()
            if job:
                shutil.rmtree(job.workdir, ignore_errors=True)
            self.current_job = None
            self.heartbeat('idle')

    def loop(self, once: bool = False) -> None:
        log.info(f'Design Lab worker {cfgmod.VERSION} on “{self.name}” · can do: {", ".join(self.caps) or "nothing yet (core only)"}')
        self.release_stale()
        last_beat = 0.0
        stamp = code_stamp()
        while not STOP:
            if code_stamp() != stamp:
                log.info('The worker was updated — restarting to use the new version.')
                break
            if time.time() - last_beat > 55:
                self.heartbeat('idle')
                last_beat = time.time()
            try:
                row = self.next_job()
            except Exception as e:
                log.warning(f'Could not check the queue (no internet?): {e}')
                row = None
            if row:
                self.run_job(row)
                last_beat = time.time()
                if once:
                    return
                continue
            if once:
                log.info('Nothing to do right now.')
                return
            self.stay_awake_for_tonight()
            for _ in range(self.cfg.poll_seconds):
                if STOP:
                    break
                time.sleep(1)
        self.heartbeat('stopped')


def selftest(cfg) -> int:
    ok = True
    print(f'Design Lab worker {cfgmod.VERSION} · self-test on “{cfg.worker_name}”\n')
    w = Worker(cfg)
    try:
        n = len(w.db.select('design_jobs', {'select': 'job_id', 'status': 'eq.queued', 'limit': 1000}))
        print(f'  ✓ Supabase: connected — {n} job(s) waiting in the queue')
    except Exception as e:
        ok = False
        print(f'  ✗ Supabase: {e}\n    → check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env')
    try:
        print(f'  ✓ Google Drive: can open the root folder “{w.drive.folder_name(cfg.drive_root)}”')
    except Exception as e:
        ok = False
        print(f'  ✗ Google Drive: {e}\n    → check the GOOGLE_* lines in .env (copy them exactly from Railway)')
    w.heartbeat('idle')
    print('  ✓ Heartbeat: the Design Lab will show this Mac as online' if w.heartbeat_ok else '  ! Heartbeat: not recorded yet (the design_workers table is missing — ask Claude to apply migration 0163)')
    print(f'  · This Mac can do: {", ".join(w.caps) or "nothing yet — core only (phase 1)"}')
    print('\nAll good.' if ok else '\nFix the ✗ lines above, then run the self-test again.')
    return 0 if ok else 1


def sync_packages() -> None:
    """After an update that needs new Python packages, install them into the worker's own .venv."""
    req, stamp = os.path.join(HERE, 'requirements.txt'), os.path.join(HERE, '.venv', '.requirements-installed')
    if not os.path.isdir(os.path.join(HERE, '.venv')) or not sys.prefix.startswith(os.path.join(HERE, '.venv')):
        return
    if os.path.exists(stamp) and open(stamp).read() == open(req).read():
        return
    log.info('Installing the Python packages this version needs…')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '-r', req], check=True)
    if 'playwright' in open(req).read():
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=False)   # 3D pictures / video (phase 4)
    open(stamp, 'w').write(open(req).read())


if __name__ == '__main__':
    sync_packages()
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    c = cfgmod.load()
    if a.selftest:
        sys.exit(selftest(c))
    Worker(c).loop(once=a.once)
