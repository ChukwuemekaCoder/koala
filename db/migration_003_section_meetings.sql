-- Splits meeting times out of `sections` into their own child table.
--
-- Real data surfaced the gap: a single section can meet with genuinely
-- different day/time patterns in the same term — e.g. CSC 255 Data
-- Structures, Fall 2026, section 01: MWF 8:40-9:35 AM AND separately
-- Tuesday 10:40-11:55 AM, both under one section. The old
-- days/start_time/end_time columns on `sections` could only hold one
-- pattern, meaning the second meeting would be silently dropped —
-- a real threat to conflict-detection correctness, the actual thing
-- this project demonstrates.

create table section_meetings (
    id uuid primary key default gen_random_uuid(),
    section_id uuid not null references sections(id) on delete cascade,
    days text not null,                     -- e.g. 'MWF', 'T'
    start_time time not null,
    end_time time not null,
    constraint valid_time_range check (end_time > start_time)
);

create index idx_section_meetings_section on section_meetings(section_id);

-- Migrate any existing single-meeting data before dropping the old
-- columns (safe no-op on a fresh/empty database).
insert into section_meetings (section_id, days, start_time, end_time)
select id, days, start_time, end_time
from sections
where days is not null;

alter table sections
    drop column days,
    drop column start_time,
    drop column end_time;
