-- NRG SolarConnect — AMC rate card seed
-- Follows 0037-0052.
--
-- Source: Amc.gs's seedAmcRates() (received in full from the owner,
-- condensed in the working scratchpad copy but this function's real
-- numbers were preserved verbatim per that file's own header). The live
-- system keys rates by 7 DISCRETE kW points (10/25/50/100/250/500/1000),
-- not a continuous range — there is no confirmed real range-boundary
-- convention anywhere in the source (unlike quote_kw_band_rates' or
-- bill_analysis_rate_bands' real tiered bands, which came with actual
-- boundary values). Rather than invent boundaries migration 0037's
-- amc_rates(kw_min, kw_max) columns don't have a real source for, each
-- real point is seeded as a narrow band (value ± 0.01) — a discrete-match
-- lookup in range-column clothing, not an asserted "10-24.99kW" business
-- rule. The application queries this as "nearest/matching discrete kW
-- tier", exactly matching the live system's own dropdown-of-7-values
-- behaviour, never a continuous kW input.
--
-- Service MONTHLY_12V and Cleaning CLEAN_2M_* rates are themselves
-- flagged in the source's own alert as "calculated estimates, adjust as
-- needed" (3x/1.85x/1.80x/3.50x multipliers off the base rates) — kept
-- exactly as the live system currently has them seeded, since that's
-- what's actually live today, not because the multipliers are confirmed
-- correct. Worth the owner reviewing in the Rates screen once real AMC
-- volume starts.

insert into amc_rates (organization_id, amc_type, frequency, kw_min, kw_max, base_amount)
select '00000000-0000-0000-0000-000000000001', v.amc_type, v.frequency, v.kw - 0.01, v.kw + 0.01, v.base_amount
from (values
  -- Service · QUARTERLY_4V
  ('service', 'quarterly_4v', 10,   4200),
  ('service', 'quarterly_4v', 25,   5600),
  ('service', 'quarterly_4v', 50,   8400),
  ('service', 'quarterly_4v', 100, 12600),
  ('service', 'quarterly_4v', 250, 16800),
  ('service', 'quarterly_4v', 500, 19600),
  ('service', 'quarterly_4v', 1000, 22400),
  -- Service · MONTHLY_12V (= 3x quarterly per the live seed — owner flagged as estimate)
  ('service', 'monthly_12v', 10,   10500),
  ('service', 'monthly_12v', 25,   14000),
  ('service', 'monthly_12v', 50,   21000),
  ('service', 'monthly_12v', 100,  31500),
  ('service', 'monthly_12v', 250,  42000),
  ('service', 'monthly_12v', 500,  49000),
  ('service', 'monthly_12v', 1000, 56000),
  -- Cleaning · CLEAN_1M_1Y (base rate card)
  ('cleaning', 'clean_1m_1y', 10,    10300),
  ('cleaning', 'clean_1m_1y', 25,    25350),
  ('cleaning', 'clean_1m_1y', 50,    50700),
  ('cleaning', 'clean_1m_1y', 100,  100600),
  ('cleaning', 'clean_1m_1y', 250,  251850),
  ('cleaning', 'clean_1m_1y', 500,  503700),
  ('cleaning', 'clean_1m_1y', 1000, 1008200),
  -- Cleaning · CLEAN_2M_1Y (= CLEAN_1M_1Y x 1.85, rounded, per the live seed)
  ('cleaning', 'clean_2m_1y', 10,    19055),
  ('cleaning', 'clean_2m_1y', 25,    46898),
  ('cleaning', 'clean_2m_1y', 50,    93795),
  ('cleaning', 'clean_2m_1y', 100,  186110),
  ('cleaning', 'clean_2m_1y', 250,  465923),
  ('cleaning', 'clean_2m_1y', 500,  931845),
  ('cleaning', 'clean_2m_1y', 1000, 1865170),
  -- Cleaning · CLEAN_1M_2Y (= CLEAN_1M_1Y x 1.80, rounded, per the live seed)
  ('cleaning', 'clean_1m_2y', 10,    18540),
  ('cleaning', 'clean_1m_2y', 25,    45630),
  ('cleaning', 'clean_1m_2y', 50,    91260),
  ('cleaning', 'clean_1m_2y', 100,  181080),
  ('cleaning', 'clean_1m_2y', 250,  453330),
  ('cleaning', 'clean_1m_2y', 500,  906660),
  ('cleaning', 'clean_1m_2y', 1000, 1814760),
  -- Cleaning · CLEAN_2M_2Y (= CLEAN_1M_1Y x 3.50, rounded, per the live seed)
  ('cleaning', 'clean_2m_2y', 10,    36050),
  ('cleaning', 'clean_2m_2y', 25,    88725),
  ('cleaning', 'clean_2m_2y', 50,    177450),
  ('cleaning', 'clean_2m_2y', 100,  352100),
  ('cleaning', 'clean_2m_2y', 250,  881475),
  ('cleaning', 'clean_2m_2y', 500,  1762950),
  ('cleaning', 'clean_2m_2y', 1000, 3528700)
) as v(amc_type, frequency, kw, base_amount)
where not exists (
  select 1 from amc_rates r
  where r.organization_id = '00000000-0000-0000-0000-000000000001'
    and r.amc_type = v.amc_type and r.frequency = v.frequency and r.kw_min = v.kw - 0.01
);
