#!/usr/bin/env sh
# Initialize the DB and start CMD as myuser
set -e

# Ensure the volume is owned by myuser
chown -R myuser:myuser /opt/pricetracker/instance

# Execute resto of the commands as myuser
su-exec myuser flask --app pricetracker init-db

exec su-exec myuser "$@"
