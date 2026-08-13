-- Synthetic test-only catalog data for exercising the solver against a
-- real Postgres instance (catalog.py / cascade.py tests). NOT real ORU
-- course data — fixed UUIDs so it's safely re-runnable (delete-then-
-- insert) and easy to reference from tests.
--
-- Shape: Computer Science (major) structurally requires a Mathematics
-- minor; Studio Art is a free-standing (elective) minor. MATH121
-- deliberately satisfies both a CS major_core requirement AND the Math
-- minor requirement, to exercise the "course takes the max tier across
-- all applicable requirement rows" rule. CS110/THEO101 deliberately
-- clash in Fall <year> so tests can exercise real conflict-avoidance
-- against DB-sourced data, matching the scheduler sketch's own example.
-- ART100 has TWO sections in the current term — one clashes with
-- HIST101 (MWF 13:00), one doesn't (TR 13:00) — so tests can exercise
-- CLAUDE.md's "Multiple sections per course": the solver must offer
-- both as candidates, never schedule both at once, and pick the
-- non-conflicting one when both ART100 and HIST101 are wanted. The
-- conflicting ART100 section is ALSO split into two section_meetings
-- rows (MW 13:00 + a standalone F 15:00) — the multi-meeting example
-- CLAUDE.md's "Real day/time overlap logic (updated —
-- section_meetings)" describes (one section, more than one meeting
-- pattern). The MW meeting alone still conflicts with HIST101, so
-- this doesn't change which section the solver ends up preferring.
--
-- Terms are computed relative to real current date so a solve run
-- against "the current term" actually finds sections. Re-run this
-- script if it goes stale relative to the real calendar.

begin;

delete from prerequisites where course_id in (
    'bbbbbbbb-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000002',
    'bbbbbbbb-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000004',
    'bbbbbbbb-0000-0000-0000-000000000005', 'bbbbbbbb-0000-0000-0000-000000000006',
    'bbbbbbbb-0000-0000-0000-000000000007', 'bbbbbbbb-0000-0000-0000-000000000008',
    'bbbbbbbb-0000-0000-0000-000000000009', 'bbbbbbbb-0000-0000-0000-000000000010'
);
delete from degree_requirements where program_id in (
    'aaaaaaaa-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000002',
    'aaaaaaaa-0000-0000-0000-000000000003'
);
delete from sections where course_id in (
    'bbbbbbbb-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000002',
    'bbbbbbbb-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000004',
    'bbbbbbbb-0000-0000-0000-000000000005', 'bbbbbbbb-0000-0000-0000-000000000006',
    'bbbbbbbb-0000-0000-0000-000000000007', 'bbbbbbbb-0000-0000-0000-000000000008',
    'bbbbbbbb-0000-0000-0000-000000000009', 'bbbbbbbb-0000-0000-0000-000000000010'
);
delete from courses where id in (
    'bbbbbbbb-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000002',
    'bbbbbbbb-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000004',
    'bbbbbbbb-0000-0000-0000-000000000005', 'bbbbbbbb-0000-0000-0000-000000000006',
    'bbbbbbbb-0000-0000-0000-000000000007', 'bbbbbbbb-0000-0000-0000-000000000008',
    'bbbbbbbb-0000-0000-0000-000000000009', 'bbbbbbbb-0000-0000-0000-000000000010'
);
delete from programs where id in (
    'aaaaaaaa-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000002',
    'aaaaaaaa-0000-0000-0000-000000000003'
);

-- Programs: CS (major) structurally requires Math (minor); Studio Art
-- (minor) is free-standing.
insert into programs (id, name, type, department, required_by_program_id) values
    ('aaaaaaaa-0000-0000-0000-000000000001', 'Computer Science (TEST)', 'major', 'CS', null),
    ('aaaaaaaa-0000-0000-0000-000000000003', 'Studio Art (TEST)', 'minor', 'Art', null);
insert into programs (id, name, type, department, required_by_program_id) values
    ('aaaaaaaa-0000-0000-0000-000000000002', 'Mathematics (TEST)', 'minor', 'Math',
     'aaaaaaaa-0000-0000-0000-000000000001');

