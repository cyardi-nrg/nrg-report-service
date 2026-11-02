# Design Lab worker v1.7.1 (2026-10-31) — reads the .env file next to worker.py.
# v1.7.1: forgiving for a hand-pasted file — a private key pasted over several lines (with or
#         without quotes), and TextEdit's curly quotes, are both read correctly.
import os
from dataclasses import dataclass

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = open(os.path.join(HERE, 'VERSION')).read().strip()

QUOTES = {'"': '"', "'": "'", '\u201c': '\u201d', '\u2018': '\u2019'}


def _load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    lines = open(path, encoding='utf-8-sig').read().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip()
        # a quoted value that goes on over more lines (e.g. a private key pasted with real line breaks)
        if v and v[0] in QUOTES and not (len(v) >= 2 and v[-1] == QUOTES[v[0]]):
            close, parts = QUOTES[v[0]], [v[1:]]
            while i < len(lines):
                nxt = lines[i].rstrip()
                i += 1
                if nxt.endswith(close):
                    parts.append(nxt[:-1]); break
                parts.append(nxt)
            v = '\n'.join(p.strip() for p in parts)
        elif len(v) >= 2 and v[0] in QUOTES and v[-1] == QUOTES[v[0]]:
            v = v[1:-1]
        # an unquoted private key pasted over several lines: read on to the END line
        if 'BEGIN' in v and 'PRIVATE KEY' in v and 'END' not in v:
            parts = [v]
            while i < len(lines):
                nxt = lines[i].strip()
                i += 1
                parts.append(nxt)
                if 'END' in nxt and 'PRIVATE KEY' in nxt:
                    break
            v = '\n'.join(parts)
        os.environ.setdefault(k, v)


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
