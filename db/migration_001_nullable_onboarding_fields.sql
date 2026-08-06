-- Fixes a real spec conflict: CLAUDE.md's POST /students/me creates a
-- profile immediately after signup (name + school only), but
-- class_standing/current_term aren't known until onboarding step 2.
-- NOT NULL on those columns was wrong. Run this once against the
-- already-applied schema (schema.sql itself is also updated to match,
-- for anyone setting up fresh going forward).

alter table students
    alter column class_standing drop not null;

alter table students
    alter column current_term drop not null;

alter table students
    add column onboarding_completed_at timestamptz;

-- Note: the existing `check (class_standing in (...))` constraint still
-- works correctly with NULL allowed — Postgres CHECK constraints treat
-- NULL as satisfying the constraint (they only fail on an explicit
-- false), so no constraint rewrite is needed.
