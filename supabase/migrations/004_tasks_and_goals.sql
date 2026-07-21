begin;

create table public.goals (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    title text not null,
    description text,
    status text not null default 'active',
    target_date date,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint goals_user_id_id_key unique (user_id, id),
    constraint goals_title_not_blank check (char_length(btrim(title)) between 1 and 500),
    constraint goals_description_length
        check (description is null or char_length(description) <= 10000),
    constraint goals_valid_status check (status in ('active', 'completed', 'archived'))
);

create table public.tasks (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    parent_task_id uuid,
    title text not null,
    description text,
    category text not null default 'work',
    status text not null default 'pending',
    estimated_minutes integer,
    initial_easiness_score smallint,
    easiness_source text,
    scheduled_date date,
    due_at timestamptz,
    position integer not null default 0,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint tasks_user_id_id_key unique (user_id, id),
    constraint tasks_parent_same_user
        foreign key (user_id, parent_task_id)
        references public.tasks (user_id, id)
        on delete cascade,
    constraint tasks_not_own_parent check (parent_task_id is null or parent_task_id <> id),
    constraint tasks_title_not_blank check (char_length(btrim(title)) between 1 and 500),
    constraint tasks_description_length
        check (description is null or char_length(description) <= 10000),
    constraint tasks_valid_category check (category in ('work', 'chore', 'personal')),
    constraint tasks_valid_status
        check (status in ('pending', 'in_progress', 'completed', 'archived')),
    constraint tasks_valid_estimate
        check (estimated_minutes is null or estimated_minutes > 0),
    constraint tasks_valid_easiness
        check (initial_easiness_score is null or initial_easiness_score between 1 and 5),
    constraint tasks_valid_easiness_source
        check (easiness_source is null or easiness_source in ('user', 'inferred')),
    constraint tasks_easiness_pair check (
        (initial_easiness_score is null and easiness_source is null)
        or (initial_easiness_score is not null and easiness_source is not null)
    ),
    constraint tasks_valid_position check (position >= 0)
);

create table public.task_goals (
    user_id uuid not null references public.users(id) on delete cascade,
    task_id uuid not null,
    goal_id uuid not null,
    created_at timestamptz not null default now(),
    primary key (task_id, goal_id),
    constraint task_goals_task_same_user
        foreign key (user_id, task_id)
        references public.tasks (user_id, id)
        on delete cascade,
    constraint task_goals_goal_same_user
        foreign key (user_id, goal_id)
        references public.goals (user_id, id)
        on delete cascade
);

create index tasks_user_status_schedule_idx
on public.tasks (user_id, status, scheduled_date, position, id);

create index tasks_user_parent_position_idx
on public.tasks (user_id, parent_task_id, position, id);

create index goals_user_status_created_idx
on public.goals (user_id, status, created_at, id);

create index task_goals_user_goal_idx
on public.task_goals (user_id, goal_id, task_id);

alter table public.goals enable row level security;
alter table public.tasks enable row level security;
alter table public.task_goals enable row level security;

revoke all on public.goals, public.tasks, public.task_goals from anon, authenticated;
grant select on public.goals, public.tasks, public.task_goals to authenticated;
grant all on public.goals, public.tasks, public.task_goals to service_role;

create policy "goals_select_own"
on public.goals
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "tasks_select_own"
on public.tasks
for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "task_goals_select_own"
on public.task_goals
for select
to authenticated
using ((select auth.uid()) = user_id);

commit;
