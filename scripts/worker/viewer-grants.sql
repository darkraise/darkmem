-- The backup worker's SELECT-only role (spec section 9.5 as redesigned; review B1).
--
-- This file IS the enforcement. The DARKMEM_READ_ONLY flag is ergonomics --
-- it stops spend and quiets known write-on-read paths -- and no code path can
-- dig under what is granted here. Additions to this file are additions to the
-- attack surface and take a recorded reason: there is deliberately no GRANT on
-- sequences, no GRANT on functions, and no write verb anywhere below.
--
-- Applied by restore-cycle.sh to every freshly restored database BEFORE the
-- swap, while the app is still serving the previous one. Grants are re-run
-- each cycle because the side database is created fresh each time, so there is
-- no ALTER DEFAULT PRIVILEGES subtlety to rot.
--
-- Usage:
--   psql -v viewer_password='...' -v dbname='...' -f viewer-grants.sql
--
-- The role is cluster-global while the grants are per-database, which is why
-- the CREATE is guarded and the ALTER is unconditional: a second worker
-- database on the same cluster must find the role already there and must not
-- fail on it.

SELECT format('CREATE ROLE darkmem_viewer LOGIN PASSWORD %L', :'viewer_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'darkmem_viewer') \gexec

SELECT format('ALTER ROLE darkmem_viewer PASSWORD %L', :'viewer_password') \gexec

SELECT format('GRANT CONNECT ON DATABASE %I TO darkmem_viewer', :'dbname') \gexec

GRANT USAGE ON SCHEMA public TO darkmem_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO darkmem_viewer;
