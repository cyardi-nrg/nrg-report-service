-- ============================================================
-- Fix employee_task_performance grouping by assignee_id as well as
-- assignee_name — 0042's own comment directly above the view says
-- "grouped by assignee_name, not assignee_id, since a team label like
-- 'Office Team' has no employee row to group by," but the view's SQL
-- did `group by t.assignee_name, t.assignee_id` anyway. Any assignee
-- whose tasks were ever recorded under two different assignee_id
-- values for the same name (a team label matched to no employee some
-- of the time, or a name reused across two employee records) produced
-- two leaderboard rows with the same assignee_name — which the app's
-- own TasksBoard renders keyed by `assignee_name` alone
-- (app/(app)/tasks/tasks-board.tsx), so those rows collided as
-- duplicate React keys instead of merging into one real leaderboard
-- entry. Recreated grouped by assignee_name only, per the comment's own
-- stated intent; assignee_id is kept as an aggregate (max) purely for
-- any incidental display use, never as a grouping key.
-- ============================================================

drop view if exists employee_task_performance;

create view employee_task_performance as
select
  t.assignee_name,
  (array_agg(t.assignee_id) filter (where t.assignee_id is not null))[1] as assignee_id,
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
group by t.assignee_name;
