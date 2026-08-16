-- ProjectPulse — project_costs Can Auto-Suggest a Project Match
-- Follows 0002-0021. Consolidated from docs/projectpulse-handover.md
-- Section 57.

-- ============================================================
-- Real bill format confirms AI can suggest, not just capture
-- ============================================================

-- Confirmed real fabricator/electrician bill format: multiple line
-- items on one bill, each already naming its own project and amount —
-- e.g. "R B Pillai - 4KW - Rs. 12,000" / "Pranayam Hospital - 100KW -
-- Rs. 30,000" on the same invoice. This isn't the "bill doesn't
-- self-identify a project" case project_costs (0011) was first built
-- for — the project name is right there on each line. AI extraction can
-- fuzzy-match it (same customers.aliases matching used everywhere else,
-- Section 39) and suggest a project_id automatically; a human still
-- confirms, but from a suggestion, not a blank pick list.

-- project_costs.assignment_status never had a state for "AI matched
-- this, unconfirmed" — only unassigned/assigned/general, conflating
-- "nobody's looked at it" with "AI already has a good guess." Every
-- other AI-extracted table in this schema (payment_receipts,
-- tally_ledger_entries, bank_statement_transactions) already
-- distinguishes unmatched from suggested. Bringing project_costs in
-- line:

alter table project_costs drop constraint project_costs_assignment_status_check;
alter table project_costs add constraint project_costs_assignment_status_check
  check (assignment_status in ('unassigned','suggested','assigned','general'));

alter table project_costs add column ai_confidence numeric(3,2);

-- One physical bill with N line items, each naming a different project,
-- is still N project_costs rows sharing one source_document_id — that
-- part of the 0011 design was already right. What's new: each row can
-- land as 'suggested' with project_id already filled in by AI and
-- ai_confidence set, instead of every line starting 'unassigned' with
-- nothing but the vendor and total amount for MP to work from. MP
-- confirming a correct suggestion is a single tap (assignment_status ->
-- 'assigned'); correcting a wrong one is the same flow as ever.
