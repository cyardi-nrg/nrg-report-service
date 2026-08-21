-- NRG SolarConnect — seed the real Service Desk engineer roster and
-- assignment rules. Both read directly from the owner-pasted
-- ServiceDesk_Code.gs (assignEngineer(), engineerPhone()) — real names,
-- real phone numbers, real complaint-type -> engineer/severity mapping,
-- not invented. Only the three field engineers (Dev, Ravindra, Narayan)
-- are seeded here — their phone numbers were given explicitly in the
-- source; other staff mentioned by first name only (Kinjal, Mahesh, ...)
-- are left for the real staff-data import, not guessed at.

insert into employees (organization_id, name, role, phone, active)
select '00000000-0000-0000-0000-000000000001', v.name, v.role, v.phone, true
from (values
  ('Dev', 'Service Engineer', '7574000799'),
  ('Ravindra', 'Service Engineer', '7574000399'),
  ('Narayan', 'Service Engineer', '7574000266')
) as v(name, role, phone)
where not exists (select 1 from employees e where e.name = v.name);

insert into service_assignment_rules (complaint_type, default_severity, primary_engineer_id, secondary_engineer_id)
select v.complaint_type, v.severity,
  (select employee_id from employees where name = v.primary_name),
  (select employee_id from employees where name = v.secondary_name)
from (values
  ('inverter_not_working',  'high',   'Dev',      null),
  ('low_generation',        'medium', 'Dev',      'Narayan'),
  ('wifi_monitoring',       'low',    'Ravindra', null),
  ('commissioning_small',   'medium', 'Ravindra', null),
  ('commissioning_large',   'high',   'Dev',      'Narayan'),
  ('follow_up',             'medium', 'Narayan',  null),
  ('physical_damage',       'high',   'Dev',      null),
  ('other',                 'low',    'Ravindra', null)
) as v(complaint_type, severity, primary_name, secondary_name)
where not exists (select 1 from service_assignment_rules r where r.complaint_type = v.complaint_type);
