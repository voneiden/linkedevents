#!/bin/bash

#################################################
# This based on:
# https://github.com/City-of-Helsinki/docker-images/blob/master/templates/postgis/9.6-2.5/initdb-postgis.sh
#
# Modifications:
# * "hstore" and "pg_trgm" extensions have been added.
# * converted $psql to not be a bash array because
#   passing those from yaml env definitions is pretty sketchy
# * Grab PG env vars from available test environment
#
#################################################

set -e

export PGUSER="$POSTGRES_USER"
export PGPASSWORD="$POSTGRES_PASSWORD"
export PGHOST="localhost"
export PGPORT="5432"

psql="psql -v ON_ERROR_STOP=1"

echo "Loading PostGIS extensions into $DB"
$psql --dbname="$POSTGRES_DB" <<-'EOSQL'
  CREATE EXTENSION IF NOT EXISTS postgis;
  CREATE EXTENSION IF NOT EXISTS hstore;
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  CREATE EXTENSION IF NOT EXISTS postgis_topology;
  -- Reconnect to update pg_setting.resetval
  -- See https://github.com/postgis/docker-postgis/issues/288
  \c
  CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
  CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
EOSQL
