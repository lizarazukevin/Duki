begin;

alter table public.duck_sessions
add column confirmed_resolutions jsonb not null default '[]'::jsonb,
add column confirmed_at timestamptz,
add constraint duck_sessions_confirmed_resolutions_array
    check (jsonb_typeof(confirmed_resolutions) = 'array'),
add constraint duck_sessions_confirmed_resolutions_limit
    check (jsonb_array_length(confirmed_resolutions) <= 100),
add constraint duck_sessions_confirmation_consistency check (
    (confirmed_at is null and jsonb_array_length(confirmed_resolutions) = 0)
    or (confirmed_at is not null and jsonb_array_length(confirmed_resolutions) > 0)
);

create function public.confirm_duck_session(
    p_user_id uuid,
    p_session_id uuid,
    p_confirmed_at timestamptz,
    p_decisions jsonb
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
declare
    target_session public.duck_sessions%rowtype;
begin
    select *
    into target_session
    from public.duck_sessions
    where id = p_session_id
      and user_id = p_user_id
    for update;

    if not found then
        raise sqlstate 'PT404' using message = 'duck_session_not_found';
    end if;

    if target_session.status <> 'completed'
       or target_session.confirmed_at is not null
       or jsonb_array_length(target_session.resolution_suggestions) = 0
    then
        raise sqlstate 'PT409' using message = 'duck_session_not_confirmable';
    end if;

    if p_confirmed_at is null
       or p_confirmed_at < target_session.finished_at
       or coalesce(jsonb_typeof(p_decisions), 'null') <> 'array'
       or jsonb_array_length(p_decisions) = 0
       or jsonb_array_length(p_decisions) > 100
       or jsonb_array_length(p_decisions)
          <> jsonb_array_length(target_session.resolution_suggestions)
    then
        raise exception 'Duck confirmation is invalid'
            using errcode = '22023';
    end if;

    perform task.id
    from public.tasks task
    join jsonb_to_recordset(p_decisions) as decision(task_id uuid)
      on decision.task_id = task.id
    where task.user_id = p_user_id
    order by task.id
    for update of task;

    if exists (
        select 1
        from jsonb_to_recordset(p_decisions) as decision(
            task_id uuid,
            action text,
            actual_minutes integer,
            actual_easiness_score smallint
        )
        where decision.task_id is null
           or decision.action is null
           or decision.action not in ('complete', 'keep_open', 'archive')
           or (
               decision.action = 'complete'
               and (
                   decision.actual_minutes is null
                   or decision.actual_minutes <= 0
                   or decision.actual_easiness_score is null
                   or decision.actual_easiness_score not between 1 and 5
               )
           )
           or (
               decision.action <> 'complete'
               and (
                   decision.actual_minutes is not null
                   or decision.actual_easiness_score is not null
               )
           )
           or not exists (
               select 1
               from public.tasks
               where id = decision.task_id
                 and user_id = p_user_id
                 and status in ('pending', 'in_progress')
           )
           or not exists (
               select 1
               from jsonb_array_elements(target_session.resolution_suggestions) suggestion
               where (suggestion->>'task_id')::uuid = decision.task_id
           )
    ) or exists (
        select decision.task_id
        from jsonb_to_recordset(p_decisions) as decision(task_id uuid)
        group by decision.task_id
        having count(*) > 1
    ) or exists (
        select 1
        from jsonb_array_elements(target_session.resolution_suggestions) suggestion
        where not exists (
            select 1
            from jsonb_to_recordset(p_decisions) as decision(task_id uuid)
            where decision.task_id = (suggestion->>'task_id')::uuid
        )
    ) then
        raise sqlstate 'PT409' using message = 'duck_resolution_conflict';
    end if;

    insert into public.task_events (
        id, user_id, task_id, event_type, actual_minutes,
        actual_easiness_score, estimated_minutes_snapshot,
        initial_easiness_score_snapshot, estimate_delta_minutes,
        easiness_delta, occurred_at
    )
    select
        gen_random_uuid(), p_user_id, task.id, 'completed',
        decision.actual_minutes, decision.actual_easiness_score,
        task.estimated_minutes, task.initial_easiness_score,
        case when task.estimated_minutes is null then null
             else decision.actual_minutes - task.estimated_minutes end,
        case when task.initial_easiness_score is null then null
             else decision.actual_easiness_score - task.initial_easiness_score end,
        p_confirmed_at
    from jsonb_to_recordset(p_decisions) as decision(
        task_id uuid,
        action text,
        actual_minutes integer,
        actual_easiness_score smallint
    )
    join public.tasks task on task.id = decision.task_id
    where decision.action = 'complete';

    update public.tasks task
    set status = case decision.action
            when 'complete' then 'completed'
            else 'archived'
        end,
        completed_at = case
            when decision.action = 'complete' then p_confirmed_at
            else null
        end,
        updated_at = p_confirmed_at
    from jsonb_to_recordset(p_decisions) as decision(task_id uuid, action text)
    where task.id = decision.task_id
      and task.user_id = p_user_id
      and decision.action in ('complete', 'archive');

    update public.duck_sessions
    set confirmed_resolutions = p_decisions,
        confirmed_at = p_confirmed_at,
        updated_at = p_confirmed_at
    where id = p_session_id
      and user_id = p_user_id;
end;
$$;

revoke all on function public.confirm_duck_session(
    uuid, uuid, timestamptz, jsonb
) from public, anon, authenticated;

grant execute on function public.confirm_duck_session(
    uuid, uuid, timestamptz, jsonb
) to service_role;

commit;
