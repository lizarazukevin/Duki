begin;

create table public.daily_debriefs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    debrief_date date not null,
    morning_mood_score_snapshot numeric(4, 3) not null,
    evening_mood_score smallint not null,
    mood_delta numeric(5, 3) not null,
    completed_task_count integer not null,
    carried_forward_task_count integer not null,
    archived_task_count integer not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint daily_debriefs_user_date_key unique (user_id, debrief_date),
    constraint daily_debriefs_morning_mood_range
        check (morning_mood_score_snapshot between 1 and 5),
    constraint daily_debriefs_evening_mood_range
        check (evening_mood_score between 1 and 5),
    constraint daily_debriefs_consistent_mood_delta
        check (mood_delta = evening_mood_score - morning_mood_score_snapshot),
    constraint daily_debriefs_nonnegative_counts check (
        completed_task_count >= 0
        and carried_forward_task_count >= 0
        and archived_task_count >= 0
    )
);

alter table public.daily_debriefs enable row level security;

revoke all on public.daily_debriefs from anon, authenticated;
grant select on public.daily_debriefs to authenticated;
grant all on public.daily_debriefs to service_role;

create policy "daily_debriefs_select_own"
on public.daily_debriefs
for select
to authenticated
using ((select auth.uid()) = user_id);

commit;
