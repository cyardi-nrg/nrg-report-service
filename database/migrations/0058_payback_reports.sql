-- NRG SolarConnect — Payback & Project Report tool
--
-- Real source: Quote Generator's own 'Payback Reports' tab (columns
-- Date/Client/Phone/Email/kW/Cost/Monthly Savings/Payback Period/Report
-- Type/Salesperson/Quote Ref/PDF Link/WA Sent/Email Sent), plus the real
-- input form (4 steps: Client & Project / System & Tariff / Financing /
-- Live Preview) and formulas verified this session against two real
-- sample PDFs (Capiq Engineering Payback report, A.S. Insulators Project
-- Report). One shared input record; two distinct formula sets render off
-- it (Payback: no panel degradation; Project Report: 0.5%/yr degradation)
-- — captured here as inputs only, the two output views are computed, not
-- stored, per the schema's "compute, don't store" discipline elsewhere.

create table payback_reports (
  payback_report_id        uuid primary key default gen_random_uuid(),
  report_number             text not null unique,   -- from next_document_number('payback_report', 'perpetual')
  client_name               text not null,
  phone                     text,
  email                     text,
  quote_ref                 text,                    -- free text — the real Quote Ref this was generated from, if any
  quote_id                  uuid references quotes(quote_id),

  system_size_kw            numeric(10,3) not null,
  turnkey_cost               numeric(14,2) not null,
  subsidy_or_discount        numeric(14,2) not null default 0,
  generation_units_per_kw_day numeric(6,2) not null default 4.0,
  banking_charge             numeric(6,2) not null default 1.5,
  electricity_rate           numeric(6,2) not null default 8.5,
  tariff_escalation_pct      numeric(5,2) not null default 2.5,
  reinvest_return_pct        numeric(5,2) not null default 8.0,

  debt_pct                   numeric(5,2) not null default 80,
  loan_annual_rate_pct       numeric(5,2) not null default 10.5,
  loan_tenure_years          numeric(4,1) not null default 5,

  salesperson_id             uuid references employees(employee_id),
  created_by                 uuid references employees(employee_id),
  wa_sent_at                 timestamptz,
  created_at                 timestamptz not null default now()
);

create index on payback_reports (quote_id);
create index on payback_reports (client_name);
