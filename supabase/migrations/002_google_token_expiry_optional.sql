begin;

-- Supabase Auth does not expose the Google access token's expiry separately
-- from the Supabase session expiry, so unknown provider expiry remains null.
alter table public.google_credentials
alter column access_token_expires_at drop not null;

commit;
