-- NRG SolarConnect — two-stage device-approval authentication
-- Follows 0002-0053.
--
-- New feature, not a port — explicitly requested by the owner (no real
-- legacy source has anything like this; every legacy tool this rebuild
-- has touched so far either has no login at all or a single-factor
-- token, repeatedly flagged as a real security gap to close, not a
-- pattern to imitate). The requirement: an employee's username+password
-- alone must never be enough to reach the data — a NEW device also
-- needs the owner's explicit, one-time approval, after which that
-- device stays trusted (no repeated login prompts) until the owner
-- revokes it. This makes "give my password to a friend" alone
-- insufficient — a friend's device is a device the owner has never
-- approved.

create table user_devices (
  device_id          uuid primary key default gen_random_uuid(),
  employee_id        uuid not null references employees(employee_id),
  device_token_hash  text not null,
    -- sha-256 of a random bearer token issued once in an httpOnly,
    -- secure cookie on the employee's browser — never stored in the
    -- clear, same reasoning as storing a password hash rather than the
    -- password itself. The cookie is what actually proves "this is the
    -- same browser", not anything guessable from the request.
  device_label       text,
    -- best-effort browser/OS string parsed from the User-Agent at
    -- request time, shown to the owner only as a hint when approving —
    -- never used for the actual security decision, which is purely the
    -- token hash match.
  status              text not null default 'pending'
                      check (status in ('pending','approved','denied','revoked')),
  requested_at        timestamptz not null default now(),
  approved_at          timestamptz,
  approved_by           uuid references employees(employee_id),
  last_seen_at           timestamptz,
  unique (employee_id, device_token_hash)
);

create index on user_devices (employee_id);
create index on user_devices (status);

-- ============================================================
-- Lockdown — this table IS the security boundary, so it gets what no
-- other table in this schema has yet: RLS enabled with zero policies.
-- The Supabase anon key is public (shipped in the browser bundle), so
-- without this, anyone with a valid password could call the Supabase
-- REST API directly and self-approve their own device — completely
-- bypassing the app's approval flow. With RLS on and no policies, the
-- anon/authenticated roles get NOTHING on this table, in either
-- direction; only the service-role key (server-only secret, never sent
-- to the browser) can read or write it. The app's own device-approval
-- code (login action, middleware, admin approvals screen) all use the
-- service-role client for exactly this reason — see lib/supabase/
-- server.ts's createServiceRoleClient().
-- ============================================================

alter table user_devices enable row level security;
