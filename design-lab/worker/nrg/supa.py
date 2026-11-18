# Design Lab worker v1.0.0 (2026-10-31) — the Supabase database, through its
# REST API (PostgREST) with the service-role key. The service role is not
# held back by the owner-only row rules, which is why the worker uses it.
import json
import requests


class Supa:
    def __init__(self, url: str, key: str):
        self.base = url + '/rest/v1'
        self.s = requests.Session()
        self.s.headers.update({'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})

    def _check(self, r: requests.Response):
        if r.status_code >= 400:
            raise RuntimeError(f'Supabase {r.request.method} {r.url.split("?")[0].rsplit("/", 1)[-1]} failed ({r.status_code}): {r.text[:400]}')
        return r

    def select(self, table: str, params: dict) -> list:
        return self._check(self.s.get(f'{self.base}/{table}', params=params, timeout=60)).json()

    def one(self, table: str, params: dict):
        rows = self.select(table, {**params, 'limit': 1})
        return rows[0] if rows else None

    def insert(self, table: str, row: dict | list, returning: bool = True) -> list:
        h = {'Prefer': 'return=representation' if returning else 'return=minimal'}
        r = self._check(self.s.post(f'{self.base}/{table}', data=json.dumps(row), headers=h, timeout=60))
        return r.json() if returning else []

    def upsert(self, table: str, row: dict, on_conflict: str) -> None:
        h = {'Prefer': 'resolution=merge-duplicates,return=minimal'}
        self._check(self.s.post(f'{self.base}/{table}', params={'on_conflict': on_conflict}, data=json.dumps(row), headers=h, timeout=60))

    def update(self, table: str, filters: dict, patch: dict) -> list:
        """Returns the rows actually changed — used to claim a job only if it is still queued."""
        h = {'Prefer': 'return=representation'}
        return self._check(self.s.patch(f'{self.base}/{table}', params=filters, data=json.dumps(patch), headers=h, timeout=60)).json()
