begin;

create or replace function public.complete_duck_session(
    p_session_id uuid,
    p_user_id uuid,
    p_transcript text,
    p_root_task_id uuid,
    p_finished_at timestamptz,
    p_tasks jsonb
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    perform 1
    from public.duck_sessions
    where id = p_session_id
      and user_id = p_user_id
      and status = 'processing'
    for update;

    if not found then
        raise exception 'Duck session is not available for completion'
            using errcode = 'P0002';
    end if;

    if coalesce(jsonb_typeof(p_tasks), 'null') <> 'array' then
        raise exception 'Generated task collection is invalid'
            using errcode = '22023';
    end if;

    if jsonb_array_length(p_tasks) not between 1 and 100 then
        raise exception 'Generated task collection is invalid'
            using errcode = '22023';
    end if;

    if not exists (
        select 1
        from jsonb_to_recordset(p_tasks) as task(id uuid, parent_task_id uuid)
        where task.id = p_root_task_id
          and task.parent_task_id is null
    ) then
        raise exception 'Generated root task is invalid'
            using errcode = '22023';
    end if;

    if exists (
        select 1
        from jsonb_to_recordset(p_tasks) as task(id uuid, parent_task_id uuid)
        where task.parent_task_id is not null
          and not exists (
              select 1
              from jsonb_to_recordset(p_tasks) as parent_task(id uuid)
              where parent_task.id = task.parent_task_id
          )
    ) then
        raise exception 'Generated task parent is invalid'
            using errcode = '22023';
    end if;

    insert into public.tasks (
        id,
        user_id,
        parent_task_id,
        title,
        description,
        category,
        estimated_minutes,
        initial_easiness_score,
        easiness_source,
        position,
        created_at,
        updated_at
    )
    select
        task.id,
        p_user_id,
        task.parent_task_id,
        task.title,
        task.description,
        task.category,
        task.estimated_minutes,
        task.initial_easiness_score,
        task.easiness_source,
        task.position,
        task.created_at,
        task.updated_at
    from jsonb_to_recordset(p_tasks) as task (
        id uuid,
        parent_task_id uuid,
        title text,
        description text,
        category text,
        estimated_minutes integer,
        initial_easiness_score smallint,
        easiness_source text,
        position integer,
        created_at timestamptz,
        updated_at timestamptz
    );

    update public.duck_sessions
    set status = 'completed',
        transcript = p_transcript,
        root_task_id = p_root_task_id,
        failure_code = null,
        finished_at = p_finished_at,
        updated_at = p_finished_at
    where id = p_session_id
      and user_id = p_user_id;
end;
$$;

revoke all on function public.complete_duck_session(
    uuid,
    uuid,
    text,
    uuid,
    timestamptz,
    jsonb
) from public, anon, authenticated;

grant execute on function public.complete_duck_session(
    uuid,
    uuid,
    text,
    uuid,
    timestamptz,
    jsonb
) to service_role;

commit;
