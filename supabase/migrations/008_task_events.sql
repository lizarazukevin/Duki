begin;

create table public.task_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    task_id uuid not null,
    event_type text not null,
    actual_minutes integer not null,
    actual_easiness_score smallint not null,
    estimated_minutes_snapshot integer,
    initial_easiness_score_snapshot smallint,
    estimate_delta_minutes integer,
    easiness_delta integer,
    occurred_at timestamptz not null default now(),
    constraint task_events_task_same_user
        foreign key (user_id, task_id)
        references public.tasks (user_id, id)
        on delete cascade,
    constraint task_events_valid_type check (event_type = 'completed'),
    constraint task_events_valid_actual_minutes check (actual_minutes > 0),
    constraint task_events_valid_actual_easiness
        check (actual_easiness_score between 1 and 5),
    constraint task_events_valid_estimate_snapshot
        check (estimated_minutes_snapshot is null or estimated_minutes_snapshot > 0),
    constraint task_events_valid_easiness_snapshot
        check (
            initial_easiness_score_snapshot is null
            or initial_easiness_score_snapshot between 1 and 5
        ),
    constraint task_events_consistent_estimate_delta check (
        (estimated_minutes_snapshot is null and estimate_delta_minutes is null)
        or (
            estimated_minutes_snapshot is not null
            and estimate_delta_minutes = actual_minutes - estimated_minutes_snapshot
        )
    ),
    constraint task_events_consistent_easiness_delta check (
        (initial_easiness_score_snapshot is null and easiness_delta is null)
        or (
            initial_easiness_score_snapshot is not null
            and easiness_delta = actual_easiness_score - initial_easiness_score_snapshot
        )
    )
);

create index task_events_user_task_time_idx
on public.task_events (user_id, task_id, occurred_at desc, id desc);

alter table public.task_events enable row level security;

revoke all on public.task_events from anon, authenticated;
grant select on public.task_events to authenticated;
grant select, insert on public.task_events to service_role;

create policy "task_events_select_own"
on public.task_events
for select
to authenticated
using ((select auth.uid()) = user_id);

commit;
