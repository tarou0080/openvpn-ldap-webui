FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Update system packages and install OpenVPN related tools and supervisord
RUN apt-get update && apt-get install -y \
    easy-rsa \
    openssl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy supervisord configuration and entrypoint
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

# Create data directories
RUN mkdir -p /app/data/{db,certs,logs}

# Expose port 5000
EXPOSE 5000

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]