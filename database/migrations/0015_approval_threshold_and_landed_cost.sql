-- NRG SolarConnect — Approval Threshold, Landed-Cost Estimates, Vendor Specialties
-- Follows 0002-0014. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 42.

-- ============================================================
-- Bring every vendor's quote onto the same landed-cost basis
-- ============================================================

-- includes_transport/includes_loading_unloading (0013) say whether a
-- rate already covers these — but when it doesn't, MP needs somewhere
-- to put an estimate, or vendors still aren't actually comparable.

alter table vendor_quote_items add column estimated_transport_charge numeric(14,2);
alter table vendor_quote_items add column estimated_loading_unloading_charge numeric(14,2);

-- Populated by MP when includes_transport/includes_loading_unloading is
-- false, so the comparison can show an effective landed total per
-- vendor (rate × qty + these estimates), not just the printed rate.

-- ============================================================
-- Approval threshold on quote comparison requests
-- ============================================================

-- Confirmed real rule: any comparison totalling more than ₹25,000
-- routes to the owner automatically; MP self-clears anything under
-- that. The threshold itself lives at the application layer (no
-- general settings table exists yet to store it in, and it's the kind
-- of number that will get tuned) — this just gives the request a
-- stable total to route and notify on, snapshotted at submission
-- rather than recomputed live (so it can't drift if quotes change
-- after the owner's already been notified about a specific number).

alter table quote_comparison_requests add column total_amount numeric(14,2);

-- Two notification moments, both application-layer jobs (same as
-- reorder_alerts, 0004) — the DB only tracks the state that triggers
-- them, it doesn't send anything:
--   draft -> submitted:  if total_amount > 25,000, notify the owner
--                        something needs their approval
--   submitted -> approved: notify MP the comparison is approved and
--                        a PO can now be raised

-- ============================================================
-- What a vendor is known to supply
-- ============================================================

-- Real need: finding "who sells cables and lugs" before any quote
-- history exists to compute it from. A manual tag, same pattern as
-- materials.aliases — not a substitute for real quote/purchase
-- history, just a starting point for a vendor nobody's bought from yet.

alter table partners add column supplies_categories text[];
