-- 1) Supprimer l’ancienne
drop function if exists public.weekly_summary_for_me();

-- 2) Recréer : agrégats hebdo + toutes les lignes brutes (toutes colonnes) en JSON
create function public.weekly_summary_for_me()
returns table (
  iso_year                    int,
  week_no                     int,
  week_key                    text,

  -- Agrégats "classiques"
  run_km                      numeric,
  run_dplus_m                 numeric,
  run_time_s                  numeric,
  allure_avg_min_km           numeric,
  vap_avg_min_km              numeric,
  average_speed               numeric,  -- (min/km) depuis la DB, pondéré par la distance
  average_grade_adjusted_pace numeric,  -- (min/km) depuis la DB, pondéré par la distance
  fc_avg_simple               numeric,
  fc_max_week                 int,
  calories_total              numeric,
  steps_total                 numeric,
  relative_effort_avg         numeric,

  -- Compteur d'activités dans la semaine
  activities_count            int,

  -- NOUVEAU : toutes les lignes brutes Strava de la semaine (toutes colonnes) 
  -- sous forme d'un array JSON (chaque élément = 1 activité, to_jsonb(strava_import))
  rows                        jsonb
)
language sql
stable
security definer
as $$
  with base as (
    select
      si.*,
      extract(isoyear from si.activity_date)::int as iso_year,
      extract(week    from si.activity_date)::int as week_no
    from public.strava_import si
    where si.user_id = auth.uid()
      and si.activity_date is not null
      and si.activity_type = 'Run'
  ),
  g as (
    select
      iso_year,
      week_no,

      -- Agrégats
      sum(distance)                                as run_km,
      sum(elevation_gain)                          as run_dplus_m,
      sum(coalesce(moving_time, elapsed_time))::numeric as run_time_s,

      -- Tes anciens calculs "déduits" (cohérents si distance/grade_adjusted_distance bien renseignées)
      (sum(coalesce(moving_time, elapsed_time)) / 60.0) / nullif(sum(distance), 0)                as allure_avg_min_km,
      (sum(coalesce(moving_time, elapsed_time)) / 60.0) / nullif(sum(grade_adjusted_distance), 0) as vap_avg_min_km,

      -- Agrégats "direct DB" (déjà en min/km) pondérés par la distance
      case when sum(distance) > 0 then sum(average_speed * distance) / sum(distance) end               as average_speed,
      case when sum(distance) > 0 then sum(average_grade_adjusted_pace * distance) / sum(distance) end as average_grade_adjusted_pace,

      avg(average_heart_rate)::numeric             as fc_avg_simple,
      max(coalesce(max_heart_rate, max_heart_rate_1))::int as fc_max_week,
      sum(calories)                                as calories_total,
      sum(total_steps)                             as steps_total,
      avg(coalesce(perceived_relative_effort, relative_effort, relative_effort_1))::numeric as relative_effort_avg,

      count(*)                                      as activities_count,

      -- Toutes les lignes (toutes colonnes) de la semaine, brutes
      jsonb_agg(to_jsonb(b) order by b.activity_date) as rows
    from base b
    group by iso_year, week_no
  )
  select
    g.iso_year,
    g.week_no,
    (g.iso_year::text || '-W' || lpad(g.week_no::text, 2, '0')) as week_key,

    g.run_km,
    g.run_dplus_m,
    g.run_time_s,
    g.allure_avg_min_km,
    g.vap_avg_min_km,
    g.average_speed,
    g.average_grade_adjusted_pace,
    g.fc_avg_simple,
    g.fc_max_week,
    g.calories_total,
    g.steps_total,
    g.relative_effort_avg,

    g.activities_count,
    g.rows
  from g
  order by iso_year, week_no;
$$;