-- Courses
insert into courses (id, code, title, credit_hours, offering_frequency, department) values
    ('bbbbbbbb-0000-0000-0000-000000000001', 'CS110 (TEST)', 'Intro to Computer Science', 3, 'every_semester', 'CS'),
    ('bbbbbbbb-0000-0000-0000-000000000002', 'CS210 (TEST)', 'Data Structures', 4, 'every_semester', 'CS'),
    ('bbbbbbbb-0000-0000-0000-000000000003', 'CS310 (TEST)', 'Algorithms', 4, 'annual', 'CS'),
    ('bbbbbbbb-0000-0000-0000-000000000004', 'MATH120 (TEST)', 'Calculus 1', 4, 'every_semester', 'Math'),
    ('bbbbbbbb-0000-0000-0000-000000000005', 'MATH121 (TEST)', 'Calculus 2', 4, 'annual', 'Math'),
    ('bbbbbbbb-0000-0000-0000-000000000006', 'THEO101 (TEST)', 'Christian Foundations', 3, 'every_semester', 'Theology'),
    ('bbbbbbbb-0000-0000-0000-000000000007', 'ENGL101 (TEST)', 'Composition', 3, 'every_semester', 'English'),
    ('bbbbbbbb-0000-0000-0000-000000000008', 'HIST101 (TEST)', 'World History', 3, 'biennial', 'History'),
    ('bbbbbbbb-0000-0000-0000-000000000009', 'ART100 (TEST)', 'Intro to Studio Art', 3, 'every_semester', 'Art'),
    ('bbbbbbbb-0000-0000-0000-000000000010', 'ART200 (TEST)', 'Painting', 3, 'annual', 'Art');

-- Prerequisites
insert into prerequisites (course_id, prerequisite_course_id) values
    ('bbbbbbbb-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000001'), -- CS210 needs CS110
    ('bbbbbbbb-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000002'), -- CS310 needs CS210
    ('bbbbbbbb-0000-0000-0000-000000000005', 'bbbbbbbb-0000-0000-0000-000000000004'), -- MATH121 needs MATH120
    ('bbbbbbbb-0000-0000-0000-000000000010', 'bbbbbbbb-0000-0000-0000-000000000009'); -- ART200 needs ART100

-- Degree requirements. MATH121 deliberately double-counts: major_core
-- under CS AND minor under Math (tests the max-tier rule).
insert into degree_requirements (program_id, course_id, category) values
    ('aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000001', 'major_core'),
    ('aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000002', 'major_core'),
    ('aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000003', 'major_core'),
    ('aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000005', 'major_core'),
    ('aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000006', 'gen_ed'),
    ('aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000007', 'gen_ed'),
    ('aaaaaaaa-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000008', 'gen_ed'),
    ('aaaaaaaa-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000004', 'minor'),
    ('aaaaaaaa-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000005', 'minor'),
    ('aaaaaaaa-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000009', 'minor'),
    ('aaaaaaaa-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000010', 'minor');

