FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .
RUN pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd -m -u 1000 devilmcp && \
    chown -R devilmcp:devilmcp /app
USER devilmcp

# Create data directory
RUN mkdir -p /home/devilmcp/data

# Environment
ENV DEVILMCP_STORAGE_PATH=/home/devilmcp/data
ENV DEVILMCP_LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD python -c "import devilmcp" || exit 1

ENTRYPOINT ["python", "-m", "devilmcp.server"]
