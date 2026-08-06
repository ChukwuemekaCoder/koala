-- ORU Scheduling Engine — Postgres schema (Supabase)
-- students.id references auth.users(id) — Supabase Auth owns identity;
-- this table extends it with profile + academic fields.

create table students (
    id uuid primary key references auth.users(id) on delete cascade,
    email text not null unique,
    first_name text not null,
    last_name text not null,
    class_standing text check (class_standing in
        ('freshman', 'sophomore', 'junior', 'senior')),
    current_term text check (current_term in ('fall', 'spring')),
    target_grad_date date,
    has_completed_tutorial boolean not null default false,
    onboarding_completed_at timestamptz,
    created_at timestamptz not null default now()
);

-- Majors and minors. Self-referencing FK encodes "this minor is
-- structurally required by that major" (e.g. CS -> Math minor),
-- which is how the solver promotes it to major-tier priority.
create table programs (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    type text not null check (type in ('major', 'minor')),
    department text,
    required_by_program_id uuid references programs(id),
    constraint no_self_requirement check (id != required_by_program_id)
);

-- Join table: which programs a student has declared, and their
-- optional manual priority rank for same-tier ties (nullable —
-- v1 default is "equal, let bottleneck score decide").
create table student_programs (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students(id) on delete cascade,
    program_id uuid not null references programs(id),
    priority_rank int check (priority_rank > 0),
    declared_at timestamptz not null default now(),
    unique (student_id, program_id)
);

-- Course catalog. offering_frequency drives the bottleneck score.
create table courses (
    id uuid primary key default gen_random_uuid(),
    code text not null unique,              -- e.g. 'CS210'
    title text not null,
    credit_hours int not null check (credit_hours > 0 and credit_hours <= 6),
    offering_frequency text not null check (offering_frequency in
        ('every_semester', 'annual', 'biennial')),
    department text
);

-- Prerequisite edges — the dependency graph the solver walks for
-- "blast radius" detection on re-solve.
create table prerequisites (
    id uuid primary key default gen_random_uuid(),
    course_id uuid not null references courses(id) on delete cascade,
    prerequisite_course_id uuid not null references courses(id) on delete cascade,
    constraint no_self_prereq check (course_id != prerequisite_course_id),
    unique (course_id, prerequisite_course_id)
);

-- Which courses satisfy which requirement category within a program.
-- A course can appear multiple times here (once per program it
-- satisfies) without being "taken" more than once — see student_progress.
create table degree_requirements (
    id uuid primary key default gen_random_uuid(),
    program_id uuid not null references programs(id) on delete cascade,
    course_id uuid not null references courses(id),
    category text not null check (category in
        ('major_core', 'major_elective', 'minor', 'gen_ed', 'christian_coursework')),
    unique (program_id, course_id, category)
);

-- A specific offering of a course in a specific term, with an actual
-- time slot. day_time kept simple (text) for v1 — revisit if the
-- conflict-check logic needs structured start/end times.
create table sections (
    id uuid primary key default gen_random_uuid(),
    course_id uuid not null references courses(id) on delete cascade,
    term text not null,                     -- e.g. 'Fall 2027'
    days text not null,                     -- e.g. 'MWF'
    start_time time not null,
    end_time time not null,
    seats_total int not null check (seats_total > 0),
    seats_taken int not null default 0 check (seats_taken >= 0),
    constraint valid_time_range check (end_time > start_time),
    constraint seats_within_capacity check (seats_taken <= seats_total)
);

-- Per-student, per-course status. Confirmed once, satisfies every
-- requirement it applies to (per the double-major decision).
create table student_progress (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students(id) on delete cascade,
    course_id uuid not null references courses(id),
    status text not null check (status in ('done', 'in_progress', 'not_taken')),
    updated_at timestamptz not null default now(),
    unique (student_id, course_id)
);

-- The solver's actual output: one row per student per planned course.
-- is_locked = manual override (hard constraint on re-solve).
-- is_flagged = poor-choice indicator (soft warning, never blocks).
create table semester_plans (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students(id) on delete cascade,
    section_id uuid not null references sections(id),
    term text not null,
    is_locked boolean not null default false,
    is_flagged boolean not null default false,
    flag_reason text,
    created_at timestamptz not null default now(),
    unique (student_id, section_id)
);

-- Indexes for the lookups the solver and re-solve cascade run most:
-- pulling a student's progress/plan, and walking prereqs by course.
create index idx_student_progress_student on student_progress(student_id);
create index idx_semester_plans_student_term on semester_plans(student_id, term);
create index idx_prerequisites_course on prerequisites(course_id);
create index idx_sections_course_term on sections(course_id, term);
