begin;

create table public.duck_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    status text not null default 'processing',
    transcript text,
    root_task_id uuid,
    failure_code text,
    finished_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint duck_sessions_user_id_id_key unique (user_id, id),
    constraint duck_sessions_root_task_same_user
        foreign key (user_id, root_task_id)
        references public.tasks (user_id, id)
        on delete set null (root_task_id),
    constraint duck_sessions_valid_status
        check (status in ('processing', 'completed', 'failed')),
    constraint duck_sessions_transcript_length
        check (
            transcript is null
            or char_length(transcript) between 1 and 100000
        ),
    constraint duck_sessions_failure_code_length
        check (
            failure_code is null
            or char_length(failure_code) between 1 and 100
        ),
    constraint duck_sessions_valid_result check (
        (
            status = 'processing'
            and root_task_id is null
            and failure_code is null
            and finished_at is null
        )
        or (
            status = 'completed'
            and transcript is not null
            and failure_code is null
            and finished_at is not null
        )
        or (
            status = 'failed'
            and root_task_id is null
            and failure_code is not null
            and finished_at is not null
        )
    )
);

create index duck_sessions_user_created_idx
on public.duck_sessions (user_id, created_at desc, id desc);

create index duck_sessions_root_task_idx
on public.duck_sessions (user_id, root_task_id)
where root_task_id is not null;

alter table public.duck_sessions enable row level security;

revoke all on public.duck_sessions from anon, authenticated;
grant select on public.duck_sessions to authenticated;
grant all on public.duck_sessions to service_role;

create policy "duck_sessions_select_own"
on public.duck_sessions
for select
to authenticated
using ((select auth.uid()) = user_id);

commit;
