-- NRG SolarConnect — Tasks (Internal Team Task Manager + Grading)
-- Follows 0002-0041. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 85.
--
-- Source: the complete Apps Script backend (doGet/doPost/createTask/
-- updateTask/uploadFile) pasted directly by the owner, cross-checked
-- against the real `TASKS` sheet's own header row and sample rows
-- (fetched via Drive — confirms the 14-column layout inferred from the
-- backend's appendRow()/setCol() calls is exact, not a guess), plus
-- `nrg_tasks.html` (nrg-cover, read in full) for the business logic the
-- backend itself never sees: effectiveStatus(), the A-D performance
-- grade formula, and the team leaderboard.
--
-- Genuinely internal, cross-cutting, and NOT project-scoped — confirmed
-- by reading createTask(): no project reference anywhere in the payload.
-- This is a general team task tracker, usable by a tenant with zero
-- other modules enabled, so it gets its own module_entitlements key
-- (`tasks`) and organization_id direct on the one real table, same
-- reasoning as quote_kw_band_rates/referral_contacts/havells_products.
--
-- A real data point from the live sheet that changed this design:
-- `Assignee` is not always an individual — a real row assigns a task to
-- "Office Team", not a named person. Forcing assignee into a hard FK to
-- `employees` would have silently broken on that row. Mirrors the exact
-- pattern already established for `leads.raw_name`/`customer_id`
-- (Section 79): the raw label is always captured, the FK is a nullable
-- best-effort resolution, never a requirement.

create table tasks (
  task_id                 uuid primary key default gen_random_uuid(),
  organization_id         uuid not null references organizations(organization_id),
  title                   text not null,
  description             text,
  assignee_name           text not null,   -- raw, as typed/selected — may be a team label like "Office Team", not always a person
  assignee_id             uuid references employees(employee_id),   -- nullable; resolved only when assignee_name matches a real individual
  assigner_name           text not null,
  assigner_id             uuid references employees(employee_id),
  due_date                date not null,
  priority                text not null default 'medium' check (priority in ('high','medium','low')),
  status                  text not null default 'pending' check (status in ('pending','partially_done','complete')),
     -- 'overdue' is deliberately NOT a stored value here either — see
     -- task_effective_status below, computed exactly like the live
     -- frontend's own effectiveStatus(): Complete always wins regardless
     -- of due date; otherwise overdue if due_date has passed; otherwise
     -- whatever status is actually stored
  pending_reason          text,
  response                text,
  attachment_name         text,
  attachment_drive_file_id text,   -- the Drive file id, not the full URL — same convention as documents.google_drive_file_id and Havells Quotes' pdf_drive_file_id (0041): the id is the durable reference, a URL is always reconstructible from it
  completed_at            date,   -- cleared back to null whenever status moves away from 'complete', matching the live updateTask()'s own behavior exactly
  created_at              timestamptz not null default now()
);

create index on tasks (organization_id);
create index on tasks (assignee_id);
create index on tasks (assignee_name);
create index on tasks (status);
create index on tasks (due_date);

-- ============================================================
-- Effective status — 'overdue' is computed, never stored, so it can
-- never silently disagree with what the app would show. Formula copied
-- exactly from the live frontend's effectiveStatus(): a completed task
-- is never overdue no matter how late it finished; an incomplete task
-- past its due date is overdue regardless of its stored status.
-- ============================================================

create view task_effective_status as
select
  t.task_id,
  case
    when t.status = 'complete' then 'complete'
    when t.due_date < current_date then 'overdue'
    else t.status
  end as effective_status
from tasks t;

-- ============================================================
-- Performance grade — A-D, computed only for completed tasks, exact
-- copy of the live getGrade() formula (verified against its source):
-- on time or early → A if it took at most 85% of the time available
-- between creation and the due date, else B; late → C if 2 days late or
-- less, else D. total_days/used_days use whole-day date arithmetic
-- because the live sheet only ever stores day-granularity dates (no
-- time component), so there is no fractional-day case to reproduce.
-- The due_date = created_at edge case (total_days = 0) is handled the
-- same way the live JS resolves it: NaN <= 0.85 is false there, which
-- falls through to grade B — nullif() below reproduces that exactly.
-- ============================================================

create view task_grade as
select
  t.task_id,
  t.assignee_id,
  t.assignee_name,
  case
    when t.completed_at <= t.due_date then
      case when (t.completed_at - t.created_at::date)::numeric
                / nullif((t.due_date - t.created_at::date), 0) <= 0.85
        then 'A' else 'B' end
    else
      case when (t.completed_at - t.due_date) <= 2 then 'C' else 'D' end
  end as grade
from tasks t
where t.status = 'complete' and t.completed_at is not null;

-- ============================================================
-- Team leaderboard — replaces the live renderLB()'s client-side
-- aggregation exactly: A=4/B=3/C=2/D=1 average grade score per
-- assignee (grouped by assignee_name, not assignee_id, since a team
-- label like "Office Team" has no employee row to group by), overall
-- letter grade at the same >=3.5/>=2.5/>=1.5 thresholds. A tenant with
-- zero completed tasks yet for someone shows no row for them here — the
-- live UI's own "–" placeholder for that case is a display concern, not
-- a schema one.
-- ============================================================

create view employee_task_performance as
select
  t.assignee_name,
  t.assignee_id,
  count(*) as total_tasks,
  count(*) filter (where t.status = 'complete') as done_tasks,
  count(*) filter (where s.effective_status = 'overdue') as overdue_tasks,
  avg(case g.grade when 'A' then 4 when 'B' then 3 when 'C' then 2 when 'D' then 1 end) as avg_grade_score,
  case
    when avg(case g.grade when 'A' then 4 when 'B' then 3 when 'C' then 2 when 'D' then 1 end) is null then null
    when avg(case g.grade when 'A' then 4 when 'B' then 3 when 'C' then 2 when 'D' then 1 end) >= 3.5 then 'A'
    when avg(case g.grade when 'A' then 4 when 'B' then 3 when 'C' then 2 when 'D' then 1 end) >= 2.5 then 'B'
    when avg(case g.grade when 'A' then 4 when 'B' then 3 when 'C' then 2 when 'D' then 1 end) >= 1.5 then 'C'
    else 'D'
  end as overall_grade
from tasks t
join task_effective_status s on s.task_id = t.task_id
left join task_grade g on g.task_id = t.task_id
group by t.assignee_name, t.assignee_id;

-- ============================================================
-- A seventh confirmed no-auth live endpoint, and the most permissive
-- one found this session — worse than the other six (Quote Generator,
-- elec_bill's /ocr-bill, Prospect List, Client Engagement, Referral
-- Network, and this same pattern again). The backend sets
-- `Access-Control-Allow-Origin: *` explicitly on every response, so
-- unlike the others it isn't just reachable by anyone with the URL —
-- it's callable cross-origin from any website's JavaScript, not only
-- from nrg-cover. Not fixed here (schema-only round); adds to the
-- running list real RLS/auth needs to close.
-- ============================================================

insert into module_entitlements (organization_id, module_key, tier) values
  ('00000000-0000-0000-0000-000000000001', 'tasks', 'advanced');
