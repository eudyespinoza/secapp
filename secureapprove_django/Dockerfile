# ================================================
# SecureApprove Django - Simple Dockerfile
# ================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gettext \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Compile translation messages
RUN python manage.py compilemessages || echo "No translations to compile"

# Create directories first
RUN mkdir -p staticfiles media logs

# Collect static files (includes tenant_chat.js and all new files)
RUN python manage.py collectstatic --noinput --clear && \
    echo "✓ Static files collected successfully"

# Create non-root user
RUN adduser --disabled-password --gecos '' django

# Set permissions AFTER all file operations
RUN chown -R django:django /app && \
    chmod -R 755 /app

# Switch to django user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Set entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Run the application with ASGI server (Daphne) to support WebSockets
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
