-- Removes seat capacity tracking from sections. koala has no live
-- connection to ORU's registration system (deliberately — see
-- CLAUDE.md's data-sourcing policy on never automating against
-- login-walled systems), so seats_total/seats_taken could only ever
-- show stale, manually-entered numbers presented as if they were
-- current. Better to not show it at all than show something that
-- looks live but isn't.

alter table sections
    drop constraint seats_within_capacity,
    drop column seats_total,
    drop column seats_taken;
