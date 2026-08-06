-- "Before User Created" Auth Hook — restricts signups to @oru.edu.
-- This is the server-side gate; the frontend's client-side check is UX only
-- (see CLAUDE.md's "Auth: restrict signups to ORU email" section).
--
-- Applying this function does NOT enable the hook by itself — Supabase Auth
-- Hooks are registered per-project via the Dashboard (Postgres function
-- hooks have no SQL-level registration API):
--   Authentication -> Hooks -> "Before user created" -> select
--   public.restrict_signup_to_oru_email -> Enable.

create or replace function public.restrict_signup_to_oru_email(event jsonb)
returns jsonb
language plpgsql
as $$
declare
  user_email text;
begin
  user_email := event->'user'->>'email';

  if user_email is null or user_email !~* '^[^@\s]+@oru\.edu$' then
    return jsonb_build_object(
      'error', jsonb_build_object(
        'http_code', 400,
        'message', 'Please use your ORU email (@oru.edu) to sign up.'
      )
    );
  end if;

  return '{}'::jsonb;
end;
$$;

grant execute
  on function public.restrict_signup_to_oru_email
  to supabase_auth_admin;

revoke execute
  on function public.restrict_signup_to_oru_email
  from authenticated, anon, public;
