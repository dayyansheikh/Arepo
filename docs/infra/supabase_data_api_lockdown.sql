-- Supabase Data API lockdown for AREPO (infra 2026-10-11). PREPARED ONLY — apply after approval.
--
-- Facts: AREPO never uses Supabase's Data API (PostgREST/supabase-js): the browser talks only to the
-- FastAPI service, which connects as the table OWNER via the session pooler. Owners bypass
-- (non-FORCED) RLS, so nothing below changes application behaviour; the backup's pg_dump also runs
-- as the owner (the 7 RLS tables already back up fine).
--
-- Effect:
--   * anon/authenticated lose every privilege on public tables/sequences/functions (now and future),
--     which also makes Supabase's 30 Oct "new tables need explicit Data API grants" change moot.
--   * RLS enabled on every public table, each with ONE explicit RESTRICTIVE deny-all policy for the
--     Data API roles: documents intent and clears the "RLS enabled, no policy" advisor (the 7 private
--     account tables) without granting anything.
-- Rollback: section at the bottom (restores Supabase's default grants; RLS/policies removable).
BEGIN;

REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;
-- Default privileges are per CREATING role: target Supabase's ``postgres`` role explicitly (the
-- app's migrations and the dashboard create objects as postgres), not just the session's role.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES    FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;

DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.relname);
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = t.relname
                   AND policyname = 'arepo_no_data_api') THEN
      EXECUTE format('CREATE POLICY arepo_no_data_api ON public.%I AS RESTRICTIVE FOR ALL '
                     'TO anon, authenticated USING (false) WITH CHECK (false)', t.relname);
    END IF;
  END LOOP;
END $$;

COMMIT;

-- Verification (expect 0 rows each; the third checks future-object defaults for postgres):
--   SELECT table_name FROM information_schema.role_table_grants
--    WHERE table_schema='public' AND grantee IN ('anon','authenticated');
--   SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
--    WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity;
--   SELECT * FROM pg_default_acl d JOIN pg_roles r ON r.oid = d.defaclrole
--    WHERE r.rolname = 'postgres' AND d.defaclnamespace = 'public'::regnamespace
--      AND (d.defaclacl::text LIKE '%anon=%' OR d.defaclacl::text LIKE '%authenticated=%');

-- ROLLBACK (only if ever needed):
-- BEGIN;
-- DO $$ DECLARE t record; BEGIN
--   FOR t IN SELECT tablename FROM pg_policies WHERE schemaname='public' AND policyname='arepo_no_data_api'
--   LOOP EXECUTE format('DROP POLICY arepo_no_data_api ON public.%I', t.tablename); END LOOP; END $$;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
-- GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO anon, authenticated;
-- ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES    TO anon, authenticated;
-- ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated;
-- ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon, authenticated;
-- (RLS on non-account tables may be left enabled: with the policy dropped and no grants it is inert.)
-- COMMIT;
