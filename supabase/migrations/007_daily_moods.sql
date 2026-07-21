begin;

create table public.daily_moods (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    mood_date date not null,
    reported_mood_score smallint not null,
    calendar_load_score numeric(4, 3) not null,
    computed_mood_score numeric(4, 3) not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint daily_moods_user_date_key unique (user_id, mood_date),
    constraint daily_moods_reported_score_range
        check (reported_mood_score between 1 and 5),
    constraint daily_moods_calendar_load_range
        check (calendar_load_score between 0 and 1),
    constraint daily_moods_computed_score_range
        check (computed_mood_score between 1 and 5)
);

alter table public.daily_moods enable row level security;

revoke all on public.daily_moods from anon, authenticated;
grant select on public.daily_moods to authenticated;
grant all on public.daily_moods to service_role;

create policy "daily_moods_select_own"
on public.daily_moods
for select
to authenticated
using ((select auth.uid()) = user_id);

commit;
