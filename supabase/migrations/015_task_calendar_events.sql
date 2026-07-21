begin;

create table public.task_calendar_events (
    task_id uuid primary key references public.tasks(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete cascade,
    provider_event_id text not null,
    provider_calendar_id text not null,
    start_time timestamptz not null,
    end_time timestamptz not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint task_calendar_events_provider_key
        unique (user_id, provider_calendar_id, provider_event_id),
    constraint task_calendar_events_valid_time check (end_time > start_time)
);

create index task_calendar_events_user_idx
on public.task_calendar_events (user_id);

alter table public.task_calendar_events enable row level security;

revoke all on public.task_calendar_events from anon, authenticated;
grant select on public.task_calendar_events to authenticated;
grant all on public.task_calendar_events to service_role;

create policy "task_calendar_events_select_own"
on public.task_calendar_events
for select
to authenticated
using ((select auth.uid()) = user_id);

commit;
