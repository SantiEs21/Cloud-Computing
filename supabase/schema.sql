-- Dashcam Video Integrity — paste this whole file in Supabase → SQL Editor → Run.
-- Safe to run more than once.

-- No foreign keys on purpose: the encoder's offline queue may deliver fingerprints before their
-- trip row, and the order must not matter.
create table if not exists trips (
  id          uuid primary key,
  driver_id   text not null,
  started_at  timestamptz not null,
  created_at  timestamptz not null default now()
);

create table if not exists segments (
  trip_id     uuid not null,
  seq         int  not null,
  t_start_ms  int  not null,
  duration_ms int  not null,
  sha256      text not null,
  size_bytes  int  not null,
  created_at  timestamptz not null default now(),
  primary key (trip_id, seq)          -- re-sending a segment is ignored (idempotent upsert)
);

create table if not exists fingerprints (
  trip_id     uuid not null,
  sample_idx  int  not null,
  t_ms        int  not null,
  phash       text not null,
  dhash       text not null,
  created_at  timestamptz not null default now(),
  primary key (trip_id, sample_idx)   -- re-sending a sample is ignored (idempotent upsert)
);

-- Append-only record: the public (anon/publishable) key may only insert and read.
-- No update/delete policy => those are rejected. Deleting expired data goes through purge_expired().
alter table trips        enable row level security;
alter table segments     enable row level security;
alter table fingerprints enable row level security;

revoke update, delete, truncate on trips, segments, fingerprints from anon, authenticated;
grant select, insert on trips, segments, fingerprints to anon, authenticated;

drop policy if exists "insert" on trips;
drop policy if exists "select" on trips;
drop policy if exists "insert" on segments;
drop policy if exists "select" on segments;
drop policy if exists "insert" on fingerprints;
drop policy if exists "select" on fingerprints;
create policy "insert" on trips        for insert to anon, authenticated with check (true);
create policy "select" on trips        for select to anon, authenticated using (true);
create policy "insert" on segments     for insert to anon, authenticated with check (true);
create policy "select" on segments     for select to anon, authenticated using (true);
create policy "insert" on fingerprints for insert to anon, authenticated with check (true);
create policy "select" on fingerprints for select to anon, authenticated using (true);

-- Deletes rows older than N hours. "security definer" runs it with the owner's rights, so it is the
-- ONLY way the public key can delete anything. Minimum 1 hour, so a caller cannot wipe fresh data.
create or replace function purge_expired(hours int)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  cutoff timestamptz := now() - greatest(hours, 1) * interval '1 hour';
  n_fp int; n_seg int; n_trip int;
begin
  delete from fingerprints where created_at < cutoff; get diagnostics n_fp = row_count;
  delete from segments     where created_at < cutoff; get diagnostics n_seg = row_count;
  delete from trips        where created_at < cutoff; get diagnostics n_trip = row_count;
  return json_build_object('fingerprints', n_fp, 'segments', n_seg, 'trips', n_trip);
end;
$$;

revoke all on function purge_expired(int) from public;
grant execute on function purge_expired(int) to anon, authenticated;

-- Optional automatic purge every 10 minutes (keeps 24 h):
--   1. Dashboard → Database → Extensions → enable "pg_cron"
--   2. Run:
-- select cron.schedule('purge-expired', '*/10 * * * *', $$select purge_expired(24)$$);
