FROM mongo:7.0-jammy

# Install cron, gzip, and other backup utilities
RUN apt-get update && apt-get install -y \
    cron \
    gzip \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install mongosh for backup operations
RUN curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
    gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg && \
    echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
    tee /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && \
    apt-get install -y mongodb-mongosh && \
    rm -rf /var/lib/apt/lists/*

# Create backup user and directories
RUN useradd -m -s /bin/bash backup && \
    mkdir -p /backups /scripts && \
    chown -R backup:backup /backups /scripts

# Copy backup scripts
COPY backup-mongodb.sh /scripts/
COPY backup-cleanup.sh /scripts/
COPY backup-entrypoint.sh /scripts/

# Make scripts executable
RUN chmod +x /scripts/*.sh

# Set up cron job for automated backups
COPY backup-crontab /etc/cron.d/backup-cron
RUN chmod 0644 /etc/cron.d/backup-cron && \
    crontab -u backup /etc/cron.d/backup-cron

# Switch to backup user
USER backup
WORKDIR /backups

# Health check
HEALTHCHECK --interval=1h --timeout=30s --start-period=1m --retries=3 \
    CMD /scripts/backup-mongodb.sh --health-check

# Entry point
ENTRYPOINT ["/scripts/backup-entrypoint.sh"]
CMD ["cron", "-f"]