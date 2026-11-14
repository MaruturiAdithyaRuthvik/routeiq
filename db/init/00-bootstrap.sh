#!/bin/sh
set -eu

case "$POSTGRES_DB" in
    ''|*[!a-zA-Z0-9_]*)
        echo "POSTGRES_DB must contain only letters, digits, or underscores" >&2
        exit 1
        ;;
esac

sql_literal() {
    printf "'"
    printf '%s' "$1" | sed "s/'/''/g"
    printf "'"
}

app_password="$(sql_literal "$ROUTEIQ_APP_PASSWORD")"
evaluator_password="$(sql_literal "$ROUTEIQ_EVALUATOR_PASSWORD")"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --file /opt/routeiq/db/schema.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --command "ALTER ROLE routeiq_app_login WITH LOGIN PASSWORD $app_password"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --command "ALTER ROLE routeiq_evaluator_login WITH LOGIN PASSWORD $evaluator_password"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --command "GRANT routeiq_app TO routeiq_app_login"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --command "GRANT routeiq_evaluator TO routeiq_evaluator_login"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --command "GRANT CONNECT ON DATABASE \"$POSTGRES_DB\" TO routeiq_app_login, routeiq_evaluator_login"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --file /opt/routeiq/db/views.sql
