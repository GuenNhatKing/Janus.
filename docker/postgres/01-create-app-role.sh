#!/usr/bin/env bash
set -eu

: "${POSTGRES_APP_PASSWORD:?POSTGRES_APP_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$POSTGRES_APP_PASSWORD" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pbl6_app') THEN
    CREATE ROLE pbl6_app LOGIN;
  END IF;
END
$$;

ALTER ROLE pbl6_app PASSWORD :'app_password';
ALTER DATABASE pbl6 OWNER TO pbl6_app;
GRANT CONNECT ON DATABASE pbl6 TO pbl6_app;
GRANT USAGE, CREATE ON SCHEMA public TO pbl6_app;
SQL
