begin;

create table public.users (
    id uuid primary key references auth.users(id) on delete cascade,
    email text not null,
    display_name text,
    avatar_url text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.google_credentials (
    user_id uuid primary key references public.users(id) on delete cascade,
    encrypted_access_token text not null,
    encrypted_refresh_token text not null,
    access_token_expires_at timestamptz not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.users enable row level security;
alter table public.google_credentials enable row level security;

revoke all on public.users from anon, authenticated;
revoke all on public.google_credentials from anon, authenticated;
grant select on public.users to authenticated;
grant all on public.users, public.google_credentials to service_role;

create policy "users_select_own_profile"
on public.users
for select
to authenticated
using ((select auth.uid()) = id);

-- Provider tokens remain backend-only. No client RLS policy is intentionally
-- created for google_credentials; only the server's secret key may access it.

commit;
