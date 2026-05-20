create table if not exists public.user_profiles (
    user_id text primary key,
    profile jsonb not null default '{"wins": 0, "losses": 0, "bias": 0, "setups": {}}'::jsonb,
    updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists set_user_profiles_updated_at on public.user_profiles;

create trigger set_user_profiles_updated_at
before update on public.user_profiles
for each row
execute function public.set_updated_at();
