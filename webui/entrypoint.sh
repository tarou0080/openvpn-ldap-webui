#!/bin/bash
# Create data directories and set permissions
mkdir -p /app/data/{db,certs,logs}
chmod 755 /app/data/{db,certs,logs}

# Start logging
echo "$(date): VPN WebUI starting with supervisord..." >> /app/data/logs/app.log

# Check database directory permissions
if [ ! -w "/app/data/db" ]; then
    echo "Error: Database directory is not writable" >> /app/data/logs/app.log
    exit 1
fi

# Start supervisord (foreground execution)
echo "$(date): Starting supervisord..." >> /app/data/logs/app.log
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf