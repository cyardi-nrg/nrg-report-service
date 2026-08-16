-- NRG SolarConnect — Customer Aliases and a Reference-Type Bug Fix
-- Follows 0002-0011. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 39.

-- ============================================================
-- Customer aliases
-- ============================================================

-- Real case: an electricity bill shows the legal owner's name
-- ("Satish Garg") while the whole team only ever refers to the project
-- by its business name ("Agarwal Roadlines"). customers.name (0002)
-- stays the primary/display name; aliases holds every other name
-- variant AI has seen on documents for this customer — same pattern
-- materials.aliases (0002) already uses for material name matching.

alter table customers add column aliases text[];

-- ============================================================
-- Bug fix: project_external_references.reference_type was never
-- actually free text
-- ============================================================

-- Section 24 explicitly decided this needed to stay a flexible,
-- extensible list rather than a fixed enum — but the shipped 0002
-- migration gave it a hard check constraint anyway, silently
-- contradicting its own documented reasoning. This blocked adding new
-- reference types (e.g. DISCOM's SR No., Section 39) without a
-- migration every time. Fixed to match every other categorical field
-- in this schema.

alter table project_external_references drop constraint project_external_references_reference_type_check;

-- Existing values ('nrg_internal','discom_consumer_number',
-- 'geda_residential','geda_commercial','ceig') remain valid — this
-- only removes the constraint stopping new ones (e.g.
-- 'discom_sr_no') from being added without a schema change.
