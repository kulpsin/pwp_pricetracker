#!/usr/bin/env sh
set -e

flask --app pricetracker init-db

exec "$@"
