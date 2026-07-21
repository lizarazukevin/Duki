begin;

create table public.calendar_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    provider_event_id text not null,
    provider_calendar_id text not null,
    title text not null,
    description text,
    location text,
    start_time timestamptz not null,
    end_time timestamptz not null,
    is_all_day boolean not null default false,
    status text not null,
    transparency text not null,
    provider_updated_at timestamptz not null,
    synced_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint calendar_events_provider_key
        unique (user_id, provider_calendar_id, provider_event_id),
    constraint calendar_events_valid_time check (end_time > start_time),
    constraint calendar_events_valid_status
        check (status in ('confirmed', 'tentative', 'cancelled')),
    constraint calendar_events_valid_transparency
        check (transparency in ('opaque', 'transparent'))
);

create index calendar_events_user_time_idx
on public.calendar_events (user_id, start_time, end_time);

alter table public.calendar_events enable row level security;

revoke all on public.calendar_events from anon, authenticated;
grant select on public.calendar_events to authenticated;
grant all on public.calendar_events to service_role;

create policy "calendar_events_select_own"
on public.calendar_events
for select
to authenticated
using ((select auth.uid()) = user_id);

commit;
