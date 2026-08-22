-- NRG SolarConnect — Test Data Teardown
--
-- Removes exactly the trial dataset seeded on 2026-08-22 for you to click
-- through Projects/BOM/Milestones/Finance/Stock before the real Google
-- Sheets migration. Every row below carries the "TEST — " name prefix or a
-- 'TEST-SEED-' document marker, and every ID is one of the fixed UUIDs used
-- when seeding (aaaaaaaa-000N-4000-8000-...) — nothing here can match a
-- real record. Real data (the 3 existing Capiq Engineering projects, real
-- employees/materials) is untouched.
--
-- Run this in the Supabase SQL editor, or ask Claude to run it via the
-- Supabase MCP connector, once you're done trialing and ready to load the
-- real migrated data. Deletes children before parents (FK order).

delete from material_transactions where source_document_id = 'aaaaaaaa-0003-4000-8000-000000000005';
delete from payment_receipts where payment_receipt_id in ('aaaaaaaa-0007-4000-8000-000000000001','aaaaaaaa-0007-4000-8000-000000000002');
delete from financial_obligations where financial_obligation_id in ('aaaaaaaa-0006-4000-8000-000000000001','aaaaaaaa-0006-4000-8000-000000000002','aaaaaaaa-0006-4000-8000-000000000003');
delete from project_milestones where project_id in (
  'aaaaaaaa-0002-4000-8000-000000000001','aaaaaaaa-0002-4000-8000-000000000002','aaaaaaaa-0002-4000-8000-000000000003',
  'aaaaaaaa-0002-4000-8000-000000000004','aaaaaaaa-0002-4000-8000-000000000005'
);
delete from bom_items where bom_id in (
  'aaaaaaaa-0004-4000-8000-000000000001','aaaaaaaa-0004-4000-8000-000000000002',
  'aaaaaaaa-0004-4000-8000-000000000003','aaaaaaaa-0004-4000-8000-000000000004'
);
delete from boms where bom_id in (
  'aaaaaaaa-0004-4000-8000-000000000001','aaaaaaaa-0004-4000-8000-000000000002',
  'aaaaaaaa-0004-4000-8000-000000000003','aaaaaaaa-0004-4000-8000-000000000004'
);
delete from documents where document_id in (
  'aaaaaaaa-0003-4000-8000-000000000001','aaaaaaaa-0003-4000-8000-000000000002','aaaaaaaa-0003-4000-8000-000000000003',
  'aaaaaaaa-0003-4000-8000-000000000004','aaaaaaaa-0003-4000-8000-000000000005'
);
delete from projects where project_id in (
  'aaaaaaaa-0002-4000-8000-000000000001','aaaaaaaa-0002-4000-8000-000000000002','aaaaaaaa-0002-4000-8000-000000000003',
  'aaaaaaaa-0002-4000-8000-000000000004','aaaaaaaa-0002-4000-8000-000000000005'
);
delete from partners where partner_id in (
  'aaaaaaaa-0005-4000-8000-000000000001','aaaaaaaa-0005-4000-8000-000000000002','aaaaaaaa-0005-4000-8000-000000000003'
);
delete from customers where customer_id in (
  'aaaaaaaa-0001-4000-8000-000000000001','aaaaaaaa-0001-4000-8000-000000000002','aaaaaaaa-0001-4000-8000-000000000003',
  'aaaaaaaa-0001-4000-8000-000000000004','aaaaaaaa-0001-4000-8000-000000000005'
);

-- Sanity check after running — should return 0 rows:
-- select count(*) from customers where name like 'TEST — %';
