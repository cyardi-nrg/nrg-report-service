# Design Lab worker v1.0.0 (2026-10-31) — reads the .env file next to worker.py.
import os
from dataclasses import dataclass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = open(os.path.join(HERE, 'VERSION')).read().strip()


def _load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    for raw in open(path, encoding='utf-8'):
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
            v = v[1:-1]
        os.environ.setdefault(k.strip(), v)


@dataclass
class Config:
    supabase_url: str
    service_key: str
    sa_email: str
    sa_private_key: str
    drive_root: str
    worker_name: str
    poll_seconds: int = 30


def load() -> Config:
    _load_env_file(os.path.join(HERE, '.env'))
    missing = [k for k in ('SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'GOOGLE_SERVICE_ACCOUNT_EMAIL',
                           'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY', 'GOOGLE_DRIVE_ROOT_FOLDER_ID')
               if not os.environ.get(k) or os.environ.get(k, '').startswith('paste-')]
    if missing:
        raise SystemExit('The .env file is missing: ' + ', '.join(missing) + '\nOpen design-lab/worker/.env and fill them in (see .env.example).')
    return Config(
        supabase_url=os.environ['SUPABASE_URL'].rstrip('/'),
        service_key=os.environ['SUPABASE_SERVICE_ROLE_KEY'],
        sa_email=os.environ['GOOGLE_SERVICE_ACCOUNT_EMAIL'],
        sa_private_key=os.environ['GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY'].replace('\\n', '\n'),
        drive_root=os.environ['GOOGLE_DRIVE_ROOT_FOLDER_ID'],
        worker_name=os.environ.get('WORKER_NAME') or os.uname().nodename,
        poll_seconds=int(os.environ.get('POLL_SECONDS', '30')),
    )
