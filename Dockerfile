FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/nikolareljin/docforge"
LABEL org.opencontainers.image.description="Auto-generate developer and end-user documentation from any codebase"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY generate.py .
COPY src/ src/
COPY prompts/ prompts/
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

# Default config (can be overridden by mounting a volume)
COPY docforge.example.yml /app/docforge.default.yml

RUN chmod +x /app/docker-entrypoint.sh

# Git is needed for the git_log section analyzer
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up volume mount points
VOLUME ["/repo", "/output"]

# Environment variables with defaults
ENV CONFIG_FILE=/repo/.docforge.yml
ENV REPO_PATH=/repo
ENV OUTPUT_DIR=/output

ENTRYPOINT ["/app/docker-entrypoint.sh"]