-- Sections, computed relative to real current date so "the current
-- term" resolves to something with real offerings. CS110/THEO101
-- deliberately clash (MWF 9:00-9:50) in the fall term. Fixed UUIDs
-- (cccc- prefix, matching aaaa-/bbbb- for programs/courses) so
-- section_meetings rows below can reference them directly.
insert into sections (id, course_id, term, seats_total) values
    ('cccccccc-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000001',
     case when extract(month from now()) between 1 and 7
          then 'Spring ' || extract(year from now())::int
          else 'Fall ' || extract(year from now())::int end,
     30),
    ('cccccccc-0000-0000-0000-000000000002', 'bbbbbbbb-0000-0000-0000-000000000006',
     case when extract(month from now()) between 1 and 7
          then 'Spring ' || extract(year from now())::int
          else 'Fall ' || extract(year from now())::int end,
     30),
    ('cccccccc-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000004',
     case when extract(month from now()) between 1 and 7
          then 'Spring ' || extract(year from now())::int
          else 'Fall ' || extract(year from now())::int end,
     30),
    ('cccccccc-0000-0000-0000-000000000004', 'bbbbbbbb-0000-0000-0000-000000000007',
     case when extract(month from now()) between 1 and 7
          then 'Spring ' || extract(year from now())::int
          else 'Fall ' || extract(year from now())::int end,
     30),
    ('cccccccc-0000-0000-0000-000000000005', 'bbbbbbbb-0000-0000-0000-000000000009',
     case when extract(month from now()) between 1 and 7
          then 'Spring ' || extract(year from now())::int
          else 'Fall ' || extract(year from now())::int end,
     30),
    ('cccccccc-0000-0000-0000-000000000006', 'bbbbbbbb-0000-0000-0000-000000000008',
     case when extract(month from now()) between 1 and 7
          then 'Spring ' || extract(year from now())::int
          else 'Fall ' || extract(year from now())::int end,
     30),
    -- ART100's second current-term section — the one that conflicts
    -- with HIST101, and the one split into two meetings below.
    ('cccccccc-0000-0000-0000-000000000007', 'bbbbbbbb-0000-0000-0000-000000000009',
     case when extract(month from now()) between 1 and 7
          then 'Spring ' || extract(year from now())::int
          else 'Fall ' || extract(year from now())::int end,
     30),
    -- next term (fall -> spring of next year, or spring -> fall same year)
    ('cccccccc-0000-0000-0000-000000000008', 'bbbbbbbb-0000-0000-0000-000000000002',
     case when extract(month from now()) between 1 and 7
          then 'Fall ' || extract(year from now())::int
          else 'Spring ' || (extract(year from now())::int + 1) end,
     30),
    ('cccccccc-0000-0000-0000-000000000009', 'bbbbbbbb-0000-0000-0000-000000000005',
     case when extract(month from now()) between 1 and 7
          then 'Fall ' || extract(year from now())::int
          else 'Spring ' || (extract(year from now())::int + 1) end,
     30),
    ('cccccccc-0000-0000-0000-000000000010', 'bbbbbbbb-0000-0000-0000-000000000010',
     case when extract(month from now()) between 1 and 7
          then 'Fall ' || extract(year from now())::int
          else 'Spring ' || (extract(year from now())::int + 1) end,
     30),
    -- term after next: CS310 needs CS210 (seeded in the "next term"
    -- bucket above), so it can't be schedulable any earlier than a
    -- third term without violating its own prerequisite. Without this
    -- row CS310 has zero sections ever, which is a required major_core
    -- course that can never be scheduled — the walk-forward cascade
    -- would spin through all MAX_SEMESTERS terms looking for it.
    ('cccccccc-0000-0000-0000-000000000011', 'bbbbbbbb-0000-0000-0000-000000000003',
     case when extract(month from now()) between 1 and 7
          then 'Spring ' || (extract(year from now())::int + 1)
          else 'Fall ' || (extract(year from now())::int + 1) end,
     30);

-- Meeting patterns. One row per section, except section 0007 (ART100's
-- conflicting section), which gets two — a lecture-style MW block plus
-- a standalone Friday block, mirroring the real CSC 255 lecture-plus-
-- discussion example. The MW meeting alone already conflicts with
-- HIST101 (0006, MWF 13:00-13:50), so this doesn't change which
-- section the solver prefers — it only proves the conflict check
-- correctly walks every meeting pair, not just the first.
insert into section_meetings (section_id, days, start_time, end_time) values
    ('cccccccc-0000-0000-0000-000000000001', 'MWF', '09:00', '09:50'),
    ('cccccccc-0000-0000-0000-000000000002', 'MWF', '09:00', '09:50'),
    ('cccccccc-0000-0000-0000-000000000003', 'TR', '09:30', '10:45'),
    ('cccccccc-0000-0000-0000-000000000004', 'MWF', '11:00', '11:50'),
    ('cccccccc-0000-0000-0000-000000000005', 'TR', '13:00', '14:15'),
    ('cccccccc-0000-0000-0000-000000000006', 'MWF', '13:00', '13:50'),
    ('cccccccc-0000-0000-0000-000000000007', 'MW', '13:00', '13:50'),
    ('cccccccc-0000-0000-0000-000000000007', 'F', '15:00', '15:50'),
    ('cccccccc-0000-0000-0000-000000000008', 'TR', '09:30', '10:45'),
    ('cccccccc-0000-0000-0000-000000000009', 'MWF', '10:00', '10:50'),
    ('cccccccc-0000-0000-0000-000000000010', 'TR', '11:00', '12:15'),
    ('cccccccc-0000-0000-0000-000000000011', 'MWF', '10:00', '10:50');

commit;
