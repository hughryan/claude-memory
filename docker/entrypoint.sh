#!/bin/bash
set -e

# Run migrations if enabled
if [ "$DEVILMCP_AUTO_MIGRATE" != "false" ]; then
    echo "Running database migrations..."
    python -c "from devilmcp.database import run_migrations; from devilmcp.config import settings; run_migrations(settings.get_database_url())"
fi

# Start server
exec python -m devilmcp.server "$@"
