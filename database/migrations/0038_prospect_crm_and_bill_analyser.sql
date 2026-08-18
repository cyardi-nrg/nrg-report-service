-- NRG SolarConnect — Prospect CRM + Solar Bill Analyser
-- Follows 0002-0037. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 81.
--
-- The two safest, most self-contained remaining live tools (docs/
-- sales-service-migration-plan.md's own risk tiering) — neither shares
-- a live spreadsheet with anything else, unlike the Quote/Follow-up
-- pair (0036). Gated behind module_entitlements (0035) module_key =
-- 'prospect_crm' and 'bill_analyser'.

-- ============================================================
-- Prospect CRM — cold-outreach tracking for companies NRG hasn't
-- engaged yet. Deliberately built to match what the live data actually
-- shows is used, not what the live code merely implements. Reading
-- the real spreadsheet (not just the code) found the elaborate 8-month
-- drip-sequence/batch/stage-progression engine is dormant in practice
-- — 3,690 companies, only 15 ever ran through it, all 180 scheduled
-- steps stuck "Pending" forever because nothing marks them sent. Real
-- activity (507 touches in the week reviewed) runs through a much
-- simpler activity log instead. Building the dormant engine here would
-- be over-building against evidence that says otherwise — so this
-- migration builds the parts that are genuinely used, and explicitly
-- does NOT build automated sequencing/batching. If real demand for
-- that shows up later, it's a schema addition, not a redesign of what
-- exists here.
-- ============================================================

create table prospect_companies (
  company_id           uuid primary key default gen_random_uuid(),
  name                 text not null,
  address              text,
  industry             text,
  gidc_plot_no         text,
  roof_area_sqft       numeric(12,2),
  estimated_solar_kw   numeric(10,2),
  estimated_saving     numeric(14,2),
  solar_already_detected  boolean,
  temperature          text not null default 'cold' check (temperature in ('hot','warm','cold')),
  stage                text not null default 'new',   -- free text, app-level reference list — same reasoning as customer_pipeline.stage's numeric equivalent (0036), kept as text here to match the live system's real stage vocabulary directly
  entry_method         text,      -- 'manual' | 'gidc_file' | 'source_approved' — how this row came to exist, kept for provenance (99.6% of live rows are a single bulk import — worth being able to tell that apart from a hand-added prospect)
  contact1_name        text,
  contact1_mobile       text,
  contact1_email         text,
  assigned_to             uuid references employees(employee_id),
  won_date                  date,
  lost_date                   date,
  converted_lead_id            uuid references leads(lead_id),   -- set once this prospect is actually engaged (0036) — the real bridge from cold prospecting into the sales pipeline
  merged_into_company_id         uuid references prospect_companies(company_id),   -- same dedup/repair pattern as materials/projects/customers (Sections 60/69/80)
  notes                            text,
  created_at                        timestamptz not null default now(),
  updated_at                         timestamptz not null default now()
);

create index on prospect_companies (assigned_to);
create index on prospect_companies (stage);
create index on prospect_companies (merged_into_company_id);

-- Hotels, Hospitals, Builder Groups, and Builder Projects are kept as
-- separate tables rather than jammed into prospect_companies — the
-- live system treats them as genuinely different record shapes
-- (Havells heat-pump prospecting for hotels/hospitals vs. solar
-- prospecting for factories; a builder project carries a RERA
-- completion date factories don't have), and conflating them would
-- lose real distinctions the live system already draws correctly.

create table prospect_hotels (
  hotel_id             uuid primary key default gen_random_uuid(),
  name                 text not null,
  address              text,
  room_count           integer,
  temperature          text not null default 'cold' check (temperature in ('hot','warm','cold')),
  stage                text not null default 'new',
  contact1_name        text,
  contact1_mobile       text,
  assigned_to             uuid references employees(employee_id),
  converted_lead_id         uuid references leads(lead_id),
  notes                       text,
  created_at                   timestamptz not null default now()
);

create table prospect_hospitals (
  hospital_id          uuid primary key default gen_random_uuid(),
  name                 text not null,
  address              text,
  bed_count            integer,
  temperature          text not null default 'cold' check (temperature in ('hot','warm','cold')),
  stage                text not null default 'new',
  contact1_name        text,
  contact1_mobile       text,
  assigned_to             uuid references employees(employee_id),
  converted_lead_id         uuid references leads(lead_id),
  notes                       text,
  created_at                   timestamptz not null default now()
);

create table prospect_builder_groups (
  builder_group_id  uuid primary key default gen_random_uuid(),
  name              text not null,
  notes             text,
  created_at        timestamptz not null default now()
);

create table prospect_builder_projects (
  builder_project_id  uuid primary key default gen_random_uuid(),
  builder_group_id    uuid references prospect_builder_groups(builder_group_id),
  name                text not null,
  address             text,
  rera_number         text,
  rera_completion_date  date,   -- drives the live system's "Approach Radar" (24 months out for Havells electrical, 12 for solar) — kept as a plain date here, the timing rule itself is a reporting/query concern, not schema
  project_type          text,   -- 'residential' | 'commercial' | 'mixed' — free text
  temperature             text not null default 'cold' check (temperature in ('hot','warm','cold')),
  stage                     text not null default 'new',
  assigned_to                 uuid references employees(employee_id),
  converted_lead_id             uuid references leads(lead_id),
  notes                           text,
  created_at                       timestamptz not null default now()
);

create index on prospect_builder_projects (builder_group_id);
create index on prospect_builder_projects (rera_completion_date);

-- Site contacts (civil incharge, PMC, architect, electrical/plumbing
-- consultant, main contractor) found on a builder project/hotel/
-- hospital — a cross-project directory the sales team mines for
-- referrals. Exactly one of the three FKs is set per row.
create table prospect_site_contacts (
  contact_id           uuid primary key default gen_random_uuid(),
  builder_project_id   uuid references prospect_builder_projects(builder_project_id),
  hotel_id             uuid references prospect_hotels(hotel_id),
  hospital_id          uuid references prospect_hospitals(hospital_id),
  role                 text not null,   -- 'civil_incharge' | 'pmc' | 'architect' | 'electrical_consultant' | 'plumbing_consultant' | 'main_contractor' | ... free text
  name                 text not null,
  mobile               text,
  created_at           timestamptz not null default now(),
  check (
    (case when builder_project_id is not null then 1 else 0 end
     + case when hotel_id is not null then 1 else 0 end
     + case when hospital_id is not null then 1 else 0 end) = 1
  )
);

create index on prospect_site_contacts (builder_project_id);
create index on prospect_site_contacts (hotel_id);
create index on prospect_site_contacts (hospital_id);
create index on prospect_site_contacts (mobile);

-- ============================================================
-- One unified touch log — the live system had two parallel,
-- non-integrated logging paths (an old "TOUCH LOG" mechanism that
-- nothing live actually calls, and a newer "PROSPECT ACTIVITY" log
-- that's what real usage runs through) — confirmed real fragmentation,
-- fixed here the same way the Quote/Follow-up split was fixed
-- (Section 79): one table, one shape, always.
-- ============================================================

create table prospect_activity_log (
  activity_id          uuid primary key default gen_random_uuid(),
  company_id           uuid references prospect_companies(company_id),
  hotel_id             uuid references prospect_hotels(hotel_id),
  hospital_id          uuid references prospect_hospitals(hospital_id),
  builder_project_id   uuid references prospect_builder_projects(builder_project_id),
  salesperson_id       uuid not null references employees(employee_id),
  action               text not null check (action in ('call','whatsapp','visit')),
  notes                text,
  created_at           timestamptz not null default now(),
  check (
    (case when company_id is not null then 1 else 0 end
     + case when hotel_id is not null then 1 else 0 end
     + case when hospital_id is not null then 1 else 0 end
     + case when builder_project_id is not null then 1 else 0 end) = 1
  )
);

create index on prospect_activity_log (company_id);
create index on prospect_activity_log (salesperson_id);
create index on prospect_activity_log (created_at);

-- ============================================================
-- Sources — the RERA/MCA scraper review queue. Kept, deliberately,
-- even though the live scrapers are confirmed pure stubs (they log a
-- message and do nothing else, despite having real trigger schedules
-- that make them look active) — the review-queue *shape* (something
-- proposes a prospect, a human approves or rejects it) is the same
-- real, useful "AI/automation suggests, human confirms" pattern used
-- throughout this schema, and costs nothing to keep even with no real
-- scraper behind it yet. Building the scraper itself is an
-- application-layer/integration job for whenever there's real RERA/MCA
-- API access, not a schema concern.
-- ============================================================

create table prospect_sources (
  source_id       uuid primary key default gen_random_uuid(),
  raw_name        text not null,
  raw_address     text,
  source_type     text,   -- 'rera' | 'mca' | 'manual' — free text
  status          text not null default 'pending' check (status in ('pending','approved','rejected')),
  approved_as_company_id  uuid references prospect_companies(company_id),   -- set on approval
  reviewed_by     uuid references employees(employee_id),
  reviewed_at     timestamptz,
  created_at      timestamptz not null default now()
);

create index on prospect_sources (status);

-- ============================================================
-- Solar Bill Analyser — a standalone lead-generation tool, confirmed
-- the cleanest and simplest of all five live tools read (no dead code,
-- no dormant automation found). One report per bill analysed.
-- ============================================================

create table bill_analysis_settings (
  organization_id                     uuid primary key references organizations(organization_id),
    -- no anchor table to inherit from (Section 78) — tenant-level sizing config
  generation_factor_units_per_kw_day  numeric(6,2) not null default 4,
  banking_percent_lt_ht               numeric(5,2) not null default 30,
  banking_charge_rs_per_unit          numeric(6,2) not null default 1.5,
  roof_sqft_per_kw                    numeric(6,2) not null default 100,
  transformer_factor                  numeric(4,2) not null default 0.9,
  default_working_hours               numeric(4,1) not null default 24,
  updated_at                           timestamptz not null default now()
);

create table bill_analysis_rate_bands (
  band_id          uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references organizations(organization_id),
  kw_min           numeric(10,2) not null,
  kw_max           numeric(10,2) not null,
  rate_per_kw      numeric(14,2) not null,
  updated_at       timestamptz not null default now(),
  check (kw_max > kw_min)
);

create index on bill_analysis_rate_bands (organization_id);

create table bill_analysis_reports (
  report_id              uuid primary key default gen_random_uuid(),
  lead_id                uuid references leads(lead_id),   -- set once someone follows up on this analysis — the bridge into the sales pipeline (0036), same role converted_lead_id plays for prospects above
  client_name            text not null,
  consumer_no            text,
  discom                 text,
  tariff_code            text,
  category               text,      -- 'residential' | 'non_residential' | 'lt_industrial' | 'ht_industrial' | 'unknown' — derived from tariff_code at analysis time, salesperson can override
  is_residential          boolean,
  contract_demand_kva      numeric(10,2),
  billing_period_days       integer,
  units_this_bill             numeric(12,2),
  day_units                     numeric(12,2),
  night_units                     numeric(12,2),
  effective_rate                   numeric(10,4),   -- ₹/unit — salesperson override always wins over OCR-derived rate, same reasoning as the live system
  ed_exempt                          boolean,
  recommended_kw                       numeric(10,2),
  annual_generation_units                numeric(14,2),
  self_use_percent                         numeric(5,2),
  bill_reduction_percent                     numeric(5,2),
  roof_sqft_required                           numeric(12,2),
  transformer_kva_required                       numeric(10,2),
  contract_demand_exceeded                         boolean not null default false,
  system_price                                       numeric(14,2),
  annual_saving                                        numeric(14,2),
  payback_years                                          numeric(6,2),
  original_bill_document_id                                uuid references documents(document_id),
  report_document_id                                          uuid references documents(document_id),
  created_by                                                    uuid references employees(employee_id),
  created_at                                                      timestamptz not null default now()
);

create index on bill_analysis_reports (lead_id);
create index on bill_analysis_reports (created_by);

-- ============================================================
-- What this migration does NOT do
-- ============================================================
-- No automated drip-sequence/campaign/batch engine for Prospect CRM —
-- confirmed dormant in the live system's own real data, built here to
-- match actual usage instead. No RERA/MCA scraper implementation —
-- the review-queue shape exists (prospect_sources), the scraper itself
-- doesn't. No OCR (bill scan or business card) — application-layer,
-- same reasoning as every other module. No RLS — same standing item
-- as every module so far.
