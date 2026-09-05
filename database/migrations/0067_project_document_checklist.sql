-- NRG SolarConnect — Project Document Checklist
-- Follows 0002-0066.
--
-- The owner's ask, directly: a progress card for "what documents does
-- this client still need to give us" — same shape as the GEDA/CEIG
-- milestone cards on Overview, with a per-item "Not needed" mark so
-- tracking stays honest (an apartment project genuinely has no board
-- resolution to chase). quote_type_terms.document_requirements (0065)
-- already holds the real per-quote-type requirement text ("Recent
-- electricity (light) bill", "PAN card of company or PAN card of
-- owner", ...) but that's a template, not a per-project tracked state —
-- this table is the per-project instance of it: one row per requirement
-- label, seeded once from the template and then tracked independently
-- (a project can gain/lose items the template doesn't have, and its own
-- status never mutates the shared template).
--
-- Deliberately its own table rather than reusing project_document_
-- exemptions (0026): that one is keyed by the classifier's document_type
-- enum and only ever means "not applicable" for a real scanned-document
-- category. Requirement labels here are free text ("Cancelled cheque",
-- "Passport-size photograph") that mostly have no matching document_type
-- at all, and need a genuine three-state status (still needed / actually
-- received / not needed), not just an exemption flag.
create table project_document_checklist (
  checklist_item_id  uuid primary key default gen_random_uuid(),
  project_id         uuid not null references projects(project_id),
  requirement_label  text not null,
  status             text not null default 'pending'
                       check (status in ('pending', 'received', 'not_needed')),
  note               text,          -- required when marking not_needed — why it doesn't apply here
  updated_by         uuid references employees(employee_id),
  updated_at         timestamptz not null default now(),
  created_at         timestamptz not null default now(),
  unique (project_id, requirement_label)
);

create index on project_document_checklist (project_id);
create index on project_document_checklist (status);

comment on table project_document_checklist is
  'Per-project tracked instance of quote_type_terms.document_requirements — one row per requirement, seeded once (insert ... on conflict do nothing) and then tracked independently via app/(app)/projects/[id]/actions.ts. Feeds the Overview "Documents Required" card and the Pending page''s sales-backend reminder list.';
