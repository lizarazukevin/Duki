begin;

create or replace function public.complete_task(
    p_user_id uuid,
    p_task_id uuid,
    p_event_id uuid,
    p_actual_minutes integer,
    p_actual_easiness_score smallint,
    p_estimated_minutes_snapshot integer,
    p_initial_easiness_score_snapshot smallint,
    p_completed_at timestamptz
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
    target_task public.tasks%rowtype;
begin
    select *
    into target_task
    from public.tasks
    where user_id = p_user_id
      and id = p_task_id
    for update;

    if not found then
        raise sqlstate 'PT404' using message = 'task_not_found';
    end if;

    if target_task.status not in ('pending', 'in_progress') then
        raise sqlstate 'PT409' using message = 'task_not_completable';
    end if;

    if target_task.estimated_minutes is distinct from p_estimated_minutes_snapshot
       or target_task.initial_easiness_score is distinct from p_initial_easiness_score_snapshot
    then
        raise sqlstate 'PT409' using message = 'task_feedback_snapshot_stale';
    end if;

    update public.tasks
    set status = 'completed',
        completed_at = p_completed_at,
        updated_at = p_completed_at
    where user_id = p_user_id
      and id = p_task_id;

    insert into public.task_events (
        id,
        user_id,
        task_id,
        event_type,
        actual_minutes,
        actual_easiness_score,
        estimated_minutes_snapshot,
        initial_easiness_score_snapshot,
        estimate_delta_minutes,
        easiness_delta,
        occurred_at
    )
    values (
        p_event_id,
        p_user_id,
        p_task_id,
        'completed',
        p_actual_minutes,
        p_actual_easiness_score,
        target_task.estimated_minutes,
        target_task.initial_easiness_score,
        case
            when target_task.estimated_minutes is null then null
            else p_actual_minutes - target_task.estimated_minutes
        end,
        case
            when target_task.initial_easiness_score is null then null
            else p_actual_easiness_score - target_task.initial_easiness_score
        end,
        p_completed_at
    );
end;
$$;

revoke all on function public.complete_task(
    uuid,
    uuid,
    uuid,
    integer,
    smallint,
    integer,
    smallint,
    timestamptz
) from public, anon, authenticated;

grant execute on function public.complete_task(
    uuid,
    uuid,
    uuid,
    integer,
    smallint,
    integer,
    smallint,
    timestamptz
) to service_role;

commit;
