-- Row Level Security policies for the ORU Scheduling Engine.
-- Run after schema.sql. Assumes Supabase Auth (auth.uid() available).

-- === Student-owned tables ===
-- A student can only read/write their own rows.

alter table students enable row level security;
create policy "students manage own row" on students
    for all
    using (auth.uid() = id)
    with check (auth.uid() = id);

alter table student_programs enable row level security;
create policy "students manage own programs" on student_programs
    for all
    using (auth.uid() = student_id)
    with check (auth.uid() = student_id);

alter table student_progress enable row level security;
create policy "students manage own progress" on student_progress
    for all
    using (auth.uid() = student_id)
    with check (auth.uid() = student_id);

alter table semester_plans enable row level security;
create policy "students manage own plans" on semester_plans
    for all
    using (auth.uid() = student_id)
    with check (auth.uid() = student_id);

-- === Catalog tables ===
-- Read-only for authenticated students. Writes restricted to the
-- service role (admin/seed scripts), never exposed to student sessions.

alter table programs enable row level security;
create policy "catalog readable by authenticated" on programs
    for select
    using (auth.role() = 'authenticated');
create policy "catalog writable by service role" on programs
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

alter table courses enable row level security;
create policy "catalog readable by authenticated" on courses
    for select
    using (auth.role() = 'authenticated');
create policy "catalog writable by service role" on courses
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

alter table prerequisites enable row level security;
create policy "catalog readable by authenticated" on prerequisites
    for select
    using (auth.role() = 'authenticated');
create policy "catalog writable by service role" on prerequisites
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

alter table degree_requirements enable row level security;
create policy "catalog readable by authenticated" on degree_requirements
    for select
    using (auth.role() = 'authenticated');
create policy "catalog writable by service role" on degree_requirements
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

alter table sections enable row level security;
create policy "catalog readable by authenticated" on sections
    for select
    using (auth.role() = 'authenticated');
create policy "catalog writable by service role" on sections
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

alter table section_meetings enable row level security;
create policy "catalog readable by authenticated" on section_meetings
    for select
    using (auth.role() = 'authenticated');
create policy "catalog writable by service role" on section_meetings
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');
